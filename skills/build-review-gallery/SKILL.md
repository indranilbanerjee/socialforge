---
name: build-review-gallery
description: Build an interactive HTML review gallery with all generated posts for team review.
argument-hint: "--brand <name> --month <YYYY-MM>"
effort: medium
user-invocable: true
---

# /socialforge:build-review-gallery — Review Gallery Builder

Build a self-contained HTML gallery showing every post in the month with its generated visual, metadata, and a copy excerpt.

## Process
1. Load calendar-data.json and status-tracker.json for the brand + month
2. For each post, locate the generated image, video (plus any alternative cut), and copy file
3. Build the gallery HTML — `build_gallery.py` generates the markup inline; it does not read a template file
4. Embed images and videos as base64 data URIs so the file is self-contained
5. Save to `${CLAUDE_PLUGIN_DATA}/socialforge/output/{brand}/{month}/review/gallery.html` (falls back to `~/socialforge-workspace/output/...` when `${CLAUDE_PLUGIN_DATA}` is unset)

## What the Gallery Shows
- Summary bar: total posts, images, videos, and counts per tier (HERO / HUB / HYGIENE)
- Per-post card: visual (video preferred over image), post id, tier badge, status, title, date, platforms, content type, and the first 200 characters of the copy

Review actions — approving, requesting revisions, adding notes — happen conversationally via `/socialforge:manage-reviews`, not inside the gallery. The gallery is a read-only view.

## Timeout & Fallback
- Gallery build: 60-second timeout for 30 posts. Videos too large to embed render as a "Video not embeddable" placeholder.
