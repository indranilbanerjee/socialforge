"""The skills only promise reference-image and keyframe inputs the scripts implement.

compose-creative and generate-video document what reference images, first
frames and last frames actually do. Those paragraphs were written from the
scripts, and they say plainly where a capability is missing:

- image references go to the primary image provider only; the WaveSpeed and
  HiggsField fallback rungs never receive them — and a result says so
  (`references_used` counts files actually sent, `references_missing` names
  paths that do not exist, `references_dropped` + `references_note` mark a
  fallback image) instead of echoing how many paths were passed
- a first frame is `generate_video.py --image`
- a last frame is `generate_video.py --last-image`: it reaches the video model
  on the kling rung only, and a clip from any other rung carries
  `last_frame_used: false` with a note

A prose claim about code goes stale silently the day the code changes. Each
test below pins one claim to the code that makes it true, so fixing the script
fails the test and the failure message says which paragraph to update. The
ALWAYS-ON recipes rely on one more behavior, that a repeat ingest of the same
file is a no-op and a cumulative export needs `--replace`, and pin it the same
way.

Stdlib only. Every test here was proven to fire by planting its failure.
"""
from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

COMPOSE = (REPO / "skills" / "compose-creative" / "SKILL.md").read_text(encoding="utf-8")
GEN_VIDEO = (REPO / "skills" / "generate-video" / "SKILL.md").read_text(encoding="utf-8")
RECIPES = (REPO / "docs" / "ALWAYS-ON-RECIPES.md").read_text(encoding="utf-8")


def _fake_google_genai():
    """In-memory stand-in for `google.genai` — enough for generate_image's primary
    rung to build its request and read back an image, and nothing else."""
    fake_types = types.ModuleType("google.genai.types")
    fake_types.Part = types.SimpleNamespace(
        from_bytes=lambda data, mime_type: ("part", mime_type))
    fake_types.GenerateContentConfig = lambda **kw: kw
    fake_types.ImageConfig = lambda **kw: kw
    fake_genai = types.ModuleType("google.genai")
    fake_genai.types = fake_types
    fake_google = types.ModuleType("google")
    fake_google.genai = fake_genai
    return {"google": fake_google, "google.genai": fake_genai,
            "google.genai.types": fake_types}


class TestImageReferences(unittest.TestCase):
    def test_references_flag_exists_and_the_skill_names_it(self):
        src = (SCRIPTS / "generate_image.py").read_text(encoding="utf-8")
        self.assertIn('"--references"', src)
        self.assertIn("--references", COMPOSE)
        edit_src = (SCRIPTS / "edit_image.py").read_text(encoding="utf-8")
        self.assertIn('"--references"', edit_src)

    def test_fallback_image_providers_receive_no_references(self):
        """The skill says a `fallback_from` result did not use the references. If a
        fallback rung starts sending them, update compose-creative and this test."""
        import generate_image as gi
        self.assertIn("fallback_from", COMPOSE)
        self.assertNotIn("reference", " ".join(
            inspect.signature(gi.generate_image_higgsfield).parameters))

        captured = {}

        class FakeClient:
            def __init__(self, api_key=None):
                pass

            def run(self, model_id, payload, **kwargs):
                captured["payload"] = dict(payload)
                return {"outputs": []}

        fake = types.ModuleType("wavespeed")
        fake.Client = FakeClient
        with patch.dict(sys.modules, {"wavespeed": fake}), \
                patch("credential_manager.get_wavespeed_key", return_value="test-key"), \
                patch.object(gi, "_resolve_execution_model", return_value="some-model"):
            gi.generate_image_wavespeed("a prompt", "out.png",
                                        reference_images=["ref-one.png", "ref-two.png"],
                                        aspect_ratio="1:1", attempts=[])
        self.assertIn("payload", captured, "premise: the WaveSpeed rung never reached its request")
        self.assertNotIn("ref-one.png", json.dumps(captured["payload"]),
                         "the WaveSpeed rung now sends references — update the "
                         "'Reference images and keyframes' table in compose-creative")
        self.assertEqual(set(captured["payload"]), {"prompt", "aspect_ratio"})

    # -- the primary rung: what was actually read and sent --------------------

    def _primary_rung(self, tmp, reference_images):
        """Run generate_image through its primary rung against a fake SDK; return
        (result, the contents list that would have been sent)."""
        import generate_image as gi
        sent = {}

        class Part:
            text = None
            inline_data = types.SimpleNamespace(data=b"fake-image-bytes")

            def as_image(self):
                raise AttributeError("force the raw-bytes branch")

        class Models:
            def generate_content(self, model, contents, config):
                sent["contents"] = contents
                return types.SimpleNamespace(parts=[Part()])

        client = types.SimpleNamespace(models=Models())
        with patch.dict(sys.modules, _fake_google_genai()), \
                patch.object(gi, "create_client", return_value=(client, "test", None)):
            result = gi.generate_image("a prompt", str(Path(tmp) / "out.png"),
                                       reference_images=reference_images, model="m")
        return result, sent.get("contents")

    def test_references_used_counts_files_actually_sent_and_missing_paths_are_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            real_png = Path(tmp) / "a.png"
            real_jpg = Path(tmp) / "b.jpg"
            real_png.write_bytes(b"png")
            real_jpg.write_bytes(b"jpg")
            missing = str(Path(tmp) / "never-existed.png")
            result, contents = self._primary_rung(tmp, [str(real_png), missing, str(real_jpg)])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["references_used"], 2,
                         "references_used must be files read and sent, not paths passed (3)")
        self.assertEqual(result["references_missing"], [missing],
                         "a reference path that does not exist must be named, not skipped silently")
        self.assertEqual(len(contents), 3, "two reference parts + the prompt")
        self.assertEqual([c[1] for c in contents[:2]], ["image/png", "image/jpeg"])

    def test_no_missing_key_when_every_reference_exists_or_none_were_passed(self):
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / "a.png"
            real.write_bytes(b"png")
            result, _ = self._primary_rung(tmp, [str(real)])
            self.assertEqual(result["references_used"], 1)
            self.assertNotIn("references_missing", result)
            self.assertNotIn("references_over_limit", result)
            bare, _ = self._primary_rung(tmp, None)
            self.assertEqual(bare["references_used"], 0)
            self.assertNotIn("references_missing", bare)

    def test_references_past_the_limit_are_counted_not_vanished(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for i in range(16):
                p = Path(tmp) / f"ref{i}.png"
                p.write_bytes(b"png")
                paths.append(str(p))
            result, contents = self._primary_rung(tmp, paths)
        self.assertEqual(result["references_used"], 14)
        self.assertEqual(result["references_over_limit"], 2,
                         "the two references past the 14-file limit were dropped without a word")
        self.assertEqual(len(contents), 15)

    # -- the fallback rungs: no references reach the provider -----------------

    def test_a_fallback_rung_result_says_the_references_were_dropped(self):
        import generate_image as gi
        refs = ["a.png", "b.png", "c.png"]

        def ok():
            return {"status": "success", "provider": "fallback", "output": "o.png"}

        no_gemini = (None, None, "no credentials")
        with patch.object(gi, "create_client", return_value=no_gemini):
            with patch.object(gi, "generate_image_wavespeed", side_effect=lambda *a, **k: ok()):
                via_wavespeed = gi.generate_image("p", "o.png", reference_images=refs, model="m")
            with patch.object(gi, "generate_image_wavespeed", return_value=None), \
                    patch.object(gi, "generate_image_higgsfield", side_effect=lambda *a, **k: ok()):
                via_higgsfield = gi.generate_image("p", "o.png", reference_images=refs, model="m")
            with patch.object(gi, "generate_image_wavespeed", side_effect=lambda *a, **k: ok()):
                no_refs = gi.generate_image("p", "o.png", reference_images=None, model="m")
        for name, result in (("wavespeed", via_wavespeed), ("higgsfield", via_higgsfield)):
            with self.subTest(rung=name):
                self.assertEqual(result["references_used"], 0)
                self.assertEqual(result["references_dropped"], 3)
                self.assertIn("prompt only", result["references_note"])
                self.assertIn("not a style-referenced image", result["references_note"])
                self.assertIn("fallback_from", result)
        self.assertNotIn("references_dropped", no_refs,
                         "no references were supplied, so nothing was dropped")
        self.assertNotIn("references_note", no_refs)

    def test_the_skill_names_the_result_fields_and_no_longer_says_skipped_silently(self):
        for field in ("references_used", "references_missing", "references_over_limit",
                      "references_dropped", "references_note"):
            self.assertIn(field, COMPOSE, f"compose-creative does not mention `{field}`")
        self.assertNotIn("skipped without an error", COMPOSE,
                         "the skill still describes the old silent skip")
        self.assertNotIn("echoes how many paths were passed", COMPOSE)


class TestVideoFrames(unittest.TestCase):
    def test_first_frame_is_the_image_flag(self):
        src = (SCRIPTS / "generate_video.py").read_text(encoding="utf-8")
        self.assertIn('"--image"', src)
        self.assertIn("--image <path>", GEN_VIDEO)

    def test_the_last_frame_flag_exists_and_the_skills_name_it(self):
        src = (SCRIPTS / "generate_video.py").read_text(encoding="utf-8")
        cli = src.split("def main()", 1)[1]
        self.assertIn('"--last-image"', cli)
        self.assertIn("--last-image <path>", GEN_VIDEO)
        self.assertIn("--last-image", COMPOSE)

    def test_the_chain_takes_a_last_frame_and_forwards_it_to_the_kling_rung(self):
        import generate_video as gv
        self.assertIn("last_image_path", inspect.signature(gv.generate_video_chain).parameters)
        kling_result = {"status": "success", "provider": "wavespeed-kling-v3",
                        "output": "o.mp4", "last_frame_used": True}
        with patch.object(gv, "generate_video_kling", return_value=dict(kling_result)) as kling:
            result = gv.generate_video_chain("p", "o.mp4", "first.png", 5,
                                             last_image_path="last.png")
        self.assertEqual(kling.call_args.args[2], "first.png")
        self.assertEqual(kling.call_args.args[3], "last.png",
                         "the chain did not hand the approved last frame to the kling rung")
        self.assertIs(result["last_frame_used"], True)
        self.assertNotIn("last_frame_note", result)

        with patch.object(gv, "generate_video_kling",
                          return_value={"status": "success", "provider": "wavespeed-kling-v3",
                                        "output": "o.mp4"}) as kling:
            bare = gv.generate_video_chain("p", "o.mp4", "first.png", 5)
        self.assertIsNone(kling.call_args.args[3])
        self.assertNotIn("last_frame_used", bare,
                         "no last frame was supplied, so the result has nothing to report about one")

    def test_the_kling_rung_really_sends_the_end_image(self):
        import generate_video as gv
        seen = {}

        class FakeClient:
            def __init__(self, api_key=None):
                pass

            def upload(self, path):
                return "uploaded:" + Path(path).name

            def run(self, model, payload, **kwargs):
                seen["payload"] = dict(payload)
                return {"outputs": ["https://example.invalid/v.mp4"]}

        fake = types.ModuleType("wavespeed")
        fake.Client = FakeClient

        def fake_retrieve(url, dest):
            Path(dest).write_bytes(b"mp4")

        with tempfile.TemporaryDirectory() as tmp:
            first, last = Path(tmp) / "first.png", Path(tmp) / "last.png"
            first.write_bytes(b"1")
            last.write_bytes(b"2")
            out = str(Path(tmp) / "o.mp4")

            def run(last_frame):
                with patch.dict(sys.modules, {"wavespeed": fake}), \
                        patch.dict(os.environ, {}), \
                        patch("credential_manager.get_wavespeed_key", return_value="k"), \
                        patch.object(gv.urllib.request, "urlretrieve", fake_retrieve):
                    return gv.generate_video_kling("p", out, str(first), last_frame,
                                                   duration=5, model="some-model", attempts=[])

            with_last = run(str(last))
            with_last_payload = dict(seen["payload"])
            without = run(None)
        self.assertEqual(with_last_payload["end_image"], "uploaded:last.png")
        self.assertIs(with_last["last_frame_used"], True)
        self.assertNotIn("end_image", seen["payload"])
        self.assertNotIn("last_frame_used", without)

    def test_a_missing_last_frame_is_recorded_as_bad_input_not_ignored(self):
        import generate_video as gv
        attempts = []
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.png"
            first.write_bytes(b"1")
            missing = str(Path(tmp) / "no-such-last-frame.png")
            result = gv.generate_video_kling("p", str(Path(tmp) / "o.mp4"), str(first), missing,
                                             attempts=attempts)
        self.assertIsNone(result)
        self.assertEqual([a["reason"] for a in attempts], ["bad-input"])
        self.assertIn("no-such-last-frame.png", attempts[0]["detail"])

    def test_a_non_kling_success_says_the_clip_was_not_steered_to_the_last_frame(self):
        import generate_video as gv

        def other_rung_result(provider):
            return {"status": "success", "provider": provider, "output": "o.mp4"}

        # kling unavailable: veo makes the clip
        with patch.object(gv, "generate_video_kling", return_value=None), \
                patch.object(gv, "generate_video_veo",
                             return_value=other_rung_result("veo-vertex")):
            via_veo = gv.generate_video_chain("p", "o.mp4", "first.png", 5,
                                              last_image_path="last.png", preferred="kling")
        # everything before higgsfield unavailable
        with patch.object(gv, "generate_video_kling", return_value=None), \
                patch.object(gv, "generate_video_veo", return_value=None), \
                patch.object(gv, "generate_video_higgsfield",
                             return_value=other_rung_result("higgsfield-kling")):
            via_higgs = gv.generate_video_chain("p", "o.mp4", "first.png", 5,
                                                last_image_path="last.png")
        # veo preferred and succeeds: kling is never even tried
        with patch.object(gv, "generate_video_kling") as kling, \
                patch.object(gv, "generate_video_veo",
                             return_value=other_rung_result("veo-vertex")):
            veo_first = gv.generate_video_chain("p", "o.mp4", "first.png", 5,
                                                last_image_path="last.png", preferred="veo")
            kling.assert_not_called()
        for name, result, rung in (("veo after kling", via_veo, "veo"),
                                   ("higgsfield last", via_higgs, "higgsfield"),
                                   ("veo preferred", veo_first, "veo")):
            with self.subTest(case=name):
                self.assertIs(result["last_frame_used"], False)
                self.assertIn(rung, result["last_frame_note"])
                self.assertIn("not steered", result["last_frame_note"])

        # no last frame requested: nothing to disclaim
        with patch.object(gv, "generate_video_kling", return_value=None), \
                patch.object(gv, "generate_video_veo",
                             return_value=other_rung_result("veo-vertex")):
            plain = gv.generate_video_chain("p", "o.mp4", "first.png", 5)
        self.assertNotIn("last_frame_used", plain)
        self.assertNotIn("last_frame_note", plain)

    # -- the CLI: a last frame is never silently dropped ----------------------

    def _cli(self, tmp, *args):
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(tmp))
        out_dir = Path(tmp) / "out"
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "generate_video.py"), "--brand", "b",
             "--month", "2026-09", "--post-id", "P01", "--output-dir", str(out_dir), *args],
            capture_output=True, text=True, env=env, timeout=60)
        return proc, out_dir

    def test_cli_exits_1_with_a_json_error_for_a_missing_last_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = str(Path(tmp) / "nope.png")
            proc, out_dir = self._cli(tmp, "--generate-video", "--last-image", missing)
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            data = json.loads(proc.stdout)
            self.assertIn("Last-frame", data["error"])
            self.assertEqual(data["path"], missing)
            self.assertFalse(out_dir.exists(),
                             "an input error must happen before any artifact is written")

    def test_cli_accepts_an_existing_last_image_and_refuses_it_without_generate_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            last = Path(tmp) / "last.png"
            last.write_bytes(b"png")
            accepted, _ = self._cli(tmp, "--generate-video", "--last-image", str(last))
            # No calendar exists in the throwaway workspace, so the run stops one
            # step later — proof the flag itself was accepted.
            self.assertEqual(accepted.returncode, 1)
            self.assertIn("Calendar not found", accepted.stdout)
            alone, _ = self._cli(tmp, "--last-image", str(last))
            self.assertEqual(alone.returncode, 2, "--last-image without --generate-video "
                             "would be silently ignored; it must be a usage error")
            self.assertIn("--last-image", alone.stderr)

    def test_cli_exits_1_for_a_missing_first_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = str(Path(tmp) / "first.png")
            proc, out_dir = self._cli(tmp, "--generate-video", "--image", missing)
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertIn("First-frame", json.loads(proc.stdout)["error"])
            self.assertFalse(out_dir.exists())

    def test_auto_routing_sends_a_last_frame_to_kling_first(self):
        import generate_video as gv
        self.assertEqual(gv.preferred_provider("auto", "veo", "last.png"), "kling")
        self.assertEqual(gv.preferred_provider("auto", "veo", None), "veo")
        self.assertEqual(gv.preferred_provider("veo", "kling", "last.png"), "veo",
                         "an explicit --provider must win")

    def test_the_skills_describe_the_last_frame_as_it_now_works(self):
        for text, name in ((GEN_VIDEO, "generate-video"), (COMPOSE, "compose-creative")):
            with self.subTest(skill=name):
                self.assertIn("last_frame_used", text)
        self.assertIn("--provider kling", GEN_VIDEO)
        self.assertNotIn("Not reachable", GEN_VIDEO)
        self.assertNotIn("a storyboard and approval artifact", GEN_VIDEO)
        self.assertNotIn("does not send it to the video provider", COMPOSE)

    def test_video_reference_images_are_not_implemented_and_the_skill_says_so(self):
        src = (SCRIPTS / "generate_video.py").read_text(encoding="utf-8")
        self.assertNotRegex(src, r'add_argument\("--(reference|references|style)[a-z-]*"')
        self.assertIn("Reference images for video", GEN_VIDEO)
        self.assertIn("Not implemented", GEN_VIDEO)


class TestRepeatIngestDocs(unittest.TestCase):
    """ALWAYS-ON-RECIPES.md tells weekly jobs what a repeat ingest does. These run
    the real script so that paragraph cannot drift from the behavior again: it
    used to say a repeat appends, which was true until the script learned to
    recognize a file it had already seen."""

    def _workspace(self):
        ws = Path(tempfile.mkdtemp())
        month = ws / "socialforge" / "output" / "acme" / "2026-09"
        month.mkdir(parents=True)
        (month / "calendar-data.json").write_text(
            json.dumps({"posts": [{"post_id": "P01", "topic": "t", "pillar": "p", "tier": "HUB"}]}),
            encoding="utf-8")
        return ws, month

    def _ingest(self, ws, csv_path, label, *extra):
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(ws))
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "ingest_performance.py"), "--action", "ingest",
             "--brand", "acme", "--month", "2026-09", "--csv", str(csv_path),
             "--source", label, *extra],
            capture_output=True, text=True, env=env, timeout=60)

    def test_ingesting_the_same_file_twice_stores_every_row_once(self):
        ws, month = self._workspace()
        export = ws / "wk1.csv"
        export.write_text("post_id,impressions,likes\nP01,1000,50\n", encoding="utf-8")
        first = self._ingest(ws, export, "wk1.csv")
        second = self._ingest(ws, export, "wk1.csv")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(json.loads(second.stdout)["status"], "already_ingested")
        perf = json.loads((month / "performance.json").read_text(encoding="utf-8"))
        self.assertEqual(len(perf["posts"]["P01"]), 1)
        self.assertEqual([s["label"] for s in perf["sources"]], ["wk1.csv"])
        self.assertIn("already_ingested", RECIPES)
        self.assertNotIn("appends; it does not replace", RECIPES,
                         "the recipes still describe the old double-counting behavior")

    def test_a_cumulative_export_under_one_label_with_replace_keeps_the_latest_snapshot(self):
        ws, month = self._workspace()
        week1, week2 = ws / "mtd-1.csv", ws / "mtd-2.csv"
        week1.write_text("post_id,impressions,likes\nP01,1000,50\n", encoding="utf-8")
        week2.write_text("post_id,impressions,likes\nP01,2500,120\n", encoding="utf-8")
        self.assertEqual(self._ingest(ws, week1, "linkedin-mtd", "--replace").returncode, 0)
        proc = self._ingest(ws, week2, "linkedin-mtd", "--replace")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        perf = json.loads((month / "performance.json").read_text(encoding="utf-8"))
        self.assertEqual([r["impressions"] for r in perf["posts"]["P01"]], [2500],
                         "week 2's cumulative totals must replace week 1's, not sit on top of them")
        self.assertEqual(len(perf["sources"]), 1)
        self.assertIn("--replace", RECIPES)
        self.assertIn("constant", RECIPES)


if __name__ == "__main__":
    unittest.main()
