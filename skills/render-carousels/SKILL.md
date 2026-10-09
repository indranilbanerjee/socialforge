---
name: render-carousels
description: "Render multi-slide carousels from HTML templates into platform-ready images or PDF. \"build the carousel slides\""
argument-hint: "[--post <id>] [--all] [--template <type>]"
effort: high
user-invocable: true
---

# /socialforge:render-carousels — Carousel Renderer

Produce multi-slide carousel images from HTML/CSS templates using Playwright headless rendering.

## Supported Templates

Pass the key to `render_carousel.py --template` (argparse rejects anything outside this list; `--list-templates` prints it).

| Key | Slides | Best For | Template File |
|-----|--------|----------|---------------|
| generic | 8 | General purpose | generic-8slide.html |
| comparison | 10 | Feature comparisons | comparison-10slide.html |
| case-study | 10 | Client success stories | case-study-10slide.html |
| tips | 5 | Quick tips | tips-5slide.html |
| playbook | 8 | Step-by-step playbooks | playbook-8slide.html |
| recap | 6 | Event/month recaps | recap-6slide.html |
| data | 6 | Data-driven infographics | data-infographic-6slide.html |
| quote | 1 | Single quote cards | quote-card-single.html |

## Process

1. Select template based on post's `carousel_type`
2. For each slide:
   - Inject content (title, body, data points, statistics)
   - Apply brand colors via CSS variables (--brand-primary, --brand-secondary, etc.)
   - Apply brand fonts
   - If slide needs background image: compose an existing brand asset (free), or generate one via image-compositor: a generated background is a paid call, so it needs an approved quote first (compose-creative, "Quote, then go"), and the compositor refuses without one
3. Render each slide via Playwright (headless Chromium → PNG, 1080x1080)
4. Show first and last slide to user for approval
5. Compile all slides into PDF (for LinkedIn document upload)
6. Resize slides for other platforms if needed

## Rules
- First slide = hook/title with brand identity
- Last slide = CTA with brand logo and contact info
- Max text per slide: 40 words (LinkedIn) | 25 words (Instagram)
- All slides use brand fonts and colors from brand-config.json
- Slide dimensions: 1080x1080 default (configurable per brand)

## Scripts Used
- render_carousel.py — Playwright HTML→PNG rendering

Prerequisites (calendar, Playwright, brand colors/fonts) and the exact files a render writes: read [prerequisites-and-output.md](prerequisites-and-output.md) when a render fails before the first slide or the user asks what was produced.

## Timeout & Fallback
- Per-slide render: 15-second timeout. If Playwright hangs, retry without custom fonts.
- Full carousel: 3-minute timeout for 10 slides.
- If Playwright unavailable: flag for manual rendering, save populated HTML for export.
