---
name: index-assets
description: "Index the brand photo library with AI vision so assets are searchable and matchable. \"catalogue our brand photos\""
argument-hint: "<brand-name> [--source <path>] [--refresh]"
effort: high
user-invocable: true
---

# /socialforge:index-assets — Asset Indexer

> **Script location.** If your host does not set `${CLAUDE_PLUGIN_ROOT}`, the scripts are in this plugin's `scripts/` folder, next to `skills/`.

Scan a brand's photo library and create an AI-powered asset index. Each image is analyzed by a vision model (registry alias `latest-vision-google`) to understand what's in it, what mood it conveys, what posts it's suitable for, and how it can be cropped for different platforms.

## Context efficiency

Asset-heavy skill. **Grep before Read** the asset catalog (`${CLAUDE_PLUGIN_DATA}/socialforge/brands/<brand>/asset-index.json`) — never list the asset directory. Reference generated images / videos by path, not by loading metadata. Brand profile loads once per session.

## How It Works

1. **Locate assets** — Read asset-source.json for the brand's photo library location
2. **Scan files** — Find all .jpg, .jpeg, .png, .webp files in the source
3. **AI analysis** — For each image, use the vision model (the registry alias `latest-vision-google`) to generate:
   - Natural language description of the image
   - Tags (categories, subjects, setting, mood)
   - Dominant colors detected
   - Lighting and composition assessment
   - What types of social media posts this image suits
   - Whether background is removable (for compositing)
   - Platform crop feasibility (can this be cropped to 1:1, 4:5, 16:9 without losing key content?)
4. **Build index** — Create asset-index.json with all analyzed assets
5. **Identify style references** — Suggest 2-8 images as style reference candidates (best represent the brand's visual DNA)

## Pre-Flight Check

Before indexing, verify:
- Brand profile exists for the specified brand
- Asset source is configured (Google Drive URL or local path)
- If Google Drive: verify Drive MCP is connected or platform integration is available

If asset source is not configured:
```
⚠️ No asset source configured for brand "{brand}".
Run /socialforge:brand-setup {brand} --update to add an asset source.
Or provide a path now: /socialforge:index-assets {brand} --source /path/to/photos
```

## Progress Updates

```
[1/4] Scanning asset source...
  Found: 47 images (32 .jpg, 12 .png, 3 .webp)

[2/4] Analyzing images with AI Vision...
  Analyzed: 12/47 (25%) — ~3 min remaining
  Analyzed: 24/47 (51%) — ~2 min remaining
  Analyzed: 47/47 (100%) ✓

[3/4] Building asset index...
  Tags generated: 184 unique tags across 47 assets
  Platform crops: 47 images × 6 platforms = 282 crop assessments

[4/4] Identifying style reference candidates...
  Top 8 candidates selected based on visual consistency and quality
```

## Output

```
Asset Index Complete: acme-corp
  Total assets: 47
  Categories: people (12), products (8), office (6), events (5), lifestyle (9), graphics (7)
  Background-removable: 23 assets (suitable for ANCHOR_COMPOSE mode)
  Style reference candidates: 8 images suggested

  Saved: ${CLAUDE_PLUGIN_DATA}/socialforge/brands/acme-corp/asset-index.json

Would you like to:
- Review style reference candidates? (I'll show all 8 with descriptions)
- Start monthly production? (/socialforge:new-month)
- Update specific assets? (/socialforge:index-assets acme-corp --source /path/to/photos --refresh)
```

## Timeout & Fallback

- Per-image AI analysis: 15-second timeout. If an image times out, mark as `analysis_pending` and continue.
- Large libraries (100+ images): Process in batches of 20. Show progress after each batch.
- If AI Vision is unavailable: Create basic index from file metadata only (dimensions, filename, folder) — flag as `ai_analysis_missing`.

## Refresh Mode

`/socialforge:index-assets [brand] --source <path> --refresh`

`--source` may be omitted on a refresh: the script reuses the source recorded by the previous index and stops only when none was recorded. Only re-analyzes new or modified images since last index. Compares file timestamps with `indexed_at` in asset-index.json.

Where the index is written (including the fallback location when no plugin data directory is set) and how `--source` is resolved: read [storage-and-refresh.md](storage-and-refresh.md) when the user asks where the index lives or why a refresh behaved a given way.

## Cost Awareness

Each image analysis is a billed call, and its rate depends on the vision model the alias resolves to today. This skill therefore states no price — it quotes one that was looked up:

1. Resolve the model id the alias points at: `python "${CLAUDE_PLUGIN_ROOT}/scripts/resolve_model.py" --alias latest-vision-google`
2. Quote the run: `python "${CLAUDE_PLUGIN_ROOT}/scripts/price_book.py" --action quote --model "<resolved model id>" --provider vertex --units <number of images to analyze>` (on `--refresh`, count only the new or modified images)

If `price_book.py` answers `unknown` or `stale`, follow `/socialforge:price-check`: read the provider's pricing page, record the rate with its source URL, then quote. If the vendor bills by token rather than per image, or no price can be quoted at all, say so and give the pricing URL — never an estimate and never a per-image figure converted from memory.

Show the quoted total before starting ("Indexing {N} images will cost {total} at {rate} per image, priced {age_hours}h ago. Proceed?") and wait for an explicit yes. A quote is not approval.
