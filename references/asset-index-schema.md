# Asset Index Schema Reference

JSON schema for `asset-index.json` — the catalog of all indexed brand visual assets with AI-generated metadata.

## Location

```
~/.claude-marketing/<brand-slug>/asset-index.json
```

## Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `brand` | string | Brand slug this index belongs to |
| `indexed_at` | string | ISO 8601 timestamp of last indexing run |
| `source` | string | Asset source directory path |
| `total_assets` | number | Total number of indexed assets |
| `assets` | array | Array of asset objects (see below) |

## Asset Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique asset identifier (e.g., `"asset-001"`) |
| `filename` | string | Original filename |
| `path` | string | Relative path from brand directory |
| `dimensions` | object | `{ "width": 1200, "height": 627 }` |
| `ai_description` | string | AI-generated description of the image content |
| `tags` | array | Semantic tags (e.g., `["team", "office", "collaboration"]`) |
| `detected_colors` | array | Dominant colors as hex values |
| `mood` | string | Detected mood (e.g., `"professional"`, `"energetic"`, `"calm"`) |
| `lighting` | string | Lighting type (e.g., `"natural"`, `"studio"`, `"warm"`) |
| `setting` | string | Environment (e.g., `"office"`, `"outdoor"`, `"abstract"`) |
| `subjects` | array | Primary subjects (e.g., `["person", "laptop", "whiteboard"]`) |
| `suitable_for` | array | Content types this suits (e.g., `["thought-leadership", "product"]`) |
| `platforms_compatible` | array | Platforms where aspect ratio works (e.g., `["linkedin", "x"]`) |
| `usage_history` | array | Previous usage records (see below) |
| `background_removable` | boolean | Whether background can be cleanly removed |
| `is_style_reference` | boolean | Whether this asset can serve as a style reference for AI generation |

## `usage_history` Entry

| Field | Type | Description |
|-------|------|-------------|
| `post_id` | string | ID of the post that used this asset |
| `date` | string | Date used (YYYY-MM-DD) |
| `platform` | string | Platform it was used on |

## Example

```json
{
  "brand": "acme-corp",
  "indexed_at": "2026-03-15T10:30:00Z",
  "source": "assets/",
  "total_assets": 42,
  "assets": [
    {
      "id": "asset-001",
      "filename": "team-meeting.jpg",
      "path": "assets/photos/team-meeting.jpg",
      "dimensions": { "width": 4000, "height": 2667 },
      "ai_description": "Diverse team of five people collaborating around a modern conference table with laptops and notebooks",
      "tags": ["team", "meeting", "collaboration", "office"],
      "detected_colors": ["#1A73E8", "#FFFFFF", "#F5F5F5"],
      "mood": "professional",
      "lighting": "natural",
      "setting": "office",
      "subjects": ["people", "laptops", "conference-table"],
      "suitable_for": ["culture", "hiring", "thought-leadership"],
      "platforms_compatible": ["linkedin", "x", "facebook"],
      "usage_history": [
        { "post_id": "post-2026-03-05-lin-001", "date": "2026-03-05", "platform": "linkedin" }
      ],
      "background_removable": false,
      "is_style_reference": true
    }
  ]
}
```

## Indexing Behavior

- Indexing runs via `/sf:index-assets` or automatically during `/sf:brand-setup`.
- Assets with `usage_history` entries in the current month are deprioritized to avoid repetition.
- `is_style_reference: true` assets are candidates for STYLE_REFERENCED image generation mode.
- `platforms_compatible` is computed from `dimensions` against platform specs.
- Re-indexing preserves `usage_history` from the previous index.
