"""The CTA is a per-platform mechanism, and it must never be silently discarded.

Two defects existed here, both shipped for months:

1. On bio-link platforms (Instagram, TikTok) the adapter appended a bare
   "Link in bio" and threw the actual CTA away. The offer the caption was
   supposed to sell never appeared on the two platforms where captions matter
   most, and nothing failed — the output looked plausible.

2. Truncation ran BEFORE the CTA was appended, so a limit-length post plus its
   CTA overflowed the platform limit. The script measured its own output as
   too long (`within_limit: false`) and shipped it anyway.

Stdlib only.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from adapt_copy import PLATFORM_LIMITS, adapt_for_platform, render_cta  # noqa: E402

CTA = "Grab the free audit template: https://example.com/audit"


class TestCtaNeverDiscarded(unittest.TestCase):
    def test_every_platform_carries_the_cta_in_some_form(self):
        """The regression that matters: no platform may drop the CTA's offer."""
        for platform, specs in PLATFORM_LIMITS.items():
            with self.subTest(platform=platform):
                out = adapt_for_platform("A post body.", platform, cta=CTA)
                self.assertIsNotNone(out["cta_rendered"], f"{platform} dropped the CTA")
                if specs.get("link") == "bio":
                    self.assertIn("audit template", out["copy"].lower(),
                                  f"{platform}: the offer vanished from the caption")
                else:
                    self.assertIn(CTA, out["copy"])

    def test_bio_platforms_strip_the_url_but_keep_the_offer(self):
        for platform in ("instagram", "tiktok"):
            with self.subTest(platform=platform):
                out = adapt_for_platform("Body.", platform, cta=CTA)
                self.assertNotIn("https://", out["copy"],
                                 "a pasted URL is dead weight in a bio-link caption")
                self.assertIn("link in bio", out["copy"].lower())
                self.assertIn("Grab the free audit template", out["copy"])

    def test_url_only_cta_on_bio_platform_falls_back_plainly(self):
        """The one case the old code handled correctly must keep working."""
        out = adapt_for_platform("Body.", "instagram", cta="https://example.com/x")
        self.assertEqual(out["cta_rendered"], "Link in bio.")

    def test_direct_platforms_keep_the_cta_verbatim(self):
        out = adapt_for_platform("Body.", "linkedin", cta=CTA)
        self.assertIn(CTA, out["copy"])
        self.assertEqual(out["cta_mechanism"], "direct-link")

    def test_no_cta_adds_nothing(self):
        out = adapt_for_platform("Body.", "instagram")
        self.assertIsNone(out["cta_rendered"])
        self.assertIsNone(out["cta_mechanism"])
        self.assertNotIn("link in bio", out["copy"].lower())


class TestCommentKeywordMechanism(unittest.TestCase):
    def test_keyword_replaces_bio_routing_when_brand_runs_an_automation(self):
        out = adapt_for_platform("Body.", "instagram", cta=CTA, cta_keyword="AUDIT")
        self.assertEqual(out["cta_mechanism"], "comment-keyword")
        self.assertIn('"AUDIT"', out["copy"])
        self.assertNotIn("link in bio", out["copy"].lower())

    def test_keyword_is_ignored_on_direct_link_platforms(self):
        """A comment automation is an Instagram/TikTok mechanism; on LinkedIn the
        link simply works, and asking for a comment keyword there is cargo cult."""
        out = adapt_for_platform("Body.", "linkedin", cta=CTA, cta_keyword="AUDIT")
        self.assertEqual(out["cta_mechanism"], "direct-link")
        self.assertIn(CTA, out["copy"])
        self.assertNotIn("AUDIT", out["copy"].split(CTA)[0])


class TestCtaFitsWithinTheLimit(unittest.TestCase):
    def test_limit_length_post_plus_cta_stays_within_limit(self):
        """Defect 2: room for the CTA must be reserved before truncation."""
        for platform in ("x", "bluesky", "threads", "pinterest"):
            specs = PLATFORM_LIMITS[platform]
            long_body = "A sentence that fills space. " * 40
            with self.subTest(platform=platform):
                out = adapt_for_platform(long_body, platform, cta="Read it here: https://example.com/p")
                self.assertTrue(out["within_limit"],
                                f"{platform}: {out['char_count']}/{specs['char_limit']} — "
                                f"the CTA pushed the copy past the platform limit")
                self.assertIn("example.com", out["copy"], "the CTA itself was truncated away")

    def test_short_posts_are_untouched(self):
        out = adapt_for_platform("Short.", "x", cta="More: https://example.com")
        self.assertTrue(out["copy"].startswith("Short."))
        self.assertTrue(out["within_limit"])


class TestRenderCta(unittest.TestCase):
    def test_render_is_pure_and_none_safe(self):
        self.assertIsNone(render_cta(None, PLATFORM_LIMITS["instagram"]))
        self.assertIsNone(render_cta("", PLATFORM_LIMITS["x"]))

    def test_offer_punctuation_is_tidied(self):
        rendered = render_cta("Download the guide — https://a.b/c", PLATFORM_LIMITS["instagram"])
        self.assertEqual(rendered, "Download the guide — link in bio.")


if __name__ == "__main__":
    unittest.main()
