"""Every platform SocialForge writes copy for must also have an image size.

This existed as a silent hole: adapt_copy.py carried char limits, hashtag rules
and link behaviour for tiktok, threads and bluesky, while resize_image.py had no
dimensions for any of them. A post targeting TikTok got adapted copy and then
failed at resize with "Unknown platform" — the copy half of the pipeline was a
generation ahead of the image half.

Nothing caught it because the two tables live in different files and no test
compared them. This is that test.

Stdlib only.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"

# Platforms deliberately absent from one side, with the reason. Empty by design:
# if you add an entry here, justify it in the comment or the test is worthless.
COPY_ONLY_ALLOWED: set[str] = set()
IMAGE_ONLY_ALLOWED: set[str] = set()


def copy_platforms() -> set[str]:
    src = (SCRIPTS / "adapt_copy.py").read_text(encoding="utf-8")
    return set(re.findall(r'^\s{4}"([a-z]+)":\s*\{"char_limit"', src, re.M))


def image_platforms() -> dict[str, list[str]]:
    """Map platform -> its spec keys, e.g. tiktok -> [tiktok_post, tiktok_portrait]."""
    src = (SCRIPTS / "resize_image.py").read_text(encoding="utf-8")
    out: dict[str, list[str]] = {}
    for key in re.findall(r'"([a-z]+_[a-z]+)":\s*\{"width"', src):
        out.setdefault(key.split("_")[0], []).append(key)
    return out


class TestPlatformParity(unittest.TestCase):
    def test_every_copy_platform_has_an_image_size(self):
        missing = copy_platforms() - set(image_platforms()) - COPY_ONLY_ALLOWED
        self.assertEqual(
            missing, set(),
            f"adapt_copy.py writes copy for {sorted(missing)} but resize_image.py "
            f"has no dimensions for them — those posts fail at resize time")

    def test_every_image_platform_has_copy_rules(self):
        missing = set(image_platforms()) - copy_platforms() - IMAGE_ONLY_ALLOWED
        self.assertEqual(
            missing, set(),
            f"resize_image.py sizes images for {sorted(missing)} but adapt_copy.py "
            f"has no char limits for them — that copy ships unadapted")

    def test_the_three_platforms_that_were_missing_are_present(self):
        """Regression pin for the specific hole this test was written for."""
        imgs = image_platforms()
        for platform in ("tiktok", "threads", "bluesky"):
            with self.subTest(platform=platform):
                self.assertIn(platform, imgs, f"{platform} image specs regressed away")

    def test_specs_are_wellformed(self):
        """Width, height and ratio must agree — a wrong ratio string silently
        misleads whoever reads the JSON output."""
        src = (SCRIPTS / "resize_image.py").read_text(encoding="utf-8")
        rows = re.findall(
            r'"([a-z_]+)":\s*\{"width":\s*(\d+),\s*"height":\s*(\d+),\s*"ratio":\s*"([^"]+)"\}',
            src)
        self.assertGreaterEqual(len(rows), 20, "spec table did not parse")
        for name, w, h, ratio in rows:
            with self.subTest(spec=name):
                w, h = int(w), int(h)
                self.assertGreater(w, 0)
                self.assertGreater(h, 0)
                if ":" not in ratio:
                    continue
                rw, rh = (float(x) for x in ratio.split(":"))
                # 4% tolerance: published ratios are rounded (1.91:1, 4:5).
                self.assertAlmostEqual(
                    w / h, rw / rh, delta=(rw / rh) * 0.04,
                    msg=f"{name}: {w}x{h} is not {ratio}")


if __name__ == "__main__":
    unittest.main()
