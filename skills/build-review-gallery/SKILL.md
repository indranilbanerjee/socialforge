---
name: build-review-gallery
description: "Build the shareable HTML review gallery of every generated post for team or client. \"make me a gallery page\""
argument-hint: "--brand <name> --month <YYYY-MM> [--no-inline-video]"
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

## Step 6 (optional) — Offer a hosted copy for review

The local `gallery.html` is built first, always. It is the fallback and the source of truth; nothing below replaces it.

`build_gallery.py` reports `size_bytes`, `size_mb` and `publishable_as_page` (true only when the file is 15 MB or smaller, a conservative ceiling for a hosted page). After the local file exists:

1. If this session has a tool that publishes an HTML page (for example an artifact or page-publishing tool) and `publishable_as_page` is true, **offer** to publish the gallery as a private page for review. Say in the offer that publishing uploads the month's creative and copy to a hosted service. Publish only on the user's explicit yes, and publish the file at `output`, unchanged.
2. Choose the private option wherever the tool has one. Never say or imply the page is shared with anyone: sharing is a separate step that is the user's to take. Give them the link and stop there.
3. If `publishable_as_page` is false, say so in one line and use the result's `note`: inlined video is what makes a gallery too large. Offer `build_gallery.py --brand <name> --month <YYYY-MM> --no-inline-video`, which links videos by relative path and keeps the file small. A published copy of that build shows images and copy but **cannot play the linked videos** — say that before offering it.
4. If no tool that publishes a page exists, say so in one line and give the local path. Do not suggest a hosting service.

## What the Gallery Shows
- Summary bar: total posts, images, videos, and counts per tier (HERO / HUB / HYGIENE)
- Per-post card: visual (video preferred over image), post id, tier badge, status, title, date, platforms, content type, and the first 200 characters of the copy

Review actions — approving, requesting revisions, adding notes — happen conversationally via `/socialforge:manage-reviews`, not inside the gallery. The gallery is a read-only view.

## Timeout & Fallback
- Gallery build: 60-second timeout for 30 posts. Every video that exists is embedded as base64, however large — there is no size cutoff, and a missing or unreadable video file renders as a "Video file missing or unreadable" placeholder. A gallery with many large videos can therefore be very large: check `size_mb` in the result, and use `--no-inline-video` to link the videos instead.
