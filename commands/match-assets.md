---
description: Match brand assets to calendar posts and assign creative modes
argument-hint: "--brand <name> --month <YYYY-MM>"
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
- Month initialized and calendar parsed (`/socialforge:new-month` or `/socialforge:parse-calendar`)
- Asset index built (`/socialforge:index-assets`)
