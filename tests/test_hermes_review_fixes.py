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
                "`scripts/` folder, next to `skills/`. Run them with Python 3.10 or newer: `python`, or "
                "`python3` where `python` is not found (macOS, many Linux systems).")

    @staticmethod
    def missing(text: str, sentence: str) -> bool:
        return "CLAUDE_PLUGIN_ROOT" in text.replace(sentence, "") and sentence not in text

    def test_every_skill_command_and_agent_that_uses_the_variable_says_where_the_scripts_are(self):
        files = sorted(SKILLS.glob("*/SKILL.md")) + sorted(COMMANDS.glob("*.md")) + sorted((ROOT / "agents").glob("*.md"))
        bad = [str(p.relative_to(ROOT)) for p in files
               if self.missing(p.read_text(encoding="utf-8", errors="replace"), self.SENTENCE)]
        self.assertEqual(bad, [])

    def test_plant_a_skill_without_the_sentence_is_flagged(self):
        self.assertTrue(self.missing("run `python ${CLAUDE_PLUGIN_ROOT}/scripts/x.py`", self.SENTENCE))
        self.assertFalse(self.missing("run `python ${CLAUDE_PLUGIN_ROOT}/scripts/x.py`\n" + self.SENTENCE, self.SENTENCE))
        self.assertFalse(self.missing("no variable here", self.SENTENCE))

    def test_plant_the_one_line_sentence_of_1_29_2_is_flagged(self):
        """Before 1.29.3 the line stopped at the folder and said nothing about which Python to run."""
        old = "If your host does not set `${CLAUDE_PLUGIN_ROOT}`, the scripts are in this plugin's `scripts/` folder, next to `skills/`."
        self.assertTrue(self.missing("run `python ${CLAUDE_PLUGIN_ROOT}/scripts/x.py`\n" + old, self.SENTENCE))
        self.assertIn("`python`", self.SENTENCE)


class TestNoPython3AsTheCommand(unittest.TestCase):
    """1.29.3: `python3` often does not resolve on Windows, where a smoke test of the installed plugin found 28 uses of it
    in skills, commands and the compositor agent. They run Python as `python` (as ContentForge and Digital Marketing Pro
    do); the script-location line above says to fall back to `python3` where `python` is not found."""
    COMMAND = re.compile(r"(?<![\w/.-])python3(?=\s+[\w\"'$./-])")

    @classmethod
    def files(cls):
        out = sorted(SKILLS.glob("*/SKILL.md")) + sorted(COMMANDS.glob("*.md")) + sorted((ROOT / "agents").glob("*.md"))
        return out + [ROOT / "SUBMISSION.md", ROOT / "TESTING-GUIDE.md"] + sorted((ROOT / "references").rglob("*.md"))

    def test_no_instruction_file_or_user_doc_runs_python3(self):
        files = self.files()
        self.assertGreater(len(files), 40, "the scan found too few files; the guard is vacuous")
        bad = []
        for p in files:
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if self.COMMAND.search(line):
                    bad.append("%s:%d" % (p.relative_to(ROOT).as_posix(), i))
        self.assertEqual(bad, [])

    def test_plant_the_old_commands_are_flagged_and_the_fallback_sentence_is_not(self):
        self.assertTrue(self.COMMAND.search('python3 "${CLAUDE_PLUGIN_ROOT}/scripts/price_book.py" --action quote'))
        self.assertTrue(self.COMMAND.search("   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/video_postprocess.py --input x"))
        self.assertTrue(self.COMMAND.search("python3 --version"))
        self.assertFalse(self.COMMAND.search('python "${CLAUDE_PLUGIN_ROOT}/scripts/price_book.py" --action quote'))
        self.assertFalse(self.COMMAND.search(TestScriptRootFallback.SENTENCE))


class TestScriptInvocationsAreRobust(unittest.TestCase):
    """A fresh-install smoke test found files that run scripts by a path that only works from one folder: `python scripts/x.py`
    resolves against the host's working directory (the user's project, not the plugin), and an unquoted
    `python ${CLAUDE_PLUGIN_ROOT}/scripts/x.py` breaks when the plugin is installed under a path with a space. This guard
    DISCOVERS every skill, command, agent and reference file that runs a script and requires (1) the script-location line,
    (2) no relative `scripts/` invocation, (3) every `${CLAUDE_PLUGIN_ROOT}` script path quoted."""

    RUN = re.compile(r"(?<![\w/.-])python\s+(?:-\w+\s+)*[\"']?(?:\./)?(?:\$\{CLAUDE_PLUGIN_ROOT\}/)?scripts/[\w./-]+")
    RELATIVE = re.compile(r"(?<![\w/.-])python\s+(?:-\w+\s+)*[\"']?(?:\./)?scripts/")
    UNQUOTED = re.compile(r"(?<![\w/.-])python\s+(?:-\w+\s+)*\$\{CLAUDE_PLUGIN_ROOT\}/")
    EXEMPT = {
        "references/c2pa-production-cert.md": "a guide for the person setting up a production certificate: its commands are run from the plugin folder in a terminal",
    }

    # Discovery is inverted: every markdown file is covered unless it is contributor documentation that runs from a repository
    # clone (where a relative `python scripts/x.py` is right). A folder added tomorrow (the way utils/ was missed) is covered by default.
    EXCLUDED_DIRS = {"docs", "tests", "research", "evals", "node_modules", "hermes", "heroes", "__pycache__"}
    EXCLUDED_FILES = {"CHANGELOG.md", "CONTRIBUTING.md", "TESTING-GUIDE.md", "TESTING.md", "SUBMISSION.md", "UPGRADE-GUIDE.md"}

    @classmethod
    def files(cls) -> dict:
        out = {}
        for dirpath, dirs, names in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in cls.EXCLUDED_DIRS and not d.startswith(".")]
            for name in sorted(names):
                if name.endswith(".md") and name not in cls.EXCLUDED_FILES and not name.startswith("README"):
                    p = Path(dirpath) / name
                    out[p.relative_to(ROOT).as_posix()] = p.read_text(encoding="utf-8", errors="replace")
        return out

    @classmethod
    def docs_files(cls) -> dict:
        """docs/ is excluded above (maintainer scripts run from a clone), but a command a person or a model copies from it must still
        survive a plugin folder with a space in its name."""
        return {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8", errors="replace") for p in sorted((ROOT / "docs").glob("**/*.md"))}

    @classmethod
    def problems(cls, files: dict, exempt: dict = None) -> list:
        exempt = cls.EXEMPT if exempt is None else exempt
        out = []
        for rel, text in files.items():
            if rel in exempt:
                continue
            lines = text.splitlines()
            if any(cls.RUN.search(l) for l in lines) and TestScriptRootFallback.SENTENCE not in text:
                out.append(rel + ": runs a script but has no script-location line")
            for n, l in enumerate(lines, 1):
                if cls.RELATIVE.search(l):
                    out.append("%s:%d: runs a script by a relative path" % (rel, n))
                if cls.UNQUOTED.search(l):
                    out.append("%s:%d: the ${CLAUDE_PLUGIN_ROOT} script path is not quoted" % (rel, n))
        return out

    def test_every_file_that_runs_a_script_invokes_it_robustly(self):
        files = self.files()
        running = [r for r, t in files.items() if any(self.RUN.search(l) for l in t.splitlines())]
        self.assertGreaterEqual(len(running), 10, "the discovery found too few files; the guard is vacuous")
        self.assertEqual(self.problems(files), [])

    def test_every_exemption_is_a_real_file_with_a_reason(self):
        files = self.files()
        for rel, why in self.EXEMPT.items():
            with self.subTest(file=rel):
                self.assertIn(rel, files)
                self.assertGreater(len(why), 20)

    def test_docs_quote_the_plugin_root_script_path(self):
        bad = ["%s:%d" % (rel, n) for rel, text in self.docs_files().items() for n, line in enumerate(text.splitlines(), 1)
               if self.UNQUOTED.search(line)]
        self.assertEqual(bad, [])
        self.assertTrue(self.UNQUOTED.search("python ${CLAUDE_PLUGIN_ROOT}/scripts/x.py --a"))   # the plant
        self.assertFalse(self.UNQUOTED.search('python "${CLAUDE_PLUGIN_ROOT}/scripts/x.py" --a'))

    def test_plant_each_of_the_three_defects_is_flagged(self):
        line = "> **Script location.** " + TestScriptRootFallback.SENTENCE
        good = "# T\n\n" + line + "\n\n```bash\npython \"${CLAUDE_PLUGIN_ROOT}/scripts/x.py\" --a 1\n```\n"
        self.assertEqual(self.problems({"skills/t/SKILL.md": good}, exempt={}), [])
        call = 'python "${CLAUDE_PLUGIN_ROOT}/scripts/x.py"'
        planted = {
            "relative": (good.replace(call, "python scripts/x.py"), "relative path"),
            "unquoted": (good.replace(call, "python ${CLAUDE_PLUGIN_ROOT}/scripts/x.py"), "not quoted"),
            "no line": (good.replace(line, ""), "no script-location line"),
        }
        for name, (text, needle) in planted.items():
            with self.subTest(defect=name):
                found = self.problems({"skills/t/SKILL.md": text}, exempt={})
                self.assertTrue(any(needle in f for f in found), found)

    def test_discovery_reaches_a_supporting_file_inside_a_skill_folder(self):
        """1.29.5: skills/render-carousels/prerequisites-and-output.md ran `python scripts/install_deps.py` by a relative path with no
        location line, and the scan (SKILL.md and skills/*/references only) could not see it."""
        rel = "skills/render-carousels/prerequisites-and-output.md"
        self.assertIn(rel, self.files())
        old = "# Prerequisites\n\n- `render_carousel.py` returns the same pointer: `python scripts/install_deps.py --groups carousel`.\n"
        files = self.files()   # inverted discovery: the repository root and any new folder are scanned
        self.assertIn("AGENTS.md", files)
        self.assertIn("SOCIALFORGE-COMPLETE-ENGINEERING-SPEC.md", files)
        self.assertNotIn("CHANGELOG.md", files)
        self.assertFalse(any(rel.startswith("docs/") for rel in files))
        found = self.problems({rel: old}, exempt={})
        self.assertTrue(any("relative path" in f for f in found) and any("no script-location line" in f for f in found), found)


class TestScriptsPrintAbsoluteCommands(unittest.TestCase):
    """1.29.5: render_carousel.py (and eleven more scripts) printed "Run: python scripts/install_deps.py ...", which is relative to
    the host's working folder, not the plugin. A command a script tells someone to run comes from _common.script_command: the
    running interpreter and the script's absolute path. Docstrings (usage text) are not output and are left alone."""
    HINT = re.compile(r"\bpython3?\s+(?:\./)?scripts/")

    @classmethod
    def findings(cls, source: str, name: str = "x.py") -> list:
        import ast
        tree = ast.parse(source)
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
                first = node.body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                    docstrings.add(id(first.value))
        return ["%s:%d" % (name, n.lineno) for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings and cls.HINT.search(n.value)]

    def test_no_script_prints_a_relative_python_scripts_command(self):
        scripts = sorted((ROOT / "scripts").glob("*.py"))
        self.assertGreater(len(scripts), 20, "the scan found too few scripts; the guard is vacuous")
        bad = [f for p in scripts for f in self.findings(p.read_text(encoding="utf-8"), p.name)]
        self.assertEqual(bad, [])

    def test_plant_the_old_hints_are_flagged_and_usage_text_and_the_helper_are_not(self):
        old = 'def f():\n    return {"error": "Pillow is not installed. Run: python scripts/install_deps.py (pinned)"}\n'
        old_fstring = 'def g(exc):\n    return f"wavespeed is not installed ({exc}). Run: python scripts/install_deps.py"\n'
        usage = '"""Usage:\n    python scripts/install_deps.py --groups image\n"""\n\ndef h():\n    """Run python scripts/x.py"""\n    return 1\n'
        fixed = 'def f():\n    return {"error": "Run: " + _common.script_command("install_deps.py")}\n'
        self.assertEqual(len(self.findings(old)), 1)
        self.assertEqual(len(self.findings(old_fstring)), 1)
        self.assertEqual(self.findings(usage), [])
        self.assertEqual(self.findings(fixed), [])

    def test_script_command_is_the_running_interpreter_and_the_absolute_script(self):
        sys.path.insert(0, str(SCRIPTS))
        import _common
        cmd = _common.script_command("price_book.py", "--action", "providers")
        self.assertTrue((SCRIPTS / "price_book.py").exists())
        self.assertIn('"%s"' % (SCRIPTS / "price_book.py").as_posix(), cmd)   # forward slashes, double-quoted
        self.assertNotIn("\\", cmd)                                         # bash drops a backslash
        self.assertNotIn("python scripts/", cmd)

    def test_the_command_shape_without_and_with_a_space_in_the_interpreter_path(self):
        """Pasted into Git Bash a backslash path arrived as `C:Python313python.exe` (exit 127), and a quoted first token is a string
        literal in PowerShell: forward slashes, the script always double-quoted, the interpreter quoted only when it has a space."""
        sys.path.insert(0, str(SCRIPTS))
        import _common
        from unittest import mock
        with mock.patch.object(sys, "executable", "C:\\Python313\\python.exe"):
            plain = _common.script_command("x.py", "--a", "1")
        self.assertTrue(plain.startswith('C:/Python313/python.exe "'), plain)
        self.assertTrue(plain.endswith('/scripts/x.py" --a 1'), plain)
        self.assertNotIn("PowerShell", plain)
        with mock.patch.object(sys, "executable", "C:\\Program Files\\Python313\\python.exe"):
            spaced = _common.script_command("x.py", "--a", "1")
        self.assertTrue(spaced.startswith('"C:/Program Files/Python313/python.exe" "'), spaced)
        self.assertTrue(spaced.endswith("--a 1  # in PowerShell, put & before it"), spaced)
        self.assertNotIn("\\", plain + spaced)

    def _runnable(self):
        sys.path.insert(0, str(SCRIPTS))
        import _common
        return _common.script_command("price_book.py", "--action", "providers").split("  # in PowerShell")[0]

    def test_the_command_runs_pasted_into_git_bash_from_another_folder(self):
        import shutil
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("no bash on PATH")
        kernel = subprocess.run([bash, "-c", "uname -s"], capture_output=True, text=True).stdout
        if sys.platform == "win32" and not any(k in kernel for k in ("MINGW", "MSYS", "CYGWIN")):
            self.skipTest("this bash is not Git Bash (WSL cannot run a Windows interpreter path)")
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([bash, "-c", self._runnable()], capture_output=True, text=True, cwd=d, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("wavespeed", r.stdout)

    def test_the_command_runs_pasted_into_powershell_from_another_folder(self):
        import shutil
        ps = shutil.which("powershell") or shutil.which("pwsh")
        if not ps:
            self.skipTest("no PowerShell on PATH")
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-Command", self._runnable()], capture_output=True, text=True, cwd=d, timeout=180)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("wavespeed", r.stdout)

    def _spaced_line(self):
        sys.path.insert(0, str(SCRIPTS))
        import _common
        from unittest import mock
        with mock.patch.object(sys, "executable", "C:\\Program Files\\Python313\\python.exe"):
            return _common.script_command("price_book.py", "--action", "providers")

    def test_the_space_case_line_parses_in_git_bash(self):
        """The note was first a parenthetical after the arguments, which bash rejects (`syntax error near unexpected token '('`).
        A trailing comment is ignored by bash and by PowerShell."""
        import shutil
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("no bash on PATH")
        kernel = subprocess.run([bash, "-c", "uname -s"], capture_output=True, text=True).stdout
        if sys.platform == "win32" and not any(k in kernel for k in ("MINGW", "MSYS", "CYGWIN")):
            self.skipTest("this bash is not Git Bash (WSL cannot parse a Windows interpreter path)")
        line = self._spaced_line()
        self.assertTrue(line.startswith('"C:/Program Files/'), line)
        ok = subprocess.run([bash, "-n", "-c", line], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, line + "\n" + ok.stderr)
        parenthetical = line.split("  # in PowerShell")[0] + " (in PowerShell, put & before it)"
        bad = subprocess.run([bash, "-n", "-c", parenthetical], capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 0, "the parenthetical form must fail `bash -n`, or this guard proves nothing")

    def test_the_space_case_line_runs_in_powershell_with_an_ampersand_and_not_without_one(self):
        import shutil
        ps = shutil.which("powershell") or shutil.which("pwsh")
        if not ps or sys.platform != "win32":
            self.skipTest("needs Windows PowerShell (the interpreter stand-in is a .cmd file in a folder with a space)")
        sys.path.insert(0, str(SCRIPTS))
        import _common
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            shim_dir = Path(d) / "dir with space"
            shim_dir.mkdir()
            shim = shim_dir / "pyshim.cmd"
            shim.write_text('@echo off\r\n"%s" %%*\r\n' % sys.executable, encoding="ascii")
            with mock.patch.object(sys, "executable", str(shim).replace("\\", "/")):
                line = _common.script_command("price_book.py", "--action", "providers")
            self.assertTrue(line.startswith('"'), line)
            run = lambda command: subprocess.run([ps, "-NoProfile", "-NonInteractive", "-Command", command],
                                                 capture_output=True, text=True, cwd=d, timeout=180)
            with_amp, without = run("& " + line), run(line)
        self.assertEqual(with_amp.returncode, 0, with_amp.stdout + with_amp.stderr)
        self.assertIn("wavespeed", with_amp.stdout)
        self.assertNotEqual(without.returncode, 0, "without `&` PowerShell reads the quoted path as a string")


class TestAgentWrittenInputsAcceptABom(unittest.TestCase):
    """1.29.5: PowerShell 5.1 writes a UTF-8 byte-order mark by default (Out-File, Set-Content -Encoding utf8). A plan file written
    that way was refused, and a calendar or brand config written that way would not have parsed. Inputs an agent or a user writes are
    read with utf-8-sig, which reads plain UTF-8 unchanged. Files the plugin writes and reads itself are not touched."""
    EXTERNAL = re.compile(r"\b(?:calendar_path|config_path|slides_path|json_path|source_file|rules_path)\.read_text\(encoding=\"utf-8\"\)")

    def test_no_script_reads_an_agent_or_user_written_input_without_allowing_a_bom(self):
        scripts = sorted((ROOT / "scripts").glob("*.py"))
        bad = ["%s:%d" % (p.name, n) for p in scripts for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
               if self.EXTERNAL.search(line)]
        self.assertEqual(bad, [])

    def test_plant_the_old_reads_are_flagged_and_the_fix_is_not(self):
        self.assertTrue(self.EXTERNAL.search('calendar = json.loads(calendar_path.read_text(encoding="utf-8"))'))
        self.assertTrue(self.EXTERNAL.search('config = json.loads(config_path.read_text(encoding="utf-8"))'))
        self.assertFalse(self.EXTERNAL.search('calendar = json.loads(calendar_path.read_text(encoding="utf-8-sig"))'))
        self.assertFalse(self.EXTERNAL.search('tracker = json.loads(tracker_path.read_text(encoding="utf-8"))'))

    def test_a_file_with_a_bom_reads_like_the_plain_file(self):
        sys.path.insert(0, str(SCRIPTS))
        import delivery_audit
        body = '{"posts": [{"id": "P01", "platforms": ["linkedin"]}]}'
        with tempfile.TemporaryDirectory() as d:
            plain, bom = Path(d) / "plain.json", Path(d) / "bom.json"
            plain.write_text(body, encoding="utf-8")
            bom.write_bytes(b"\xef\xbb\xbf" + body.encode("utf-8"))
            self.assertIsNotNone(delivery_audit._json(plain))
            self.assertEqual(delivery_audit._json(bom), delivery_audit._json(plain))


class TestErrorResultsExitNonZero(unittest.TestCase):
    """1.29.6: edit_image.py, adapt_copy.py, the credential_manager.py setup actions and render_carousel.py printed {"error": ...} and exited 0,
    so an `&&` chain, a CI step or a batch loop read the failure as success. Offline: every credential-like variable is stripped, so no
    provider is called."""

    def _run(self, script, *args):
        with tempfile.TemporaryDirectory() as home:
            env = {k: v for k, v in os.environ.items() if not any(w in k.upper() for w in ("KEY", "SECRET", "TOKEN", "CRED", "PASSWORD"))}
            env.update(HOME=home, USERPROFILE=home, APPDATA=home, CLAUDE_PLUGIN_DATA=home)
            return subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True, env=env, cwd=home, timeout=120)

    def test_a_failed_image_edit_exits_1(self):
        r = self._run("edit_image.py", "--image", str(ROOT / "no-such.png"), "--instruction", "x", "--output", str(ROOT / "o.png"))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("error", json.loads(r.stdout))

    def test_an_unknown_platform_exits_1(self):
        r = self._run("adapt_copy.py", "--text", "hello", "--platform", "no-such-platform")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("error", json.loads(r.stdout))

    def test_a_missing_service_account_file_exits_1(self):
        r = self._run("credential_manager.py", "setup-vertex", "--json-path", str(ROOT / "no-such-key.json"))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("error", json.loads(r.stdout))

    def test_the_success_paths_still_exit_0(self):
        a = self._run("adapt_copy.py", "--text", "hello", "--platform", "linkedin")
        self.assertEqual(a.returncode, 0, a.stdout + a.stderr)
        self.assertNotIn("error", json.loads(a.stdout))
        b = self._run("credential_manager.py", "status")
        self.assertEqual(b.returncode, 0, b.stdout + b.stderr)

    def test_render_carousel_exits_1_when_the_render_reports_an_error_and_0_when_it_does_not(self):
        sys.path.insert(0, str(SCRIPTS))
        import render_carousel
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            slides = Path(d) / "slides.json"
            slides.write_text('[{"title": "t"}]', encoding="utf-8")
            argv = ["render_carousel.py", "--template", "generic", "--slides", str(slides), "--brand", "b", "--output-dir", d]
            for result, code in (({"error": "Playwright is not installed. Run: python x.py"}, 1), ({"status": "success", "slides": []}, 0)):
                with self.subTest(result=result), mock.patch.object(sys, "argv", argv), \
                        mock.patch.object(render_carousel, "render_slides", return_value=result), \
                        mock.patch("builtins.print"), self.assertRaises(SystemExit) as cm:
                    render_carousel.main()
                self.assertEqual(cm.exception.code, code)


class TestSecretsNeverBlock(unittest.TestCase):
    """1.29.7: setup-wavespeed / setup-higgsfield with no key waited forever on Windows (an open non-TTY pipe for stdin, or NUL, which
    reports isatty() True). A key is read from stdin only with --api-key-stdin and prompted for only with --prompt on a real console;
    otherwise the script stops at once with exit 2. Every run is bounded: a child still alive after TIMEOUT fails the test, and is
    killed in a finally block so none is left behind. Each run uses a temporary home AND data folder (the credentials folder is the
    data folder only when it exists, else ~/socialforge-workspace), and a test refuses to continue if a key would land outside it."""
    TIMEOUT = 30
    WS_ERROR = "no key: pass --api-key, set WAVESPEED_API_KEY, or use --api-key-stdin"

    def _run(self, args, stdin, env_extra=None):
        """stdin is "open-pipe" (a pipe nobody closes, like the Bash tool), "devnull" (NUL), or bytes that are written and closed."""
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as logs:
            env = {k: v for k, v in os.environ.items() if not any(w in k.upper() for w in ("KEY", "SECRET", "TOKEN", "CRED", "PASSWORD"))}
            env.update(HOME=home, USERPROFILE=home, APPDATA=home, LOCALAPPDATA=home, CLAUDE_PLUGIN_DATA=home, PLUGIN_DATA=home)
            env.update(env_extra or {})
            out_path, err_path = Path(logs) / "out.txt", Path(logs) / "err.txt"
            with open(out_path, "wb") as out, open(err_path, "wb") as err:
                proc = subprocess.Popen([sys.executable, str(SCRIPTS / "credential_manager.py"), *args],
                                        stdin=subprocess.DEVNULL if stdin == "devnull" else subprocess.PIPE,
                                        stdout=out, stderr=err, env=env, cwd=home)
                try:
                    if isinstance(stdin, bytes):
                        proc.stdin.write(stdin)
                        proc.stdin.close()
                    try:
                        proc.wait(timeout=self.TIMEOUT)
                    except subprocess.TimeoutExpired:
                        self.fail("credential_manager.py was still waiting after %d s: it reads a stream nobody is feeding" % self.TIMEOUT)
                finally:
                    if proc.poll() is None:
                        proc.kill()
                        proc.wait()
                    if proc.stdin and not proc.stdin.closed:
                        proc.stdin.close()
            text = out_path.read_text(encoding="utf-8", errors="replace")
            try:
                payload = json.loads(text)
            except ValueError:
                payload = {"_stdout": text, "_stderr": err_path.read_text(encoding="utf-8", errors="replace")}
            stored = payload.get("stored_at", "")
            if stored:
                self.assertTrue(os.path.normcase(os.path.abspath(stored)).startswith(os.path.normcase(os.path.abspath(home))),
                                "a key was stored outside the temporary folder: " + stored)
            return proc.returncode, payload

    def test_no_key_stops_at_once_with_exit_2_whatever_stdin_is(self):
        cases = {
            "wavespeed, open pipe": (["setup-wavespeed"], "open-pipe", self.WS_ERROR),
            "wavespeed, NUL": (["setup-wavespeed"], "devnull", self.WS_ERROR),
            "higgsfield, open pipe": (["setup-higgsfield"], "open-pipe", "no HiggsField API key: pass --api-key, set HF_API_KEY, or use --api-key-stdin"),
            "higgsfield, NUL": (["setup-higgsfield"], "devnull", "no HiggsField API key: pass --api-key, set HF_API_KEY, or use --api-key-stdin"),
        }
        for name, (args, stdin, message) in cases.items():
            with self.subTest(case=name):
                code, payload = self._run(args, stdin)
                self.assertEqual(code, 2, payload)
                self.assertEqual(payload.get("error"), message)

    def test_a_key_in_the_environment_is_stored_and_stdin_is_never_read(self):
        code, payload = self._run(["setup-wavespeed"], "open-pipe", {"WAVESPEED_API_KEY": "k" * 24})
        self.assertEqual((code, payload.get("status")), (0, "success"), payload)
        code, payload = self._run(["setup-higgsfield"], "open-pipe", {"HF_API_KEY": "a" * 24, "HF_API_SECRET": "b" * 24})
        self.assertEqual((code, payload.get("status")), (0, "success"), payload)

    def test_api_key_stdin_reads_exactly_what_it_is_given(self):
        code, payload = self._run(["setup-wavespeed", "--api-key-stdin"], ("k" * 24 + "\n").encode())
        self.assertEqual((code, payload.get("status")), (0, "success"), payload)
        code, payload = self._run(["setup-higgsfield", "--api-key-stdin"], ("a" * 24 + "\n" + "b" * 24 + "\n").encode())
        self.assertEqual((code, payload.get("status")), (0, "success"), payload)
        code, payload = self._run(["setup-wavespeed", "--api-key-stdin"], b"")
        self.assertEqual(code, 2, payload)
        self.assertIn("stdin held no line", payload.get("error", ""))
        code, payload = self._run(["setup-higgsfield", "--api-key-stdin"], ("a" * 24 + "\n").encode())
        self.assertEqual(code, 2, payload)      # the secret line is missing
        self.assertIn("HiggsField API secret", payload.get("error", ""))

    def test_prompt_needs_a_real_console_and_otherwise_stops_with_exit_2(self):
        for stdin in ("open-pipe", "devnull"):
            with self.subTest(stdin=stdin):
                code, payload = self._run(["setup-wavespeed", "--prompt"], stdin)
                self.assertEqual(code, 2, payload)
                self.assertIn("real console", payload.get("error", ""))


class TestNoImplicitStdinReads(unittest.TestCase):
    """1.29.7: `credential_manager.py setup-wavespeed` with no key blocked forever on Windows. The Bash tool's stdin is an open pipe, so
    readline() never returns, and `stdin < NUL` reports isatty() True, so getpass blocks on the console. A script never reads stdin or
    prompts unless the caller passed an explicit flag; `getpass.getuser()` (the user NAME) is not a read."""
    CALLS = {"input", "getpass.getpass"}
    ATTRS = {"sys.stdin.read", "sys.stdin.readline", "sys.stdin.readlines", "sys.stdin.buffer.read", "sys.stdin.buffer.readline"}
    # Where an explicit flag gates the read; every other script has none.
    ALLOWED = {"credential_manager.py"}

    @classmethod
    def findings(cls, source: str, name: str = "x.py") -> list:
        import ast
        out = []
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Call) and ast.unparse(node.func) in cls.CALLS:
                out.append("%s:%d: %s()" % (name, node.lineno, ast.unparse(node.func)))
            if isinstance(node, ast.Attribute) and ast.unparse(node) in cls.ATTRS:
                out.append("%s:%d: %s" % (name, node.lineno, ast.unparse(node)))
        return out

    def test_only_the_flag_gated_readers_touch_stdin_or_prompt(self):
        scripts = sorted((ROOT / "scripts").glob("*.py"))
        self.assertGreater(len(scripts), 20, "the scan found too few scripts; the guard is vacuous")
        bad = [f for p in scripts if p.name not in self.ALLOWED for f in self.findings(p.read_text(encoding="utf-8"), p.name)]
        self.assertEqual(bad, [])
        for name in self.ALLOWED:
            self.assertIn(name, [p.name for p in scripts])

    def test_plant_each_kind_of_implicit_read_is_flagged_and_getuser_is_not(self):
        for source in ("x = input('key: ')\n", "import getpass\nk = getpass.getpass('k')\n", "import sys\nk = sys.stdin.readline()\n",
                       "import sys\nk = sys.stdin.read()\n", "import sys\nit = iter(sys.stdin.readline, '')\n"):
            with self.subTest(source=source):
                self.assertTrue(self.findings(source), source)
        self.assertEqual(self.findings("import getpass\nuser = getpass.getuser()\n"), [])


class TestPrintedCommandsAreLastOnTheLine(unittest.TestCase):
    """4.5.6 / 1.29.6 as first built: three recovery messages did `script_command("run-audit.py") + " --brand ..."`. With an interpreter
    path that has a space the command ends in a trailing comment, so those arguments became part of the comment and the pasted command
    ran with none (exit 2). A printed command is built with every argument as a token and nothing is appended after it."""
    FUNCS = {"script_command", "install_command", "browser_command", "printed_command"}

    @classmethod
    def _is_command(cls, node) -> bool:
        import ast
        return isinstance(node, ast.Call) and (getattr(node.func, "attr", None) or getattr(node.func, "id", None)) in cls.FUNCS

    @classmethod
    def _flag_text(cls, node) -> bool:
        import ast
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value.startswith(" -")
        if isinstance(node, ast.JoinedStr) and node.values and isinstance(node.values[0], ast.Constant):
            return str(node.values[0].value).startswith(" -")
        return False

    @classmethod
    def findings(cls, source: str, name: str = "x.py") -> list:
        import ast
        out = []
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                left = node.left
                while isinstance(left, ast.BinOp) and isinstance(left.op, ast.Add):
                    left = left.right
                if cls._is_command(left) and cls._flag_text(node.right):
                    out.append("%s:%d" % (name, node.lineno))
            if isinstance(node, ast.JoinedStr):
                for here, after in zip(node.values, node.values[1:]):
                    if isinstance(here, ast.FormattedValue) and cls._is_command(here.value) and cls._flag_text(after):
                        out.append("%s:%d" % (name, node.lineno))
        return out

    def test_no_script_appends_arguments_after_a_printed_command(self):
        scripts = sorted((ROOT / "scripts").glob("*.py"))
        self.assertGreater(len(scripts), 20, "the scan found too few scripts; the guard is vacuous")
        bad = [f for p in scripts for f in self.findings(p.read_text(encoding="utf-8"), p.name)]
        self.assertEqual(bad, [])

    def test_plant_the_old_forms_are_flagged_and_the_good_forms_are_not(self):
        concat = '_common.script_command("run-audit.py") + " --brand " + brand\n'
        chained = '"Run: " + _common.script_command("run-audit.py") + " --brand " f"{brand} --run-id {rid}" "  then finalize"\n'
        fstring = 'm = f"{_common.script_command(\'run-audit.py\')} --brand {brand}"\n'
        for source in (concat, chained, fstring):
            with self.subTest(source=source):
                self.assertEqual(len(self.findings(source)), 1, source)
        good = '"Re-run the audit: " + _common.script_command("run-audit.py", "--brand", brand, "--run-id", rid)\n'
        prose_after = '"Run: " + install_command(["Pillow"]) + " (it prints the pinned command)"\n'
        self.assertEqual(self.findings(good), [])
        self.assertEqual(self.findings(prose_after), [])   # prose after a command is harmless (a comment); an argument is not


class TestInstallHintsUseThePrintedShape(unittest.TestCase):
    """What is PRINTED for someone to paste is a shell line in the printed shape; what is EXECUTED is an argv list and never a string."""

    def _both(self, make):
        from unittest import mock
        with mock.patch.object(sys, "executable", "C:\\Python313\\python.exe"):
            plain = make()
        with mock.patch.object(sys, "executable", "C:\\Program Files\\Python313\\python.exe"):
            spaced = make()
        return plain, spaced

    def test_the_pip_hint_has_forward_slashes_and_the_note_only_when_the_path_has_a_space(self):
        sys.path.insert(0, str(SCRIPTS))
        import install_deps
        plain, spaced = self._both(lambda: install_deps.install_command(["Pillow"]))
        self.assertTrue(plain.startswith("C:/Python313/python.exe -m pip install "), plain)
        self.assertNotIn("PowerShell", plain)
        self.assertTrue(spaced.startswith('"C:/Program Files/Python313/python.exe" -m pip install '), spaced)
        self.assertTrue(spaced.endswith("  # in PowerShell, put & before it"), spaced)
        self.assertNotIn("\\", plain + spaced)

    def test_the_printed_install_line_works_in_both_shells(self):
        """Git Bash gave exit 127 for the backslash form, and PowerShell a parse error for a quoted first token."""
        import shutil
        sys.path.insert(0, str(SCRIPTS))
        import _common
        from unittest import mock
        bash = shutil.which("bash")
        if bash and (sys.platform != "win32" or any(k in subprocess.run([bash, "-c", "uname -s"], capture_output=True, text=True).stdout
                                                     for k in ("MINGW", "MSYS", "CYGWIN"))):
            line = _common.printed_command("-m", "pip", "--version")
            with tempfile.TemporaryDirectory() as d:
                r = subprocess.run([bash, "-c", line], capture_output=True, text=True, cwd=d, timeout=120)
            self.assertEqual(r.returncode, 0, line + "\n" + r.stdout + r.stderr)
            self.assertIn("pip", r.stdout)
            with mock.patch.object(sys, "executable", "C:\\Program Files\\Python313\\python.exe"):
                spaced = _common.printed_command("-m", "pip", "install", "x==1")
            self.assertEqual(subprocess.run([bash, "-n", "-c", spaced], capture_output=True, text=True).returncode, 0, spaced)
        ps = shutil.which("powershell") or shutil.which("pwsh")
        if ps and sys.platform == "win32":
            line = _common.printed_command("-m", "pip", "--version")
            with tempfile.TemporaryDirectory() as d:
                shim_dir = Path(d) / "dir with space"
                shim_dir.mkdir()
                shim = shim_dir / "pyshim.cmd"
                shim.write_text('@echo off\r\n"%s" %%*\r\n' % sys.executable, encoding="ascii")
                with mock.patch.object(sys, "executable", str(shim).replace("\\", "/")):
                    spaced = _common.printed_command("-m", "pip", "--version")
                run = lambda command: subprocess.run([ps, "-NoProfile", "-NonInteractive", "-Command", command],
                                                     capture_output=True, text=True, cwd=d, timeout=180)
                plain_run, with_amp, without = run(line), run("& " + spaced), run(spaced)
            self.assertEqual(plain_run.returncode, 0, plain_run.stdout + plain_run.stderr)
            self.assertEqual(with_amp.returncode, 0, with_amp.stdout + with_amp.stderr)
            self.assertNotEqual(without.returncode, 0, "without `&` PowerShell reads the quoted path as a string")
        if not bash and not ps:
            self.skipTest("neither bash nor PowerShell is installed")


class TestNoTmpPathsInInstructions(unittest.TestCase):
    """/tmp is not one folder on Windows: Git Bash maps it to the user's temp folder while Python resolves it elsewhere, so a
    file the shell wrote was not found by the script and the command stopped. Instructions use a folder the plugin knows."""
    TMP = re.compile(r"(?<![\w.-])/tmp/")

    def test_no_skill_command_agent_or_reference_uses_a_tmp_path(self):
        files = TestScriptInvocationsAreRobust.files()
        self.assertGreater(len(files), 20, "the scan found too few files; the guard is vacuous")
        bad = ["%s:%d" % (rel, n) for rel, text in files.items() for n, l in enumerate(text.splitlines(), 1) if self.TMP.search(l)]
        self.assertEqual(bad, [])

    def test_plant_the_old_path_is_flagged_and_the_replacement_is_not(self):
        self.assertTrue(self.TMP.search("--action quote-batch --items @/tmp/run-plan.json"))
        self.assertTrue(self.TMP.search("write the plan to /tmp/plan.json"))
        self.assertFalse(self.TMP.search("write run-plan.json in the month's output folder, not in /tmp"))
        self.assertFalse(self.TMP.search("--output {tmp}/harvest.json"))


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
        "generate-all": ("commands/generate-all.md", r"Quote, then go",
                         "Generate image(s) via image-compositor agent"),
        "edit-image": ("commands/edit-image.md", r"Quote, then go",
                       "4. Only after the go above, call the editor"),
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
        return out + TestPaidGenerationIsQuotedThenWaitsForGo.section_problems(section)

    @staticmethod
    def section_problems(section: str) -> list[str]:
        out = []
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


class TestEverySpendingFilePassesThroughAQuote(unittest.TestCase):
    """1.29.3: a smoke test of the installed plugin found three more commands that could spend with no quote (edit-image,
    reactive-post, revision) and one whose quote section did not use the standard words (generate-all). The guard above
    lists the paid paths by hand, which is how they were missed. This one DISCOVERS every skill, command and agent file
    that can spend (it names a paid script, dispatches the image-compositor, or says to generate or regenerate a creative)
    and requires, for each, its own "Quote, then go" section or a named hand-off to a file that has one and says it quotes."""

    PAID_SCRIPT = re.compile(r"\b(?:generate_image|generate_video|edit_image)\.py")
    COMPOSITOR = re.compile(r"image-compositor")
    INTENT = re.compile(r"(?i)\bgenerate (?:the |a |new |an |all )?(?:creative|image|images|video|visuals?|keyframe\w*)"
                        r"|\bregenerat\w*|re-?run (?:the )?(?:affected )?pipeline steps?")
    # Files the detector flags that spend nothing, each with the reason. A file named here is not checked.
    EXEMPT = {
        "agents/image-compositor.md": "refuses a paid call without an approved quote (its own guard, below)",
        "skills/c2pa-sign/SKILL.md": "names generate_image.py only to describe its signing post-step; runs no paid script",
        "skills/brand-manager/SKILL.md": "says generation needs credentials; generates nothing",
        "skills/setup/SKILL.md": "credential setup; 'regenerate' there means rotating an API key",
    }

    @classmethod
    def files(cls) -> dict:
        paths = sorted(SKILLS.glob("*/SKILL.md")) + sorted(COMMANDS.glob("*.md")) + sorted((ROOT / "agents").glob("*.md"))
        return {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8") for p in paths}

    @staticmethod
    def body(text: str) -> str:
        return re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.S)

    @classmethod
    def spends(cls, text: str) -> bool:
        b = cls.body(text)
        return bool(cls.PAID_SCRIPT.search(b) or cls.COMPOSITOR.search(b) or cls.INTENT.search(b))

    @staticmethod
    def name_of(rel: str) -> str:
        parts = rel.split("/")
        return parts[1] if parts[-1] == "SKILL.md" else parts[-1][:-3]

    @classmethod
    def own_section(cls, text: str):
        m = re.search(r"(?m)^#{2,4} Quote, then go\b.*$", text)
        if not m:
            return None
        nxt = re.search(r"(?m)^#{1,4} (?!Quote, then go)", text[m.end():])
        return text[m.end(): m.end() + nxt.start()] if nxt else text[m.end():]

    @classmethod
    def problems(cls, files: dict, exempt: dict = None, ordered: set = None) -> list:
        exempt = cls.EXEMPT if exempt is None else exempt
        if ordered is None:
            ordered = {v[0] for v in TestPaidGenerationIsQuotedThenWaitsForGo.PAID.values()}
        spending = {rel: t for rel, t in files.items() if rel not in exempt and cls.spends(t)}
        out, compliant, pending = [], set(), {}
        for rel, t in spending.items():
            section = cls.own_section(t)
            if section is None:
                pending[rel] = t
                continue
            bad = TestPaidGenerationIsQuotedThenWaitsForGo.section_problems(section)
            if bad:
                out.append("%s: %s" % (rel, "; ".join(bad)))
            elif rel not in ordered:
                out.append("%s: has a quote section but no ordering marker in TestPaidGenerationIsQuotedThenWaitsForGo.PAID" % rel)
            else:
                compliant.add(rel)
        changed = True
        while changed:   # a hand-off may point at another hand-off, so settle to a fixed point
            changed = False
            for rel, t in list(pending.items()):
                b = cls.body(t)
                if not re.search(r"(?i)\bquote", b):
                    continue
                for c in sorted(compliant):
                    if c != rel and re.search(r"(?<![\w-])" + re.escape(cls.name_of(c)) + r"(?![\w-])", b):
                        compliant.add(rel)
                        del pending[rel]
                        changed = True
                        break
        for rel in sorted(pending):
            out.append("%s: can spend but has no 'Quote, then go' section and no named hand-off to a file that has one" % rel)
        return out

    def test_every_file_that_can_spend_is_quoted_or_hands_off_to_a_file_that_quotes(self):
        files = self.files()
        self.assertGreaterEqual(sum(1 for t in files.values() if self.spends(t)), 10, "the discovery found too little; the guard is vacuous")
        self.assertEqual(self.problems(files), [])

    def test_every_exemption_is_a_real_file_with_a_reason(self):
        files = self.files()
        for rel, why in self.EXEMPT.items():
            with self.subTest(file=rel):
                self.assertIn(rel, files)
                self.assertGreater(len(why), 20)

    CARRIER = ("---\nname: compose-creative\ndescription: x\n---\n# c\n\n## Quote, then go (before any paid call)\n\n"
               "Run `price_book.py --action quote-batch ...`. Show the total, the source URL and the age (valid for 24 hours). "
               "Type \"go\" to generate. Anything else cancels. Continue only on an explicit `go`.\n\n"
               "## Process\n\nRun generate_image.py and dispatch the image-compositor.\n")

    def planted(self, rel: str, text: str) -> list:
        files = {"skills/compose-creative/SKILL.md": self.CARRIER, rel: text}
        return self.problems(files, exempt={}, ordered={"skills/compose-creative/SKILL.md"})

    def test_plant_the_1_29_2_edit_image_is_flagged(self):
        """The command ran edit_image.py (a paid call) at step 4 with no quote; the only approval came after the edit."""
        old = ("---\ndescription: Edit a generated image\n---\n# Edit Image\n\nSend an AI edit instruction.\n\n## Process\n"
               "1. Load the current image\n3. Accept edit instruction\n4. Call the editor with the instruction plus any style references:\n"
               "   ```bash\n   python \"${CLAUDE_PLUGIN_ROOT}/scripts/edit_image.py\" --image <current> --instruction \"<text>\" --output <new>\n   ```\n"
               "5. Show edited result for approval\n")
        found = self.planted("commands/edit-image.md", old)
        self.assertEqual(len(found), 1)
        self.assertIn("commands/edit-image.md", found[0])

    def test_plant_the_1_29_2_generate_all_is_flagged(self):
        """It had a Step 0 quote, but not the standard section: no 'Quote, then go' heading, no `Type "go"`, no 'anything else cancels'."""
        old = ("---\ndescription: Generate creative\n---\n# Generate All\n\n## Step 0 \u2014 Price the run and get a go (required)\n\n"
               "```bash\npython \"${CLAUDE_PLUGIN_ROOT}/scripts/price_book.py\" --action quote-batch --items @/tmp/run-plan.json\n```\n\n"
               "- A clean quote still returns `approved_to_run: false`. Show the user the total and wait for an explicit go.\n\n"
               "## Process\n2. For each post:\n   - Generate image(s) via image-compositor agent\n")
        found = self.planted("commands/generate-all.md", old)
        self.assertEqual(len(found), 1)
        self.assertIn("commands/generate-all.md", found[0])

    def test_plant_the_two_commands_that_regenerated_with_no_quote_are_flagged(self):
        reactive = "---\ndescription: React\n---\n# Reactive Post\n\n## Process\n5. Generate creative using STYLE_REFERENCED or PURE_CREATIVE mode\n"
        revision = "---\ndescription: Revise\n---\n# Revision\n\n## Process\n4. Re-run affected pipeline steps\n"
        for rel, text in (("commands/reactive-post.md", reactive), ("commands/revision.md", revision)):
            with self.subTest(file=rel):
                self.assertEqual(len(self.planted(rel, text)), 1)

    def test_plant_a_hand_off_must_name_the_file_and_say_it_quotes(self):
        named = "# R\n\n## Process\n5. Generate the creative with `/socialforge:compose-creative`, which quotes first.\n"
        self.assertEqual(self.planted("commands/reactive-post.md", named), [])
        no_quote_word = "# R\n\n## Process\n5. Generate the creative with `/socialforge:compose-creative`.\n"
        self.assertEqual(len(self.planted("commands/reactive-post.md", no_quote_word)), 1)
        unnamed = "# R\n\n## Process\n5. Generate the creative. The user is told the price first.\n"
        self.assertEqual(len(self.planted("commands/reactive-post.md", unnamed)), 1)

    def test_plant_a_quote_section_missing_a_required_part_is_flagged(self):
        broken = self.CARRIER.replace('Type "go" to generate.', "Generating now.")
        found = self.problems({"skills/compose-creative/SKILL.md": broken}, exempt={}, ordered={"skills/compose-creative/SKILL.md"})
        self.assertEqual(len(found), 1)
        self.assertIn('"go"', found[0])
        self.assertEqual(self.problems({"skills/compose-creative/SKILL.md": self.CARRIER}, exempt={}, ordered=set())[0].split(":")[0],
                         "skills/compose-creative/SKILL.md")


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
