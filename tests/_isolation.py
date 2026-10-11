"""The test suite never touches the user's real folders, and fails the session if it ever does.

1.29.7: a full suite run appended four entries to the real `~/socialforge-workspace/socialforge/shared/failure-log.jsonl`
(129 runs, 516 entries by 2026-10-12). `test_provider_failures.py` isolated the CREDENTIAL store but not the failure log, and
`provider_failures` falls back to `Path.home()` when no data folder is set, so the failure of a deliberately credential-less
provider chain was written where a customer's real "action required" list is read from.

Two layers, because one test forgetting to isolate must not be enough to reach a real folder:

1. `start()` points HOME, USERPROFILE and every plugin-data variable the scripts read at a temporary folder, before any test
   module is imported. A test that sets nothing therefore writes into the temporary folder.
2. `start()` also snapshots the REAL folders (path, size, mtime of every file) and `finish()` compares at the end. Any added,
   removed or changed file is a failure of the whole session, so the next leak is loud instead of 129 runs old.

`tests/__init__.py` starts it for pytest and `python -m unittest`, `run_all.py` starts it for the stdlib runner, and an exit
hook covers direct runs of one test file. `start(redirect=False)` is the guard alone, used to prove the guard catches a leak.
"""
from __future__ import annotations

import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

HOME_VARS = ("HOME", "USERPROFILE")
DATA_VARS = ("CLAUDE_PLUGIN_DATA", "CLAUDE_PLUGIN_DATA_DIR", "PLUGIN_DATA")

_state: dict = {"started": False, "finished": False}


def real_folders() -> list:
    """The folders a SocialForge run really writes to for this user, as the environment names them at this moment."""
    roots = [Path.home() / "socialforge-workspace"]
    roots += [Path(os.environ[name]) for name in DATA_VARS if os.environ.get(name)]
    unique, seen = [], set()
    for root in roots:
        key = os.path.normcase(os.path.abspath(root))
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def snapshot(roots) -> dict:
    """path -> "dir" | "absent" | (size, mtime_ns) for every folder and file under each root."""
    seen: dict = {}
    for root in roots:
        root = str(root)
        if not os.path.isdir(root):
            seen[root] = "absent"
            continue
        seen[root] = "dir"
        for dirpath, dirnames, filenames in os.walk(root, onerror=lambda error: None):
            for name in dirnames:
                seen[os.path.join(dirpath, name)] = "dir"
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    stat = os.stat(path)
                except OSError:
                    continue
                seen[path] = (stat.st_size, stat.st_mtime_ns)
    return seen


def changes(before: dict, after: dict) -> list:
    out = []
    for path in sorted(set(before) | set(after)):
        was, now = before.get(path), after.get(path)
        if was == now:
            continue
        if was in (None, "absent"):
            out.append("added: " + path)
        elif now in (None, "absent"):
            out.append("removed: " + path)
        else:
            out.append("changed: " + path)
    return out


def start(redirect: bool = True) -> None:
    """Idempotent. Call before any test module is imported."""
    if _state["started"]:
        return
    _state.update(started=True, finished=False, roots=real_folders())
    _state["before"] = snapshot(_state["roots"])
    if redirect:
        tmp = Path(tempfile.mkdtemp(prefix="sf-tests-"))
        home, data = tmp / "home", tmp / "plugin-data"
        home.mkdir()
        data.mkdir()
        for name in HOME_VARS:
            os.environ[name] = str(home)
        for name in DATA_VARS:
            os.environ[name] = str(data)
        _state["tmp"] = tmp
        _state["redirected"] = {name: os.environ[name] for name in HOME_VARS + DATA_VARS}
    atexit.register(_at_exit)


def finish() -> list:
    """Compare the real folders with their snapshot and remove the temporary folder. Returns the changes (empty is good)."""
    if not _state["started"] or _state["finished"]:
        return []
    _state["finished"] = True
    problems = changes(_state["before"], snapshot(_state["roots"]))
    if _state.get("tmp"):
        shutil.rmtree(_state["tmp"], ignore_errors=True)
    return problems


def report(problems: list) -> str:
    shown = problems[:12]
    more = "" if len(problems) <= 12 else "\n  ... and %d more" % (len(problems) - 12)
    return ("\nTEST SUITE TOUCHED THE USER'S REAL FOLDERS (%d change%s):\n  %s%s\n"
            "A test wrote there instead of into its temporary folder, or a live SocialForge run wrote there while the suite ran: "
            "run the suite again to tell which. A test that leaks is a bug: it pollutes the customer's own failure log and credentials."
            % (len(problems), "" if len(problems) == 1 else "s", "\n  ".join(shown), more))


def _at_exit() -> None:
    """Direct runs (`python tests/test_x.py`) have no runner hook, so the exit hook enforces the guard."""
    problems = finish()
    if problems:
        sys.stderr.write(report(problems))
        sys.stderr.flush()
        os._exit(1)
