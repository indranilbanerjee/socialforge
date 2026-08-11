"""The price book must never invent a number.

SocialForge previously priced work from a hardcoded table keyed by *operation*,
so every video clip billed the same regardless of length, and the 57-model
registry carried no prices at all. These tests pin the replacement's core
promise: a price exists only if a live lookup put it there, with a source, and
recently enough to still be true.

Everything here runs against a throwaway workspace — no test may touch the
user's real price book.

Stdlib only.
"""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

SRC = "https://wavespeed.ai/pricing"


class PriceBookCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["CLAUDE_PLUGIN_DATA_DIR"] = self._tmp.name
        import price_book
        self.pb = importlib.reload(price_book)
        self.assertIn(self._tmp.name, str(self.pb.PRICE_BOOK),
                      "test would have written to the real workspace")

    def tearDown(self):
        os.environ.pop("CLAUDE_PLUGIN_DATA_DIR", None)
        self._tmp.cleanup()


class TestProvenanceIsMandatory(PriceBookCase):
    def test_record_rejects_a_price_with_no_source(self):
        for bad in ("", "trust me", "the docs", "wavespeed.ai"):
            with self.subTest(source=bad):
                with self.assertRaises(ValueError):
                    self.pb.record("kling-3.0-std", "wavespeed", "second", 0.084, bad)

    def test_record_accepts_a_real_url(self):
        entry = self.pb.record("kling-3.0-std", "wavespeed", "second", 0.084, SRC)
        self.assertEqual(entry["source"], SRC)
        self.assertIn("fetched_at", entry)

    def test_rejects_bad_unit_and_negative_price(self):
        with self.assertRaises(ValueError):
            self.pb.record("m", "wavespeed", "per-frame", 0.01, SRC)
        with self.assertRaises(ValueError):
            self.pb.record("m", "wavespeed", "second", -1, SRC)


class TestRefusesToGuess(PriceBookCase):
    def test_quote_for_unknown_model_is_not_quotable(self):
        q = self.pb.quote("never-heard-of-it", "wavespeed", 10)
        self.assertFalse(q["quotable"])
        self.assertEqual(q["status"], "unknown")
        self.assertIn("action_required", q)

    def test_unknown_quote_carries_no_number(self):
        """The failure mode that matters: a caller must not be able to read a
        cost off a refusal."""
        q = self.pb.quote("never-heard-of-it", "wavespeed", 10)
        for field in ("total_usd", "unit_price_usd"):
            self.assertNotIn(field, q, f"a refusal leaked a {field}")

    def test_unknown_names_where_to_look(self):
        q = self.pb.quote("mystery", "wavespeed", 1)
        self.assertEqual(q.get("lookup_url"), "https://wavespeed.ai/pricing")

    def test_provider_that_blocks_fetching_says_so(self):
        """Kie AI returns 403 to automated fetches — measured. A lookup must not
        report that as 'no price exists'."""
        q = self.pb.quote("anything", "kie", 1)
        self.assertIn("lookup_note", q)
        self.assertFalse(self.pb.PROVIDERS["kie"]["fetchable"])


class TestStaleness(PriceBookCase):
    def _age_entry(self, model, provider, hours):
        book = json.loads(self.pb.PRICE_BOOK.read_text(encoding="utf-8"))
        key = self.pb._key(model, provider)
        old = datetime.now(timezone.utc) - timedelta(hours=hours)
        book["entries"][key]["fetched_at"] = old.isoformat()
        self.pb.PRICE_BOOK.write_text(json.dumps(book), encoding="utf-8")

    def test_fresh_price_quotes(self):
        self.pb.record("kling-3.0-std", "wavespeed", "second", 0.084, SRC)
        q = self.pb.quote("kling-3.0-std", "wavespeed", 55)
        self.assertTrue(q["quotable"])
        self.assertAlmostEqual(q["total_usd"], 4.62, places=4)

    def test_price_past_the_window_goes_stale_and_stops_quoting(self):
        self.pb.record("kling-3.0-std", "wavespeed", "second", 0.084, SRC)
        self._age_entry("kling-3.0-std", "wavespeed", 48)
        q = self.pb.quote("kling-3.0-std", "wavespeed", 55)
        self.assertEqual(q["status"], "stale")
        self.assertFalse(q["quotable"])
        self.assertIsNone(q.get("total_usd"))

    def test_staleness_report_counts_correctly(self):
        self.pb.record("a-model", "wavespeed", "second", 0.05, SRC)
        self.pb.record("b-model", "wavespeed", "second", 0.06, SRC)
        self._age_entry("b-model", "wavespeed", 100)
        rep = self.pb.staleness_report()
        self.assertEqual(rep["total"], 2)
        self.assertEqual(rep["fresh"], 1)
        self.assertEqual(rep["stale"], 1)


class TestModelProviderKeying(PriceBookCase):
    def test_same_model_holds_a_separate_price_per_provider(self):
        """The observed case: Seedance 2.0 Fast at $0.10/s on one provider and
        $0.24/s on another. One global price per model is wrong somewhere."""
        self.pb.record("seedance-2.0-fast", "wavespeed", "second", 0.10, SRC)
        self.pb.record("seedance-2.0-fast", "fal", "second", 0.24, "https://fal.ai/pricing")
        self.assertAlmostEqual(
            self.pb.quote("seedance-2.0-fast", "wavespeed", 10)["total_usd"], 1.0, places=4)
        self.assertAlmostEqual(
            self.pb.quote("seedance-2.0-fast", "fal", 10)["total_usd"], 2.4, places=4)

    def test_compare_orders_cheapest_first(self):
        self.pb.record("seedance-2.0-fast", "fal", "second", 0.24, "https://fal.ai/pricing")
        self.pb.record("seedance-2.0-fast", "wavespeed", "second", 0.10, SRC)
        rows = self.pb.compare("seedance-2.0-fast")["by_unit"]["second"]
        self.assertEqual([r["provider"] for r in rows], ["wavespeed", "fal"])

    def test_compare_never_ranks_across_different_units(self):
        """A per-image price is not 'cheaper' than a per-second one."""
        self.pb.record("thing", "wavespeed", "image", 0.005, SRC)
        self.pb.record("thing", "fal", "second", 0.05, "https://fal.ai/pricing")
        by_unit = self.pb.compare("thing")["by_unit"]
        self.assertEqual(set(by_unit), {"image", "second"})
        for rows in by_unit.values():
            self.assertEqual(len(rows), 1)

    def test_single_provider_is_flagged_as_not_a_comparison(self):
        self.pb.record("lonely", "wavespeed", "second", 0.09, SRC)
        self.assertIn("note", self.pb.compare("lonely"))

    def test_alias_folding_unifies_provider_spellings(self):
        """Google, fal.ai and WaveSpeed each spell Nano Banana differently."""
        self.assertEqual(self.pb.normalise("gemini-3.1-flash-image-preview"), "nano-banana-2")
        self.assertEqual(self.pb.normalise("fal-ai/nano-banana"), "nano-banana")
        self.assertEqual(self.pb.normalise("Nano Banana 2"), "nano-banana-2")
        self.assertEqual(self.pb.normalise("  KLING-3.0-STD  "), "kling-3.0-std")


class TestBatchGate(PriceBookCase):
    def setUp(self):
        super().setUp()
        self.pb.record("kling-3.0-std", "wavespeed", "second", 0.084, SRC)

    def test_one_unpriced_item_blocks_the_whole_batch(self):
        out = self.pb.quote_batch([
            {"model": "kling-3.0-std", "provider": "wavespeed", "units": 5, "label": "a"},
            {"model": "not-priced", "provider": "wavespeed", "units": 5, "label": "b"},
        ])
        self.assertEqual(out["blocked"], 1)
        self.assertIsNone(out["total_usd"],
                          "a partial total must never be presented as the run cost")
        self.assertFalse(out["approved_to_run"])

    def test_fully_priced_batch_totals_correctly(self):
        out = self.pb.quote_batch([
            {"model": "kling-3.0-std", "provider": "wavespeed", "units": 5},
            {"model": "kling-3.0-std", "provider": "wavespeed", "units": 10},
        ])
        self.assertEqual(out["blocked"], 0)
        self.assertAlmostEqual(out["total_usd"], 1.26, places=4)

    def test_a_quote_is_never_an_approval(self):
        """Even a clean, fully-priced batch must not mark itself runnable."""
        out = self.pb.quote_batch(
            [{"model": "kling-3.0-std", "provider": "wavespeed", "units": 5}])
        self.assertFalse(out["approved_to_run"])
        self.assertIn("not consent", out["action_required"])


class TestCliContract(PriceBookCase):
    def _run(self, *args):
        env = dict(os.environ, CLAUDE_PLUGIN_DATA_DIR=self._tmp.name)
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "price_book.py"), *args],
            capture_output=True, text=True, env=env)

    def test_unquotable_exits_nonzero(self):
        """A caller must not be able to mistake a refusal for a priced run."""
        r = self._run("--action", "quote", "--model", "nope",
                      "--provider", "wavespeed", "--units", "5")
        self.assertEqual(r.returncode, 3)
        self.assertFalse(json.loads(r.stdout)["quotable"])

    def test_quote_exits_zero_when_priced(self):
        self.pb.record("kling-3.0-std", "wavespeed", "second", 0.084, SRC)
        r = self._run("--action", "quote", "--model", "kling-3.0-std",
                      "--provider", "wavespeed", "--units", "5")
        self.assertEqual(r.returncode, 0)
        self.assertTrue(json.loads(r.stdout)["quotable"])

    def test_batch_with_blocked_items_exits_nonzero(self):
        r = self._run("--action", "quote-batch", "--items",
                      '[{"model":"nope","provider":"wavespeed","units":5}]')
        self.assertEqual(r.returncode, 3)

    def test_providers_action_lists_auth_shape_per_provider(self):
        """Three providers, three different auth headers — the single thing that
        most often breaks a first integration."""
        r = self._run("--action", "providers")
        self.assertEqual(r.returncode, 0)
        provs = json.loads(r.stdout)
        for name in ("wavespeed", "fal", "vertex", "kie"):
            self.assertIn(name, provs)
            self.assertTrue(provs[name]["auth"], f"{name} has no auth shape documented")
            self.assertTrue(provs[name]["pricing_url"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()
