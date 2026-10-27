"""The model registry's dates and statuses must agree with each other and with the day it was reviewed.

This is the sibling copy of Digital Marketing Pro's tests/test_model_registry_dates.py. The registry is synced from
that canonical file (scripts/sync_model_registry.sh there), so what goes red as TIME passes (a shutdown date reached, a
retirement floor unchecked for 30 days, next_review_due gone by) is checked by DMP's weekly dated-checks job and reaches
this repo with the next sync. Here the rules run on the day the registry says it was last reviewed, which never changes,
so this suite cannot go red because the calendar moved.

The failures the rules prevent (all found in the 2026-10-04 registry on 2026-10-27):
  * latest-fast-anthropic pointed at Claude Haiku 4.5 three weeks after Haiku 5.5 shipped;
  * gemini-2.5-flash-image was marked "retired 2026-10-02": that was its RELEASE date (its shutdown is 2027-03-15);
  * Gemini 2.5 was marked deprecated with a shutdown date the vendor page no longer showed;
  * veo-3.0 entries fell forward to a preview id that had itself shut down.

Rules (ISO date strings):
  1. A `current`/`supported` entry with a `shutdown_date` on or before the review day is wrong: mark it retired.
     A `deprecated` entry past its `shutdown_date`: same.
  2. A `current`/`supported` entry past its `tentative_retirement` ("not sooner than") must carry `retirement_checked`
     on or after that date and at most RECHECK_DAYS old.
  3. No alias may point at a deprecated or retired id, or at one whose `shutdown_date` is within SHUTDOWN_WARN_DAYS.
  4. Every deprecated/retired entry's `replacement_id` exists and is current or supported.
  5. A retired entry is dropped DROP_AFTER_DAYS after its shutdown date.
  6. `next_review_due` is not before the review day.
  7. Kinds no vendor list endpoint can discover (text-to-speech, speech-to-text) are PINS: each entry carries `pinned_on` and
     `pin_expires`, at most PIN_MAX_DAYS apart. An expired pin is a failure in Digital Marketing Pro's weekly job, so someone
     re-reads the vendor page and re-pins; the pin dates ride in with the next registry sync.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / "scripts" / "model_registry.json"

RECHECK_DAYS = 30
SHUTDOWN_WARN_DAYS = 30
DROP_AFTER_DAYS = 120
LIVE = {"current", "supported"}
PINNED_TIERS = {"text-to-speech", "speech-to-text"}
PIN_MAX_DAYS = 92


def _d(value):
    return date.fromisoformat(value[:10]) if value else None


def registry_problems(reg: dict, on: date) -> list[str]:
    out = []
    models = {m["id"]: m for m in reg["models"]}
    for mid, m in models.items():
        status = m.get("status", "current")
        shut, floor, checked = _d(m.get("shutdown_date")), _d(m.get("tentative_retirement")), _d(m.get("retirement_checked"))
        if status in LIVE | {"deprecated"} and shut and shut <= on:
            out.append(f"{mid}: {status} but shut down {shut}; mark it retired")
        if status in LIVE and floor and floor < on:
            if not checked or checked < floor:
                out.append(f"{mid}: past its retirement floor {floor} with no retirement_checked on or after it")
            elif (on - checked).days > RECHECK_DAYS:
                out.append(f"{mid}: retirement floor {floor} passed; last checked {checked}, over {RECHECK_DAYS} days ago")
        if status in {"deprecated", "retired"}:
            rep = m.get("replacement_id")
            if not rep or rep not in models:
                out.append(f"{mid}: {status} with replacement {rep!r} missing from the registry")
            elif models[rep].get("status", "current") not in LIVE:
                out.append(f"{mid}: falls forward to {rep}, which is {models[rep].get('status')}")
        if status == "retired" and shut and (on - shut).days > DROP_AFTER_DAYS:
            out.append(f"{mid}: retired {shut}, over {DROP_AFTER_DAYS} days ago; drop it")
        pinned, expires = _d(m.get("pinned_on")), _d(m.get("pin_expires"))
        if m.get("tier") in PINNED_TIERS and not (pinned and expires):
            out.append(f"{mid}: {m['tier']} is a pinned kind; give it pinned_on and pin_expires")
        elif expires and expires < on:
            out.append(f"{mid}: pin expired {expires}; re-read {m.get('docs_url', 'the vendor page')} and re-pin")
        elif pinned and expires and (expires - pinned).days > PIN_MAX_DAYS:
            out.append(f"{mid}: pin runs {(expires - pinned).days} days; at most {PIN_MAX_DAYS}")
    for alias, target in reg.get("aliases", {}).items():
        m = models.get(target)
        if m is None:
            out.append(f"alias {alias}: target {target} missing")
            continue
        if m.get("status", "current") not in LIVE:
            out.append(f"alias {alias}: points at {target}, which is {m.get('status')}")
        shut = _d(m.get("shutdown_date"))
        if shut and shut - on <= timedelta(days=SHUTDOWN_WARN_DAYS):
            out.append(f"alias {alias}: {target} shuts down {shut}; repoint it")
    due = _d(reg.get("next_review_due"))
    if not due or due < on:
        out.append(f"next_review_due {reg.get('next_review_due')!r} is before {on}; review the registry")
    return out


RECORD_FAIL_DAYS = 45


def record_problems(hints: dict, on: date) -> list[str]:
    """The router's hand-read lifecycle record (scripts/model_hints.json 'deprecations') goes stale like any pin: the router
    warns in its own output after 30 days, and a maintainer's check on a given day fails it after 45. Like the registry check
    above, the suite judges it on a day it is given, never on the wall clock, so a customer's test run does not turn red."""
    out = []
    for provider, record in (hints.get("deprecations") or {}).items():
        age = (on - date.fromisoformat(record["read_on"])).days
        if age > RECORD_FAIL_DAYS:
            out.append(f"deprecations.{provider} read {record['read_on']}, {age} days ago; re-read {record['source']}")
    return out


class TestRegistryDates(unittest.TestCase):

    def test_registry_is_consistent_on_the_day_it_was_reviewed(self):
        reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
        problems = registry_problems(reg, _d(reg["last_updated"]))
        self.assertEqual(problems, [], "\n  " + "\n  ".join(problems))

    def test_plants_from_the_2026_10_04_registry(self):
        old = {
            "next_review_due": "2026-11-01",
            "aliases": {"latest-fast-anthropic": "claude-haiku-4-5-20251001",
                        "latest-image-balanced-google": "gemini-3.1-flash-image"},
            "models": [
                # Haiku 4.5: floor passed, nobody re-checked
                {"id": "claude-haiku-4-5-20251001", "status": "current", "tentative_retirement": "2026-10-15"},
                # Nano Banana 2 deprecated on 2026-10-06 but still the alias target
                {"id": "gemini-3.1-flash-image", "status": "deprecated", "replacement_id": "gemini-nano-banana-2.1"},
                {"id": "gemini-nano-banana-2.1", "status": "current"},
                # veo-3.0 falling forward to a retired preview
                {"id": "veo-3.1-generate-preview", "status": "retired", "shutdown_date": "2026-10-22",
                 "replacement_id": "veo-3.1-generate-001"},
                {"id": "veo-3.1-generate-001", "status": "current"},
                {"id": "veo-3.0-generate-001", "status": "retired", "shutdown_date": "2026-06-30",
                 "replacement_id": "veo-3.1-generate-preview"},
                # deprecated with a shutdown that passed
                {"id": "gemini-2.5-flash", "status": "deprecated", "shutdown_date": "2026-10-16",
                 "replacement_id": "gemini-nano-banana-2.1"},
            ],
        }
        joined = "\n".join(registry_problems(old, date(2026, 11, 20)))
        for expected in ("claude-haiku-4-5-20251001: past its retirement floor",
                         "alias latest-image-balanced-google: points at gemini-3.1-flash-image",
                         "veo-3.0-generate-001: falls forward to veo-3.1-generate-preview",
                         "gemini-2.5-flash: deprecated but shut down",
                         "veo-3.0-generate-001: retired 2026-06-30, over",
                         "next_review_due"):
            self.assertIn(expected, joined)

    def test_the_router_hint_books_record_is_consistent_on_the_day_it_was_read(self):
        hints = json.loads((REPO / "scripts" / "model_hints.json").read_text(encoding="utf-8"))
        problems = record_problems(hints, date.fromisoformat(hints["deprecations"]["google"]["read_on"]))
        self.assertEqual(problems, [], "\n  " + "\n  ".join(problems))

    def test_a_record_read_more_than_45_days_ago_is_a_problem(self):
        hints = {"deprecations": {"google": {"read_on": "2026-10-27", "source": "https://x"}}}
        self.assertEqual(record_problems(hints, date(2026, 12, 11)), [])
        self.assertIn("46 days ago", "\n".join(record_problems(hints, date(2026, 12, 12))))

    def test_recheck_and_shutdown_windows(self):
        reg = {"next_review_due": "2027-01-01", "aliases": {"a": "x"},
               "models": [{"id": "x", "status": "current", "shutdown_date": "2026-11-20"},
                          {"id": "y", "status": "supported", "tentative_retirement": "2026-10-15",
                           "retirement_checked": "2026-10-27"}]}
        self.assertEqual(registry_problems(reg, date(2026, 10, 1)), [])
        late = "\n".join(registry_problems(reg, date(2026, 11, 30)))
        self.assertIn("alias a: x shuts down", late)
        self.assertIn("y: retirement floor 2026-10-15 passed; last checked 2026-10-27", late)

    def test_the_registry_carries_the_new_date_fields_and_param_notes(self):
        reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.assertIn("anthropic_sampling_parameters", reg["param_compatibility_notes"])
        self.assertIn("veo_backend", reg["param_compatibility_notes"])
        self.assertNotIn("claude_opus_4_7_and_later", reg["param_compatibility_notes"])
        self.assertTrue(any("shutdown_date" in m for m in reg["models"]))


class TestSpeechPins(unittest.TestCase):
    """The speech models are pins that expire: no list endpoint tells a speech model from a chat model, and three defaults
    (a text-to-speech id, two transcription ids) were deprecated before anything in the suite said so."""

    def setUp(self):
        self.reg = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_every_speech_kind_has_an_alias_per_vendor(self):
        for kind in ("tts", "stt"):
            for vendor in ("openai", "elevenlabs", "sarvam"):
                self.assertIn(f"latest-{kind}-{vendor}", self.reg["aliases"])

    def test_speech_aliases_resolve_to_their_kind(self):
        models = {m["id"]: m for m in self.reg["models"]}
        tier = {"tts": "text-to-speech", "stt": "speech-to-text"}
        for alias, target in self.reg["aliases"].items():
            kind = alias.split("-")[1]
            if kind in tier:
                self.assertEqual(models[target]["tier"], tier[kind], alias)

    def test_plants(self):
        base = {"next_review_due": "2027-06-01", "aliases": {}}
        unpinned = dict(base, models=[{"id": "t", "status": "current", "tier": "text-to-speech"}])
        self.assertIn("t: text-to-speech is a pinned kind", "\n".join(registry_problems(unpinned, date(2026, 10, 27))))
        pinned = dict(base, models=[{"id": "t", "status": "current", "tier": "speech-to-text",
                                     "pinned_on": "2026-10-27", "pin_expires": "2027-01-25"}])
        self.assertEqual(registry_problems(pinned, date(2027, 1, 25)), [])
        self.assertIn("t: pin expired 2027-01-25", "\n".join(registry_problems(pinned, date(2027, 1, 26))))
        forever = dict(base, models=[dict(pinned["models"][0], pin_expires="2099-01-01")])
        self.assertIn("at most 92", "\n".join(registry_problems(forever, date(2026, 10, 27))))


class TestCheckParamsScope(unittest.TestCase):
    """API version 2026-10-21 rejects temperature/top_p/top_k on every Anthropic model."""

    def scan(self, code: str):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
        try:
            return subprocess.run([sys.executable, str(REPO / "scripts" / "resolve_model.py"),
                                   "--check-params", f.name, "--json"],
                                  capture_output=True, text=True, timeout=60)
        finally:
            os.unlink(f.name)

    def test_scan_flags_any_claude_target(self):
        proc = self.scan('c.messages.create(model="claude-haiku-5-5", max_tokens=10, temperature=0.2)\n')
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["targets_anthropic"])
        self.assertEqual(payload["findings"][0]["param"], "temperature")

    def test_scan_flags_a_latest_anthropic_alias(self):
        proc = self.scan('model = resolve("latest-fast-anthropic")\nc.create(model=model, top_p=0.9)\n')
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["findings"][0]["param"], "top_p")

    def test_the_old_opus_only_scan_would_have_missed_both(self):
        # The earlier scan looked for claude-opus-4-7/4-8 only; a Haiku 5.5 or Sonnet 5.5 call passed clean.
        old_pattern = re.compile(r"claude-opus-4-[78]")
        self.assertIsNone(old_pattern.search('model="claude-haiku-5-5", temperature=0.2'))
        self.assertIsNone(old_pattern.search('model="claude-sonnet-5-5", top_k=5'))

    def test_a_file_with_no_anthropic_target_is_skipped(self):
        proc = self.scan('requests.post(url, json={"temperature": 0.2})\n')
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse(json.loads(proc.stdout)["targets_anthropic"])


if __name__ == "__main__":
    unittest.main()
