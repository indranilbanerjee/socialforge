"""1.30.0: the vision model for asset indexing comes from the Gemini API's own model list, not from a name.

Before 1.30.0 `index_assets.py` asked the shipped registry for the alias `latest-vision-google` and sent whatever id that
named. The registry is reviewed by hand, so an indexing run could be sent to a model Google had since shut down, or miss a
newer one the key could already use. Now the id is decided once per run, in this order:

  1. the brand's pin (`model_pins` in brand-config.json), then
  2. `--model`, then
  3. `scripts/model_router.py`, which lists the models the key can use (`GET .../v1beta/models`, the key in the
     x-goog-api-key header) and takes the newest active, generally available Flash in the hint book's family, then
  4. the registry alias `latest-vision-google`, tagged "offline", when the list cannot be read or the run is served by Vertex AI.

A pin or `--model` is a name asked for: the router keeps it with a warning if it is deprecated and refuses it, exit 2, if it
is retired. Nothing is swapped silently, and the index records what was asked, what was sent, and where the answer came from.

`scripts/model_router.py` is the suite's canonical file copied byte for byte; the first group below keeps it identical.
The fixtures in tests/fixtures/model_router/ follow the documented models.list shape; the hint book's record is what an
agent read from Google's deprecations page on 2026-10-27.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import types
import unittest
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "model_router"
sys.path.insert(0, str(SCRIPTS))

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
KEY = "g-test-0000-not-a-real-google-key"
CRED = "GEMINI_API_KEY"
JOB = "index-assets.vision.google"
ROUTER_SHA256 = "9e179aef1a78647897129584744b5e013713b546aab512dd7cfac376d78ed547"  # the canonical file, LF as git stores it


def committed_bytes(path: Path) -> bytes:
    """The file as git stores it: a checkout with core.autocrlf=true writes CRLF on disk while the committed blob stays LF."""
    return path.read_bytes().replace(b"\r\n", b"\n")


def load_hints() -> dict:
    return json.loads((SCRIPTS / "model_hints.json").read_text(encoding="utf-8-sig"))


def list_fixture() -> list:
    return copy.deepcopy(json.loads((FIXTURES / "google_models.json").read_text(encoding="utf-8"))["models"])


def entry(mid: str, methods=("generateContent", "countTokens")) -> dict:
    return {"name": f"models/{mid}", "baseModelId": mid, "version": "001", "displayName": mid,
            "supportedGenerationMethods": list(methods)}


class Fetch:
    """A stand-in for the list call: counts calls, checks the key it was handed, raises when told to."""

    def __init__(self, data=None, error=None):
        self.data, self.error, self.calls = data, error, 0

    def __call__(self, api_key, _version=None):
        self.calls += 1
        assert api_key == KEY, "the router must hand the list call the key from GEMINI_API_KEY"
        if self.error:
            raise self.error
        return copy.deepcopy(self.data if self.data is not None else list_fixture())


# --- the canonical router, copied byte for byte --------------------------------------------------------------------

class TestRouterCopy(unittest.TestCase):

    def test_the_copy_is_the_canonical_file_as_git_stores_it(self):
        digest = hashlib.sha256(committed_bytes(SCRIPTS / "model_router.py")).hexdigest()
        self.assertEqual(digest, ROUTER_SHA256,
                         "scripts/model_router.py differs from the suite's canonical file; copy it again, byte for byte, "
                         "and update ROUTER_SHA256 only when the canonical file itself changed")

    def test_it_matches_the_canonical_checkout_when_that_is_beside_this_one(self):
        canonical = REPO.parent / "digital-marketing-pro" / "scripts" / "model_router.py"
        if not canonical.exists():
            self.skipTest("the canonical checkout is not beside this one")
        self.assertEqual(committed_bytes(SCRIPTS / "model_router.py"), committed_bytes(canonical))

    def test_plant_line_endings_are_not_a_difference_but_a_changed_byte_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            lf, crlf, edited = Path(tmp, "lf.py"), Path(tmp, "crlf.py"), Path(tmp, "edited.py")
            lf.write_bytes(b"a = 1\nb = 2\n")
            crlf.write_bytes(b"a = 1\r\nb = 2\r\n")
            edited.write_bytes(b"a = 1\nb = 3\n")
            self.assertEqual(committed_bytes(crlf), committed_bytes(lf))
            self.assertNotEqual(committed_bytes(edited), committed_bytes(lf))

    def test_it_has_a_google_adapter(self):
        import model_router
        self.assertIn("google", model_router.ADAPTERS)


# --- SF's hint book -------------------------------------------------------------------------------------------------

class TestHintBook(unittest.TestCase):

    def test_the_hint_book_is_valid(self):
        import model_router
        self.assertEqual(model_router.validate_hints(load_hints()), [])

    def test_the_vision_job_names_a_family_and_the_method_it_calls_never_an_id(self):
        rule = load_hints()["jobs"][JOB]
        self.assertEqual((rule["provider"], rule["capabilities"], rule["default_alias"]),
                         ("google", ["generateContent"], "latest-vision-google"))
        self.assertTrue(rule["family"].startswith("^") and "(?P<version>" in rule["family"])
        self.assertTrue(rule["source"].startswith("https://"))
        self.assertNotIn("model", rule)

    def test_the_default_alias_exists_in_the_registry(self):
        from resolve_model import resolve
        self.assertTrue(resolve(load_hints()["jobs"][JOB]["default_alias"]))

    def test_the_record_is_the_deprecations_page_with_its_source_and_date(self):
        record = load_hints()["deprecations"]["google"]
        self.assertEqual(record["source"], "https://ai.google.dev/gemini-api/docs/deprecations")
        self.assertRegex(record["read_on"], r"^\d{4}-\d{2}-\d{2}$")
        rows = record["models"].values()
        self.assertTrue(any(r.get("shut_down") for r in rows), "the page greys out shut-down models; the record keeps that")
        self.assertTrue(any(r.get("redirects_to") for r in rows), "the page names models whose endpoint now routes elsewhere")

    def test_the_pick_today_is_the_newest_flash_the_key_lists_and_never_a_redirect_lite_tts_latest_or_preview(self):
        import model_router
        routing = model_router.route(JOB, load_hints(), provider="google", credential_name=CRED, api_key=KEY,
                                     default_model="x", fetch=Fetch(), now=NOW, env={})
        self.assertEqual((routing["model"], routing["basis"]), ("gemini-3.8-flash", "live"))
        for never in ("gemini-3.7-flash", "gemini-3.5-flash", "gemini-2.0-flash", "gemini-flash-latest",
                      "gemini-3-flash-preview", "gemini-3.8-flash-tts", "gemini-3.5-flash-lite"):
            self.assertNotEqual(routing["model"], never)


# --- choosing the model ---------------------------------------------------------------------------------------------

class VisionCase(unittest.TestCase):
    def setUp(self):
        import index_assets
        self.ia = index_assets
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = Path(self.tmp.name) / "model-router-cache.json"

    def pick(self, fetch=None, brand_config=None, cli_model=None, backend="ai-studio-fallback", env=None, now=NOW,
             cache=True):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            return self.ia.choose_vision_model(brand_config, cli_model, backend=backend, api_key=KEY, fetch=fetch, now=now,
                                               cache_path=self.cache if cache else None, env={} if env is None else env)


class TestChooseVisionModel(VisionCase):

    def test_with_no_pin_and_no_flag_the_router_takes_the_newest_flash_from_the_live_list(self):
        fetch = Fetch()
        got = self.pick(fetch)
        self.assertEqual((got["model"], got["basis"], got["selected_by"], got["model_requested"]),
                         ("gemini-3.8-flash", "live", "router", None))
        self.assertEqual(got["source"], "https://generativelanguage.googleapis.com/v1beta/models")
        self.assertEqual(got["job"], JOB)
        self.assertTrue(got["discovered_at"] and got["decided_at"])
        self.assertEqual(fetch.calls, 1)

    def test_the_second_run_inside_the_week_reads_the_cache_and_calls_nothing(self):
        self.pick(Fetch())
        fetch = Fetch()
        got = self.pick(fetch)
        self.assertEqual((got["model"], got["basis"], fetch.calls), ("gemini-3.8-flash", "cache", 0))

    def test_the_brand_pin_beats_the_flag_and_says_so(self):
        got = self.pick(Fetch(), brand_config={"model_pins": {JOB: "gemini-3.6-flash"}}, cli_model="gemini-2.5-flash")
        self.assertEqual((got["model"], got["selected_by"], got["basis"], got["model_requested"]),
                         ("gemini-3.6-flash", "brand-pin", "requested", "gemini-3.6-flash"))
        self.assertTrue(any("--model" in w and "gemini-3.6-flash" in w for w in got["warnings"]), got["warnings"])

    def test_the_flag_beats_the_router(self):
        got = self.pick(Fetch(), cli_model="gemini-2.5-flash")
        self.assertEqual((got["model"], got["selected_by"], got["basis"]), ("gemini-2.5-flash", "--model", "requested"))

    def test_a_models_prefix_on_the_flag_is_understood(self):
        got = self.pick(Fetch(), cli_model="models/gemini-3.6-flash")
        self.assertEqual((got["model"], got["model_requested"]), ("gemini-3.6-flash", "gemini-3.6-flash"))
        self.assertEqual(got["warnings"], [])

    def test_a_pin_the_page_marks_shut_down_is_refused_naming_the_replacement_and_sends_nothing(self):
        import model_router
        with self.assertRaises(model_router.RouterError) as ctx:
            self.pick(Fetch(), brand_config={"model_pins": {JOB: "gemini-2.0-flash"}})
        self.assertEqual(ctx.exception.exit_code, 2)
        self.assertIn("gemini-2.0-flash is retired", ctx.exception.reason)
        self.assertIn("gemini-3.6-flash", ctx.exception.reason)

    def test_a_deprecated_pin_is_kept_with_a_warning_naming_the_date_and_the_replacement(self):
        got = self.pick(Fetch(), brand_config={"model_pins": {JOB: "gemini-3.1-flash-lite"}})
        self.assertEqual((got["model"], got["basis"]), ("gemini-3.1-flash-lite", "requested"))
        warning = " ".join(got["warnings"])
        self.assertIn("deprecated", warning)
        self.assertIn("2027-05-07", warning)
        self.assertIn("gemini-3.5-flash-lite", warning)

    def test_a_redirected_model_asked_for_by_name_is_kept_with_a_warning_that_the_answer_comes_from_another(self):
        got = self.pick(Fetch(), cli_model="gemini-3.7-flash")
        self.assertEqual(got["model"], "gemini-3.7-flash")
        self.assertIn("gemini-3.8-flash", " ".join(got["warnings"]))

    def test_a_malformed_pin_is_refused_never_ignored(self):
        import model_router
        for bad in ({"model_pins": {JOB: 3}}, {"model_pins": {JOB: ""}}, {"model_pins": ["x"]}, {"model_pins": {JOB: ["a"]}}):
            with self.subTest(pin=bad), self.assertRaises(model_router.RouterError) as ctx:
                self.pick(Fetch(), brand_config=bad)
            self.assertEqual(ctx.exception.exit_code, 2)
            self.assertIn("model_pins", ctx.exception.reason)

    def test_a_pin_for_another_job_is_not_this_jobs_pin(self):
        got = self.pick(Fetch(), brand_config={"model_pins": {"some.other.job": "gemini-2.5-flash"}})
        self.assertEqual((got["model"], got["selected_by"]), ("gemini-3.8-flash", "router"))

    def test_a_model_the_record_does_not_know_is_held_back_and_named(self):
        data = list_fixture() + [entry("gemini-3.9-flash")]
        got = self.pick(Fetch(data))
        self.assertEqual(got["model"], "gemini-3.8-flash")
        self.assertIn("no known release date", " ".join(got["warnings"]))

    def test_a_record_read_long_ago_is_named(self):
        got = self.pick(Fetch(), now=datetime(2026, 12, 20, tzinfo=timezone.utc), cache=False)
        self.assertIn("deprecations record was read", " ".join(got["warnings"]))

    def test_no_flash_the_key_may_call_is_refused_and_nothing_is_swapped(self):
        import model_router
        data = [entry("gemini-3.8-flash", methods=("bidiGenerateContent",)), entry("gemini-embedding-2", ("embedContent",))]
        with self.assertRaises(model_router.RouterError) as ctx:
            self.pick(Fetch(data))
        self.assertEqual(ctx.exception.exit_code, 2)

    def test_a_rejected_key_refuses_and_names_the_credential(self):
        import model_router
        fetch = Fetch(error=model_router.FetchError("auth", "HTTP 401 invalid x", 401))
        with self.assertRaises(model_router.RouterError) as ctx:
            self.pick(fetch)
        self.assertIn(CRED, ctx.exception.reason)
        self.assertNotIn(KEY, ctx.exception.reason)

    def test_a_list_timeout_falls_back_to_the_registry_alias_tagged_offline_with_the_reason(self):
        import model_router
        from resolve_model import resolve
        got = self.pick(Fetch(error=model_router.FetchError("timeout", "timed out")))
        self.assertEqual((got["model"], got["basis"], got["selected_by"]),
                         (resolve("latest-vision-google"), "offline", "registry-alias"))
        self.assertIn("timed out", got["reason"])
        self.assertEqual(got["source"], "shipped-default")

    def test_offline_env_makes_no_call_and_still_checks_the_name_asked_for_against_the_registry(self):
        import model_router
        from resolve_model import resolve
        fetch = Fetch()
        got = self.pick(fetch, env={model_router.OFFLINE_ENV: "1"})
        self.assertEqual((got["model"], got["basis"], fetch.calls), (resolve("latest-vision-google"), "offline", 0))
        reg = json.loads((SCRIPTS / "model_registry.json").read_text(encoding="utf-8"))
        retired = next((m for m in reg["models"] if m.get("vendor") == "google" and m.get("status") == "retired"), None)
        if retired:
            with self.assertRaises(model_router.RouterError):
                self.pick(Fetch(), cli_model=retired["id"], env={model_router.OFFLINE_ENV: "1"})

    def test_a_vertex_run_never_lists_the_gemini_api_models_even_with_a_key_set(self):
        from resolve_model import resolve
        for backend in ("vertex-ai", "vertex-ai-env"):
            with self.subTest(backend=backend):
                fetch = Fetch()
                got = self.pick(fetch, backend=backend)
                self.assertEqual((got["model"], got["basis"], got["selected_by"], fetch.calls),
                                 (resolve("latest-vision-google"), "offline", "registry-alias", 0))
                self.assertIn("Vertex", got["reason"])

    def test_the_cache_holds_the_credential_name_and_chosen_ids_and_never_the_key_or_the_list(self):
        self.pick(Fetch())
        text = self.cache.read_text(encoding="utf-8")
        self.assertNotIn(KEY, text)
        self.assertIn(CRED, text)
        self.assertNotIn("gemini-3.7-flash", text, "the cache must not keep the list")

    def test_a_corrupted_cache_is_rebuilt_with_a_warning(self):
        self.cache.write_text("{not json", encoding="utf-8")
        fetch = Fetch()
        got = self.pick(fetch)
        self.assertEqual((got["model"], got["basis"], fetch.calls), ("gemini-3.8-flash", "live", 1))
        self.assertIn("unreadable", " ".join(got["warnings"]))


OFFLINE = {"MODEL_ROUTER_OFFLINE": "1"}


class TestOfflineAndVertexLifecycle(VisionCase):
    """1.30.1. With no live list, a named model is checked against the hint book's Gemini API deprecations record as well as the
    registry (1.30.0 checked only the registry, so a pin on a model the record says is shut down was sent with a warning that
    it was 'not in the shipped registry'). The record describes the Gemini API; Vertex AI retires Gemini models on its own
    schedule, so a Vertex run must not be refused by it, and the registry's Gemini lifecycle data is the same kind of claim."""

    SHUT_DOWN = "gemini-2.0-flash"        # the record: shut_down, 2026-06-01, replacement gemini-3.6-flash; not in the registry
    REGISTRY_RETIRED = "gemini-omni-flash-preview"   # the registry marks it retired (and so does the record)

    def test_offline_a_pin_on_a_model_the_record_says_is_shut_down_is_refused_naming_the_record_and_the_replacement(self):
        import model_router
        with self.assertRaises(model_router.RouterError) as ctx:
            self.pick(Fetch(), brand_config={"model_pins": {JOB: self.SHUT_DOWN}}, env=OFFLINE)
        self.assertEqual(ctx.exception.exit_code, 2)
        reason = ctx.exception.reason
        self.assertIn(f"{self.SHUT_DOWN} is retired", reason)
        self.assertIn("2026-06-01", reason)
        self.assertIn("deprecations record", reason)
        self.assertIn("gemini-3.6-flash", reason)

    def test_offline_the_flag_is_checked_the_same_way(self):
        import model_router
        with self.assertRaises(model_router.RouterError):
            self.pick(Fetch(), cli_model=self.SHUT_DOWN, env=OFFLINE)

    def test_a_list_that_cannot_be_read_takes_the_same_check(self):
        import model_router
        for error in (model_router.FetchError("timeout", "timed out"), model_router.FetchError("unavailable", "HTTP 503", 503)):
            with self.subTest(kind=error.kind), self.assertRaises(model_router.RouterError):
                self.pick(Fetch(error=error), brand_config={"model_pins": {JOB: self.SHUT_DOWN}})

    def test_a_list_longer_than_the_page_cap_is_not_used_and_the_run_falls_back_offline_with_the_reason(self):
        import model_router

        class Page(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def endless(req, timeout=None):
            return Page(json.dumps({"models": [{"name": "models/gemini-3.8-flash",
                                                "supportedGenerationMethods": ["generateContent"]}],
                                    "nextPageToken": "more"}).encode("utf-8"))

        from resolve_model import resolve
        got = self.pick(lambda key, version: model_router.fetch_google(key, version, urlopen=endless))
        self.assertEqual((got["model"], got["basis"], got["selected_by"]), (resolve("latest-vision-google"), "offline", "registry-alias"))
        self.assertIn(f"more than {model_router.MAX_PAGES} pages", got["reason"])

    def test_offline_a_redirected_model_asked_for_warns_that_the_answer_comes_from_another(self):
        got = self.pick(Fetch(), cli_model="gemini-3.5-flash", env=OFFLINE)
        self.assertEqual(got["model"], "gemini-3.5-flash")
        self.assertIn("routes requests for it to gemini-3.6-flash", " ".join(got["warnings"]))

    def test_offline_an_unknown_name_is_named_as_unchecked(self):
        got = self.pick(Fetch(), cli_model="gemini-9.9-flash", env=OFFLINE)
        self.assertEqual(got["model"], "gemini-9.9-flash")
        self.assertIn("lifecycle could not be checked", " ".join(got["warnings"]))

    def test_vertex_the_gemini_api_record_does_not_refuse_a_pin(self):
        for backend in ("vertex-ai", "vertex-ai-env"):
            with self.subTest(backend=backend):
                fetch = Fetch()
                got = self.pick(fetch, backend=backend, brand_config={"model_pins": {JOB: self.SHUT_DOWN}})
                self.assertEqual((got["model"], got["selected_by"], got["basis"], fetch.calls),
                                 (self.SHUT_DOWN, "brand-pin", "offline", 0))
                self.assertNotIn("deprecations record", " ".join(got["warnings"] + [got["reason"] or ""]))

    def test_vertex_the_registrys_gemini_lifecycle_data_does_not_refuse_either(self):
        got = self.pick(Fetch(), backend="vertex-ai", cli_model=self.REGISTRY_RETIRED)
        self.assertEqual(got["model"], self.REGISTRY_RETIRED)

    def test_the_same_registry_retired_name_is_refused_offline_on_the_gemini_api(self):
        import model_router
        with self.assertRaises(model_router.RouterError):
            self.pick(Fetch(), cli_model=self.REGISTRY_RETIRED, env=OFFLINE)

    def test_vertex_says_a_name_asked_for_was_not_checked_against_the_gemini_apis_data(self):
        got = self.pick(Fetch(), backend="vertex-ai", brand_config={"model_pins": {JOB: self.SHUT_DOWN}})
        note = " ".join(got["warnings"])
        self.assertIn("Vertex AI", note)
        self.assertIn(self.SHUT_DOWN, note)
        self.assertIn("not checked", note)

    def test_vertex_with_no_name_asked_for_adds_no_such_note(self):
        got = self.pick(Fetch(), backend="vertex-ai")
        self.assertNotIn("not checked", " ".join(got["warnings"]))

    def test_vertex_never_reports_a_stale_gemini_api_record(self):
        late = datetime(2027, 1, 20, tzinfo=timezone.utc)
        vertex = self.pick(Fetch(), backend="vertex-ai", now=late)
        self.assertNotIn("deprecations record was read", " ".join(vertex["warnings"]))
        api = self.pick(Fetch(), env=OFFLINE, now=late)
        self.assertIn("deprecations record was read", " ".join(api["warnings"]))


# --- a whole indexing run --------------------------------------------------------------------------------------------

REPLY = json.dumps({"description": "A person at a desk.", "subjects": ["person"], "tags": ["desk", "office"],
                    "dominant_colors_hex": ["#112233"], "mood": "calm", "lighting": "natural", "setting": "indoor office",
                    "suitable_for": ["team post"], "background_removable": False, "style_reference_worthy": True})


class FakeClient:
    def __init__(self):
        self.sent = []
        self.models = self

    def generate_content(self, model, contents):
        self.sent.append(model)
        return types.SimpleNamespace(text=REPLY)


def fake_genai():
    """Stand-ins for the google-genai modules index_assets imports, so a run needs no SDK and no network."""
    part = types.SimpleNamespace(from_bytes=lambda data, mime_type: {"mime": mime_type, "bytes": len(data)})
    sdk_types = types.ModuleType("google.genai.types")
    sdk_types.Part = part
    genai = types.ModuleType("google.genai")
    genai.types = sdk_types
    google = types.ModuleType("google")
    google.genai = genai
    return {"google": google, "google.genai": genai, "google.genai.types": sdk_types}


class IndexRunCase(VisionCase):
    def setUp(self):
        super().setUp()
        self.work = Path(self.tmp.name)
        self.photos = self.work / "photos"
        self.photos.mkdir()
        for name in ("a.jpg", "b.png", "c.webp"):
            (self.photos / name).write_bytes(b"\x89not-really-an-image" + name.encode())
        self.ws = self.work / "ws"
        (self.ws / "brands" / "acme").mkdir(parents=True)
        self.cache = self.ws / self.ia.ROUTER_CACHE_NAME
        self.client = FakeClient()
        patches = [mock.patch.object(self.ia, "WORKSPACE", self.ws),
                   mock.patch.object(self.ia, "open_client", lambda: (self.client, self.backend, None)),
                   mock.patch.dict(sys.modules, fake_genai()),
                   mock.patch.dict(os.environ, {CRED: KEY})]
        self.backend = "ai-studio-fallback"
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        for var in (self.ia.model_router.OFFLINE_ENV,):
            os.environ.pop(var, None)

    def write_config(self, config: dict):
        (self.ws / "brands" / "acme" / "brand-config.json").write_text(json.dumps(config), encoding="utf-8")

    def run_index(self, fetch=None, refresh=False, model=None):
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                self.ia.index_all("acme", str(self.photos), refresh, model=model, fetch=fetch, now=NOW)
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def index(self) -> dict:
        return json.loads((self.ws / "brands" / "acme" / "asset-index.json").read_text(encoding="utf-8"))


class TestIndexRunRecordsTheChoice(IndexRunCase):

    def test_every_image_is_sent_to_the_model_the_router_chose_and_the_list_is_read_once(self):
        fetch = Fetch()
        code, out, _ = self.run_index(fetch)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.client.sent, ["gemini-3.8-flash"] * 3)
        self.assertEqual(fetch.calls, 1)

    def test_the_index_records_what_was_asked_what_was_sent_and_where_the_answer_came_from(self):
        self.run_index(Fetch())
        block = self.index()["vision_model"]
        for field in ("model", "model_requested", "selected_by", "basis", "source", "discovered_at", "decided_at", "warnings"):
            self.assertIn(field, block)
        self.assertEqual((block["model"], block["basis"], block["selected_by"], block["model_requested"]),
                         ("gemini-3.8-flash", "live", "router", None))

    def test_each_analysed_asset_names_the_model_that_analysed_it(self):
        self.run_index(Fetch())
        for asset in self.index()["assets"]:
            self.assertEqual(asset["analysis_model"], "gemini-3.8-flash", asset["id"])
            self.assertRegex(asset["analyzed_at"], r"^\d{4}-\d{2}-\d{2}T")

    def test_the_summary_printed_to_the_user_carries_the_same_record(self):
        _, out, _ = self.run_index(Fetch())
        summary = json.loads(out[out.index("{"):])
        self.assertEqual(summary["vision_model"]["model"], "gemini-3.8-flash")

    def test_a_brand_pin_in_brand_config_is_what_is_sent(self):
        self.write_config({"brand_name": "Acme", "model_pins": {JOB: "gemini-3.6-flash"}})
        self.run_index(Fetch())
        self.assertEqual(set(self.client.sent), {"gemini-3.6-flash"})
        self.assertEqual(self.index()["vision_model"]["selected_by"], "brand-pin")

    def test_an_unreadable_brand_config_is_named_not_ignored_silently(self):
        (self.ws / "brands" / "acme" / "brand-config.json").write_text("{nope", encoding="utf-8")
        _, _, err = self.run_index(Fetch())
        self.assertIn("brand-config.json", err)
        self.assertIn("no model pin", err)

    def test_a_retired_pin_stops_the_run_before_any_image_is_sent_and_before_any_index_is_written(self):
        self.write_config({"model_pins": {JOB: "gemini-2.0-flash"}})
        code, out, _ = self.run_index(Fetch())
        self.assertEqual(code, 2)
        self.assertEqual(self.client.sent, [])
        self.assertFalse((self.ws / "brands" / "acme" / "asset-index.json").exists())
        error = json.loads(out)
        self.assertEqual(error["stage"], "model routing")
        self.assertIn("gemini-3.6-flash", error["error"])

    def test_a_rejected_key_stops_the_run_with_exit_2_and_sends_nothing(self):
        import model_router
        code, out, _ = self.run_index(Fetch(error=model_router.FetchError("auth", "HTTP 401", 401)))
        self.assertEqual((code, self.client.sent), (2, []))
        refusal = json.loads(out)
        self.assertIn(CRED, refusal["error"])
        # A rejected, denied or unpaid key fails every image the same way, so offline mode would only move the failure.
        self.assertNotIn("MODEL_ROUTER_OFFLINE", json.dumps(refusal), "offline mode does not fix a rejected key")

    def test_an_offline_gemini_api_run_with_a_pin_on_a_shut_down_model_stops_and_sends_nothing(self):
        self.write_config({"model_pins": {JOB: "gemini-2.0-flash"}})
        with mock.patch.dict(os.environ, {"MODEL_ROUTER_OFFLINE": "1"}):
            code, out, _ = self.run_index(Fetch())
        self.assertEqual((code, self.client.sent), (2, []))
        self.assertFalse((self.ws / "brands" / "acme" / "asset-index.json").exists())
        error = json.loads(out)["error"]
        self.assertIn("gemini-2.0-flash is retired", error)
        self.assertIn("gemini-3.6-flash", error)

    def test_the_same_pin_on_a_vertex_run_is_sent_because_the_gemini_api_record_does_not_apply(self):
        self.backend = "vertex-ai"
        self.write_config({"model_pins": {JOB: "gemini-2.0-flash"}})
        fetch = Fetch()
        code, out, err = self.run_index(fetch)
        self.assertEqual((code, fetch.calls), (0, 0), out)
        self.assertEqual(set(self.client.sent), {"gemini-2.0-flash"})
        self.assertIn("not checked", err)
        self.assertEqual(self.index()["vision_model"]["model"], "gemini-2.0-flash")

    def test_a_vertex_run_uses_the_registry_alias_and_makes_no_list_call(self):
        from resolve_model import resolve
        self.backend = "vertex-ai"
        fetch = Fetch()
        self.run_index(fetch)
        block = self.index()["vision_model"]
        self.assertEqual((block["model"], block["basis"], fetch.calls), (resolve("latest-vision-google"), "offline", 0))
        self.assertEqual(set(self.client.sent), {block["model"]})

    def test_a_refresh_with_nothing_new_asks_for_no_model_and_makes_no_list_call(self):
        self.run_index(Fetch())
        before = self.index()["vision_model"]
        fetch, self.client.sent[:] = Fetch(), []
        code, _, _ = self.run_index(fetch, refresh=True)
        self.assertEqual((code, fetch.calls, self.client.sent), (0, 0, []))
        self.assertEqual(self.index()["vision_model"], before, "no model was chosen this run, so the last record stands")

    def test_a_refresh_keeps_each_old_asset_under_the_model_that_analysed_it(self):
        self.run_index(Fetch(), model=None)
        (self.photos / "d.png").write_bytes(b"\x89new")
        self.write_config({"model_pins": {JOB: "gemini-3.6-flash"}})
        self.run_index(Fetch(), refresh=True)
        models = {a["filename"]: a["analysis_model"] for a in self.index()["assets"]}
        self.assertEqual(models, {"a.jpg": "gemini-3.8-flash", "b.png": "gemini-3.8-flash",
                                  "c.webp": "gemini-3.8-flash", "d.png": "gemini-3.6-flash"})
        self.assertEqual(self.index()["vision_model"]["model"], "gemini-3.6-flash")

    def test_a_webp_image_is_sent_as_webp(self):
        sent = []
        real = fake_genai()
        real["google.genai.types"].Part = types.SimpleNamespace(
            from_bytes=lambda data, mime_type: sent.append(mime_type) or {"mime": mime_type})
        with mock.patch.dict(sys.modules, real):
            self.run_index(Fetch())
        self.assertEqual(sorted(sent), ["image/jpeg", "image/png", "image/webp"])

    def test_no_credentials_still_ends_with_exit_3_and_a_metadata_only_index_and_no_model_is_chosen(self):
        with mock.patch.object(self.ia, "open_client", lambda: (None, None, "no-credentials: nothing set")):
            fetch = Fetch()
            code, _, _ = self.run_index(fetch)
        self.assertEqual((code, fetch.calls), (3, 0))
        self.assertEqual(self.index()["vision_model"]["basis"], "unavailable")
        self.assertTrue(all(not a.get("analysis_model") for a in self.index()["assets"]))


# --- the CLI ---------------------------------------------------------------------------------------------------------

def genai_importable() -> bool:
    try:
        return importlib.util.find_spec("google.genai") is not None
    except (ImportError, ValueError):
        return False


@unittest.skipUnless(genai_importable(), "google-genai is not installed here; the in-process tests above cover the logic")
class TestShowModelCli(unittest.TestCase):
    """`--show-model` prints the decision for the quote step and does nothing else: no image is read or sent, no index is written."""

    def run_cli(self, *args, extra_env=None):
        with tempfile.TemporaryDirectory() as tmp:
            env = {k: v for k, v in os.environ.items() if not k.startswith(("GOOGLE_", "GEMINI_"))}
            env.update(CLAUDE_PLUGIN_DATA=tmp, HOME=tmp, USERPROFILE=tmp, GEMINI_API_KEY=KEY, MODEL_ROUTER_OFFLINE="1",
                       PYTHONUTF8="1")
            env.update(extra_env or {})
            proc = subprocess.run([sys.executable, str(SCRIPTS / "index_assets.py"), *args], capture_output=True, text=True,
                                  env=env, stdin=subprocess.DEVNULL, timeout=60)
            leftovers = sorted(p.relative_to(tmp).as_posix() for p in Path(tmp).rglob("*") if p.is_file())
        return proc, leftovers

    def test_it_prints_the_decision_and_writes_nothing(self):
        from resolve_model import resolve
        proc, leftovers = self.run_cli("--brand", "acme", "--show-model")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        shown = json.loads(proc.stdout)
        self.assertEqual((shown["model"], shown["basis"], shown["job"]), (resolve("latest-vision-google"), "offline", JOB))
        self.assertEqual(leftovers, [], "--show-model wrote a file")

    def test_it_needs_no_source(self):
        proc, _ = self.run_cli("--brand", "acme", "--show-model")
        self.assertNotIn("--source is required", proc.stderr)

    def test_an_unknown_option_exits_2(self):
        proc, _ = self.run_cli("--brand", "acme", "--no-such-option")
        self.assertEqual(proc.returncode, 2)


# --- the registry refresh's Google list call -------------------------------------------------------------------------

class TestRefreshModelsKeepsTheKeyOutOfTheUrl(unittest.TestCase):
    """refresh_models.py wrote `...v1beta/models?key=<key>`, where proxies and server logs keep the key, and read only the first
    page of the list (Google pages by 50 unless asked for more). PRIVACY.md now says the Gemini key goes only in the
    x-goog-api-key header, so this call has to agree with it."""

    def setUp(self):
        import refresh_models
        self.rm = refresh_models

    def run_list(self, pages):
        seen = []

        def fake(url, headers, timeout=15):
            seen.append((url, dict(headers)))
            return pages[len(seen) - 1], None

        with mock.patch.dict(os.environ, {CRED: KEY}), mock.patch.object(self.rm, "_http_get", fake):
            return self.rm.list_gemini(), seen

    def test_the_key_is_in_the_header_and_never_in_any_url(self):
        (ids, err), seen = self.run_list([{"models": [{"name": "models/gemini-3.8-flash"}]}])
        self.assertIsNone(err)
        self.assertEqual(ids, {"gemini-3.8-flash"})
        self.assertEqual(len(seen), 1)
        url, headers = seen[0]
        self.assertNotIn(KEY, url)
        self.assertNotIn("key=", url)
        self.assertEqual(headers, {"x-goog-api-key": KEY})

    def test_every_page_is_read_and_none_carries_the_key_in_its_url(self):
        pages = [{"models": [{"name": "models/a"}], "nextPageToken": "tok1"},
                 {"models": [{"name": "models/b"}], "nextPageToken": "tok2"},
                 {"models": [{"name": "models/c"}]}]
        (ids, err), seen = self.run_list(pages)
        self.assertEqual((ids, err), ({"a", "b", "c"}, None))
        self.assertEqual(len(seen), 3)
        self.assertIn("pageToken=tok1", seen[1][0])
        self.assertIn("pageToken=tok2", seen[2][0])
        for url, headers in seen:
            self.assertNotIn(KEY, url)
            self.assertEqual(headers, {"x-goog-api-key": KEY})

    def test_a_failed_page_is_reported_not_swallowed(self):
        def fake(url, headers, timeout=15):
            return None, "http-401: Unauthorized"

        with mock.patch.dict(os.environ, {CRED: KEY}), mock.patch.object(self.rm, "_http_get", fake):
            ids, err = self.rm.list_gemini()
        self.assertEqual((ids, err), (None, "http-401: Unauthorized"))

    # Anthropic lists 20 models by default (up to 1000 a page) and pages by has_more / last_id -> after_id. A list that stops at
    # the first page reports every current Claude id past the 20th as "registry says live, provider does not list it".
    A_KEY = "ant-test-0000-not-a-real-anthropic-key"

    def run_anthropic(self, pages):
        seen = []

        def fake(url, headers, timeout=15):
            seen.append((url, dict(headers)))
            return pages[len(seen) - 1], None

        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": self.A_KEY}), mock.patch.object(self.rm, "_http_get", fake):
            return self.rm.list_anthropic(), seen

    def test_anthropic_follows_has_more_and_last_id_and_asks_for_the_largest_page(self):
        pages = [{"data": [{"id": "claude-one"}, {"id": "claude-two"}], "has_more": True, "last_id": "claude-two"},
                 {"data": [{"id": "claude-three"}], "has_more": False, "last_id": "claude-three"}]
        (ids, err), seen = self.run_anthropic(pages)
        self.assertEqual((ids, err), ({"claude-one", "claude-two", "claude-three"}, None))
        self.assertEqual(len(seen), 2)
        first = urllib.parse.parse_qs(urllib.parse.urlsplit(seen[0][0]).query)
        second = urllib.parse.parse_qs(urllib.parse.urlsplit(seen[1][0]).query)
        self.assertEqual(first.get("limit"), ["1000"])
        self.assertEqual(second.get("after_id"), ["claude-two"])
        for url, headers in seen:
            self.assertNotIn(self.A_KEY, url)
            self.assertEqual(headers.get("x-api-key"), self.A_KEY)

    def test_a_single_anthropic_page_is_read_once(self):
        (ids, err), seen = self.run_anthropic([{"data": [{"id": "claude-only"}], "has_more": False}])
        self.assertEqual((ids, err, len(seen)), ({"claude-only"}, None, 1))

    def test_a_failed_second_anthropic_page_is_reported_never_returned_as_a_short_list(self):
        pages = [{"data": [{"id": "claude-one"}], "has_more": True, "last_id": "claude-one"}]

        def fake(url, headers, timeout=15):
            return (pages[0], None) if "after_id" not in url else (None, "network: connection reset")

        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": self.A_KEY}), mock.patch.object(self.rm, "_http_get", fake):
            self.assertEqual(self.rm.list_anthropic(), (None, "network: connection reset"))

    def test_a_list_that_never_ends_is_an_error_not_a_truncated_set(self):
        """A short list would report every model past the cut as gone. Both paged providers stop and say so."""
        def endless_anthropic(url, headers, timeout=15):
            return {"data": [{"id": "claude-x"}], "has_more": True, "last_id": "claude-x"}, None

        def endless_google(url, headers, timeout=15):
            return {"models": [{"name": "models/x"}], "nextPageToken": "again"}, None

        for fn, endless, env in ((self.rm.list_anthropic, endless_anthropic, {"ANTHROPIC_API_KEY": self.A_KEY}),
                                 (self.rm.list_gemini, endless_google, {CRED: KEY})):
            with self.subTest(fn=fn.__name__), mock.patch.dict(os.environ, env), \
                    mock.patch.object(self.rm, "_http_get", endless):
                ids, err = fn()
                self.assertIsNone(ids)
                self.assertIn("too-many-pages", err)


# --- the docs say what the code does ---------------------------------------------------------------------------------

class TestDocsTruth(unittest.TestCase):

    def setUp(self):
        import index_assets
        import model_router
        self.ia, self.router = index_assets, model_router
        self.privacy = (REPO / "PRIVACY.md").read_text(encoding="utf-8")

    def test_privacy_names_the_list_call_and_its_limits(self):
        for fact in (self.router.GOOGLE_MODELS_URL, "x-goog-api-key", f"{self.router.TTL_DAYS} days",
                     self.ia.ROUTER_CACHE_NAME, f"{self.router.OFFLINE_ENV}=1", "GEMINI_API_KEY", "Vertex AI",
                     "scripts/model_router.py"):
            self.assertIn(fact, self.privacy, f"PRIVACY.md does not mention {fact!r}")

    def test_privacy_says_the_key_never_goes_in_the_url_and_the_cache_never_holds_it(self):
        flat = " ".join(self.privacy.split())
        self.assertRegex(flat, r"never in the URL")
        self.assertRegex(flat, r"never the key")

    def test_the_index_assets_row_of_the_privacy_table_names_the_list_call(self):
        row = next(line for line in self.privacy.splitlines() if "scripts/index_assets.py" in line and line.startswith("|"))
        self.assertIn("models", row)
        self.assertIn(self.router.GOOGLE_MODELS_URL, row)

    def test_the_skill_quotes_the_model_the_run_will_use_not_the_registry_alias(self):
        text = (REPO / "skills" / "index-assets" / "SKILL.md").read_text(encoding="utf-8")
        cost = text[text.index("## Cost Awareness"):]
        self.assertIn("--show-model", cost)
        self.assertNotIn("resolve_model.py --alias latest-vision-google", cost,
                         "a quote for the registry alias is wrong when the router picks a newer model")

    def test_the_skill_explains_the_order_the_model_is_chosen_in(self):
        text = (REPO / "skills" / "index-assets" / "SKILL.md").read_text(encoding="utf-8")
        for fact in ("model_pins", "--model", "model list", "latest-vision-google"):
            self.assertIn(fact, text)

    def test_the_brand_config_schema_documents_model_pins(self):
        text = (REPO / "references" / "brand-config-schema.md").read_text(encoding="utf-8")
        self.assertIn("model_pins", text)
        self.assertIn(JOB, text)

    def test_the_offline_check_and_the_vertex_exception_are_documented_where_users_read_them(self):
        pages = {
            "docs/MODEL-CURATOR.md": ("deprecations.google", "record_applies=False", "20 pages", "stricter"),
            "skills/index-assets/SKILL.md": ("Vertex AI", "not checked", "deprecations page"),
            "docs/USER-GUIDE.md": ("Vertex AI", "not checked"),
            "references/brand-config-schema.md": ("Vertex AI", "not checked", "offline as well as online"),
            "references/asset-index-schema.md": ("not checked on Vertex AI",),
            "PRIVACY.md": ("20 pages", "local data only", "scripts/model_hints.json"),
        }
        for rel, facts in pages.items():
            text = " ".join((REPO / rel).read_text(encoding="utf-8").split())
            for fact in facts:
                self.assertIn(fact, text, f"{rel} does not say {fact!r}")

    def test_the_router_page_cap_the_privacy_text_names_is_the_routers(self):
        self.assertEqual(self.router.MAX_PAGES, 20)

    def test_the_asset_index_schema_documents_the_provenance_fields(self):
        text = (REPO / "references" / "asset-index-schema.md").read_text(encoding="utf-8")
        for field in ("vision_model", "analysis_model", "analyzed_at", "selected_by", "basis"):
            self.assertIn(field, text, f"asset-index-schema.md does not document {field}")

    def test_the_curator_doc_describes_the_router_copy_and_the_hint_book(self):
        text = (REPO / "docs" / "MODEL-CURATOR.md").read_text(encoding="utf-8")
        for fact in ("model_router.py", "model_hints.json", JOB):
            self.assertIn(fact, text)

    def test_no_script_names_a_vision_model_literal(self):
        src = (SCRIPTS / "index_assets.py").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"""["']gemini-\d[^"']*["']""", src), [])


class TestTheServiceIsNamed(VisionCase):
    """1.30.2. A retired model's replacement can depend on the service the request goes to (the registry's
    replacement_by_backend): veo-3.1-generate-preview's is gemini-omni-1.1-flash on the Gemini API and
    veo-3.1-generate-001 on Vertex AI. The run knows which it is on, so it says so to the router."""

    def test_the_router_is_told_the_service_each_run_goes_to(self):
        import model_router
        seen = {}
        real = model_router.route

        def spy(*args, **kwargs):
            seen.clear()
            seen.update(kwargs)
            return real(*args, **kwargs)

        for backend, service in (("ai-studio-fallback", "gemini-api"), ("vertex-ai", "vertex"), ("vertex-ai-env", "vertex")):
            with self.subTest(backend=backend):
                with mock.patch.object(model_router, "route", spy):
                    self.pick(Fetch(), backend=backend, cache=False)
                self.assertEqual(seen["backend"], service)

    def test_offline_a_retired_veo_pin_names_the_gemini_apis_replacement_not_vertexs(self):
        import model_router
        with self.assertRaises(model_router.RouterError) as ctx:
            self.pick(Fetch(), brand_config={"model_pins": {JOB: "veo-3.1-generate-preview"}}, env=OFFLINE)
        reason = ctx.exception.reason
        self.assertIn("gemini-omni-1.1-flash", reason)
        self.assertNotIn("veo-3.1-generate-001", reason)

    def test_on_vertex_the_same_pin_is_not_checked_against_the_gemini_apis_data(self):
        got = self.pick(Fetch(), backend="vertex-ai", brand_config={"model_pins": {JOB: "veo-3.1-generate-preview"}})
        self.assertEqual(got["model"], "veo-3.1-generate-preview")
        self.assertTrue(any("not checked" in w for w in got["warnings"]), got["warnings"])


if __name__ == "__main__":
    unittest.main()
