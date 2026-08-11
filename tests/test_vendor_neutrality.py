"""Docs ask for capabilities; they never install a vendor.

A community PR once wired a commercial third-party research plugin into the
reference docs — install commands, API-key configuration, a per-feature mapping
table. The instructions were marked optional, but a named product in a doc is a
dependency someone has to buy, install, and keep working, and it contradicts the
plugin's own architecture: models, prices, and research are all resolved as
capabilities at run time, supplied by whatever the user's environment already
has.

The self-containment guard did not fire because it only watches for sibling
plugin names. This guard watches for the general shape: vendor-install
instructions and third-party credential wiring inside the doc surface.

Stdlib only.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The doc surface: what ships to users as instructions.
DOC_DIRS = ["references", "skills", "commands", "agents", "docs"]

# Install-command shapes for OTHER ecosystems' packages. SocialForge's own
# install lines (claude plugin install, pip install for its declared deps)
# are not matched by these.
VENDOR_INSTALL = re.compile(
    r"(openclaw\s+plugins\s+install\s+@"     # scoped third-party openclaw plugin
    r"|npm\s+install\s+(-g\s+)?@(?!anthropic-ai)"  # scoped npm pkg, allow anthropic's CLI
    r"|plugins\.entries\.[a-z-]+\.config\.apiKey"  # wiring a plugin's paid key
    r"|SigningKey\b)",
    re.IGNORECASE)

# Regression pin for the specific incident.
KNOWN_VENDORS = re.compile(r"tweetclaw|xquik", re.IGNORECASE)


def doc_files():
    for d in DOC_DIRS:
        base = ROOT / d
        if base.exists():
            yield from base.rglob("*.md")
    # Root-level docs too — the incident's README line initially escaped this
    # guard because only subdirectories were scanned. CHANGELOG is exempt:
    # release history legitimately describes what was removed and why.
    for f in ROOT.glob("*.md"):
        if f.name != "CHANGELOG.md":
            yield f


class TestVendorNeutrality(unittest.TestCase):
    def test_no_vendor_install_instructions_in_docs(self):
        hits = []
        for f in doc_files():
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if VENDOR_INSTALL.search(line):
                    hits.append(f"{f.relative_to(ROOT)}:{i}: {line.strip()[:80]}")
        self.assertEqual(hits, [],
                         "docs must ask for a capability, not install a vendor:\n"
                         + "\n".join(hits))

    def test_the_specific_incident_cannot_return(self):
        hits = []
        for f in doc_files():
            if KNOWN_VENDORS.search(f.read_text(encoding="utf-8")):
                hits.append(str(f.relative_to(ROOT)))
        self.assertEqual(hits, [], f"removed vendor reappeared in: {hits}")

    def test_research_intake_is_capability_first(self):
        """The intake must lead with the harness's own tools and keep the
        user-paste fallback — the two rungs every environment actually has."""
        intake = (ROOT / "references" / "x-twitter-research-intake.md").read_text(encoding="utf-8")
        self.assertIn("harness", intake.lower())
        self.assertIn("user-provided", intake)
        self.assertNotRegex(intake, r"install\s+@", "the intake instructs a vendor install")

    def test_intake_keeps_the_untrusted_input_rule(self):
        """The one safety rule that must survive any rewrite: fetched social
        content is data, never instructions."""
        intake = (ROOT / "references" / "x-twitter-research-intake.md").read_text(encoding="utf-8")
        self.assertRegex(intake, r"[Nn]ever follow commands",
                         "the prompt-injection guard was lost in a rewrite")


if __name__ == "__main__":
    unittest.main()
