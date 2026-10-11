"""The suite stays out of the user's real folders (1.29.7), and the guard that says so is itself tested.

`test_provider_failures.py` isolated the credential store but not the failure log, so every run appended four entries to the
real `~/socialforge-workspace/socialforge/shared/failure-log.jsonl` (516 entries over 129 runs before anyone noticed). The fix
has two layers (see `_isolation.py`) and each one is proved here: the redirect keeps a forgetful test out of the real folder, and
the guard fails the session when something still gets in. The plants run the real writer in a child process against a FAKE
home, with the redirect on, with only the guard on, and with neither, because a guard nobody has seen fail has not been tested.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "scripts"
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(SCRIPTS))

import _isolation  # noqa: E402

_isolation.start()    # a direct run of this file is protected too; a no-op when the runner already started it

LEAK = r'''
import json, os, sys
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, sys.argv[2])
mode = sys.argv[3]
import _isolation
if mode in ("guard-only", "exit-hook"):
    _isolation.start(redirect=False)
elif mode == "full":
    _isolation.start()
import provider_failures
provider_failures.failure_payload([{"provider": "a", "stage": "credentials", "reason": "no-credentials", "detail": ""}], context="plant")
if mode != "exit-hook":
    print(json.dumps({"problems": _isolation.finish()}))
'''


class TestTheSessionIsRedirected(unittest.TestCase):
    def test_home_and_every_data_variable_were_pointed_into_the_temporary_folder(self):
        """Judged from what start() set, not from os.environ now: several older tests pop CLAUDE_PLUGIN_DATA when they finish, which
        is why HOME is a second layer (the next test)."""
        tmp = _isolation._state["tmp"]
        self.assertEqual(sorted(_isolation._state["redirected"]), sorted(_isolation.HOME_VARS + _isolation.DATA_VARS))
        for name, value in _isolation._state["redirected"].items():
            with self.subTest(var=name):
                self.assertEqual(Path(value).parent, tmp)
        for name in _isolation.HOME_VARS:      # no test removes these
            self.assertEqual(Path(os.environ[name]).parent, tmp)
        self.assertEqual(Path.home().parent, tmp)

    def test_the_failure_log_and_the_workspace_resolve_inside_it(self):
        import provider_failures
        tmp = _isolation._state["tmp"]
        self.assertTrue(str(provider_failures._failure_log_path()).startswith(str(tmp)), provider_failures._failure_log_path())

    def test_a_test_that_pops_the_data_variables_still_cannot_reach_the_real_home(self):
        """Several existing tests do `os.environ.pop("CLAUDE_PLUGIN_DATA")` in a finally block. The second layer (HOME) holds."""
        import provider_failures
        tmp = _isolation._state["tmp"]
        with mock.patch.dict(os.environ):
            for name in _isolation.DATA_VARS:
                os.environ.pop(name, None)
            self.assertTrue(str(provider_failures._failure_log_path()).startswith(str(tmp)), provider_failures._failure_log_path())

    def test_the_real_folders_named_by_the_guard_are_not_the_redirected_ones(self):
        tmp = _isolation._state["tmp"]
        self.assertTrue(_isolation._state["roots"], "the guard watches nothing")
        for root in _isolation._state["roots"]:
            self.assertFalse(str(root).startswith(str(tmp)), "the guard is watching the temporary folder, not the real one: %s" % root)


class TestTheSnapshotSeesEveryKindOfChange(unittest.TestCase):
    def test_added_changed_removed_new_folder_and_a_root_that_appears(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "workspace"
            root.mkdir()
            (root / "keep.txt").write_text("one", encoding="utf-8")
            (root / "edit.txt").write_text("one", encoding="utf-8")
            (root / "drop.txt").write_text("one", encoding="utf-8")
            missing = Path(d) / "not-there-yet"
            before = _isolation.snapshot([root, missing])
            self.assertEqual(_isolation.changes(before, _isolation.snapshot([root, missing])), [])
            (root / "edit.txt").write_text("one and more", encoding="utf-8")
            (root / "drop.txt").unlink()
            (root / "new.txt").write_text("x", encoding="utf-8")
            (root / "sub").mkdir()
            missing.mkdir()
            found = _isolation.changes(before, _isolation.snapshot([root, missing]))
            self.assertEqual(sorted(entry.split(":")[0] for entry in found), ["added", "added", "added", "changed", "removed"], found)
            self.assertTrue(any(entry.startswith("added: ") and entry.endswith("not-there-yet") for entry in found), found)
            self.assertFalse(any("keep.txt" in entry for entry in found), found)


class TestThePlantsTheGuardMustCatch(unittest.TestCase):
    """The real failure writer, run in a child process against a FAKE home so nothing real is at risk."""

    def _run(self, mode):
        with tempfile.TemporaryDirectory() as fake_home:
            env = {k: v for k, v in os.environ.items() if k not in _isolation.DATA_VARS}
            env.update(HOME=fake_home, USERPROFILE=fake_home, PYTHONIOENCODING="utf-8")
            r = subprocess.run([sys.executable, "-c", LEAK, str(TESTS), str(SCRIPTS), mode],
                               capture_output=True, text=True, env=env, timeout=120)
            log = Path(fake_home) / "socialforge-workspace" / "socialforge" / "shared" / "failure-log.jsonl"
            return r, log.is_file(), json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else None

    def test_without_the_fixture_the_writer_does_reach_the_home_folder(self):
        """The victim can be hit: this is the 1.29.6 behaviour, and the reason the other plants mean anything."""
        r, leaked, _ = self._run("off")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(leaked, "the plant did not reproduce the leak, so the next two tests prove nothing")

    def test_the_guard_alone_catches_the_leak(self):
        r, leaked, out = self._run("guard-only")
        self.assertTrue(leaked)
        self.assertTrue(any(p.startswith("added: ") and p.endswith("failure-log.jsonl") for p in out["problems"]), out)
        self.assertIn("TEST SUITE TOUCHED THE USER'S REAL FOLDERS", _isolation.report(out["problems"]))

    def test_the_redirect_alone_keeps_the_same_test_out_of_the_home_folder(self):
        r, leaked, out = self._run("full")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(leaked, "the redirect did not hold")
        self.assertEqual(out["problems"], [])

    def test_a_run_nobody_wraps_still_exits_nonzero_when_the_guard_trips(self):
        """`python tests/test_x.py` has no runner hook; the exit hook turns a leak into exit status 1."""
        r, leaked, _ = self._run("exit-hook")
        self.assertTrue(leaked)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("TEST SUITE TOUCHED THE USER'S REAL FOLDERS", r.stderr)


if __name__ == "__main__":
    unittest.main()
