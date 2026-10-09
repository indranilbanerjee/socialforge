"""Findings from the Hermes Agent catalog review (2026-10-04), each with a planted failure.

A Hermes maintainer reviewed SocialForge 1.27.2 for catalog listing and asked for:

  S1  no package installed behind the user's back (setup ran an unpinned install of nine
      packages plus a browser; c2pa signing ran `pip install c2pa-python>=0.32` mid-run)
  S2  `${CLAUDE_PLUGIN_ROOT}` is not defined on Hermes, so a skill command became
      `python /scripts/...` - every skill that uses it now says where the scripts are
  S3  --brand / --month must not choose a path
  S4  PRIVACY.md must list what really runs
  S5  the throwaway C2PA dev signing key must not outlive the signing
  F1  API keys never travel through the chat or the command line
  F2  paid generation is quoted, then waits for an explicit "go" (PRIVACY.md says it always does)
  F3  provider-returned URLs are https only; slide text is HTML-escaped; a missing c2pa-python
      raises instead of exiting after a paid generation; no skill claims an install that does
      not happen

Every check is exercised on a good input AND on the failing input it exists to catch.
Stdlib only (the signing-key test also needs `cryptography` and skips without it).
"""
from __future__ import annotations

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
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
SKILLS = ROOT / "skills"
COMMANDS = ROOT / "commands"
sys.path.insert(0, str(SCRIPTS))


def load(filename: str, modname: str):
    spec = importlib.util.spec_from_file_location(modname, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


install_deps = load("install_deps.py", "sf_install_deps")


# ── S1: nothing installs itself ─────────────────────────────────────────

class TestNoInstallBehindTheUsersBack(unittest.TestCase):
    def test_every_package_has_an_exact_pin_and_an_import_name(self):
        for group, pkgs in install_deps.ALL_GROUPS.items():
            for pkg in pkgs:
                with self.subTest(group=group, package=pkg):
                    self.assertRegex(install_deps.PINNED[pkg], r"^\d+(\.\d+)+$")
                    self.assertIn(pkg, install_deps.IMPORT_NAMES)
                    self.assertTrue(install_deps.pin(pkg).startswith(pkg + "=="))
        with self.assertRaises(ValueError):
            install_deps.pin("not-a-pinned-package")

    def test_the_default_groups_leave_out_the_optional_packages(self):
        defaults = {p for g in install_deps.DEFAULT_GROUPS for p in install_deps.ALL_GROUPS[g]}
        for optional in ("rembg", "higgsfield-client", "c2pa-python", "cryptography"):
            self.assertNotIn(optional, defaults)

    def test_ensure_package_prints_the_pinned_command_and_installs_nothing(self):
        err = io.StringIO()
        with mock.patch.object(install_deps, "check_package", return_value=False), \
                mock.patch.dict(os.environ, {}, clear=False), \
                mock.patch("subprocess.run") as run, mock.patch("sys.stderr", err):
            os.environ.pop(install_deps.OPT_IN_ENV, None)
            self.assertFalse(install_deps.ensure_package("google-genai"))
        run.assert_not_called()
        self.assertIn("google-genai==" + install_deps.PINNED["google-genai"], err.getvalue())
        self.assertIn("-m pip install", err.getvalue())

    def test_only_the_explicit_opt_in_installs_and_it_uses_the_pin(self):
        ok = types.SimpleNamespace(returncode=0)
        checks = iter([False, True])        # missing, then importable after the install
        with mock.patch.object(install_deps, "check_package", side_effect=lambda p: next(checks)), \
                mock.patch.dict(os.environ, {install_deps.OPT_IN_ENV: "1"}), \
                mock.patch("subprocess.run", return_value=ok) as run:
            self.assertTrue(install_deps.ensure_package("wavespeed"))
        cmd = run.call_args[0][0]
        self.assertEqual(cmd[1:4], ["-m", "pip", "install"])
        self.assertEqual(cmd[4], "wavespeed==" + install_deps.PINNED["wavespeed"])

    def test_any_other_value_is_not_consent(self):
        for v in ("0", "yes", "true", ""):
            with self.subTest(value=v), mock.patch.object(install_deps, "check_package", return_value=False), \
                    mock.patch.dict(os.environ, {install_deps.OPT_IN_ENV: v}), \
                    mock.patch("subprocess.run") as run, mock.patch("sys.stderr", io.StringIO()):
                self.assertFalse(install_deps.ensure_package("Pillow"))
                run.assert_not_called()

    def test_the_command_line_reports_by_default_and_installs_only_with_install(self):
        def run_main(argv):
            out = io.StringIO()
            with mock.patch.object(install_deps, "check_package", return_value=False), \
                    mock.patch("subprocess.run", return_value=types.SimpleNamespace(returncode=0)) as run, \
                    mock.patch("sys.argv", ["install_deps.py"] + argv), mock.patch("sys.stdout", out):
                try:
                    install_deps.main()
                    code = 0
                except SystemExit as exc:
                    code = exc.code
            return code, run, out.getvalue()

        code, run, text = run_main([])
        self.assertEqual(code, 1)
        run.assert_not_called()
        self.assertIn("Nothing was installed", text)
        self.assertIn("-m playwright install chromium", text)          # the browser command is printed, not run
        code, run, text = run_main(["--check"])
        run.assert_not_called()
        code, run, _ = run_main(["--install", "--groups", "core"])
        self.assertTrue(run.called)
        self.assertEqual(run.call_args_list[0][0][0][4], "Pillow==" + install_deps.PINNED["Pillow"])

    def test_no_script_installs_on_its_own(self):
        offenders = []
        for p in sorted(SCRIPTS.glob("*.py")):
            if p.name == "install_deps.py":
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            if re.search(r'["\']pip["\']\s*,\s*["\']install["\']', text) or "ensurepip" in text:
                offenders.append(p.name)
        self.assertEqual(offenders, [])

    def test_plant_the_scan_catches_a_raw_pip_call(self):
        sample = 'subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "c2pa-python>=0.32"])'
        self.assertTrue(re.search(r'["\']pip["\']\s*,\s*["\']install["\']', sample))


class TestC2paNeverInstallsMidRun(unittest.TestCase):
    def setUp(self):
        self.c2 = load("c2pa_sign.py", "sf_c2pa_sign")

    def test_missing_package_raises_with_the_pinned_command_and_runs_nothing(self):
        with mock.patch.dict(sys.modules, {"c2pa": None}), mock.patch("subprocess.run") as run, \
                mock.patch("subprocess.check_call") as call, mock.patch("sys.stderr", io.StringIO()), \
                mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(install_deps.OPT_IN_ENV, None)
            with self.assertRaises(self.c2.C2paNotInstalled) as ctx:
                self.c2.ensure_c2pa()
        run.assert_not_called()
        call.assert_not_called()
        self.assertIn("c2pa-python==" + install_deps.PINNED["c2pa-python"], str(ctx.exception))

    def test_the_command_line_exits_2_with_that_message_instead_of_a_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "in.png"
            src.write_bytes(b"\x89PNG\r\n\x1a\n")
            argv = ["c2pa_sign.py", "--input", str(src), "--output", str(Path(d) / "out.png"),
                    "--brand", "t", "--generator", "g"]
            err = io.StringIO()
            with mock.patch.dict(sys.modules, {"c2pa": None}), mock.patch("sys.argv", argv), \
                    mock.patch("sys.stderr", err), mock.patch("subprocess.run") as run:
                with self.assertRaises(SystemExit) as ctx:
                    self.c2.main()
        self.assertEqual(ctx.exception.code, 2)
        run.assert_not_called()
        self.assertIn("-m pip install", err.getvalue())

    def test_plant_a_failed_install_no_longer_kills_the_caller(self):
        # the old code called sys.exit(2) here, which `except Exception` in the image generator cannot catch
        self.assertTrue(issubclass(self.c2.C2paNotInstalled, Exception))
        self.assertNotIn("sys.exit(2)", Path(SCRIPTS / "c2pa_sign.py").read_text(encoding="utf-8").split("def ensure_c2pa")[1].split("def _plugin_version")[0])


class TestManifestIsValidForC2pa038(unittest.TestCase):
    """c2pa-python 0.38 (the pin) refuses a manifest whose c2pa.created action has no digitalSourceType, and
    refuses a second created/opened action. Verified end to end with the real library; these keep the shape."""

    def setUp(self):
        self.c2 = load("c2pa_sign.py", "sf_c2pa_sign_manifest")

    def _actions(self, claim, prompt=None, platform=None, reviewer=None):
        m = self.c2.build_manifest("Acme", "gen", claim, "2026-10-10T00:00:00+00:00", prompt, platform, ".png",
                                   reviewed_by=reviewer)
        return [a for assertion in m["assertions"] if assertion["label"].startswith("c2pa.actions")
                for a in assertion["data"]["actions"]]

    def test_created_carries_the_iptc_source_type_for_every_claim(self):
        for claim, iptc in self.c2.IPTC_SOURCE_TYPE.items():
            with self.subTest(claim=claim):
                created = [a for a in self._actions(claim) if a["action"] == "c2pa.created"]
                self.assertEqual(len(created), 1)
                self.assertEqual(created[0]["digitalSourceType"], iptc)
        self.assertEqual(set(self.c2.IPTC_SOURCE_TYPE), set(self.c2.AI_CLAIM_TO_C2PA_TYPE))

    def test_a_prompt_does_not_add_a_second_created_or_opened_action(self):
        acts = self._actions("ai-generated-content", prompt="a red square", platform="linkedin", reviewer="A. Reviewer")
        self.assertEqual([a["action"] for a in acts].count("c2pa.created"), 1)
        self.assertNotIn("c2pa.opened", [a["action"] for a in acts])
        self.assertIn("a red square", acts[0]["description"])

    def test_the_pin_is_the_version_it_was_verified_against(self):
        self.assertEqual(install_deps.PINNED["c2pa-python"], "0.38.0")


# ── S5: the throwaway key ──────────────────────────────────────────────

class TestDevSigningKeyIsDeleted(unittest.TestCase):
    def test_throwaway_key_folder_is_gone_after_signing(self):
        try:
            import cryptography  # noqa: F401
        except ImportError:
            self.skipTest("cryptography not installed")
        c2 = load("c2pa_sign.py", "sf_c2pa_sign_key")

        class _Anything:
            def __getattr__(self, name):
                return name

        class _Signer:
            @staticmethod
            def from_info(info):
                return object()

        class _Builder:
            def __init__(self, manifest):
                pass

            def set_intent(self, *a):
                pass

            def sign_file(self, src, dst, signer=None):
                Path(dst).write_bytes(Path(src).read_bytes())

        fake = types.ModuleType("c2pa")
        fake.C2paSignerInfo = lambda **kw: kw
        fake.Signer = _Signer
        fake.Builder = _Builder
        fake.C2paBuilderIntent = _Anything()
        fake.C2paDigitalSourceType = _Anything()
        created = []
        real_mkdtemp = tempfile.mkdtemp

        def spy(*a, **k):
            d = real_mkdtemp(*a, **k)
            created.append(d)
            return d

        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "in.png"
            src.write_bytes(b"\x89PNG\r\n\x1a\n")
            with mock.patch.dict(sys.modules, {"c2pa": fake}), mock.patch("tempfile.mkdtemp", spy):
                result = c2.sign_asset(src, Path(d) / "out.png", "t", "g", "ai-generated-content")
        self.assertEqual(result.get("status"), "success", result)
        dev = [x for x in created if os.path.basename(x).startswith("sf-c2pa-")]
        self.assertEqual(len(dev), 1, "the dev key folder was never created, so this test proves nothing")
        self.assertFalse(os.path.exists(dev[0]), "dev signing key folder survived the signing")


# ── F3: downloads, escaping ────────────────────────────────────────────

class TestProviderUrlsAreHttpsOnly(unittest.TestCase):
    def setUp(self):
        self.pf = load("provider_failures.py", "sf_provider_failures")

    def test_https_downloads_and_nothing_else(self):
        with mock.patch("urllib.request.urlretrieve") as get:
            self.pf.download_https("https://cdn.example.com/a.png", "/tmp/a.png")
        get.assert_called_once_with("https://cdn.example.com/a.png", "/tmp/a.png")
        for url in ("file:///etc/passwd", "ftp://example.com/a.png", "http://example.com/a.png", "", "//example.com/a.png",
                    "data:text/plain;base64,AAAA"):
            with self.subTest(url=url), mock.patch("urllib.request.urlretrieve") as get:
                with self.assertRaises(ValueError):
                    self.pf.download_https(url, "/tmp/a.png")
                get.assert_not_called()

    def test_the_generators_use_it_and_never_call_urlretrieve_directly(self):
        for name in ("generate_image.py", "generate_video.py"):
            text = (SCRIPTS / name).read_text(encoding="utf-8")
            with self.subTest(script=name):
                self.assertNotIn("urllib.request.urlretrieve(", text)
                self.assertIn("download_https(", text)


class TestSlideTextIsEscaped(unittest.TestCase):
    def test_markup_in_a_slide_value_cannot_reach_the_page(self):
        rc = load("render_carousel.py", "sf_render_carousel")
        page = rc.inject_slide_values("<h1>{{slide_title}}</h1><p>{{slide_body}}</p>",
                                      {"title": "<script>alert(1)</script>", "body": 'a "quote" & <b>bold</b>'})
        self.assertNotIn("<script>", page)
        self.assertNotIn("<b>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertEqual(rc.inject_slide_values("{{slide_n}}", {"n": 7}), "7")


# ── S3: --brand / --month ──────────────────────────────────────────────

class TestBrandAndMonthCannotChooseAPath(unittest.TestCase):
    BAD = ["../x", "..", ".", "a/b", "/abs", "C:\\x", "..\\..\\x", "a\\b", "", "x:y", "nul\x00byte"]

    def setUp(self):
        self.sm = load("status_manager.py", "sf_status_manager")

    def test_component_check(self):
        for good in ("acme", "Acme Coffee", "2026-11"):
            self.assertTrue(self.sm.is_single_component(good), good)
        for bad in self.BAD + [None]:
            with self.subTest(value=bad):
                self.assertFalse(self.sm.is_single_component(bad))

    def test_library_functions_refuse_a_path_and_write_nothing(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(self.sm, "WORKSPACE", Path(d) / "ws"):
            for bad in ("../escape", "..\\escape", "/abs/path"):
                with self.subTest(value=bad):
                    with self.assertRaises(ValueError):
                        self.sm.init_month(bad, "2026-11")
                    with self.assertRaises(ValueError):
                        self.sm.init_month("acme", bad)
                    with self.assertRaises(ValueError):
                        self.sm.get_summary(bad, "2026-11")
            self.assertEqual([p for p in Path(d).rglob("*") if p.is_file()], [])

    def test_command_line_rejects_a_path_with_an_error_and_exit_1(self):
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ, CLAUDE_PLUGIN_DATA=d)
            for flag, value in (("--brand", "../x"), ("--month", "..\\..\\x")):
                args = ["--action", "get-summary", "--brand", "acme", "--month", "2026-11"]
                args[args.index(flag) + 1] = value
                p = subprocess.run([sys.executable, str(SCRIPTS / "status_manager.py")] + args,
                                   capture_output=True, text=True, env=env, timeout=60)
                with self.subTest(flag=flag):
                    self.assertEqual(p.returncode, 1)
                    self.assertIn("single folder name", json.loads(p.stdout)["error"])
            ok = subprocess.run([sys.executable, str(SCRIPTS / "status_manager.py"), "--action", "init-month",
                                 "--brand", "acme", "--month", "2026-11"],
                                capture_output=True, text=True, env=env, timeout=60)
            self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)


# ── S2: script location ────────────────────────────────────────────────

class TestScriptRootFallback(unittest.TestCase):
    SENTENCE = ("If your host does not set `${CLAUDE_PLUGIN_ROOT}`, the scripts are in this plugin's "
                "`scripts/` folder, next to `skills/`.")

    @staticmethod
    def missing(text: str, sentence: str) -> bool:
        return "CLAUDE_PLUGIN_ROOT" in text.replace(sentence, "") and sentence not in text

    def test_every_skill_and_command_that_uses_the_variable_says_where_the_scripts_are(self):
        files = sorted(SKILLS.glob("*/SKILL.md")) + sorted(COMMANDS.glob("*.md"))
        bad = [str(p.relative_to(ROOT)) for p in files
               if self.missing(p.read_text(encoding="utf-8", errors="replace"), self.SENTENCE)]
        self.assertEqual(bad, [])

    def test_plant_a_skill_without_the_sentence_is_flagged(self):
        self.assertTrue(self.missing("run `python ${CLAUDE_PLUGIN_ROOT}/scripts/x.py`", self.SENTENCE))
        self.assertFalse(self.missing("run `python ${CLAUDE_PLUGIN_ROOT}/scripts/x.py`\n" + self.SENTENCE, self.SENTENCE))
        self.assertFalse(self.missing("no variable here", self.SENTENCE))


# ── F1: keys never in the chat or on the command line ──────────────────

class TestSetupNeverTakesKeysThroughTheChat(unittest.TestCase):
    TEXT = (SKILLS / "setup" / "SKILL.md").read_text(encoding="utf-8")

    @staticmethod
    def problems(text: str) -> list[str]:
        out = []
        if re.search(r"setup-(wavespeed|higgsfield)[^\n]*--api-(key|secret)", text):
            out.append("a setup command puts a key or secret on the command line")
        if re.search(r"(?i)paste (the|it|them|your)[^\n.]*(key|secret)\b[^\n]*here|paste the key here", text):
            out.append("asks the user to paste a key into the chat")
        for var in ("WAVESPEED_API_KEY", "HF_API_KEY", "HF_API_SECRET"):
            if var not in text:
                out.append(f"never names {var}")
        return out

    def test_the_setup_skill_is_clean(self):
        self.assertEqual(self.problems(self.TEXT), [])

    def test_plant_the_old_instructions_are_flagged(self):
        old = ('Do you have a WaveSpeed API key?\n  Paste the key here\n'
               'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/credential_manager.py" setup-wavespeed --api-key "<user-provided-key>"\n')
        found = self.problems(old)
        self.assertTrue(any("command line" in p for p in found))
        self.assertTrue(any("chat" in p for p in found))

    def test_the_script_really_reads_the_environment_variables(self):
        text = (SCRIPTS / "credential_manager.py").read_text(encoding="utf-8")
        for var in ("WAVESPEED_API_KEY", "HF_API_KEY", "HF_API_SECRET"):
            self.assertIn(var, text)

    def test_setup_asks_before_installing(self):
        self.assertIn("install_deps.py\" --install", self.TEXT)
        self.assertRegex(self.TEXT, r"(?i)only on an explicit `?yes`?")
        self.assertNotIn("(Automatic)", self.TEXT)


# ── F2: quote, then go ─────────────────────────────────────────────────

class TestPaidGenerationIsQuotedThenWaitsForGo(unittest.TestCase):
    # Every path that can spend: where it carries its quote section (file, the heading's own
    # words, the text that marks that path's first paid step). The quote section must come
    # BEFORE that step. 1.29.2: generate-post and the full pipeline's interactive mode used to
    # generate with no quote at all (only the batch path and compose-creative / generate-video
    # had one), so a single post could spend without the user seeing a price.
    PAID = {
        "compose-creative": ("skills/compose-creative/SKILL.md", r"Quote, then go",
                             "### Stage 3: Generate and Select"),
        "generate-video": ("skills/generate-video/SKILL.md", r"Quote, then go",
                           "### Stage 2: First Frame Generation"),
        "full-pipeline batch": ("skills/full-pipeline/SKILL.md", r"Quote, then go \(batch",
                                "2. **Quote, then go, then auto-generate**"),
        "full-pipeline interactive": ("skills/full-pipeline/SKILL.md", r"Quote, then go \(interactive",
                                      "2. **Generate** \u2014 AI generates 2-3 variants"),
        "generate-post": ("commands/generate-post.md", r"Quote, then go",
                          "3. Generate the image"),
    }

    @staticmethod
    def problems(text: str, paid_marker: str, heading: str = r"Quote, then go") -> list[str]:
        out = []
        m = re.search(r"(?m)^#{2,4} " + heading + r"\b.*$", text)
        if not m:
            return ["no 'Quote, then go' section"]
        nxt = re.search(r"(?m)^#{1,4} (?!Quote, then go)", text[m.end():])
        section = text[m.end(): m.end() + nxt.start()] if nxt else text[m.end():]
        if text.find(paid_marker) < m.start():
            out.append("the quote section does not come before the first paid step")
        if "price_book.py" not in section or not re.search(r"--action quote(-batch)?\b", section):
            out.append("does not run price_book.py quote")
        if not re.search(r"(?i)source", section) or not re.search(r"24 hours|age_hours|\bTTL\b", section):
            out.append("does not show the source and the age/TTL of the price")
        if not re.search(r'Type "go"', section):
            out.append('never prompts the user to type "go"')
        if not re.search(r"only on an explicit `?go`?", section):
            out.append("never says to continue only on an explicit go")
        if not re.search(r"(?i)anything else[^.\n]*cancels", section):
            out.append("never says that anything else cancels")
        return out

    def test_each_paid_path_carries_the_quote_then_go_step(self):
        for name, (rel, heading, marker) in self.PAID.items():
            text = (ROOT / rel).read_text(encoding="utf-8")
            with self.subTest(path=name):
                self.assertEqual(self.problems(text, marker, heading), [])

    GOOD = ("# s\n\n## Quote, then go (before any paid call)\n\nRun `price_book.py --action quote-batch ...`. Show the total, the "
            "source URL and the age (valid for 24 hours). Type \"go\" to generate. Anything else cancels. "
            "Continue only on an explicit `go`.\n\n"
            "## Process\n\n### Stage 3: Generate and Select\n\ngenerate\n")

    def test_plant_a_skill_body_without_the_step_is_flagged(self):
        marker = "### Stage 3: Generate and Select"
        self.assertEqual(self.problems(self.GOOD, marker), [])
        self.assertEqual(self.problems(self.GOOD.replace("Quote, then go", "Estimate"), marker), ["no 'Quote, then go' section"])
        self.assertTrue(any("price_book" in p for p in self.problems(self.GOOD.replace("price_book.py", "a script"), marker)))
        self.assertTrue(any('type "go"' in p for p in self.problems(self.GOOD.replace('Type "go" to generate.', "Generating now."), marker)))
        self.assertTrue(any("explicit go" in p for p in self.problems(self.GOOD.replace("Continue only on an explicit `go`.", "Continue."), marker)))
        self.assertTrue(any("cancels" in p for p in self.problems(self.GOOD.replace("Anything else cancels.", ""), marker)))
        self.assertTrue(any("source" in p for p in self.problems(self.GOOD.replace("source URL and the age (valid for 24 hours)", "figure"), marker)))
        late = "# s\n\n### Stage 3: Generate and Select\n\ngenerate\n\n" + self.GOOD.split("# s\n\n", 1)[1]
        self.assertTrue(any("before the first paid step" in p for p in self.problems(late, marker)))

    def test_plant_the_two_paths_that_spent_without_a_quote_are_flagged(self):
        """The 1.29.1 text of both paths: a command and an interactive mode with no quote section."""
        old_command = "# Generate Post\n\n## Process\n1. Load post\n2. Load asset\n3. Generate the image using the assigned creative mode\n"
        self.assertEqual(self.problems(old_command, "3. Generate the image"), ["no 'Quote, then go' section"])
        old_interactive = ("### Interactive mode\n\n**Image posts**\n1. **Direction**\n"
                           "2. **Generate** \u2014 AI generates 2-3 variants; user picks the best\n")
        self.assertEqual(self.problems(old_interactive, "2. **Generate** \u2014 AI generates 2-3 variants",
                                       r"Quote, then go \(interactive"), ["no 'Quote, then go' section"])

    def test_privacy_sentence_and_skills_agree(self):
        privacy = (ROOT / "PRIVACY.md").read_text(encoding="utf-8")
        self.assertIn("Generation always waits for your approval of the brief and the quoted cost", privacy)

    def test_no_price_is_written_in_the_quote_sections(self):
        for name, (rel, heading, _marker) in self.PAID.items():
            text = (ROOT / rel).read_text(encoding="utf-8")
            m = re.search(r"(?m)^#{2,4} " + heading + r"\b.*$", text)
            section = text[m.end(): m.end() + 2600]
            with self.subTest(path=name):
                self.assertIsNone(re.search(r"\$\s?\d", section), "a dollar figure in a quote section")

    def test_every_dispatcher_of_the_compositor_passes_the_approved_quote(self):
        """A skill or command that hands generation to the image-compositor agent must say it
        passes the approved quote, because the agent refuses to run a paid call without one."""
        dispatchers = [p for p in list(SKILLS.glob("*/SKILL.md")) + list(COMMANDS.glob("*.md"))
                       if "image-compositor" in p.read_text(encoding="utf-8")]
        self.assertTrue(dispatchers, "no dispatcher of image-compositor found; the guard is vacuous")
        for p in dispatchers:
            with self.subTest(file=p.relative_to(ROOT).as_posix()):
                self.assertIn("approved quote", p.read_text(encoding="utf-8").lower())


class TestImageCompositorRefusesWithoutAnApprovedQuote(unittest.TestCase):
    """The agent can spend (generate_image.py, generate_video.py, edit_image.py) but has no way
    to ask the user, so it must run a paid call only when the dispatching skill hands it an
    approved quote. Before 1.29.2 its body said "WAIT for approval" at a creative stage and
    never mentioned a price."""
    AGENT = ROOT / "agents" / "image-compositor.md"
    PAID_STEP = re.compile(r"(?m)^\d+\. .*\b(?:generate_image|generate_video|edit_image)\.py")

    @classmethod
    def problems(cls, text: str) -> list[str]:
        m = re.search(r"(?m)^## Paid calls need an approved quote\b.*$", text)
        if not m:
            return ["no 'Paid calls need an approved quote' section"]
        nxt = re.search(r"(?m)^#{1,2} ", text[m.end():])
        section = text[m.end(): m.end() + nxt.start()] if nxt else text[m.end():]
        out = []
        first = cls.PAID_STEP.search(text)
        if first and first.start() < m.start():
            out.append("the section comes after the first paid script step")
        for script in ("generate_image.py", "generate_video.py", "edit_image.py"):
            if script not in section:
                out.append("does not name " + script)
        if not re.search(r"(?i)\brefuse", section):
            out.append("never says the agent refuses")
        if "needs_quote" not in section:
            out.append("never names the needs_quote result")
        if not re.search(r"(?i)dispatching (?:skill|command)", section):
            out.append("never says the dispatching skill supplies the quote")
        if not re.search(r"explicit `?go`?", section):
            out.append("never ties the quote to the user's explicit go")
        if not re.search(r"(?i)total", section) or not re.search(r"(?i)source", section):
            out.append("does not say what the approved quote carries (total, source)")
        return out

    def test_the_agent_body_carries_the_refusal(self):
        self.assertEqual(self.problems(self.AGENT.read_text(encoding="utf-8")), [])

    GOOD = ("# A\n\n## Paid calls need an approved quote\n\ngenerate_image.py, generate_video.py and edit_image.py spend. "
            "Run one only when the dispatching skill passes an approved quote: the total, the source and age of the price, "
            "and the user's explicit `go`. Otherwise refuse and return `status: needs_quote`.\n\n"
            "## Pipeline\n\n1. Run generate_image.py\n")

    def test_plant_the_agent_without_the_refusal_is_flagged(self):
        self.assertEqual(self.problems(self.GOOD), [])
        self.assertEqual(self.problems(self.GOOD.replace("Paid calls need an approved quote", "Spending")),
                         ["no 'Paid calls need an approved quote' section"])
        self.assertTrue(any("refuses" in p for p in self.problems(self.GOOD.replace("refuse", "ask"))))
        self.assertTrue(any("needs_quote" in p for p in self.problems(self.GOOD.replace("needs_quote", "stop"))))
        self.assertTrue(any("dispatching" in p for p in self.problems(self.GOOD.replace("dispatching skill", "caller"))))
        self.assertTrue(any("explicit go" in p for p in self.problems(self.GOOD.replace("explicit `go`", "approval"))))
        self.assertTrue(any("edit_image.py" in p for p in self.problems(self.GOOD.replace("edit_image.py", "an editor"))))
        late = "# A\n\n1. Run generate_image.py\n\n" + self.GOOD.split("# A\n\n", 1)[1].replace("1. Run generate_image.py\n", "")
        self.assertTrue(any("after the first paid" in p for p in self.problems(late)))


# ── S4 / F3: what the docs say ─────────────────────────────────────────

class TestDocsMatchWhatRuns(unittest.TestCase):
    PRIVACY = (ROOT / "PRIVACY.md").read_text(encoding="utf-8")

    def test_privacy_rows(self):
        for needle in ("timestamp.digicert.com", "SOCIALFORGE_INSTALL_DEPS=1", "rembg", "application-default credentials",
                       "makes no Drive call"):
            self.assertIn(needle, self.PRIVACY)
        self.assertNotIn("the first time a provider you have a key for needs its SDK", self.PRIVACY)

    def test_no_user_facing_text_claims_an_automatic_install(self):
        offenders = []
        files = list(SKILLS.glob("*/*.md")) + list(COMMANDS.glob("*.md")) + [ROOT / "README.md", ROOT / "PRIVACY.md"] \
            + list((ROOT / "docs").glob("*.md"))
        for p in files:
            text = p.read_text(encoding="utf-8", errors="replace")
            if re.search(r"(?i)auto-?install|installs? automatically|automatically installs?|installed automatically", text):
                offenders.append(str(p.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_plant_the_claim_is_recognised(self):
        self.assertTrue(re.search(r"(?i)auto-?install", "The script auto-installs them via pip"))

    def test_the_readme_has_no_byte_order_mark(self):
        self.assertNotEqual((ROOT / "README.md").read_bytes()[:3], b"\xef\xbb\xbf")


# ── S3 (sweep): every --brand / --month goes through the validating type ───

class TestEveryBrandAndMonthArgumentIsValidated(unittest.TestCase):
    # Scripts allowed to validate some other way, with the reason.
    OWN_CHECK = {
        "status_manager.py": "checks right after parse so its error stays a JSON object with exit 1 (tested above)",
    }

    @staticmethod
    def unvalidated(source: str) -> list[str]:
        """Names of --brand/--month arguments declared without type=_common.path_component."""
        import ast
        bad = []
        for node in ast.walk(ast.parse(source)):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument"
                    and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value in ("--brand", "--month")):
                typed = any(k.arg == "type" and ast.unparse(k.value) == "_common.path_component" for k in node.keywords)
                if not typed:
                    bad.append(node.args[0].value)
        return bad

    @staticmethod
    def declares(source: str) -> bool:
        return bool(re.search(r'add_argument\(\s*"--(brand|month)"', source))

    def test_every_script_that_takes_brand_or_month_validates_it(self):
        offenders, checked = {}, []
        for p in sorted(SCRIPTS.glob("*.py")):
            src = p.read_text(encoding="utf-8")
            if not self.declares(src) or p.name in self.OWN_CHECK:
                continue
            checked.append(p.name)
            bad = self.unvalidated(src)
            if bad or "import _common" not in src:
                offenders[p.name] = bad or ["_common not imported"]
        self.assertEqual(offenders, {})
        self.assertGreaterEqual(len(checked), 15, "the scan found suspiciously few scripts")
        for name in self.OWN_CHECK:
            self.assertTrue((SCRIPTS / name).exists())

    def test_plant_a_script_without_the_type_is_flagged(self):
        good = 'parser.add_argument("--brand", type=_common.path_component, required=True)' + chr(10)
        bad_brand = 'parser.add_argument("--brand", required=True)' + chr(10)
        bad_month = 'ap.add_argument(' + chr(10) + '    "--month", required=True, help="YYYY-MM")' + chr(10)
        self.assertEqual(self.unvalidated(good), [])
        self.assertEqual(self.unvalidated(bad_brand), ["--brand"])
        self.assertEqual(self.unvalidated(bad_month), ["--month"])
        self.assertEqual(self.unvalidated('parser.add_argument("--post-id")' + chr(10)), [])

    def test_each_script_refuses_a_path_before_doing_anything(self):
        names = [p.name for p in sorted(SCRIPTS.glob("*.py"))
                 if self.declares(p.read_text(encoding="utf-8")) and p.name not in self.OWN_CHECK]
        for name in names:
            for flag, value in (("--brand", "../x"), ("--brand", "a" + chr(92) + "b"), ("--month", "/abs")):
                with self.subTest(script=name, flag=flag, value=value):
                    if flag == "--month" and "--month" not in (SCRIPTS / name).read_text(encoding="utf-8"):
                        continue
                    p = subprocess.run([sys.executable, str(SCRIPTS / name), flag, value],
                                       capture_output=True, text=True, timeout=60)
                    self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                    self.assertIn("single folder name", p.stderr)

    def test_the_empty_default_still_means_not_given(self):
        cm = load("_common.py", "sf_common")
        self.assertEqual(cm.path_component(""), "")
        for good in ("acme", "Acme Coffee", "2026-11"):
            self.assertEqual(cm.path_component(good), good)
        for bad in ("../x", "a/b", "C:x", "x" + chr(92) + "y", ".."):
            with self.assertRaises(__import__("argparse").ArgumentTypeError):
                cm.path_component(bad)

    def test_safe_child_in_the_shared_module(self):
        cm = load("_common.py", "sf_common2")
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(cm.safe_child(d, "ok").parent, Path(d).resolve())
            for bad in ("../x", "..", "a/b", "/abs", ""):
                with self.assertRaises(ValueError):
                    cm.safe_child(d, bad)


# ── the credentials the scripts read are declared in plugin.yaml ───────

class TestCredentialsAreDeclared(unittest.TestCase):
    """Hermes shows `optional_env` / `requires_env` to users; `requires_env: []` while the scripts read six
    third-party credentials under-declared them (non-blocking review note). They are all optional, so they
    are listed under optional_env."""

    READ = re.compile(r"""(?:environ\.get\(|environ\[|getenv\()\s*["']([A-Z][A-Z0-9_]+)["']""")
    CREDENTIAL = re.compile(r"(_KEY|_TOKEN|_SECRET|_PROJECT|_LOCATION|_CREDENTIALS)$")

    @classmethod
    def read_by_scripts(cls) -> set[str]:
        names = set()
        for p in SCRIPTS.glob("*.py"):
            names.update(cls.READ.findall(p.read_text(encoding="utf-8", errors="replace")))
        return {n for n in names if cls.CREDENTIAL.search(n)}

    @staticmethod
    def declared(yaml_text: str) -> set[str]:
        return set(re.findall(r"(?m)^\s*-\s*name:\s*([A-Z][A-Z0-9_]+)\s*$", yaml_text))

    def test_every_credential_a_script_reads_is_listed(self):
        text = (ROOT / "plugin.yaml").read_text(encoding="utf-8")
        missing = sorted(self.read_by_scripts() - self.declared(text))
        self.assertEqual(missing, [], "scripts read these credentials but plugin.yaml does not list them")
        self.assertGreaterEqual(len(self.read_by_scripts()), 3, "the scan found suspiciously few credentials")

    def test_nothing_is_required_to_install(self):
        self.assertIn("requires_env: []", (ROOT / "plugin.yaml").read_text(encoding="utf-8"))

    def test_plant_an_undeclared_credential_is_flagged(self):
        sample = 'key = os.environ.get("NEW_VENDOR_API_KEY")'
        found = {n for n in self.READ.findall(sample) if self.CREDENTIAL.search(n)}
        self.assertEqual(found, {"NEW_VENDOR_API_KEY"})
        self.assertEqual(found - self.declared("optional_env:\n  - name: OTHER_API_KEY\n"), {"NEW_VENDOR_API_KEY"})


if __name__ == "__main__":
    unittest.main()
