"""pytest: fail the whole session when the suite changed the user's real folders (see _isolation.py)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _isolation  # noqa: E402

_isolation.start()


def pytest_sessionfinish(session, exitstatus):
    problems = _isolation.finish()
    if problems:
        sys.stderr.write(_isolation.report(problems))
        session.exitstatus = 1
