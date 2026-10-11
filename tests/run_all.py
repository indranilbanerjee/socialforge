"""Run every test_*.py in this directory. Exit non-zero on failure.

Stdlib-only. No pytest needed.

Usage:
    python tests/run_all.py
    python tests/run_all.py -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

import _isolation  # noqa: E402  (before any test module is imported: keeps the suite out of the user's real folders)

_isolation.start()


def main() -> int:
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(TESTS_DIR), pattern="test_*.py",
                            top_level_dir=str(TESTS_DIR))
    verbosity = 2 if "-v" in sys.argv else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    problems = _isolation.finish()
    if problems:
        sys.stderr.write(_isolation.report(problems))
    return 0 if result.wasSuccessful() and not problems else 1


if __name__ == "__main__":
    sys.exit(main())
