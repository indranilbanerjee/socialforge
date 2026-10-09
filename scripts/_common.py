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
from pathlib import Path


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
