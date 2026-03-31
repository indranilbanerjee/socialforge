---
description: Generate creative for a single post by ID
argument-hint: "<post-id> [--variant b]"
---

# Generate Post

Produce the complete creative package for one post.

## Process
1. Load post from calendar-data.json by ID (e.g., P04)
2. Load matched asset from asset-matches.json
3. Generate image using the assigned creative mode
4. Show generated image to user for approval
5. If approved: adapt copy, run compliance, generate previews
6. If rejected: regenerate with adjusted prompt or different asset
7. Update status-tracker.json

## Variants
`/sf:generate-post P04 --variant b` generates an alternative version for A/B testing.
