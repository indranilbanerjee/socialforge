#!/usr/bin/env python3
"""
adapt_copy.py — Adapt social media copy for platform-specific requirements.
Handles character limits, hashtag optimization, and CTA formatting.
"""

import argparse
import json
import os
import re
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
    "threads": {"char_limit": 500, "hashtag_limit": 3, "link": "direct"},
    "bluesky": {"char_limit": 300, "hashtag_limit": 2, "hashtag_placement": "tag_facets", "link": "direct"},
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


def _always_include_hashtags(value):
    """Pull the always-include hashtags out of either documented shape.

    references/brand-config-schema.md documents `brand_hashtags` as a plain
    array (["#AcmeCorp", "#BuildBetter"]); the engineering spec documents an
    object ({"always_include": [...], "campaign_hashtags": {...}}). Brands
    written from the reference schema previously crashed this script with
    AttributeError, so accept both and ignore anything else.
    """
    if isinstance(value, list):
        return [h for h in value if isinstance(h, str)]
    if isinstance(value, dict):
        return [h for h in value.get("always_include", []) if isinstance(h, str)]
    return []


_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)


def render_cta(cta, specs, cta_keyword=None):
    """Turn the intended call-to-action into the platform's actual mechanism.

    A CTA is not a string you append — it is a mechanism that differs per
    platform. On link platforms the CTA (URL and all) works as written. On
    bio-link platforms (Instagram, TikTok) a pasted URL is dead weight: the
    link lives in the profile, and the caption's job is to name the offer and
    route the reader there — or, when the brand runs a comment-keyword
    automation, to ask for the keyword.

    This function used to be the bug: on bio platforms it appended a bare
    "Link in bio" and threw the actual CTA away, so the offer the caption was
    supposed to sell never appeared on the two platforms where captions matter
    most.
    """
    if not cta:
        return None
    if specs.get("link") != "bio":
        return cta

    keyword = (cta_keyword or "").strip()
    if keyword:
        # Brand runs a comment-keyword automation: the keyword IS the mechanism.
        return f'Comment "{keyword}" and we\'ll send you the link.'

    offer = _URL_RE.sub("", cta).strip(" \t-–—:,.")
    if offer:
        return f"{offer} — link in bio."
    # The CTA was only a URL; nothing to name, so route to the bio plainly.
    return "Link in bio."


def adapt_for_platform(copy_text, platform, brand_hashtags=None, cta=None, cta_keyword=None):
    """Adapt copy for a specific platform."""
    specs = PLATFORM_LIMITS.get(platform)
    if not specs:
        return {"error": f"Unknown platform: {platform}"}

    # Render the CTA first: the room it needs must be reserved BEFORE
    # truncation. It used to be appended after, so a limit-length post plus its
    # CTA overflowed the platform limit and the script shipped copy it had
    # itself just measured as too long.
    rendered_cta = render_cta(cta, specs, cta_keyword)
    cta_block = f"\n\n{rendered_cta}" if rendered_cta else ""

    adapted = copy_text

    # Truncate to fold point (for preview visibility) or optimal limit
    fold_at = specs.get("fold_at")
    limit = specs.get("optimal_limit", specs["char_limit"])
    body_limit = max(1, limit - len(cta_block))

    if fold_at and len(copy_text) > fold_at:
        # For platforms with "see more" fold: ensure hook is in first N chars
        # Full copy still saved, but first fold_at chars must be compelling
        adapted = copy_text  # Keep full copy
        if len(adapted) > body_limit:
            adapted = truncate_smart(adapted, body_limit)
    else:
        adapted = truncate_smart(adapted, body_limit)

    adapted += cta_block

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
        "cta_mechanism": ("comment-keyword" if (cta and cta_keyword and specs.get("link") == "bio")
                          else "bio-link" if (cta and specs.get("link") == "bio")
                          else "direct-link" if cta else None),
        "cta_rendered": rendered_cta,
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
    # Required for an adaptation, but must stay optional so --list-platforms works
    parser.add_argument("--text", help="Source copy text")
    parser.add_argument("--platform", help="Target platform")
    parser.add_argument("--brand", default=None, help="Brand slug for hashtags")
    parser.add_argument("--cta", default=None, help="Call-to-action text or URL")
    parser.add_argument("--cta-keyword", default=None,
                        help="Comment-keyword for bio-link platforms when the brand runs a "
                             "comment automation (e.g. GUIDE). Falls back to brand config "
                             "cta_keyword; without one, the CTA names the offer + 'link in bio'.")
    parser.add_argument("--secondary-lang", default=None, help="Secondary language for bilingual posts")
    parser.add_argument("--bilingual-mode", default="separate_posts", choices=["separate_posts", "bilingual_single_post", "language_per_platform"])
    parser.add_argument("--campaign-hashtags", nargs="*", default=None, help="Campaign-specific hashtags")
    parser.add_argument("--list-platforms", action="store_true")
    args = parser.parse_args()

    if args.list_platforms:
        print(json.dumps(PLATFORM_LIMITS, indent=2))
        return

    missing = [flag for flag, value in (("--text", args.text), ("--platform", args.platform)) if not value]
    if missing:
        parser.error("the following arguments are required: " + ", ".join(missing))

    brand_hashtags = []
    cta_keyword = args.cta_keyword
    if args.brand:
        config_path = WORKSPACE / "brands" / args.brand / "brand-config.json"
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding="utf-8"))
            brand_hashtags = _always_include_hashtags(config.get("brand_hashtags"))
            if not cta_keyword:
                value = config.get("cta_keyword")
                cta_keyword = value if isinstance(value, str) else None

    if args.campaign_hashtags:
        brand_hashtags.extend(args.campaign_hashtags)

    result = adapt_for_platform(args.text, args.platform, brand_hashtags, args.cta,
                                cta_keyword=cta_keyword)

    # Bilingual variants when a secondary language is requested
    if args.secondary_lang and "error" not in result:
        primary_lang = "en"
        if args.brand:
            config_path = WORKSPACE / "brands" / args.brand / "brand-config.json"
            if config_path.exists():
                config = json.loads(config_path.read_text(encoding="utf-8"))
                languages = config.get("languages") or []
                if languages:
                    primary_lang = languages[0]
        result["bilingual"] = generate_bilingual(
            result["copy"], args.platform, primary_lang, args.secondary_lang, args.bilingual_mode
        )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
