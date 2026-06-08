"""SocialForge OpenClaw native manifest tests."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = PLUGIN_ROOT / "openclaw.plugin.json"


class TestOpenClawManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_exists(self):
        self.assertTrue(MANIFEST.exists())

    def test_id_required(self):
        self.assertEqual(self.data["id"], "socialforge")

    def test_id_is_kebab_case(self):
        self.assertRegex(self.data["id"], r"^[a-z][a-z0-9-]*[a-z0-9]$")

    def test_id_matches_claude_plugin_name(self):
        cp = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(self.data["id"], cp["name"])

    def test_configSchema_required(self):
        s = self.data["configSchema"]
        self.assertEqual(s["type"], "object")
        self.assertEqual(s["additionalProperties"], False)
        self.assertIn("properties", s)

    def test_skills_points_at_dir(self):
        self.assertEqual(self.data["skills"], ["./skills"])
        skills_dir = PLUGIN_ROOT / "skills"
        self.assertTrue(skills_dir.exists())

    def test_version_matches_canonical(self):
        cp = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(self.data["version"], cp["version"])

    def test_no_unexpected_top_level_fields(self):
        allowed = {"id", "configSchema", "name", "description", "version",
                   "kind", "channels", "providers", "skills",
                   "enabledByDefault", "requiresPlugins",
                   "activation", "setup", "contracts", "uiHints",
                   "modelCatalog", "channelConfigs"}
        self.assertEqual(set(self.data.keys()) - allowed, set())


class TestVersionConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canonical = json.loads(
            (PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )["version"]

    def test_all_json_manifests_match(self):
        manifests = [
            PLUGIN_ROOT / ".claude-plugin" / "plugin.json",
            PLUGIN_ROOT / ".codex-plugin" / "plugin.json",
            PLUGIN_ROOT / ".cursor-plugin" / "plugin.json",
            PLUGIN_ROOT / ".github" / "plugin" / "plugin.json",
            PLUGIN_ROOT / "gemini-extension.json",
            PLUGIN_ROOT / "openclaw.plugin.json",
        ]
        out = []
        for m in manifests:
            v = json.loads(m.read_text(encoding="utf-8"))["version"]
            if v != self.canonical:
                out.append(f"{m.name}={v}")
        self.assertEqual(out, [], f"Out of sync: {out}")

    def test_plugin_yaml_matches(self):
        text = (PLUGIN_ROOT / "plugin.yaml").read_text(encoding="utf-8")
        m = re.search(r"^version:\s*(.+)$", text, re.MULTILINE)
        self.assertEqual(m.group(1).strip(), self.canonical)

    def test_init_py_PLUGIN_VERSION_matches(self):
        text = (PLUGIN_ROOT / "__init__.py").read_text(encoding="utf-8")
        m = re.search(r'PLUGIN_VERSION\s*=\s*["\'](.*?)["\']', text)
        self.assertEqual(m.group(1), self.canonical)


if __name__ == "__main__":
    unittest.main()
