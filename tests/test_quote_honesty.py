"""1.29.8: a quote names only providers that can run, and nothing is ever spent on a provider the user was not quoted.

Found by a research pass on 2026-10-27. Google's Gemini API stopped serving the Veo 3.1 previews on 2026-10-22 and never listed
`veo-3.1-generate-001`; Veo 3.1 is a Vertex AI model. SocialForge counted a bare GEMINI_API_KEY as "Google available", so for a
key-only user routing and the quote named Veo for a clip that could only fail, and the chain then fell through to Kling or
HiggsField, each with its own price, without the user being quoted for it. Four things changed and each is pinned here, with a plant
that fails against the old behaviour:

1. availability is per BACKEND (Veo needs Vertex AI), and routing and the quote only name a provider that can run;
2. a fallback runs only if it was in the approved quote (`--quoted-providers`), else the run stops as NEEDS_REQUOTE, nothing spent;
3. a fallback that did run is reported to the user (`provider_notice`, `fallback_from`, `earlier_attempts`);
4. Veo is asked for 4, 6 or 8 seconds only.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(SCRIPTS))

import _isolation  # noqa: E402

_isolation.start()    # a direct run of this file is protected too; a no-op when the runner already started it

# Every credential the scripts read, blank: each test then sets exactly the ones it is about.
NO_KEYS = {"GEMINI_API_KEY": "", "GOOGLE_CLOUD_PROJECT": "", "GOOGLE_APPLICATION_CREDENTIALS": "", "WAVESPEED_API_KEY": "",
           "HF_API_KEY": "", "HF_API_SECRET": ""}


def _empty_store():
    """Point credential_manager at an empty temporary store so a stored profile can never leak into a test."""
    import credential_manager as cm
    tmp = Path(tempfile.mkdtemp())
    cm.CRED_DIR = tmp
    cm.CRED_FILE = tmp / "credentials.json"
    cm.GCP_KEY_FILE = tmp / "gcp-credentials.json"


def _env(**keys):
    _empty_store()
    return patch.dict(os.environ, {**NO_KEYS, **keys})


class TestVeoNeedsVertex(unittest.TestCase):
    def test_a_gemini_key_alone_is_not_a_video_provider(self):
        import generate_video as gv
        with _env(GEMINI_API_KEY="k"):
            avail = gv._provider_availability()
            routing = gv.route_video_provider(8, "short_reel")
        self.assertTrue(avail["google"], "a Gemini key still covers images")
        self.assertFalse(avail["veo"])
        self.assertIn("Vertex", avail["unavailable"]["veo"])
        self.assertEqual(routing["provider"], "none")
        self.assertIn("Vertex", routing["error"])

    def test_the_quote_for_a_key_plus_wavespeed_setup_names_kling_never_veo(self):
        import generate_video as gv
        with _env(GEMINI_API_KEY="k", WAVESPEED_API_KEY="w"):
            routing = gv.route_video_provider(5, "short_reel")
        self.assertEqual(routing["provider"], "kling")
        self.assertEqual(routing["quote_providers"], ["kling"])
        self.assertIn("veo", routing["unavailable"])
        self.assertNotIn("veo", routing["fallbacks_if_quoted"])

    def test_vertex_makes_veo_available_and_other_runnable_providers_are_offered_as_quotable_fallbacks(self):
        import generate_video as gv
        with _env(GOOGLE_CLOUD_PROJECT="p", WAVESPEED_API_KEY="w", HF_API_KEY="a", HF_API_SECRET="b"):
            short = gv.route_video_provider(8, "short_reel")
            long = gv.route_video_provider(12, "short_reel")
        self.assertEqual(short["provider"], "veo")
        self.assertEqual(short["quote_providers"], ["veo"])
        self.assertEqual(short["fallbacks_if_quoted"], ["kling", "higgsfield"])
        self.assertEqual(long["provider"], "kling")
        self.assertEqual(short["unavailable"], {})

    def test_plant_the_1_29_7_routing_named_veo_for_a_key_only_setup(self):
        """The old routing, reproduced: `google` was true for a Gemini key, and 8 seconds or less went to Veo."""
        def old_route(duration, avail):
            if duration <= 8 and avail["google"]:
                return "veo"
            return "none"
        old_avail = {"google": bool("" or "" or "a-gemini-key")}
        self.assertEqual(old_route(8, old_avail), "veo", "the plant no longer reproduces the old quote naming Veo")
        import generate_video as gv
        with _env(GEMINI_API_KEY="a-gemini-key"):
            self.assertNotEqual(gv.route_video_provider(8, "short_reel")["provider"], "veo")

    def test_the_veo_rung_on_a_key_only_setup_records_unavailable_backend_and_builds_no_client(self):
        import generate_video as gv
        fake_google = types.ModuleType("google")
        fake_genai = types.ModuleType("google.genai")

        def never(*args, **kwargs):
            raise AssertionError("an AI Studio client was built for Veo")

        fake_genai.Client = never
        fake_genai.types = types.ModuleType("google.genai.types")
        fake_google.genai = fake_genai
        attempts = []
        with _env(GEMINI_API_KEY="k"), patch.dict(sys.modules, {"google": fake_google, "google.genai": fake_genai,
                                                                "google.genai.types": fake_genai.types}), \
                patch("credential_manager.get_vertex_client", return_value=(None, "no Vertex AI profile and no GOOGLE_CLOUD_PROJECT")):
            result = gv.generate_video_veo("p", "o.mp4", attempts=attempts)
        self.assertIsNone(result)
        self.assertEqual([(a["provider"], a["reason"]) for a in attempts], [("veo", "unavailable-backend")])
        self.assertIn("Vertex AI", attempts[0]["detail"])


class TestFallbackOnlyWithinTheQuote(unittest.TestCase):
    """A fallback has its own price. The chain runs a provider only if the user was quoted for it."""

    @staticmethod
    def _chain(quoted=None, preferred=None, status=None, kling=None, veo=None, higgs=None):
        import generate_video as gv
        status = status or (lambda rung: (True, "", "no-credentials"))

        def fails(name):
            def rung(*args, attempts=None, **kwargs):
                if attempts is not None:
                    attempts.append({"provider": name, "stage": "request", "reason": "request-error", "detail": name + " failed"})
                return None
            return rung

        mocks = {"generate_video_kling": kling or fails("kling"), "generate_video_veo": veo or fails("veo"),
                 "generate_video_higgsfield": higgs or fails("higgsfield")}
        called = {}
        patches = []
        for fn, impl in mocks.items():
            wrapper = (lambda impl, fn: lambda *a, **k: (called.setdefault(fn, 0), called.__setitem__(fn, called[fn] + 1), impl(*a, **k))[2])(impl, fn)
            patches.append(patch.object(gv, fn, wrapper))
        patches.append(patch.object(gv, "_rung_status", status))
        for p in patches:
            p.start()
        try:
            result = gv.generate_video_chain("p", "o.mp4", "first.png", 5, preferred=preferred, quoted=quoted)
        finally:
            for p in patches:
                p.stop()
        return result, called

    @staticmethod
    def _ok(provider):
        return lambda *a, **k: {"status": "success", "provider": provider, "output": "o.mp4"}

    def test_by_default_only_the_first_provider_may_run_and_the_rest_are_withheld(self):
        result, called = self._chain()
        self.assertEqual(result["status"], "NEEDS_REQUOTE")
        self.assertEqual(result["quoted_providers"], ["kling"])
        self.assertEqual(result["withheld_providers"], ["veo", "higgsfield"])
        self.assertEqual(called, {"generate_video_kling": 1}, "a provider outside the quote was called")
        self.assertIn("Nothing was spent", result["next_steps"][0])
        self.assertTrue(result["action_required"])

    def test_a_quoted_fallback_runs_and_the_user_is_told_which_provider_made_the_clip(self):
        result, called = self._chain(quoted=["kling", "veo"], veo=self._ok("veo-vertex"))
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["fallback_from"], "kling")
        self.assertIn("kling", result["provider_notice"])
        self.assertIn("veo", result["provider_notice"])
        self.assertIn("approved quote", result["provider_notice"])
        self.assertEqual(result["earlier_attempts"][0]["provider"], "kling")
        self.assertNotIn("generate_video_higgsfield", called)

    def test_a_provider_that_cannot_run_is_skipped_with_its_reason_and_is_not_a_reason_to_requote(self):
        def status(rung):
            return (rung == "kling", "" if rung == "kling" else "no key for " + rung, "no-credentials")
        result, called = self._chain(status=status)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(called, {"generate_video_kling": 1})
        skipped = [a for a in result["attempts"] if a["provider"] in ("veo", "higgsfield")]
        self.assertEqual([a["reason"] for a in skipped], ["no-credentials", "no-credentials"])
        self.assertIn("no key for veo", skipped[0]["detail"])

    def test_an_explicit_provider_choice_sets_what_the_default_quote_covers(self):
        result, called = self._chain(preferred="veo")
        self.assertEqual(result["quoted_providers"], ["veo"])
        self.assertEqual(result["withheld_providers"], ["kling", "higgsfield"])
        self.assertEqual(called, {"generate_video_veo": 1})

    def test_the_cli_refuses_a_provider_name_it_does_not_know(self):
        with tempfile.TemporaryDirectory() as home:
            env = {**os.environ, **NO_KEYS, "HOME": home, "USERPROFILE": home}
            for script, extra, quoted in (
                    ("generate_video.py", ["--brand", "b", "--month", "2026-10", "--post-id", "P1", "--output-dir", home], "kling,bogus"),
                    ("generate_image.py", ["--prompt", "p", "--output", os.path.join(home, "o.png")], "gemini,bogus")):
                with self.subTest(script=script):
                    r = subprocess.run([sys.executable, str(SCRIPTS / script), *extra, "--quoted-providers", quoted],
                                       capture_output=True, text=True, env=env, timeout=60, cwd=home)
                    self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                    self.assertIn("unknown provider 'bogus'", r.stderr)

    def test_parse_quoted(self):
        from provider_failures import parse_quoted
        self.assertIsNone(parse_quoted(None, ("a", "b")))
        self.assertEqual(parse_quoted(" A, b ,a", ("a", "b")), ["a", "b"])
        with self.assertRaises(ValueError):
            parse_quoted("", ("a", "b"))
        with self.assertRaises(ValueError):
            parse_quoted("c", ("a", "b"))

    def test_plant_the_main_flow_passes_the_quote_to_the_chain(self):
        """Dropping `quoted=` from the call would restore unquoted fallbacks; the check below is what would catch it."""
        def passes_quote(src):
            return bool(re.search(r"generate_video_chain\(.*?quoted=quoted_providers", src, re.S))
        real = (SCRIPTS / "generate_video.py").read_text(encoding="utf-8")
        self.assertTrue(passes_quote(real))
        self.assertFalse(passes_quote(real.replace("last_image_path=args.last_image, quoted=quoted_providers)", "last_image_path=args.last_image)")))


class TestImageChainQuote(unittest.TestCase):
    def _run(self, quoted, statuses):
        import generate_image as gi
        called = []

        def wavespeed(*args, attempts=None, **kwargs):
            called.append("wavespeed")
            return {"status": "success", "provider": "wavespeed-image", "output": "o.png"}

        def higgs(*args, attempts=None, **kwargs):
            called.append("higgsfield")
            return {"status": "success", "provider": "higgsfield-image", "output": "o.png"}

        with patch.object(gi, "create_client", return_value=(None, None, "no credentials")), \
                patch.object(gi, "_image_rung_status", lambda rung: statuses[rung]), \
                patch.object(gi, "generate_image_wavespeed", wavespeed), patch.object(gi, "generate_image_higgsfield", higgs):
            return gi.generate_image("p", "o.png", model="m", quoted=quoted), called

    ALL_OK = {"gemini": (True, ""), "wavespeed": (True, ""), "higgsfield": (True, "")}

    def test_an_unquoted_fallback_image_provider_is_withheld(self):
        result, called = self._run(["gemini"], self.ALL_OK)
        self.assertEqual(result["status"], "NEEDS_REQUOTE")
        self.assertEqual(result["withheld_providers"], ["wavespeed", "higgsfield"])
        self.assertEqual(called, [])

    def test_a_quoted_fallback_image_provider_runs_and_says_so(self):
        result, called = self._run(["gemini", "wavespeed"], self.ALL_OK)
        self.assertEqual(result["status"], "success")
        self.assertEqual(called, ["wavespeed"])
        self.assertIn("wavespeed", result["provider_notice"])

    def test_with_only_a_fallback_key_the_default_quote_is_that_provider_and_it_runs(self):
        statuses = {"gemini": (False, "no credentials"), "wavespeed": (True, ""), "higgsfield": (False, "no key")}
        import generate_image as gi
        with patch.object(gi, "_image_rung_status", lambda rung: statuses[rung]):
            self.assertEqual(gi.first_image_rung(), "wavespeed")
        result, called = self._run(None, statuses)
        self.assertEqual(result["status"], "success")
        self.assertEqual(called, ["wavespeed"])


class TestVeoDurations(unittest.TestCase):
    def test_only_4_6_and_8_second_clips_are_requested(self):
        import generate_video as gv
        got = {d: gv.veo_duration(d) for d in (None, 1, 3, 4, 5, 6, 7, 8, 9, 15, 90)}
        self.assertEqual(got, {None: 4, 1: 4, 3: 4, 4: 4, 5: 6, 6: 6, 7: 8, 8: 8, 9: 8, 15: 8, 90: 8})

    def test_the_rung_sends_an_allowed_length_and_reports_the_rounding(self):
        import generate_video as gv
        seen = {}

        class Op:
            done = True
            result = types.SimpleNamespace(generated_videos=[types.SimpleNamespace(video="v")])

        class Client:
            def __init__(self):
                self.models = types.SimpleNamespace(generate_videos=self.generate_videos)
                self.files = types.SimpleNamespace(download=lambda file: b"mp4")
                self.operations = types.SimpleNamespace(get=lambda op: op)

            def generate_videos(self, **kwargs):
                seen.update(kwargs)
                return Op()

        fake_types = types.ModuleType("google.genai.types")
        fake_types.GenerateVideosConfig = lambda **kw: types.SimpleNamespace(**kw)
        fake_types.Image = lambda **kw: types.SimpleNamespace(**kw)
        fake_genai = types.ModuleType("google.genai")
        fake_genai.types = fake_types
        fake_google = types.ModuleType("google")
        fake_google.genai = fake_genai
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {"google": fake_google, "google.genai": fake_genai,
                                                                           "google.genai.types": fake_types}), \
                patch("credential_manager.get_vertex_client", return_value=(Client(), "vertex-env")):
            result = gv.generate_video_veo("p", str(Path(tmp) / "o.mp4"), duration=5, model="veo-test", attempts=[])
        self.assertEqual(seen["config"].duration_seconds, 6)
        self.assertEqual((result["duration"], result["requested_duration"]), (6, 5))
        self.assertIn("rounded to 6s", result["duration_note"])


class TestSkillsAndAgentsCarryTheRule(unittest.TestCase):
    RUNS_PAID_CHAIN = re.compile(r"generate_video\.py --generate-video")

    @staticmethod
    def files():
        out = {}
        for pattern in ("skills/*/SKILL.md", "commands/*.md", "agents/*.md"):
            for p in sorted(ROOT.glob(pattern)):
                out[p.relative_to(ROOT).as_posix()] = p.read_text(encoding="utf-8")
        return out

    @classmethod
    def missing_flag(cls, text):
        return bool(cls.RUNS_PAID_CHAIN.search(text)) and "--quoted-providers" not in text

    def test_every_file_that_runs_the_paid_video_chain_names_the_quoted_providers_flag(self):
        files = self.files()
        self.assertGreater(len(files), 30)
        runners = [rel for rel, text in files.items() if self.RUNS_PAID_CHAIN.search(text)]
        self.assertIn("skills/generate-video/SKILL.md", runners)
        self.assertEqual([rel for rel in runners if self.missing_flag(files[rel])], [])

    def test_plant_a_skill_that_runs_the_chain_without_the_flag_is_flagged(self):
        self.assertTrue(self.missing_flag("1. Run `generate_video.py --generate-video --image a.png`"))
        self.assertFalse(self.missing_flag("1. Run `generate_video.py --generate-video --image a.png --quoted-providers kling`"))

    def test_the_three_files_that_run_the_scripts_tell_the_agent_what_to_do_with_a_fallback_and_a_requote(self):
        files = self.files()
        for rel in ("skills/generate-video/SKILL.md", "skills/compose-creative/SKILL.md", "agents/image-compositor.md"):
            with self.subTest(file=rel):
                text = files[rel]
                self.assertIn("--quoted-providers", text)
                self.assertIn("provider_notice", text)
                self.assertTrue("NEEDS_REQUOTE" in text or "needs_quote" in text)
        self.assertIn("routing", files["skills/generate-video/SKILL.md"])
        self.assertIn("Vertex AI", files["skills/generate-video/SKILL.md"])

    def test_agent_descriptions_fit_the_listing_budget(self):
        for p in sorted((ROOT / "agents").glob("*.md")):
            m = re.search(r'(?m)^description:\s*(.*)$', p.read_text(encoding="utf-8"))
            self.assertIsNotNone(m, p.name)
            n = len(m.group(1).strip().strip('"'))
            with self.subTest(agent=p.name):
                self.assertTrue(60 <= n <= 150, "%s description is %d characters; the rule is 60-150" % (p.name, n))

    def test_plant_agent_descriptions_outside_60_to_150_are_caught(self):
        for length in (40, 160):
            self.assertFalse(60 <= len("x" * length) <= 150)


class TestDocsTellTheNewFacts(unittest.TestCase):
    def read(self, rel):
        return (ROOT / rel).read_text(encoding="utf-8")

    def test_the_veo_reference_describes_the_vertex_only_ga_model(self):
        text = self.read("references/models/veo-3.1.md")
        self.assertIn("`veo-3.1-generate-001`", text)
        self.assertNotIn("`veo-3.1-generate-preview` (see", text)
        for needle in ("Vertex AI", "4, 6 or 8", "2026-10-22", "2026-11-17", "GenerateVideosSource"):
            with self.subTest(needle=needle):
                self.assertIn(needle, text)
        self.assertNotIn("clamped, not rejected", text)

    def test_the_article_50_reference_has_the_50_2_grace_period_and_who_owes_what(self):
        text = self.read("references/eu-ai-act-article50.md")
        for needle in ("2 December 2026", "50(2)", "50(4)", "provider"):
            with self.subTest(needle=needle):
                self.assertIn(needle, text)

    def test_no_c2pa_version_claim_is_older_than_the_current_spec(self):
        for rel in ("references/eu-ai-act-article50.md", "skills/c2pa-sign/SKILL.md", "scripts/c2pa_sign.py"):
            text = self.read(rel)
            with self.subTest(file=rel):
                self.assertNotRegex(text, r"(?i)c2pa (spec(ification)? )?v2\.0")
                self.assertNotIn("specifications/2.0/", text)
        self.assertIn("2.5", self.read("skills/c2pa-sign/SKILL.md"))

    def test_the_one_command_install_is_in_the_readme_and_the_user_guide(self):
        line = "claude plugin install socialforge --marketplace indranilbanerjee/neels-plugins"
        for rel in ("README.md", "docs/USER-GUIDE.md"):
            with self.subTest(file=rel):
                text = self.read(rel)
                self.assertIn(line, text)
                self.assertIn("/plugin marketplace add indranilbanerjee/neels-plugins", text)   # the older route stays


class TestPythonFloorWarning(unittest.TestCase):
    def test_python_3_10_is_warned_and_3_11_is_not(self):
        import _common
        warning = _common.python_floor_warning((3, 10, 12))
        self.assertIn("3.11", warning)
        self.assertIn("end of life", warning)
        self.assertIsNone(_common.python_floor_warning((3, 11, 0)))
        self.assertIsNone(_common.python_floor_warning((3, 13, 1)))

    def test_install_deps_prints_the_warning_to_stderr_and_credential_status_carries_it(self):
        import io
        import json
        import install_deps
        import credential_manager
        with patch("_common.python_floor_warning", return_value="WARN-TEXT"), patch("sys.argv", ["install_deps.py", "--check"]), \
                patch("sys.stderr", io.StringIO()) as err, patch("sys.stdout", io.StringIO()), \
                patch.object(install_deps, "check_and_install", return_value={}):
            install_deps.main()
        self.assertIn("WARN-TEXT", err.getvalue())
        _empty_store()
        out = io.StringIO()
        with patch("_common.python_floor_warning", return_value="WARN-TEXT"), patch("sys.argv", ["credential_manager.py", "status"]), \
                patch("sys.stdout", out):
            credential_manager.main()
        self.assertEqual(json.loads(out.getvalue())["python_warning"], "WARN-TEXT")


class TestNoPromisedPythonFloor(unittest.TestCase):
    """Claude's Cowork environment ran Python 3.10.12 when last checked, so promising "3.11 from the next minor release" would break every
    Cowork user. The wording is conditional everywhere: the plugin moves to 3.11 once Cowork does, and no release is named."""
    PROMISE = re.compile(r"(?is)(?:will\s+(?:be\s+)?requires?d?|requires?d?)[^.]{0,60}\b3\.11\b[^.]{0,60}\bnext\s+(?:minor|release)"
                         r"|\b3\.11\b[^.]{0,60}\bfrom\s+the\s+next\s+(?:minor|release)")

    def test_no_shipped_text_promises_python_3_11_from_a_release(self):
        skip_dirs = {".git", "node_modules", ".pytest_cache", "tests", "research", "heroes", ".superpowers"}
        scanned, bad = 0, []
        for path in ROOT.rglob("*"):
            if not path.is_file() or skip_dirs & set(path.relative_to(ROOT).parts):
                continue
            if path.suffix.lower() not in {".md", ".py", ".json", ".yml", ".yaml", ".txt"}:
                continue
            try:
                text = path.read_text(encoding="utf-8-sig")
            except (UnicodeDecodeError, OSError):
                continue
            scanned += 1
            if self.PROMISE.search(text):
                bad.append(path.relative_to(ROOT).as_posix())
        self.assertGreater(scanned, 100, "the scan saw too few files; the guard is vacuous")
        self.assertEqual(bad, [])

    def test_plant_the_old_wordings_are_caught_and_the_conditional_one_is_not(self):
        for old in ("SocialForge will require Python 3.11 from the next minor release.",
                    "SocialForge will require Python 3.11 or newer from the next minor release: install a newer Python.",
                    "Scripts require Python 3.10+ today (3.11 will be required from the next minor release, and setup warns on 3.10)",
                    "(3.11 from the next minor release; setup warns on 3.10)",
                    "will require\n  Python 3.11 from the next release"):
            with self.subTest(old=old):
                self.assertTrue(self.PROMISE.search(old), old)
        new = ("Python 3.10 reached end of life on 2026-10-01. SocialForge still runs on it, and will move to 3.11 once Claude's Cowork "
               "environment does (it ran 3.10.12 when last checked). Use 3.11 or newer where you can.")
        self.assertFalse(self.PROMISE.search(new))

    def test_the_warning_is_conditional_and_names_cowork(self):
        import _common
        warning = _common.python_floor_warning((3, 10, 12))
        self.assertIn("once Claude's Cowork environment does", warning)
        self.assertIn("3.10.12", warning)
        self.assertNotIn("next minor", warning)


if __name__ == "__main__":
    unittest.main()
