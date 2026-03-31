# Carousel Templates Guide

How SocialForge builds carousels — template selection, brand theming via CSS variables, slide content structure, custom templates, and the Playwright rendering pipeline.

## Template Architecture

Each carousel template is an HTML file with CSS custom properties (variables) that get injected with brand values at render time. Templates live in:

```
skills/carousel-builder/templates/
```

## Available Templates

| Template | Slides | Best For |
|----------|--------|----------|
| `tips-listicle` | 5-7 | Numbered tips, how-to lists |
| `data-story` | 4-6 | Statistics, charts, data narratives |
| `before-after` | 4 | Transformation stories, case studies |
| `quote-series` | 3-5 | Customer quotes, thought leadership |
| `process-steps` | 4-6 | Step-by-step guides, workflows |
| `myth-vs-fact` | 5-7 | Myth-busting, misconception correction |
| `product-features` | 4-6 | Feature highlights, product showcases |

## Template Selection Logic

The template is chosen based on `carousel_details.template` in calendar-data.json. If not specified, the pipeline selects automatically:

1. Content contains numbered items → `tips-listicle`
2. Content contains statistics → `data-story`
3. Content contrasts two states → `before-after`
4. Content contains quotes → `quote-series`
5. Content describes a process → `process-steps`
6. Default fallback → `tips-listicle`

## CSS Variable Injection

Templates use these CSS custom properties, injected from brand-config.json:

```css
:root {
  --brand-primary: #1A73E8;
  --brand-secondary: #34A853;
  --brand-accent: #FBBC04;
  --brand-bg: #FFFFFF;
  --brand-text: #202124;
  --brand-text-light: #FFFFFF;
  --font-heading: 'Inter', sans-serif;
  --font-body: 'Inter', sans-serif;
  --logo-url: url('logos/logo-icon.png');
}
```

Templates reference these variables exclusively — no hardcoded colors or fonts.

## Slide Content Structure

Each slide in `carousel_details.slides` contains:

```json
{
  "headline": "Short punchy headline",
  "body": "1-2 sentences of supporting content",
  "visual_note": "Optional note for background image or icon",
  "stat": "42%",
  "stat_label": "of marketers agree"
}
```

Not all fields are used by every template. `stat` and `stat_label` are specific to `data-story`.

### Slide Types

| Slide Position | Purpose | Content |
|----------------|---------|---------|
| First (cover) | Hook + title | Headline only, brand gradient background |
| Middle (content) | Core information | Headline + body, optional stat |
| Last (CTA) | Call to action | CTA text + handle/website, brand gradient |

## Custom Template Creation

To create a custom template:

1. Create an HTML file in the templates directory.
2. Use only CSS custom properties for colors and fonts (see list above).
3. Structure with a `.slide` container per slide.
4. Include `{{HEADLINE}}`, `{{BODY}}`, `{{STAT}}` placeholders — the renderer replaces these.
5. Include a `{{LOGO}}` placeholder for brand logo placement.
6. Set dimensions to 1080x1080 (LinkedIn/Instagram carousel standard).

### Template HTML Structure

```html
<div class="slide" style="width: 1080px; height: 1080px;">
  <div class="logo">{{LOGO}}</div>
  <h1>{{HEADLINE}}</h1>
  <p>{{BODY}}</p>
  <div class="footer">{{BRAND_NAME}}</div>
</div>
```

## Playwright Rendering Pipeline

Carousels are rendered to images using Playwright (headless Chromium):

1. **Inject brand variables** — Replace CSS custom properties with brand-config values.
2. **Inject slide content** — Replace `{{HEADLINE}}`, `{{BODY}}`, etc., with content from `carousel_details.slides`.
3. **Load in headless browser** — Playwright launches Chromium, loads the HTML.
4. **Screenshot each slide** — Each `.slide` element is captured at 1080x1080 (2x for retina = 2160x2160, then downscaled).
5. **Export** — PNG files saved as `slide-01.png`, `slide-02.png`, etc.
6. **Assemble** — Optionally combine into a PDF (LinkedIn document format) or keep as individual images.

### Playwright Requirements

- Playwright must be installed: `pip install playwright && playwright install chromium`
- Fonts must be installed on the system or loaded via `@font-face` in the template.
- Rendering timeout: 10 seconds per slide (increase for complex templates).

## Quality Checks

- All slides render at correct dimensions (1080x1080).
- Text does not overflow slide boundaries.
- Brand colors match config (no template defaults leaking through).
- Logo is visible on every slide.
- Font rendering is consistent across all slides.
- Cover slide has enough visual weight to stop the scroll.
