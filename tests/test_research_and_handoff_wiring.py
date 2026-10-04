"""research-month feeds ideate-month; the scheduler hand-off stays opt-in and approved.

Three structural promises, each one a way this could rot without anything failing:

1. /socialforge:research-month and ideate-month agree on the brief's name and
   location, and the skill only names scripts and actions that exist.
2. The optional scheduler hand-off after finalize-month never becomes automatic:
   the section stays marked opt-in, requires explicit approval of the exact
   batch, and depends on the delivery audit.
3. The connector catalog stays opt-in. The shipped `.mcp.json` connects nothing,
   the two new entries (a scheduler, and a messaging setup tool that can act on
   real customers) exist only in the catalog and not in the copy-me example,
   and no catalog URL carries a credential.

The frontmatter guards in test_description_density.py already iterate every
skill directory, so research-month is held to them without a change there.

Stdlib only. Every test here was proven to fire by planting its failure.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESEARCH = (REPO / "skills" / "research-month" / "SKILL.md").read_text(encoding="utf-8")
IDEATE = (REPO / "skills" / "ideate-month" / "SKILL.md").read_text(encoding="utf-8")
FINALIZE = (REPO / "skills" / "finalize-month" / "SKILL.md").read_text(encoding="utf-8")
CONNECTORS_MD = (REPO / "CONNECTORS.md").read_text(encoding="utf-8")
RECIPES = (REPO / "docs" / "ALWAYS-ON-RECIPES.md").read_text(encoding="utf-8")

CATALOG = REPO / ".mcp.json.connectors-reference"
EXAMPLE = REPO / ".mcp.json.example"
SHIPPED = REPO / ".mcp.json"

# Catalog entries that can schedule public posts or message customers.
HIGH_IMPACT = ("postiz", "whatsapp-business-tools")


def frontmatter(text):
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    return m.group(1) if m else ""


class TestResearchMonthWiring(unittest.TestCase):
    def test_frontmatter_names_the_skill_and_its_slash_alias(self):
        fm = frontmatter(RESEARCH)
        self.assertRegex(fm, r"(?m)^name:\s*research-month\s*$")
        self.assertIn('\\"/research-month\\"', fm)
        self.assertRegex(fm, r"(?m)^user-invocable:\s*true\s*$")
        self.assertNotIn("triggers:", fm, "triggers belong inside the description")

    def test_the_skill_only_runs_scripts_and_actions_that_exist(self):
        script = REPO / "scripts" / "research_month.py"
        self.assertTrue(script.is_file())
        self.assertIn("scripts/research_month.py", RESEARCH)
        source = script.read_text(encoding="utf-8")
        for action in re.findall(r"research_month\.py --action (\w+)", RESEARCH):
            self.assertIn(f'"{action}"', source, f"skill runs --action {action}; the script has no such action")
        for flag in set(re.findall(r"(--(?:group-by|metric|min-count|stopwords|dedupe|column|csv))\b", RESEARCH)):
            self.assertIn(f'"{flag}"', source, f"skill documents {flag}; the script does not accept it")

    def test_the_brief_path_agrees_between_the_two_skills(self):
        self.assertIn("research-brief.md", RESEARCH)
        self.assertIn("research-brief.md", IDEATE)
        self.assertIn("/socialforge:research-month", IDEATE)
        path = "output/{brand}/{YYYY-MM}/research-brief.md"
        self.assertIn(path, RESEARCH)
        self.assertIn("output/{brand}/{month}/research-brief.md", IDEATE)

    def test_the_safety_rules_are_stated(self):
        lowered = RESEARCH.lower()
        for phrase in ("untrusted data", "personal data", "scrapes nothing", "one account per run"):
            self.assertIn(phrase, lowered, f"research-month lost its rule: {phrase}")

    def test_the_skill_names_no_scraping_vendor(self):
        """A named collection product is a dependency someone has to buy."""
        for vendor in ("apify", "phantombuster", "brightdata", "bright data", "scrapingbee",
                       "octoparse", "scrapy", "firecrawl", "outscraper"):
            self.assertNotIn(vendor, RESEARCH.lower())


class TestSchedulerHandoff(unittest.TestCase):
    def section(self):
        self.assertIn("## Optional: hand off to a scheduler (opt-in)", FINALIZE)
        return FINALIZE.split("## Optional: hand off to a scheduler (opt-in)", 1)[1]

    def test_the_handoff_is_opt_in_and_requires_explicit_approval_of_the_exact_batch(self):
        section = self.section()
        self.assertIn("only when the user asks", section)
        self.assertIn("never schedules or publishes on its own initiative", section)
        self.assertIn("Explicit approval for exactly that batch", section)
        self.assertIn("is a new approval", section)
        self.assertIn("`~~scheduler`", section)

    def test_the_handoff_depends_on_the_delivery_audit(self):
        section = self.section()
        self.assertIn("delivery audit passed", section)
        self.assertIn("force-finalized", section)

    def test_finalize_month_step_list_points_at_the_handoff_only_when_asked(self):
        self.assertIn("8. Only if the user asks: the optional scheduler hand-off below", FINALIZE)


class TestConnectorCatalog(unittest.TestCase):
    def load(self, path):
        return json.loads(path.read_text(encoding="utf-8"))["mcpServers"]

    def test_the_shipped_mcp_json_connects_nothing(self):
        # .mcp.json is gitignored, so an installed copy has none at all — which
        # connects nothing. A local one must still be empty, and the ignore rule
        # keeps any local edit out of every install.
        ignored = [ln.strip() for ln in (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()]
        self.assertIn(".mcp.json", ignored, ".mcp.json must stay gitignored")
        if SHIPPED.exists():
            self.assertEqual(self.load(SHIPPED), {}, "zero auto-connecting MCP servers is a house rule")

    def test_every_catalog_entry_is_https_http_transport_and_described(self):
        for name, entry in self.load(CATALOG).items():
            with self.subTest(connector=name):
                self.assertEqual(entry.get("type"), "http")
                self.assertTrue(entry.get("url", "").startswith("https://"))
                self.assertTrue(entry.get("_description"))

    def test_no_catalog_url_carries_a_credential(self):
        for name, entry in self.load(CATALOG).items():
            url = entry["url"]
            with self.subTest(connector=name):
                self.assertNotRegex(url, r"(?i)(api[_-]?key|token|secret|bearer)=")
                self.assertNotRegex(url, r"/mcp/[A-Za-z0-9_-]{16,}")
                self.assertNotIn("@", url)

    def test_the_two_high_impact_entries_exist_marked_opt_in(self):
        catalog = self.load(CATALOG)
        for name in HIGH_IMPACT:
            self.assertIn(name, catalog)
            self.assertIn("opt-in", catalog[name]["_description"].lower())
        self.assertEqual(catalog["postiz"]["url"], "https://mcp.postiz.com/mcp-oauth-dynamic")
        self.assertEqual(catalog["whatsapp-business-tools"]["url"],
                         "https://mcp.facebook.com/whatsapp_business_tools")
        self.assertIn("BETA", catalog["whatsapp-business-tools"]["_description"])
        self.assertIn("approve each call", catalog["whatsapp-business-tools"]["_description"])
        self.assertIn("approval", catalog["postiz"]["_description"])

    def test_the_copy_me_example_never_includes_them(self):
        """`cp .mcp.json.example .mcp.json` connects everything in the file."""
        example = self.load(EXAMPLE)
        for name in HIGH_IMPACT:
            self.assertNotIn(name, example,
                             f"{name} can schedule public posts or message customers; "
                             "it belongs only in the opt-in catalog")

    def test_connectors_doc_lists_both_as_catalog_only(self):
        for needle in ("`~~scheduler`", "`~~messaging`", "Postiz", "WhatsApp Business Tools",
                       "not in `.mcp.json.example`"):
            self.assertIn(needle, CONNECTORS_MD)


class TestRecipesKeepTheApprovalBoundary(unittest.TestCase):
    def test_each_job_states_its_approval_boundary(self):
        self.assertGreaterEqual(RECIPES.count("Approval boundary:"), 2)

    def test_creative_generation_and_hand_off_are_never_unattended(self):
        row = next(ln for ln in RECIPES.splitlines()
                   if ln.startswith("| Creative generation"))
        self.assertIn("**Never**", row)
        for skill in ("compose-creative", "generate-video", "finalize-month", "manage-reviews"):
            self.assertIn(skill, row)

    def test_write_connectors_are_kept_out_of_routines(self):
        self.assertIn("Leave the `postiz` and `whatsapp-business-tools` catalog connectors out", RECIPES)


if __name__ == "__main__":
    unittest.main()
