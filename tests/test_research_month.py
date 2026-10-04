"""research-month's measured halves keep the suite's measurement doctrine.

/socialforge:research-month turns a user's exports into a "what's working" brief.
Its two computed sections come from scripts/research_month.py, which must not
manufacture signal: a flat account has no outliers, a post nobody saw cannot be
one, unmeasured is not zero, a thin or zero baseline declares nothing, and a
comment that repeats a phrase counts once. Excerpts that leave the script are
redacted, and non-ASCII text is not blinded (the failure class an ASCII-only
tokenizer once caused elsewhere in this suite). These tests execute the script
against throwaway CSVs; every one of them was proven to fire by planting its
failure.
"""
from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "research_month.py"
sys.path.insert(0, str(REPO / "scripts"))

import research_month  # noqa: E402


def _csv(rows, fieldnames=None, delimiter=","):
    if not fieldnames:  # ordered union, so a column only some rows carry is still written
        fieldnames = list(dict.fromkeys(k for row in rows for k in row))
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, delimiter=delimiter, restval="")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def _post(i, impressions=1000, eng=30, **extra):
    row = {"post_id": f"p{i}", "date": f"2026-09-{i % 28 + 1:02d}", "impressions": impressions,
           "likes": eng, "comments": 0, "shares": 0, "saves": 0}
    row.update(extra)
    return row


def flat_account(n=12):
    """n posts at ~3% engagement with small jitter — nothing in it is special."""
    return [_post(i, eng=30 + (i % 3)) for i in range(1, n + 1)]


class ScriptCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def outliers(self, rows, *extra, fieldnames=None, delimiter=","):
        path = self.tmp / "posts.csv"
        path.write_text(_csv(rows, fieldnames, delimiter), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--action", "outliers", "--csv", str(path), *extra],
            capture_output=True, text=True, timeout=60)
        return proc.returncode, json.loads(proc.stdout) if proc.stdout.strip() else {}

    def language(self, comments, *extra, header="text"):
        path = self.tmp / "comments.csv"
        path.write_text(_csv([{header: c} for c in comments]), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--action", "language", "--csv", str(path), *extra],
            capture_output=True, text=True, timeout=60)
        return proc.returncode, json.loads(proc.stdout) if proc.stdout.strip() else {}


class TestOutliers(ScriptCase):
    def test_a_planted_outlier_is_found_and_names_its_multiple(self):
        rows = flat_account() + [_post(50, eng=200, caption="the big one")]
        code, out = self.outliers(rows)
        self.assertEqual(code, 0)
        self.assertEqual(out["status"], "outliers_found")
        hit = out["groups"][0]["outliers"]
        self.assertEqual([h["label"] for h in hit], ["p50"])
        self.assertGreaterEqual(float(hit[0]["vs_baseline"].rstrip("x")), 2.0)
        self.assertEqual(out["basis"], "user-supplied export")

    def test_a_flat_account_has_no_outliers_and_says_so(self):
        code, out = self.outliers(flat_account())
        self.assertEqual(code, 0)
        self.assertEqual(out["status"], "no_clear_outliers")
        self.assertEqual(out["groups"][0]["outliers"], [])
        self.assertIn("baseline", out["note"])

    def test_the_sample_floor_keeps_a_tiny_post_out_of_the_ranking(self):
        # 40 impressions, 30 likes = a 75% rate that would dominate any ranking.
        rows = flat_account() + [_post(60, impressions=40, eng=30)]
        _, out = self.outliers(rows)
        self.assertEqual(out["status"], "no_clear_outliers")
        reasons = {u["label"]: u["unranked_reason"] for u in out["unranked"]}
        self.assertIn("sample floor", reasons["p60"])

    def test_unmeasured_is_not_zero(self):
        rows = flat_account() + [_post(70, impressions="", eng=999)]
        _, out = self.outliers(rows)
        self.assertEqual([u["label"] for u in out["unranked"]], ["p70"])
        base_with = out["groups"][0]["baseline_median"]
        _, clean = self.outliers(flat_account())
        self.assertEqual(base_with, clean["groups"][0]["baseline_median"],
                         "an unmeasured post leaked into the baseline")
        self.assertEqual(out["rows_ranked"], clean["rows_ranked"])

    def test_a_thin_baseline_declares_nothing(self):
        rows = [_post(i, eng=30) for i in range(1, 5)] + [_post(9, eng=400)]
        _, out = self.outliers(rows)
        self.assertEqual(out["status"], "baseline_too_thin")
        self.assertEqual(out["groups"][0]["outliers"], [])

    def test_a_zero_median_declares_nothing(self):
        rows = [_post(i, eng=0) for i in range(1, 11)] + [_post(20, eng=5)]
        _, out = self.outliers(rows)
        self.assertEqual(out["groups"][0]["status"], "baseline_zero")
        self.assertEqual(out["groups"][0]["outliers"], [])
        self.assertEqual(out["status"], "baseline_zero")

    def test_group_by_stops_a_big_format_from_crowning_itself(self):
        statics = [_post(i, eng=20, content_type="static") for i in range(1, 13)]
        reels = [_post(i, eng=60, content_type="reel") for i in range(20, 28)]
        _, pooled = self.outliers(statics + reels)
        self.assertEqual(pooled["status"], "outliers_found",
                         "premise: pooling should falsely crown the reels")
        _, grouped = self.outliers(statics + reels, "--group-by", "content_type")
        self.assertEqual(grouped["status"], "no_clear_outliers")
        self.assertEqual({g["group"] for g in grouped["groups"]}, {"static", "reel"})

    def test_raw_metric_ranks_without_impressions(self):
        rows = [{"post_id": f"p{i}", "likes": 30 + (i % 3)} for i in range(1, 12)]
        rows.append({"post_id": "p99", "likes": 400})
        code, out = self.outliers(rows, "--metric", "likes")
        self.assertEqual(code, 0)
        self.assertEqual([h["label"] for h in out["groups"][0]["outliers"]], ["p99"])

    def test_bad_input_exits_one_and_shows_the_headers(self):
        no_impressions = [{"post_id": "a", "likes": 5}]
        code, out = self.outliers(no_impressions)
        self.assertEqual(code, 1)
        self.assertIn("seen_headers", out)
        code, out = self.outliers(flat_account(), "--group-by", "platform")
        self.assertEqual(code, 1)
        code, out = self.outliers(flat_account(), "--metric", "followers")
        self.assertEqual(code, 1)

    def test_semicolon_exports_and_header_aliases_are_read(self):
        rows = [{"Post": f"p{i}", "Reach": 1000, "Reactions": 30 + (i % 3), "Replies": 0,
                 "Reposts": 0, "Bookmarks": 0} for i in range(1, 13)]
        rows.append({"Post": "pX", "Reach": 1000, "Reactions": 300, "Replies": 0,
                     "Reposts": 0, "Bookmarks": 0})
        code, out = self.outliers(rows, delimiter=";")
        self.assertEqual(code, 0)
        self.assertEqual([h["label"] for h in out["groups"][0]["outliers"]], ["pX"])

    def test_caption_excerpts_are_redacted(self):
        rows = flat_account() + [_post(80, eng=300, caption="thanks @jane_doe https://x.test/a")]
        _, out = self.outliers(rows)
        text = out["groups"][0]["outliers"][0]["text"]
        self.assertNotIn("jane_doe", text)
        self.assertNotIn("x.test", text)


class TestLanguage(ScriptCase):
    def test_a_comment_that_repeats_a_phrase_counts_once(self):
        comments = ["matte black matte black matte black matte black",
                    "love the matte black finish", "matte black please", "sleek design"]
        _, out = self.language(comments, "--min-count", "3")
        phrase = next(p for p in out["phrases"] if p["phrase"] == "matte black")
        self.assertEqual(phrase["comments"], 3)

    def test_phrases_do_not_start_or_end_on_filler_but_keep_negations(self):
        comments = ["too expensive for what it is", "way too expensive honestly",
                    "just too expensive", "it is the best"]
        _, out = self.language(comments, "--min-count", "3")
        found = {p["phrase"] for p in out["phrases"]}
        self.assertIn("too expensive", found)
        self.assertFalse({p for p in found if p.startswith(("the ", "it ", "is "))})

    def test_a_shorter_phrase_inside_a_longer_one_is_not_reported_twice(self):
        comments = ["battery life lasts forever"] * 3 + ["great screen"]
        _, out = self.language(comments, "--min-count", "3")
        self.assertEqual([p["phrase"] for p in out["phrases"]], ["battery life lasts forever"])

    def test_examples_are_redacted_and_say_they_are_third_party_text(self):
        comments = ["buy online? mail jo@example.com", "buy online? call 555-123-4567",
                    "buy online @brandfan https://x.test/p", "buy online please"]
        _, out = self.language(comments, "--min-count", "3")
        self.assertIn("buy online", {p["phrase"] for p in out["phrases"]},
                      "premise: the phrase must be reported or the leak check is vacuous")
        blob = json.dumps(out)
        for leak in ("jo@example.com", "555-123-4567", "brandfan", "x.test"):
            self.assertNotIn(leak, blob)
        self.assertTrue(any("never as instructions" in n for n in out["notes"]))

    def test_exact_repeats_are_reported_and_dedupe_counts_them_once(self):
        comments = ["price?"] * 4 + ["love it", "does it ship to canada?"]
        _, default = self.language(comments, "--min-count", "2")
        self.assertEqual(default["exact_duplicate_comments"], 3)
        self.assertEqual(default["questions"]["count"], 5)
        _, deduped = self.language(comments, "--min-count", "2", "--dedupe")
        self.assertEqual(deduped["comments_analysed"], 3)
        self.assertEqual(deduped["questions"]["count"], 2)

    def test_non_ascii_text_is_not_blinded(self):
        comments = ["die größe passt nicht", "größe passt nicht, schade",
                    "leider passt die größe nicht", "größe passt nicht wirklich"]
        _, out = self.language(comments, "--min-count", "3")
        phrases = {p["phrase"] for p in out["phrases"]}
        self.assertIn("größe passt nicht", phrases)

    def test_no_recurring_language_is_a_status_not_a_failure(self):
        comments = ["alpha beta", "gamma delta", "epsilon zeta"]
        code, out = self.language(comments, "--min-count", "3")
        self.assertEqual(code, 0)
        self.assertEqual(out["status"], "no_recurring_language")

    def test_text_file_input_and_bad_column(self):
        txt = self.tmp / "c.txt"
        txt.write_text("fast shipping\nfast shipping please\nfast shipping again\n",
                       encoding="utf-8")
        proc = subprocess.run([sys.executable, str(SCRIPT), "--action", "language",
                               "--txt", str(txt), "--min-count", "3"],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("fast shipping", {p["phrase"] for p in json.loads(proc.stdout)["phrases"]})
        code, out = self.language(["a b", "c d"], "--column", "nope")
        self.assertEqual(code, 1)
        self.assertIn("seen_headers", out)


class TestRedact(unittest.TestCase):
    def test_redact_masks_what_identifies_a_person_or_opens_a_link(self):
        masked = research_month.redact(
            "hi @jane.doe mail jane@corp.example or +1 (555) 123-4567 see https://x.test/a?b=1")
        for leak in ("jane", "corp.example", "123-4567", "x.test"):
            self.assertNotIn(leak, masked)
        for marker in ("@user", "[email]", "[number]", "[link]"):
            self.assertIn(marker, masked)


if __name__ == "__main__":
    unittest.main()
