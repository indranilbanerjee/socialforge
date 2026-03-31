---
name: match-assets
description: "Match brand assets to calendar posts and assign creative modes. Use when: after calendar parsing or asset re-matching."
argument-hint: "[--brand <name>] [--post <id>] [--override]"
effort: high
user-invocable: true
---

# /sf:match-assets — Asset Matcher

Match brand assets to parsed calendar posts using the multi-factor scoring algorithm. Assigns one of 4 creative modes per post.

## Prerequisites
- Calendar parsed (calendar-data.json exists)
- Asset index built (asset-index.json exists)

If either is missing, prompt: "Run `/sf:parse-calendar` first, then `/sf:index-assets`."

## The Matching Algorithm

For each post, calculate a multi-factor score against every indexed asset:

| Factor | Weight | What It Measures |
|--------|--------|------------------|
| Tag Overlap | 30% | Post keywords vs asset tags |
| Suitability Match | 25% | Asset's "suitable_for" vs post context |
| Content Bucket Match | 20% | Does asset suit this content bucket? |
| Crop Feasibility | 15% | Can asset be cropped to all required platform ratios? |
| Freshness Penalty | 10% | Penalize assets used recently this month |

**Freshness penalty:** 0 uses = no penalty | 1 use = score x 0.85 | 2 uses = score x 0.60 | 3+ uses = score x 0.30

## Creative Mode Assignment

| Score Range | Recommended Mode |
|-------------|-----------------|
| > 0.8 | ANCHOR_COMPOSE or ENHANCE_EXTEND |
| 0.5 - 0.8 | ENHANCE_EXTEND or STYLE_REFERENCED |
| 0.3 - 0.5 | STYLE_REFERENCED |
| < 0.3 | PURE_CREATIVE |

Also selects 2-5 style reference images per post (always fed to AI generation alongside prompts).

## Process

1. Load calendar-data.json and asset-index.json
2. For each post: extract keywords → score all assets → rank → assign mode
3. Select style references per post
4. Generate coverage report

## Coverage Report

```
Asset Matching Complete: 28 posts
  ANCHOR_COMPOSE: 8 posts (direct brand asset matches)
  ENHANCE_EXTEND: 5 posts (asset needs enhancement)
  STYLE_REFERENCED: 9 posts (AI gen guided by brand DNA)
  PURE_CREATIVE: 4 posts (full AI generation)
  CAROUSEL_TEMPLATE: 2 posts (HTML template rendering)

  Asset gaps: 3 posts flagged (should have brand assets but none found)
    - P07: Founder post but no founder photos indexed
    - P14: Product demo but no product screenshots available
    - P22: Office culture post but no office photos

  Top used assets: asset_012 (3 posts), asset_005 (2 posts)
```

5. Present for user confirmation — user can override any match
6. Save to `output/{brand}/{YYYY-MM}/asset-matches.json`

## User Override

For any post, user can:
- Accept the recommendation
- Select a different asset: "Use asset_015 for P07"
- Change creative mode: "Make P14 PURE_CREATIVE instead"
- Upload a new asset on the spot
- Skip: "I'll handle P22 manually"

## Timeout & Fallback
- Per-post matching: 5-second timeout. If an asset index is very large (500+ images), process in batches.
- Show progress: `[12/28] Matching Post P12 — best match: asset_023 (score: 0.74, STYLE_REFERENCED)`
