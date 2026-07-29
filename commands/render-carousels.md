---
description: Render multi-slide carousels from HTML templates via Playwright
argument-hint: "[--post <id>] [--all] [--template <type>]"
---

# Render Carousels

Produce carousel slide images from HTML/CSS templates with brand theming.

## Process
1. Load carousel post data from calendar-data.json
2. Select template key (generic, comparison, case-study, tips, etc.)
3. Inject brand colors, fonts, and content via CSS variables
4. Render each slide to PNG via Playwright
5. Assemble into PDF for LinkedIn document posts
6. Save slides to post folder

## Templates Available

These are the keys accepted by `render_carousel.py --template`:

- generic — General purpose (8 slides)
- comparison — Feature comparisons (10 slides)
- case-study — Client success stories (10 slides)
- tips — Quick tips (5 slides)
- playbook — Step-by-step playbooks (8 slides)
- recap — Event/month recaps (6 slides)
- data — Data-driven infographics (6 slides)
- quote — Single quote cards (1 slide)

## Prerequisites
- Calendar parsed with carousel posts identified
- Playwright installed (auto-installed via /socialforge:setup)
- Brand config with colors and fonts set
