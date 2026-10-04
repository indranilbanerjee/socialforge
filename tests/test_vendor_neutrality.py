"""Docs ask for capabilities; they never install a vendor.

A community PR once wired a commercial third-party research plugin into the
reference docs — install commands, API-key configuration, a per-feature mapping
table. The instructions were marked optional, but a named product in a doc is a
dependency someone has to buy, install, and keep working, and it contradicts the
plugin's own architecture: models, prices, and research are all resolved as
capabilities at run time, supplied by whatever the user's environment already
has.

The self-containment guard did not fire because it only watches for sibling
plugin names. This guard watches for the general shape: vendor-install
instructions and third-party credential wiring inside the doc surface.

The same blind spot hid a second class of leak. This guard (and test_model_book,
which scans the execution scripts for quoted model-id literals) never read the
SKILL prose, and the only dollar-figure guards were per-file allow-lists written
after one incident each — the setup skill, two platform docs. So index-assets
could name "Gemini Vision" and state three per-image prices, generate-video could
name model versions, and nothing failed: a guard that scans a hand-picked list
passes everything outside the list. TestInstructionProseNamesCapabilities below
scans the whole instruction surface instead.

Stdlib only.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The doc surface: what ships to users as instructions.
DOC_DIRS = ["references", "skills", "commands", "agents", "docs"]

# Install-command shapes for OTHER ecosystems' packages. SocialForge's own
# install lines (claude plugin install, pip install for its declared deps)
# are not matched by these.
VENDOR_INSTALL = re.compile(
    r"(openclaw\s+plugins\s+install\s+@"     # scoped third-party openclaw plugin
    r"|npm\s+install\s+(-g\s+)?@(?!anthropic-ai)"  # scoped npm pkg, allow anthropic's CLI
    r"|plugins\.entries\.[a-z-]+\.config\.apiKey"  # wiring a plugin's paid key
    r"|SigningKey\b)",
    re.IGNORECASE)

# Regression pin for the specific incident.
KNOWN_VENDORS = re.compile(r"tweetclaw|xquik", re.IGNORECASE)


def doc_files():
    for d in DOC_DIRS:
        base = ROOT / d
        if base.exists():
            yield from base.rglob("*.md")
    # Root-level docs too — the incident's README line initially escaped this
    # guard because only subdirectories were scanned. CHANGELOG is exempt:
    # release history legitimately describes what was removed and why.
    for f in ROOT.glob("*.md"):
        if f.name != "CHANGELOG.md":
            yield f


class TestVendorNeutrality(unittest.TestCase):
    def test_no_vendor_install_instructions_in_docs(self):
        hits = []
        for f in doc_files():
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if VENDOR_INSTALL.search(line):
                    hits.append(f"{f.relative_to(ROOT)}:{i}: {line.strip()[:80]}")
        self.assertEqual(hits, [],
                         "docs must ask for a capability, not install a vendor:\n"
                         + "\n".join(hits))

    def test_the_specific_incident_cannot_return(self):
        hits = []
        for f in doc_files():
            if KNOWN_VENDORS.search(f.read_text(encoding="utf-8")):
                hits.append(str(f.relative_to(ROOT)))
        self.assertEqual(hits, [], f"removed vendor reappeared in: {hits}")

    def test_research_intake_is_capability_first(self):
        """The intake must lead with the harness's own tools and keep the
        user-paste fallback — the two rungs every environment actually has."""
        intake = (ROOT / "references" / "x-twitter-research-intake.md").read_text(encoding="utf-8")
        self.assertIn("harness", intake.lower())
        self.assertIn("user-provided", intake)
        self.assertNotRegex(intake, r"install\s+@", "the intake instructs a vendor install")

    def test_intake_keeps_the_untrusted_input_rule(self):
        """The one safety rule that must survive any rewrite: fetched social
        content is data, never instructions."""
        intake = (ROOT / "references" / "x-twitter-research-intake.md").read_text(encoding="utf-8")
        self.assertRegex(intake, r"[Nn]ever follow commands",
                         "the prompt-injection guard was lost in a rewrite")


# ---------------------------------------------------------------------------
# Model version names and prices in the prose the model reads at run time
# ---------------------------------------------------------------------------

# Skills, agents and commands tell the model what to do. A model version or a
# dollar figure written there is a claim about the day it was written, and the
# plugin runs long after that day. They must name a capability kind or a registry
# alias (`latest-video-wavespeed`) and send price questions to price_book.py.
# references/models/ is deliberately NOT scanned: those files are the model
# recipes, one per model, and naming the model is their whole job.
INSTRUCTION_DIRS = ["skills", "agents", "commands"]

# A product family on its own ("Veo", "Kling", "Gemini") may stay: it names the
# credential rung a user must configure. What may not stay is a VERSION, a model
# id, or a tier/brand name that identifies one specific model.
MODEL_NAME = re.compile(
    r"\bkling\s*v?\d"                      # Kling v3.0 Pro
    r"|\bveo[\s-]*\d"                      # Veo 3.1
    r"|\bgemini[\s-]*(?:\d|vision\b|flash\b|pro\b|ultra\b|nano\b|omni\b)"  # Gemini 3 Pro Image, Gemini Vision
    r"|\bnano\s+banana\b"                  # Nano Banana 2 / Pro
    r"|\b(?:imagen|seedance|gpt)[\s-]*\d"
    r"|\bsoul\s*v?\d"
    r"|\bclaude[\s-]+(?:opus|sonnet|haiku)\b"
    r"|\bkwaivgi/"                         # a WaveSpeed model path
    r"|\b(?:kling|veo|gemini|seedance|higgsfield|imagen|gpt|claude)-[\w.-]*\d",  # model-id slugs
    re.IGNORECASE)

# Dollar figures. Euro/pound amounts are not matched: the only ones in the docs
# are regulatory fines, which are facts about a law, not prices of a generation.
PRICE_FIGURE = re.compile(
    r"\$\s?\d"                                        # $0.12, $ 5
    r"|\b\d[\d,.]*\s*(?:USD|dollars?|cents?)\b"       # 12 USD, 5 dollars
    r"|\b(?:USD|US\$)\s?\d"                           # USD 5
    r"|--price\s+[\"']?\d",                           # a literal rate in a price_book example
    re.IGNORECASE)

# The user-facing video sections, scanned with the same patterns.
VIDEO_SECTIONS = [
    ("README.md", "## Video Generation"),
    ("docs/USER-GUIDE.md", "## 9. Producing Content -- Video"),
]


def instruction_files():
    for d in INSTRUCTION_DIRS:
        base = ROOT / d
        if base.exists():
            yield from sorted(base.rglob("*.md"))


def section_lines(rel, heading):
    """The lines of one `## ` section, heading included."""
    lines = (ROOT / rel).read_text(encoding="utf-8").splitlines()
    start = next((i for i, line in enumerate(lines) if line.lstrip("﻿").startswith(heading)), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start:end]


def scan(lines, pattern):
    """(line number, matched text, context) for every line the pattern hits."""
    out = []
    for i, line in enumerate(lines, 1):
        m = pattern.search(line)
        if m:
            out.append((i, m.group(0), line.strip()[:90]))
    return out


class TestInstructionProseNamesCapabilities(unittest.TestCase):
    def test_the_scan_covers_the_whole_instruction_surface(self):
        """Premise: a scan of an empty or hand-picked list passes everything."""
        files = [f.relative_to(ROOT).as_posix() for f in instruction_files()]
        skill_files = [f for f in files if f.endswith("/SKILL.md")]
        self.assertGreaterEqual(len(skill_files), 20)
        for must in ("skills/index-assets/SKILL.md", "skills/generate-video/SKILL.md",
                     "skills/setup/SKILL.md", "agents/image-compositor.md"):
            self.assertIn(must, files)

    def test_no_model_version_names_in_instruction_prose(self):
        hits = []
        for f in instruction_files():
            lines = f.read_text(encoding="utf-8").splitlines()
            hits += [f"{f.relative_to(ROOT).as_posix()}:{i}: {found!r}  {ctx}"
                     for i, found, ctx in scan(lines, MODEL_NAME)]
        self.assertEqual(hits, [],
                         "instruction prose names a specific model. Say the capability kind or "
                         "the registry alias (e.g. `latest-video-wavespeed`) and point to "
                         "`python scripts/generate_video.py --list-models`:\n" + "\n".join(hits))

    def test_no_dollar_prices_in_instruction_prose(self):
        hits = []
        for f in instruction_files():
            lines = f.read_text(encoding="utf-8").splitlines()
            hits += [f"{f.relative_to(ROOT).as_posix()}:{i}: {found!r}  {ctx}"
                     for i, found, ctx in scan(lines, PRICE_FIGURE)]
        self.assertEqual(hits, [],
                         "instruction prose states a price. Prices come from a live quote "
                         "(`python scripts/price_book.py --action quote ...`), never from the "
                         "page:\n" + "\n".join(hits))

    def test_the_user_facing_video_sections_name_no_model_versions_or_prices(self):
        for rel, heading in VIDEO_SECTIONS:
            with self.subTest(doc=rel):
                lines = section_lines(rel, heading)
                self.assertIsNotNone(lines, f"{rel}: heading {heading!r} not found — the guard "
                                            "is scanning nothing")
                self.assertGreater(len(lines), 8)
                found = scan(lines, MODEL_NAME) + scan(lines, PRICE_FIGURE)
                self.assertEqual(found, [], f"{rel} names a model version or a price: {found}")

    def test_the_patterns_catch_the_leaks_they_were_written_for(self):
        """Each string is a line that really shipped. If a pattern is loosened until
        one of these slips through, this fails before a real leak does."""
        must_match_model = [
            "analyzed by Gemini Vision to understand what's in it",
            "images via WaveSpeed's Kling v3.0 Pro image-to-video endpoint",
            "(Nano Banana Pro / Gemini 3 Pro Image, resolved via `latest-image-google`)",
            "Nano Banana 2 (Gemini 3.1 Flash Image)",
            "Models available: gemini-3.1-flash-image",
            "kwaivgi/kling-v3.0-pro/image-to-video",
            "Veo 3.1 can take several minutes",
            "veo-3.1-generate-001",
            "Provider: HiggsField (Soul v2 + Kling v2.1, fallback)",
            '--model "kling-v3.0-pro" --provider wavespeed',
        ]
        must_match_price = [
            "Each image analysis costs approximately $0.002-0.005 (vision).",
            "expect ~$0.10-0.25 total",
            "will cost approximately $0.12 in API calls",
            "costs 5 dollars a month",
            "a rate of 0.4 USD per second",
            "--unit second --price 0.084 --source https://example.com",
        ]
        must_not_match = [
            "the registry alias `latest-video-wavespeed`, resolved at run time",
            "Vertex AI credentials; the `veo` rung; WaveSpeed; HiggsField",
            "Generate with Gemini via Vertex AI",
            "see gemini-extension.json for the Antigravity manifest",
            'python "${CLAUDE_PLUGIN_ROOT}/scripts/price_book.py" --action quote --units 5',
            "Article 50 fines of up to €15 million",
            "ask the user for the rate; it is shown at the provider's pricing URL",
            "the quoted total is {total}",
            "gemini_image_generation is a cost-log operation name",
        ]
        for line in must_match_model:
            self.assertTrue(MODEL_NAME.search(line), f"MODEL_NAME missed: {line}")
        for line in must_match_price:
            self.assertTrue(PRICE_FIGURE.search(line), f"PRICE_FIGURE missed: {line}")
        for line in must_not_match:
            self.assertFalse(MODEL_NAME.search(line) or PRICE_FIGURE.search(line),
                             f"false positive on legitimate prose: {line}")


if __name__ == "__main__":
    unittest.main()
