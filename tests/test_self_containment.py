"""Self-containment guard: the functional surface (skills/, agents/, commands/)
must never reference a sibling plugin for any capability.

Rule (2026-07-12): each plugin in the suite is fully standalone. Cross-promotion
in README/AGENTS.md is fine; capability delegation in skills is not.
This test keeps it from regressing.
"""
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SURFACE_DIRS = ("skills", "agents", "commands")
SIBLING_PATTERN = re.compile(
    r"digital-marketing-pro|digital marketing pro|contentforge|content-forge", re.IGNORECASE
)
# Deliberate exceptions, as "relative/path.md:token" (none today).
ALLOWLIST: set = set()


class TestSelfContainment(unittest.TestCase):
    def test_no_sibling_plugin_references_in_functional_surface(self):
        violations = []
        for d in SURFACE_DIRS:
            root = REPO / d
            if not root.is_dir():
                continue
            for f in sorted(root.rglob("*.md")):
                rel = f.relative_to(REPO).as_posix()
                for i, line in enumerate(
                    f.read_text(encoding="utf-8", errors="replace").splitlines(), 1
                ):
                    m = SIBLING_PATTERN.search(line)
                    if m and f"{rel}:{m.group(0).lower()}" not in ALLOWLIST:
                        violations.append(f"{rel}:{i}: {line.strip()[:100]}")
        self.assertEqual(
            violations,
            [],
            "Sibling-plugin references found in the functional surface "
            "(skills must be self-contained):\n"
            + "\n".join(violations),
        )


if __name__ == "__main__":
    unittest.main()
