"""A Veo clip is rendered on Vertex AI, and a retired Veo id must fall forward to Vertex's replacement.

The registry's replacement for veo-3.1-generate-preview depends on the service: gemini-omni-1.1-flash on the Gemini API,
veo-3.1-generate-001 on Vertex AI. SocialForge's Veo rung only runs on Vertex AI (a GEMINI_API_KEY alone cannot make a Veo
clip), so generate_video names that backend when it negotiates the model, instead of leaving the registry to guess.
Runs against the shipped registry; no network, nothing written.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import generate_video  # noqa: E402

RETIRED = "veo-3.1-generate-preview"


class TestVeoBackend(unittest.TestCase):

    def test_veo_is_a_vertex_clip(self):
        self.assertEqual(generate_video.VEO_BACKEND, "vertex")

    def test_a_retired_veo_id_falls_forward_to_the_vertex_replacement(self):
        got = generate_video._negotiate_video_model(RETIRED, "latest-video-google", backend=generate_video.VEO_BACKEND)
        self.assertEqual(got, "veo-3.1-generate-001")

    def test_the_replacement_follows_the_backend_that_is_named(self):
        got = generate_video._negotiate_video_model(RETIRED, "latest-video-google", backend="gemini-api")
        self.assertEqual(got, "gemini-omni-1.1-flash")

    def test_the_veo_call_site_names_the_backend(self):
        src = (SCRIPTS / "generate_video.py").read_text(encoding="utf-8-sig")
        call = re.search(r"chosen_veo = \(?_negotiate_video_model\([^\n]*", src)
        self.assertIsNotNone(call)
        self.assertIn("backend=VEO_BACKEND", src[call.start():call.start() + 250])

    def test_the_default_alias_still_resolves_for_vertex(self):
        self.assertEqual(generate_video._negotiate_video_model(None, "latest-video-google", backend="vertex"),
                         generate_video.DEFAULT_VEO_MODEL)


if __name__ == "__main__":
    unittest.main()
