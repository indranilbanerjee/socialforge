"""Adversarial execution pins for the state-writing scripts.

Each of these tests replays a probe that found a real defect during the
v1.19.0 adversarial sweep, executed against a throwaway workspace:

- compliance_check failed OPEN: unknown severity words downgraded to
  warnings, one bad regex crashed the whole gate, a typo'd brand passed as
  SKIPPED, and an empty forbidden-content entry matched everything.
- status_manager minted ghost posts from typo'd ids, accepted "FINAL " as a
  brand-new frozen status, and let calendar fields traverse out of the
  month tree via '../' in a platform key.
- index_assets minted duplicate asset ids on --refresh, so downstream
  lookups by id resolved to the wrong image.
- credential_manager destroyed every stored provider key when setup ran
  over a corrupt credentials.json.
- resolve_model handed retired model ids straight to SDKs when reached
  through an alias (direct id lookups fell forward correctly).
- build_gallery interpolated calendar strings into the review HTML raw.

All subprocesses run offline: provider env vars are cleared.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"

OFFLINE = {
    "GEMINI_API_KEY": "", "GOOGLE_CLOUD_PROJECT": "", "GOOGLE_APPLICATION_CREDENTIALS": "",
    "WAVESPEED_API_KEY": "", "HF_API_KEY": "", "HF_API_SECRET": "",
    "ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": "",
}


def run(script, *args, workspace=None, stdin=None, extra_env=None):
    """Run a scripts/ CLI against an isolated workspace; return (exit, stdout)."""
    env = dict(os.environ)
    env.update(OFFLINE)
    if workspace:
        env["CLAUDE_PLUGIN_DATA"] = str(workspace)
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True, text=True, env=env, input=stdin, timeout=120,
    )
    return proc.returncode, proc.stdout


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())
        (self.ws / "socialforge").mkdir()

    def brand_dir(self, brand="probe"):
        d = self.ws / "socialforge" / "brands" / brand
        d.mkdir(parents=True, exist_ok=True)
        return d

    def month_dir(self, brand="probe", month="2026-09"):
        d = self.ws / "socialforge" / "output" / brand / month
        d.mkdir(parents=True, exist_ok=True)
        return d


class TestComplianceGateFailsClosed(WorkspaceCase):
    RULES = {
        "banned_phrases": [
            {"phrase": "guaranteed returns", "severity": "high"},
            {"phrase": "unbalanced (regex", "match_type": "regex", "severity": "block"},
            {"no_phrase_key": True},
        ],
        "platform_specific_rules": {"linkedin": {"forbidden_content_types": ["", "ad"]}},
    }

    def setUp(self):
        super().setUp()
        (self.brand_dir() / "compliance-rules.json").write_text(
            json.dumps(self.RULES), encoding="utf-8")

    def test_unknown_severity_blocks_and_bad_rules_never_crash_the_gate(self):
        code, out = run("compliance_check.py", "--brand", "probe",
                        "--text", "Our advice: enjoy guaranteed returns today",
                        "--platform", "linkedin", workspace=self.ws)
        self.assertEqual(code, 1, "BLOCKED must exit 1 so shell callers cannot sail past")
        d = json.loads(out)
        self.assertEqual(d["status"], "BLOCKED")
        # One bad regex, one phrase-less rule, one empty forbidden entry:
        # all three become blocking rule_errors instead of a crash or a skip.
        self.assertEqual(d["rule_errors"], 3)
        banned = [v for v in d["violations"] if v["type"] == "banned_phrase"]
        self.assertEqual(len(banned), 1)
        self.assertIn("fail closed", banned[0]["note"])
        # Word-boundary matching: 'ad' must not fire on 'advice'.
        self.assertFalse([v for v in d["violations"] if v["type"] == "forbidden_content"])

    def test_typo_brand_fails_instead_of_skipping(self):
        code, out = run("compliance_check.py", "--brand", "probe-typo",
                        "--text", "anything", workspace=self.ws)
        self.assertEqual(code, 2)
        d = json.loads(out)
        self.assertEqual(d["status"], "FAILED")
        self.assertIn("probe", d["known_brands"])

    def test_brand_without_rules_still_skips_cleanly(self):
        self.brand_dir("bare")
        code, out = run("compliance_check.py", "--brand", "bare",
                        "--text", "anything", workspace=self.ws)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["status"], "SKIPPED")


class TestStatusLedger(WorkspaceCase):
    CALENDAR = {"posts": [
        {"post_id": "P01", "date": "2026-09-03",
         "platforms": [{"key": "../../../escaped"}], "tier": "HERO", "content_type": "static"},
        {"post_id": "P02", "date": "2026-09-10", "platforms": ["linkedin"],
         "tier": "HUB", "content_type": "static"},
    ]}

    def setUp(self):
        super().setUp()
        (self.month_dir() / "calendar-data.json").write_text(
            json.dumps(self.CALENDAR), encoding="utf-8")
        run("status_manager.py", "--action", "init-month", "--brand", "probe",
            "--month", "2026-09", workspace=self.ws)

    def test_ghost_post_ids_are_rejected(self):
        code, out = run("status_manager.py", "--action", "update-status",
                        "--brand", "probe", "--month", "2026-09",
                        "--post-id", "P99", "--status", "ASSET_MATCHING",
                        workspace=self.ws)
        self.assertEqual(code, 1)
        self.assertIn("Unknown post id", json.loads(out)["error"])

    def test_unknown_status_rejected_even_with_force(self):
        code, out = run("status_manager.py", "--action", "update-status",
                        "--brand", "probe", "--month", "2026-09",
                        "--post-id", "P02", "--status", "BOGUS_STATE", "--force",
                        workspace=self.ws)
        self.assertEqual(code, 1)
        self.assertIn("known_statuses", json.loads(out))

    def test_calendar_post_transitions_normally(self):
        code, out = run("status_manager.py", "--action", "update-status",
                        "--brand", "probe", "--month", "2026-09",
                        "--post-id", "P02", "--status", "ASSET_MATCHING",
                        workspace=self.ws)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["new_status"], "ASSET_MATCHING")

    def test_traversal_in_calendar_fields_is_sanitized(self):
        code, out = run("status_manager.py", "--action", "get-post-folder",
                        "--brand", "probe", "--month", "2026-09",
                        "--post-id", "P01", workspace=self.ws)
        self.assertEqual(code, 0)
        name = json.loads(out)["name"]
        self.assertNotIn("..", name)
        self.assertNotIn("/", name)
        self.assertNotIn("\\", name)


class TestAssetIndexIds(WorkspaceCase):
    def test_refresh_never_mints_duplicate_ids(self):
        src = self.ws / "assets"
        src.mkdir()
        for n in ("beta.png", "gamma.png", "delta.png"):
            (src / n).write_bytes(b"fake")
        code, _ = run("index_assets.py", "--brand", "probe", "--source", str(src),
                      workspace=self.ws)
        self.assertIn(code, (0, 3))  # 3 = honest "AI analysis did not run"
        (src / "alpha.png").write_bytes(b"fake")  # sorts before every existing file
        code, _ = run("index_assets.py", "--brand", "probe", "--source", str(src),
                      "--refresh", workspace=self.ws)
        self.assertIn(code, (0, 3))
        index = json.loads((self.ws / "socialforge" / "brands" / "probe" /
                            "asset-index.json").read_text(encoding="utf-8"))
        ids = [a["id"] for a in index["assets"]]
        self.assertEqual(len(ids), len(set(ids)),
                         f"duplicate asset ids after refresh: {ids}")

    def test_total_ai_failure_is_loud_not_a_quiet_success(self):
        src = self.ws / "assets"
        src.mkdir()
        (src / "one.png").write_bytes(b"fake")
        code, out = run("index_assets.py", "--brand", "probe", "--source", str(src),
                        workspace=self.ws)
        self.assertEqual(code, 3)
        d = json.loads(out)
        self.assertIn("ai_failure_reasons", d)
        self.assertTrue(d.get("action_required"))


class TestCredentialCorruptionProtection(WorkspaceCase):
    def test_setup_refuses_to_overwrite_a_corrupt_credentials_file(self):
        key = "probe-key-abcdefgh12345678901234"
        code, out = run("credential_manager.py", "setup-wavespeed",
                        workspace=self.ws, stdin=key + "\n")
        self.assertEqual(json.loads(out)["status"], "success")
        cred_file = self.ws / "socialforge" / "credentials.json"
        cred_file.write_text(cred_file.read_text(encoding="utf-8") + "}",
                             encoding="utf-8")
        code, out = run("credential_manager.py", "setup-wavespeed",
                        workspace=self.ws, stdin="other-key-abcdefgh12345678901234\n")
        d = json.loads(out)
        self.assertEqual(d["status"], "FAILED")
        self.assertIn("refusing to overwrite", d["error"])
        # The original key must still be on disk, recoverable.
        self.assertIn(key, cred_file.read_text(encoding="utf-8"))


class TestResolverAliasStatusLadder(unittest.TestCase):
    def test_alias_to_retired_model_falls_forward(self):
        reg = {"last_updated": "2026-08-01",
               "aliases": {"latest-test-alias": "dead-model-1"},
               "models": [
                   {"id": "dead-model-1", "status": "retired",
                    "replacement_id": "live-model-2", "modality": "text"},
                   {"id": "live-model-2", "status": "current", "modality": "text"},
               ]}
        with tempfile.TemporaryDirectory() as tmp:
            reg_path = Path(tmp) / "registry.json"
            reg_path.write_text(json.dumps(reg), encoding="utf-8")
            env = dict(os.environ)
            env["MODEL_REGISTRY"] = str(reg_path)
            proc = subprocess.run(
                [sys.executable, "-c",
                 "import sys; sys.path.insert(0, r'" + str(SCRIPTS) + "'); "
                 "from resolve_model import resolve; "
                 "print(resolve('latest-test-alias'))"],
                capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(proc.stdout.strip(), "live-model-2",
                         "an alias to a retired model must fall forward like a "
                         "direct id lookup does — never hand a dead id to an SDK")


class TestGalleryEscapes(WorkspaceCase):
    def test_calendar_strings_never_reach_the_review_html_raw(self):
        month = self.month_dir()
        calendar = {"posts": [{
            "post_id": "P01", "date": "2026-09-03", "platforms": ["linkedin"],
            "tier": "HERO", "content_type": "static",
            "title": "</div><script>alert(1)</script>",
        }]}
        (month / "calendar-data.json").write_text(json.dumps(calendar), encoding="utf-8")
        run("status_manager.py", "--action", "init-month", "--brand", "probe",
            "--month", "2026-09", workspace=self.ws)
        code, out = run("build_gallery.py", "--brand", "probe", "--month", "2026-09",
                        workspace=self.ws)
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertEqual(d["posts_without_media"], ["P01"],
                         "posts with no media must be named, not hidden in a count")
        html = (month / "review" / "gallery.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)


class TestVideoChainEndToEnd(WorkspaceCase):
    def test_failed_video_is_failed_at_the_top_level_with_attempts(self):
        month = self.month_dir()
        (month / "calendar-data.json").write_text(json.dumps({"posts": [
            {"post_id": "P02", "date": "2026-09-10", "platforms": ["linkedin"],
             "tier": "HUB", "content_type": "static"}]}), encoding="utf-8")
        out_dir = self.ws / "video-out"
        code, out = run("generate_video.py", "--brand", "probe", "--month", "2026-09",
                        "--post-id", "P02", "--output-dir", str(out_dir),
                        "--generate-video", workspace=self.ws)
        self.assertEqual(code, 4, "requested-but-failed video must exit 4")
        d = json.loads(out)
        self.assertEqual(d["status"], "FAILED",
                         "top-level status must reflect the failed video, not say success")
        self.assertEqual(d["routing"]["provider"], "none")
        self.assertIn("credentials_found", d["routing"])
        # Script and storyboard artifacts still exist — express honesty, not loss
        self.assertTrue((out_dir / "post-P02-script.json").exists())


class TestRefreshModelsHonesty(unittest.TestCase):
    def test_bump_refused_when_nothing_was_checked(self):
        reg_src = (SCRIPTS / "model_registry.json").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            reg_path = Path(tmp) / "registry.json"
            reg_path.write_text(reg_src, encoding="utf-8")
            env = dict(os.environ)
            env.update(OFFLINE)
            env["MODEL_REGISTRY"] = str(reg_path)
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "refresh_models.py"),
                 "--json", "--bump-timestamp"],
                capture_output=True, text=True, env=env, timeout=60)
            d = json.loads(proc.stdout)
            self.assertEqual(proc.returncode, 2)
            self.assertEqual(d["vendors_checked"], 0)
            self.assertIn("timestamp_bump_refused", d)
            self.assertNotIn("timestamp_bumped", d)
            # Every vendor names its reason; none hide behind a conflated string
            for vendor in ("anthropic", "openai", "google"):
                self.assertIn("reason", d[vendor])
                self.assertIn("no-key", d[vendor]["reason"])
            # The registry file itself must be untouched
            self.assertEqual(reg_path.read_text(encoding="utf-8"), reg_src)


if __name__ == "__main__":
    unittest.main()
