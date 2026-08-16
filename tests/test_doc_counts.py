"""Live documentation must not advertise stale skill / agent / command / script counts.

The repo grows faster than the prose describing it: skills, agents and commands are added
release after release while guides keep quoting the counts they were written against.
Counts are derived from the filesystem here, so the only way to satisfy this test is to
fix the prose.

The 2026-08-16 documentation audit found the original guard was pattern-blind: the README
said "All 16 SKILL.md files" (the repo has 20 skills) and quoted "25 scripts" in four
places (the repo has 28), and AGENTS.md pinned v1.13.1 — eleven releases stale — on the
line every non-Claude runtime auto-loads. The guard now also covers scripts and
"N SKILL.md files", and AGENTS.md must carry the current release version.

Deliberately NOT flagged:
  - CHANGELOG.md, research/ (dated internal design docs), and any file banner-marked
    HISTORICAL DOCUMENT
  - lines carrying a bold dated version tag ("**v3.9 rebuilt ..."), which narrate a past
    release truthfully and must keep their ship-time numbers
  - sections whose heading names a release ("### Release v1.24.0"), for the same reason
  - ranges and thresholds ("3-5 skills", "<5 agents", "~20 scripts")
  - sentences about a sibling plugin, which has its own counts
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# "20 skills" / "28 Python scripts" but not "3-5 skills", "<5 agents", "v1.19.2 skills"
COUNT_RE = re.compile(r"(?<![-<>~\d])\b(\d{1,3})\s+(?:Python\s+)?(skills|agents|commands|scripts)\b")
# "All 16 SKILL.md files" — the phrasing the original guard could not see
SKILL_MD_RE = re.compile(r"(?<![-<>~\d])\b(\d{1,3})\s+SKILL\.md files?\b")
# "all 16 SocialForge skills" — plugin name between number and noun
NAMED_SKILLS_RE = re.compile(r"(?<![-<>~\d])\b(\d{1,3})\s+SocialForge skills\b", re.I)
DATED_LINE = re.compile(r"\*\*v\d+\.\d+")
# A heading that narrates a release keeps its ship-time numbers.
RELEASE_HEADING = re.compile(r"^#{1,6}\s.*\bv\d+\.\d+.*", re.I)
RELEASE_HEADING_WORDS = ("release", "earlier", "previous", "what's new", "whats-new",
                        "shipped", "upgrad", "history", "changelog")
HISTORICAL_BANNER = "HISTORICAL DOCUMENT"
SIBLINGS = ("contentforge", "content forge", "digital-marketing-pro", "digital marketing pro")


def ground_truth():
    return {
        "skills": len([d for d in (REPO / "skills").iterdir() if d.is_dir()]),
        "agents": len(list((REPO / "agents").glob("*.md"))),
        "commands": len(list((REPO / "commands").glob("*.md"))),
        "scripts": len(list((REPO / "scripts").glob("*.py"))),
    }


def live_docs():
    for f in sorted(REPO.rglob("*.md")):
        if any(p in f.parts for p in (".git", "node_modules", ".pytest_cache", "research")):
            continue
        if f.name == "CHANGELOG.md":
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        if HISTORICAL_BANNER in text[:800]:
            continue
        yield f, text


def _is_release_heading(line):
    if not RELEASE_HEADING.match(line):
        return False
    # A heading that IS a version number labels a release entry outright.
    if re.match(r'#{1,6}\s+v\d+\.\d+', line):
        return True
    low = line.lower()
    return any(w in low for w in RELEASE_HEADING_WORDS)


class TestLiveDocCounts(unittest.TestCase):
    def test_no_stale_counts_in_live_docs(self):
        truth = ground_truth()
        stale = []
        for f, text in live_docs():
            in_history = False
            for i, line in enumerate(text.splitlines(), 1):
                # Headings reset the state: a release-narrative heading opens a
                # historical run, any other heading closes one.
                if line.lstrip().startswith("#"):
                    in_history = _is_release_heading(line.lstrip())
                # A bold dated version tag opens one, and everything after it in this
                # section narrates past releases: the entry's body keeps its ship-time
                # numbers even though the tag sits on an earlier line.
                if DATED_LINE.search(line):
                    in_history = True
                    continue
                if in_history:
                    continue
                low = line.lower()
                if any(s in low for s in SIBLINGS):
                    continue
                found = [(int(m.group(1)), m.group(2), m.group(0))
                         for m in COUNT_RE.finditer(line)]
                found += [(int(m.group(1)), "skills", m.group(0))
                          for pat in (SKILL_MD_RE, NAMED_SKILLS_RE)
                          for m in pat.finditer(line)]
                for n, noun, shown in found:
                    if n != truth[noun]:
                        stale.append(
                            "%s:%d says '%s' but the repo has %d %s"
                            % (f.relative_to(REPO).as_posix(), i, shown, truth[noun], noun))
        self.assertEqual(stale, [], "Stale counts in live docs:\n  " + "\n  ".join(stale))

    def test_ground_truth_is_sane(self):
        """A miscounted truth would make the guard above vacuous."""
        truth = ground_truth()
        self.assertGreater(truth["skills"], 0)
        self.assertGreater(truth["agents"], 0)
        self.assertGreater(truth["commands"], 0)
        self.assertGreater(truth["scripts"], 0)

    def test_guard_can_fail(self):
        """Plant-check: each new pattern must actually match its rot form."""
        self.assertTrue(SKILL_MD_RE.search("All 16 SKILL.md files in SocialForge"))
        self.assertTrue(NAMED_SKILLS_RE.search("all 16 SocialForge skills register"))
        self.assertTrue(COUNT_RE.search("22 Python scripts"))
        self.assertFalse(COUNT_RE.search("~22 scripts"))  # approx stays exempt


class TestAgentsContextCurrent(unittest.TestCase):
    """AGENTS.md is auto-loaded by Codex / Cursor / Copilot / Antigravity. Before this
    guard it pinned 'Supported surfaces (v1.13.1)' — eleven releases stale."""

    def setUp(self):
        self.text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
        self.version = json.loads(
            (REPO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]

    def test_supported_surfaces_version_is_current(self):
        m = re.search(r"Supported surfaces \(v([\d.]+)\)", self.text)
        self.assertIsNotNone(m, "AGENTS.md lost its 'Supported surfaces (vX.Y.Z)' line")
        self.assertEqual(m.group(1), self.version,
                         "AGENTS.md surfaces line pins v%s but the plugin is v%s"
                         % (m.group(1), self.version))

    def test_supported_surfaces_lists_all_eight(self):
        m = re.search(r"^.*Supported surfaces.*$", self.text, re.M)
        line = m.group(0) if m else ""
        for name in ("Claude Code", "Cowork", "Codex", "Cursor", "Copilot",
                     "Antigravity", "Hermes", "OpenClaw"):
            self.assertIn(name, line, "AGENTS.md surfaces line is missing %s" % name)


if __name__ == "__main__":
    unittest.main()
