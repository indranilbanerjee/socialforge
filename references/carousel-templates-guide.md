# Carousel Templates Guide

How SocialForge builds carousels — template selection, brand theming via placeholder substitution, slide content structure, custom templates, and the Playwright rendering pipeline.

`scripts/render_carousel.py` is the renderer and the source of truth for everything below.

## Template Architecture

Each carousel template is a standalone HTML file. Brand values and per-slide content are injected as `{{...}}` placeholders by plain string substitution at render time. Templates ship with the plugin at:

```
assets/carousel-templates/
```

A brand can override any template by dropping a file with the **same filename** into its workspace:

```
${CLAUDE_PLUGIN_DATA}/socialforge/brands/<brand-slug>/carousel-templates/<template-file>.html
# fallback when CLAUDE_PLUGIN_DATA is unset:
~/socialforge-workspace/brands/<brand-slug>/carousel-templates/<template-file>.html
```

If the brand override exists it wins; otherwise the shipped template is used.

## Available Templates

The eight keys below are the complete set — they are the `--template` choices in `render_carousel.py` and the keys of its `TEMPLATE_MAP`. Run `python3 scripts/render_carousel.py --list-templates` to print the mapping.

| Key | File | Design slide count | Best For |
|-----|------|--------------------|----------|
| `generic` | `generic-8slide.html` | 8 | Default narrative carousel, any topic |
| `comparison` | `comparison-10slide.html` | 10 | Two-column contrasts, this-vs-that, myth vs fact |
| `case-study` | `case-study-10slide.html` | 10 | Customer stories with a headline metric |
| `tips` | `tips-5slide.html` | 5 | Numbered tips, how-to lists |
| `playbook` | `playbook-8slide.html` | 8 | Step-by-step guides, workflows |
| `recap` | `recap-6slide.html` | 6 | Event recaps, month-in-review, dated highlights |
| `data` | `data-infographic-6slide.html` | 6 | Statistics with sources, data narratives |
| `quote` | `quote-card-single.html` | 1 | Single quote card, thought leadership pull-quote |

The slide count in the filename is the design intent, not an enforced limit. The renderer emits one PNG per entry in the slides JSON array, so the array length determines how many slides you get.

## Template Selection Logic

The template is chosen from `carousel_details.template` in calendar-data.json. If not specified, the pipeline selects:

1. Content is a single pull-quote → `quote`
2. Content contrasts two states or options → `comparison`
3. Content leads with a customer outcome + metric → `case-study`
4. Content is numbered tips → `tips`
5. Content is an ordered process → `playbook`
6. Content is dated highlights / a recap → `recap`
7. Content is statistics with sources → `data`
8. Default fallback → `generic`

## Brand Variable Injection

`inject_brand_vars()` reads the brand's `brand-config.json` from the workspace and substitutes these eight placeholders. Values shown are the fallbacks used when the field is absent from the config.

| Placeholder | brand-config.json source | Fallback |
|-------------|--------------------------|----------|
| `{{brand_primary}}` | `colors.primary` | `#0066CC` |
| `{{brand_secondary}}` | `colors.secondary` | `#FF6600` |
| `{{brand_accent}}` | `colors.accent` | `#00CC66` |
| `{{brand_bg_light}}` | `colors.background_light` | `#FFFFFF` |
| `{{brand_bg_dark}}` | `colors.background_dark` | `#1A1A1A` |
| `{{brand_text}}` | `colors.text_primary` | `#333333` |
| `{{font_heading}}` | `fonts.heading` | `Montserrat-Bold` |
| `{{font_body}}` | `fonts.body` | `OpenSans-Regular` |

The shipped templates also carry a `{{brand_name}}` placeholder in the footer/logo slot. It is **not** currently injected by `render_carousel.py` — pass the brand name as a per-slide field (`{{slide_brand_name}}`) if you need it filled, or hardcode it in a brand override template.

### CSS custom properties

Templates bind the injected values to CSS custom properties in `:root`, then reference those variables throughout — no hardcoded colors or fonts in the rules:

```css
:root {
  --brand-primary: {{brand_primary}};
  --brand-secondary: {{brand_secondary}};
  --brand-accent: {{brand_accent}};
  --brand-bg-light: {{brand_bg_light}};
  --brand-bg-dark: {{brand_bg_dark}};
  --brand-text: {{brand_text}};
  --font-heading: '{{font_heading}}', 'Montserrat', sans-serif;
  --font-body: '{{font_body}}', 'Open Sans', sans-serif;
}
```

That is the whole injected set. There is no logo-image variable — the logo slot is a text element.

## Slide Content Structure

`--slides` points at a JSON file containing an **array of slide objects**. For each slide, every key `k` is substituted into the placeholder `{{slide_k}}`. Any placeholder with no matching key is left in the output verbatim, so supply every field the template uses.

Per-slide keys by template:

| Template | Slide keys |
|----------|-----------|
| `generic` | `number`, `title`, `body` |
| `comparison` | `number`, `title`, `left_title`, `left_body`, `right_title`, `right_body` |
| `case-study` | `number`, `metric`, `metric_label`, `title`, `body`, `client` |
| `tips` | `number`, `tip_number`, `title`, `body` |
| `playbook` | `number`, `step`, `title`, `body` |
| `recap` | `number`, `date`, `highlight`, `title`, `body` |
| `data` | `number`, `stat`, `stat_unit`, `title`, `body`, `source` |
| `quote` | `quote`, `author`, `author_title` |

```json
[
  { "number": "1/5", "tip_number": "01", "title": "Short punchy headline", "body": "1-2 sentences of supporting content" },
  { "number": "2/5", "tip_number": "02", "title": "Next tip", "body": "..." }
]
```

### Slide Types

| Slide Position | Purpose | Content |
|----------------|---------|---------|
| First (cover) | Hook + title | Headline only, brand gradient background |
| Middle (content) | Core information | Headline + body, plus the template's accent field (stat, step, metric…) |
| Last (CTA) | Call to action | CTA text + handle/website, brand gradient |

## Custom Template Creation

To create a custom template:

1. Add an HTML file to `assets/carousel-templates/`, or to the brand's `carousel-templates/` override directory using an existing filename.
2. Declare the eight brand placeholders in `:root` as CSS custom properties (see list above) and reference only those variables for colors and fonts.
3. Set `body` (or the slide container) to 1080x1080 — the renderer screenshots the viewport, not a `.slide` selector.
4. Use `{{slide_<key>}}` placeholders for content. Choose your own key names; they just have to match the keys in the slides JSON.
5. Adding a **new** key (not just a new file for an existing key) also requires adding it to `TEMPLATE_MAP` in `scripts/render_carousel.py`.

### Template HTML Structure

```html
<body>
  <div class="slide-number">{{slide_number}}</div>
  <h1>{{slide_title}}</h1>
  <div class="accent-line"></div>
  <p>{{slide_body}}</p>
  <div class="logo">{{brand_name}}</div>
</body>
```

## Playwright Rendering Pipeline

Carousels are rendered to images using Playwright (headless Chromium):

1. **Resolve template** — brand override if present, otherwise the shipped file for the requested key.
2. **Inject brand variables** — replace the eight `{{brand_*}}` / `{{font_*}}` placeholders with brand-config values.
3. **Inject slide content** — per slide, replace `{{slide_<key>}}` with the slide object's values.
4. **Load in headless browser** — `page.set_content()` at the requested viewport (default 1080x1080, override with `--width` / `--height`).
5. **Screenshot each slide** — viewport screenshot (`full_page=False`) saved as `slide-01.png`, `slide-02.png`, …
6. **Assemble** — Pillow combines the PNGs into `carousel.pdf` at 150 dpi (LinkedIn document format). If Pillow is unavailable the PDF is skipped and the PNGs are still returned.

### Playwright Requirements

- Playwright must be installed: `pip install playwright && playwright install chromium`
- Fonts must be installed on the system or loaded via `@font-face` in the template — the injected font names are resolved by the browser, not bundled.
- Rendering timeout: 10 seconds per slide (increase for complex templates).

## Quality Checks

- All slides render at correct dimensions (matching `--width` / `--height`).
- Text does not overflow slide boundaries.
- Brand colors match config (no template fallback colors leaking through — a `#0066CC` primary usually means the config was missing).
- No unsubstituted `{{...}}` placeholders visible in the rendered PNGs.
- Font rendering is consistent across all slides.
- Cover slide has enough visual weight to stop the scroll.
