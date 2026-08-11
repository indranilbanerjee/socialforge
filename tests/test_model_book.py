"""No model id may be written into the execution path.

A model string in source is a claim about the day it was written, shipped to
someone running it much later. This plugin had six of them. One video fallback
stayed pinned to a superseded generation for roughly six months and nothing in
the system could say so — and a retired id does not degrade gracefully, it fails
at the moment the two providers ahead of it have already failed.

So the code asks for a *kind* of model and something that looked recently
answers. These tests pin that: the ladder is live-discovery, then the shipped
registry with an explicit age warning, then refusal. Never a literal.

Stdlib only.
"""
from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

SRC = "https://wavespeed.ai/models"

# Every script that can call a generation API.
EXECUTION_PATH = ["generate_image.py", "generate_video.py", "edit_image.py"]

# Shapes that identify a specific model version rather than a capability.
MODEL_LITERAL = re.compile(
    r'"('
    r'kwaivgi/[^"]+'          # kwaivgi/kling-v3.0-pro/image-to-video
    r'|higgsfield/[^"]+'      # higgsfield/soul-v2/text-to-image
    r'|kling-video/v[\d.]+[^"]*'
    r'|gemini-[\d][^"]*'      # gemini-3.1-flash-image
    r'|veo-[\d][^"]*'         # veo-3.1-generate-preview
    r')"')


class TestNoHardcodedModelsInCode(unittest.TestCase):
    def test_execution_scripts_contain_no_model_literals(self):
        for name in EXECUTION_PATH:
            src = (SCRIPTS / name).read_text(encoding="utf-8")
            code = "\n".join(line.split("#")[0] for line in src.splitlines()
                             if not line.strip().startswith("#"))
            code = re.sub(r'"""..*?"""', "", code, flags=re.S)
            with self.subTest(script=name):
                found = MODEL_LITERAL.findall(code)
                self.assertEqual(
                    found, [],
                    f"{name} names specific models: {found}. Ask model_book for a "
                    f"kind instead — a literal here outlives the model.")

    def test_defaults_are_none_not_strings(self):
        """The `except ImportError` rung must not reintroduce a literal."""
        for name, var in [("generate_image.py", "DEFAULT_MODEL"),
                          ("generate_video.py", "DEFAULT_KLING_MODEL"),
                          ("generate_video.py", "DEFAULT_VEO_MODEL"),
                          ("edit_image.py", "DEFAULT_MODEL")]:
            src = (SCRIPTS / name).read_text(encoding="utf-8")
            with self.subTest(script=name, var=var):
                self.assertRegex(
                    src, rf"{var}\s*=\s*None",
                    f"{name}: {var} has no None fallback — a literal has crept back")

    def test_model_book_itself_ships_no_model_ids(self):
        src = (SCRIPTS / "model_book.py").read_text(encoding="utf-8")
        header = src.split("def record")[0]
        self.assertEqual(MODEL_LITERAL.findall(header), [],
                         "model_book seeded a model id — it must hold none")


class ModelBookCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["CLAUDE_PLUGIN_DATA_DIR"] = self._tmp.name
        import model_book
        self.mb = importlib.reload(model_book)
        self.assertIn(self._tmp.name, str(self.mb.MODEL_BOOK))

    def tearDown(self):
        os.environ.pop("CLAUDE_PLUGIN_DATA_DIR", None)
        self._tmp.cleanup()

    def _age(self, kind, provider, days):
        book = json.loads(self.mb.MODEL_BOOK.read_text(encoding="utf-8"))
        old = datetime.now(timezone.utc) - timedelta(days=days)
        book["entries"][self.mb._key(kind, provider)]["discovered_at"] = old.isoformat()
        self.mb.MODEL_BOOK.write_text(json.dumps(book), encoding="utf-8")


class TestProvenance(ModelBookCase):
    def test_record_requires_a_source_url(self):
        for bad in ("", "the docs", "i remember", "wavespeed.ai"):
            with self.subTest(source=bad):
                with self.assertRaises(ValueError):
                    self.mb.record("image.text-to-image", "wavespeed", "some/model", bad)

    def test_record_rejects_an_unknown_kind(self):
        with self.assertRaises(ValueError):
            self.mb.record("image.make-it-pop", "wavespeed", "some/model", SRC)

    def test_record_requires_a_model_id(self):
        with self.assertRaises(ValueError):
            self.mb.record("image.text-to-image", "wavespeed", "  ", SRC)

    def test_recorded_model_resolves(self):
        self.mb.record("image.text-to-image", "wavespeed", "vendor/model/task", SRC)
        got = self.mb.resolve("image.text-to-image", "wavespeed")
        self.assertEqual(got["status"], "ok")
        self.assertEqual(got["model_id"], "vendor/model/task")
        self.assertEqual(got["source"], SRC)


class TestRefusal(ModelBookCase):
    def test_unknown_kind_provider_refuses_and_says_where_to_look(self):
        got = self.mb.resolve("video.image-to-video", "higgsfield")
        self.assertEqual(got["status"], "unknown")
        self.assertIn("discovery_url", got)
        self.assertNotIn("model_id", got, "a refusal leaked a model id")

    def test_stale_discovery_stops_resolving(self):
        self.mb.record("video.image-to-video", "wavespeed", "vendor/v1/task", SRC)
        self._age("video.image-to-video", "wavespeed", 30)
        got = self.mb.resolve("video.image-to-video", "wavespeed")
        self.assertEqual(got["status"], "stale")
        self.assertIn("superseded", got["action_required"])

    def test_kie_carries_its_fetch_restriction(self):
        self.assertIn("403", self.mb.DISCOVERY["kie"]["note"])


class TestExecutionLadder(ModelBookCase):
    def test_live_discovery_wins(self):
        self.mb.record("image.text-to-image", "wavespeed", "vendor/current/task", SRC)
        got = self.mb.resolve_for_execution("image.text-to-image", "wavespeed",
                                            "latest-image-wavespeed")
        self.assertEqual(got["basis"], "live-discovery")
        self.assertEqual(got["model_id"], "vendor/current/task")
        self.assertNotIn("warning", got)

    def test_unresolved_returns_no_model_and_says_what_to_do(self):
        got = self.mb.resolve_for_execution("image.character-consistency", "higgsfield")
        self.assertIsNone(got["model_id"])
        self.assertEqual(got["basis"], "unresolved")
        self.assertIn("Refusing to fall back", got["action_required"])

    def test_registry_rung_always_warns_when_it_is_used(self):
        """The shipped registry may answer, but never silently — it is a file
        with a release date, not a lookup."""
        got = self.mb.resolve_for_execution("image.text-to-image", "vertex",
                                            "latest-image-balanced-google")
        if got["basis"] == "shipped-registry":
            self.assertIn("warning", got)
            self.assertIn("record the current model", got["warning"])
        else:
            self.assertEqual(got["basis"], "unresolved")

    def test_stale_discovery_is_reported_alongside_the_fallback(self):
        self.mb.record("video.text-to-video", "wavespeed", "vendor/old/task", SRC)
        self._age("video.text-to-video", "wavespeed", 30)
        got = self.mb.resolve_for_execution("video.text-to-video", "wavespeed")
        self.assertIn("stale_discovery", got)
        self.assertEqual(got["stale_discovery"]["model_id"], "vendor/old/task")


class TestKindsAreCapabilities(ModelBookCase):
    def test_kinds_name_capabilities_not_products(self):
        """A kind outlives every model that satisfies it. If a vendor or version
        appears here, the abstraction has leaked."""
        for kind in self.mb.KINDS:
            with self.subTest(kind=kind):
                self.assertNotRegex(kind, r"kling|veo|gemini|soul|nano|seedance|flux",
                                    f"{kind} names a product, not a capability")
                self.assertRegex(kind, r"^(image|video)\.[a-z-]+$")

    def test_every_wired_capability_has_a_kind(self):
        for required in ("image.text-to-image", "image.edit",
                         "video.image-to-video", "video.text-to-video"):
            self.assertIn(required, self.mb.KINDS)

    def test_staleness_reports_kinds_with_no_model(self):
        rep = self.mb.staleness_report()
        self.assertIn("image.edit", rep["kinds_with_no_model"])
        self.mb.record("image.edit", "vertex", "vendor/edit/task", SRC)
        self.assertNotIn("image.edit", self.mb.staleness_report()["kinds_with_no_model"])


class TestCli(ModelBookCase):
    def _run(self, *args):
        env = dict(os.environ, CLAUDE_PLUGIN_DATA_DIR=self._tmp.name)
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "model_book.py"), *args],
            capture_output=True, text=True, env=env)

    def test_unresolved_exits_nonzero(self):
        """A caller must not be able to proceed on an unresolved model."""
        r = self._run("--action", "resolve", "--kind", "video.text-to-video",
                      "--provider", "wavespeed")
        self.assertEqual(r.returncode, 3)

    def test_resolved_exits_zero(self):
        self.mb.record("video.text-to-video", "wavespeed", "vendor/v/task", SRC)
        r = self._run("--action", "resolve", "--kind", "video.text-to-video",
                      "--provider", "wavespeed")
        self.assertEqual(r.returncode, 0)

    def test_kinds_and_discovery_are_listable(self):
        for action in ("kinds", "discovery"):
            with self.subTest(action=action):
                r = self._run("--action", action)
                self.assertEqual(r.returncode, 0)
                self.assertTrue(json.loads(r.stdout))


if __name__ == "__main__":
    unittest.main()
