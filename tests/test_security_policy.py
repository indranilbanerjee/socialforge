"""SECURITY.md names the version that is actually supported.

The policy sentence says "the latest minor release receives security fixes"; the table under it must name that
minor. For a long time it did not: the supported-versions table named a release many minors behind the product
(ContentForge 3.12.x while the product was on 4.5.x, SocialForge 1.13.x on 1.30.x, CutForge 1.0.x on 1.1.x), so a reader
could not tell what was supported. Release.py stamps manifests and READMEs but not SECURITY.md, so nothing noticed.

The table must read, for a product on MAJOR.MINOR.PATCH:
  * first row: MAJOR.MINOR.x, supported;
  * second row (only when MINOR > 0): MAJOR.(MINOR-1).x, fixes only when trivially backportable;
  * last row: everything older, "< MAJOR.(MINOR-1)" (or "< MAJOR.MINOR" at MINOR 0), please upgrade.
So bumping the manifest without updating SECURITY.md fails here, on the day of the release.
Stdlib only.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / ".claude-plugin" / "plugin.json"
SECTION = re.compile(r"(?ms)^## Supported Versions\s*$(.*?)(?=^## |\Z)")
ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*$")


def rows(text: str) -> list:
    """(version cell, status cell) for each data row of the Supported Versions table."""
    m = SECTION.search(text)
    if not m:
        return []
    found = [ROW.match(line.strip()) for line in m.group(1).splitlines()]
    cells = [(r.group(1), r.group(2)) for r in found if r]
    return [c for c in cells if c[0].lower() != "version" and not set(c[0]) <= set("-: ")]


def problems(text: str, version: str) -> list:
    major, minor = (int(p) for p in version.split(".")[:2])
    table = rows(text)
    if not table:
        return ["SECURITY.md has no 'Supported Versions' table"]
    want = [(f"{major}.{minor}.x", "✅")]
    if minor > 0:
        want.append((f"{major}.{minor - 1}.x", "⚠️"))
    want.append((f"< {major}.{minor - 1 if minor > 0 else minor}", "❌"))
    out = []
    if len(table) != len(want):
        out.append(f"the table has {len(table)} rows; for {version} it needs {len(want)}: " + ", ".join(w[0] for w in want))
    for got, (ver, mark) in zip(table, want):
        if got[0] != ver:
            out.append(f"row says {got[0]!r}; for {version} it should say {ver!r}")
        elif not got[1].startswith(mark):
            out.append(f"row {ver!r} has status {got[1]!r}; it should start with {mark}")
    return out


STALE = ("# Security Policy\n\n## Supported Versions\n\nThe latest minor release receives security fixes.\n\n"
         "| Version | Supported |\n|---------|-----------|\n| 3.12.x   | ✅ |\n"
         "| 3.11.x   | ⚠️ Security fixes only when trivially backportable |\n| < 3.11   | ❌ Please upgrade |\n\n"
         "## Reporting a Vulnerability\n\nx\n")


def policy(first: str, second: str | None, last: str) -> str:
    body = f"| {first} | ✅ |\n"
    if second:
        body += f"| {second} | ⚠️ Security fixes only when trivially backportable |\n"
    return ("# Security Policy\n\n## Supported Versions\n\nThe latest minor release receives security fixes.\n\n"
            f"| Version | Supported |\n|---------|-----------|\n{body}| {last} | ❌ Please upgrade |\n\n"
            "## Reporting a Vulnerability\n\nx\n")


class TestSecurityPolicyNamesTheCurrentVersion(unittest.TestCase):

    def test_the_shipped_policy_matches_the_manifest(self):
        version = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))["version"]
        found = problems((REPO / "SECURITY.md").read_text(encoding="utf-8-sig"), version)
        self.assertEqual(found, [], "\n  " + "\n  ".join(found))

    def test_a_table_that_lags_the_product_fails(self):
        found = problems(STALE, "4.5.12")
        self.assertTrue(any("'3.12.x'" in line and "'4.5.x'" in line for line in found), found)

    def test_the_right_table_passes(self):
        self.assertEqual(problems(policy("4.5.x", "4.4.x", "< 4.4"), "4.5.12"), [])
        self.assertEqual(problems(policy("1.30.x", "1.29.x", "< 1.29"), "1.30.2"), [])

    def test_a_release_bump_without_the_policy_fails(self):
        # The day 4.5.12 becomes 4.6.0 and SECURITY.md still says 4.5.x, the guard goes red.
        found = problems(policy("4.5.x", "4.4.x", "< 4.4"), "4.6.0")
        self.assertTrue(found)
        self.assertIn("'4.6.x'", found[0])

    def test_a_first_minor_has_no_previous_row(self):
        self.assertEqual(problems(policy("2.0.x", None, "< 2.0"), "2.0.3"), [])
        self.assertTrue(problems(policy("2.0.x", "1.9.x", "< 1.9"), "2.0.3"))

    def test_a_status_without_its_mark_fails(self):
        text = policy("4.5.x", "4.4.x", "< 4.4").replace("| 4.5.x | ✅ |", "| 4.5.x | yes |")
        self.assertTrue(any("status" in line for line in problems(text, "4.5.12")))

    def test_a_missing_table_fails(self):
        self.assertEqual(problems("# Security Policy\n\nNothing here.\n", "4.5.12"),
                         ["SECURITY.md has no 'Supported Versions' table"])


if __name__ == "__main__":
    unittest.main()
