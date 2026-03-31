---
description: Send approved posts to client for review via Slack or email
argument-hint: "[--tier HERO|HUB] [--all-approved]"
---

# Client Review

Send internally-approved posts to the client for review.

## Process
1. Filter posts with status APPROVED_INTERNAL
2. Build review package (gallery link or attached previews)
3. Send via Slack (if connected) or email (if Gmail connected)
4. Update status → PENDING_CLIENT for all sent posts
5. Set reminder timer per approval-chain.json escalation rules
