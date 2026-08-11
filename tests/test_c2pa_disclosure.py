"""EU AI Act Article 50 disclosure must be in the manifest, and on by default.

Article 50 became enforceable on 2 August 2026. It requires that generative AI
output be marked in a machine-readable format detectable as artificially
generated. Article 50(4) then provides an editorial-control exemption for
AI-assisted content a human reviews and takes responsibility for before
publication.

That second half is the part specific to this pipeline: SocialForge already
gates every asset behind a human approval queue, so it can attest the review —
but only if the approval is actually carried into the signed manifest. An
approval that lives only in a JSON status file is not evidence attached to the
asset.

These tests exercise the manifest builder directly. They do not sign anything,
so they need no certificate and no c2pa-python install.

Stdlib only.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import c2pa_sign  # noqa: E402

CREATED = "2026-08-11T10:00:00Z"


def build(**kw):
    args = dict(
        brand="Acme", generator="WaveSpeed Kling v3.0 Pro",
        ai_claim="ai-generated-content", created=CREATED,
        prompt=None, platform=None, asset_format=".jpg",
    )
    args.update(kw)
    return c2pa_sign.build_manifest(**args)


def assertion(manifest, label):
    for a in manifest["assertions"]:
        if a["label"] == label:
            return a["data"]
    return None


class TestDisclosureIsDefaultOn(unittest.TestCase):
    def test_ai_disclosure_present_without_being_asked(self):
        """The obligation is live. Opting in is the wrong default."""
        data = assertion(build(), "c2pa.ai-disclosure")
        self.assertIsNotNone(data, "no c2pa.ai-disclosure assertion in a default manifest")
        self.assertIs(data["disclosure"], True)

    def test_names_the_regulation_and_states_it_plainly(self):
        data = assertion(build(), "c2pa.ai-disclosure")
        self.assertEqual(data["regulation"], "EU AI Act Article 50")
        self.assertIn("generative AI", data["statement"])

    def test_can_be_switched_off_explicitly(self):
        self.assertIsNone(assertion(build(ai_disclosure=False), "c2pa.ai-disclosure"))

    def test_digital_source_type_is_a_real_c2pa_value(self):
        data = assertion(build(), "c2pa.ai-disclosure")
        self.assertIn(data["digital_source_type"], set(c2pa_sign.AI_CLAIM_TO_C2PA_TYPE.values()))


class TestHumanOversight(unittest.TestCase):
    def test_unreviewed_asset_records_none_rather_than_claiming_review(self):
        """Silence must not read as oversight. An unreviewed asset says so."""
        data = assertion(build(), "c2pa.ai-disclosure")
        self.assertEqual(data["human_oversight"], "none-recorded")
        self.assertNotIn("reviewed_by", data)

    def test_reviewer_is_carried_into_the_disclosure(self):
        data = assertion(build(reviewed_by="Neel Banerjee"), "c2pa.ai-disclosure")
        self.assertEqual(data["human_oversight"], "reviewed-before-publication")
        self.assertEqual(data["reviewed_by"], "Neel Banerjee")

    def test_review_is_also_a_c2pa_action_not_just_metadata(self):
        actions = assertion(build(reviewed_by="Neel Banerjee"), "c2pa.actions.v2")["actions"]
        edited = [a for a in actions if a["action"] == "c2pa.edited"]
        self.assertEqual(len(edited), 1, "human approval did not appear in the action chain")
        self.assertIn("Neel Banerjee", edited[0]["parameters"]["description"])

    def test_reviewer_appears_as_editor_in_schema_org(self):
        cw = assertion(build(reviewed_by="Neel Banerjee"), "stds.schema-org.CreativeWork")
        self.assertEqual(cw["editor"], {"@type": "Person", "name": "Neel Banerjee"})

    def test_review_timestamp_defaults_to_creation_when_not_given(self):
        data = assertion(build(reviewed_by="Neel"), "c2pa.ai-disclosure")
        self.assertEqual(data["reviewed_at"], CREATED)

    def test_explicit_review_timestamp_is_kept(self):
        later = "2026-08-11T14:30:00Z"
        data = assertion(build(reviewed_by="Neel", reviewed_at=later), "c2pa.ai-disclosure")
        self.assertEqual(data["reviewed_at"], later)


class TestModelProvenance(unittest.TestCase):
    def test_model_id_recorded_when_supplied(self):
        """'Vertex AI' is a service, not provenance — a reviewer asking what made
        this needs the model."""
        data = assertion(build(model_id="kwaivgi/kling-v3.0-pro"), "c2pa.ai-disclosure")
        self.assertEqual(data["model"], "kwaivgi/kling-v3.0-pro")

    def test_no_model_key_invented_when_absent(self):
        self.assertNotIn("model", assertion(build(), "c2pa.ai-disclosure"))

    def test_generator_always_present(self):
        self.assertEqual(assertion(build(), "c2pa.ai-disclosure")["generator"],
                         "WaveSpeed Kling v3.0 Pro")


class TestManifestStaysValid(unittest.TestCase):
    def test_core_assertions_survive_the_addition(self):
        labels = [a["label"] for a in build(reviewed_by="Neel")["assertions"]]
        for required in ("c2pa.actions.v2", "stds.schema-org.CreativeWork",
                         "c2pa.ai-disclosure"):
            self.assertIn(required, labels)

    def test_claim_generator_reports_the_real_plugin_version(self):
        info = build()["claim_generator_info"][0]
        self.assertEqual(info["name"], "SocialForge")
        self.assertRegex(info["version"], r"^\d+\.\d+\.\d+$",
                         "claim generator version is not the shipped semver")

    def test_cli_exposes_the_new_flags(self):
        """Documented behaviour has to be reachable from the command line."""
        src = (SCRIPTS / "c2pa_sign.py").read_text(encoding="utf-8")
        for flag in ("--no-ai-disclosure", "--reviewed-by", "--reviewed-at", "--model-id"):
            self.assertIn(flag, src, f"{flag} is not wired into argparse")


if __name__ == "__main__":
    unittest.main()
