"""Skill descriptions must carry enough signal to route on.

For a model-invoked skill, the frontmatter description is the entire routing
layer: it is the only thing the model reads when deciding whether a skill
applies. Before this guard, SocialForge descriptions had a median of 105
characters — one terse sentence — while the routing decision needs the trigger
phrases a user would actually type.

The pattern enforced here: every description states what the skill does, then
"Triggers on" followed by quoted trigger phrases (slash aliases plus natural
language), then what it reads or pairs with. Median after the rewrite: ~445.

Stdlib only.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent / "skills"

MIN_LENGTH = 250
MIN_TRIGGER_PHRASES = 4


def description_of(skill_dir: Path) -> str:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    m = re.search(r"^description:\s*(.+)$", text, re.M)
    if not m:
        return ""
    raw = m.group(1).strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1].replace('\\"', '"')
    return raw


class TestDescriptionDensity(unittest.TestCase):
    def test_every_skill_has_a_description(self):
        for d in sorted(SKILLS.iterdir()):
            if d.is_dir():
                with self.subTest(skill=d.name):
                    self.assertTrue(description_of(d), f"{d.name} has no description")

    def test_descriptions_are_dense_enough_to_route_on(self):
        for d in sorted(SKILLS.iterdir()):
            if not d.is_dir():
                continue
            desc = description_of(d)
            with self.subTest(skill=d.name):
                self.assertGreaterEqual(
                    len(desc), MIN_LENGTH,
                    f"{d.name}: {len(desc)} chars. The description is the routing "
                    f"layer — one terse sentence gives the model nothing to match "
                    f"a user's phrasing against.")

    def test_descriptions_declare_their_triggers(self):
        for d in sorted(SKILLS.iterdir()):
            if not d.is_dir():
                continue
            desc = description_of(d)
            with self.subTest(skill=d.name):
                self.assertIn("Triggers on", desc,
                              f"{d.name}: no 'Triggers on' clause — the phrases a "
                              f"user would type are the strongest routing signal")
                phrases = re.findall(r'"([^"]+)"', desc)
                self.assertGreaterEqual(
                    len(phrases), MIN_TRIGGER_PHRASES,
                    f"{d.name}: only {len(phrases)} quoted trigger phrases "
                    f"({phrases}); needs ≥{MIN_TRIGGER_PHRASES} including the "
                    f"slash alias")

    def test_slash_alias_is_among_the_triggers(self):
        """The literal slash command is what power users type; it must be quoted
        in the description so the router sees it."""
        for d in sorted(SKILLS.iterdir()):
            if not d.is_dir():
                continue
            desc = description_of(d)
            with self.subTest(skill=d.name):
                self.assertIn(f'"/{d.name}"', desc,
                              f'{d.name}: description never quotes "/{d.name}"')


if __name__ == "__main__":
    unittest.main()
