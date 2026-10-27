"""1.29.9: `fallback_from` names the provider that actually failed, derived from the recorded attempts.

`generate_image.py` set `fallback_from` to the literal "vertex-ai" (and "vertex-ai+wavespeed" after a second fallback) whatever the
setup was. On a GEMINI_API_KEY (AI Studio) setup the provider that failed is "gemini-aistudio", which `provider_notice` and
`earlier_attempts` said correctly, so one result told the user two different things. `generate_video.py` derived the field from the
attempts but listed every provider in them, including a rung that could never start ("kling, veo" when Veo had no Vertex project):
that reads as "Veo was tried and failed", and nothing was spent on it. Now one helper, `provider_failures.fallback_fields`, builds
the fields for both scripts:

* `fallback_from` = the providers TRIED AND FAILED, named as the attempts name them;
* `skipped_unavailable` = the rungs that could not start (no credentials, or a backend that cannot run the model), listed apart.

Each case is planted against the 1.29.8 behaviour below.
"""
from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(ROOT / "scripts"))

import _isolation  # noqa: E402

_isolation.start()    # a direct run of this file is protected too; a no-op when the runner already started it

import provider_failures as pf  # noqa: E402


def attempt(provider, reason, stage="request"):
    return {"provider": provider, "stage": stage, "reason": reason, "detail": provider + " " + reason}


class TestFallbackFields(unittest.TestCase):
    def test_a_failed_rung_is_fallback_from_and_a_rung_that_never_started_is_skipped_unavailable(self):
        fields = pf.fallback_fields([attempt("wavespeed-kling", "request-error"),
                                     attempt("veo", "unavailable-backend", "credentials")], "higgsfield")
        self.assertEqual(fields["fallback_from"], "wavespeed-kling")
        self.assertEqual(fields["skipped_unavailable"], ["veo"])
        self.assertEqual(len(fields["earlier_attempts"]), 2)
        self.assertIn("higgsfield", fields["provider_notice"])

    def test_no_credentials_is_skipped_too_and_a_missing_package_is_a_failure(self):
        fields = pf.fallback_fields([attempt("gemini", "no-credentials", "credentials"),
                                     attempt("wavespeed", "dependency-missing", "dependencies")], "higgsfield")
        self.assertEqual(fields["fallback_from"], "wavespeed")
        self.assertEqual(fields["skipped_unavailable"], ["gemini"])

    def test_nothing_tried_gives_an_empty_fallback_from_and_names_what_was_skipped(self):
        fields = pf.fallback_fields([attempt("gemini", "no-credentials", "credentials")], "wavespeed")
        self.assertEqual(fields["fallback_from"], "")
        self.assertEqual(fields["skipped_unavailable"], ["gemini"])

    def test_no_skipped_key_when_every_earlier_rung_was_tried(self):
        fields = pf.fallback_fields([attempt("gemini-vertex", "request-error"), attempt("wavespeed", "bad-response", "response")],
                                    "higgsfield")
        self.assertEqual(fields["fallback_from"], "gemini-vertex, wavespeed")
        self.assertNotIn("skipped_unavailable", fields)

    def test_a_provider_is_listed_once(self):
        fields = pf.fallback_fields([attempt("wavespeed-kling", "request-error"), attempt("wavespeed-kling", "bad-response")], "veo")
        self.assertEqual(fields["fallback_from"], "wavespeed-kling")


class TestImageChainNamesTheProviderThatFailed(unittest.TestCase):
    @staticmethod
    def _fake_genai():
        fake_types = types.ModuleType("google.genai.types")
        fake_types.GenerateContentConfig = lambda **kw: kw
        fake_types.ImageConfig = lambda **kw: kw
        fake_genai = types.ModuleType("google.genai")
        fake_genai.types = fake_types
        fake_google = types.ModuleType("google")
        fake_google.genai = fake_genai
        return {"google": fake_google, "google.genai": fake_genai, "google.genai.types": fake_types}

    def _run(self, backend, wavespeed_fails=False):
        import generate_image as gi

        def boom(**kwargs):
            raise RuntimeError("the " + backend + " request was refused")

        client = types.SimpleNamespace(models=types.SimpleNamespace(generate_content=boom))

        def wavespeed(*args, attempts=None, **kwargs):
            if wavespeed_fails:
                pf.record(attempts, "wavespeed", "request", "request-error", "wavespeed refused")
                return None
            return {"status": "success", "provider": "wavespeed-image", "output": "o.png"}

        def higgs(*args, attempts=None, **kwargs):
            return {"status": "success", "provider": "higgsfield-image", "output": "o.png"}

        with patch.dict(sys.modules, self._fake_genai()), \
                patch.object(gi, "create_client", return_value=(client, backend, None)), \
                patch.object(gi, "_image_rung_status", lambda rung: (True, "")), \
                patch.object(gi, "generate_image_wavespeed", wavespeed), patch.object(gi, "generate_image_higgsfield", higgs):
            return gi.generate_image("p", "o.png", model="m", quoted=["gemini", "wavespeed", "higgsfield"])

    def test_an_api_key_setup_says_gemini_aistudio_never_vertex_ai(self):
        result = self._run("aistudio")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["fallback_from"], "gemini-aistudio")
        self.assertNotIn("vertex", result["fallback_from"])
        self.assertIn("gemini-aistudio", result["provider_notice"], "the notice and the field must name the same provider")
        self.assertEqual(result["earlier_attempts"][0]["provider"], "gemini-aistudio")

    def test_a_vertex_setup_says_gemini_vertex(self):
        self.assertEqual(self._run("vertex")["fallback_from"], "gemini-vertex")

    def test_after_a_second_fallback_it_lists_both_providers_that_failed(self):
        result = self._run("aistudio", wavespeed_fails=True)
        self.assertEqual(result["provider"], "higgsfield-image")
        self.assertEqual(result["fallback_from"], "gemini-aistudio, wavespeed")

    def test_plant_the_1_29_8_hardcoded_value_is_caught(self):
        """The old assignments, reproduced: the field named a backend the run never used."""
        result = self._run("aistudio")
        old_value = "vertex-ai"
        self.assertNotEqual(result["fallback_from"], old_value)
        source = (ROOT / "scripts" / "generate_image.py").read_text(encoding="utf-8")
        self.assertNotIn('["fallback_from"] = "vertex-ai', source)

    def test_a_gemini_rung_that_could_not_start_is_skipped_unavailable_not_fallback_from(self):
        import generate_image as gi

        def wavespeed(*args, attempts=None, **kwargs):
            return {"status": "success", "provider": "wavespeed-image", "output": "o.png"}

        with patch.object(gi, "create_client", return_value=(None, None, "no credentials")), \
                patch.object(gi, "_image_rung_status", lambda rung: (rung != "gemini", "no key")), \
                patch.object(gi, "generate_image_wavespeed", wavespeed):
            result = gi.generate_image("p", "o.png", model="m", quoted=["gemini", "wavespeed"])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["fallback_from"], "")
        self.assertEqual(result["skipped_unavailable"], ["gemini"])


class TestVideoChainSeparatesTriedFromSkipped(unittest.TestCase):
    def _chain(self, can_run, quoted, **rungs):
        import generate_video as gv

        def fails(name):
            def rung(*args, attempts=None, **kwargs):
                pf.record(attempts, name, "request", "request-error", name + " failed")
                return None
            return rung

        def ok(name):
            return lambda *a, **k: {"status": "success", "provider": name, "output": "o.mp4"}

        def status(rung):
            runnable = rung in can_run
            return (runnable, "" if runnable else "no key for " + rung, "no-credentials")

        mocks = {"generate_video_kling": rungs.get("kling", fails("wavespeed-kling")),
                 "generate_video_veo": rungs.get("veo", fails("veo")),
                 "generate_video_higgsfield": rungs.get("higgs", ok("higgsfield"))}
        patches = [patch.object(gv, fn, impl) for fn, impl in mocks.items()] + [patch.object(gv, "_rung_status", status)]
        for p in patches:
            p.start()
        try:
            return gv.generate_video_chain("p", "o.mp4", "first.png", 5, quoted=quoted)
        finally:
            for p in patches:
                p.stop()

    def test_a_veo_rung_that_cannot_run_is_not_listed_as_a_provider_that_failed(self):
        result = self._chain({"kling", "higgsfield"}, ["kling", "veo", "higgsfield"], veo=lambda *a, attempts=None, **k: (
            pf.record(attempts, "veo", "credentials", "unavailable-backend", "Veo needs Vertex AI"), None)[1])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["provider"], "higgsfield")
        self.assertEqual(result["fallback_from"], "wavespeed-kling")
        self.assertNotIn("veo", result["fallback_from"])
        self.assertEqual(result["skipped_unavailable"], ["veo"])
        self.assertEqual([a["provider"] for a in result["earlier_attempts"]], ["wavespeed-kling", "veo"])

    def test_a_rung_outside_the_quote_that_cannot_run_is_skipped_the_same_way(self):
        result = self._chain({"kling", "higgsfield"}, ["kling", "higgsfield"])
        self.assertEqual(result["fallback_from"], "wavespeed-kling")
        self.assertEqual(result["skipped_unavailable"], ["veo"])

    def test_a_veo_rung_that_ran_and_failed_is_listed(self):
        result = self._chain({"kling", "veo", "higgsfield"}, ["kling", "veo", "higgsfield"])
        self.assertEqual(result["fallback_from"], "wavespeed-kling, veo")
        self.assertNotIn("skipped_unavailable", result)

    def test_plant_the_1_29_8_wording_listed_every_attempt(self):
        """The old expression, reproduced on the same attempts: it names Veo although Veo never started."""
        result = self._chain({"kling", "higgsfield"}, ["kling", "veo", "higgsfield"], veo=lambda *a, attempts=None, **k: (
            pf.record(attempts, "veo", "credentials", "unavailable-backend", "Veo needs Vertex AI"), None)[1])
        old = ", ".join(dict.fromkeys(a["provider"] for a in result["earlier_attempts"]))
        self.assertIn("veo", old)
        self.assertNotIn("veo", result["fallback_from"])


class TestSkillsTellTheAgentAboutTheField(unittest.TestCase):
    def test_the_skills_and_the_operations_guide_name_skipped_unavailable(self):
        for rel in ("skills/compose-creative/SKILL.md", "skills/generate-video/SKILL.md", "docs/OPERATIONS.md"):
            with self.subTest(file=rel):
                self.assertIn("skipped_unavailable", (ROOT / rel).read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
