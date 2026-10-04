"""Skills point at files that exist, supplements stay reachable, sources stay graded.

The always-on context tax: SocialForge once listed 45 entries for 20 skills,
because seven slash commands duplicated a skill of the same name. A command
whose name equals a skill directory is the same `/socialforge:<name>` twice, so
the guard here fails the moment one returns, and tells the author to fold any
command-only content into the skill instead.

Folding leaves supplementary files inside skill directories (read on demand,
named by one line in SKILL.md). A supplement nothing links to is dead weight,
and a link that points nowhere is a broken promise, so both are checked.

New reference docs carry factual claims about other companies' platforms. The
house rule is primary sources with a URL and a checked date, and anything
secondary labeled as such. Those documents must keep a source ledger, every
ledger row must carry a date, and a row whose source is press coverage must be
graded secondary.

Stdlib only. Every test here was proven to fire by planting its failure.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"
COMMANDS = REPO / "commands"

MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
TICK_PATH = re.compile(r"`((?:references|docs|assets)/[^`\s<>{}*]+\.(?:md|json|html))`")
DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")

# Reference documents that make claims about third-party platforms.
SOURCED_DOCS = (
    "references/content-credentials-by-platform.md",
    "references/conversational-commerce.md",
    "docs/ALWAYS-ON-RECIPES.md",
)
# Hosts whose pages are press coverage, not the platform's own words.
PRESS_HOSTS = ("techcrunch.com", "nbcnews.com", "digitalcameraworld.com")


def skill_files():
    return sorted(SKILLS.glob("*/SKILL.md"))


def local_targets(skill_md: Path):
    """Yield (kind, raw_target, resolved_path) for every in-repo file a SKILL.md names."""
    text = skill_md.read_text(encoding="utf-8")
    for m in MD_LINK.finditer(text):
        target = m.group(1)
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            continue
        yield "link", target, (skill_md.parent / target.split("#")[0]).resolve()
    for m in TICK_PATH.finditer(text):
        yield "path", m.group(1), (REPO / m.group(1)).resolve()


def ledger_rows(text: str):
    """Table rows under the '## Source ledger' heading, header and separator excluded."""
    if "## Source ledger" not in text:
        return None
    section = text.split("## Source ledger", 1)[1]
    rows = [ln for ln in section.splitlines() if ln.startswith("|")]
    return [r for r in rows[2:]]  # drop the header row and the |---| separator


class TestNoDuplicateCommands(unittest.TestCase):
    def test_no_command_shares_a_name_with_a_skill(self):
        skill_names = {d.name for d in SKILLS.iterdir() if d.is_dir()}
        dupes = sorted(c.stem for c in COMMANDS.glob("*.md") if c.stem in skill_names)
        self.assertEqual(
            dupes, [],
            "A command named like a skill lists `/socialforge:<name>` twice and doubles its "
            "always-on cost. Fold any command-only content into the skill (a supplementary .md "
            f"read on demand) and git rm: {dupes}")


class TestSkillLinksResolve(unittest.TestCase):
    def test_every_markdown_link_and_referenced_doc_path_exists(self):
        broken = []
        for skill in skill_files():
            for kind, raw, resolved in local_targets(skill):
                if not resolved.is_file():
                    broken.append(f"{skill.parent.name}: {kind} {raw}")
        self.assertEqual(broken, [], "SKILL.md names files that do not exist:\n" + "\n".join(broken))

    def test_the_scan_is_not_vacuous(self):
        found = [t for s in skill_files() for t in local_targets(s)]
        self.assertGreater(len(found), 4, "no links found — the pattern stopped matching")


class TestSupplementsAreReachable(unittest.TestCase):
    def test_every_supplementary_markdown_file_is_linked_from_its_skill(self):
        orphans = []
        for skill_dir in sorted(d for d in SKILLS.iterdir() if d.is_dir()):
            body = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            for extra in sorted(skill_dir.rglob("*.md")):
                if extra.name == "SKILL.md":
                    continue
                rel = extra.relative_to(skill_dir).as_posix()
                if f"]({rel}" not in body:
                    orphans.append(f"skills/{skill_dir.name}/{rel}")
        self.assertEqual(orphans, [], "supplementary files no SKILL.md line points at:\n" + "\n".join(orphans))

    def test_the_folded_commands_left_their_supplements_behind(self):
        for rel in ("skills/index-assets/storage-and-refresh.md",
                    "skills/render-carousels/prerequisites-and-output.md"):
            self.assertTrue((REPO / rel).is_file(), f"{rel} was lost")

    def test_new_reference_docs_are_reachable_from_a_skill(self):
        bodies = {s.parent.name: s.read_text(encoding="utf-8") for s in skill_files()}
        for ref, owner in (("content-credentials-by-platform.md", "c2pa-sign"),
                           ("conversational-commerce.md", "adapt-copy")):
            self.assertTrue((REPO / "references" / ref).is_file(), ref)
            self.assertIn(ref, bodies[owner], f"{owner} no longer points at {ref}")


class TestSourceDiscipline(unittest.TestCase):
    def test_sourced_docs_carry_a_checked_date_and_a_ledger(self):
        for rel in SOURCED_DOCS:
            text = (REPO / rel).read_text(encoding="utf-8")
            with self.subTest(doc=rel):
                self.assertRegex(text, r"\*\*Checked 20\d\d-\d\d-\d\d\.\*\*",
                                 f"{rel}: the opening 'Checked <date>' line is gone")
                rows = ledger_rows(text)
                self.assertIsNotNone(rows, f"{rel}: no '## Source ledger' section")
                self.assertGreaterEqual(len(rows), 5, f"{rel}: ledger is nearly empty")
                for row in rows:
                    self.assertIn("http", row, f"{rel}: ledger row has no URL: {row[:80]}")
                    self.assertRegex(row, DATE, f"{rel}: ledger row has no checked date: {row[:80]}")

    def test_press_sources_are_graded_secondary(self):
        for rel in ("references/content-credentials-by-platform.md",
                    "references/conversational-commerce.md"):
            rows = ledger_rows((REPO / rel).read_text(encoding="utf-8")) or []
            press = [r for r in rows if any(h in r for h in PRESS_HOSTS)]
            with self.subTest(doc=rel):
                self.assertTrue(press, f"{rel}: premise — expected at least one press source")
                for row in press:
                    cells = [c.strip() for c in row.strip("|").split("|")]
                    self.assertEqual(cells[2], "S", f"{rel}: press coverage not graded S: {row[:90]}")

    def test_the_two_platform_docs_state_their_grading_legend(self):
        for rel in ("references/content-credentials-by-platform.md",
                    "references/conversational-commerce.md"):
            text = (REPO / rel).read_text(encoding="utf-8")
            self.assertIn("[S]", text, f"{rel}: no secondary label anywhere")
            self.assertIn("[P]", text, f"{rel}: no primary label anywhere")

    def test_no_dollar_price_is_quoted_in_the_platform_docs(self):
        """Prices rot; the docs send readers to the vendor's page instead."""
        for rel in SOURCED_DOCS:
            text = (REPO / rel).read_text(encoding="utf-8")
            with self.subTest(doc=rel):
                self.assertNotRegex(text, r"\$\s?\d", f"{rel}: a dollar figure crept in")


if __name__ == "__main__":
    unittest.main()
