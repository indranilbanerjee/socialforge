---
description: Apply revision feedback to a post and regenerate affected elements
argument-hint: "<post-id> <feedback>"
---

# Revision

Apply specific revision feedback to a post. Regenerates only the affected elements (image, copy, or both).

## Process
1. Load post and current state from status-tracker.json
2. Parse feedback to determine what needs changing (image, copy, or both)
3. Incorporate feedback into regeneration prompt
4. Re-run affected pipeline steps
5. Update revision_history in status-tracker.json
6. Show revised post for approval
7. Max 3 revision cycles per post before escalation
