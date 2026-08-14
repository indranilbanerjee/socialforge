""""Nothing fails silently" was true of the code designed for it, and false at the seams.

A full-pipeline run with no image or video credentials found the claim holding
exactly where the plugin had thought about it — the provider chain, the price
book, the compliance gate, the asset matcher all refused honestly with named
reasons — and breaking in three places nobody had brought into the discipline:

  1. `render_preview.py` returned {"status": "success"} for an image path that
     did not exist. It wrote a real 600x800 PNG that was blank white, because
     the missing path became a file:// URI and the browser rendered a broken
     image as nothing. A reviewer approving that gallery approves a blank
     rectangle. This is the precise failure mode the plugin claims is impossible.
  2. `generate_image.py` exited 0 after every provider failed. Any `&&` chain,
     CI step, or batch loop read total failure as success — while price_book.py
     exits 3 and compliance_check.py exits 1 in the same situation, so the
     contract was inconsistent inside one plugin.
  3. `provider_failures.py` built an excellent structured record and never wrote
     it anywhere. Once stdout scrolled past, the record was gone. A record
     nobody can read afterwards is not a record.

Plus two that only bite in the no-credentials case, which is the case under test:
`cost_tracker.py --action report` raised TypeError on an unpriced entry, and
price/model lookups read a different env var than everything else, resolving to
a different workspace than costs were written to.

Stdlib only.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestPreviewRefusesToInventSuccess(unittest.TestCase):
    def _run(self, extra_args, out_name):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / out_name
            cmd = [sys.executable, str(SCRIPTS / "render_preview.py"),
                   "--image", str(Path(td) / "does-not-exist.png"),
                   "--copy", "some post copy",
                   "--platform", "linkedin", "--brand", "t",
                   "--output", str(out)] + extra_args
            p = subprocess.run(cmd, capture_output=True, text=True,
                               encoding="utf-8", timeout=180)
            return p, out

    def test_missing_image_is_refused_not_rendered(self):
        p, out = self._run([], "p.png")
        self.assertNotEqual(p.returncode, 0,
                            "a failed render must not exit 0 — callers chain on $?")
        payload = json.loads(p.stdout)
        self.assertEqual(payload["status"], "FAILED")
        self.assertEqual(payload["reason"], "missing-image")
        self.assertTrue(payload["next_steps"], "a refusal must say what to do next")
        self.assertFalse(out.exists(),
                         "no preview file may be written for an image that does not exist")

    def test_explicit_opt_in_is_placeholder_never_success(self):
        """There is a legitimate use for a copy-layout preview. It must still be
        impossible to mistake for a finished creative by reading one field."""
        p, _ = self._run(["--allow-missing-image"], "q.png")
        payload = json.loads(p.stdout)
        self.assertEqual(payload["status"], "placeholder")
        self.assertNotEqual(payload["status"], "success")
        self.assertIn("warning", payload)


class TestFailureRecordsSurviveTheTerminal(unittest.TestCase):
    def test_failure_payload_is_written_to_disk(self):
        pf = _load("sf_provider_failures", "provider_failures.py")
        with tempfile.TemporaryDirectory() as td:
            os.environ["CLAUDE_PLUGIN_DATA"] = td
            try:
                attempts = []
                pf.record(attempts, "gemini", "credentials", "no-credentials", "no key")
                pf.record(attempts, "wavespeed", "credentials", "no-credentials", "no key")
                payload = pf.failure_payload(attempts, context="image generation")
                log = Path(td) / "socialforge" / "shared" / "failure-log.jsonl"
                self.assertTrue(log.is_file(), "the record must outlive stdout")
                written = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[-1])
                self.assertEqual(written["status"], "FAILED")
                self.assertEqual(written["providers_tried"], ["gemini", "wavespeed"])
                self.assertIn("logged_at", written)
                self.assertEqual(written["attempts"], payload["attempts"])
            finally:
                os.environ.pop("CLAUDE_PLUGIN_DATA", None)

    def test_logging_failure_never_masks_the_provider_failure(self):
        """The record is a convenience; the returned payload is the product. If
        the log cannot be written the caller must still get the real error."""
        pf = _load("sf_provider_failures_2", "provider_failures.py")
        # Point at a FILE, so mkdir on a subdirectory of it must fail.
        os.environ["CLAUDE_PLUGIN_DATA"] = str(Path(__file__))
        try:
            attempts = []
            pf.record(attempts, "gemini", "credentials", "no-credentials", "x")
            payload = pf.failure_payload(attempts)
            self.assertEqual(payload["status"], "FAILED")
            self.assertEqual(payload["providers_tried"], ["gemini"])
        finally:
            os.environ.pop("CLAUDE_PLUGIN_DATA", None)


class TestUnpricedIsNotFree(unittest.TestCase):
    """`--action report` crashed with TypeError as soon as any entry carried
    cost_usd: None — and an unpriced entry is exactly what a run without
    credentials produces, so the cost report broke in the scenario it was most
    needed for."""

    def _report(self, entries):
        with tempfile.TemporaryDirectory() as td:
            os.environ["CLAUDE_PLUGIN_DATA"] = td
            try:
                # WORKSPACE is resolved at import time, so load AFTER setting it.
                ct = _load("sf_cost_tracker_" + str(len(entries)), "cost_tracker.py")
                log = (Path(td) / "socialforge" / "output" / "b" / "2026-09")
                log.mkdir(parents=True, exist_ok=True)
                (log / "cost-log.json").write_text(json.dumps({
                    "total_cost_usd": 0.0, "entries": entries}), encoding="utf-8")
                import io
                from contextlib import redirect_stdout
                buf = io.StringIO()
                with redirect_stdout(buf):
                    ct.get_report("b", "2026-09")
                return json.loads(buf.getvalue())
            finally:
                os.environ.pop("CLAUDE_PLUGIN_DATA", None)

    def test_report_survives_an_unpriced_entry(self):
        out = self._report([
            {"operation": "image", "post_id": "P01", "cost_usd": 0.03},
            {"operation": "video", "post_id": "P02", "cost_usd": None},
        ])
        self.assertEqual(out["unpriced_calls"], 1)
        self.assertFalse(out["totals_complete"])
        self.assertIn("LOWER BOUND", out["note"])

    def test_a_complete_report_says_so(self):
        out = self._report([{"operation": "image", "post_id": "P01", "cost_usd": 0.03}])
        self.assertEqual(out["unpriced_calls"], 0)
        self.assertTrue(out["totals_complete"])
        self.assertIsNone(out["note"])


class TestWorkspaceResolutionIsConsistent(unittest.TestCase):
    """price_book and model_book read CLAUDE_PLUGIN_DATA_DIR while every other
    script read CLAUDE_PLUGIN_DATA, so a price the user recorded was invisible
    to the tracker that needed it."""

    def test_all_scripts_accept_the_canonical_env_var(self):
        offenders = []
        for f in SCRIPTS.glob("*.py"):
            text = f.read_text(encoding="utf-8", errors="replace")
            if "CLAUDE_PLUGIN_DATA_DIR" in text and 'get("CLAUDE_PLUGIN_DATA")' not in text:
                offenders.append(f.name)
        self.assertEqual(offenders, [],
                         f"these read only the legacy env var name: {offenders}")


class TestSetupQuotesNoPricesFromMemory(unittest.TestCase):
    """The plugin's own price-check rule is "never state a cost you did not look
    up in this session or the last 24 hours", and price_book.py enforces it by
    refusing to quote an unrecorded price. The setup skill was quoting six
    figures from memory anyway — per-image cost, per-second video cost, two
    worked video examples, and two promotional credit amounts."""

    SETUP = REPO / "skills" / "setup" / "SKILL.md"

    def test_no_dollar_amounts_in_the_setup_skill(self):
        import re
        text = self.SETUP.read_text(encoding="utf-8")
        hits = re.findall(r"\$\s?\d[\d,.]*", text)
        self.assertEqual(hits, [],
                         f"setup states prices from memory: {hits}. Route the user to "
                         "price_book.py, which refuses rather than guesses.")

    def test_no_promotional_credit_amounts(self):
        import re
        text = self.SETUP.read_text(encoding="utf-8")
        hits = re.findall(r"\b\d+\s+free credits\b", text, re.I)
        self.assertEqual(hits, [], f"promotional amounts quoted from memory: {hits}")


if __name__ == "__main__":
    unittest.main()
