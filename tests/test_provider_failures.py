"""The provider layer may fail, but it may never fail silently.

Every fallback rung used to collapse its reason into a bare `return None`:
a missing API key, a retired model id, an HTTP 401, and a content-policy
rejection all looked identical, and the terminal error was one truncated
string. These tests pin the structured-failure contract: every abandoned
attempt is recorded with provider/stage/reason/detail, every recorded reason
has a next step, and the chain's terminal payload names everything tried.

All tests run OFFLINE: credentials are cleared so every rung stops at its
credentials/model-resolution stage before any network call.
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

from provider_failures import NEXT_STEPS, record, failure_payload  # noqa: E402

# Env vars that could make a rung go to the network — cleared in every test.
CRED_ENV = {
    "GEMINI_API_KEY": "", "GOOGLE_CLOUD_PROJECT": "", "GOOGLE_APPLICATION_CREDENTIALS": "",
    "WAVESPEED_API_KEY": "", "HF_API_KEY": "", "HF_API_SECRET": "",
}


def _isolated_creds():
    """Point credential_manager at an empty temp store so machine-local
    credentials can never leak into a test."""
    import credential_manager as cm
    tmp = Path(tempfile.mkdtemp())
    cm.CRED_DIR = tmp
    cm.CRED_FILE = tmp / "credentials.json"
    cm.GCP_KEY_FILE = tmp / "gcp-credentials.json"


class TestFailureRecordContract(unittest.TestCase):
    def test_record_appends_and_is_none_safe(self):
        attempts = []
        record(attempts, "prov", "credentials", "no-credentials", "detail")
        self.assertEqual(attempts[0]["provider"], "prov")
        self.assertEqual(attempts[0]["reason"], "no-credentials")
        record(None, "prov", "request", "request-error", "x")  # must not raise

    def test_failure_payload_names_everything_tried(self):
        attempts = []
        record(attempts, "a", "credentials", "no-credentials", "")
        record(attempts, "b", "content-policy", "content-rejected", "")
        payload = failure_payload(attempts, context="probe")
        self.assertEqual(payload["status"], "FAILED")
        self.assertTrue(payload["action_required"])
        self.assertEqual(payload["providers_tried"], ["a", "b"])
        self.assertIn("a: no-credentials (credentials)", payload["error"])
        self.assertIn("b: content-rejected (content-policy)", payload["error"])
        # Two distinct reasons -> two distinct next steps
        self.assertEqual(len(payload["next_steps"]), 2)

    def test_every_recorded_reason_has_a_next_step(self):
        """Scan the generation scripts for record(...) calls: every reason
        they can emit must map to an actionable next step."""
        reason_re = re.compile(r'record\(attempts,\s*"[^"]+",\s*"[^"]+",\s*"([a-z-]+)"')
        used = set()
        for script in ("generate_image.py", "generate_video.py"):
            used |= set(reason_re.findall((SCRIPTS / script).read_text(encoding="utf-8")))
        self.assertTrue(used, "no record() calls found — the contract was removed?")
        missing = used - set(NEXT_STEPS)
        self.assertFalse(missing, f"reasons with no next step: {missing}")


class TestImageRungsRecordFailures(unittest.TestCase):
    def test_wavespeed_rung_records_missing_credentials(self):
        _isolated_creds()
        with patch.dict(os.environ, CRED_ENV):
            from generate_image import generate_image_wavespeed
            attempts = []
            out = generate_image_wavespeed("p", "out.png", attempts=attempts)
        self.assertIsNone(out)
        self.assertEqual(attempts[0]["provider"], "wavespeed")
        self.assertEqual(attempts[0]["reason"], "no-credentials")

    def test_higgsfield_rung_records_missing_credentials(self):
        _isolated_creds()
        with patch.dict(os.environ, CRED_ENV):
            from generate_image import generate_image_higgsfield
            attempts = []
            out = generate_image_higgsfield("p", "out.png", attempts=attempts)
        self.assertIsNone(out)
        self.assertEqual(attempts[0]["reason"], "no-credentials")

    def test_image_chain_reports_all_providers_when_everything_fails(self):
        """A missing Gemini credential must NOT abort the chain (a user with
        only a fallback key still generates), and the terminal payload names
        every rung tried."""
        _isolated_creds()
        with patch.dict(os.environ, CRED_ENV):
            from generate_image import generate_image
            result = generate_image("p", "out.png")
        self.assertEqual(result["status"], "FAILED")
        providers = result["providers_tried"]
        for prov in ("gemini", "wavespeed", "higgsfield"):
            self.assertIn(prov, providers,
                          f"{prov} missing from the failure report — a rung "
                          "failed without being recorded")
        self.assertTrue(result["next_steps"])


class TestVideoRungsRecordFailures(unittest.TestCase):
    def test_kling_checks_credentials_before_installing_anything(self):
        """Credentials come before dependencies: the rung must never
        pip-install an SDK the caller has no key for."""
        src = (SCRIPTS / "generate_video.py").read_text(encoding="utf-8")
        body = src.split("def generate_video_kling", 1)[1].split("def ", 1)[0]
        self.assertLess(body.index("no-credentials"), body.index("ensure_package"))

    def test_video_chain_reports_all_three_rungs(self):
        _isolated_creds()
        with patch.dict(os.environ, CRED_ENV):
            from generate_video import generate_video_chain
            result = generate_video_chain("p", "out.mp4", None, 5)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(len(result["providers_tried"]), 3)
        reasons = {a["reason"] for a in result["attempts"]}
        self.assertIn("no-credentials", reasons)

    def test_preferred_provider_goes_first(self):
        _isolated_creds()
        with patch.dict(os.environ, CRED_ENV):
            from generate_video import generate_video_chain
            result = generate_video_chain("p", "out.mp4", None, 5, preferred="higgsfield")
        self.assertEqual(result["attempts"][0]["provider"], "higgsfield")

    def test_veo_prompt_is_not_a_config_field(self):
        """Regression pin for a live bug: the SDK rejects `prompt` inside
        GenerateVideosConfig (it is a direct generate_videos argument), so
        every Veo call failed validation before reaching the API."""
        src = (SCRIPTS / "generate_video.py").read_text(encoding="utf-8")
        m = re.search(r"GenerateVideosConfig\(([^)]*)\)", src, re.S)
        self.assertIsNotNone(m)
        self.assertNotIn("prompt", m.group(1),
                         "prompt crept back into GenerateVideosConfig — the "
                         "SDK rejects it there; pass it to generate_videos directly")
        self.assertIn("prompt=prompt", src)

    def test_routing_consults_stored_credentials_not_just_env(self):
        """route_video_provider used to read env vars only, telling fully
        configured /socialforge:setup users 'No video API configured'."""
        src = (SCRIPTS / "generate_video.py").read_text(encoding="utf-8")
        body = src.split("def _provider_availability", 1)[1].split("\ndef route_video_provider", 1)[0]
        for fn in ("get_wavespeed_key", "get_higgsfield_auth", "validate_vertex_ai"):
            self.assertIn(fn, body, f"availability no longer checks {fn}")

    def test_no_bare_return_none_in_fallback_rungs(self):
        """Every `return None` in a provider rung must be preceded by a
        record() call in the same statement group — no silent fall-throughs."""
        for script in ("generate_image.py", "generate_video.py"):
            src = (SCRIPTS / script).read_text(encoding="utf-8")
            for fn_name in ("generate_image_wavespeed", "generate_image_higgsfield",
                            "generate_video_kling", "generate_video_veo",
                            "generate_video_higgsfield"):
                if f"def {fn_name}" not in src:
                    continue
                body = src.split(f"def {fn_name}", 1)[1].split("\ndef ", 1)[0]
                # Between consecutive `return None`s there must be a record()
                chunks = body.split("return None")
                for i, chunk in enumerate(chunks[:-1]):
                    self.assertIn("record(", chunk,
                                  f"{script}:{fn_name}: `return None` #{i + 1} has no "
                                  "record() before it — a silent fall-through returned")


if __name__ == "__main__":
    unittest.main()
