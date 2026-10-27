"""A skill, command or agent is only offered if its names are visible plain text.

Claude Code 2.1.252 to 2.1.311 stopped offering a skill or command whose file or folder name carries a hidden,
direction-changing or blank-like character, or `<` or `>`, and it ignores such a `name:`. A zero-width space pasted into a
folder name is invisible in every editor and the skill simply never appears. This guard keeps every path part under
skills/, commands/ and agents/, and every frontmatter `name:`, free of exactly those characters:
  * hidden: control, format, surrogate, private-use and unassigned code points (zero-width space and joiners, the byte
    order mark, the soft hyphen), plus the combining grapheme joiner and variation selectors;
  * direction-changing: the bidirectional marks, embeddings, overrides and isolates (all format characters);
  * blank-like: space separators (no-break and ideographic spaces), line and paragraph separators, the braille blank,
    the Hangul fillers and the Halfwidth Hangul filler;
  * `<` and `>`.
Dots stay allowed (agents/03.5-* and 06.5-* are fine). Letters of any script stay allowed too: this checks for
characters a reader cannot see, not for English.
Stdlib only; works from an installed copy (no git) by walking the folder.
"""
from __future__ import annotations

import re
import tempfile
import unicodedata
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOTS = ("skills", "commands", "agents")
HIDDEN_CATEGORIES = {"Cc", "Cf", "Cs", "Co", "Cn"}
BLANK_CATEGORIES = {"Zs", "Zl", "Zp"}
EXTRA_BLANK = {0x2800, 0x3164, 0x115F, 0x1160, 0xFFA0, 0x17B4, 0x17B5, 0x034F}
VARIATION_SELECTORS = set(range(0xFE00, 0xFE10)) | set(range(0xE0100, 0xE01F0)) | set(range(0x180B, 0x180E))
NAME_LINE = re.compile(r"(?m)^name:[ \t]*(.*?)[ \t]*$")


def bad_chars(text: str) -> list:
    """The code points in `text` the host would refuse, as 'U+200B ZERO WIDTH SPACE' style labels."""
    out = []
    for ch in text:
        cp = ord(ch)
        category = unicodedata.category(ch)
        if (category in HIDDEN_CATEGORIES or category in BLANK_CATEGORIES or cp in EXTRA_BLANK
                or cp in VARIATION_SELECTORS or ch in "<>"):
            out.append(f"U+{cp:04X} {unicodedata.name(ch, 'UNNAMED')}")
    return out


def frontmatter_name(text: str) -> str | None:
    if not text.startswith(("---", "﻿---")):
        return None
    head = text.lstrip("﻿").split("\n---", 1)[0]
    m = NAME_LINE.search(head)
    return m.group(1) if m else None


def problems(root: Path) -> list:
    out = []
    for top in ROOTS:
        base = root / top
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            rel = path.relative_to(root)
            for part in rel.parts:
                found = bad_chars(part)
                if found:
                    out.append(f"{rel.as_posix()}: a name contains {', '.join(sorted(set(found)))}")
                    break
            if path.is_file() and path.suffix == ".md" and (path.name == "SKILL.md" or path.parent.name in ("commands", "agents")):
                try:
                    declared = frontmatter_name(path.read_text(encoding="utf-8-sig"))
                except (OSError, UnicodeDecodeError):
                    continue
                found = bad_chars(declared) if declared else []
                if found:
                    out.append(f"{rel.as_posix()}: name: contains {', '.join(sorted(set(found)))}")
    return out


class TestNamesAreVisiblePlainText(unittest.TestCase):

    def test_shipped_skills_commands_and_agents_are_clean(self):
        found = problems(REPO)
        self.assertEqual(found, [], "\n  " + "\n  ".join(found))

    def test_dots_and_other_scripts_are_allowed(self):
        for fine in ("03.5-humanizer-pass", "06.5-opener-check", "cf-aeo-check", "नमस्ते", "café"):
            self.assertEqual(bad_chars(fine), [], fine)

    def test_each_kind_of_character_is_caught(self):
        planted = {
            "zero-width space": "brief​-writer",
            "zero-width joiner": "brief‍",
            "byte order mark": "﻿brief",
            "soft hyphen": "bri­ef",
            "left-to-right mark": "brief‎",
            "right-to-left override": "brief‮",
            "bidi isolate": "brief⁦",
            "no-break space": "brief writer",
            "ideographic space": "brief　writer",
            "braille blank": "brief⠀",
            "hangul filler": "briefㅤ",
            "variation selector": "brief️",
            "control character": "brief\x07",
            "less-than": "brief<writer",
            "greater-than": "brief>writer",
        }
        for label, name in planted.items():
            with self.subTest(label):
                self.assertTrue(bad_chars(name), f"{label} slipped through")

    def test_a_skill_folder_with_a_zero_width_space_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = root / "skills" / "brief-writer"
            bad = root / "skills" / "brief​-writer"
            for folder in (good, bad):
                folder.mkdir(parents=True)
                (folder / "SKILL.md").write_text("---\nname: brief-writer\ndescription: x\n---\nBody\n", encoding="utf-8")
            found = problems(root)
            self.assertEqual(len(found), 2, found)  # the folder and the SKILL.md inside it
            self.assertTrue(all("U+200B ZERO WIDTH SPACE" in line for line in found))
            self.assertTrue(any(line.endswith("a name contains U+200B ZERO WIDTH SPACE") and "SKILL.md" in line for line in found))

    def test_a_hidden_character_in_the_declared_name_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "agents").mkdir()
            (root / "agents" / "reviewer.md").write_text("---\nname: review‮er\ndescription: x\n---\nBody\n", encoding="utf-8")
            (root / "commands").mkdir()
            (root / "commands" / "resume.md").write_text("---\nname: resume\ndescription: x\n---\nBody\n", encoding="utf-8")
            found = problems(root)
            self.assertEqual(len(found), 1, found)
            self.assertIn("agents/reviewer.md: name: contains U+202E", found[0])

    def test_a_clean_tree_with_dotted_agent_names_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "agents").mkdir()
            (root / "agents" / "03.5-humanizer.md").write_text("---\nname: humanizer\ndescription: x\n---\n", encoding="utf-8")
            self.assertEqual(problems(root), [])


if __name__ == "__main__":
    unittest.main()
