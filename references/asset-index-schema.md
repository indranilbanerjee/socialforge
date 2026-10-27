# Asset Index Schema Reference

JSON schema for `asset-index.json` — the catalog of all indexed brand visual assets with AI-generated metadata.

## Location

```
${CLAUDE_PLUGIN_DATA}/socialforge/brands/<brand-slug>/asset-index.json
```

When `CLAUDE_PLUGIN_DATA` is unset, the scripts fall back to:

```
~/socialforge-workspace/brands/<brand-slug>/asset-index.json
```

## Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `brand` | string | Brand slug this index belongs to |
| `indexed_at` | string | ISO 8601 timestamp of last indexing run |
| `source` | string | Kind of source indexed (`"local"` for a folder) |
| `source_path` | string | The folder that was indexed; `--refresh` without `--source` reuses it |
| `total_assets` | number | Total number of indexed assets |
| `vision_model` | object | The model decision of the latest run that analysed an image (see below); absent in indexes written before 1.30.0 |
| `assets` | array | Array of asset objects (see below) |

## `vision_model`

The decision `index_assets.py` made once for the run, before the first image. A refresh that finds nothing new to analyse keeps the previous run's record.

| Sub-field | Type | Description |
|-----------|------|-------------|
| `model` | string or null | The id that was sent to the vision API; null when nothing could be analysed |
| `model_requested` | string or null | The id asked for by name (the brand's pin or `--model`); null when the router chose |
| `selected_by` | string or null | `"brand-pin"`, `"--model"`, `"router"` or `"registry-alias"` |
| `basis` | string | `"live"` (read from the key's model list this run), `"cache"` (from a list read within the last 7 days), `"requested"` (a name asked for, checked against the list or the record), `"offline"` (the shipped registry alias: the list could not be read, `MODEL_ROUTER_OFFLINE=1` was set, or Vertex AI served the run) or `"unavailable"` (no client, so no image could be analysed) |
| `source` | string or null | The list endpoint, or `"shipped-default"` for `"offline"` |
| `discovered_at` | string or null | When the list was read (ISO 8601, UTC) |
| `decided_at` | string | When this decision was made |
| `replacement` | string or null | The model the vendor or the router names instead of one asked for that is deprecated |
| `reason` | string or null | Why the router fell back to the shipped default, when it did |
| `warnings` | array | Everything the run said about the choice (a deprecated pin, a stale record, a model held back for want of a release date) |
| `job`, `router` | string | The hint-book job (`"index-assets.vision.google"`) and the router version |

## Asset Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique asset identifier (e.g., `"asset_001"`); never re-minted, so a refresh keeps every existing id |
| `filename` | string | Original filename |
| `path` | string | Path of the file as scanned (the key `--refresh` matches on) |
| `relative_path` | string | Path relative to the indexed folder |
| `folder` | string | The file's folder relative to the indexed folder |
| `dimensions` | object | `{ "width": 1200, "height": 627 }`; `dimensions_unreadable: true` is set beside it when the file could not be opened |
| `ai_description` | string | AI-generated description of the image content |
| `analysis_model` | string | The model that analysed this image; absent when no AI analysis ran. A refresh can mix models in one index, and this field is what says which |
| `analyzed_at` | string | When that analysis ran (ISO 8601, UTC) |
| `tags` | array | Semantic tags (e.g., `["team", "office", "collaboration"]`) |
| `detected_colors` | array | Dominant colors as hex values |
| `dominant_mood` | string | Detected mood (e.g., `"professional"`, `"energetic"`, `"calm"`) |
| `lighting` | string | Lighting type (e.g., `"natural"`, `"studio"`, `"warm"`) |
| `setting` | string | Environment (e.g., `"office"`, `"outdoor"`, `"abstract"`) |
| `subjects` | array | Primary subjects (e.g., `["person", "laptop", "whiteboard"]`) |
| `suitable_for` | array | Content types this suits (e.g., `["thought-leadership", "product"]`) |
| `platforms_compatible` | object | Per-platform compatibility keyed by platform key (see below) |
| `usage_history` | array | Previous usage records (see below) |
| `background_removable` | boolean | Whether background can be cleanly removed |
| `is_style_reference` | boolean | Whether this asset can serve as a style reference for AI generation |

## `platforms_compatible`

A dict keyed by platform key, each value an object describing how the asset behaves on that platform. `index_assets.py` initializes it as `{}`; `match_assets.py` reads `platforms_compatible[<platform_key>]["crop_feasible"]` for the crop-feasibility scoring factor (15% of the match score).

| Sub-field | Type | Description |
|-----------|------|-------------|
| `crop_feasible` | boolean | Whether the asset can be cropped to this platform's aspect ratio without losing the subject |

```json
"platforms_compatible": {
  "linkedin": { "crop_feasible": true },
  "instagram": { "crop_feasible": true },
  "x": { "crop_feasible": false }
}
```

A bare boolean value (`"linkedin": true`) is tolerated, as is the legacy flat array form (`["linkedin", "x"]`) — in the array form every listed platform is treated as crop-feasible. New indexes should write the dict-of-dicts form.

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
  "indexed_at": "2026-03-15T10:30:00+00:00",
  "source": "local",
  "source_path": "/photos/acme",
  "total_assets": 42,
  "vision_model": {
    "job": "index-assets.vision.google",
    "model": "<the id that was sent>",
    "model_requested": null,
    "selected_by": "router",
    "basis": "live",
    "source": "https://generativelanguage.googleapis.com/v1beta/models",
    "discovered_at": "2026-03-15T10:29:41Z",
    "decided_at": "2026-03-15T10:29:41Z",
    "replacement": null,
    "reason": null,
    "router": "model_router/1",
    "warnings": []
  },
  "assets": [
    {
      "id": "asset_001",
      "filename": "team-meeting.jpg",
      "path": "/photos/acme/team/team-meeting.jpg",
      "relative_path": "team/team-meeting.jpg",
      "folder": "team",
      "dimensions": { "width": 4000, "height": 2667 },
      "ai_description": "Diverse team of five people collaborating around a modern conference table with laptops and notebooks",
      "analysis_model": "<the id that analysed it>",
      "analyzed_at": "2026-03-15T10:29:58+00:00",
      "tags": ["team", "meeting", "collaboration", "office"],
      "detected_colors": ["#1A73E8", "#FFFFFF", "#F5F5F5"],
      "dominant_mood": "professional",
      "lighting": "natural",
      "setting": "office",
      "subjects": ["people", "laptops", "conference-table"],
      "suitable_for": ["culture", "hiring", "thought-leadership"],
      "platforms_compatible": {
        "linkedin": { "crop_feasible": true },
        "x": { "crop_feasible": true },
        "facebook": { "crop_feasible": true }
      },
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

- Indexing runs via `/socialforge:index-assets` or automatically during `/socialforge:brand-setup`.
- Assets with `usage_history` entries in the current month are deprioritized to avoid repetition.
- `is_style_reference: true` assets are candidates for STYLE_REFERENCED image generation mode.
- `platforms_compatible` is computed from `dimensions` against platform specs, one entry per platform key.
- Re-indexing preserves `usage_history` from the previous index.
