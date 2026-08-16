"""The month-delivery auditor: the ledger's claims vs the disk.

Follows the suite-wide run-audit pattern. Each plant reproduces a
failure class this plugin has already met once: ghost posts minted from typos,
"FINAL " frozen in a bucket no transition table knows, a bypassed gate buried
as a JSON flag, an approved gallery whose image was an empty file, a failure
record nobody could load, a cost total that silently pretended to be complete.
Stdlib only.
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
AUDIT = REPO / "scripts" / "delivery_audit.py"


class Fixture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)
        self.month_dir = self.ws / "socialforge" / "output" / "acme" / "2026-08"
        self.month_dir.mkdir(parents=True)
        self.asset = self.month_dir / "post-001-image.png"
        self.asset.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 128)
        self._write_calendar()
        self._write_tracker()

    def tearDown(self):
        self._tmp.cleanup()

    def _write_calendar(self, posts=None):
        posts = posts if posts is not None else [
            {"post_id": "post-001", "platform": "instagram",
             "asset_path": str(self.asset)},
            {"post_id": "post-002", "platform": "linkedin"},
        ]
        (self.month_dir / "calendar-data.json").write_text(
            json.dumps({"posts": posts}), encoding="utf-8")

    def _write_tracker(self, posts=None):
        posts = posts if posts is not None else {
            "post-001": {"status": "FINAL", "flags": [], "revision_history": [
                {"from": "QUEUED", "to": "PENDING_REVIEW", "actor": "t",
                 "timestamp": "2026-08-10T00:00:00Z", "notes": ""},
                {"from": "PENDING_REVIEW", "to": "APPROVED_INTERNAL",
                 "actor": "t", "timestamp": "2026-08-11T00:00:00Z", "notes": ""},
                {"from": "APPROVED_INTERNAL", "to": "FINAL", "actor": "t",
                 "timestamp": "2026-08-12T00:00:00Z", "notes": ""}]},
            "post-002": {"status": "PENDING_REVIEW", "flags": [],
                         "revision_history": [
                {"from": "QUEUED", "to": "PENDING_REVIEW", "actor": "t",
                 "timestamp": "2026-08-10T00:00:00Z", "notes": ""}]},
        }
        (self.month_dir / "status-tracker.json").write_text(
            json.dumps({"posts": posts, "last_updated": "2026-08-12T00:00:00Z"}),
            encoding="utf-8")

    def audit(self, *extra):
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(self.ws))
        proc = subprocess.run(
            [sys.executable, str(AUDIT), "--brand", "acme",
             "--month", "2026-08", *extra],
            capture_output=True, text=True, env=env,
            encoding="utf-8", errors="replace")
        try:
            return proc.returncode, json.loads(proc.stdout)
        except json.JSONDecodeError:
            self.fail(f"non-JSON (exit {proc.returncode}): "
                      f"{proc.stdout[:300]} {proc.stderr[:300]}")


class TestCleanMonth(Fixture):
    def test_clean_month_is_clean(self):
        code, out = self.audit()
        fails = [c for c in out["checks"] if c["result"] == "FAIL"]
        self.assertEqual(code, 0, fails)
        self.assertEqual(out["verdict"], "CLEAN")
        self.assertEqual(out["final_posts"], 1)

    def test_result_written_into_month_folder(self):
        self.audit()
        rec = json.loads((self.month_dir / "delivery-audit.json")
                         .read_text(encoding="utf-8"))
        self.assertEqual(rec["verdict"], "CLEAN")

    def test_no_failure_log_is_na_not_pass(self):
        _, out = self.audit()
        na = [c for c in out["checks"] if c["result"] == "N/A"]
        self.assertTrue(any("failure log" in c["name"] for c in na), na)


class TestPlants(Fixture):
    def test_unknown_status_in_the_ledger(self):
        t = json.loads((self.month_dir / "status-tracker.json")
                       .read_text(encoding="utf-8"))
        t["posts"]["post-002"]["status"] = "FINAL "  # the trailing-space classic
        (self.month_dir / "status-tracker.json").write_text(
            json.dumps(t), encoding="utf-8")
        code, out = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("vocabulary", str(out["checks"]))

    def test_history_that_does_not_land_on_the_status(self):
        t = json.loads((self.month_dir / "status-tracker.json")
                       .read_text(encoding="utf-8"))
        t["posts"]["post-001"]["status"] = "PENDING_CLIENT"  # history says FINAL
        (self.month_dir / "status-tracker.json").write_text(
            json.dumps(t), encoding="utf-8")
        code, out = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("post-001", str(out["checks"]))

    def test_ghost_post(self):
        t = json.loads((self.month_dir / "status-tracker.json")
                       .read_text(encoding="utf-8"))
        t["posts"]["post-999"] = {"status": "QUEUED", "revision_history": []}
        (self.month_dir / "status-tracker.json").write_text(
            json.dumps(t), encoding="utf-8")
        code, out = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("post-999", str(out["checks"]))

    def test_force_finalized_is_surfaced_loudly(self):
        t = json.loads((self.month_dir / "status-tracker.json")
                       .read_text(encoding="utf-8"))
        t["posts"]["post-001"]["force_finalized"] = True
        (self.month_dir / "status-tracker.json").write_text(
            json.dumps(t), encoding="utf-8")
        code, out = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("bypassed", str(out["checks"]))

    def test_final_post_with_empty_asset_file(self):
        """The render_preview lesson: a path that resolves to nothing becomes
        an empty rectangle a client approves."""
        self.asset.write_bytes(b"")
        code, out = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("post-001", str(out["checks"]))

    def test_unreadable_failure_log_line(self):
        shared = self.ws / "socialforge" / "shared"
        shared.mkdir(parents=True, exist_ok=True)
        (shared / "failure-log.jsonl").write_text(
            '{"stage": "provider", "reason": "quota"}\nnot json at all\n',
            encoding="utf-8")
        code, out = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("unreadable", str(out["checks"]))


class TestContractWiring(unittest.TestCase):
    def test_finalize_month_requires_the_audit(self):
        text = (REPO / "skills" / "finalize-month" / "SKILL.md")\
            .read_text(encoding="utf-8")
        self.assertIn("delivery_audit.py", text,
                      "finalize-month never runs the auditor, so the delivery "
                      "claims are still trusted rather than re-derived")


if __name__ == "__main__":
    unittest.main(verbosity=2)
