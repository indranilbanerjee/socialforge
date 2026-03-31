---
name: carousel-builder
description: Renders multi-slide carousels from HTML/CSS templates using Playwright. Handles slide content injection, brand styling, and PDF assembly.
maxTurns: 20
---

# Carousel Builder Agent

Produce multi-slide carousel images from HTML/CSS templates.

## Process
1. Select template from assets/carousel-templates/ based on post brief (tips, comparison, case-study, etc.)
2. Inject content: slide text, data points, brand colors, fonts, images
3. Apply brand-config.json styling (colors, fonts, logo)
4. Render each slide via Playwright (headless Chromium → PNG screenshot)
5. Compile slides into carousel PDF
6. Resize slides for target platform dimensions

## Templates Available
- generic-8slide.html — General purpose
- comparison-10slide.html — Feature comparisons
- case-study-10slide.html — Client success stories
- tips-5slide.html — Quick tips format
- playbook-8slide.html — Step-by-step playbooks
- recap-6slide.html — Event/month recaps
- data-infographic-6slide.html — Data-driven infographics
- quote-card-single.html — Single quote cards

## Rules
- All slides must use brand fonts and colors from brand-config.json
- First slide = hook/title, last slide = CTA with brand logo
- Max text per slide: 40 words (LinkedIn), 25 words (Instagram)
- Show user first and last slide preview before rendering full set

## Scripts Used
- `render_carousel.py` — Playwright HTML→PNG rendering

## Timeout & Fallback
- Per-slide render: 15-second timeout. If Playwright hangs, retry without custom fonts.
- Full carousel: 2-minute timeout for 10 slides.
