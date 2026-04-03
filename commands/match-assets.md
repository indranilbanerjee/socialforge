---
description: Match brand assets to calendar posts and assign creative modes
argument-hint: "[--brand <name>] [--post <id>] [--override]"
---

# Match Assets

Run the asset matching algorithm to pair brand photos with calendar posts.

## Process
1. Load calendar-data.json and asset-index.json
2. Score each asset against each post using 5-factor algorithm (tags, suitability, bucket, crop, freshness)
3. Assign creative mode per post (ANCHOR_COMPOSE, ENHANCE_EXTEND, STYLE_REFERENCED, PURE_CREATIVE)
4. Show match summary for user review
5. User can override any match before proceeding

## Prerequisites
- Calendar parsed (/sf:parse-calendar)
- Asset index built (/sf:index-assets)
