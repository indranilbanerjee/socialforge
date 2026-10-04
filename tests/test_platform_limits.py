"""Platform limits are sourced data, X is counted the way X counts, no hashtag is
dropped silently, and the docs do not claim the adapter inserts an AI label.

Four defects shipped together in scripts/adapt_copy.py:

1. Every number in PLATFORM_LIMITS was a bare literal: no source, no check date.
   Pinterest's own page says the description may be 800 characters (the literal
   said 500); Instagram announced a 5-hashtag cap on 2025-12-18 (the literal
   said 30); Threads allows one topic tag per post (the literal said 3).
2. X was measured with len(). X counts every URL as 23 characters and every
   emoji and CJK character as 2, so a short URL or a Japanese post could be
   reported within the limit and then be refused by X.
3. Hashtags past a platform's cap were thrown away without a word.
4. references/channel-changes-may-2026.md said the caption adapter inserts the
   AI-disclosure label. No code does.

The guards here are written as functions that take the thing under test, so each
one can be run twice: once on the real repository (it must pass) and once on a
planted failure (it must fire). A guard that never fires is not a guard.

Stdlib only.
"""
from __future__ import annotations

import copy
import datetime
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import adapt_copy  # noqa: E402

DATA_PATH = SCRIPTS / "platform_limits.json"
UNSOURCED = "SocialForge data, unsourced"
NINE = ["linkedin", "instagram", "x", "facebook", "youtube", "tiktok", "pinterest", "threads", "bluesky"]
LIMIT_KEYS = {"char_limit", "count_method", "fold_at", "optimal_limit", "hashtag_limit",
              "hashtag_placement", "link"}
SPEC_NAMES = {"LinkedIn": "linkedin", "Instagram": "instagram", "X/Twitter": "x", "X": "x",
              "Facebook": "facebook", "YouTube": "youtube", "TikTok": "tiktok",
              "Pinterest": "pinterest", "Threads": "threads", "Bluesky": "bluesky"}

# twitter-text config/v3.json as read on 2026-10-04. Hard-coded here on purpose:
# editing the data file away from the primary source must fail a test.
X_CONFIG_V3 = {
    "version": 3, "maxWeightedTweetLength": 280, "scale": 100, "defaultWeight": 200,
    "emojiParsingEnabled": True, "transformedURLLength": 23,
    "ranges": [{"start": 0, "end": 4351, "weight": 100}, {"start": 8192, "end": 8205, "weight": 100},
               {"start": 8208, "end": 8223, "weight": 100}, {"start": 8242, "end": 8247, "weight": 100}],
}


def read(path):
    return Path(path).read_text(encoding="utf-8")


def load_data():
    return json.loads(read(DATA_PATH))


def run_script(*args):
    proc = subprocess.run([sys.executable, "-B", str(SCRIPTS / "adapt_copy.py"), *args],
                          capture_output=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")


def literal_limits_problems(script_text):
    """The limits must be loaded from the data file, never a literal in the script."""
    if re.search(r"(?m)^PLATFORM_LIMITS\s*=\s*\{", script_text):
        return ["PLATFORM_LIMITS is a literal in adapt_copy.py again"]
    if "platform_limits.json" not in script_text:
        return ["adapt_copy.py does not name platform_limits.json"]
    return []


def valid_date(value):
    try:
        return datetime.date.fromisoformat(value) <= datetime.date.today()
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Guard 1: the data file's shape (every entry sourced-or-marked, dated)
# ---------------------------------------------------------------------------

def table_problems(data):
    """Everything wrong with a limits table, as strings. [] means sound."""
    problems = []
    platforms = data.get("platforms")
    if not isinstance(platforms, dict):
        return ["no platforms object"]
    if list(platforms) != NINE:
        problems.append(f"platforms are {list(platforms)}, expected {NINE}")
    for name, entry in platforms.items():
        where = f"{name}:"
        limits = entry.get("limits", {})
        if not set(limits) <= LIMIT_KEYS:
            problems.append(f"{where} unknown limits keys {sorted(set(limits) - LIMIT_KEYS)}")
        for key in ("char_limit", "link", "hashtag_limit"):
            if key not in limits:
                problems.append(f"{where} limits.{key} missing")
        for key in ("char_limit", "fold_at", "optimal_limit", "hashtag_limit"):
            if key in limits and not (isinstance(limits[key], int) and not isinstance(limits[key], bool)
                                      and limits[key] > 0):
                problems.append(f"{where} limits.{key} must be a positive integer")
        if limits.get("link") not in {"direct", "bio"}:
            problems.append(f"{where} limits.link must be direct or bio")
        if "hashtag_placement" in limits and limits["hashtag_placement"] not in {"first_comment", "tag_facets"}:
            problems.append(f"{where} limits.hashtag_placement is not a known placement")
        if "optimal_limit" in limits and limits["optimal_limit"] > limits.get("char_limit", 0):
            problems.append(f"{where} optimal_limit exceeds char_limit")
        if "count_method" in limits and limits["count_method"] not in {"x_weighted"}:
            problems.append(f"{where} unknown count_method")

        source = entry.get("source")
        if not (source == UNSOURCED or (isinstance(source, str) and re.match(r"^https://\S+$", source))):
            problems.append(f"{where} source must be an https URL or the text {UNSOURCED!r}")
        if not valid_date(entry.get("checked")):
            problems.append(f"{where} checked must be a real past ISO date, got {entry.get('checked')!r}")

        lists = [entry.get(k, []) for k in ("confirmed", "differs", "unsourced")]
        if sum(len(x) for x in lists) != len(limits) or set().union(*map(set, lists)) != set(limits):
            problems.append(f"{where} confirmed/differs/unsourced must partition the limits keys exactly once")

        also = entry.get("also_read", [])
        also_keys = set()
        if not isinstance(also, list):
            problems.append(f"{where} also_read must be a list")
            also = []
        for item in also:
            if not (isinstance(item.get("url"), str) and re.match(r"^https://\S+$", item["url"])):
                problems.append(f"{where} also_read entry without an https url")
            if not valid_date(item.get("checked")):
                problems.append(f"{where} also_read entry without a real checked date")
            if not (isinstance(item.get("says"), str) and len(item["says"]) > 20):
                problems.append(f"{where} also_read entry without a says text")
            if "key" in item:
                if item["key"] not in limits:
                    problems.append(f"{where} also_read key {item['key']!r} is not a limits key")
                also_keys.add(item["key"])

        claimed = set(entry.get("confirmed", [])) | set(entry.get("differs", []))
        if source == UNSOURCED:
            unbacked = claimed - also_keys
            if unbacked:
                problems.append(f"{where} {sorted(unbacked)} marked confirmed/differs but nothing was read for it "
                                f"(source is unsourced and no also_read entry carries the key)")
        elif claimed == set():
            problems.append(f"{where} a source is cited but nothing is marked confirmed or differs")
        if entry.get("differs") and "kept" not in entry.get("notes", "").lower():
            problems.append(f"{where} a differing value must be explained in notes (say what was kept)")
        if len(entry.get("notes", "")) <= 20:
            problems.append(f"{where} notes missing")

        if limits.get("count_method") == "x_weighted":
            config = data.get("counting", {}).get("x_weighted", {}).get("config")
            if not config:
                problems.append(f"{where} count_method x_weighted but no counting.x_weighted.config")
            elif config.get("maxWeightedTweetLength") != limits.get("char_limit"):
                problems.append(f"{where} char_limit differs from counting.x_weighted.config.maxWeightedTweetLength")
    return problems


def pinned_value_problems(data):
    """The numbers a primary page was read for on 2026-10-04, plus the ones that must NOT
    be upgraded because no readable primary page exists."""
    problems = []
    p = data["platforms"]
    if p["pinterest"]["limits"]["char_limit"] != 800 or "char_limit" not in p["pinterest"]["confirmed"]:
        problems.append("pinterest char_limit must be 800 and confirmed (help.pinterest.com says up to 800)")
    if "help.pinterest.com" not in p["pinterest"]["source"]:
        problems.append("pinterest source must be the Pinterest help page")
    if p["threads"]["limits"]["hashtag_limit"] != 1 or "hashtag_limit" not in p["threads"]["confirmed"]:
        problems.append("threads hashtag_limit must be 1 and confirmed (one topic tag per post)")
    ig = p["instagram"]
    if ig["limits"]["hashtag_limit"] != 5 or "hashtag_limit" not in ig["confirmed"]:
        problems.append("instagram hashtag_limit must be 5 and confirmed (the @creators announcement)")
    if not any(a.get("key") == "hashtag_limit" and "threads.com/@creators" in a["url"]
               for a in ig.get("also_read", [])):
        problems.append("instagram hashtag_limit needs the @creators post in also_read")
    for name in ("tiktok", "facebook", "instagram"):
        if "char_limit" in p[name]["confirmed"] or "char_limit" not in p[name]["unsourced"]:
            problems.append(f"{name} char_limit has no readable primary source and must stay unsourced")
    if p["tiktok"]["limits"]["char_limit"] != 2200:
        problems.append("tiktok char_limit stays 2200 (the conservative cap) until a primary page says otherwise")
    for name in ("linkedin", "x", "youtube", "threads", "bluesky"):
        if "char_limit" not in p[name]["confirmed"]:
            problems.append(f"{name} char_limit was confirmed against a primary page on 2026-10-04")
    return problems


class TestLimitsDataFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()

    # -- the real file passes ------------------------------------------------
    def test_the_data_file_is_sound(self):
        self.assertEqual(table_problems(self.data), [])

    def test_the_primary_page_numbers_are_in_and_the_unreadable_ones_are_not_upgraded(self):
        self.assertEqual(pinned_value_problems(self.data), [])

    def test_the_script_loads_its_limits_from_the_file(self):
        self.assertEqual(adapt_copy.PLATFORMS_PATH.resolve(), DATA_PATH.resolve())
        self.assertIsNone(adapt_copy._DATA_ERROR)
        self.assertEqual(adapt_copy.PLATFORM_LIMITS, {n: e["limits"] for n, e in self.data["platforms"].items()})
        self.assertEqual(literal_limits_problems(read(SCRIPTS / "adapt_copy.py")), [])

    def test_pinterest_now_allows_what_pinterest_says(self):
        long_body = "A sentence that fills space. " * 40  # 1,160 characters
        out = adapt_copy.adapt_for_platform(long_body, "pinterest")
        self.assertEqual(out["char_limit"], 800)
        self.assertGreater(out["char_count"], 500)
        self.assertLessEqual(out["char_count"], 800)

    def test_no_model_ids_or_prices_in_the_data(self):
        raw = read(DATA_PATH)
        self.assertIsNone(re.search(r"\$\s?\d", raw))
        self.assertIsNone(re.search(r"(?i)\b(claude|gpt|gemini|veo|kling|sora|imagen|llama|mistral)[-\s]?\d", raw))

    # -- --sources and --list-platforms ---------------------------------------
    def test_sources_prints_the_record(self):
        code, out, _ = run_script("--sources")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(list(data), NINE)
        for name, entry in data.items():
            with self.subTest(platform=name):
                self.assertEqual(set(entry), {"source", "checked", "status", "confirmed", "differs",
                                              "unsourced", "also_read", "notes"})
                self.assertEqual(set(entry["status"]), set(adapt_copy.PLATFORM_LIMITS[name]))
                self.assertLessEqual(set(entry["status"].values()), {"confirmed", "differs", "unsourced"})
        self.assertEqual(data["pinterest"]["status"]["char_limit"], "confirmed")
        self.assertEqual(data["tiktok"]["status"]["char_limit"], "unsourced")
        self.assertEqual(data["tiktok"]["source"], UNSOURCED)
        self.assertEqual(data["x"]["source"], "https://docs.x.com/fundamentals/counting-characters")

    def test_list_platforms_prints_what_the_script_reads(self):
        code, out, _ = run_script("--list-platforms")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), adapt_copy.PLATFORM_LIMITS)

    def test_a_broken_data_file_is_an_error_not_a_traceback(self):
        for label, broken in (("not json", "{nope"),
                              ("no platforms", json.dumps({"platforms": {}})),
                              ("bad limit", json.dumps({"platforms": {"x": {"limits": {"char_limit": "280"}}}})),
                              ("unknown method", json.dumps({"platforms": {"x": {"limits": {
                                  "char_limit": 280, "count_method": "magic"}}}})),
                              ("weighted without a config", json.dumps({"platforms": {"x": {"limits": {
                                  "char_limit": 280, "count_method": "x_weighted"}}}}))):
            with self.subTest(case=label):
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp = Path(tmpdir) / "platform_limits.json"
                    tmp.write_text(broken, encoding="utf-8")
                    limits, raw, error = adapt_copy._load_platforms(tmp)
                self.assertEqual((limits, raw), ({}, {}))
                self.assertIn("could not load", error)

    # -- plants: each guard must fire -----------------------------------------
    def assertFires(self, mutate, needle, guard=table_problems):
        broken = copy.deepcopy(self.data)
        mutate(broken)
        problems = guard(broken)
        self.assertTrue(any(needle in p for p in problems), f"planted failure not caught ({needle!r}): {problems}")

    def test_plant_missing_source(self):
        self.assertFires(lambda d: d["platforms"]["linkedin"].pop("source"), "source must be")

    def test_plant_a_made_up_source(self):
        self.assertFires(lambda d: d["platforms"]["linkedin"].update(source="trust me"), "source must be")

    def test_plant_missing_or_future_or_garbled_date(self):
        self.assertFires(lambda d: d["platforms"]["x"].pop("checked"), "checked must be")
        self.assertFires(lambda d: d["platforms"]["x"].update(checked="2999-01-01"), "checked must be")
        self.assertFires(lambda d: d["platforms"]["x"].update(checked="last week"), "checked must be")

    def test_plant_a_limit_listed_nowhere_or_twice(self):
        self.assertFires(lambda d: d["platforms"]["youtube"]["unsourced"].remove("link"), "partition")
        self.assertFires(lambda d: d["platforms"]["youtube"]["confirmed"].append("link"), "partition")

    def test_plant_confirmed_without_reading_anything(self):
        # TikTok has no readable primary page; marking its limit confirmed must be refused.
        def upgrade(d):
            t = d["platforms"]["tiktok"]
            t["unsourced"].remove("char_limit")
            t["confirmed"].append("char_limit")
        self.assertFires(upgrade, "nothing was read")
        self.assertFires(upgrade, "must stay unsourced", guard=pinned_value_problems)

    def test_plant_a_source_that_confirms_nothing(self):
        def hollow(d):
            e = d["platforms"]["linkedin"]
            e["unsourced"] += e["confirmed"]
            e["confirmed"] = []
        self.assertFires(hollow, "nothing is marked confirmed")

    def test_plant_an_also_read_entry_that_says_nothing(self):
        self.assertFires(lambda d: d["platforms"]["youtube"]["also_read"][0].pop("says"), "without a says")
        self.assertFires(lambda d: d["platforms"]["youtube"]["also_read"][0].update(url="not a url"), "without an https url")
        self.assertFires(lambda d: d["platforms"]["instagram"]["also_read"][0].update(key="nope"), "not a limits key")

    def test_plant_a_weighted_platform_with_no_counting_rules(self):
        self.assertFires(lambda d: d.pop("counting"), "no counting.x_weighted.config")
        self.assertFires(lambda d: d["counting"]["x_weighted"]["config"].update(maxWeightedTweetLength=281),
                         "differs from counting")

    def test_plant_pinterest_back_at_500(self):
        self.assertFires(lambda d: d["platforms"]["pinterest"]["limits"].update(char_limit=500),
                         "pinterest char_limit must be 800", guard=pinned_value_problems)

    def test_plant_threads_and_instagram_hashtag_caps_back_to_the_old_numbers(self):
        self.assertFires(lambda d: d["platforms"]["threads"]["limits"].update(hashtag_limit=3),
                         "threads hashtag_limit must be 1", guard=pinned_value_problems)
        self.assertFires(lambda d: d["platforms"]["instagram"]["limits"].update(hashtag_limit=30),
                         "instagram hashtag_limit must be 5", guard=pinned_value_problems)

    def test_plant_a_dropped_platform_and_an_unknown_key(self):
        self.assertFires(lambda d: d["platforms"].pop("bluesky"), "platforms are")
        self.assertFires(lambda d: d["platforms"]["x"]["limits"].update(magic=1), "unknown limits keys")

    def test_plant_the_script_going_back_to_a_literal(self):
        real = read(SCRIPTS / "adapt_copy.py")
        planted = real + '\nPLATFORM_LIMITS = {\n    "x": {"char_limit": 280},\n}\n'
        self.assertTrue(any("literal" in p for p in literal_limits_problems(planted)))
        stripped = real.replace("platform_limits.json", "limits.json")
        self.assertTrue(any("does not name" in p for p in literal_limits_problems(stripped)))


# ---------------------------------------------------------------------------
# Guard 2: X weighted counting
# ---------------------------------------------------------------------------

_REF_PUNCT = ".,;:!?)]}'\"\u201d\u2019\u00bb"
_REF_NO_URL_BEFORE = "@#$./-"


def _ref_url_spans(text):
    """URL spans found by plain string scanning (not the module's regex): a scheme or
    www. not glued to a word, running to the end of its whitespace-free run minus
    trailing sentence punctuation, with at least one character left after the scheme."""
    spans, i, n = [], 0, len(text)
    while i < n:
        if text[i].isspace():
            i += 1
            continue
        j = i
        while j < n and not text[j].isspace():
            j += 1
        token, k = text[i:j], 0
        while k < len(token):
            low = token[k:].lower()
            scheme = 8 if low.startswith("https://") else 7 if low.startswith("http://") else \
                4 if low.startswith("www.") else 0
            before = token[k - 1] if k else ""
            if scheme and not (before and (before.isalnum() or before == "_" or before in _REF_NO_URL_BEFORE)):
                end = len(token)
                while end > k + scheme and token[end - 1] in _REF_PUNCT:
                    end -= 1
                if end > k + scheme:
                    spans.append((i + k, i + end))
                    break
            k += 1
        i = j
    return spans


def ref_weight(text, config=X_CONFIG_V3):
    """An independent reference for X's weighted length, written from the primary config and
    the docs (not from the module under test): NFC first, each URL one 23-weight token, every
    other code point weighed by range."""
    text = unicodedata.normalize("NFC", text)
    total, pos = 0, 0
    for start, end in _ref_url_spans(text):
        total += sum(_ref_char(c, config) for c in text[pos:start])
        total += config["transformedURLLength"] * config["scale"]
        pos = end
    total += sum(_ref_char(c, config) for c in text[pos:])
    return -(-total // config["scale"])


def _ref_char(char, config):
    code = ord(char)
    for r in config["ranges"]:
        if r["start"] <= code <= r["end"]:
            return r["weight"]
    return config["defaultWeight"]


def x_counting_problems(mod):
    """What must hold for X counting in module `mod` (the real one, or a planted break)."""
    problems = []
    w = lambda text: mod.adapt_for_platform(text, "x")["char_count"]  # noqa: E731
    cases = [
        ("a plain ASCII post counts its characters", "Hello there.", 12),
        ("a URL counts 23 however long", "https://example.com/" + "p" * 500, 23),
        ("a short URL counts 23, which len() undercounts", "http://a.b", 23),
        ("www. URLs count 23", "www.example.com", 23),
        ("text around a URL still counts", "See https://example.com/a for more", 4 + 23 + 9),
        ("a URL followed by sentence punctuation: the punctuation counts apart", "See https://example.com/a.", 4 + 23 + 1),
        ("CJK characters count 2 each", "世界", 4),
        ("an emoji counts 2", "\U0001F600", 2),
        ("a word glued to http:// is not a URL", "xhttps://example.com", 20),
    ]
    for label, text, expected in cases:
        got = w(text)
        if got != expected:
            problems.append(f"{label}: {text[:30]!r} counted {got}, expected {expected}")
    out = mod.adapt_for_platform("x" * 200 + " http://a.b", "x")
    if out["char_count"] != 224 or len(out["copy"]) != 211:
        problems.append(f"a short URL must count 23, not its length: char_count {out['char_count']}, "
                        f"len {len(out['copy'])}, expected 224 and 211")
    decomposed = mod.adapt_for_platform("cafe\u0301", "x")["char_count"]
    if decomposed != 4 or mod.adapt_for_platform("caf\u00e9", "x")["char_count"] != 4:
        problems.append(f"composed and decomposed forms must count alike (NFC): got {decomposed}, expected 4")
    if mod.adapt_for_platform("\u0344", "x")["char_count"] != 2:
        problems.append("U+0344 expands to two marks under NFC and must count 2")
    cjk = mod.adapt_for_platform("世界" * 100, "x")
    if cjk["char_count"] > 280 or not cjk["within_limit"]:
        problems.append(f"a 200-character CJK post was not cut to X's weighted 280 (char_count {cjk['char_count']})")
    if cjk["count_method"] != "x_weighted":
        problems.append("the result must say how it counted")
    return problems


class TestXWeightedCounting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()

    # -- the recorded config is the primary source's config --------------------
    def test_the_recorded_config_equals_twitter_texts_v3(self):
        self.assertEqual(self.data["counting"]["x_weighted"]["config"], X_CONFIG_V3)
        self.assertTrue(self.data["counting"]["x_weighted"]["source"].endswith("/twitter-text/master/config/v3.json"))
        self.assertTrue(valid_date(self.data["counting"]["x_weighted"]["checked"]))

    def test_x_uses_it_and_the_others_do_not(self):
        for name, spec in adapt_copy.PLATFORM_LIMITS.items():
            with self.subTest(platform=name):
                self.assertEqual(spec.get("count_method") == "x_weighted", name == "x")
        self.assertEqual(adapt_copy.PLATFORM_LIMITS["x"]["char_limit"], X_CONFIG_V3["maxWeightedTweetLength"])

    def test_plant_a_config_edited_away_from_the_source_is_caught(self):
        drifted = copy.deepcopy(self.data["counting"]["x_weighted"]["config"])
        drifted["transformedURLLength"] = 24
        self.assertNotEqual(drifted, X_CONFIG_V3)
        drifted = copy.deepcopy(self.data["counting"]["x_weighted"]["config"])
        drifted["ranges"][0]["end"] = 4000
        self.assertNotEqual(drifted, X_CONFIG_V3)

    # -- the weights -----------------------------------------------------------
    def test_the_documented_counting_examples(self):
        self.assertEqual(x_counting_problems(adapt_copy), [])

    def test_range_boundaries(self):
        wl = lambda ch: adapt_copy.weighted_length(ch, adapt_copy._X_WEIGHTED)  # noqa: E731
        for code in (0, 65, 4351, 8192, 8205, 8208, 8223, 8242, 8247):
            self.assertEqual(wl(chr(code)), 1, code)
        for code in (4352, 8191, 8206, 8207, 8224, 8241, 8248, 0x4E16, 0x1F600):
            self.assertEqual(wl(chr(code)), 2, code)

    def test_scripts_below_u10ff_weigh_one_as_the_config_says(self):
        # Documented in the data file: the docs table says 'Other Unicode 2', the config says 1 up to U+10FF.
        self.assertEqual(adapt_copy.weighted_length("नमस्ते", adapt_copy._X_WEIGHTED), 6)

    def test_emoji_sequences_are_over_counted_never_under_counted(self):
        family = "\U0001F468‍\U0001F469‍\U0001F467‍\U0001F466"
        flag = "\U0001F1FA\U0001F1F8"
        for emoji in (family, flag, "❤️", "1️⃣"):
            with self.subTest(emoji=emoji.encode("unicode_escape")):
                self.assertGreaterEqual(adapt_copy.weighted_length(emoji, adapt_copy._X_WEIGHTED), 2)
        self.assertEqual(adapt_copy.weighted_length(family, adapt_copy._X_WEIGHTED), 11)  # X counts it 2
        self.assertEqual(ref_weight(family), 11)

    def test_text_is_counted_after_nfc_as_x_does(self):
        """X's docs: length is calculated after NFC. Raw weighing is NOT a safe shortcut: a few
        code points weigh MORE after NFC (U+0344 becomes two marks, the Devanagari nukta forms
        become base + nukta, Tibetan vowel signs split), so the script normalises first."""
        cfg = adapt_copy._X_WEIGHTED
        wl = lambda s: adapt_copy.weighted_length(s, cfg)  # noqa: E731
        self.assertEqual(wl("caf\u00e9"), 4)
        self.assertEqual(wl("cafe\u0301"), 4)      # the docs' own example: composed and decomposed agree
        self.assertEqual(wl("\u0344"), 2)
        self.assertEqual(wl("\u0958"), 2)          # Devanagari QA: NFC splits it into KA + NUKTA
        raw_weight = lambda s: sum(_ref_char(c, X_CONFIG_V3) for c in s) // 100  # noqa: E731
        self.assertEqual(raw_weight("\u0344"), 1)  # the shortcut that would have undercounted
        lower = []
        for code in range(0x110000):
            if 0xD800 <= code <= 0xDFFF:
                continue
            ch = chr(code)
            if unicodedata.normalize("NFC", ch) != ch and raw_weight(ch) < ref_weight(ch):
                lower.append(code)
        self.assertGreater(len(lower), 10)           # the exceptions are real, and counted correctly below
        for code in range(0x110000):
            if 0xD800 <= code <= 0xDFFF:
                continue
            ch = chr(code)
            self.assertEqual(wl(ch), ref_weight(ch), hex(code))

    def test_plant_no_normalisation_undercounts(self):
        # With NFC switched off the guard's own examples fail.
        identity = lambda form, text: text  # noqa: E731
        with mock.patch.object(adapt_copy.unicodedata, "normalize", identity):
            problems = x_counting_problems(adapt_copy)
        self.assertTrue(any("NFC" in p or "U+0344" in p for p in problems), problems)

    # -- adaptation uses it -----------------------------------------------------
    def test_a_short_url_len_would_undercount(self):
        body = "x" * 254 + "."
        out = adapt_copy.adapt_for_platform(body, "x", cta="Go: http://a.b")
        # len() sees 255 + 16 = 271 and would call it fine; X counts 255 + 2 + 4 + 23 = 284 and refuses it.
        self.assertEqual(len(body + "\n\nGo: http://a.b"), 271)
        self.assertEqual(ref_weight(body + "\n\nGo: http://a.b"), 284)
        self.assertLessEqual(out["char_count"], 280)
        self.assertTrue(out["within_limit"])
        self.assertLess(len(out["copy"]), 271)            # the body was cut to make room for the 23
        self.assertGreater(out["char_count"], len(out["copy"]))
        self.assertTrue(out["copy"].endswith("\n\nGo: http://a.b"))

    def test_a_long_url_is_not_over_counted(self):
        url = "https://example.com/" + "p" * 400
        body = "A short post. "
        out = adapt_copy.adapt_for_platform(body.strip(), "x", cta="Read: " + url)
        self.assertEqual(out["copy"], body.strip() + "\n\nRead: " + url)  # len() would have refused all of it
        self.assertEqual(out["char_count"], len(body.strip()) + 2 + len("Read: ") + 23)
        self.assertTrue(out["within_limit"])

    def test_a_cjk_post_is_cut_by_weight(self):
        out = adapt_copy.adapt_for_platform("世界" * 100, "x")
        self.assertEqual(out["char_count"], ref_weight(out["copy"]))
        self.assertLessEqual(out["char_count"], 280)
        self.assertTrue(out["copy"].endswith("..."))
        self.assertLess(len(out["copy"]), 200)

    def test_the_other_platforms_still_use_plain_len(self):
        text = "Café ☕ 世界 \U0001F600 https://example.com/" + "p" * 300
        for name in NINE:
            if name != "x":
                with self.subTest(platform=name):
                    out = adapt_copy.adapt_for_platform(text, name)
                    self.assertEqual(out["char_count"], len(out["copy"]))
                    self.assertEqual(out["count_method"], "code_points")

    def test_fuzz_x_results_agree_with_an_independent_count_and_fit(self):
        rng = random.Random(20261004)
        pieces = ["growth", "the", "checklist", "dashboard", "Café", "नमस्ते", "世界", "こんにちは", "😀", "☕", "❤️",
                  "\U0001F468‍\U0001F469‍\U0001F467‍\U0001F466", "\U0001F1FA\U0001F1F8", "14", "steps"]
        urls = ["https://example.com/", "http://a.b", "www.x.org/p", "https://example.com/" + "q" * 120]
        terminators = [". ", "! ", "? ", ", ", " ", "\n\n", ".) ", ".\n"]
        ctas = [None, "", "Get it: https://example.com/checklist", "http://a.b", "Join us", "Read: www.example.org/long/path"]
        checked = cut = 0
        for _ in range(3000):
            parts, size = [], 0
            target = rng.randint(1, 700)
            while size < target:
                piece = " ".join(rng.choice(pieces) for _ in range(rng.randint(1, 8)))
                if rng.random() < 0.25:
                    piece += " " + rng.choice(urls) + rng.choice(["", ".", ")", ","])
                piece += rng.choice(terminators)
                parts.append(piece)
                size += len(piece)
            text = "".join(parts).rstrip()
            if not text:
                continue
            cta = rng.choice(ctas)
            out = adapt_copy.adapt_for_platform(text, "x", None, cta)
            checked += 1
            self.assertEqual(out["char_count"], ref_weight(out["copy"]), (text[:60], cta))
            self.assertEqual(out["within_limit"], out["char_count"] <= 280)
            cta_block = f"\n\n{cta}" if cta else ""
            self.assertTrue(out["copy"].endswith(cta_block))
            if ref_weight(cta_block) <= 276:  # room for at least an ellipsis: it must fit
                self.assertTrue(out["within_limit"], (text[:60], cta, out["char_count"]))
            if ref_weight(text + cta_block) <= 280:  # fits whole: untouched
                self.assertEqual(out["copy"], text + cta_block)
            else:
                cut += 1
                body = out["copy"][:len(out["copy"]) - len(cta_block)] if cta_block else out["copy"]
                self.assertTrue(text.startswith(body) or text.startswith(body[:-3]), (text[:60], body[:60]))
        self.assertGreater(checked, 2500)
        self.assertGreater(cut, 500)

    def test_check_counts_nothing_differently_for_plain_ascii(self):
        for n in (1, 100, 279, 280):
            self.assertEqual(adapt_copy.adapt_for_platform("a" * n, "x")["char_count"], n)

    # -- plants -----------------------------------------------------------------
    def test_plant_x_measured_with_len_again(self):
        with mock.patch.object(adapt_copy, "_measurer", lambda specs: len):
            problems = x_counting_problems(adapt_copy)
        self.assertTrue(any("short URL" in p or "counts" in p for p in problems), problems)
        self.assertGreaterEqual(len(problems), 4, problems)

    def test_plant_url_weight_changed(self):
        broken = dict(adapt_copy._X_WEIGHTED, url_length=22)
        with mock.patch.object(adapt_copy, "_X_WEIGHTED", broken):
            self.assertTrue(x_counting_problems(adapt_copy))

    def test_plant_every_emoji_and_cjk_weighed_one(self):
        broken = dict(adapt_copy._X_WEIGHTED, default_weight=100)
        with mock.patch.object(adapt_copy, "_X_WEIGHTED", broken):
            problems = x_counting_problems(adapt_copy)
        self.assertTrue(any("CJK" in p or "emoji" in p for p in problems), problems)

    def test_plant_urls_not_detected(self):
        with mock.patch.object(adapt_copy, "_X_URL_RE", re.compile(r"(?!x)x")):
            problems = x_counting_problems(adapt_copy)
        self.assertTrue(any("URL" in p for p in problems), problems)

    def test_plant_the_cut_ignoring_weight(self):
        # truncate_smart always measuring with len: the CJK post is not cut to X's weighted limit.
        real = adapt_copy.truncate_smart
        with mock.patch.object(adapt_copy, "truncate_smart", lambda text, limit, measure=len: real(text, limit)):
            problems = x_counting_problems(adapt_copy)
        self.assertTrue(any("CJK post was not cut" in p for p in problems), problems)

    def test_the_reference_counter_agrees_with_the_documented_examples(self):
        self.assertEqual(ref_weight("https://..."), 11)         # a scheme with nothing after it is not a URL
        self.assertEqual(ref_weight("(https://example.com)"), 25)
        self.assertEqual(ref_weight("See https://example.com/a."), 28)
        self.assertEqual(ref_weight("xhttps://example.com"), 20)

    def test_plant_the_reference_counter_catches_a_wrong_count(self):
        # The fuzz test compares against ref_weight; prove ref_weight disagrees with a wrong count.
        self.assertNotEqual(ref_weight("世界"), len("世界"))
        self.assertNotEqual(ref_weight("http://a.b"), len("http://a.b"))


# ---------------------------------------------------------------------------
# Guard 3: no silent hashtag drops
# ---------------------------------------------------------------------------

def hashtag_problems(mod):
    problems = []
    tags = [f"#t{i}" for i in range(12)]
    for name, spec in mod.PLATFORM_LIMITS.items():
        cap = spec.get("hashtag_limit", 5)
        out = mod.adapt_for_platform("Hi.", name, tags)
        if "hashtags_dropped" not in out:
            problems.append(f"{name}: result has no hashtags_dropped")
            continue
        kept = (out["first_comment"] if out["first_comment"] is not None else out["hashtags"]).split()
        if kept + out["hashtags_dropped"] != tags:
            problems.append(f"{name}: kept + dropped is not the full list in order")
        if out["hashtags_dropped"] != tags[cap:]:
            problems.append(f"{name}: dropped {out['hashtags_dropped']}, expected {tags[cap:]}")
        if mod.adapt_for_platform("Hi.", name, tags[:1])["hashtags_dropped"] != ([] if cap >= 1 else tags[:1]):
            problems.append(f"{name}: one tag within the cap must drop nothing")
        for given in (None, []):
            if mod.adapt_for_platform("Hi.", name, given)["hashtags_dropped"] != []:
                problems.append(f"{name}: no hashtags given must give an empty list")
    return problems


class TestNoSilentHashtagDrops(unittest.TestCase):
    def test_every_platform_reports_what_its_cap_removed(self):
        self.assertEqual(hashtag_problems(adapt_copy), [])

    def test_the_documented_example(self):
        out = adapt_copy.adapt_for_platform("Post.", "x", ["#Onboarding", "#SaaS", "#CustomerSuccess"])
        self.assertEqual(out["hashtags"], "#Onboarding #SaaS")
        self.assertEqual(out["hashtags_dropped"], ["#CustomerSuccess"])

    def test_instagram_first_comment_reports_drops_too(self):
        tags = [f"#i{i}" for i in range(8)]
        out = adapt_copy.adapt_for_platform("Post.", "instagram", tags)
        self.assertEqual(out["first_comment"], "#i0 #i1 #i2 #i3 #i4")
        self.assertEqual(out["hashtags_dropped"], ["#i5", "#i6", "#i7"])

    def test_threads_keeps_one_topic_tag(self):
        out = adapt_copy.adapt_for_platform("Post.", "threads", ["#a", "#b"])
        self.assertEqual((out["hashtags"], out["hashtags_dropped"]), ("#a", ["#b"]))

    def test_the_cli_prints_it(self):
        code, out, _ = run_script("--text", "Post.", "--platform", "x", "--campaign-hashtags", "#a", "#b", "#c")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["hashtags_dropped"], ["#c"])

    def test_the_prose_tells_the_agent_to_tell_the_user(self):
        for rel in ("skills/adapt-copy/SKILL.md", "agents/copy-adapter.md"):
            text = read(REPO / rel)
            with self.subTest(file=rel):
                self.assertIn("hashtags_dropped", text)
                self.assertRegex(text, r"(?i)tell the user which")

    def test_plant_silent_dropping_is_caught(self):
        real = adapt_copy.adapt_for_platform

        def silent(*args, **kwargs):
            out = real(*args, **kwargs)
            out.pop("hashtags_dropped", None)
            return out
        wrapped = mock.Mock(PLATFORM_LIMITS=adapt_copy.PLATFORM_LIMITS, adapt_for_platform=silent)
        self.assertTrue(any("no hashtags_dropped" in p for p in hashtag_problems(wrapped)))

    def test_plant_a_wrong_dropped_list_is_caught(self):
        real = adapt_copy.adapt_for_platform

        def off_by_one(*args, **kwargs):
            out = real(*args, **kwargs)
            out["hashtags_dropped"] = out["hashtags_dropped"][1:]
            return out
        wrapped = mock.Mock(PLATFORM_LIMITS=adapt_copy.PLATFORM_LIMITS, adapt_for_platform=off_by_one)
        self.assertTrue(any("expected" in p or "full list" in p for p in hashtag_problems(wrapped)))


# ---------------------------------------------------------------------------
# Guard 4: docs match the data, and the adapter is not said to insert labels
# ---------------------------------------------------------------------------

def table_after(text, header_start):
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(header_start))
    rows = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def first_int(cell):
    return int(re.search(r"\d[\d,]*", cell).group(0).replace(",", ""))


def doc_table_problems(skill_text, specs_text, agent_text, limits, data):
    problems = []
    names = {k: v for k, v in SPEC_NAMES.items()}
    # skills/adapt-copy/SKILL.md
    rows = table_after(skill_text, "| Platform | Tone |")
    if [names[r[0]] for r in rows] != NINE:
        problems.append(f"SKILL.md table lists {[r[0] for r in rows]}, expected all nine platforms in order")
    for r in rows:
        key = names.get(r[0])
        if key not in limits:
            continue
        spec = limits[key]
        shown = first_int(r[2])
        want = spec.get("optimal_limit", spec["char_limit"])
        if shown != want:
            problems.append(f"SKILL.md {r[0]}: limit {shown}, data says {want}")
        if "optimal_limit" in spec and f"{spec['char_limit']:,}" not in r[2]:
            problems.append(f"SKILL.md {r[0]}: hard limit {spec['char_limit']:,} not shown")
        cap = int(r[3].split("/")[1].split()[0])
        if cap != spec["hashtag_limit"]:
            problems.append(f"SKILL.md {r[0]}: hashtag cap {cap}, data says {spec['hashtag_limit']}")
    # references/platform-specs.md
    for r in table_after(specs_text, "| Platform | Max Length |"):
        key = names.get(r[0])
        spec = limits[key]
        if first_int(r[1]) != spec["char_limit"]:
            problems.append(f"platform-specs {r[0]}: max {r[1]}, data says {spec['char_limit']}")
        entry = data["platforms"][key]
        status = ("confirmed" if "char_limit" in entry["confirmed"]
                  else "differs" if "char_limit" in entry["differs"] else "unsourced")
        if r[2] != status:
            problems.append(f"platform-specs {r[0]}: status {r[2]!r}, data says {status}")
    for r in table_after(specs_text, "| Platform | Platform maximum |"):
        key = names.get(r[0])
        if first_int(r[2]) != limits[key]["hashtag_limit"]:
            problems.append(f"platform-specs {r[0]}: script cap {r[2]}, data says {limits[key]['hashtag_limit']}")
    # agents/copy-adapter.md
    seen = []
    for line in agent_text.splitlines():
        m = re.match(r"^\s+- (LinkedIn|Instagram|X/Twitter|Facebook|YouTube|TikTok|Pinterest|Threads|Bluesky):(.*)$", line)
        if not m:
            continue
        key = names[m.group(1)]
        seen.append(key)
        spec = limits[key]
        body = m.group(2)
        shown = first_int(re.search(r"([\d,]+) chars", body).group(0))
        want = spec.get("optimal_limit", spec["char_limit"])
        if shown != want:
            problems.append(f"agent {m.group(1)}: {shown} chars, data says {want}")
        cap = re.search(r"script cap (\d+)", body)
        if not cap or int(cap.group(1)) != spec["hashtag_limit"]:
            problems.append(f"agent {m.group(1)}: script cap {cap.group(1) if cap else None}, data says {spec['hashtag_limit']}")
    if seen != NINE:
        problems.append(f"agent lists {seen}, expected {NINE}")
    return problems


_NEGATION = re.compile(r"(?i)\b(never|nothing|not|nor|no|none|neither|without|only reports|does nothing)\b")
_ACTOR = re.compile(r"(?i)(caption[- ]adapter|copy[- ]adapter|adapt_copy|adapt-copy|compliance_check)")
_ACTION = re.compile(r"(?i)\b(insert|inserts|inserted|append|appends|add|adds)\b")
_LABEL = re.compile(r"(?i)\b(label|disclosure|disclaimer)s?\b")


def label_claim_problems(text, where):
    """A sentence that says the adapter (or the compliance script) inserts a label or
    disclaimer, with no negation, is the false claim. A sentence that denies it is fine."""
    problems = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n", text):
        if _ACTOR.search(sentence) and _ACTION.search(sentence) and _LABEL.search(sentence) \
                and not _NEGATION.search(sentence):
            problems.append(f"{where}: claims code inserts a label: {sentence.strip()[:110]}")
    return problems


def key_recommendation_problems(lines):
    """`ai_disclosure_required` is read by nothing; a line may mention it only to say so."""
    return [f"recommends a key nothing reads: {line[:100]}" for line in lines
            if "ai_disclosure_required" in line
            and not re.search(r"(?i)does nothing|no script or skill reads", line)]


def inserted_label_problems(adapt):
    """Whatever the platform, copy in is copy out (plus the CTA): no label, no disclaimer."""
    problems = []
    body = "A short post about onboarding."
    for name in NINE:
        out = adapt(body, name, ["#a"], cta=None)
        if out["copy"] != body:
            problems.append(f"{name}: copy changed with no CTA: {out['copy']!r}")
        out = adapt(body, name, ["#a"], cta="Read more: https://example.com/p")
        if not out["copy"].startswith(body + "\n\n") or re.search(
                r"(?i)\b(AI|artificial|generated|label|disclos)", out["copy"]):
            problems.append(f"{name}: something other than the CTA was added: {out['copy']!r}")
    return problems


LABEL_DOCS = ["references/channel-changes-may-2026.md", "skills/adapt-copy/SKILL.md", "agents/copy-adapter.md",
              "skills/brand-manager/SKILL.md", "references/compliance-rules-schema.md", "docs/OPERATIONS.md"]

OLD_CLAIM = ("- Add `ai_disclosure_required: true` for TikTok / YouTube / EU markets so the caption-adapter "
             "inserts the required visible label.")
OLD_AGENT_CLAIM = "- `compliance_check.py` — Banned phrase detection + disclaimer insertion"


class TestDocsMatchTheDataAndTheCode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()
        cls.limits = {n: e["limits"] for n, e in cls.data["platforms"].items()}
        cls.skill = read(REPO / "skills" / "adapt-copy" / "SKILL.md")
        cls.specs = read(REPO / "references" / "platform-specs.md")
        cls.agent = read(REPO / "agents" / "copy-adapter.md")

    def test_the_limit_tables_in_the_docs_match_the_data(self):
        self.assertEqual(doc_table_problems(self.skill, self.specs, self.agent, self.limits, self.data), [])

    def test_the_skill_names_the_unsourced_limits_and_they_are_unsourced(self):
        for name in ("instagram", "facebook", "tiktok"):
            self.assertIn("char_limit", self.data["platforms"][name]["unsourced"])
        self.assertRegex(self.skill, r"(?s)character limits for Instagram, Facebook and TikTok were unsourced")
        self.assertIn("--sources", self.skill)
        self.assertIn("platform_limits.json", self.skill)

    def test_the_docs_explain_how_x_counts(self):
        for text in (self.skill, self.specs):
            self.assertIn("23", text)
        self.assertIn("x_weighted", self.skill)
        self.assertIn("graphemes", self.specs)
        self.assertIn("UTF-8 bytes", self.specs)

    def test_youtube_hashtag_max_is_the_pages_number_not_15(self):
        row = next(r for r in table_after(self.specs, "| Platform | Platform maximum |") if r[0] == "YouTube")
        self.assertIn("60", row[1])
        self.assertNotIn("15", row[1])

    def test_no_doc_says_the_adapter_inserts_a_label(self):
        for rel in LABEL_DOCS:
            with self.subTest(file=rel):
                self.assertEqual(label_claim_problems(read(REPO / rel), rel), [])

    def test_the_channel_changes_page_says_who_adds_the_label(self):
        text = read(REPO / "references" / "channel-changes-may-2026.md")
        self.assertIn("Visible AI labels in captions are a manual step", text)
        self.assertIn("no script or skill reads that key", text)
        self.assertNotIn(OLD_CLAIM, text)

    def test_the_agent_no_longer_says_compliance_check_inserts_disclaimers(self):
        text = self.agent
        self.assertNotIn(OLD_AGENT_CLAIM, text)
        self.assertIn("it inserts nothing", text)

    def test_no_code_reads_ai_disclosure_required(self):
        # The premise of the doc fix: the key the old page told you to set is read by nothing.
        readers = [p.name for p in SCRIPTS.glob("*.py") if "ai_disclosure_required" in read(p)]
        self.assertEqual(readers, [])

    def test_the_adapter_really_inserts_no_label(self):
        self.assertEqual(inserted_label_problems(adapt_copy.adapt_for_platform), [])

    def test_no_doc_recommends_a_key_nothing_reads(self):
        lines = []
        for rel in ("skills", "agents", "commands", "references", "docs"):
            for path in (REPO / rel).rglob("*.md"):
                lines += [f"{path.name}: {l}" for l in read(path).splitlines()]
        self.assertEqual(key_recommendation_problems(lines), [])

    # -- plants -------------------------------------------------------------------
    def test_plant_a_doc_table_number_that_disagrees_with_the_data(self):
        wrong = self.skill.replace("| Pinterest | Search-friendly description | 800 chars |",
                                   "| Pinterest | Search-friendly description | 500 chars |")
        self.assertNotEqual(wrong, self.skill)
        self.assertTrue(any("Pinterest" in p for p in doc_table_problems(wrong, self.specs, self.agent,
                                                                         self.limits, self.data)))
        wrong = self.specs.replace("| Threads | 1 topic tag per post | 1 |", "| Threads | 1 topic tag per post | 3 |")
        self.assertNotEqual(wrong, self.specs)
        self.assertTrue(any("Threads" in p for p in doc_table_problems(self.skill, wrong, self.agent,
                                                                       self.limits, self.data)))
        wrong = self.agent.replace("(script cap 1)", "(script cap 3)")
        self.assertNotEqual(wrong, self.agent)
        self.assertTrue(any("Threads" in p for p in doc_table_problems(self.skill, self.specs, wrong,
                                                                       self.limits, self.data)))
        wrong = self.specs.replace("| Pinterest | 800 | confirmed |", "| Pinterest | 800 | unsourced |")
        self.assertNotEqual(wrong, self.specs)
        self.assertTrue(any("status" in p for p in doc_table_problems(self.skill, wrong, self.agent,
                                                                      self.limits, self.data)))

    def test_plant_a_status_claim_upgraded_in_the_docs(self):
        wrong = self.specs.replace("| TikTok | 2,200 | unsourced |", "| TikTok | 2,200 | confirmed |")
        self.assertNotEqual(wrong, self.specs)
        self.assertTrue(any("TikTok" in p and "status" in p for p in doc_table_problems(
            self.skill, wrong, self.agent, self.limits, self.data)))

    def test_plant_the_false_label_claim_is_caught(self):
        self.assertTrue(label_claim_problems(OLD_CLAIM, "old page"), "the original sentence must be flagged")
        self.assertTrue(label_claim_problems("The copy adapter adds the AI disclosure label automatically.", "x"))
        self.assertTrue(label_claim_problems("adapt_copy.py appends a disclaimer to each caption.", "x"))
        # and the page as it stands once the old sentence is put back
        page = read(REPO / "references" / "channel-changes-may-2026.md")
        restored = page.replace(
            [l for l in page.splitlines() if l.startswith("- **Visible AI labels")][0], OLD_CLAIM)
        self.assertNotEqual(restored, page)
        self.assertTrue(label_claim_problems(restored, "restored"))
        # denials are not flagged
        self.assertEqual(label_claim_problems("`adapt_copy.py` adds no label to any caption.", "x"), [])
        self.assertEqual(label_claim_problems("Nothing inserts one: adapt_copy.py never adds a label.", "x"), [])

    def test_plant_the_agent_claim_coming_back(self):
        restored = self.agent.replace(
            [l for l in self.agent.splitlines() if l.startswith("- `compliance_check.py`")][0], OLD_AGENT_CLAIM)
        self.assertIn(OLD_AGENT_CLAIM, restored)
        self.assertNotIn("it inserts nothing", restored)  # what test_the_agent_no_longer_says... asserts

    def test_plant_a_recommended_key_nothing_reads(self):
        planted = ["x.md: - Add `ai_disclosure_required: true` for TikTok so it works."]
        self.assertTrue(key_recommendation_problems(planted))
        self.assertEqual(key_recommendation_problems(
            ["x.md: An earlier version told you to set `ai_disclosure_required: true`; "
             "no script or skill reads that key."]), [])

    def test_plant_the_adapter_inserting_a_label(self):
        real = adapt_copy.adapt_for_platform

        def inserting(text, platform, *a, **k):
            return real(text + " Created with AI", platform, *a, **k)
        self.assertTrue(inserted_label_problems(inserting))


if __name__ == "__main__":
    unittest.main()
