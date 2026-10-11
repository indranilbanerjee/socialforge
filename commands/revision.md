---
description: "Apply revision feedback to a post and regenerate what changed. \"apply the client's feedback\""
argument-hint: "<post-id> <feedback>"
---

# Revision

Apply specific revision feedback to a post. Regenerates only the affected elements (image, copy, or both).

## Process
1. Load post and current state from status-tracker.json
2. Parse feedback to determine what needs changing (image, copy, or both)
3. Incorporate feedback into regeneration prompt
4. Re-run the affected steps. A changed image or video goes back through `/socialforge:compose-creative`, whose "Quote, then go" section quotes the paid generation and waits for the user's `go` (a revision is a new paid call, even when the first one was approved); changed copy goes through `/socialforge:adapt-copy`, which is free
5. Update revision_history in status-tracker.json
6. Show revised post for approval
7. Max 3 revision cycles per post before escalation
