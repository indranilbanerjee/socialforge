#!/usr/bin/env python3
"""
adapt_copy.py — Adapt social media copy for platform-specific requirements.
Handles character limits, hashtag optimization, and CTA formatting.

The limits are data: scripts/platform_limits.json carries every number with
its source URL, the date it was checked and its status (confirmed, differs or
unsourced), and `--sources` prints that record. X is counted the way X counts
(emoji and CJK weigh 2, every URL weighs 23); every other platform by plain
characters (Python len). Hashtags past a platform's cap are never lost
silently: they come back in `hashtags_dropped`.
"""

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

# Persistent storage: prefer ${CLAUDE_PLUGIN_DATA} (survives sessions/updates),
# fall back to ~/socialforge-workspace (legacy/local)
_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("PLUGIN_DATA") or ""
if _plugin_data and Path(_plugin_data).exists():
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
    WORKSPACE = Path.home() / "socialforge-workspace"

# The limits table sits beside this script.
PLATFORMS_PATH = Path(__file__).resolve().parent / "platform_limits.json"

_COUNT_METHODS = ("x_weighted",)


def _x_weighted_config(raw):
    """The X counting rules recorded in the data file (`counting.x_weighted.config`,
    field names as in twitter-text's config/v3.json), checked and unpacked."""
    cfg = raw["counting"]["x_weighted"]["config"]
    ranges = []
    for item in cfg["ranges"]:
        start, end, weight = item["start"], item["end"], item["weight"]
        if (not all(isinstance(v, int) and not isinstance(v, bool) for v in (start, end, weight))
                or start > end or weight < 0):
            raise ValueError("counting.x_weighted.config.ranges needs integer start <= end and weight >= 0")
        ranges.append((start, end, weight))
    scale, default, url_len = cfg["scale"], cfg["defaultWeight"], cfg["transformedURLLength"]
    if not all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in (scale, default, url_len)):
        raise ValueError("counting.x_weighted.config needs positive integer scale, "
                         "defaultWeight and transformedURLLength")
    return {"scale": scale, "default_weight": default, "url_length": url_len, "ranges": ranges}


def _load_platforms(path):
    """Read the limits table. Returns (limits_by_platform, raw_data, error)."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        platforms = raw["platforms"]
        limits = {}
        for name, entry in platforms.items():
            spec = entry["limits"]
            if not isinstance(spec.get("char_limit"), int) or spec["char_limit"] < 1:
                raise ValueError(f"{name}: limits.char_limit must be a positive integer")
            method = spec.get("count_method")
            if method is not None and method not in _COUNT_METHODS:
                raise ValueError(f"{name}: limits.count_method must be one of {', '.join(_COUNT_METHODS)}")
            if method == "x_weighted":
                _x_weighted_config(raw)
            limits[name] = spec
        if not limits:
            raise ValueError("no platforms listed")
        return limits, raw, None
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return {}, {}, f"could not load {path}: {exc}"


PLATFORM_LIMITS, _RAW_DATA, _DATA_ERROR = _load_platforms(PLATFORMS_PATH)
_X_WEIGHTED = _x_weighted_config(_RAW_DATA) if any(
    spec.get("count_method") == "x_weighted" for spec in PLATFORM_LIMITS.values()) else None


def _provenance(raw):
    """What --sources prints: per platform, where each number came from."""
    out = {}
    for name, entry in raw["platforms"].items():
        confirmed = entry.get("confirmed", [])
        differs = entry.get("differs", [])
        out[name] = {
            "source": entry.get("source"),
            "checked": entry.get("checked"),
            "status": {key: ("confirmed" if key in confirmed else "differs" if key in differs else "unsourced")
                       for key in entry["limits"]},
            "confirmed": confirmed,
            "differs": differs,
            "unsourced": entry.get("unsourced", []),
            "also_read": entry.get("also_read", []),
            "notes": entry.get("notes"),
        }
    return out


# A URL as X counts it for weighting: starts with http://, https:// or www.,
# is not glued to a word, and does not end in sentence punctuation (that
# stays ordinary text, which can only make the count higher than X's).
_X_URL_RE = re.compile(
    r"(?<![\w@#$.\-/])(?:https?://|www\.)\S*[^\s.,;:!?)\]}'\"”’»]", re.IGNORECASE)


def _plain_weight(text, default, ranges):
    total = 0
    for char in text:
        code = ord(char)
        for start, end, weight in ranges:
            if start <= code <= end:
                total += weight
                break
        else:
            total += default
    return total


def weighted_length(text, config):
    """X's weighted length of `text` under `config` (see _x_weighted_config),
    rounded up to whole characters.

    The text is normalised to NFC first, as X does. A code point inside a
    configured range then weighs that range's weight, every other code point
    the default (so emoji and CJK weigh 2), and every URL weighs the
    transformed URL length (23) however long it is. One thing the reference
    counter does is left out on purpose: it parses an emoji sequence as one
    emoji (2), while here each code point of the sequence is weighed, which can
    only make the count higher.
    """
    text = unicodedata.normalize("NFC", text)
    scale, default, ranges = config["scale"], config["default_weight"], config["ranges"]
    total = 0
    position = 0
    for match in _X_URL_RE.finditer(text):
        total += _plain_weight(text[position:match.start()], default, ranges)
        total += config["url_length"] * scale
        position = match.end()
    total += _plain_weight(text[position:], default, ranges)
    return -(-total // scale)


def _measurer(specs):
    """The length function for a platform: len() unless its limits say otherwise."""
    if specs.get("count_method") == "x_weighted":
        return lambda text: weighted_length(text, _X_WEIGHTED)
    return len


def _fit(text, budget, measure):
    """The longest prefix length whose measure is within budget (0 if none)."""
    low, high = 0, len(text)
    while low < high:
        mid = (low + high + 1) // 2
        if measure(text[:mid]) <= budget:
            low = mid
        else:
            high = mid - 1
    return low


def truncate_smart(text, limit, measure=len):
    """Truncate at last complete sentence that fits.

    `measure` is how the platform counts length: len for most platforms, X's
    weighted count for X. With the default, the slicing is exactly what it
    always was.
    """
    if measure(text) <= limit:
        return text
    if measure is len:
        keep, keep_ellipsis = limit, limit - 3
    else:
        keep, keep_ellipsis = _fit(text, limit, measure), _fit(text, limit - 3, measure)
    truncated = text[:keep]
    last_period = truncated.rfind(".")
    last_excl = truncated.rfind("!")
    last_quest = truncated.rfind("?")
    best_break = max(last_period, last_excl, last_quest)
    if best_break > keep * 0.5:
        candidate = truncated[:best_break + 1]
        if measure(candidate) <= limit:
            return candidate
    return truncated[:keep_ellipsis] + "..."


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

    # Length is counted the way the platform counts it: X by weight (URLs
    # count 23, emoji and CJK 2), every other platform by plain len().
    count = _measurer(specs)

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
    body_limit = max(1, limit - count(cta_block))

    if fold_at and len(copy_text) > fold_at:
        # For platforms with "see more" fold: ensure hook is in first N chars
        # Full copy still saved, but first fold_at chars must be compelling
        adapted = copy_text  # Keep full copy
        if count(adapted) > body_limit:
            adapted = truncate_smart(adapted, body_limit, count)
    else:
        adapted = truncate_smart(adapted, body_limit, count)

    adapted += cta_block

    # Prepare hashtags. Whatever the cap leaves out is reported, never lost silently.
    all_hashtags = list(brand_hashtags or [])
    hashtag_limit = specs.get("hashtag_limit", 5)
    hashtag_text = " ".join(all_hashtags[:hashtag_limit])
    hashtags_dropped = all_hashtags[hashtag_limit:]

    # Instagram first-comment strategy: hashtags go in first comment, not caption
    first_comment = None
    if specs.get("hashtag_placement") == "first_comment":
        first_comment = hashtag_text
        hashtag_text = ""  # Don't include in main copy

    fold_at_val = specs.get("fold_at")
    result = {
        "platform": platform,
        "copy": adapted,
        "char_count": count(adapted),
        "char_limit": specs["char_limit"],
        "within_limit": count(adapted) <= specs["char_limit"],
        "count_method": specs.get("count_method", "code_points"),
        "cta_mechanism": ("comment-keyword" if (cta and cta_keyword and specs.get("link") == "bio")
                          else "bio-link" if (cta and specs.get("link") == "bio")
                          else "direct-link" if cta else None),
        "cta_rendered": rendered_cta,
        "fold_at": fold_at_val,
        "hook_visible": adapted[:fold_at_val] if fold_at_val else adapted[:100],
        "hashtags": hashtag_text,
        "hashtag_placement": specs.get("hashtag_placement", "inline"),
        "first_comment": first_comment,
        "hashtags_dropped": hashtags_dropped,
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
    parser.add_argument("--campaign-hashtags", nargs="*", default=None, help="Campaign-specific hashtags (any past the platform's cap come back in hashtags_dropped)")
    parser.add_argument("--list-platforms", action="store_true",
                        help="Print the limits the script reads")
    parser.add_argument("--sources", action="store_true",
                        help="Print where each platform's limits came from and what is "
                             "confirmed, differs or unsourced")
    args = parser.parse_args()

    if _DATA_ERROR:
        print(json.dumps({"error": _DATA_ERROR,
                          "recovery": "Restore scripts/platform_limits.json, or fix the field named above."},
                         indent=2))
        sys.exit(1)

    if args.list_platforms:
        print(json.dumps(PLATFORM_LIMITS, indent=2))
        return
    if args.sources:
        print(json.dumps(_provenance(_RAW_DATA), indent=2))
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
