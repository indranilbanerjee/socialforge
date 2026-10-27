#!/usr/bin/env python3
"""
_common.py - helpers shared by the SocialForge scripts. Stdlib only.

Today it holds the path-containment helpers. `--brand` and `--month` arrive from the model or from a
pasted brief, and most scripts join them straight into the workspace (`WORKSPACE / "output" / brand /
month / ...`), so a value such as `../../x` or an absolute path would pick a folder outside the
workspace (Hermes review of 2026-10-04). Every script that declares `--brand` or `--month` passes the
value through `path_component` as its argparse `type`; a guard test enforces it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


PYTHON_PREFERRED = (3, 11)


def python_floor_warning(version=None):
    """A warning when this interpreter is older than 3.11, else None.

    Python 3.10 reached end of life on 2026-10-01 (PEP 619), but Claude's Cowork environment ran 3.10.12 when last checked,
    so NO release is promised for the move: SocialForge still runs on 3.10 and will move to 3.11 once Cowork does. The warning says that,
    conditionally, and asks for 3.11 or newer where the user can."""
    found = tuple((version or sys.version_info)[:2])
    if found < PYTHON_PREFERRED:
        return ("Python 3.10 reached end of life on 2026-10-01. SocialForge still runs on it, and will move to 3.11 once Claude's Cowork "
                "environment does (it ran 3.10.12 when last checked). Use 3.11 or newer where you can.")
    return None


def printed_command(*tokens: str) -> str:
    """A command to PRINT, ready to paste into Git Bash or PowerShell: the interpreter that is running now, then `tokens`. The
    interpreter path uses FORWARD slashes (bash drops a backslash, so `C:\\Python313\\python.exe` arrives as `C:Python313python.exe`)
    and is quoted only when it has a space, because a quoted first token is a string literal in PowerShell; then the line ends with
    a trailing comment (bash and PowerShell both ignore it) saying to put `&` before it. A parenthetical there is a syntax error in
    bash, and anything appended after the line lands inside the comment, so a caller puts prose BEFORE the command and passes every
    argument as a token. Code that RUNS something passes an argv list to subprocess instead and never uses this."""
    exe = sys.executable.replace("\\", "/")
    spaced = " " in exe
    line = " ".join(['"%s"' % exe if spaced else exe, *tokens])
    return line + "  # in PowerShell, put & before it" if spaced else line


def _quote_arg(arg: str) -> str:
    return '"%s"' % arg if any(c.isspace() for c in arg) and '"' not in arg else arg


def script_command(script: str, *args: str) -> str:
    """The exact command that runs one of this plugin's scripts (see printed_command): the script's absolute path with forward
    slashes, always double-quoted, then the arguments (quoted when they contain a space). A printed `python scripts/x.py` is relative
    to the host's working folder (the user's project), which is the wrong place, so every command a script tells someone to run
    comes from here."""
    path = str(Path(__file__).resolve().parent / script).replace("\\", "/")
    return printed_command('"%s"' % path, *[_quote_arg(a) for a in args])


def is_single_component(name) -> bool:
    """True for one plain folder name: not empty, not '.' or '..', no separator of either kind, no
    drive or stream colon, no NUL, not absolute."""
    s = str(name if name is not None else "")
    if not s or s in (".", "..") or "\x00" in s or "/" in s or chr(92) in s or ":" in s:
        return False
    return Path(s).name == s and not Path(s).is_absolute()


def path_component(value):
    """argparse `type` for --brand / --month: one plain folder name, or a clear usage error.

    An empty string passes through unchanged: several scripts default these to "" meaning "not
    given", and argparse also runs the type over string defaults."""
    if value == "":
        return value
    if not is_single_component(value):
        raise argparse.ArgumentTypeError(
            f"must be a single folder name, not a path (no '/', '\\', '..' or ':'): {value!r}")
    return value


def safe_child(base, name) -> Path:
    """`base / name`, resolved, guaranteed to stay directly inside `base` (ValueError otherwise)."""
    if not is_single_component(name):
        raise ValueError(f"unsafe path component: {name!r}")
    base_resolved = Path(base).resolve()
    child = (base_resolved / str(name)).resolve()
    if child.parent != base_resolved:
        raise ValueError(f"path escapes its directory: {name!r}")
    return child


def genai_http_options():
    """HttpOptions for a google-genai client built with an API key: the client never follows a redirect.

    The SDK's own httpx client follows redirects, httpx drops only `Authorization` when one leaves the origin, and an API key
    travels as `x-goog-api-key`, so a 30x answer would carry the key to whatever host it names. `follow_redirects=False` keeps
    it on the host it was sent to (the SDK still adds its TLS context to these arguments). A Vertex AI client sends an OAuth
    `Authorization` header, which httpx and `requests` both drop, and does not need this.
    """
    from google.genai import types
    return types.HttpOptions(client_args={"follow_redirects": False}, async_client_args={"follow_redirects": False})
