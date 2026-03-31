---
description: Generate creative assets for all posts in the current month's calendar
argument-hint: "[--brand <name>] [--week <N>]"
---

# Generate All

Produce images, carousels, copy, and previews for every post in the calendar.

## Process
1. Load calendar-data.json and asset-matches.json
2. For each post (ordered by date):
   - Determine creative mode (ANCHOR_COMPOSE, ENHANCE_EXTEND, STYLE_REFERENCED, PURE_CREATIVE)
   - Generate image(s) via image-compositor agent
   - Render carousel if content_type = carousel
   - Adapt copy for each target platform
   - Run compliance check
   - Generate platform previews
   - Run quality review
3. Show progress: `[12/28] Generating Post P12 — carousel (8 slides) for LinkedIn...`
4. At completion: show summary card with quality scores, issues, and next steps

## Filters
- `--week 2` — Only generate posts for week 2
- `--tier HERO` — Only generate HERO tier posts
- `--platform instagram` — Only generate for Instagram
