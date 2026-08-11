"""A cost report must never contain a number nobody looked up.

The old cost table is gone. It was keyed by operation rather than model, so a
3-second clip and a 15-second clip logged identical cost; it assumed $0.40/sec
for video while a wired provider sold at a fraction of that; and it went stale
without saying so. These tests pin the replacement's promises:

  - local work is free, and says why
  - paid work with no price is recorded as *unpriced*, never as $0.00
  - a month total announces when it is incomplete
  - an invoiced figure always beats a quote

Plus a coverage guard: every model the code can actually call needs a recipe
file, because the sync-vs-async and auth details are what make a first call work.

Stdlib only.
"""
from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
RECIPES = ROOT / "references" / "models"
sys.path.insert(0, str(SCRIPTS))

SRC = "https://wavespeed.ai/models/kwaivgi/kling-v3.0-pro/image-to-video"


class TestNoHardcodedPrices(unittest.TestCase):
    def test_cost_estimates_table_is_gone(self):
        src = (SCRIPTS / "cost_tracker.py").read_text(encoding="utf-8")
        self.assertNotIn("COST_ESTIMATES", src,
                         "the hardcoded per-operation cost table is back")

    def test_no_dollar_figures_left_in_cost_tracker(self):
        """Any bare float that looks like a rate is a price in hiding.

        Comments and string literals are stripped first: a rate lives in code, so
        "$0.00" inside a warning message is prose, not a price.
        """
        src = (SCRIPTS / "cost_tracker.py").read_text(encoding="utf-8")
        code = "\n".join(
            line.split("#")[0] for line in src.splitlines()
            if not line.strip().startswith("#"))
        code = re.sub(r'"""..*?"""', "", code, flags=re.S)
        code = re.sub(r"'''.*?'''", "", code, flags=re.S)
        code = re.sub(r'"[^"\n]*"', '""', code)
        code = re.sub(r"'[^'\n]*'", "''", code)
        # 0.0 is legitimate — the recorded cost of local work.
        suspicious = [m for m in re.findall(r"(?<![\w.])0\.\d+", code) if m != "0.0"]
        self.assertEqual(suspicious, [],
                         f"cost_tracker.py still carries rate-like literals: {suspicious}")

    def test_price_book_ships_no_prices(self):
        src = (SCRIPTS / "price_book.py").read_text(encoding="utf-8")
        self.assertNotIn("price_usd\":", src.split("def ")[0],
                         "price_book has a seeded price in its module header")


class CostTrackerCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.month_dir = root / "socialforge" / "output" / "acme" / "2026-08"
        self.month_dir.mkdir(parents=True)
        self.log = self.month_dir / "cost-log.json"
        self.log.write_text(json.dumps({"entries": [], "total_cost_usd": 0}), encoding="utf-8")

        os.environ["CLAUDE_PLUGIN_DATA"] = str(root)
        os.environ["CLAUDE_PLUGIN_DATA_DIR"] = str(root)
        import price_book
        self.pb = importlib.reload(price_book)
        self.pb.record("kling-v3.0-pro", "wavespeed", "second", 0.112, SRC)

    def tearDown(self):
        for var in ("CLAUDE_PLUGIN_DATA", "CLAUDE_PLUGIN_DATA_DIR"):
            os.environ.pop(var, None)
        self._tmp.cleanup()

    def _log(self, *args):
        env = dict(os.environ)
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "cost_tracker.py"), "--action", "log",
             "--brand", "acme", "--month", "2026-08", *args],
            capture_output=True, text=True, env=env)

    def _entries(self):
        return json.loads(self.log.read_text(encoding="utf-8"))["entries"]


class TestUnpricedIsNotZero(CostTrackerCase):
    def test_paid_op_with_no_price_records_null_not_zero(self):
        """The failure that matters: $0.00 makes a month look cheaper than it was."""
        self._log("--operation", "kling_video", "--post-id", "p1")
        entry = self._entries()[0]
        self.assertIsNone(entry["cost_usd"])
        self.assertEqual(entry["basis"], "unpriced")

    def test_unpriced_entry_warns_on_stderr(self):
        r = self._log("--operation", "kling_video", "--post-id", "p1")
        self.assertIn("unpriced", r.stderr.lower())

    def test_local_operations_are_free_and_say_why(self):
        for op in ("compositing", "carousel_render", "background_removal", "resize"):
            with self.subTest(op=op):
                self._log("--operation", op, "--post-id", "p")
                entry = self._entries()[-1]
                self.assertEqual(entry["cost_usd"], 0.0)
                self.assertEqual(entry["basis"], "local-no-api-cost")


class TestTotalHonesty(CostTrackerCase):
    def test_total_flags_itself_incomplete_when_something_is_unpriced(self):
        self._log("--operation", "kling_video", "--post-id", "p1")
        book = json.loads(self.log.read_text(encoding="utf-8"))
        self.assertFalse(book["total_is_complete"])
        self.assertEqual(book["unpriced_entries"], 1)
        self.assertIn("could not be priced", book["total_note"])

    def test_total_is_complete_when_everything_priced(self):
        self._log("--operation", "kling_video", "--post-id", "p1",
                  "--model", "kling-v3.0-pro", "--provider", "wavespeed", "--units", "5")
        book = json.loads(self.log.read_text(encoding="utf-8"))
        self.assertTrue(book["total_is_complete"])
        self.assertNotIn("total_note", book)

    def test_unpriced_entries_do_not_drag_the_total_down(self):
        self._log("--operation", "kling_video", "--post-id", "p1",
                  "--model", "kling-v3.0-pro", "--provider", "wavespeed", "--units", "10")
        self._log("--operation", "kling_video", "--post-id", "p2")
        book = json.loads(self.log.read_text(encoding="utf-8"))
        self.assertAlmostEqual(book["total_cost_usd"], 1.12, places=4)


class TestPricingBasis(CostTrackerCase):
    def test_quote_from_the_price_book_carries_its_provenance(self):
        self._log("--operation", "kling_video", "--post-id", "p1",
                  "--model", "kling-v3.0-pro", "--provider", "wavespeed", "--units", "10")
        entry = self._entries()[0]
        self.assertEqual(entry["basis"], "price-book-quote")
        self.assertAlmostEqual(entry["cost_usd"], 1.12, places=4)
        self.assertEqual(entry["source"], SRC)
        self.assertIn("priced_at", entry)

    def test_invoiced_amount_beats_a_quote(self):
        self._log("--operation", "kling_video", "--post-id", "p1", "--cost", "1.99",
                  "--model", "kling-v3.0-pro", "--provider", "wavespeed", "--units", "10")
        entry = self._entries()[0]
        self.assertEqual(entry["basis"], "actual")
        self.assertAlmostEqual(entry["cost_usd"], 1.99, places=4)

    def test_sound_multiplier_is_applied_and_recorded(self):
        """sound=True bills above the base rate on at least one wired model, and
        was previously not priced at all."""
        self._log("--operation", "kling_video", "--post-id", "p1",
                  "--model", "kling-v3.0-pro", "--provider", "wavespeed",
                  "--units", "10", "--multiplier", "1.5")
        entry = self._entries()[0]
        self.assertAlmostEqual(entry["cost_usd"], 1.68, places=4)
        self.assertEqual(entry["multiplier"], 1.5)

    def test_multiplier_shows_base_and_reason_in_a_quote(self):
        q = self.pb.quote("kling-v3.0-pro", "wavespeed", 10,
                          multiplier=1.5, multiplier_reason="sound=true")
        self.assertAlmostEqual(q["base_usd"], 1.12, places=4)
        self.assertAlmostEqual(q["total_usd"], 1.68, places=4)
        self.assertEqual(q["multiplier_reason"], "sound=true")

    def test_plain_quote_carries_no_multiplier_noise(self):
        q = self.pb.quote("kling-v3.0-pro", "wavespeed", 10)
        for field in ("multiplier", "base_usd", "multiplier_reason"):
            self.assertNotIn(field, q)

    def test_zero_or_negative_multiplier_rejected(self):
        for bad in (0, -1):
            with self.subTest(multiplier=bad):
                with self.assertRaises(ValueError):
                    self.pb.quote("kling-v3.0-pro", "wavespeed", 10, multiplier=bad)


class TestRecipeCoverage(unittest.TestCase):
    """Every model the code can call needs a recipe — that is where sync-vs-async
    and the auth shape live, and getting either wrong looks like a hang."""

    WIRED = {
        "gemini-flash-image": "primary image path (sync)",
        "kling-image-v3": "WaveSpeed image fallback",
        "higgsfield-soul-v2": "Higgsfield image fallback",
        "kling-v3.0-pro-video": "primary video path",
        "veo-3.1": "Vertex video path",
        "higgsfield-kling-v2.1": "Higgsfield video fallback",
    }

    def test_every_wired_model_has_a_recipe(self):
        present = {p.stem for p in RECIPES.glob("*.md")} - {"README", "_TEMPLATE"}
        missing = set(self.WIRED) - present
        self.assertEqual(missing, set(),
                         f"wired models with no recipe: {sorted(missing)}")

    def test_every_recipe_declares_sync_or_async(self):
        for path in RECIPES.glob("*.md"):
            if path.stem in ("README", "_TEMPLATE"):
                continue
            with self.subTest(recipe=path.name):
                body = path.read_text(encoding="utf-8")
                self.assertRegex(body, r"\*\*(Sync|Async)\*\*",
                                 f"{path.name} does not state sync or async")

    def test_no_recipe_carries_a_price(self):
        """Prices belong to the price book. One written here is stale on arrival
        and looks authoritative."""
        for path in RECIPES.glob("*.md"):
            if path.stem in ("README", "_TEMPLATE"):
                continue
            body = path.read_text(encoding="utf-8")
            table = body.split("## ")[0]  # the header table only
            with self.subTest(recipe=path.name):
                self.assertNotRegex(
                    table, r"\|\s*(Cost|Price)\s*\|",
                    f"{path.name} has a price row in its spec table")

    def test_recipes_carry_a_verification_date(self):
        for path in RECIPES.glob("*.md"):
            if path.stem in ("README", "_TEMPLATE"):
                continue
            with self.subTest(recipe=path.name):
                self.assertRegex(path.read_text(encoding="utf-8"),
                                 r"\|\s*Verified\s*\|\s*20\d\d-\d\d-\d\d",
                                 f"{path.name} has no Verified date")


if __name__ == "__main__":
    unittest.main()
