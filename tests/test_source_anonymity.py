"""The methodology's source organization must NEVER be named anywhere in the repo.

This is a hard product rule that was, until now, only ever enforced by hand —
and a violation shipped for months in a sibling plugin's spec before the
2026-07-29 audit caught it. The forbidden strings are assembled at runtime from
fragments so this test file itself keeps the repository grep-clean.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2",
                 ".ttf", ".zip", ".docx", ".pdf", ".pyc"}


def _needles() -> list[re.Pattern]:
    # Assembled from fragments on purpose — the plain strings must not exist
    # in the repository, including in this file.
    org = "tech" + "shu"
    agency_host = "int" + "global"
    agency_name = r"\bint\.?\s+" + "global" + r"\b"
    return [
        re.compile(org, re.I),
        re.compile(agency_host, re.I),
        re.compile(agency_name, re.I),
    ]


class TestSourceAnonymity(unittest.TestCase):
    def test_source_organization_never_named(self):
        needles = _needles()
        this_file = Path(__file__).resolve()
        hits: list[str] = []
        for p in REPO.rglob("*"):
            if not p.is_file():
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if p.suffix.lower() in SKIP_SUFFIXES:
                continue
            if p.resolve() == this_file:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for n in needles:
                m = n.search(text)
                if m:
                    line = text.count("\n", 0, m.start()) + 1
                    hits.append(f"{p.relative_to(REPO)}:{line}")
                    break
        self.assertEqual(hits, [],
                         "the source organization is named in these files — "
                         "remove every occurrence before shipping: " + ", ".join(hits))


if __name__ == "__main__":
    unittest.main()
