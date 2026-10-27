"""A retired model's replacement can depend on the service a request goes to.

veo-3.1-generate-preview was shut down on the Gemini API on 2026-10-22. Its replacement there is
gemini-omni-1.1-flash; on Vertex AI it is veo-3.1-generate-001, which the Gemini API does not serve. The registry carried
one replacement_id, so resolve_model forwarded a Gemini API caller to a Vertex-only id and the request failed.

The canonical registry now gives such an entry a replacement_by_backend map. resolve_model takes --backend (backend= in
Python): an entry with a map forwards only to the named backend's id; with no listed backend a retired or deprecated id
is refused (BackendRequired, exit 2), naming every replacement. An entry without a map behaves as before.
Digital Marketing Pro owns the canonical resolve_model.py; this is the same behaviour in this plugin's copy.
Everything here runs against throwaway registries and HOME/USERPROFILE in a temp folder.
"""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import resolve_model  # noqa: E402

MAP = {"gemini-api": "gemini-omni-1.1-flash", "vertex": "veo-3.1-generate-001"}


def registry() -> dict:
    models = [
        {"id": "veo-3.1-generate-preview", "vendor": "google", "status": "retired", "shutdown_date": "2026-10-22",
         "replacement_id": "veo-3.1-generate-001", "replacement_by_backend": dict(MAP)},
        {"id": "veo-3.1-generate-001", "vendor": "google", "status": "current"},
        {"id": "gemini-omni-1.1-flash", "vendor": "google", "status": "current"},
        {"id": "old-split", "vendor": "x", "status": "deprecated", "replacement_id": "veo-3.1-generate-001",
         "replacement_by_backend": dict(MAP)},
        {"id": "old-plain", "vendor": "x", "status": "retired", "replacement_id": "new-plain"},
        {"id": "new-plain", "vendor": "x", "status": "current"},
    ]
    return {"last_updated": "2026-10-27", "models": models,
            "aliases": {"latest-video-google": "veo-3.1-generate-001", "stale-video": "veo-3.1-generate-preview"}}


class RegistryCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        path = Path(self._tmp.name) / "model_registry.json"
        path.write_text(json.dumps(registry()), encoding="utf-8")
        self._saved = os.environ.get("MODEL_REGISTRY")
        os.environ["MODEL_REGISTRY"] = str(path)
        self.rm = importlib.reload(resolve_model)
        self.rm.get_registry(force_reload=True)
        self.path = path

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("MODEL_REGISTRY", None)
        else:
            os.environ["MODEL_REGISTRY"] = self._saved
        self._tmp.cleanup()
        importlib.reload(resolve_model).get_registry(force_reload=True)


class TestResolveWithABackend(RegistryCase):

    def test_each_backend_gets_its_own_replacement(self):
        self.assertEqual(self.rm.resolve("veo-3.1-generate-preview", backend="gemini-api"), "gemini-omni-1.1-flash")
        self.assertEqual(self.rm.resolve("veo-3.1-generate-preview", backend="vertex"), "veo-3.1-generate-001")

    def test_no_backend_is_refused_and_names_both(self):
        with self.assertRaises(self.rm.BackendRequired) as ctx:
            self.rm.resolve("veo-3.1-generate-preview")
        message = str(ctx.exception)
        self.assertIn("gemini-omni-1.1-flash (gemini-api)", message)
        self.assertIn("veo-3.1-generate-001 (vertex)", message)
        self.assertIn("--backend", message)

    def test_an_unlisted_backend_is_refused_too(self):
        with self.assertRaises(self.rm.BackendRequired) as ctx:
            self.rm.resolve("veo-3.1-generate-preview", backend="bedrock")
        self.assertIn("no replacement for bedrock", str(ctx.exception))

    def test_a_deprecated_entry_with_a_map_is_refused_unless_deprecated_is_allowed(self):
        with self.assertRaises(self.rm.BackendRequired):
            self.rm.resolve("old-split")
        self.assertEqual(self.rm.resolve("old-split", backend="vertex"), "veo-3.1-generate-001")
        self.assertEqual(self.rm.resolve("old-split", allow_deprecated=True), "old-split")

    def test_an_entry_without_a_map_ignores_the_backend(self):
        self.assertEqual(self.rm.resolve("old-plain"), "new-plain")
        self.assertEqual(self.rm.resolve("old-plain", backend="vertex"), "new-plain")

    def test_current_ids_and_aliases_are_untouched(self):
        self.assertEqual(self.rm.resolve("latest-video-google"), "veo-3.1-generate-001")
        self.assertEqual(self.rm.resolve("veo-3.1-generate-001", backend="gemini-api"), "veo-3.1-generate-001")

    def test_check_reports_the_replacement_for_the_backend(self):
        self.assertEqual(self.rm.check("veo-3.1-generate-preview", "gemini-api"), ("retired", "gemini-omni-1.1-flash"))
        self.assertEqual(self.rm.check("veo-3.1-generate-preview", "vertex"), ("retired", "veo-3.1-generate-001"))
        # with no backend named, check keeps reporting the default (replacement_id) for readers of one id
        self.assertEqual(self.rm.check("veo-3.1-generate-preview"), ("retired", "veo-3.1-generate-001"))


class TestTheCommandLine(RegistryCase):

    def run_cli(self, *args):
        env = dict(os.environ, MODEL_REGISTRY=str(self.path), HOME=self._tmp.name, USERPROFILE=self._tmp.name)
        return subprocess.run([sys.executable, str(SCRIPTS / "resolve_model.py"), *args],
                              capture_output=True, text=True, env=env, timeout=60)

    def test_backend_picks_the_replacement(self):
        out = self.run_cli("--alias", "veo-3.1-generate-preview", "--backend", "gemini-api")
        self.assertEqual((out.returncode, out.stdout.strip()), (0, "gemini-omni-1.1-flash"))

    def test_no_backend_exits_two_and_names_both_replacements(self):
        out = self.run_cli("--alias", "veo-3.1-generate-preview")
        self.assertEqual(out.returncode, 2, out.stdout + out.stderr)
        self.assertIn("gemini-omni-1.1-flash", out.stderr)
        self.assertIn("veo-3.1-generate-001", out.stderr)
        self.assertEqual(out.stdout, "")

    def test_a_deprecated_split_id_is_refused_without_a_backend(self):
        out = self.run_cli("--alias", "old-split")
        self.assertEqual(out.returncode, 2, out.stdout + out.stderr)

    def test_check_with_a_backend(self):
        out = self.run_cli("--check", "veo-3.1-generate-preview", "--backend", "vertex", "--json")
        self.assertEqual(json.loads(out.stdout)["replacement_id"], "veo-3.1-generate-001")
        self.assertEqual(out.returncode, 1)  # retired ids keep exiting 1 under --check


class TestUtf8Output(RegistryCase):
    """A registry note in a script outside Windows-1252 (an arrow, Devanagari) must print, not end in UnicodeEncodeError,
    when PYTHONUTF8 is unset and stdout is a pipe (the default for a customer on Windows)."""

    def test_list_json_prints_non_latin_notes_with_python_utf8_unset(self):
        reg = registry()
        reg["models"][1]["display_name"] = "Veo → नमस्ते 😀"
        self.path.write_text(json.dumps(reg), encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
        env.update(MODEL_REGISTRY=str(self.path), HOME=self._tmp.name, USERPROFILE=self._tmp.name)
        out = subprocess.run([sys.executable, str(SCRIPTS / "resolve_model.py"), "--list", "--json"],
                             capture_output=True, env=env, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr.decode("utf-8", "replace"))
        self.assertIn("नमस्ते", out.stdout.decode("utf-8"))


class TestTheShippedRegistry(unittest.TestCase):
    """The mirrored registry carries the split, so the behaviour above reaches real callers."""

    def test_the_shipped_veo_preview_entry_has_both_replacements(self):
        reg = json.loads((SCRIPTS / "model_registry.json").read_text(encoding="utf-8-sig"))
        entry = next(m for m in reg["models"] if m["id"] == "veo-3.1-generate-preview")
        self.assertEqual(entry["replacement_by_backend"], MAP)
        self.assertEqual(entry["replacement_id"], MAP["vertex"])


if __name__ == "__main__":
    unittest.main()
