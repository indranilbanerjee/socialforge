"""The video script scaffold must obey the craft rules, mechanically.

The old scaffold opened every video with three seconds of brand logo — on a
social feed those are the only seconds most viewers give, and a logo is the one
thing guaranteed not to earn the next three. It also emitted the same four
generic scenes for every video regardless of type, length, or content, with no
per-scene payoff and no rules carried to the agent that fills it in.

These tests pin the replacement's structure. The agent supplies the creative;
the scaffold supplies the discipline.

Stdlib only.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from generate_video import generate_script, generate_storyboard, generate_srt  # noqa: E402


def make(duration=30, video_type="short_reel", brief="Product demo against a city backdrop"):
    return generate_script(
        {"title": "Test post", "visual": {"direction_a": brief},
         "video_details": {"video_type": video_type, "duration_seconds": duration}},
        {"brand_name": "Acme"})


class TestHookFirst(unittest.TestCase):
    def test_the_video_never_opens_with_the_logo(self):
        """The regression that matters: seconds 0-3 belong to the hook."""
        for duration in (10, 15, 30, 60, 90):
            with self.subTest(duration=duration):
                first = make(duration)["scenes"][0]
                self.assertEqual(first["role"], "hook")
                self.assertNotIn("logo", first["visual"].lower(),
                                 "the open is spending the only guaranteed seconds on a logo")

    def test_the_logo_lives_in_the_end_card(self):
        last = make()["scenes"][-1]
        self.assertEqual(last["role"], "cta-endcard")
        self.assertIn("logo", last["visual"].lower())

    def test_hook_is_short(self):
        """A hook that runs past ~3s is an intro wearing a hook's name."""
        for duration in (10, 30, 90):
            with self.subTest(duration=duration):
                ts = make(duration)["scenes"][0]["timestamp"]
                end_s = int(ts.split("-")[1].split(":")[1]) + 60 * int(ts.split("-")[1].split(":")[0])
                self.assertLessEqual(end_s, 3)


class TestPayoffPerScene(unittest.TestCase):
    def test_every_scene_carries_a_payoff_field(self):
        for scene in make()["scenes"]:
            with self.subTest(role=scene["role"]):
                self.assertTrue(scene.get("payoff"),
                                f"{scene['role']} has no payoff — that is where viewers leave")

    def test_beat_count_scales_with_duration(self):
        """A 10-second story is not a 90-second hero video with the same four
        scenes — the old scaffold's exact failure."""
        short = [s["role"] for s in make(10)["scenes"]]
        long = [s["role"] for s in make(90)["scenes"]]
        self.assertLess(len(short), len(long))
        self.assertEqual(short[0], "hook")
        self.assertEqual(long[-1], "cta-endcard")

    def test_timestamps_are_continuous_and_fill_the_duration(self):
        for duration in (10, 15, 30, 45, 60, 90):
            with self.subTest(duration=duration):
                scenes = make(duration)["scenes"]
                prev_end = "0:00"
                for s in scenes:
                    start, end = s["timestamp"].split("-")
                    self.assertEqual(start, prev_end,
                                     f"gap before {s['role']}: {prev_end} -> {start}")
                    prev_end = end
                mins, secs = prev_end.split(":")
                self.assertEqual(int(mins) * 60 + int(secs), duration)


class TestRulesTravelWithTheScript(unittest.TestCase):
    """The scaffold's discipline must reach the agent that fills it in."""

    def test_script_carries_its_rules(self):
        rules = " ".join(make()["script_rules"])
        for needle in ("hook-first", "payoff-per-scene", "pairing", "compliance"):
            self.assertIn(needle, rules)

    def test_brief_reaches_the_hook_scene(self):
        """The scaffold must be built FROM the post, not beside it."""
        script = make(brief="A barista pouring latte art in slow motion")
        self.assertIn("barista pouring latte art", script["scenes"][0]["visual"])

    def test_overlay_placeholder_states_the_pairing_rule(self):
        hook = make()["scenes"][0]
        self.assertIn("caption", hook["text_overlay"].lower(),
                      "the hook overlay placeholder must warn against echoing the caption")


class TestDownstreamCompatibility(unittest.TestCase):
    def test_storyboard_builds_from_the_new_shape(self):
        board = generate_storyboard(make())
        self.assertEqual(board["total_scenes"], len(make()["scenes"]))
        self.assertTrue(all(f["timestamp"] for f in board["frames"]))

    def test_srt_builds_from_the_new_shape(self, tmp=None):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "test.srt"
            generate_srt(make(), out)
            content = out.read_text(encoding="utf-8")
            self.assertIn("1\n", content)
            self.assertIn("-->", content)


if __name__ == "__main__":
    unittest.main()
