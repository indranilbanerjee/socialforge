---
description: "Finalize the month and package approved content for delivery. \"close out the month\""
argument-hint: "[--brand <name>] [--force]"
disable-model-invocation: true
---

# Finalize

Package all approved content into the delivery folder structure. The user typed this command, so read this plugin's `skills/finalize-month/SKILL.md` (the `skills/` folder next to `commands/`) and follow it exactly, including its Step 0 delivery audit, its Execution gate (an explicit `yes` before anything is written or sent) and its `--force` rule. That skill is not model-invocable, so the Skill tool refuses it; reading it is the intended path from this command.

## Pre-Check
- All posts must be FINAL status (or --force to include unapproved)
- Calendar document must be assembled
- All compliance checks passed

## Output
Organized FINAL/ folder on disk; optional Drive upload only if a Drive MCP has been opted into.
