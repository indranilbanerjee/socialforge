---
description: Edit an existing post's copy, visual direction, or metadata
argument-hint: "<post-id> [--copy] [--visual] [--meta]"
---

# Edit Post

Modify a generated post's content. Targets: copy text, visual direction, or metadata (date, platform, tier).

## Process
1. Load post from calendar-data.json by ID
2. Show current state (image, copy, metadata)
3. Accept edits from user
4. If copy changed: re-run adapt-copy for affected platforms
5. If visual changed: re-run compose-creative for this post
6. If metadata changed: update calendar-data.json + status-tracker.json
7. Re-run compliance check on edited content
