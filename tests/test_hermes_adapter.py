"""SocialForge Hermes Agent adapter tests."""
from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_YAML = PLUGIN_ROOT / "plugin.yaml"
ADAPTER_PY = PLUGIN_ROOT / "__init__.py"


def _read_yaml_field(yaml_text: str, key: str) -> str | None:
    m = re.search(rf"^{key}:\s*>-\s*\n((?:\s+\S.*\n)+)", yaml_text, re.MULTILINE)
    if m:
        return " ".join(line.strip() for line in m.group(1).splitlines() if line.strip())
    m = re.search(rf'^{key}:\s*["\']?(.*?)["\']?\s*$', yaml_text, re.MULTILINE)
    if m:
        return m.group(1).strip().rstrip('"\'')
    return None


class TestHermesPluginYaml(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.yaml_text = PLUGIN_YAML.read_text(encoding="utf-8")

    def test_plugin_yaml_exists(self):
        self.assertTrue(PLUGIN_YAML.exists())

    def test_required_name(self):
        self.assertEqual(_read_yaml_field(self.yaml_text, "name"), "socialforge")

    def test_required_version_semver(self):
        v = _read_yaml_field(self.yaml_text, "version")
        self.assertRegex(v, r"^\d+\.\d+\.\d+$")

    def test_required_description(self):
        d = _read_yaml_field(self.yaml_text, "description")
        self.assertGreater(len(d), 30)

    def test_zero_hooks_policy(self):
        m = re.search(r"^provides_hooks:\s*\[(.*?)\]", self.yaml_text, re.MULTILINE)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).strip(), "")

    def test_requires_env_empty(self):
        m = re.search(r"^requires_env:\s*\[(.*?)\]", self.yaml_text, re.MULTILINE)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).strip(), "")


class TestHermesAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("sf_hermes_adapter", ADAPTER_PY)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_register_function_exists(self):
        self.assertTrue(callable(getattr(self.module, "register", None)))

    def test_audit_works(self):
        result = self.module.audit()
        self.assertIn("skill_count", result)
        self.assertGreater(result["skill_count"], 10)

    def test_register_against_mock_ctx(self):
        registered = []
        class Ctx:
            def register_skill(self, name, path): registered.append((name, str(path)))
        self.module.register(Ctx())
        self.assertGreater(len(registered), 10)

    def test_register_degrades_on_bad_ctx(self):
        class BadCtx: pass
        try:
            self.module.register(BadCtx())
        except Exception as e:
            self.fail(f"register() must not raise on bad ctx; raised: {e}")

    def test_register_with_None_ctx(self):
        try:
            self.module.register(None)
        except Exception as e:
            self.fail(f"register(None) must not raise; raised: {e}")

    def test_version_matches_yaml(self):
        yaml_text = PLUGIN_YAML.read_text(encoding="utf-8")
        yaml_version = _read_yaml_field(yaml_text, "version")
        self.assertEqual(self.module.PLUGIN_VERSION, yaml_version)


if __name__ == "__main__":
    unittest.main()
