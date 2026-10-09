---
description: "Finalize the month and package approved content for delivery. \"close out the month\""
argument-hint: "[--brand <name>] [--force]"
disable-model-invocation: true
---

# Finalize

Package all approved content into the delivery folder structure. Runs /socialforge:finalize-month skill.

## Pre-Check
- All posts must be FINAL status (or --force to include unapproved)
- Calendar document must be assembled
- All compliance checks passed

## Output
Organized FINAL/ folder on disk; optional Drive upload only if a Drive MCP has been opted into.
