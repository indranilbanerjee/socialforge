---
description: "Check pending approvals and send reminders where overdue. \"who still owes an approval\""
argument-hint: "[--brand <name>] [--send-reminders]"
disable-model-invocation: true
---

# Check Approvals

Show all pending approvals and optionally send overdue reminders. The user starts this command; it is not model-invocable, because `--send-reminders` messages reviewers. Reminders go out only when the user typed `--send-reminders` in this conversation, and then only through the Execution gate below. Without it, this command only reads the status tracker.

## Execution gate

Sending is a side effect other people see. Before any Slack message, email or reminder goes out, show an Execution Summary: who receives it (each recipient or channel), through which connector, which posts, and the exact message text. Send only on an explicit `yes` typed by the user for exactly that summary; any other reply cancels with nothing sent and no status changed. A changed recipient, post list or message is a new summary and a new `yes`. Hosts that ignore `disable-model-invocation` (Codex, for one) still get this gate.

## Output
```
Pending Approvals — AcmeCorp / April 2026
  Internal review: 3 posts (P14, P18, P22) — 2 days pending
  Client review: 5 posts (P01-P05) — sent 3 days ago, reminder due
  CEO approval: 1 post (P01 HERO) — waiting

  --send-reminders to notify overdue reviewers
```
