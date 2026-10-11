"""Importing the tests package (pytest, `python -m unittest`) puts the suite behind the real-folder guard before any test is collected."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _isolation  # noqa: E402

_isolation.start()
