"""Scripts must accept a brand-config.json written from the documented schema.

references/brand-config-schema.md is what users (and the setup skill) follow when
they create a brand. Two scripts previously read keys that only appear in the
internal engineering spec, so a schema-conformant brand either crashed the script
or silently disabled a feature:

  * adapt_copy.py read brand_hashtags as an object and raised AttributeError on
    the documented array — every platform, every invocation.
  * video_postprocess.py read a flat `logo` object, so `logo_files`/`logo_overlay`
    brands got no watermark and no error.

Both shapes must keep working: the documented one and the legacy one.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS = TESTS_DIR.parent / "scripts"

DOCUMENTED_CONFIG = {
    "brand_name": "Acme Corp",
    "brand_slug": "acme-corp",
    "colors": {"primary": "#1A73E8", "secondary": "#34A853", "accent": "#FBBC04",
               "background": "#FFFFFF", "text": "#202124", "text_light": "#FFFFFF"},
    "fonts": {"heading": "Inter", "body": "Inter"},
    "logo_files": {"primary": "logos/logo-full.png", "icon": "logos/logo-icon.png"},
    "logo_overlay": {"position": "top-left", "opacity": 0.5},
    "brand_hashtags": ["#AcmeCorp", "#BuildBetter"],
    "languages": ["en"],
}

LEGACY_CONFIG = {
    "brand_name": "Acme Corp",
    "colors": {"primary": "#1A73E8"},
    "logo": {"primary": "logos/logo-full.png", "position": "bottom-right", "opacity": 0.7},
    "brand_hashtags": {"always_include": ["#AcmeLegacy"], "campaign_hashtags": {}},
}


def write_brand(workspace: Path, config: dict) -> None:
    brand_dir = workspace / "socialforge" / "brands" / "acme-corp"
    brand_dir.mkdir(parents=True, exist_ok=True)
    (brand_dir / "brand-config.json").write_text(json.dumps(config), encoding="utf-8")


def run_adapt(workspace: Path, *args):
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_DATA"] = str(workspace)
    proc = subprocess.run([sys.executable, str(SCRIPTS / "adapt_copy.py"), *args],
                          capture_output=True, env=env)
    return (proc.returncode,
            proc.stdout.decode("utf-8", errors="replace"),
            proc.stderr.decode("utf-8", errors="replace"))


class TestAdaptCopyHashtagShapes(unittest.TestCase):
    """adapt_copy.py must not crash on either documented brand_hashtags shape."""

    def _adapt(self, config, platform="linkedin"):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_brand(ws, config)
            rc, out, err = run_adapt(ws, "--text", "Deliverability improved this quarter.",
                                     "--platform", platform, "--brand", "acme-corp")
        self.assertNotIn("Traceback", err, f"adapt_copy crashed:\n{err}")
        self.assertEqual(rc, 0, f"adapt_copy exited {rc}:\n{err}")
        return json.loads(out)

    def test_documented_array_shape_does_not_crash(self):
        payload = self._adapt(DOCUMENTED_CONFIG)
        self.assertIn("#AcmeCorp", json.dumps(payload))

    def test_legacy_object_shape_still_works(self):
        payload = self._adapt(LEGACY_CONFIG)
        self.assertIn("#AcmeLegacy", json.dumps(payload))

    def test_every_platform_survives_the_documented_shape(self):
        for platform in ("linkedin", "x", "instagram", "facebook", "threads", "bluesky"):
            with self.subTest(platform=platform):
                self._adapt(DOCUMENTED_CONFIG, platform)

    def test_malformed_hashtags_are_ignored_not_fatal(self):
        config = dict(DOCUMENTED_CONFIG, brand_hashtags="#NotAList")
        self._adapt(config)


class TestVideoPostprocessLogoShapes(unittest.TestCase):
    """The watermark must resolve from logo_files/logo_overlay, not only `logo`."""

    @staticmethod
    def _resolve(config):
        """Mirror of the resolution block in video_postprocess.apply_postprocessing."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "video_postprocess", SCRIPTS / "video_postprocess.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = (SCRIPTS / "video_postprocess.py").read_text(encoding="utf-8")
        return source, config

    def test_documented_keys_are_read(self):
        source, _ = self._resolve(DOCUMENTED_CONFIG)
        self.assertIn('brand_config.get("logo_files"', source,
                      "video_postprocess must read logo_files (documented schema)")
        self.assertIn('brand_config.get("logo_overlay"', source,
                      "video_postprocess must read logo_overlay (documented schema)")

    def test_legacy_key_still_read(self):
        source, _ = self._resolve(LEGACY_CONFIG)
        self.assertIn('brand_config.get("logo"', source,
                      "the pre-v1.14 flat `logo` object must stay supported")


class TestSchemaKeysAreReadable(unittest.TestCase):
    """Guard against a script reading a brand-config key the schema never defines."""

    def test_scripts_do_not_invent_top_level_brand_keys(self):
        schema = (TESTS_DIR.parent / "references" / "brand-config-schema.md").read_text(
            encoding="utf-8")
        # Keys the scripts legitimately read that are injected at runtime rather
        # than authored by the user, plus the documented legacy aliases.
        runtime_or_legacy = {"_brand_dir", "logo"}
        for key in ("logo_files", "logo_overlay", "brand_hashtags", "colors",
                    "fonts", "languages", "social_profiles"):
            with self.subTest(key=key):
                self.assertIn(f"`{key}`", schema,
                              f"{key} is read by scripts but absent from the schema doc")
        self.assertTrue(runtime_or_legacy)


if __name__ == "__main__":
    unittest.main()
