"""The delivery manifest's AI-assistance note: honest, fail-safe, right-sized.

SF's mirror of the suite's disclosure layer is deliberately scoped to the
DELIVERY MANIFEST, not the captions: per-post AI disclosure belongs to each
platform's native label toggle, and the long-form structural scan does not
apply to caption-length copy (no document structure to measure). These tests
pin the surface classifier, the uncertain⇒disclose fail-safe, the manifest
wiring, and the vendor-neutral default note.
"""
from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location(
    "sf_detect_surface", REPO / "scripts" / "detect_surface.py")
ds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ds)

BRAND_MANAGER = (REPO / "skills" / "brand-manager" / "SKILL.md").read_text(encoding="utf-8")
ASSEMBLE = (REPO / "skills" / "assemble-document" / "SKILL.md").read_text(encoding="utf-8")


class TestSurfaceClassifier(unittest.TestCase):
    def test_directions(self):
        self.assertEqual(ds.classify_surface({"CLAUDECODE": "1"})["surface"], "claude")
        self.assertEqual(ds.classify_surface({"CODEX_SESSION_ID": "x"})["surface"], "non-claude")
        self.assertEqual(ds.classify_surface({})["surface"], "uncertain")

    def test_decision_matrix_with_failsafe(self):
        cases = {("always", "non-claude"): True, ("off", "claude"): False,
                 ("claude-surfaces", "claude"): True,
                 ("claude-surfaces", "non-claude"): False,
                 ("claude-surfaces", "uncertain"): True}  # the fail-safe pin
        for (mode, surface), expected in cases.items():
            with self.subTest(mode=mode, surface=surface):
                self.assertEqual(ds.disclosure_applies(mode, surface), expected)


class TestManifestWiring(unittest.TestCase):
    def test_assemble_document_applies_and_records(self):
        self.assertIn("detect_surface.py", ASSEMBLE)
        self.assertIn("Never override the script's answer", ASSEMBLE)
        self.assertIn("a recorded choice, not an omission", ASSEMBLE)

    def test_default_note_is_vendor_neutral_and_claims_only_real_review(self):
        m = re.search(r'"ai_assistance_note": "([^"]+)"', ASSEMBLE)
        self.assertIsNotNone(m, "default note string missing from assemble-document")
        note = m.group(1)
        vendor_re = re.compile(r"\b(claude|anthropic|gpt|openai|gemini|google|copilot|codex)\b", re.I)
        self.assertIsNone(vendor_re.search(note), f"vendor name in default note: {note}")
        self.assertIn("human review", note)

    def test_platform_native_labels_own_per_post_disclosure(self):
        self.assertIn("platform-native AI-content labels", ASSEMBLE)
        self.assertIn("platform's native disclosure toggle", BRAND_MANAGER)

    def test_brand_manager_documents_the_modes(self):
        for token in ('"claude-surfaces"', "`always`", "`off`", "ai_disclosure"):
            self.assertIn(token, BRAND_MANAGER)

    def test_c2pa_stays_independent_of_the_text_note(self):
        self.assertIn("independently of this setting", BRAND_MANAGER)


if __name__ == "__main__":
    unittest.main()
