#!/usr/bin/env python3
"""
adapt_copy.py — Adapt social media copy for platform-specific requirements.
Handles character limits, hashtag optimization, and CTA formatting.
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

PLATFORM_LIMITS = {
    "linkedin": {"char_limit": 3000, "fold_at": 140, "hashtag_limit": 5, "link": "direct"},
    "instagram": {"char_limit": 2200, "hashtag_limit": 30, "hashtag_placement": "first_comment", "link": "bio"},
    "x": {"char_limit": 280, "hashtag_limit": 2, "link": "direct"},
    "facebook": {"char_limit": 63206, "optimal_limit": 500, "hashtag_limit": 3, "link": "direct"},
    "youtube": {"char_limit": 5000, "hashtag_limit": 5, "link": "direct"},
    "tiktok": {"char_limit": 2200, "hashtag_limit": 10, "link": "bio"},
    "pinterest": {"char_limit": 500, "hashtag_limit": 20, "link": "direct"},
}


def truncate_smart(text, limit):
    """Truncate at last complete sentence that fits."""
    if len(text) <= limit:
        return text
    truncated = text[:limit]
    last_period = truncated.rfind(".")
    last_excl = truncated.rfind("!")
    last_quest = truncated.rfind("?")
    best_break = max(last_period, last_excl, last_quest)
    if best_break > limit * 0.5:
        return truncated[:best_break + 1]
    return truncated[:limit - 3] + "..."


def adapt_for_platform(copy_text, platform, brand_hashtags=None, cta=None):
    """Adapt copy for a specific platform."""
    specs = PLATFORM_LIMITS.get(platform)
    if not specs:
        return {"error": f"Unknown platform: {platform}"}

    adapted = copy_text

    # Truncate to fold point (for preview visibility) or optimal limit
    fold_at = specs.get("fold_at")
    limit = specs.get("optimal_limit", specs["char_limit"])

    if fold_at and len(copy_text) > fold_at:
        # For platforms with "see more" fold: ensure hook is in first N chars
        # Full copy still saved, but first fold_at chars must be compelling
        adapted = copy_text  # Keep full copy
        if len(adapted) > limit:
            adapted = truncate_smart(adapted, limit)
    else:
        adapted = truncate_smart(adapted, limit)

    # Add CTA
    if cta:
        if specs.get("link") == "bio":
            adapted += f"\n\nLink in bio"
        elif specs.get("link") == "direct":
            adapted += f"\n\n{cta}"

    # Prepare hashtags
    all_hashtags = list(brand_hashtags or [])
    hashtag_limit = specs.get("hashtag_limit", 5)
    hashtag_text = " ".join(all_hashtags[:hashtag_limit])

    # Instagram first-comment strategy: hashtags go in first comment, not caption
    first_comment = None
    if specs.get("hashtag_placement") == "first_comment":
        first_comment = hashtag_text
        hashtag_text = ""  # Don't include in main copy

    fold_at_val = specs.get("fold_at")
    result = {
        "platform": platform,
        "copy": adapted,
        "char_count": len(adapted),
        "char_limit": specs["char_limit"],
        "within_limit": len(adapted) <= specs["char_limit"],
        "fold_at": fold_at_val,
        "hook_visible": adapted[:fold_at_val] if fold_at_val else adapted[:100],
        "hashtags": hashtag_text,
        "hashtag_placement": specs.get("hashtag_placement", "inline"),
        "first_comment": first_comment,
    }

    return result


def generate_bilingual(copy_text, platform, primary_lang="en", secondary_lang=None, mode="separate_posts"):
    """Generate bilingual copy variants."""
    if not secondary_lang:
        return {"primary": copy_text, "secondary": None, "mode": mode}

    # In actual use, Claude generates the translation. This function structures the output.
    return {
        "primary": copy_text,
        "primary_lang": primary_lang,
        "secondary": f"[TRANSLATE TO {secondary_lang}]: {copy_text}",
        "secondary_lang": secondary_lang,
        "mode": mode,
        "note": "Secondary copy requires translation. Use Claude or connected translation MCP."
    }


def main():
    parser = argparse.ArgumentParser(description="SocialForge Copy Adapter")
    parser.add_argument("--text", required=True, help="Source copy text")
    parser.add_argument("--platform", required=True, help="Target platform")
    parser.add_argument("--brand", default=None, help="Brand slug for hashtags")
    parser.add_argument("--cta", default=None, help="Call-to-action text or URL")
    parser.add_argument("--secondary-lang", default=None, help="Secondary language for bilingual posts")
    parser.add_argument("--bilingual-mode", default="separate_posts", choices=["separate_posts", "bilingual_single_post", "language_per_platform"])
    parser.add_argument("--campaign-hashtags", nargs="*", default=None, help="Campaign-specific hashtags")
    parser.add_argument("--list-platforms", action="store_true")
    args = parser.parse_args()

    if args.list_platforms:
        print(json.dumps(PLATFORM_LIMITS, indent=2))
        return

    brand_hashtags = []
    if args.brand:
        config_path = WORKSPACE / "brands" / args.brand / "brand-config.json"
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding="utf-8"))
            brand_hashtags = config.get("brand_hashtags", {}).get("always_include", [])

    if args.campaign_hashtags:
        brand_hashtags.extend(args.campaign_hashtags)

    result = adapt_for_platform(args.text, args.platform, brand_hashtags, args.cta)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
