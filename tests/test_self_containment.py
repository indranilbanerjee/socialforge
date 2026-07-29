"""Self-containment guard: no part of the plugin may delegate a capability to a
sibling plugin.

Rule: each plugin in the suite is fully standalone. Cross-promotion (links to the
author's other repos, marketplace install lines, shared model-registry sync
infrastructure) is fine; capability delegation is not.

Extended 2026-07-29 after the full-repo audit: the original guard scanned only
skills/agents/commands/*.md and therefore missed live violations in references/ and scripts/.
"""
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SIBLING_PATTERN = re.compile(
    r"digital-marketing-pro|digital marketing pro|contentforge|content-forge", re.IGNORECASE
)

# The functional surface: capability delegation here is always a violation.
SURFACE_DIRS = ("skills", "agents", "commands")

# Extended scope: everything else that ships.
EXTENDED_DIRS = ("docs", "scripts", "references", "assets")
ROOT_FILES = ("AGENTS.md", "CONTRIBUTING.md", "SUBMISSION.md", "TESTING-GUIDE.md",
    "CONNECTORS.md", "SECURITY.md", "SOCIALFORGE-COMPLETE-ENGINEERING-SPEC.md",)
EXTENDED_SUFFIXES = {".md", ".py", ".sh", ".yaml", ".yml", ".js"}

# Files that legitimately reference the sibling repos (shared registry infra).
FILE_ALLOWLIST = {
    "scripts/model_registry.json",
}

# A line mentioning a sibling is allowed only if it is clearly promo/infra:
LINE_ALLOW_MARKERS = (
    "github.com/indranilbanerjee/",   # links to the author's other repos
    "/plugin install",                # marketplace install commands
    "claude plugin install",
)

# Deliberate one-off exceptions, as "relative/path.md:token".
ALLOWLIST: set = set()


def _scan(files):
    violations = []
    for f in files:
        rel = f.relative_to(REPO).as_posix()
        if rel in FILE_ALLOWLIST or rel == "CHANGELOG.md":
            continue
        for i, line in enumerate(
            f.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            m = SIBLING_PATTERN.search(line)
            if not m:
                continue
            if any(marker in line for marker in LINE_ALLOW_MARKERS):
                continue
            if f"{rel}:{m.group(0).lower()}" in ALLOWLIST:
                continue
            violations.append(f"{rel}:{i}: {line.strip()[:100]}")
    return violations


class TestSelfContainment(unittest.TestCase):
    def test_no_sibling_plugin_references_in_functional_surface(self):
        files = []
        for d in SURFACE_DIRS:
            root = REPO / d
            if root.is_dir():
                files.extend(sorted(root.rglob("*.md")))
        violations = _scan(files)
        self.assertEqual(
            violations,
            [],
            "Sibling-plugin references found in the functional surface "
            "(skills must be self-contained):\n" + "\n".join(violations),
        )

    def test_no_sibling_plugin_references_in_docs_scripts_and_root(self):
        files = []
        for d in EXTENDED_DIRS:
            root = REPO / d
            if root.is_dir():
                files.extend(
                    f
                    for f in sorted(root.rglob("*"))
                    if f.is_file() and f.suffix.lower() in EXTENDED_SUFFIXES
                )
        for name in ROOT_FILES:
            f = REPO / name
            if f.is_file():
                files.append(f)
        violations = _scan(files)
        self.assertEqual(
            violations,
            [],
            "Sibling-plugin references found outside the functional surface "
            "(docs/scripts/root must also be self-contained; cross-promo lines "
            "must carry a repo link or install command):\n" + "\n".join(violations),
        )


if __name__ == "__main__":
    unittest.main()
