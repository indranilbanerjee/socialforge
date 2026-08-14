"""Significance markers stay out of captions — and SocialForge stays scanner-free.

The suite's long-form plugins gained a deterministic AI-tell scan. SocialForge
deliberately did not: caption-length copy has no document structure to measure,
and per-1000-word metrics are noise at 280 characters. The judgment belongs at
the point the caption is written, so it lives as a writing rule on the
copy-adapter agent and the adapt-copy skill.

These tests pin that rule in place, pin the reasoning for the deliberate
absence (so a later reader does not mistake it for an oversight), and pin that
no evasion vocabulary ever arrives here either.
"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

COPY_ADAPTER = (REPO / "agents" / "copy-adapter.md").read_text(encoding="utf-8")
ADAPT_COPY = (REPO / "skills" / "adapt-copy" / "SKILL.md").read_text(encoding="utf-8")

MARKERS = ("here's the thing", "the thing is,", "here's the kicker",
           "here's where it gets interesting", "that's the part that got me",
           "let that sink in", "read that again")


class TestSignificanceMarkersAreForbidden(unittest.TestCase):
    def test_both_surfaces_name_the_markers(self):
        for name, text in (("copy-adapter.md", COPY_ADAPTER),
                           ("adapt-copy/SKILL.md", ADAPT_COPY)):
            low = text.lower()
            with self.subTest(surface=name):
                for m in MARKERS:
                    self.assertIn(m, low, f"{name} must name {m!r} as forbidden")

    def test_both_surfaces_forbid_rather_than_recommend(self):
        """The phrases appear only inside a prohibition. This is the guard that
        would catch a future edit turning the ban list into a style tip."""
        for name, text in (("copy-adapter.md", COPY_ADAPTER),
                           ("adapt-copy/SKILL.md", ADAPT_COPY)):
            with self.subTest(surface=name):
                for line in text.splitlines():
                    low = line.lower()
                    if any(m in low for m in MARKERS):
                        self.assertTrue(
                            any(w in low for w in ("never", "no significance", "not ",
                                                   "avoid", "don't", "do not", "forbidden")),
                            f"{name} names a marker on a line that does not forbid it: {line[:90]}")

    def test_the_fix_is_lead_with_the_specific(self):
        for text in (COPY_ADAPTER, ADAPT_COPY):
            self.assertIn("Approvals went from 14 days to 31", text,
                          "the concrete replacement example must survive edits")

    def test_soft_adverb_cap_is_stated(self):
        for text in (COPY_ADAPTER, ADAPT_COPY):
            low = text.lower()
            self.assertIn("honestly", low)
            self.assertIn("never two in", low.replace("never two in one sentence",
                                                      "never two in a sentence"))


class TestScannerAbsenceIsDeliberate(unittest.TestCase):
    """A missing capability should read as a decision, not a gap."""

    def test_both_surfaces_explain_why_there_is_no_scan(self):
        for name, text in (("copy-adapter.md", COPY_ADAPTER),
                           ("adapt-copy/SKILL.md", ADAPT_COPY)):
            with self.subTest(surface=name):
                low = text.lower()
                self.assertIn("no ai-tell scanner", low)
                self.assertIn("no document structure to measure", low)

    def test_no_scanner_script_was_added(self):
        for name in ("ai-tell-scan.py", "structural-tell-scan.py", "text-metrics.py"):
            self.assertFalse((REPO / "scripts" / name).exists(),
                             f"scripts/{name} exists — if a scanner is now wanted here, "
                             "update this test and the reasoning in both surfaces")


class TestNoEvasionSurface(unittest.TestCase):
    FORBIDDEN = ("zero-width", "homoglyph", "watermark removal", "remove the watermark",
                 "strip the watermark", "bypass the detector", "evade detection",
                 "pass as human", "discourse fracture")

    def test_caption_surfaces_carry_no_evasion_vocabulary(self):
        offenders = []
        for name, text in (("copy-adapter.md", COPY_ADAPTER),
                           ("adapt-copy/SKILL.md", ADAPT_COPY)):
            low = text.lower()
            offenders += [f"{name}: {t}" for t in self.FORBIDDEN if t in low]
        self.assertEqual(offenders, [], f"evasion surface introduced: {offenders}")


if __name__ == "__main__":
    unittest.main()
