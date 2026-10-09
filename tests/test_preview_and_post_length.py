"""A preview must show the post, and a post's length must include what gets posted.

Found by rendering a real LinkedIn preview for the README (2026-10-10):

  1. Every preview showed a broken-image icon while `render_preview.py` reported
     success. The page is loaded with set_content(), so it lives at about:blank,
     and Chromium refuses file:// images from there. The 1.19 fix refused a
     MISSING image; an existing one still rendered as nothing. The image is now
     embedded as a data: URI, and the script checks the page actually drew it.
  2. The preview collapsed the post's line breaks into one paragraph, so it did
     not show how the post will look. LinkedIn, X and the rest keep them.
  3. `adapt_copy.py` measured the copy without its inline hashtags, which
     platform_limits.json places "inline at the end of the post": a 255-character
     X post plus "#LinkRot #ContentMarketing" was reported within 280 and
     published at 282. Bare tags ("LinkRot") were also passed through without '#'.

Stdlib unittest; the render tests need Playwright with Chromium and the pixel
check needs Pillow, and each skips without them.
"""
from __future__ import annotations

import importlib.util
import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _solid_png(path, rgb=(220, 20, 60), size=40):
    """A size x size PNG of one colour, written with the stdlib only."""
    row = b"\x00" + bytes(rgb) * size
    raw = row * size

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw))
           + chunk(b"IEND", b""))
    Path(path).write_bytes(png)


def _have_chromium():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            p.chromium.launch(headless=True).close()
        return True
    except Exception:
        return False


HAVE_CHROMIUM = _have_chromium()
try:
    from PIL import Image  # noqa: F401
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False


def _render(image, copy, out):
    p = subprocess.run([sys.executable, str(SCRIPTS / "render_preview.py"),
                        "--image", str(image), "--copy", copy, "--platform", "linkedin",
                        "--brand", "t", "--output", str(out)],
                       capture_output=True, text=True, encoding="utf-8", timeout=180)
    return p, json.loads(p.stdout)


class TestPreviewShowsTheImage(unittest.TestCase):
    def test_image_is_embedded_not_linked(self):
        rp = _load("sf_render_preview_embed", "render_preview.py")
        with tempfile.TemporaryDirectory() as td:
            img = Path(td) / "a.png"
            _solid_png(img)
            uri = rp._image_data_uri(img)
        self.assertTrue(uri.startswith("data:image/png;base64,"),
                        "a file:// URI is blocked from the about:blank preview page")

    def test_line_breaks_are_kept(self):
        rp = _load("sf_render_preview_breaks", "render_preview.py")
        html = rp.build_default_html("n", "@n", "LINKEDIN", "", "one\n\ntwo")
        self.assertIn("white-space: pre-wrap", html,
                      "without pre-wrap the preview joins paragraphs the platform keeps apart")

    @unittest.skipUnless(HAVE_CHROMIUM and HAVE_PIL, "needs Playwright Chromium and Pillow")
    def test_rendered_preview_contains_the_image_pixels(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as td:
            img, out = Path(td) / "red.png", Path(td) / "preview.png"
            _solid_png(img, rgb=(220, 20, 60))
            p, payload = _render(img, "one\n\ntwo", out)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual(payload["status"], "success")
            pixels = Image.open(out).convert("RGB").getdata()
            red = sum(1 for (r, g, b) in pixels if r > 200 and g < 60 and b < 90)
            self.assertGreater(red, 1000, "the preview must show the image, not a broken-image icon")

    @unittest.skipUnless(HAVE_CHROMIUM, "needs Playwright Chromium")
    def test_a_file_that_is_not_an_image_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            bad, out = Path(td) / "not-an-image.png", Path(td) / "p.png"
            bad.write_text("this is not an image", encoding="utf-8")
            p, payload = _render(bad, "copy", out)
            self.assertNotEqual(p.returncode, 0)
            self.assertEqual(payload["status"], "FAILED")
            self.assertEqual(payload["reason"], "image-did-not-render")
            self.assertFalse(out.exists(), "no preview file for an image the page could not draw")

    @unittest.skipUnless(HAVE_CHROMIUM, "needs Playwright Chromium")
    def test_long_copy_is_marked_not_cut_silently(self):
        with tempfile.TemporaryDirectory() as td:
            img, out = Path(td) / "a.png", Path(td) / "p.png"
            _solid_png(img)
            _, payload = _render(img, "word " * 200, out)
            self.assertTrue(payload.get("copy_truncated"))


class TestPostLengthIncludesInlineHashtags(unittest.TestCase):
    def setUp(self):
        self.ac = _load("sf_adapt_copy_len", "adapt_copy.py")

    def test_x_post_with_hashtags_stays_within_the_limit(self):
        r = self.ac.adapt_for_platform("Dead links quietly erode trust. " * 20, "x",
                                       ["#LinkRot", "#ContentMarketing"])
        self.assertTrue(r["post_text"].endswith("#LinkRot #ContentMarketing"))
        self.assertEqual(r["post_char_count"], len(r["post_text"]))
        self.assertLessEqual(r["post_char_count"], r["char_limit"])
        self.assertTrue(r["within_limit"])

    def test_bare_tags_get_their_hash(self):
        r = self.ac.adapt_for_platform("Short post.", "linkedin", ["LinkRot", " #Trust ", ""])
        self.assertEqual(r["hashtags"], "#LinkRot #Trust")

    def test_first_comment_hashtags_stay_out_of_the_post(self):
        r = self.ac.adapt_for_platform("Short post.", "instagram", ["LinkRot"])
        self.assertEqual(r["post_text"], r["copy"])
        self.assertEqual(r["first_comment"], "#LinkRot")
        self.assertEqual(r["hashtags"], "")


if __name__ == "__main__":
    unittest.main()
