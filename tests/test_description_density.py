"""Skill and command descriptions must fit the model's skill listing and still route.

Claude Code puts every model-invocable skill and command into ONE listing as
``- <plugin>:<name>: <description>`` lines. Its budget is characters, not
tokens: context tokens x 4 x 1% (8,000 chars on a 200k window, 40,000 on 1M),
shared by every installed plugin. Entries that do not fit lose their
description first (names are never dropped), so a long description is not
"more routing signal" - past the budget it is no signal at all.

WHY THIS IS SHORT - read before "improving" it. The budget is CHARACTERS
(context window x 4 x 1%), shared by every installed plugin, and every
entry's namespaced name counts and is never dropped, so the descriptions are
what gets lost first. SocialForge's CHANGELOG (0.1.0) records descriptions under 130 characters "to fit the discovery budget"; the August 2026 density guard (250+ characters, four or more trigger phrases) then reversed it, because the reason was not written down. Without the reason written down, a
density guard that rewarded length undid it. Before lengthening any
description, run the trigger evals (evals/triggers, with
SLASH_COMMAND_TOOL_CHAR_BUDGET pinned) before and after: they are the check
that a description still routes, and length is not evidence of routing.

The rule enforced here (measured with the trigger evals in evals/triggers):

  * 60-150 characters, median <= 120; the decisive words come first:
    ``<Verb> <object> <scope/output>. "<one phrase a user types>"``
  * one or two quoted phrases, never the slash alias, no "Triggers on",
    no ``when_to_use`` (it is appended to the listing and counts against it)
  * at least one token of the skill's name appears in the first 100 characters
  * one owner per quoted phrase, plugin-wide
  * a registered near-miss pair states its axis in both descriptions; a
    "-> sibling" pointer sits on exactly ONE side, and nowhere else
  * listing cost (formula below, namespaced names, skills, commands AND
    workflows) stays under 5800 characters for this plugin

Workflows (workflows/*.js, `meta.description`) are listed to the model next to
skills - the model calls them through the Skill tool - so they follow the same
rule and count toward the ceiling. The first version of this guard read only
skills and commands: the month-copy-preview workflow carried a 185-character description
that broke the 60-150 rule, and every published listing figure left it out.
test_plant_old_workflow_text_is_rejected puts that text back and requires the
guard to fail; test_every_workflow_description_is_readable fails when a workflow
cannot be parsed, so a workflow cannot escape the count.

Stdlib only.
"""
from __future__ import annotations

import json
import re
import statistics
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / "workflows"
PLUGIN = "socialforge"
# The description this plugin's workflow shipped with in the first stage-2 release (4.4.0 / 1.28.0).
OLD_WORKFLOW_NAME = "month-copy-preview"
OLD_WORKFLOW_DESC = "For an already-parsed month, adapt every post's copy per platform and run the compliance check in parallel, then return one review sheet — no image or video generation, no credits spent"

MIN_LENGTH = 60
MAX_LENGTH = 150
MEDIAN_CEILING = 120
MAX_PHRASES = 2
NAME_WINDOW = 100
NAME_STOPLIST = {"check", "plan", "run", "audit", "cf", "sf"}
LISTING_CEILING = 5800   # chars for this plugin's share of the listing
ENTRY_DESC_CAP = 1536                   # description is truncated here by the host

# (a, b): a and b are confusable siblings; exactly one description names the other.
NEAR_MISS_PAIRS = [('generate-post', 'compose-creative'), ('client-review', 'review'), ('new-month', 'parse-calendar'), ('new-month', 'ideate-month'), ('month-copy-preview', 'adapt-copy')]

FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.S)
PHRASE_RE = re.compile(r'"([^"]+)"')
SLASH_ALIAS_RE = re.compile(r"(?<![\w/])/[A-Za-z][\w-]*")
POINTER_RE = re.compile(r"(?:->|→)\s*([a-z0-9-]+)")
WORKFLOW_META_RE = re.compile(r"export const meta = \{(.*?)\n\}", re.S)
WORKFLOW_DESC_RE = re.compile(r"^\s*description:\s*'((?:[^'\\]|\\.)*)'", re.M)


def _unquote(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
        try:
            return json.loads(raw)
        except ValueError:
            return raw[1:-1].replace('\\"', '"')
    return raw


def parse_entry(path: Path, name: str, kind: str) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    m = FM_RE.match(text)
    fm = m.group(1) if m else ""
    d = re.search(r"^description:[ \t]*(.*)$", fm, re.M)
    return {
        "name": name,
        "kind": kind,
        "desc": _unquote(d.group(1)) if d else "",
        "single_line": bool(d) and bool(d.group(1).strip()),
        "has_when_to_use": bool(re.search(r"^when_to_use:", fm, re.M)),
        "model_hidden": bool(re.search(r"^disable-model-invocation:\s*true\s*$", fm, re.M)),
    }


def parse_workflow_description(js: str) -> str | None:
    """The literal single-quoted `description` inside a workflow's `export const meta = {...}` block."""
    meta = WORKFLOW_META_RE.search(js)
    m = WORKFLOW_DESC_RE.search(meta.group(1)) if meta else None
    return re.sub(r"\\(.)", r"\1", m.group(1)) if m else None


def workflow_files() -> dict[str, Path]:
    return {p.stem: p for p in sorted(WORKFLOWS.glob("*.js"))} if WORKFLOWS.is_dir() else {}


def load_entries() -> list[dict]:
    out = []
    for d in sorted((ROOT / "skills").iterdir()):
        if d.is_dir() and (d / "SKILL.md").exists():
            out.append(parse_entry(d / "SKILL.md", d.name, "skill"))
    cmds = ROOT / "commands"
    if cmds.is_dir():
        for f in sorted(cmds.glob("*.md")):
            out.append(parse_entry(f, f.stem, "command"))
    for name, p in workflow_files().items():
        desc = parse_workflow_description(p.read_text(encoding="utf-8", errors="replace"))
        if desc is not None:
            out.append({"name": name, "kind": "workflow", "desc": desc, "single_line": True,
                        "has_when_to_use": False, "model_hidden": False})
    return out


# ── pure checks (the plant tests call these with synthetic data) ────────

def normalize_phrase(p: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", p.lower()).split())


def phrases_of(desc: str) -> list[str]:
    return PHRASE_RE.findall(desc)


def name_tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[-_ ]+", name.lower()) if t and t not in NAME_STOPLIST]


def entry_problems(e: dict) -> list[str]:
    desc, name = e["desc"], e["name"]
    probs = []
    if not e["single_line"]:
        probs.append("description is not a single-line string")
    if len(desc) < MIN_LENGTH:
        probs.append(f"{len(desc)} chars < {MIN_LENGTH}")
    if len(desc) > MAX_LENGTH:
        probs.append(f"{len(desc)} chars > {MAX_LENGTH}")
    n = len(phrases_of(desc))
    if not 1 <= n <= MAX_PHRASES:
        probs.append(f"{n} quoted phrases (want 1-{MAX_PHRASES})")
    if SLASH_ALIAS_RE.search(desc):
        probs.append("contains a slash alias (the name is already listed)")
    if "triggers on" in desc.lower():
        probs.append("contains 'Triggers on' (dead weight in the listing)")
    if e["has_when_to_use"]:
        probs.append("has when_to_use (appended to the listing; fold it into the description)")
    toks = name_tokens(name)
    if toks and not any(t in desc[:NAME_WINDOW].lower() for t in toks):
        probs.append(f"none of {toks} appears in the first {NAME_WINDOW} chars")
    return probs


def duplicate_phrases(entries: list[dict]) -> dict[str, list[str]]:
    seen: dict[str, list[str]] = {}
    for e in entries:
        for p in phrases_of(e["desc"]):
            seen.setdefault(normalize_phrase(p), []).append(e["name"])
    return {p: names for p, names in seen.items() if len(set(names)) > 1}


def pair_problems(entries: list[dict], pairs) -> list[str]:
    by_name = {e["name"]: e["desc"] for e in entries}
    probs, registered = [], set()
    for a, b in pairs:
        registered.update((a, b))
        if a not in by_name or b not in by_name:
            probs.append(f"pair ({a}, {b}) names a missing entry")
            continue
        a_names_b = b in POINTER_RE.findall(by_name[a])
        b_names_a = a in POINTER_RE.findall(by_name[b])
        if a_names_b == b_names_a:
            probs.append(f"pair ({a}, {b}): exactly one side must carry the '-> sibling' pointer "
                         f"(a->b={a_names_b}, b->a={b_names_a})")
    for e in entries:
        if POINTER_RE.search(e["desc"]) and e["name"] not in registered:
            probs.append(f"{e['name']}: '->' pointer on an entry that is not in a registered pair")
    return probs


def listing_cost(entries: list[dict], plugin: str = PLUGIN, only_model_visible: bool = False) -> int:
    """Characters one listing line costs: '- ' + '<plugin>:<name>' + ': ' + description
    (capped at 1,536) + newline, i.e. len(namespaced) + 4 + len(desc) + 1."""
    total = 0
    for e in entries:
        if only_model_visible and e["model_hidden"]:
            continue
        total += len(f"{plugin}:{e['name']}") + 4 + min(len(e["desc"]), ENTRY_DESC_CAP) + 1
    return total


# ── tests against the real plugin ───────────────────────────────────────

class TestDescriptionRule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = load_entries()

    def test_entries_were_found(self):
        self.assertGreater(len(self.entries), 20)

    def test_every_workflow_description_is_readable(self):
        unreadable = [n for n, p in workflow_files().items()
                      if parse_workflow_description(p.read_text(encoding="utf-8", errors="replace")) is None]
        self.assertEqual(unreadable, [], "workflows whose meta.description this guard cannot read "
                                         "(they would escape the rule and the listing ceiling)")
        listed = {e["name"] for e in self.entries if e["kind"] == "workflow"}
        self.assertEqual(listed, set(workflow_files()))

    def test_every_entry_meets_the_rule(self):
        failures = [f"{e['kind']} {e['name']}: " + "; ".join(p)
                    for e in self.entries if (p := entry_problems(e))]
        self.assertEqual(failures, [], "Descriptions off the rule:\n  " + "\n  ".join(failures))

    def test_median_is_short_and_not_empty(self):
        med = statistics.median(len(e["desc"]) for e in self.entries)
        self.assertLessEqual(med, MEDIAN_CEILING, f"median {med} chars")
        self.assertGreaterEqual(med, MIN_LENGTH, f"median {med} chars")

    def test_one_owner_per_quoted_phrase(self):
        self.assertEqual(duplicate_phrases(self.entries), {})

    def test_near_miss_pairs_name_each_other_on_one_side_only(self):
        self.assertEqual(pair_problems(self.entries, NEAR_MISS_PAIRS), [])

    def test_listing_cost_fits_the_ceiling(self):
        cost = listing_cost(self.entries)
        self.assertLessEqual(
            cost, LISTING_CEILING,
            f"listing cost {cost} chars > {LISTING_CEILING}. Shorten descriptions; do not raise the "
            "ceiling without re-running evals/triggers at the default budget.")

    def test_model_visible_cost_never_exceeds_total(self):
        self.assertLessEqual(listing_cost(self.entries, only_model_visible=True),
                             listing_cost(self.entries))

    # ── planted failures: every check must catch its failure ────────────

    GOOD = {"name": "example-skill", "kind": "skill", "single_line": True, "has_when_to_use": False,
            "model_hidden": False,
            "desc": 'Run the example skill over a folder and report what it finds. "do the example thing"'}

    def _bad(self, **kw) -> dict:
        return {**self.GOOD, **kw}

    def test_plant_good_entry_is_clean(self):
        self.assertEqual(entry_problems(self.GOOD), [])

    def test_plant_too_short(self):
        self.assertTrue(any("<" in p for p in entry_problems(self._bad(desc='Do it. "do it"'))))

    def test_plant_too_long(self):
        long_desc = 'Example ' + "word " * 40 + '"do the example thing"'
        self.assertTrue(any(">" in p for p in entry_problems(self._bad(desc=long_desc))))

    def test_plant_no_phrase_and_too_many_phrases(self):
        none = self._bad(desc="Example skill that reports on a folder of files and summarizes what it finds there.")
        many = self._bad(desc='Example skill for folders. "do the example" "run the example" "an example thing"')
        self.assertTrue(any("quoted phrases" in p for p in entry_problems(none)))
        self.assertTrue(any("quoted phrases" in p for p in entry_problems(many)))

    def test_plant_slash_alias_and_triggers_on(self):
        alias = self._bad(desc='Example skill that reports on a folder. "do the example thing" /' + PLUGIN + ':example-skill')
        trig = self._bad(desc='Example skill that reports on a folder of files. Triggers on "do the example thing"')
        self.assertTrue(any("slash alias" in p for p in entry_problems(alias)))
        self.assertTrue(any("Triggers on" in p for p in entry_problems(trig)))
        # ordinary slashes are fine
        self.assertEqual(entry_problems(self._bad(desc='Example skill for A/B tests over a 30/60/90-day window. "do the example thing"')), [])

    def test_plant_when_to_use(self):
        self.assertTrue(any("when_to_use" in p for p in entry_problems(self._bad(has_when_to_use=True))))

    def test_plant_name_token_missing_from_first_100_chars(self):
        late = self._bad(desc=("Report on a folder of files and summarize what it finds there, in a long preamble "
                               'that delays the name past the window: example. "do the thing"'))
        self.assertTrue(any("first" in p for p in entry_problems(late)))
        # tokens in the stoplist exempt a name that has nothing else
        stop = self._bad(name="cf-audit", desc='Report on a folder of files and summarize what it finds there. "do the thing"')
        self.assertEqual(entry_problems(stop), [])

    def test_plant_duplicate_phrase_across_entries(self):
        a = self._bad(name="a-one", desc='Example one. "Do The Example!"')
        b = self._bad(name="b-two", desc='Example two. "do the example"')
        self.assertEqual(list(duplicate_phrases([a, b])), ["do the example"])
        self.assertEqual(duplicate_phrases([a, self._bad(name="c", desc='Other. "something else"')]), {})

    def test_plant_pair_pointer_rules(self):
        a = self._bad(name="alpha", desc='Alpha does one thing; the other thing -> beta. "do alpha"')
        b = self._bad(name="beta", desc='Beta does the other thing. "do beta"')
        self.assertEqual(pair_problems([a, b], [("alpha", "beta")]), [])
        both = self._bad(name="beta", desc='Beta does the other thing -> alpha. "do beta"')
        self.assertTrue(pair_problems([a, both], [("alpha", "beta")]))          # both sides name each other
        self.assertTrue(pair_problems([self._bad(name="alpha", desc='Alpha. "do alpha"'), b], [("alpha", "beta")]))  # neither
        self.assertTrue(pair_problems([a, b], []))                               # pointer outside a registered pair
        self.assertTrue(pair_problems([a], [("alpha", "beta")]))                 # missing entry

    def test_plant_listing_cost_formula_and_ceiling(self):
        e = self._bad(name="x", desc="d" * 100)
        self.assertEqual(listing_cost([e], "p"), len("p:x") + 4 + 100 + 1)
        huge = self._bad(name="x", desc="d" * 5000)
        self.assertEqual(listing_cost([huge], "p"), len("p:x") + 4 + ENTRY_DESC_CAP + 1)
        over = [self._bad(name=f"n{i}", desc="d" * 150) for i in range(60)]
        self.assertGreater(listing_cost(over), LISTING_CEILING)
        hidden = self._bad(name="h", desc="d" * 100, model_hidden=True)
        self.assertEqual(listing_cost([hidden], "p", only_model_visible=True), 0)

    def test_plant_old_workflow_text_is_rejected(self):
        old = self._bad(name=OLD_WORKFLOW_NAME, kind="workflow", desc=OLD_WORKFLOW_DESC)
        self.assertGreater(len(OLD_WORKFLOW_DESC), MAX_LENGTH)
        self.assertTrue(any(">" in p for p in entry_problems(old)))
        current = [e for e in self.entries if e["name"] == OLD_WORKFLOW_NAME and e["kind"] == "workflow"]
        self.assertEqual(len(current), 1, "the workflow is no longer in the guard's entries")
        swapped = [old if e is current[0] else e for e in self.entries]
        self.assertGreater(listing_cost(swapped), listing_cost(self.entries))

    def test_plant_workflow_parser(self):
        js = ("export const meta = {\n  name: 'w',\n  description: 'It\\'s a sweep',\n}\n"
              "const schema = { description: 'not this one' }\n")
        self.assertEqual(parse_workflow_description(js), "It's a sweep")
        # a double-quoted or missing description is unreadable; the readability test turns that into a failure
        self.assertIsNone(parse_workflow_description('export const meta = {\n  name: "w",\n  description: "d",\n}\n'))
        self.assertIsNone(parse_workflow_description("export const meta = {\n  name: 'w',\n}\n"))

    def test_plant_unicode_arrow_cannot_hide_a_pointer(self):
        # a stray U+2192 pointer is parsed like "->", so it cannot slip past the pair check
        a = self._bad(name="alpha", desc='Alpha does one thing; the other thing → beta. "do alpha"')
        b = self._bad(name="beta", desc='Beta does the other thing → alpha. "do beta"')
        self.assertTrue(pair_problems([a, b], [("alpha", "beta")]))            # both sides name each other
        stray = self._bad(name="gamma", desc='Gamma does a thing → alpha. "do gamma"')
        self.assertTrue(pair_problems([a, self._bad(name="beta", desc='Beta. "do beta"'), stray], [("alpha", "beta")]))
        self.assertEqual(pair_problems([a, self._bad(name="beta", desc='Beta. "do beta"')], [("alpha", "beta")]), [])

    def test_plant_multiline_description_is_flagged(self):
        self.assertTrue(any("single-line" in p for p in entry_problems(self._bad(single_line=False))))


if __name__ == "__main__":
    unittest.main()
