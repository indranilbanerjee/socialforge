"""Release-consistency tests — catches cross-manifest drift before it ships.

These tests fail when:
- The 7 platform manifests (5 Claude-family + Hermes + OpenClaw) get out of version sync
- The README version badge falls behind plugin.json
- The CHANGELOG's latest entry doesn't match the current plugin version
- The test-count badge in the README is stale
- A native platform's install command goes missing from the README
- A README internal anchor link points at a non-existent heading
- Critical README sections (Supported surfaces, Quick Start, Installation,
  Architecture, Current Release) go missing
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
README = PLUGIN_ROOT / "README.md"
CHANGELOG = PLUGIN_ROOT / "CHANGELOG.md"

PLATFORM_MANIFESTS_JSON = [
    PLUGIN_ROOT / ".claude-plugin" / "plugin.json",
    PLUGIN_ROOT / ".codex-plugin" / "plugin.json",
    PLUGIN_ROOT / ".cursor-plugin" / "plugin.json",
    PLUGIN_ROOT / ".github" / "plugin" / "plugin.json",
    PLUGIN_ROOT / "gemini-extension.json",
    PLUGIN_ROOT / "openclaw.plugin.json",
]
PLUGIN_YAML = PLUGIN_ROOT / "plugin.yaml"
HERMES_ADAPTER_PY = PLUGIN_ROOT / "__init__.py"


def _canonical_version() -> str:
    """The one true version: from .claude-plugin/plugin.json."""
    data = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    return data["version"]


def _read_yaml_field(yaml_text: str, key: str) -> str | None:
    m = re.search(rf"^{key}:\s*>-\s*\n((?:\s+\S.*\n)+)", yaml_text, re.MULTILINE)
    if m:
        return " ".join(line.strip() for line in m.group(1).splitlines() if line.strip())
    m = re.search(rf'^{key}:\s*["\']?(.*?)["\']?\s*$', yaml_text, re.MULTILINE)
    if m:
        return m.group(1).strip().rstrip('"\'')
    return None


class TestVersionConsistency(unittest.TestCase):
    """Every manifest + adapter + README badge must declare the same version."""

    @classmethod
    def setUpClass(cls):
        cls.canonical = _canonical_version()

    def test_all_json_manifests_match_canonical_version(self):
        mismatched = []
        for manifest_path in PLATFORM_MANIFESTS_JSON:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            version = data.get("version")
            if version != self.canonical:
                mismatched.append(f"{manifest_path.name}: {version}")
        self.assertEqual(mismatched, [],
                         f"Canonical version is {self.canonical}. "
                         f"Out-of-sync manifests: {mismatched}")

    def test_hermes_plugin_yaml_matches_canonical_version(self):
        yaml_version = _read_yaml_field(PLUGIN_YAML.read_text(encoding="utf-8"), "version")
        self.assertEqual(yaml_version, self.canonical,
                         f"plugin.yaml v={yaml_version} != canonical v={self.canonical}")

    def test_hermes_adapter_PLUGIN_VERSION_matches_canonical(self):
        text = HERMES_ADAPTER_PY.read_text(encoding="utf-8")
        m = re.search(r'PLUGIN_VERSION\s*=\s*["\'](.*?)["\']', text)
        self.assertIsNotNone(m, "PLUGIN_VERSION constant not found in __init__.py")
        self.assertEqual(m.group(1), self.canonical,
                         f"__init__.py PLUGIN_VERSION={m.group(1)} != canonical v={self.canonical}")

    def test_readme_version_badge_matches_canonical(self):
        text = README.read_text(encoding="utf-8")
        m = re.search(r"badge/version-(\d+\.\d+\.\d+)-blue", text)
        self.assertIsNotNone(m, "Version badge not found in README")
        self.assertEqual(m.group(1), self.canonical,
                         f"README badge version={m.group(1)} != canonical v={self.canonical}")

    def test_readme_supported_surfaces_section_mentions_canonical(self):
        text = README.read_text(encoding="utf-8")
        # SF README uses "## Supported surfaces (v1.12.0)" pattern — keeps the section
        # title in lock-step with the canonical version.
        m = re.search(r"## Supported surfaces \(v(\d+\.\d+\.\d+)\)", text)
        self.assertIsNotNone(m, "'## Supported surfaces (vX.Y.Z)' section heading not found")
        self.assertEqual(m.group(1), self.canonical,
                         f"Supported-surfaces heading says v{m.group(1)} but canonical is {self.canonical}")

    def test_readme_current_release_section_mentions_canonical(self):
        text = README.read_text(encoding="utf-8")
        # SF README uses "## Current Release (vX.Y.Z)" pattern.
        m = re.search(r"## Current Release \(v(\d+\.\d+\.\d+)\)", text)
        self.assertIsNotNone(m, "'## Current Release (vX.Y.Z)' section heading not found")
        self.assertEqual(m.group(1), self.canonical,
                         f"Current-Release heading says v{m.group(1)} but canonical is {self.canonical}")

    def test_readme_recent_release_callout_mentions_canonical_version(self):
        text = README.read_text(encoding="utf-8")
        m = re.search(r"Just shipped — v(\d+\.\d+\.\d+)", text)
        self.assertIsNotNone(m, "'Just shipped' callout not found in README hero")
        self.assertEqual(m.group(1), self.canonical,
                         f"Recent-release callout mentions v{m.group(1)} but canonical is {self.canonical}")

    def test_changelog_latest_entry_matches_canonical(self):
        text = CHANGELOG.read_text(encoding="utf-8")
        m = re.search(r"^##\s*\[(\d+\.\d+\.\d+)\]", text, re.MULTILINE)
        self.assertIsNotNone(m, "No version header found in CHANGELOG")
        self.assertEqual(m.group(1), self.canonical,
                         f"CHANGELOG latest entry is v{m.group(1)} but canonical is {self.canonical}")


class TestDescriptionConsistency(unittest.TestCase):
    """The 5 Claude-family manifests should share their short description verbatim."""

    @classmethod
    def setUpClass(cls):
        cls.descriptions = {}
        for manifest_path in PLATFORM_MANIFESTS_JSON:
            # Skip OpenClaw — its description is intentionally longer.
            if manifest_path.name == "openclaw.plugin.json":
                continue
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            cls.descriptions[manifest_path.name] = data.get("description", "")

    def test_all_claude_family_manifests_share_description(self):
        unique_descriptions = set(self.descriptions.values())
        self.assertEqual(
            len(unique_descriptions), 1,
            f"Description drift across Claude-family manifests:\n" +
            "\n".join(f"  {name}: {desc[:60]}..."
                      for name, desc in self.descriptions.items())
        )

    def test_description_mentions_canonical_skill_count(self):
        # The SF description string should contain "16 skills" — keep it true.
        actual_skill_count = sum(
            1 for d in (PLUGIN_ROOT / "skills").iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        )
        for name, desc in self.descriptions.items():
            self.assertIn(
                f"{actual_skill_count} skills", desc,
                f"{name} description should mention '{actual_skill_count} skills'; got: {desc[:100]}",
            )


class TestReadmeBadgeAccuracy(unittest.TestCase):
    """README badges must reflect the actual state of the repo."""

    @classmethod
    def setUpClass(cls):
        cls.text = README.read_text(encoding="utf-8")

    def test_test_count_badge_matches_actual(self):
        # Count actual test methods across all test_*.py files
        total = 0
        for f in PLUGIN_ROOT.glob("tests/test_*.py"):
            for line in f.read_text(encoding="utf-8").splitlines():
                if re.match(r"^\s*def test_", line):
                    total += 1
        m = re.search(r"tests-(\d+)%2F\d+", self.text)
        self.assertIsNotNone(m, "Test count badge not found")
        badge_count = int(m.group(1))
        self.assertEqual(
            badge_count, total,
            f"README test badge says {badge_count}/{badge_count} but repo has {total} test methods. "
            "Bump the badge."
        )


class TestInstallCommandCoverage(unittest.TestCase):
    """Every native platform listed in 'Supported surfaces' must have an install command in the README."""

    @classmethod
    def setUpClass(cls):
        cls.text = README.read_text(encoding="utf-8")

    def test_claude_code_install_command_present(self):
        self.assertIn("/plugin install socialforge@neels-plugins", self.text)

    def test_codex_install_command_present(self):
        self.assertIn("codex plugin install socialforge", self.text)

    def test_cursor_install_command_present(self):
        self.assertIn("/add-plugin socialforge", self.text)

    def test_copilot_install_command_present(self):
        self.assertIn("copilot plugin install socialforge", self.text)

    def test_antigravity_install_command_present(self):
        self.assertIn("agy plugin install", self.text)

    def test_hermes_install_command_present(self):
        self.assertIn("hermes plugins install indranilbanerjee/socialforge", self.text)

    def test_openclaw_install_command_present(self):
        self.assertIn(
            "openclaw plugins install git:github.com/indranilbanerjee/socialforge",
            self.text,
        )


class TestCriticalReadmeSections(unittest.TestCase):
    """The high-traffic sections must exist by their canonical names."""

    @classmethod
    def setUpClass(cls):
        cls.text = README.read_text(encoding="utf-8")

    def test_core_principle_section(self):
        self.assertIn("## Core Principle", self.text)

    def test_four_creative_modes_section(self):
        self.assertIn("## The Four Creative Modes", self.text)

    def test_quick_start_section(self):
        self.assertIn("## Quick Start", self.text)

    def test_supported_surfaces_section(self):
        self.assertIn("## Supported surfaces", self.text)

    def test_architecture_section(self):
        self.assertIn("## Architecture", self.text)

    def test_installation_section(self):
        self.assertIn("## Installation", self.text)

    def test_first_time_setup_section(self):
        self.assertIn("## First-Time Setup", self.text)

    def test_video_generation_section(self):
        self.assertIn("## Video Generation", self.text)

    def test_connectors_section(self):
        self.assertIn("## Connectors", self.text)

    def test_storage_section(self):
        self.assertIn("## Storage", self.text)

    def test_current_release_section(self):
        self.assertIn("## Current Release", self.text)

    def test_eight_native_platforms_mentioned(self):
        # Each native platform should appear by name somewhere in the README.
        for platform in ("Claude Code", "Cowork", "Codex", "Cursor",
                         "Copilot CLI", "Antigravity", "Hermes", "OpenClaw"):
            self.assertIn(platform, self.text,
                          f"README missing '{platform}' coverage")


class TestReadmeAnchorIntegrity(unittest.TestCase):
    """Every internal anchor link in the README must resolve to a heading."""

    def test_all_internal_anchors_resolve(self):
        text = README.read_text(encoding="utf-8")
        refs = set(re.findall(r"\]\(#([a-z0-9-]+)\)", text))
        headings = re.findall(r"^#{1,3}\s+(.+)$", text, re.MULTILINE)

        def slugify(h: str) -> str:
            return re.sub(r"[^a-z0-9 -]", "", h.lower()).strip().replace(" ", "-")

        heading_slugs = {slugify(h) for h in headings}
        missing = refs - heading_slugs
        self.assertEqual(missing, set(),
                         f"Broken internal anchors: {missing}")


if __name__ == "__main__":
    unittest.main()
