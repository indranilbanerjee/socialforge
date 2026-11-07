"""Side-effect skills carry a typed-yes gate; the ones that send, publish or deliver are started by the user only.

Two rules, and why each exists.

1. Every skill or command that changes something outside the conversation carries an `## Execution gate` block: a
   scope or preview first, an explicit typed `yes`, anything else cancels. Hosts that ignore `disable-model-invocation`
   (Codex) make that gate the real safety layer on every platform.

2. (1.31.0) A skill or command that SENDS, PUBLISHES or DELIVERS is not model-invocable: `disable-model-invocation:
   true`. Before 1.31.0 `commands/finalize.md` was hidden but `skills/finalize-month/SKILL.md`, the skill it wraps, was
   model-invocable, so injected text in a calendar, a brief or a fetched page could get the model to start the delivery
   (Drive upload, completion message, Postiz hand-off) on its own, and `client-review` / `check-approvals` could message a
   client with no gate at all. The cost of hiding: a plain request such as "package the month" no longer matches a skill,
   so orchestrators (full-pipeline) tell the user which command to type instead of invoking it. The paid generation
   skills (compose-creative, generate-video, full-pipeline, index-assets, edit-image) stay invocable: every paid call
   already waits for a quote and a typed `go`, and the scripts refuse a provider that was not quoted.

Which files must be user-only is not a hand-kept list: SEND_MARKERS finds them by what their text says they do (a
Postiz hand-off, `--force`, sending reminders, sending to a client or over Slack/email, a Drive upload, publishing now),
so a new skill that sends is caught the day it is written. Naming the word "finalize" is deliberately NOT a marker: an
orchestrator that tells the user to run `/socialforge:finalize` must stay invocable.

digital-marketing-pro/tests/test_execution_gates.py holds the DMP side of the same rules. Stdlib only.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
COMMANDS = ROOT / "commands"

# Skills that change something local (write files) and stay model-invocable behind their gate.
SIDE_EFFECT_SKILLS = frozenset({"create-previews"})

# Skills and commands that send, publish or deliver: user-started only, and still gated (Codex ignores the flag).
USER_ONLY_SKILLS = frozenset({"finalize-month", "manage-reviews"})
USER_ONLY_COMMANDS = frozenset({"client-review", "check-approvals"})

# Hidden wrapper command -> the skill it hands over to.
WRAPPER_TARGETS = {
    "finalize": "finalize-month",
    "preview-batch": "create-previews",
    "brand-setup": "brand-manager",
}

# Skills allowed to stay hidden besides the user-only ones (internal steps whose commands are the visible entries).
INTERNAL_HIDDEN_SKILLS = frozenset({"assemble-document"})

SEND_MARKERS = {
    "a Postiz hand-off": re.compile(r"(?i)\bpostiz\b"),
    "--force": re.compile(r"--force\b"),
    "sending reminders": re.compile(r"(?i)--send-reminders|\bsend(?:s|ing)? (?:overdue )?reminders?\b"),
    "sending to a client or over Slack/email": re.compile(
        r"(?i)\bsend(?:s|ing)?\b[^.\n]{0,80}\b(?:to (?:the )?client|via slack|by slack|via email|by email|"
        r"slack/email|slack or email|gmail)\b"),
    "a Drive upload": re.compile(r"(?i)\bupload(?:s|ing)?\b[^.\n]{0,30}\bdrive\b"),
    "publishing now": re.compile(r"(?i)\bpublish(?:es|ing)? (?:immediately|now)\b"),
}

FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.S)
GATE_RE = re.compile(r"^## Execution gate\b[^\n]*\n(.*?)(?=^## |\Z)", re.M | re.S)


def frontmatter(text: str) -> str:
    m = FM_RE.match(text)
    return m.group(1) if m else ""


def body(text: str) -> str:
    m = FM_RE.match(text)
    return text[m.end():] if m else text


def flag(text: str) -> str | None:
    m = re.search(r"^disable-model-invocation:\s*(true|false)\s*$", frontmatter(text), re.M)
    return m.group(1) if m else None


def send_markers(text: str) -> list[str]:
    b = body(text) + "\n" + (re.search(r"^argument-hint:.*$", frontmatter(text), re.M) or [""])[0]
    return [name for name, rx in SEND_MARKERS.items() if rx.search(b)]


def gate_body_problems(text: str) -> list[str]:
    m = GATE_RE.search(text.replace("\r\n", "\n"))
    if not m:
        return ["no `## Execution gate` block"]
    out = []
    if "`yes`" not in m.group(1):
        out.append("gate block never asks for a typed `yes`")
    if "cancel" not in m.group(1).lower():
        out.append("gate block never says that any other reply cancels")
    return out


def gate_problems(text: str) -> list[str]:
    """A model-invocable side-effect skill: visible, and gated."""
    out = []
    if flag(text) != "false":
        out.append("frontmatter does not say `disable-model-invocation: false`")
    return out + gate_body_problems(text)


def user_only_problems(text: str) -> list[str]:
    """A skill or command that sends, publishes or delivers: hidden from the model, and still gated."""
    out = []
    if flag(text) != "true":
        out.append("frontmatter does not say `disable-model-invocation: true`")
    return out + gate_body_problems(text)


def wrapper_problems(commands: dict[str, str], skills: dict[str, str], targets: dict[str, str],
                     user_only_commands=frozenset(), user_only_skills=frozenset()) -> list[str]:
    """commands/skills: name -> file text."""
    out = []
    for name, text in commands.items():
        if flag(text) == "true" and name not in targets and name not in user_only_commands:
            out.append(f"hidden command {name} has no registered target skill")
    for cmd, skill in targets.items():
        if cmd not in commands:
            out.append(f"registered wrapper {cmd} does not exist")
        elif skill not in skills:
            out.append(f"wrapper {cmd} points at missing skill {skill}")
        elif flag(skills[skill]) == "true":
            if skill not in user_only_skills:
                out.append(f"wrapper {cmd} is hidden and so is its target {skill}: nothing is left to route to")
            elif f"skills/{skill}/SKILL.md" not in commands[cmd]:
                out.append(f"wrapper {cmd} wraps the user-only skill {skill} but never says to read "
                           f"skills/{skill}/SKILL.md (the Skill tool refuses a hidden skill)")
    return out


def hidden_skill_problems(skills: dict[str, str], allowed) -> list[str]:
    return [f"skill {n} is hidden but is not an allowed internal or user-only step"
            for n, t in sorted(skills.items()) if flag(t) == "true" and n not in allowed]


def _load(dirpath: Path, pattern: str, name_of) -> dict[str, str]:
    out = {}
    for p in sorted(dirpath.glob(pattern)):
        out[name_of(p)] = p.read_text(encoding="utf-8", errors="replace")
    return out


class TestExecutionGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skills = _load(SKILLS, "*/SKILL.md", lambda p: p.parent.name)
        cls.commands = _load(COMMANDS, "*.md", lambda p: p.stem)

    def test_named_skills_and_commands_exist(self):
        self.assertEqual(sorted(n for n in SIDE_EFFECT_SKILLS | USER_ONLY_SKILLS if n not in self.skills), [])
        self.assertEqual(sorted(n for n in USER_ONLY_COMMANDS if n not in self.commands), [])

    def test_every_local_side_effect_skill_is_invocable_and_has_its_gate(self):
        bad = {n: p for n in sorted(SIDE_EFFECT_SKILLS) if (p := gate_problems(self.skills[n]))}
        self.assertEqual(bad, {})

    def test_every_send_or_deliver_skill_and_command_is_user_only_and_gated(self):
        bad = {n: p for n in sorted(USER_ONLY_SKILLS) if (p := user_only_problems(self.skills[n]))}
        bad.update({f"commands/{n}": p for n in sorted(USER_ONLY_COMMANDS) if (p := user_only_problems(self.commands[n]))})
        self.assertEqual(bad, {})

    def test_whatever_names_a_send_is_not_model_invocable(self):
        """The scan, not the lists above, decides: any skill or command whose text sends, publishes or delivers."""
        found = {}
        for kind, files in (("skills", self.skills), ("commands", self.commands)):
            for name, text in files.items():
                markers = send_markers(text)
                if markers and flag(text) != "true":
                    found[f"{kind}/{name}"] = markers
        self.assertEqual(found, {}, "these send, publish or deliver but the model can still start them on its own")
        flagged = {n for n, t in self.skills.items() if send_markers(t)}
        self.assertIn("finalize-month", flagged, "the scan no longer sees finalize-month: the markers are vacuous")

    def test_the_finalize_command_and_skill_agree(self):
        self.assertEqual((flag(self.commands["finalize"]), flag(self.skills["finalize-month"])), ("true", "true"))
        self.assertIn("skills/finalize-month/SKILL.md", self.commands["finalize"])
        self.assertIn("`yes`", self.commands["finalize"])

    def test_the_pipeline_hands_finalizing_to_the_user(self):
        text = self.skills["full-pipeline"]
        self.assertIn("Run `/socialforge:finalize`", text)
        self.assertRegex(text, r"never invokes the finalize skill")
        self.assertNotRegex(text, r"(?i)auto-?finali[sz]e")

    def test_every_hidden_wrapper_points_at_a_reachable_skill(self):
        self.assertEqual(wrapper_problems(self.commands, self.skills, WRAPPER_TARGETS,
                                          USER_ONLY_COMMANDS, USER_ONLY_SKILLS), [])

    def test_no_skill_is_hidden_unless_it_is_an_internal_or_user_only_step(self):
        self.assertEqual(hidden_skill_problems(self.skills, INTERNAL_HIDDEN_SKILLS | USER_ONLY_SKILLS), [])

    # ── planted failures ────────────────────────────────────────────────

    GOOD_SKILL = ("---\nname: x\ndisable-model-invocation: false\n---\n\n# x\n\n## Execution gate\n\n"
                  "Show the preview and wait for `yes`; any other reply cancels.\n\n## Process\n")

    def test_plant_gate_missing(self):
        t = self.GOOD_SKILL.replace("## Execution gate", "## Notes")
        self.assertIn("no `## Execution gate` block", gate_problems(t))
        self.assertIn("no `## Execution gate` block", user_only_problems(t.replace(": false", ": true")))

    def test_plant_hidden_again(self):
        t = self.GOOD_SKILL.replace("disable-model-invocation: false", "disable-model-invocation: true")
        self.assertTrue(any("disable-model-invocation: false" in p for p in gate_problems(t)))
        self.assertTrue(gate_problems(self.GOOD_SKILL.replace("disable-model-invocation: false\n", "")))

    def test_plant_a_sending_skill_left_invocable(self):
        for line in ("Hand the batch to Postiz.", "Finalize anyway with --force.", "Send the posts to the client by email.",
                     "Upload the folder to Google Drive.", "Then send overdue reminders.", "Publish immediately if asked."):
            with self.subTest(line=line):
                t = self.GOOD_SKILL.replace("## Process\n", "## Process\n" + line + "\n")
                self.assertTrue(send_markers(t))
                self.assertTrue(user_only_problems(t))
                self.assertEqual(user_only_problems(t.replace(": false", ": true")), [])
        self.assertEqual(send_markers(self.GOOD_SKILL + "\nWhen done, run `/socialforge:finalize` to package the month.\n"), [])
        self.assertEqual(send_markers(self.GOOD_SKILL + "\nWith --provider auto, a missing frame sends clips of 8 s.\n"), [])

    def test_plant_gate_without_yes_or_cancel(self):
        no_yes = self.GOOD_SKILL.replace("`yes`", "a go-ahead")
        no_cancel = self.GOOD_SKILL.replace("; any other reply cancels", "")
        self.assertTrue(any("typed `yes`" in p for p in gate_problems(no_yes)))
        self.assertTrue(any("cancels" in p for p in gate_problems(no_cancel)))
        self.assertEqual(gate_problems(self.GOOD_SKILL), [])

    def test_plant_wrapper_target_hidden_or_missing(self):
        hidden = "---\nname: t\ndisable-model-invocation: true\n---\n"
        visible = "---\nname: t\ndisable-model-invocation: false\n---\n"
        cmd = "---\ndescription: d\ndisable-model-invocation: true\n---\n"
        reads = cmd + "Read skills/t/SKILL.md and follow it.\n"
        self.assertEqual(wrapper_problems({"w": cmd}, {"t": visible}, {"w": "t"}), [])
        self.assertTrue(wrapper_problems({"w": cmd}, {"t": hidden}, {"w": "t"}))      # target hidden too
        self.assertTrue(wrapper_problems({"w": cmd}, {"t": hidden}, {"w": "t"}, user_only_skills={"t"}))  # never says read
        self.assertEqual(wrapper_problems({"w": reads}, {"t": hidden}, {"w": "t"}, user_only_skills={"t"}), [])
        self.assertTrue(wrapper_problems({"w": cmd}, {}, {"w": "t"}))                  # target missing
        self.assertTrue(wrapper_problems({"w": cmd}, {"t": visible}, {}))              # unregistered hidden command
        self.assertEqual(wrapper_problems({"w": cmd}, {}, {}, user_only_commands={"w"}), [])
        self.assertTrue(wrapper_problems({}, {"t": visible}, {"w": "t"}))              # registered wrapper missing

    def test_plant_unexpected_hidden_skill(self):
        hidden = "---\nname: s\ndisable-model-invocation: true\n---\n"
        self.assertTrue(hidden_skill_problems({"s": hidden}, frozenset()))
        self.assertEqual(hidden_skill_problems({"s": hidden}, frozenset({"s"})), [])


class TestNoApprovalFreePath(unittest.TestCase):
    """1.31.0 (#10): reference docs described an `auto_publish` block and HYGIENE posts finalizing without sign-off. No
    code implemented it, but a model reads docs as instructions and the approval chain is a file the model writes. Every
    shipped doc must either not mention it or say it is not supported."""
    PATTERN = re.compile(r"(?i)auto[-_ ]?publish|auto[-_]finali[sz]|\bauto-send|auto-approved by hooks|"
                         r"finali[sz]ed without (?:client )?sign-off")
    DISCLAIMS = re.compile(r"(?i)not supported|is ignored|\bignored\b|never|nothing is finali[sz]ed")
    SKIP = {"CHANGELOG.md"}

    @classmethod
    def lines(cls):
        for p in sorted(ROOT.rglob("*")):
            rel = p.relative_to(ROOT).as_posix()
            if not p.is_file() or p.suffix not in {".md", ".json", ".py", ".yaml", ".js"}:
                continue
            if rel.split("/")[0] in {".git", "tests"} or p.name in cls.SKIP:
                continue
            for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                yield rel, n, line

    def test_no_doc_describes_an_approval_free_path(self):
        bad = [f"{rel}:{n}" for rel, n, line in self.lines()
               if self.PATTERN.search(line) and not self.DISCLAIMS.search(line)]
        self.assertEqual(bad, [])

    def test_plant_the_old_passages_are_flagged(self):
        for old in ("| `auto_publish` | object | Auto-publish conditions (see below) |",
                    "- Auto-finalize HYGIENE tier after N days if configured",
                    "the post can be finalized without client sign-off, with an audit note appended."):
            with self.subTest(old=old):
                self.assertTrue(self.PATTERN.search(old) and not self.DISCLAIMS.search(old))


if __name__ == "__main__":
    unittest.main()
