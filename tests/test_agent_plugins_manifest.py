"""Agent Plugins 1.0 root manifest: closed schema, version-synced, skills-shaped.

OpenAI's Agent Plugins standard (2026-08-06; ChatGPT, Codex, Cursor, GitHub
Copilot, VS Code, Kiro) reads a root plugin.json with a closed schema. Two
manifests must carry one version or the directories serve different plugins
under the same name. ${PLUGIN_DATA} is the standard's data-dir name; hosts
outside Claude set only that one. Stdlib only.
"""
import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class TestRootManifest(unittest.TestCase):
    def setUp(self):
        self.m = json.loads((REPO / "plugin.json").read_text(encoding="utf-8"))

    def test_schema_and_name(self):
        self.assertEqual(self.m["$schema"],
                         "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json")
        self.assertEqual(self.m["name"], "socialforge")

    def test_version_matches_claude_manifest(self):
        claude = json.loads((REPO / ".claude-plugin" / "plugin.json")
                            .read_text(encoding="utf-8"))
        self.assertEqual(self.m["version"], claude["version"])

    def test_closed_schema(self):
        allowed = {"$schema", "name", "version", "description", "author", "extensions"}
        self.assertLessEqual(set(self.m), allowed, set(self.m) - allowed)

    def test_name_rules(self):
        self.assertRegex(self.m["name"], r"^[a-z0-9][a-z0-9.-]{0,62}[a-z0-9]$")
        self.assertNotRegex(self.m["name"], r"[.-]{2}")

    def test_skills_are_first_level_skill_md_dirs(self):
        for d in (REPO / "skills").iterdir():
            if d.is_dir():
                self.assertTrue((d / "SKILL.md").is_file(),
                                f"skills/{d.name}/ has no SKILL.md")

    def test_plugin_data_fallback_present_in_resolvers(self):
        """A host setting only PLUGIN_DATA must resolve a data dir."""
        hits = 0
        for p in (REPO / "scripts").glob("*.py"):
            t = p.read_text(encoding="utf-8")
            if 'os.environ.get("CLAUDE_PLUGIN_DATA")' in t or 'CLAUDE_PLUGIN_DATA", "")' in t:
                self.assertIn('os.environ.get("PLUGIN_DATA")', t,
                              f"{p.name} reads CLAUDE_PLUGIN_DATA without the "
                              f"standard-name fallback")
                hits += 1
        self.assertGreater(hits, 0, "no resolver found — test is vacuous")


if __name__ == "__main__":
    unittest.main(verbosity=2)
