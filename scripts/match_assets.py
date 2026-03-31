#!/usr/bin/env python3
"""
match_assets.py — Multi-factor asset matching algorithm.
Matches brand assets to calendar posts and recommends creative modes.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Persistent storage: prefer ${CLAUDE_PLUGIN_DATA} (survives sessions/updates),
# fall back to ~/socialforge-workspace (legacy/local)
_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
if _plugin_data and Path(_plugin_data).exists():
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
    WORKSPACE = Path.home() / "socialforge-workspace"


def extract_keywords(post):
    """Extract matching keywords from a post."""
    keywords = set()
    for field in ["title", "content_bucket", "category"]:
        if post.get(field):
            keywords.update(post[field].lower().split())
    visual = post.get("visual", {})
    for field in ["direction_a", "direction_b"]:
        if visual.get(field):
            keywords.update(visual[field].lower().split())
    # Remove common stop words
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "is", "it", "this", "that"}
    return keywords - stop_words


def score_asset(asset, post_keywords, post, month_usage, week_usage=None):
    """Calculate multi-factor match score for an asset against a post."""
    if week_usage is None:
        week_usage = {}

    asset_tags = set(t.lower() for t in asset.get("tags", []))

    # Factor 1: Tag overlap (30%)
    overlap = len(post_keywords & asset_tags)
    tag_score = min(overlap / max(len(post_keywords), 1), 1.0)

    # Factor 2: Suitability match (25%)
    suitable = asset.get("suitable_for", [])
    suit_score = 0
    post_context = f"{post.get('title', '')} {post.get('content_bucket', '')}".lower()
    for s in suitable:
        if any(word in post_context for word in s.lower().split()):
            suit_score += 0.25
    suit_score = min(suit_score, 1.0)

    # Factor 3: Content bucket match (20%)
    bucket = post.get("content_bucket", "").lower()
    bucket_score = 1.0 if bucket and any(bucket in t for t in asset_tags) else 0.0

    # Factor 4: Crop feasibility (15%)
    platforms = post.get("platforms", [])
    crop_feasible = 0
    compat = asset.get("platforms_compatible", {})
    for p in platforms:
        if compat.get(p.get("key", ""), {}).get("crop_feasible", False):
            crop_feasible += 1
    crop_score = crop_feasible / max(len(platforms), 1)

    # Factor 5: Freshness penalty (10%)
    asset_id = asset.get("id", "")
    uses = month_usage.get(asset_id, 0)
    freshness_penalty = 0 if uses == 0 else (0.15 if uses == 1 else (0.40 if uses == 2 else 0.70))

    # Same-week additional penalty (spec: ×0.50 additional)
    post_week = post.get("week_number", 0)
    if post_week and asset_id in week_usage.get(post_week, set()):
        freshness_penalty = min(freshness_penalty + 0.50, 1.0)  # Additional 0.50, cap at 1.0

    final = (tag_score * 0.30) + (suit_score * 0.25) + (bucket_score * 0.20) + (crop_score * 0.15) - (freshness_penalty * 0.10)
    return max(0, min(final, 1.0))


def recommend_mode(score):
    """Recommend creative mode based on match score."""
    if score > 0.8:
        return "ANCHOR_COMPOSE"
    elif score > 0.5:
        return "ENHANCE_EXTEND"
    elif score > 0.3:
        return "STYLE_REFERENCED"
    else:
        return "PURE_CREATIVE"


def match_all(brand, month):
    """Run matching for all posts."""
    calendar_path = WORKSPACE / "output" / brand / month / "calendar-data.json"
    index_path = WORKSPACE / "brands" / brand / "asset-index.json"

    if not calendar_path.exists():
        print(json.dumps({"error": "Calendar not parsed. Run parse-calendar first."}))
        sys.exit(1)
    if not index_path.exists():
        print(json.dumps({"error": "Assets not indexed. Run index-assets first."}))
        sys.exit(1)

    calendar = json.loads(calendar_path.read_text(encoding="utf-8"))
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assets = index.get("assets", [])

    # Build month + week usage from existing matches
    month_usage = {}
    week_usage = {}

    results = []
    mode_counts = {"ANCHOR_COMPOSE": 0, "ENHANCE_EXTEND": 0, "STYLE_REFERENCED": 0, "PURE_CREATIVE": 0}

    for post in calendar.get("posts", []):
        post_keywords = extract_keywords(post)

        # Score all assets
        scored = []
        for asset in assets:
            score = score_asset(asset, post_keywords, post, month_usage, week_usage)
            scored.append({"asset_id": asset["id"], "score": round(score, 3), "filename": asset.get("filename", "")})

        scored.sort(key=lambda x: -x["score"])
        top = scored[:5] if scored else []

        best_score = top[0]["score"] if top else 0
        mode = recommend_mode(best_score)

        # Handle content type overrides
        if post.get("content_type") == "carousel":
            mode = "CAROUSEL_TEMPLATE"
        elif post.get("content_type") == "text_only":
            mode = "TEXT_ONLY"

        mode_counts[mode] = mode_counts.get(mode, 0) + 1

        # Track usage (month + week)
        if top and best_score > 0.5:
            month_usage[top[0]["asset_id"]] = month_usage.get(top[0]["asset_id"], 0) + 1
            post_week = post.get("week_number", 0)
            if post_week:
                week_usage.setdefault(post_week, set()).add(top[0]["asset_id"])

        # Select style references
        style_refs = [a["id"] for a in assets if a.get("is_style_reference")][:5]

        results.append({
            "post_id": post["post_id"],
            "recommendation": mode,
            "primary_asset": top[0] if top else None,
            "alternatives": top[1:],
            "style_references": style_refs,
            "gap_flag": best_score < 0.3 and post.get("tier") in ["HERO", "HUB"]
        })

    output = {"brand": brand, "month": month, "matches": results, "mode_distribution": mode_counts}

    output_path = WORKSPACE / "output" / brand / month / "asset-matches.json"
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({"matched": len(results), "modes": mode_counts, "output": str(output_path)}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="SocialForge Asset Matcher")
    parser.add_argument("--brand", required=True)
    parser.add_argument("--month", required=True)
    args = parser.parse_args()

    match_all(args.brand, args.month)


if __name__ == "__main__":
    main()
