# Brand Config Schema Reference

JSON schema for `brand-config.json` — the core brand identity file loaded by `/sf:brand-setup`.

## Location

```
${CLAUDE_PLUGIN_DATA}/socialforge/brands/<brand-slug>/brand-config.json
```

Falls back to `~/socialforge-workspace/brands/<brand-slug>/brand-config.json` when `CLAUDE_PLUGIN_DATA` is not set.

## Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `brand_name` | string | Yes | Display name of the brand |
| `brand_slug` | string | Yes | Kebab-case identifier used in file paths and references |
| `tagline` | string | No | Brand tagline or slogan |
| `industry` | string | Yes | Industry vertical (e.g., "fintech", "saas", "ecommerce") |
| `website` | string | No | Primary website URL |
| `logo_files` | object | No | Paths to logo variants (see below) |
| `colors` | object | Yes | Brand color palette (see below) |
| `fonts` | object | No | Typography definitions (see below) |
| `visual_style` | string | No | High-level visual direction (e.g., "minimal", "bold", "corporate") |
| `image_rules` | object | No | Constraints for image usage (see below) |
| `logo_overlay` | object | No | Logo placement rules for composited images (see below) |
| `social_profiles` | object | No | Platform handle mapping (see below) |
| `languages` | array | No | Supported languages, first is primary (e.g., `["en", "es"]`) |
| `brand_hashtags` | array | No | Default hashtags appended to social posts |

## `logo_files`

```json
{
  "primary": "logos/logo-full.png",
  "icon": "logos/logo-icon.png",
  "dark_bg": "logos/logo-white.png",
  "light_bg": "logos/logo-dark.png"
}
```

All paths are relative to the brand directory.

## `colors`

| Sub-field | Type | Description |
|-----------|------|-------------|
| `primary` | string | Primary brand color (hex, e.g., `"#1A73E8"`) |
| `secondary` | string | Secondary accent color |
| `accent` | string | Highlight/CTA color |
| `background` | string | Default background color |
| `text` | string | Default body text color |
| `text_light` | string | Text color for dark backgrounds |
| `gradient` | array | Gradient stops, e.g., `["#1A73E8", "#34A853"]` |
| `social_overlay` | string | Color used for text overlays on images |

## `fonts`

```json
{
  "heading": "Inter",
  "body": "Inter",
  "accent": "Space Grotesk",
  "fallback": "Arial, sans-serif"
}
```

## `image_rules`

| Sub-field | Type | Description |
|-----------|------|-------------|
| `prefer_photography` | boolean | Prefer real photos over illustrations |
| `avoid_stock` | boolean | Flag stock-looking imagery for review |
| `min_resolution` | string | Minimum acceptable resolution (e.g., `"1080x1080"`) |
| `banned_subjects` | array | Subjects to never depict (e.g., `["alcohol", "weapons"]`) |
| `style_keywords` | array | Keywords for AI image generation prompts |

## `logo_overlay`

| Sub-field | Type | Description |
|-----------|------|-------------|
| `position` | string | Placement: `"bottom-right"`, `"bottom-left"`, `"top-right"`, `"top-left"` |
| `opacity` | number | 0.0 to 1.0 |
| `max_width_pct` | number | Max width as percentage of image width (e.g., `15`) |
| `padding_px` | number | Padding from edge in pixels |

## `social_profiles`

```json
{
  "linkedin": "company/acme-corp",
  "instagram": "@acmecorp",
  "x": "@acmecorp",
  "facebook": "acmecorp",
  "tiktok": "@acmecorp",
  "youtube": "@AcmeCorp"
}
```

## Example

```json
{
  "brand_name": "Acme Corp",
  "brand_slug": "acme-corp",
  "tagline": "Build better, ship faster",
  "industry": "saas",
  "website": "https://acme.com",
  "colors": {
    "primary": "#1A73E8",
    "secondary": "#34A853",
    "accent": "#FBBC04",
    "background": "#FFFFFF",
    "text": "#202124",
    "text_light": "#FFFFFF"
  },
  "fonts": {
    "heading": "Inter",
    "body": "Inter"
  },
  "visual_style": "modern-minimal",
  "brand_hashtags": ["#AcmeCorp", "#BuildBetter"],
  "languages": ["en"]
}
```

## Validation

- `brand_name` and `brand_slug` must be present or the pipeline aborts.
- `colors.primary` is required — all other color fields fall back to defaults.
- `brand_slug` must match the directory name under `${CLAUDE_PLUGIN_DATA}/socialforge/brands/` (or `~/socialforge-workspace/brands/` fallback).
