---
name: index-assets
description: "Index the brand photo library with AI vision so assets are searchable and matchable. \"catalogue our brand photos\""
argument-hint: "<brand-name> [--source <path>] [--refresh]"
effort: high
user-invocable: true
---

# /socialforge:index-assets — Asset Indexer

> **Script location.** If your host does not set `${CLAUDE_PLUGIN_ROOT}`, the scripts are in this plugin's `scripts/` folder, next to `skills/`. Run them with Python 3.10 or newer: `python`, or `python3` where `python` is not found (macOS, many Linux systems).

Scan a brand's photo library and create an AI-powered asset index. Each image is analyzed by a vision model, chosen from your Google key's own model list (see "Which model" below), to understand what's in it, what mood it conveys, what posts it's suitable for, and how it can be cropped for different platforms.

## Context efficiency

Asset-heavy skill. **Grep before Read** the asset catalog (`${CLAUDE_PLUGIN_DATA}/socialforge/brands/<brand>/asset-index.json`) — never list the asset directory. Reference generated images / videos by path, not by loading metadata. Brand profile loads once per session.

## How It Works

1. **Locate assets** — Read asset-source.json for the brand's photo library location
2. **Scan files** — Find all .jpg, .jpeg, .png, .webp files in the source
3. **AI analysis** — For each image, use the vision model chosen for the run (decided once, before the first image) to generate:
   - Natural language description of the image
   - Tags (categories, subjects, setting, mood)
   - Dominant colors detected
   - Lighting and composition assessment
   - What types of social media posts this image suits
   - Whether background is removable (for compositing)
   - Platform crop feasibility (can this be cropped to 1:1, 4:5, 16:9 without losing key content?)
4. **Build index** — Create asset-index.json with all analyzed assets
5. **Identify style references** — Suggest 2-8 images as style reference candidates (best represent the brand's visual DNA)

## Which model

The script decides the model once per run and never swaps one silently. In order:

1. **The brand's pin** — `model_pins["index-assets.vision.google"]` in the brand's `brand-config.json` (see `references/brand-config-schema.md`). Pin when a library must stay analysed by one model so its tags remain comparable.
2. **`--model <id>`** — for one run.
3. **The router** — `scripts/model_router.py` reads the models your `GEMINI_API_KEY` can use (one list call at most every 7 days) and takes the newest generally available Flash-class model. Previews, "latest" aliases, lite, image, speech and live variants, models shut down or redirected, and models younger than 14 days are never picked.
4. **The registry alias `latest-vision-google`**, tagged `offline` — when the list cannot be read, `MODEL_ROUTER_OFFLINE=1` is set, or Vertex AI serves the run (its catalogue is not the Gemini API's list).

A pin or `--model` is a name asked for: a deprecated model is kept with a warning that names its retirement date and replacement; a retired one stops the run (exit 2, nothing sent) and names the replacement. That holds offline too: with no list to read, the name is checked against the shipped registry and the hint book's record of Google's deprecations page, and the stricter wins. On a Vertex AI run neither applies (Vertex retires models on its own schedule), so the name is sent as asked and the run says it was not checked. A rejected key stops the run the same way. `index_assets.py --brand <brand> --show-model` prints the decision and stops. `asset-index.json` then records `vision_model` (what was asked, what was sent, the basis `live`, `cache`, `requested` or `offline`, the source and the time) and, on each analysed asset, `analysis_model` and `analyzed_at`, so a refresh that mixes models says so.

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

Each image analysis is a billed call, and its rate depends on the vision model the run will use. This skill therefore states no price — it quotes one that was looked up, for the model the run will actually use (which the router may have moved past the registry alias):

1. Ask the script which model the run will use: `python "${CLAUDE_PLUGIN_ROOT}/scripts/index_assets.py" --brand <brand> --show-model` (it reads no image, sends nothing and writes no index; the `model` field of its answer is the id to quote, and its `warnings` are shown to the user)
2. Quote the run: `python "${CLAUDE_PLUGIN_ROOT}/scripts/price_book.py" --action quote --model "<resolved model id>" --provider vertex --units <number of images to analyze>` (on `--refresh`, count only the new or modified images)

If `price_book.py` answers `unknown` or `stale`, follow `/socialforge:price-check`: read the provider's pricing page, record the rate with its source URL, then quote. If the vendor bills by token rather than per image, or no price can be quoted at all, say so and give the pricing URL — never an estimate and never a per-image figure converted from memory.

Show the quoted total before starting ("Indexing {N} images will cost {total} at {rate} per image, priced {age_hours}h ago. Proceed?") and wait for an explicit yes. A quote is not approval.
