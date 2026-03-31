---
name: build-review-gallery
description: Build an interactive HTML review gallery with all generated posts for team review.
argument-hint: "[--brand <name>] [--tier HERO|HUB|HYGIENE]"
effort: medium
user-invocable: true
---

# /sf:build-review-gallery — Review Gallery Builder

Build an interactive HTML gallery showing all generated posts with quality scores, copy, and approval controls.

## Process
1. Load all generated previews and quality scores
2. Populate gallery.html template with post cards
3. Each card shows: preview image, quality score, copy text, compliance status, creative mode
4. Filter by: tier (HERO/HUB/HYGIENE), platform, status
5. Export as self-contained HTML file (all images embedded as base64)
6. Save to `output/{brand}/{month}/review/gallery.html`

## Gallery Features
- Sort by: date, tier priority, quality score
- Filter by: tier, platform, status, creative mode
- Actions per post: approve, flag for revision, add notes
- Bulk actions: approve all HYGIENE, flag all below score X

## Timeout & Fallback
- Gallery build: 60-second timeout for 30 posts. If base64 encoding is too slow, link to image files instead.
