"""The wins rung feeds from measured numbers — with honest limits.

ideate-month compounds "what worked last month". ingest_performance.py is the
measured path for that rung, and its doctrine mirrors the suite's measurement
ladder: unmeasured is never zero, small samples are never ranked, a flat month
says "no clear wins" instead of crowning noise, and unmatched CSV rows are
listed rather than silently dropped. These tests execute the script against a
throwaway workspace and pin each of those behaviors, plus the skill wiring
that makes ideate-month read the measured path first.
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
SCRIPTS = REPO / "scripts"

CALENDAR = {"posts": [
    {"post_id": "P01", "date": "2026-07-02", "tier": "HUB", "pillar": "ops",
     "topic": "5 reporting mistakes", "platforms": ["linkedin"], "content_type": "carousel"},
    {"post_id": "P02", "date": "2026-07-09", "tier": "HERO", "pillar": "ops",
     "topic": "case study teardown", "platforms": ["linkedin"], "content_type": "video"},
    {"post_id": "P03", "date": "2026-07-16", "tier": "HYGIENE", "pillar": "culture",
     "topic": "team ritual", "platforms": ["instagram"], "content_type": "static"},
]}


def run(*args, workspace, stdin=None):
    env = dict(os.environ)
    env["CLAUDE_PLUGIN_DATA"] = str(workspace)
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "ingest_performance.py"), *args],
        capture_output=True, text=True, env=env, input=stdin, timeout=60)
    return proc.returncode, proc.stdout


class IngestionCase(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())
        month = self.ws / "socialforge" / "output" / "acme" / "2026-07"
        month.mkdir(parents=True)
        (month / "calendar-data.json").write_text(json.dumps(CALENDAR), encoding="utf-8")
        self.csv_path = self.ws / "export.csv"

    def ingest_csv(self, csv_text):
        self.csv_path.write_text(csv_text, encoding="utf-8")
        return run("--action", "ingest", "--brand", "acme", "--month", "2026-07",
                   "--csv", str(self.csv_path), "--source", "test-export",
                   workspace=self.ws)


class TestIngest(IngestionCase):
    def test_header_aliases_and_unmatched_rows_are_named(self):
        code, out = self.ingest_csv(
            "Post,Views,Reactions,Comments,Shares\n"
            "p01,2000,80,12,8\n"
            "P02,4000,60,5,3\n"
            "P77,100,1,0,0\n")
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertEqual(d["rows_matched"], 2)  # p01 case-folded, P77 unmatched
        self.assertEqual(d["unmatched_row_ids"], ["P77"],
                         "unmatched rows must be NAMED, never silently dropped")
        perf = json.loads((self.ws / "socialforge" / "output" / "acme" / "2026-07" /
                           "performance.json").read_text(encoding="utf-8"))
        self.assertEqual(perf["basis"], "platform-export")
        self.assertIn("P01", perf["posts"])

    def test_nothing_matched_is_exit_3_not_a_quiet_success(self):
        code, out = self.ingest_csv("Post,Views\nX01,50\n")
        self.assertEqual(code, 3)
        self.assertIn("calendar_post_ids", json.loads(out))

    def test_unrecognizable_id_column_fails_with_the_headers_it_saw(self):
        code, out = self.ingest_csv("Caption,Views\nhello,50\n")
        self.assertEqual(code, 1)
        self.assertIn("seen_headers", json.loads(out))


class TestWins(IngestionCase):
    def test_clear_win_carries_margin_and_calendar_context(self):
        self.ingest_csv(
            "post_id,impressions,likes,comments,shares\n"
            "P01,2000,150,30,20\n"   # 10% ER — the clear win
            "P02,4000,80,20,20\n"    # 3% ER
            "P03,3000,60,15,15\n")   # 3% ER
        code, out = run("--action", "wins", "--brand", "acme", "--month", "2026-07",
                        workspace=self.ws)
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertEqual(d["status"], "clear_wins")
        top = d["winners"][0]
        self.assertEqual(top["post_id"], "P01")
        self.assertEqual(top["topic"], "5 reporting mistakes",
                         "winners must carry calendar context — ideation compounds "
                         "the topic and pillar, not a bare id")
        self.assertIn("x", top["vs_month_median"])

    def test_flat_month_says_no_clear_wins(self):
        self.ingest_csv(
            "post_id,impressions,likes,comments,shares\n"
            "P01,2000,40,10,10\n"    # 3% — all identical
            "P02,4000,80,20,20\n"
            "P03,3000,60,15,15\n")
        code, out = run("--action", "wins", "--brand", "acme", "--month", "2026-07",
                        workspace=self.ws)
        d = json.loads(out)
        self.assertEqual(d["status"], "no_clear_wins",
                         "a flat month must not crown noise as a win")
        self.assertFalse(d["winners"])
        self.assertIn("flat", d["note"])

    def test_sample_floor_keeps_noise_out_of_the_ranking(self):
        self.ingest_csv(
            "post_id,impressions,likes,comments,shares\n"
            "P01,40,20,10,10\n"      # 100% ER on 40 impressions — noise
            "P02,4000,80,20,20\n"
            "P03,3000,60,15,15\n")
        code, out = run("--action", "wins", "--brand", "acme", "--month", "2026-07",
                        workspace=self.ws)
        d = json.loads(out)
        winner_ids = [w["post_id"] for w in d["winners"]]
        self.assertNotIn("P01", winner_ids,
                         "a below-floor post must never rank, whatever its rate")
        unranked = {u["post_id"]: u for u in d["unranked"]}
        self.assertIn("P01", unranked)
        self.assertIn("sample floor", unranked["P01"]["unranked_reason"])

    def test_unmeasured_is_not_zero(self):
        self.ingest_csv(
            "post_id,impressions,likes,comments,shares\n"
            "P01,,150,30,20\n"       # no impressions -> unmeasurable, NOT 0%
            "P02,4000,80,20,20\n"
            "P03,3000,60,15,15\n")
        code, out = run("--action", "wins", "--brand", "acme", "--month", "2026-07",
                        workspace=self.ws)
        d = json.loads(out)
        unranked = {u["post_id"]: u for u in d["unranked"]}
        self.assertIn("P01", unranked)
        self.assertIsNone(unranked["P01"]["engagement_rate"],
                          "missing impressions must yield rate=None, never 0.0")

    def test_no_data_directs_to_ingest_and_labels_the_alternative_anecdotal(self):
        code, out = run("--action", "wins", "--brand", "acme", "--month", "2026-07",
                        workspace=self.ws)
        self.assertEqual(code, 1)
        d = json.loads(out)
        self.assertEqual(d["status"], "no_data")
        self.assertIn("anecdotal", d["note"])


class TestSkillWiring(unittest.TestCase):
    def test_ideate_month_reads_the_measured_path_first(self):
        skill = (REPO / "skills" / "ideate-month" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("ingest_performance.py --action wins", skill)
        self.assertIn("no_clear_wins", skill)
        self.assertIn("anecdotal", skill)
        # The output contract labels the basis of every win
        self.assertIn("measured", skill)

    def test_ingest_performance_skill_exists_with_the_honesty_rules(self):
        skill = (REPO / "skills" / "ingest-performance" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("never silently dropped", skill)
        self.assertIn("Sample floor", skill)
        self.assertIn("no_clear_wins", skill)

    def test_finalize_month_hands_off_to_ingestion(self):
        skill = (REPO / "skills" / "finalize-month" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("ingest-performance", skill)


if __name__ == "__main__":
    unittest.main()
