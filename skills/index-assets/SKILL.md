---
name: index-assets
description: Index brand photo library using AI vision. Use when: setting up assets, adding new photos, or refreshing the index.
argument-hint: "[brand-name] [--source drive|local] [--refresh]"
effort: high
user-invocable: true
---

# /sf:index-assets — Asset Indexer

Scan a brand's photo library and create an AI-powered asset index. Each image is analyzed by Gemini Vision to understand what's in it, what mood it conveys, what posts it's suitable for, and how it can be cropped for different platforms.

## How It Works

1. **Locate assets** — Read asset-source.json for the brand's photo library location
2. **Scan files** — Find all .jpg, .jpeg, .png, .webp files in the source
3. **AI analysis** — For each image, use Gemini Vision (gemini-3-flash) to generate:
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
Run /sf:brand-setup --update {brand} to add an asset source.
Or provide a path now: /sf:index-assets {brand} --source local --path /path/to/photos
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

  Saved: ~/socialforge-workspace/brands/acme-corp/asset-index.json

Would you like to:
- Review style reference candidates? (I'll show all 8 with descriptions)
- Start monthly production? (/sf:new-month)
- Update specific assets? (/sf:index-assets --refresh)
```

## Timeout & Fallback

- Per-image AI analysis: 15-second timeout. If an image times out, mark as `analysis_pending` and continue.
- Large libraries (100+ images): Process in batches of 20. Show progress after each batch.
- If AI Vision is unavailable: Create basic index from file metadata only (dimensions, filename, folder) — flag as `ai_analysis_missing`.

## Refresh Mode

`/sf:index-assets [brand] --refresh`

Only re-analyzes new or modified images since last index. Compares file timestamps with `indexed_at` in asset-index.json.

## Cost Awareness

Each image analysis costs approximately $0.002-0.005 (Gemini Vision). For a 50-image library, expect ~$0.10-0.25 total.

Show estimated cost before starting: "Indexing 47 images will cost approximately $0.12 in Gemini Vision API calls. Proceed?"
