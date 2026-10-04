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


class RepeatIngestCase(IngestionCase):
    """Helpers for the repeat-ingest rules: the file's identity is its bytes, and
    a row remembers which source it came from."""

    def perf_path(self):
        return self.ws / "socialforge" / "output" / "acme" / "2026-07" / "performance.json"

    def perf(self):
        return json.loads(self.perf_path().read_text(encoding="utf-8"))

    def ingest_as(self, name, csv_text, label, *extra):
        path = self.ws / name
        path.write_text(csv_text, encoding="utf-8")
        return run("--action", "ingest", "--brand", "acme", "--month", "2026-07",
                   "--csv", str(path), "--source", label, *extra, workspace=self.ws)


class TestIdempotentIngest(RepeatIngestCase):
    EXPORT = "post_id,impressions,likes,comments,shares\nP01,2000,150,30,20\nP02,4000,80,20,20\n"

    def test_the_same_file_twice_is_a_noop_that_names_the_earlier_source(self):
        code, _ = self.ingest_as("wk1.csv", self.EXPORT, "wk1.csv")
        self.assertEqual(code, 0)
        before = self.perf_path().read_bytes()
        code, out = self.ingest_as("wk1.csv", self.EXPORT, "wk1.csv")
        self.assertEqual(code, 0, "a repeat is not an error")
        d = json.loads(out)
        self.assertEqual(d["status"], "already_ingested")
        self.assertEqual(d["earlier_source"]["label"], "wk1.csv")
        self.assertEqual(self.perf_path().read_bytes(), before,
                         "an already-ingested file must not touch performance.json at all")
        self.assertEqual(len(self.perf()["posts"]["P01"]), 1)

    def test_identical_bytes_under_another_label_are_still_the_same_export(self):
        self.ingest_as("a.csv", self.EXPORT, "label-a")
        code, out = self.ingest_as("b.csv", self.EXPORT, "label-b")
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertEqual(d["status"], "already_ingested")
        self.assertEqual(d["earlier_source"]["label"], "label-a")
        self.assertEqual(len(self.perf()["posts"]["P01"]), 1,
                         "a new file name must not launder the same numbers into a double count")

    def test_a_replace_of_identical_bytes_is_also_a_noop(self):
        self.ingest_as("a.csv", self.EXPORT, "mtd", "--replace")
        code, out = self.ingest_as("a.csv", self.EXPORT, "mtd", "--replace")
        self.assertEqual(json.loads(out)["status"], "already_ingested")
        self.assertEqual(len(self.perf()["sources"]), 1)

    def test_a_changed_file_is_a_different_export_and_appends(self):
        self.ingest_as("wk1.csv", self.EXPORT, "wk1.csv")
        code, out = self.ingest_as("wk2.csv", self.EXPORT + "P03,3000,60,15,15\n", "wk2.csv")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["status"], "success")
        perf = self.perf()
        self.assertEqual(len(perf["posts"]["P01"]), 2, "different files append; that is how "
                         "one CSV per platform is combined")
        self.assertEqual(len(perf["sources"]), 2)

    def test_the_source_records_the_sha256_of_the_csv_bytes(self):
        import hashlib
        self.ingest_as("wk1.csv", self.EXPORT, "wk1.csv")
        expected = hashlib.sha256((self.ws / "wk1.csv").read_bytes()).hexdigest()
        self.assertEqual(self.perf()["sources"][0]["sha256"], expected)

    def test_every_stored_row_carries_its_source_label(self):
        self.ingest_as("wk1.csv", self.EXPORT, "linkedin")
        for rows in self.perf()["posts"].values():
            self.assertTrue(all(r["source"] == "linkedin" for r in rows))


class TestReplace(RepeatIngestCase):
    def test_a_cumulative_export_under_a_constant_label_keeps_only_the_latest_snapshot(self):
        self.ingest_as("w1.csv", "post_id,impressions,likes\nP01,1000,50\nP02,900,20\n",
                       "linkedin-mtd", "--replace")
        code, out = self.ingest_as("w2.csv", "post_id,impressions,likes\nP01,2400,150\n"
                                   "P02,2100,60\nP03,800,10\n", "linkedin-mtd", "--replace")
        self.assertEqual(code, 0, out)
        d = json.loads(out)
        self.assertEqual(d["replaced"], {"rows_removed": 2, "sources_removed": 1})
        perf = self.perf()
        self.assertEqual([r["impressions"] for r in perf["posts"]["P01"]], [2400])
        self.assertEqual([r["impressions"] for r in perf["posts"]["P02"]], [2100])
        self.assertIn("P03", perf["posts"])
        self.assertEqual([s["label"] for s in perf["sources"]], ["linkedin-mtd"])

    def test_replace_removes_posts_that_the_new_snapshot_no_longer_contains(self):
        self.ingest_as("w1.csv", "post_id,impressions,likes\nP01,1000,50\nP02,900,20\n", "mtd")
        self.ingest_as("w2.csv", "post_id,impressions,likes\nP01,1500,60\n", "mtd", "--replace")
        self.assertEqual(set(self.perf()["posts"]), {"P01"},
                         "a post absent from the latest snapshot must not linger from the old one")

    def test_replace_touches_only_its_own_label(self):
        self.ingest_as("li1.csv", "post_id,impressions,likes\nP01,1000,50\n", "linkedin")
        self.ingest_as("ig1.csv", "post_id,impressions,likes\nP01,500,40\nP02,700,10\n", "instagram")
        self.ingest_as("li2.csv", "post_id,impressions,likes\nP01,1800,90\n", "linkedin", "--replace")
        perf = self.perf()
        by_source = {r["source"]: r["impressions"] for r in perf["posts"]["P01"]}
        self.assertEqual(by_source, {"linkedin": 1800, "instagram": 500})
        self.assertEqual([r["source"] for r in perf["posts"]["P02"]], ["instagram"])
        self.assertEqual(sorted(s["label"] for s in perf["sources"]), ["instagram", "linkedin"])

    def test_replace_without_prior_rows_just_ingests(self):
        code, out = self.ingest_as("w1.csv", "post_id,impressions,likes\nP01,1000,50\n",
                                   "mtd", "--replace")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["replaced"], {"rows_removed": 0, "sources_removed": 0})

    def test_a_replace_that_matches_nothing_leaves_the_old_snapshot_alone(self):
        self.ingest_as("w1.csv", "post_id,impressions,likes\nP01,1000,50\n", "mtd")
        before = self.perf_path().read_bytes()
        code, out = self.ingest_as("w2.csv", "post_id,impressions,likes\nX99,5,1\n", "mtd",
                                   "--replace")
        self.assertEqual(code, 3)
        self.assertEqual(self.perf_path().read_bytes(), before,
                         "a failed replace must not delete the snapshot it was meant to refresh")

    def test_replace_is_not_valid_for_the_wins_action(self):
        self.ingest_as("w1.csv", "post_id,impressions,likes\nP01,1000,50\n", "mtd")
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "ingest_performance.py"), "--action", "wins",
             "--brand", "acme", "--month", "2026-07", "--replace"],
            capture_output=True, text=True, timeout=60,
            env=dict(os.environ, CLAUDE_PLUGIN_DATA=str(self.ws)))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--replace", proc.stderr)

    def test_an_older_cumulative_file_replaces_a_newer_snapshot_which_the_docs_warn_about(self):
        """The script cannot tell which file is newer — --replace trusts what it is
        given, and a replaced file's hash is no longer on record. So the recipes and
        the skill say: under --replace, ingest only the newest export. If the script
        ever learns to refuse a stale file, this test and those warnings change."""
        week1 = "post_id,impressions,likes\nP01,1000,50\n"
        week2 = "post_id,impressions,likes\nP01,2400,150\n"
        self.ingest_as("w1.csv", week1, "mtd", "--replace")
        self.ingest_as("w2.csv", week2, "mtd", "--replace")
        code, out = self.ingest_as("w1.csv", week1, "mtd", "--replace")
        self.assertEqual(json.loads(out)["status"], "success",
                         "week 1's hash was dropped when week 2 replaced it, so it ingests again")
        self.assertEqual([r["impressions"] for r in self.perf()["posts"]["P01"]], [1000],
                         "the stale file replaced the newer snapshot")
        recipes = (REPO / "docs" / "ALWAYS-ON-RECIPES.md").read_text(encoding="utf-8")
        skill = (REPO / "skills" / "ingest-performance" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("ONLY its newest file", recipes)
        self.assertIn("only the newest file", recipes)
        self.assertIn("**newest** export", skill)

    def test_wins_count_the_replaced_snapshot_once(self):
        """The reason --replace exists: stacked cumulative snapshots inflate a post's
        impressions and quietly change which post wins."""
        self.ingest_as("w1.csv", "post_id,impressions,likes,comments,shares\n"
                       "P01,2000,100,20,10\nP02,4000,80,20,20\nP03,3000,60,15,15\n",
                       "mtd", "--replace")
        self.ingest_as("w2.csv", "post_id,impressions,likes,comments,shares\n"
                       "P01,2100,110,22,11\nP02,4100,82,21,21\nP03,3100,61,16,16\n",
                       "mtd", "--replace")
        code, out = run("--action", "wins", "--brand", "acme", "--month", "2026-07",
                        workspace=self.ws)
        d = json.loads(out)
        impressions = {w["post_id"]: w["impressions"] for w in d["winners"]}
        impressions.update({u["post_id"]: u["impressions"] for u in d["unranked"]})
        self.assertEqual(impressions.get("P01"), 2100,
                         "P01's impressions must be week 2's 2100, not 2000 + 2100")


class TestLegacyPerformanceFiles(RepeatIngestCase):
    """performance.json files written before rows carried a source label and
    sources carried a sha256 must keep working."""

    def write_legacy(self):
        legacy = {"brand": "acme", "month": "2026-07", "basis": "platform-export",
                  "sources": [{"label": "old.csv", "ingested_at": "2026-07-31T00:00:00+00:00",
                               "rows_matched": 2, "rows_unmatched": 0}],
                  "posts": {"P01": [{"platform": "linkedin", "impressions": 2000, "likes": 150,
                                     "comments": 30, "shares": 20}],
                            "P02": [{"platform": "linkedin", "impressions": 4000, "likes": 80,
                                     "comments": 20, "shares": 20}]}}
        self.perf_path().write_text(json.dumps(legacy), encoding="utf-8")

    def test_wins_reads_a_legacy_file(self):
        self.write_legacy()
        code, out = run("--action", "wins", "--brand", "acme", "--month", "2026-07",
                        workspace=self.ws)
        self.assertEqual(code, 0)
        self.assertIn(json.loads(out)["status"], ("clear_wins", "no_clear_wins"))

    def test_a_new_ingest_appends_beside_legacy_rows(self):
        self.write_legacy()
        code, out = self.ingest_as("new.csv", "post_id,impressions,likes\nP03,900,30\n", "new.csv")
        self.assertEqual(code, 0, out)
        perf = self.perf()
        self.assertEqual(set(perf["posts"]), {"P01", "P02", "P03"})
        self.assertNotIn("source", perf["posts"]["P01"][0], "legacy rows are left as they were")
        self.assertEqual([s["label"] for s in perf["sources"]], ["old.csv", "new.csv"])

    def test_replace_refuses_a_label_it_cannot_isolate(self):
        self.write_legacy()
        before = self.perf_path().read_bytes()
        code, out = self.ingest_as("old.csv", "post_id,impressions,likes\nP01,2500,200\n",
                                   "old.csv", "--replace")
        self.assertEqual(code, 1)
        self.assertIn("cannot isolate", json.loads(out)["error"])
        self.assertEqual(self.perf_path().read_bytes(), before,
                         "refusing means touching nothing — never guess which legacy rows to drop")

    def test_replace_works_for_a_fresh_label_in_a_legacy_month(self):
        self.write_legacy()
        code, out = self.ingest_as("m.csv", "post_id,impressions,likes\nP03,900,30\n", "mtd",
                                   "--replace")
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.perf()["posts"]["P01"]), 1)


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

    def test_ingest_performance_skill_describes_idempotence_and_replace(self):
        skill = (REPO / "skills" / "ingest-performance" / "SKILL.md").read_text(encoding="utf-8")
        for token in ("already_ingested", "--replace", "sha256", "constant"):
            self.assertIn(token, skill, f"the skill does not mention `{token}`")
        self.assertNotIn("repeat ingests append", skill,
                         "the skill still describes the old double-counting behavior")

    def test_finalize_month_hands_off_to_ingestion(self):
        skill = (REPO / "skills" / "finalize-month" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("ingest-performance", skill)


if __name__ == "__main__":
    unittest.main()
