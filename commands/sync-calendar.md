---
description: Re-sync the calendar from its source (Notion, Drive, or file)
argument-hint: "[--brand <name>] [--source <path-or-url>]"
---

# Sync Calendar

Re-read the calendar source to pick up changes (new posts, modified briefs, removed posts).

## Process
1. Re-parse the calendar source (same format as original)
2. Compare with current calendar-data.json
3. Show diff: new posts, modified posts, removed posts
4. Confirm changes with user before applying
5. Update calendar-data.json
6. Re-run asset matching for new/modified posts only
