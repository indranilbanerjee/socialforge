# Calendar Data Schema Reference

JSON schema for `calendar-data.json` — the monthly content calendar with all planned posts, scheduling, and production metadata.

## Location

```
~/socialforge-workspace/brands/<brand-slug>/calendar-data.json
```

## Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `brand` | string | Brand slug |
| `month` | string | Target month (e.g., `"2026-04"`) |
| `campaign` | string | Campaign name or theme for the month |
| `summary` | string | One-line description of the month's content strategy |
| `special_dates` | array | Key dates to plan around (see below) |
| `content_buckets` | array | Content pillar names (e.g., `["thought-leadership", "product", "culture"]`) |
| `posts` | array | Array of planned post objects (see below) |

## `special_dates` Entry

| Field | Type | Description |
|-------|------|-------------|
| `date` | string | Date (YYYY-MM-DD) |
| `event` | string | Event name (e.g., `"Product Launch"`, `"Earth Day"`) |
| `tier` | string | Content tier: `"HERO"`, `"HUB"`, or `"HYGIENE"` |

## Post Object

| Field | Type | Description |
|-------|------|-------------|
| `post_id` | string | Unique ID (e.g., `"post-2026-04-07-lin-001"`) |
| `date` | string | Scheduled date (YYYY-MM-DD) |
| `tier` | string | `"HERO"`, `"HUB"`, or `"HYGIENE"` |
| `platforms` | array | Target platforms (e.g., `["linkedin", "x"]`) |
| `copy` | object | Copy content (see below) |
| `visual` | object | Visual asset assignment (see below) |
| `content_type` | string | Type: `"static"`, `"carousel"`, `"video"`, `"text-only"` |
| `carousel_details` | object | Carousel-specific data (if applicable) |
| `video_details` | object | Video-specific data (if applicable) |
| `production` | object | Production metadata (see below) |
| `boosting` | object | Paid promotion details (if applicable) |
| `dependencies` | array | Post IDs this post depends on |

## `copy`

| Field | Type | Description |
|-------|------|-------------|
| `hook` | string | Opening line / hook text |
| `body` | string | Main body copy |
| `cta` | string | Call to action |
| `hashtags` | array | Post-specific hashtags |
| `variants` | object | Platform-specific copy overrides keyed by platform name |

## `visual`

| Field | Type | Description |
|-------|------|-------------|
| `mode` | string | `"ASSET_ONLY"`, `"ANCHOR_COMPOSE"`, `"STYLE_REFERENCED"`, `"AI_ORIGINAL"` |
| `asset_id` | string | Reference to asset-index ID (if using existing asset) |
| `prompt` | string | AI generation prompt (if generating) |
| `style_reference_id` | string | Asset ID for style reference (if STYLE_REFERENCED) |
| `text_overlay` | object | `{ "headline": "...", "subtext": "..." }` |

## `carousel_details`

| Field | Type | Description |
|-------|------|-------------|
| `slide_count` | number | Number of slides |
| `template` | string | Template name (e.g., `"tips-listicle"`, `"data-story"`) |
| `slides` | array | Array of `{ "headline": "...", "body": "...", "visual_note": "..." }` |

## `video_details`

| Field | Type | Description |
|-------|------|-------------|
| `duration_seconds` | number | Target video length |
| `format` | string | `"reel"`, `"story"`, `"long-form"` |
| `script_outline` | string | Brief script description |

## `production`

| Field | Type | Description |
|-------|------|-------------|
| `writer` | string | Assigned content creator |
| `designer` | string | Assigned visual designer |
| `due_date` | string | Internal deadline (YYYY-MM-DD) |
| `status` | string | `"planned"`, `"drafting"`, `"in-review"`, `"approved"`, `"scheduled"` |

## `boosting`

| Field | Type | Description |
|-------|------|-------------|
| `budget` | number | Spend amount in brand currency |
| `objective` | string | Campaign objective (e.g., `"awareness"`, `"engagement"`, `"traffic"`) |
| `audience` | string | Target audience segment name |
| `duration_days` | number | Boost duration |

## Example Post

```json
{
  "post_id": "post-2026-04-07-lin-001",
  "date": "2026-04-07",
  "tier": "HUB",
  "platforms": ["linkedin", "x"],
  "copy": {
    "hook": "We analyzed 10,000 SaaS onboarding flows. Here's what the top 1% do differently.",
    "body": "...",
    "cta": "Link in comments",
    "hashtags": ["#SaaS", "#ProductLed"],
    "variants": {
      "x": { "body": "Shorter version for X..." }
    }
  },
  "visual": {
    "mode": "ANCHOR_COMPOSE",
    "asset_id": "asset-012",
    "text_overlay": { "headline": "Top 1% Onboarding" }
  },
  "content_type": "static",
  "production": {
    "status": "planned",
    "due_date": "2026-04-04"
  },
  "dependencies": []
}
```
