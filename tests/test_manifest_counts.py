"""Every manifest that states a count states the true one, and names no model.

The description guard in test_release_consistency compares only the
Claude-family descriptions, so it skipped openclaw.plugin.json, package.json,
plugin.yaml and the OpenAI interface's longDescription. Those carried
"16 skills, 25 commands" (plugin.yaml, several releases stale), "25 scripts",
and model names such as "Nano Banana Pro" and "Kling v3.0 Pro" until v1.27.0.
Models are resolved live from the registry, so a manifest must not name one.

Stdlib only.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MANIFESTS = [
    ".claude-plugin/plugin.json", ".codex-plugin/plugin.json", ".cursor-plugin/plugin.json",
    ".github/plugin/plugin.json", ".grok-plugin/plugin.json", ".grok-plugin/marketplace.json",
    "gemini-extension.json", "openclaw.plugin.json", "package.json", "plugin.json", "plugin.yaml",
]

COUNT = re.compile(r"(?<![-~<>\d.])\b(\d{1,3})\s+(skills|commands|agents|scripts)\b")
MODEL_NAMES = re.compile(
    r"Nano Banana|Kling\s*v?\d|Veo\s*\d|Imagen\s*\d|Gemini\s*\d|GPT[- ]?\d|"
    r"\b(?:Opus|Sonnet|Haiku)\s*\d|Seedream|Flux\s*\d", re.I)


def truth() -> dict[str, int]:
    return {
        "skills": sum(1 for d in (ROOT / "skills").iterdir() if (d / "SKILL.md").is_file()),
        "commands": len(list((ROOT / "commands").glob("*.md"))),
        "agents": len(list((ROOT / "agents").glob("*.md"))),
        "scripts": len(list((ROOT / "scripts").glob("*.py"))),
    }


def stale_counts(text: str, real: dict[str, int]) -> list[str]:
    return [m.group(0) for m in COUNT.finditer(text) if int(m.group(1)) != real[m.group(2)]]


class TestManifestCounts(unittest.TestCase):
    def test_every_stated_count_is_true(self):
        real = truth()
        bad = {}
        for rel in MANIFESTS:
            p = ROOT / rel
            if p.is_file() and (s := stale_counts(p.read_text(encoding="utf-8"), real)):
                bad[rel] = s
        self.assertEqual(bad, {}, f"stale counts (repo has {real}): {bad}")

    def test_no_manifest_names_a_model(self):
        bad = {rel: m.group(0) for rel in MANIFESTS
               if (ROOT / rel).is_file()
               and (m := MODEL_NAMES.search((ROOT / rel).read_text(encoding="utf-8")))}
        self.assertEqual(bad, {}, f"manifests naming a model (resolve it live instead): {bad}")

    def test_guard_can_fail(self):
        real = {"skills": 21, "commands": 18, "agents": 5, "scripts": 29}
        self.assertEqual(stale_counts("21 skills, 18 commands", real), [])
        self.assertEqual(stale_counts("16 skills, 25\n  commands", real), ["16 skills", "25\n  commands"])
        self.assertTrue(stale_counts("5 agents + 25 scripts", real))
        self.assertTrue(MODEL_NAMES.search("AI image (Vertex AI Nano Banana Pro)"))
        self.assertTrue(MODEL_NAMES.search("AI video (Kling v3.0 Pro)"))
        self.assertFalse(MODEL_NAMES.search("AI image + AI video, C2PA signing"))


if __name__ == "__main__":
    unittest.main()
