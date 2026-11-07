---
description: "Send internally approved posts to the client by Slack or email with reminders; internal pass -> review. \"send these to the client\""
argument-hint: "[--tier HERO|HUB] [--all-approved]"
disable-model-invocation: true
---

# Client Review

Send internally-approved posts to the client for review. The user starts this command; it is not model-invocable.

## Execution gate

Sending is a side effect other people see. Before any Slack message, email or reminder goes out, show an Execution Summary: who receives it (each recipient or channel), through which connector, which posts, and the exact message text. Send only on an explicit `yes` typed by the user for exactly that summary; any other reply cancels with nothing sent and no status changed. A changed recipient, post list or message is a new summary and a new `yes`. Hosts that ignore `disable-model-invocation` (Codex, for one) still get this gate.

## Process
1. Filter posts with status APPROVED_INTERNAL
2. Build review package (gallery link or attached previews)
3. Show the Execution Summary from the Execution gate above and wait for `yes`; then send via Slack (if connected) or email (if Gmail connected)
4. Update status → PENDING_CLIENT for all sent posts
5. Set reminder timer per approval-chain.json escalation rules
