---
description: Render multi-slide carousels from HTML templates via Playwright
argument-hint: "[--post <id>] [--all] [--template <type>]"
---

# Render Carousels

Produce carousel slide images from HTML/CSS templates with brand theming.

## Process
1. Load carousel post data from calendar-data.json
2. Select template (tips-listicle, data-story, quote-series, etc.)
3. Inject brand colors, fonts, and content via CSS variables
4. Render each slide to PNG via Playwright
5. Assemble into PDF for LinkedIn document posts
6. Save slides to post folder

## Templates Available
- tips-listicle — Numbered tips with icons
- data-story — Stats and charts progression
- quote-series — Quote cards with attribution
- before-after — Comparison slides
- process-steps — Step-by-step workflow
- product-features — Feature highlights
- team-spotlight — Team member cards
- case-study — Problem/solution/result

## Prerequisites
- Calendar parsed with carousel posts identified
- Playwright installed (auto-installed via /sf:setup)
- Brand config with colors and fonts set
