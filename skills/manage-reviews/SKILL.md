---
name: manage-reviews
description: Handle approval workflows — internal review, client review, CEO approval, revision requests.
argument-hint: "[--post <id>] [--approve] [--revise] [--client-send]"
effort: medium
user-invocable: true
disable-model-invocation: true
---

# /sf:manage-reviews — Review & Approval Manager

Manage the multi-tier approval workflow per brand's approval-chain.json.

## Approval Tiers
- **HERO content**: Internal review → Client approval → CEO approval (if configured)
- **HUB content**: Internal review → Client approval (optional)
- **HYGIENE content**: Internal review only (auto-approvable if configured)

## Actions
- `/sf:manage-reviews --approve P04` — Approve post P04 at current tier
- `/sf:manage-reviews --revise P04 "Make the background warmer"` — Request revision with feedback
- `/sf:manage-reviews --client-send` — Send all internally-approved posts to client review
- `/sf:manage-reviews --check` — Check pending approvals and send reminders

## State Transitions
PENDING_REVIEW → APPROVED_INTERNAL → PENDING_CLIENT → APPROVED_CLIENT → PENDING_CEO → FINAL

## Rules
- FINAL status is write-protected — cannot be modified after finalization
- Revision requests re-enter the generation pipeline with specific feedback
- Max 3 revision cycles per HERO post before escalation
- Reminders sent via Slack/email after N days (per escalation_rules)
