# Calendar Data Schema Reference

JSON schema for `calendar-data.json` — the monthly content calendar with all planned posts, scheduling, and production metadata.

## Location

```
${CLAUDE_PLUGIN_DATA}/socialforge/output/<brand-slug>/<month>/calendar-data.json
```

When `CLAUDE_PLUGIN_DATA` is unset, the scripts fall back to:

```
~/socialforge-workspace/output/<brand-slug>/<month>/calendar-data.json
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
| `platforms` | array | Target platform objects — `[{ "key": "linkedin", "name": "LinkedIn" }, ...]` (see below) |
| `copy` | object | Copy content (see below) |
| `visual` | object | Visual asset assignment (see below) |
| `content_type` | string | Type: `"static"`, `"carousel"`, `"video"`, `"text_only"` |
| `carousel_details` | object | Carousel-specific data (if applicable) |
| `video_details` | object | Video-specific data (if applicable) |
| `production` | object | Production metadata (see below) |
| `boosting` | object | Paid promotion details (if applicable) |
| `dependencies` | array | Post IDs this post depends on |

## `platforms` Entry

Each entry is an object. The scripts are canonical here: `match_assets.py` reads `platform["key"]` to look up crop feasibility, and `status_manager.py` reads `platform["name"]` when building the post folder name.

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | Machine key used for lookups (`"linkedin"`, `"instagram"`, `"x"`, `"facebook"`, `"youtube"`, `"tiktok"`, `"pinterest"`) |
| `name` | string | Display name used in folder names and galleries (e.g., `"LinkedIn"`) |

```json
"platforms": [
  { "key": "linkedin", "name": "LinkedIn" },
  { "key": "x", "name": "X" }
]
```

Plain string entries (`["linkedin", "x"]`) are tolerated throughout: `match_assets.py` treats the string as the key, and `status_manager.py` uses it directly in the folder name. Prefer the object form so galleries and folder names get a properly cased display label.

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
| `mode` | string | Creative mode. Four generation modes: `"ANCHOR_COMPOSE"`, `"ENHANCE_EXTEND"`, `"STYLE_REFERENCED"`, `"PURE_CREATIVE"`. `match_assets.py` also emits `"CAROUSEL_TEMPLATE"` when `content_type` is `"carousel"` and `"TEXT_ONLY"` when it is `"text_only"`. |
| `asset_id` | string | Reference to asset-index ID (if using existing asset) |
| `prompt` | string | AI generation prompt (if generating) |
| `style_reference_id` | string | Asset ID for style reference (if STYLE_REFERENCED) |
| `text_overlay` | object | `{ "headline": "...", "subtext": "..." }` |

## `carousel_details`

| Field | Type | Description |
|-------|------|-------------|
| `slide_count` | number | Number of slides |
| `template` | string | Template key (e.g., `"tips"`, `"data"`) — one of `generic`, `comparison`, `case-study`, `tips`, `playbook`, `recap`, `data`, `quote`. See `references/carousel-templates-guide.md`. |
| `slides` | array | Array of per-slide objects; each key `k` fills the template's `{{slide_k}}` placeholder |

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
  "platforms": [
    { "key": "linkedin", "name": "LinkedIn" },
    { "key": "x", "name": "X" }
  ],
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
