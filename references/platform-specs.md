# Platform Specifications Reference

Complete dimension, character limit, and format specs for all supported social media platforms.

## Image Dimensions

| Platform | Format | Width | Height | Ratio | Notes |
|----------|--------|-------|--------|-------|-------|
| LinkedIn | Feed post | 1200 | 627 | 1.91:1 | Recommended landscape |
| LinkedIn | Square | 1080 | 1080 | 1:1 | Alternative feed format |
| LinkedIn | Carousel/Doc | 1080 | 1080 | 1:1 | Per-slide dimension |
| Instagram | Feed square | 1080 | 1080 | 1:1 | Default feed format |
| Instagram | Feed portrait | 1080 | 1350 | 4:5 | Preferred — more real estate |
| Instagram | Story/Reel | 1080 | 1920 | 9:16 | Full screen vertical |
| Instagram | Carousel | 1080 | 1080 | 1:1 | Per-slide dimension |
| X/Twitter | Post | 1600 | 900 | 16:9 | Landscape recommended |
| X/Twitter | Square | 1080 | 1080 | 1:1 | Alternative |
| Facebook | Feed | 1200 | 630 | 1.91:1 | Same as LinkedIn landscape |
| Facebook | Square | 1080 | 1080 | 1:1 | Alternative |
| Facebook | Story | 1080 | 1920 | 9:16 | Full screen vertical |
| YouTube | Thumbnail | 1280 | 720 | 16:9 | Mandatory for videos |
| Pinterest | Pin | 1000 | 1500 | 2:3 | Tall portrait preferred |
| TikTok | Video | 1080 | 1920 | 9:16 | Full screen vertical |

## Character Limits

The numbers `adapt_copy.py` enforces live in `scripts/platform_limits.json`, each with a source URL, the date it was checked and a status; `python scripts/adapt_copy.py --sources` prints the record. Status below is as of 2026-10-04: **confirmed** means a primary platform page says it, **unsourced** means SocialForge's working value with no readable primary page. Optimal and Fold At are working guidance, not platform rules.

| Platform | Max Length | Status | Optimal | Fold At | Notes |
|----------|-----------|--------|---------|---------|-------|
| LinkedIn | 3,000 | confirmed | 500-700 | 140 | "...see more" at 140 chars (a working value) |
| Instagram | 2,200 | unsourced | 500-1000 | First line | First line is the hook |
| X/Twitter | 280 | confirmed | 240 | — | Hard limit, no fold; counted by weight, see below |
| Facebook | 63,206 | unsourced | 300-500 | 400 | Optimal is short; the adapter cuts at 500 |
| YouTube | 5,000 | confirmed | 200-500 | 200 | First 200 visible |
| TikTok | 2,200 | unsourced | 100-300 | — | Third-party pages report 4,000, unconfirmed; 2,200 stays as the safe cap |
| Pinterest | 800 | confirmed | 200-300 | — | Description for SEO (title: 100) |
| Threads | 500 | confirmed | — | — | Emojis count as UTF-8 bytes |
| Bluesky | 300 | confirmed | — | — | 300 graphemes |

### How platforms count

- **X** counts by weight, not characters (twitter-text v3 config, read 2026-10-04): code points 0-4351, 8192-8205, 8208-8223 and 8242-8247 weigh 1, every other code point weighs 2 (so emoji and CJK cost 2), every URL costs 23 however long it is, and the maximum is 280. `adapt_copy.py` implements this for X, so X's `char_count` is a weighted length. It over-counts emoji sequences (each code point of a family emoji is weighed, where X weighs the whole sequence 2) and does not normalise to NFC, both in the safe direction. It counts a bare domain (no `http://`, `https://` or `www.`) as plain text although X links it, so a long bare domain counts low. X's docs table groups "Other Unicode" at weight 2, but the config gives weight 1 to everything up to U+10FF (Cyrillic, Greek, Hebrew, Arabic, Devanagari and Thai included); the script follows the config.
- **Bluesky** counts 300 graphemes; `adapt_copy.py` counts code points, which can only over-count.
- **Threads** counts an emoji as its number of UTF-8 bytes; `adapt_copy.py` counts an emoji as 1, so it under-counts emoji on Threads (not implemented).
- Every other platform: plain characters.

## Hashtag Limits

| Platform | Platform maximum | Script cap | Optimal | Placement |
|----------|------------------|------------|---------|-----------|
| LinkedIn | unsourced | 5 | 3-5 | End of post |
| Instagram | 5 (Instagram's @creators account, 2025-12-18) | 5 | 3-5 | First comment (SocialForge default) |
| X/Twitter | no separate limit stated; tags count toward the 280 | 2 | 1-2 | Inline |
| Facebook | unsourced | 3 | 1-3 | End of post |
| YouTube | 60 (more than 60 and all are ignored; 3 show above the title) | 5 | 3-5 | Description |
| TikTok | unsourced | 10 | 3-5 | End of caption |
| Pinterest | unsourced | 20 | 5-10 | Description |
| Threads | 1 topic tag per post | 1 | 1 | Inline |
| Bluesky | 8 tags in the post record | 2 | 1-2 | Tag facets |

The script cap is how many hashtags `adapt_copy.py` keeps; the rest come back in `hashtags_dropped`, so a cap never removes a tag without saying so. Where the maximum is "unsourced" the cap is SocialForge's own working value.

## Video Specs

| Platform | Max Duration | Recommended | Min Resolution | Format |
|----------|-------------|-------------|----------------|--------|
| LinkedIn | 10 min | 30-90s | 720p | MP4 |
| Instagram Reel | 3 min | 15-30s | 720p | MP4 |
| Instagram Story | 60s | 15s | 720p | MP4 |
| X/Twitter | 2:20 | 15-45s | 720p | MP4 |
| Facebook | 240 min | 15-60s | 720p | MP4 |
| YouTube | 12 hours | 8-15 min | 1080p | MP4 |
| YouTube Short | 3 min | 15-60s | 720p (9:16) | MP4 |
| TikTok | 60 min | 15-60s | 720p (9:16) | MP4 |

## Supported Content Formats

| Platform | Static | Carousel | Video | Story | Reel/Short | Text Only | Poll | Document |
|----------|--------|----------|-------|-------|-----------|-----------|------|----------|
| LinkedIn | ✓ | ✓ (PDF) | ✓ | — | — | ✓ | ✓ | ✓ |
| Instagram | ✓ | ✓ | — | ✓ | ✓ | — | — | — |
| X/Twitter | ✓ | ✓ (multi-image) | ✓ | — | — | ✓ | ✓ | — |
| Facebook | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| YouTube | ✓ (community) | — | ✓ | — | ✓ | ✓ | ✓ | — |
| TikTok | — | — | ✓ | — | ✓ | — | — | — |
| Pinterest | ✓ | ✓ | ✓ | ✓ | — | — | — | — |
