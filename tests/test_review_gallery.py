"""The review gallery says how big it is and whether it can be published.

`build_gallery.py` writes one self-contained HTML file. It stays the source of
truth, but a reviewer may be offered a hosted copy, and a hosted page has a size
ceiling: inlined video is what blows through it. These tests pin that the result
reports the real size, that `publishable_as_page` is true only at or under the
15 MB ceiling, that an oversize gallery says why and how to shrink it, and that
`--no-inline-video` links videos by relative path instead of embedding them.

Stdlib only. Every test here was proven to fire by planting its failure.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_gallery as bg  # noqa: E402

LIMIT = 15 * 1024 * 1024
# A 1x1 PNG — small, but a real image file the gallery will embed.
TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360f8cfc0f01f0005000201a5f645400000000049454e44ae426082")


def make_workspace(video_bytes=0, image=False):
    """A one-post month with a video in the legacy flat layout (and optionally an
    image). Returns (workspace root, month dir)."""
    ws = Path(tempfile.mkdtemp())
    month = ws / "socialforge" / "output" / "probe" / "2026-09"
    month.mkdir(parents=True)
    (month / "calendar-data.json").write_text(json.dumps({"posts": [{
        "post_id": "P01", "date": "2026-09-03", "platforms": ["linkedin"],
        "tier": "HERO", "content_type": "video", "title": "Launch teaser"}]}), encoding="utf-8")
    (month / "status-tracker.json").write_text(json.dumps({"posts": {}}), encoding="utf-8")
    if video_bytes:
        videos = month / "production" / "videos"
        videos.mkdir(parents=True)
        (videos / "post-P01-video.mp4").write_bytes(b"\x00" * video_bytes)
    if image:
        images = month / "production" / "images"
        images.mkdir(parents=True)
        (images / "post-P01-variant-a.png").write_bytes(TINY_PNG)
    return ws, month


def run_cli(ws, *extra):
    env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(ws))
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "build_gallery.py"), "--brand", "probe",
         "--month", "2026-09", *extra],
        capture_output=True, text=True, env=env, timeout=120)
    return proc.returncode, json.loads(proc.stdout) if proc.stdout.strip() else None


def run_in_process(ws, limit=None, **kwargs):
    """Call build_gallery directly so the ceiling can be moved for boundary tests."""
    buf = io.StringIO()
    patches = [patch.object(bg, "WORKSPACE", ws / "socialforge")]
    if limit is not None:
        patches.append(patch.object(bg, "PAGE_PUBLISH_LIMIT_BYTES", limit))
    with contextlib.ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        with contextlib.redirect_stdout(buf):
            bg.build_gallery("probe", "2026-09", **kwargs)
    return json.loads(buf.getvalue())


class TestSizeReporting(unittest.TestCase):
    def test_the_publish_ceiling_is_15_mib(self):
        self.assertEqual(bg.PAGE_PUBLISH_LIMIT_BYTES, LIMIT)

    def test_a_small_gallery_reports_its_real_size_and_is_publishable(self):
        ws, month = make_workspace(image=True)
        code, d = run_cli(ws)
        self.assertEqual(code, 0)
        on_disk = (month / "review" / "gallery.html").stat().st_size
        self.assertEqual(d["size_bytes"], on_disk, "size_bytes must be the file's real size")
        self.assertEqual(d["size_mb"], round(on_disk / (1024 * 1024), 2))
        self.assertIs(d["publishable_as_page"], True)
        self.assertNotIn("note", d, "nothing to warn about for a small, fully-embedded gallery")
        self.assertEqual(d["videos_embedded"], 0)

    def test_publishable_is_true_at_the_ceiling_and_false_one_byte_over(self):
        ws, month = make_workspace(video_bytes=2000)
        size = run_in_process(ws)["size_bytes"]
        at_limit = run_in_process(ws, limit=size)
        over = run_in_process(ws, limit=size - 1)
        self.assertIs(at_limit["publishable_as_page"], True, "exactly at the ceiling still fits")
        self.assertIs(over["publishable_as_page"], False, "one byte over the ceiling does not")
        self.assertIn("note", over)

    def test_an_oversize_gallery_with_inlined_video_blames_the_video_and_offers_the_fix(self):
        # 12 MB of video is ~16 MB once base64-encoded: over the real 15 MiB ceiling.
        ws, month = make_workspace(video_bytes=12 * 1024 * 1024)
        code, d = run_cli(ws)
        self.assertEqual(code, 0)
        self.assertGreater(d["size_bytes"], LIMIT)
        self.assertIs(d["publishable_as_page"], False)
        self.assertEqual(d["videos_embedded"], 1)
        self.assertIn("video", d["note"])
        self.assertIn("--no-inline-video", d["note"])
        self.assertTrue((month / "review" / "gallery.html").exists(),
                        "the local file is built regardless — it is the source of truth")

    def test_an_oversize_gallery_with_no_video_does_not_blame_video(self):
        ws, _ = make_workspace(image=True)
        d = run_in_process(ws, limit=10)
        self.assertIs(d["publishable_as_page"], False)
        self.assertIn("no inlined video", d["note"])
        self.assertNotIn("--no-inline-video", d["note"],
                         "rebuilding without video cannot shrink a gallery that has none")


class TestNoInlineVideo(unittest.TestCase):
    def test_videos_are_linked_by_relative_path_and_the_file_stays_small(self):
        ws, month = make_workspace(video_bytes=12 * 1024 * 1024)
        code, d = run_cli(ws, "--no-inline-video")
        self.assertEqual(code, 0)
        html = (month / "review" / "gallery.html").read_text(encoding="utf-8")
        self.assertIn('src="../production/videos/post-P01-video.mp4"', html)
        self.assertNotIn("data:video", html, "no video may be embedded in this mode")
        self.assertEqual(d["videos_linked"], 1)
        self.assertEqual(d["videos_embedded"], 0)
        self.assertLess(d["size_bytes"], 100_000)
        self.assertIs(d["publishable_as_page"], True)

    def test_the_result_warns_that_a_published_copy_cannot_play_linked_videos(self):
        ws, _ = make_workspace(video_bytes=1000)
        _, d = run_cli(ws, "--no-inline-video")
        self.assertIn("relative path", d["note"])
        self.assertIn("published elsewhere", d["note"])

    def test_the_default_still_embeds_the_video(self):
        ws, month = make_workspace(video_bytes=1000)
        _, d = run_cli(ws)
        html = (month / "review" / "gallery.html").read_text(encoding="utf-8")
        self.assertIn("data:video/mp4;base64,", html)
        self.assertEqual((d["videos_embedded"], d["videos_linked"]), (1, 0))
        self.assertNotIn("note", d)

    def test_an_unreadable_video_is_not_counted_as_embedded_and_says_so(self):
        ws, month = make_workspace(video_bytes=10)
        # The gallery finds the file, then cannot read it: it must say so in the
        # card and must not count it as embedded.
        with patch.object(bg, "file_to_base64", return_value=""):
            inline = run_in_process(ws)
        self.assertEqual(inline["videos_embedded"], 0)
        html = (month / "review" / "gallery.html").read_text(encoding="utf-8")
        self.assertIn("Video file missing or unreadable", html)


class TestGallerySkill(unittest.TestCase):
    SKILL = (REPO / "skills" / "build-review-gallery" / "SKILL.md").read_text(encoding="utf-8")

    def test_the_publish_step_is_optional_gated_and_never_claims_sharing(self):
        text = self.SKILL
        self.assertIn("publishable_as_page", text)
        self.assertIn("--no-inline-video", text)
        self.assertIn("explicit yes", text)
        self.assertIn("never say or imply", text.lower())
        self.assertIn("local", text)
        self.assertIn("fallback and the source of truth", text)

    def test_the_skill_no_longer_promises_a_placeholder_the_script_never_renders(self):
        self.assertNotIn("Video not embeddable", self.SKILL)


if __name__ == "__main__":
    unittest.main()
