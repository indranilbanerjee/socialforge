# SocialForge — Technical Operations Reference

**How it works under the hood.** This document explains the logic behind every pipeline phase, how data flows, what's deterministic vs AI-driven, evaluation parameters, folder structures, and fallback mechanisms.

---

## Table of Contents

1. [Pipeline Architecture](#1-pipeline-architecture)
2. [Calendar Parsing Logic](#2-calendar-parsing-logic)
3. [Asset Indexing Logic](#3-asset-indexing-logic)
4. [Asset Matching Algorithm](#4-asset-matching-algorithm)
5. [Creative Production Logic](#5-creative-production-logic)
6. [AI Models & Fallbacks](#6-ai-models--fallbacks)
7. [Copy Adaptation Logic](#7-copy-adaptation-logic)
8. [Compliance Engine](#8-compliance-engine)
9. [Quality Evaluation System](#9-quality-evaluation-system)
10. [Carousel Rendering Pipeline](#10-carousel-rendering-pipeline)
11. [Video Production Logic](#11-video-production-logic)
12. [Approval State Machine](#12-approval-state-machine)
13. [Batch vs Individual Processing](#13-batch-vs-individual-processing)
14. [Folder Structure & File Organization](#14-folder-structure--file-organization)
15. [Deterministic vs Non-Deterministic Steps](#15-deterministic-vs-non-deterministic-steps)
16. [API Keys & When They're Needed](#16-api-keys--when-theyre-needed)
17. [Cost Tracking](#17-cost-tracking)
18. [Cross-Platform Compatibility](#18-cross-platform-compatibility)

---

## 1. Pipeline Architecture

The full pipeline has 8 phases. Each phase has defined inputs, outputs, a quality gate, and a fallback.

```
Phase 0: PARSE CALENDAR ────────────→ calendar-data.json
  Gate: All required fields present    │
  Fallback: Ask user for missing       │
                                       ▼
Phase 1: MATCH ASSETS ──────────────→ asset-matches.json
  Gate: User confirms matches          │
  Fallback: Manual override            │
                                       ▼
Phase 2: PRODUCE CREATIVE ──────────→ production/week-{N}/{PostID}-.../versions/
  Gate: Quality score ≥7.0/10          │
  Fallback: Regenerate (max 3x)        │
                                       ▼
Phase 3: ADAPT COPY ────────────────→ production/week-{N}/{PostID}-.../copy/
  Gate: Compliance PASSED              │
  Fallback: Flag for human edit        │
                                       ▼
Phase 4: CREATE PREVIEWS ───────────→ production/week-{N}/{PostID}-.../final/
  Gate: All platforms rendered          │
  Fallback: Raw image + copy           │
                                       ▼
Phase 5: BUILD REVIEW GALLERY ──────→ review/gallery.html
  Gate: Gallery accessible              │
  Fallback: Show posts in conversation  │
                                       ▼
Phase 6: MANAGE REVIEWS ────────────→ status-tracker.json (ASYNC)
  Gate: All posts APPROVED/FINAL       │
  Fallback: Escalation after N days     │
                                       ▼
Phase 7: FINALIZE ──────────────────→ FINAL/ folder
  Gate: All approval gates passed      │
  Fallback: --force for emergency      │
```

**Each phase writes data. Each phase reads the previous phase's output.** There is no skipping -- Phase 2 cannot run without Phase 1's asset-matches.json.

### Phase Dependencies

The dependency chain is strictly linear for the first five phases. Phase 6 (reviews) is asynchronous and can run over days or weeks. Phase 7 (finalize) requires all posts to reach terminal approval states (APPROVED_INTERNAL, APPROVED_CLIENT, APPROVED_CEO, or FINAL depending on tier).

### Phase Interruption & Resume

If the pipeline is interrupted (session ends, user stops, error), the status-tracker.json records which phase was last completed for each post. On resume, the pipeline reads the tracker and picks up from the last incomplete phase. No work is lost -- all intermediate outputs (images, copy files, previews) persist on disk.

### Data Flow Between Phases

```
Phase 0 writes: calendar-data.json
Phase 1 reads:  calendar-data.json + asset-index.json
Phase 1 writes: asset-matches.json + updates calendar-data.json (production block)
Phase 2 reads:  calendar-data.json + asset-matches.json + brand-config.json
Phase 2 writes: production/week-{N}/{PostID}-.../versions/*.png + status-tracker.json
Phase 3 reads:  calendar-data.json + brand-config.json + compliance-rules.json
Phase 3 writes: production/week-{N}/{PostID}-.../copy/*.txt
Phase 4 reads:  .../versions/ + .../copy/ + brand-config.json
Phase 4 writes: production/week-{N}/{PostID}-.../final/*.png
Phase 5 reads:  everything in production/ + calendar-data.json + status-tracker.json
Phase 5 writes: review/gallery.html
Phase 6 reads:  status-tracker.json + approval-chain.json
Phase 6 writes: status-tracker.json (state transitions)
Phase 7 reads:  all production/ + status-tracker.json
Phase 7 writes: FINAL/ folder tree
```

---

## 2. Calendar Parsing Logic

**Execution:** parse-calendar skill (Claude-driven) -- no Python script. Claude reads the document directly and extracts structured data.

### What Happens When You Upload a DOCX

1. **Format detection** -- Claude reads the file and identifies it as DOCX (vs XLSX/Notion/text).
2. **Table extraction** -- Most agency calendars use tables. Claude extracts rows where each row = one post.
3. **Section scanning** -- Some calendars have per-post creative briefs after the main table. Claude extracts these as visual/copy briefs.
4. **Field mapping** -- For each post, Claude maps columns/sections to schema fields:

| Calendar Column | Maps To | Required? | If Missing |
|-----------------|---------|-----------|------------|
| Date | `post.date` | Yes | Ask user |
| Platform | `post.platforms[].key` | Yes | Ask user |
| Post # / ID | `post.post_id` | Auto-generated if absent | P01, P02, P03... |
| Content Bucket | `post.content_bucket` | Yes | Ask user |
| Tier | `post.tier` | Yes | Default: HUB |
| Format | `post.content_type` | Yes | Default: static |
| Post Hint / Description | `post.title` | Yes | Derive from bucket |
| Copy Option A | `post.copy.option_a` | Recommended | Generate during copy phase |
| Copy Option B | `post.copy.option_b` | Optional | Skip |
| Image Direction / Visual Brief | `post.visual.direction_a` | Recommended | Use bucket + tier to infer |
| Carousel Slide Count | `post.carousel_details.slide_count` | If carousel | Default: 8 |
| Video Duration | `post.video_details.duration_seconds` | If video | Default: 30s |
| Hashtags | `post.copy.hashtags` | Optional | Brand hashtags only |
| CTA | `post.copy.first_comment` or inline | Optional | Default: none |
| Dependencies | `post.dependencies` | Optional | Auto-detect from text |
| Notes | `post.production_notes` | Optional | None |

5. **Cross-reference validation** -- Every platform mentioned must exist in the brand's platform-config.json. Unknown platforms are flagged immediately.
6. **Content type classification** -- If the format column says "carousel", "slides", or a slide count is mentioned, type = carousel. If "video", "reel", "clip", type = video. If "text", "no image", type = text_only.
7. **Dependency detection** -- Scans for phrases like "needs approval", "requires filming", "client permission needed" and extracts them as dependency items.
8. **Summary generation** -- Total posts, per-platform breakdown, tier distribution, content type mix.
9. **User confirmation** -- Shows parsed summary. User confirms or fixes issues before proceeding.

### What Gets Stored: calendar-data.json

```json
{
  "brand": "greenleaf-organics",
  "month": "2026-04",
  "summary": {
    "total_posts": 28,
    "posts_per_platform": {"linkedin": 12, "instagram": 10, "facebook": 6},
    "tier_distribution": {"HERO": 4, "HUB": 14, "HYGIENE": 10},
    "content_type_distribution": {"static": 16, "carousel": 6, "video": 4, "text_only": 2}
  },
  "posts": [
    {
      "post_id": 1,
      "date": "2026-04-01",
      "day_of_week": "Wednesday",
      "week_number": 1,
      "title": "Introducing our new Avocado Oil product line",
      "content_bucket": "Product Launch",
      "tier": "HERO",
      "platforms": [
        {"key": "linkedin", "format": "static", "image_size": "1200x627"},
        {"key": "instagram", "format": "static", "image_size": "1080x1350"},
        {"key": "facebook", "format": "static", "image_size": "1200x630"}
      ],
      "copy": {"option_a": "Full copy text here...", "option_b": null, "hashtags": ["#AvocadoOil"]},
      "visual": {"direction_a": "Product bottle on rustic wooden counter, morning light, fresh avocados", "direction_b": null},
      "content_type": "static",
      "production": {
        "creative_mode": null,
        "matched_asset_id": null,
        "style_references": []
      }
    }
  ]
}
```

The `production` block starts empty -- it gets populated by Phase 1 (asset matching).

### XLSX Parsing

Same logic, but columns are read from spreadsheet headers via openpyxl. If column names do not match expected fields, Claude asks the user to confirm mapping: "Column D is labeled 'Image Description' -- should I map this to visual_brief?"

### Notion Parsing

Requires Notion MCP connector. Claude queries the Notion database and maps properties to schema fields. Expected properties: Date, Platform, Copy, Image Brief, Content Bucket, Tier, Status.

---

## 3. Asset Indexing Logic

**Script:** `index_assets.py` -- deterministic scan + AI vision analysis

### Step-by-Step

1. **Scan source directory** -- Recursively find all .jpg/.jpeg/.png/.webp files under the asset source path.
2. **Incremental detection** -- Compare the file list against the existing asset-index.json. Only new or modified files (by modification timestamp) are sent for AI analysis. Already-indexed files are skipped.
3. **For each new image** -- Call Gemini Vision API (`gemini-3-flash`) with a structured prompt requesting JSON analysis:
   - Description (2-3 sentences of what the image shows)
   - Subjects (person, product, office, event, nature, abstract, etc.)
   - Tags (15-20 descriptive keywords covering subject, setting, mood, style, colors, composition)
   - Dominant colors (5 hex codes)
   - Mood, lighting, setting
   - What social media posts this suits (3-5 natural language descriptions)
   - Background type and removability (transparent, solid white, complex, etc.)
   - Quality assessment (high/medium/low)
   - Style reference worthiness (true/false)

4. **Build metadata** -- File dimensions (via Pillow), size in MB, format, relative path from the asset library root.
5. **Crop feasibility** -- For each platform's aspect ratio defined in platform-config.json, calculate whether the image can be cropped to that ratio without losing key content. This is a deterministic dimension calculation: if the subject occupies the center 60% of the frame, and the crop requires removing more than 40% of either axis, it is flagged as infeasible.
6. **Style reference selection** -- After indexing completes, the script suggests 5-8 photos that best represent the brand's visual DNA (high quality, good variety of settings, style_reference_worthy = true). The user confirms or adjusts.
7. **Low-quality flagging** -- Images below 800px in either dimension are flagged as unsuitable for social media production.

### What Gets Stored: asset-index.json

Each asset entry contains approximately 30 fields. The most critical for downstream matching:
- `tags` -- 15-20 keywords derived from AI analysis
- `suitable_for` -- Natural language descriptions of what posts this image suits
- `background_removable` -- Determines if ANCHOR_COMPOSE mode is possible
- `is_style_reference` -- Used for STYLE_REFERENCED mode generation
- `platforms_compatible` -- Per-platform crop feasibility with recommended crop coordinates
- `usage_history` -- Array of previous uses (month, post IDs, platforms, dates)

### Deterministic vs AI

| Step | Type | Can Fail? | Fallback |
|------|------|-----------|----------|
| File scanning | Deterministic | No | -- |
| Dimension reading (Pillow) | Deterministic | Rare (corrupt file) | Skip file, log warning |
| AI vision analysis | Non-deterministic | Yes (API timeout, rate limit) | Metadata-only entry (dimensions, filename, folder) |
| Tag generation | Non-deterministic | Part of AI call | Empty tags if AI fails |
| Crop feasibility | Deterministic | No | Pure math from dimensions |
| Style ref suggestion | Non-deterministic | Part of AI judgment | User selects manually |

### Rate Limiting

Gemini Vision free tier allows approximately 500 requests/day. For large libraries (200+ images), `index_assets.py` enforces a 2-second delay between API calls. The `--new-only` flag ensures re-indexing only processes new files, avoiding unnecessary API costs.

---

## 4. Asset Matching Algorithm

**Script:** `match_assets.py` -- fully deterministic scoring

### The Priority Chain

Before the scoring formula runs, explicit references are resolved first:

```
PRIORITY 1: Does the calendar brief reference a specific asset by name?
  YES -> Load that asset -> Assign creative mode based on brief language
  NO  -> Continue to Priority 2

PRIORITY 2: Does the scoring formula find a high-confidence match (score > 0.8)?
  YES -> Recommend ANCHOR_COMPOSE or ENHANCE_EXTEND
  NO  -> Continue to Priority 3

PRIORITY 3: Partial matches (score 0.3-0.8)?
  YES -> Recommend STYLE_REFERENCED (use matches as reference images)
  NO  -> Continue to Priority 4

PRIORITY 4: No relevant brand assets found
  -> Assign PURE_CREATIVE (or CAROUSEL_TEMPLATE for carousels)
  -> If content_type is 'video', assign NEEDS_REAL_ASSET + generate script/storyboard only
```

### The 5-Factor Scoring Formula

```
FINAL_SCORE = (TAG_OVERLAP * 0.30) + (SUITABILITY * 0.25) + (BUCKET_MATCH * 0.20)
            + (CROP_FEASIBILITY * 0.15) - (FRESHNESS_PENALTY * 0.10)
```

**Factor 1: Tag Overlap (weight 0.30)**
```
post_keywords = extract from title + content_bucket + visual_brief
asset_tags = from AI vision analysis in asset-index.json
score = |post_keywords INTERSECTION asset_tags| / |post_keywords|
```
Normalized 0-1. Higher means more keyword overlap between what the post needs and what the asset contains.

**Factor 2: Suitability Match (weight 0.25)**
```
For each of the asset's "suitable_for" descriptions:
  If any word matches post context -> +0.25 (capped at 1.0)
```
This is semantic matching, not exact keyword. A post about "product launch" matches an asset suitable for "product showcase posts" and "new announcement content."

**Factor 3: Content Bucket Match (weight 0.20)**
```
If content bucket name appears in asset tags -> 1.0
Else -> 0.0
```
Binary score. An asset tagged with "product launch" gets full marks for a post in the "Product Launch" bucket.

**Factor 4: Crop Feasibility (weight 0.15)**
```
For each platform the post targets:
  Check if asset can be cropped to that platform's aspect ratio
score = platforms_feasible / total_platforms
```
If a post targets LinkedIn (16:9), Instagram (4:5), and Facebook (1.91:1), the asset must be croppable to all three for a perfect score.

**Factor 5: Freshness Penalty (weight 0.10, subtractive)**
```
0 uses this month -> no penalty (0.00)
1 use             -> -0.15
2 uses            -> -0.40
3+ uses           -> -0.70
Same week as previous use -> additional -0.50 (capped at 1.0 total penalty)
```
Prevents the same hero product shot from appearing in every post.

### Score-to-Mode Mapping

| Score Range | Recommended Mode | What It Means |
|-------------|------------------|---------------|
| > 0.8 | ANCHOR_COMPOSE | Perfect match -- use asset as untouchable centerpiece, AI generates around it |
| 0.5 - 0.8 | ENHANCE_EXTEND | Good match -- keep asset as foundation, AI enhances periphery |
| 0.3 - 0.5 | STYLE_REFERENCED | Partial -- asset is not suitable for direct use but can guide AI visual DNA |
| < 0.3 | PURE_CREATIVE | No match -- full AI generation with brand config only |

### What Gets Stored: asset-matches.json

```json
{
  "matches": [
    {
      "post_id": 1,
      "recommendation": "ANCHOR_COMPOSE",
      "primary_asset": {"asset_id": "asset_012", "score": 0.83, "filename": "avocado-oil-bottle.jpg"},
      "alternatives": [{"asset_id": "asset_005", "score": 0.61}],
      "style_references": ["asset_003", "asset_008", "asset_015", "asset_022", "asset_031"],
      "gap_flag": false,
      "gap_note": null
    }
  ],
  "mode_distribution": {"ANCHOR_COMPOSE": 8, "ENHANCE_EXTEND": 5, "STYLE_REFERENCED": 9, "PURE_CREATIVE": 4}
}
```

The user reviews matches before production begins. Any match can be overridden: swap the asset, force a different creative mode, or upload an entirely new image.

---

## 5. Creative Production Logic

**Scripts:** `generate_image.py`, `compose_image.py`, `edit_image.py`, `compose_text_overlay.py`, `resize_image.py`

### ANCHOR_COMPOSE Pipeline (Deterministic + AI)

```
1. Load brand asset                           [Deterministic]
2. Remove background (rembg or threshold)     [Deterministic -- rembg is ML but consistent]
3. Generate AI background scene               [Non-deterministic -- Gemini API]
4. Composite asset onto scene (Pillow)        [Deterministic]
5. Add drop shadow                            [Deterministic -- calculated from alpha channel]
6. Edge feathering (2px Gaussian blur)        [Deterministic]
7. Color temperature matching                 [Deterministic -- RGB analysis + 3% shift]
8. Add text overlay (brand fonts/colors)      [Deterministic]
9. Add logo watermark                         [Deterministic]
10. Resize for each platform                  [Deterministic]
```

Steps 1-2 and 4-10 always produce the same output for the same input. Only Step 3 (AI scene generation) introduces variability. The scene is generated 2-3 times to give the user options.

### Compositing Detail (compose_image.py)

The compositing script handles precise placement:

- **Positioning**: center, left_third (33% from left), right_third (67% from left), or custom X,Y coordinates
- **Scaling**: asset occupies a configurable percentage of canvas width (default 40%), maintaining aspect ratio
- **Shadow**: created from the asset's alpha channel, offset 3-5px down-right, Gaussian-blurred, opacity controlled by settings
- **Edge feathering**: subtle blur at asset edges prevents the hard "cut-out" appearance
- **Color matching**: samples average color temperature of both asset and background, applies a subtle correction (3% max shift) to the asset edges if the difference exceeds a threshold

### ENHANCE_EXTEND Pipeline

```
1. Load brand asset (full photo with background)  [Deterministic]
2. Determine edit type from brief:                 [Non-deterministic -- Claude interprets]
   a) BACKGROUND_EXTENSION (needs wider frame)
   b) MOOD_ENHANCEMENT (needs different feel)
   c) ELEMENT_ADDITION (needs visual additions)
   d) STYLE_TRANSFER (needs polish)
3. Send asset + edit instruction to Gemini         [Non-deterministic]
4. Verify core preservation (SSIM check)           [Deterministic]
5. Add text overlay + logo + resize                [Deterministic]
```

The SSIM (structural similarity) check in step 4 compares the edited image against the original. If SSIM drops below 0.3, the core subject may have been altered too much -- the system warns and flags for human review.

### STYLE_REFERENCED Pipeline

```
1. Load 2-14 style reference images               [Deterministic]
2. Construct 5-layer prompt:                       [Deterministic -- template-based]
   Layer 1: Brand identity (colors, style keywords, mood)
   Layer 2: Post context (bucket, tier, campaign)
   Layer 3: Creative direction (visual brief from calendar)
   Layer 4: Image rules (from brand-config.json)
   Layer 5: Technical (aspect ratio, resolution, platform)
3. Feed refs + prompt to Gemini Nano Banana 2      [Non-deterministic]
4. Quality review (5-dimension scoring)            [Non-deterministic -- but scored numerically]
5. Text overlay + logo + resize                    [Deterministic]
```

Nano Banana 2 (`gemini-3.1-flash-image-preview`) accepts up to 14 reference images per request. The references cause the AI to absorb the brand's visual DNA -- lighting style, color temperature, composition patterns. The output is a new image that looks like it belongs in the same photo library.

### PURE_CREATIVE Pipeline

Same as STYLE_REFERENCED but without reference images in the API call. Only the text prompt and brand-config text guide the generation. Used when no style references are defined or for generic content (festival greetings, industry news reactions) where brand visual DNA is not critical.

### When Things Fail

| Failure | Handling |
|---------|---------|
| AI generation returns no image | Retry once with simplified prompt. If still fails, placeholder image + manual flag |
| Background removal produces artifacts | Flag for manual masking, continue with original background |
| Quality score < 3.0 | Auto-regenerate once with strengthened prompt |
| Quality score 3.0-6.9 | Flag for user review but do not auto-regenerate |
| Quality score >= 7.0 | Pass |
| API timeout (60s) | Retry once. If still fails, placeholder + flag |
| Rate limit (429) | Wait rate_limit_delay_ms, retry up to retry_attempts |
| Content policy block | Log, return failure with "content policy violation" message |
| Total per-post timeout (5 min) | Mark as `production_timeout`, move to next post |

---

## 6. AI Models & Fallbacks

### Image Generation

| Provider | Model ID | When Used | Fallback |
|----------|----------|-----------|----------|
| **Gemini (primary)** | `gemini-3.1-flash-image-preview` (Nano Banana 2) | All 4 creative modes, ref image support | fal.ai MCP |
| **fal.ai (HTTP MCP)** | Flux 2, SDXL, etc. | When Gemini unavailable or user prefers | Replicate MCP |
| **Replicate (HTTP MCP)** | Various (user's choice) | Alternative provider | Placeholder |
| **Placeholder (Pillow)** | None (local rendering) | When ALL providers fail | Gray image with prompt text overlay |

The fallback chain is: Gemini -> fal.ai -> Replicate -> Placeholder. Each transition is automatic when the previous provider returns an error or is not configured.

### Image Editing

| Provider | Model ID | When Used |
|----------|----------|-----------|
| **Gemini** | `gemini-3.1-flash-image-preview` | ENHANCE_EXTEND mode edits, iterative refinement |

Image editing uses the same model as generation. The original image is sent as the first content part, edit instructions as text, and optional style references alongside.

### Vision Analysis (Asset Indexing)

| Provider | Model ID | When Used |
|----------|----------|-----------|
| **Gemini** | `gemini-3-flash` | Asset indexing (understanding what each photo contains) |

This is a different model from the image generator. Flash is used because vision analysis is a classification/description task, not a generation task.

### Video Generation

| Provider | Model ID | When Used | Duration |
|----------|----------|-----------|----------|
| **Veo 3.1 (fast)** | `veo-3.1-generate-preview` | Quick social clips | <=10 seconds |
| **Veo 3.1 (standard)** | `veo-3.1-generate-preview` | Reels, stories | 10-30 seconds |
| **Kling** | `kling-v2` | Longer form content | 30s-3min |
| **Manual** | None | Extended content | Script + storyboard only |

### When API Keys Are Checked

SocialForge checks for API keys at specific execution points, not at startup:

| Moment | Key Needed | What Happens If Missing |
|--------|-----------|------------------------|
| `/sf:index-assets` | `GEMINI_API_KEY` | Metadata-only index (dimensions, filename, folder). No AI analysis. Warning shown. |
| `/sf:generate-all` or `/sf:generate-post` | `GEMINI_API_KEY` or fal.ai/Replicate connected | Placeholder images generated. Warning: "Connect an image generation provider." |
| `/sf:generate-video --generate-video` | `GEMINI_API_KEY` (for Veo) | Script + storyboard only. No actual video clip. |
| Brand setup | None | No API needed for configuration |
| Calendar parsing | None | Claude reads the document directly |
| Asset matching | None | Uses existing index, pure math |
| Copy adaptation | None | Claude handles this directly |
| Carousel rendering | None (Playwright is local) | If Playwright missing: prompt to install |
| Compliance checking | None | Regex/string matching, no API |

---

## 7. Copy Adaptation Logic

**Script:** `adapt_copy.py` -- deterministic text transformation

### Per-Platform Rules

| Platform | Max Chars | Optimal Range | Fold Point | Hashtag Strategy | Link Strategy |
|----------|-----------|---------------|------------|-----------------|---------------|
| LinkedIn | 3,000 | 500-700 | 140 chars ("see more") | 3-5 at end of post | Direct URL in copy |
| Instagram | 2,200 | 500-1,000 | First line | 20-30 in FIRST COMMENT (not caption) | "Link in bio" |
| X/Twitter | 280 | 240 | -- (hard limit) | 1-2 inline | Direct URL (counts toward limit) |
| Facebook | 63,206 (optimal: 500) | 300-500 | 400 chars | 1-3 at end | Direct URL |
| YouTube | 5,000 | 200-500 | 200 | 3-5 in description | Direct URLs + timestamps |
| TikTok | 2,200 | 100-300 | -- | 3-5 trending + branded | "Link in bio" |
| Pinterest | 500 | 200-300 | -- | 5-10 SEO-focused | Direct URL |

### Smart Truncation

If copy exceeds the platform limit:
1. Find the last complete sentence that fits within the character limit.
2. If no sentence break falls within 50% of the limit, truncate at the limit boundary with "..."
3. For LinkedIn specifically: the full copy is preserved, but the first 140 characters must be the hook because that is the fold point (the "see more" boundary).

### Fold-Point Awareness

The adapt-copy skill does not just truncate. It restructures:

- **LinkedIn**: Front-loads the most compelling sentence into the first 140 characters. The hook must stand alone because most readers never tap "see more."
- **Instagram**: First line is the entire visible text before the fold. Must be self-contained and engaging.
- **X/Twitter**: No fold. Everything must fit in 280 characters including hashtags and links.

### Hashtag Processing

1. Load the brand's `always_include` hashtags from brand-config.json.
2. Add campaign-specific hashtags if an active campaign matches the post's campaign field.
3. Respect the per-platform hashtag limit (e.g., Instagram allows 30, LinkedIn best practice is 3-5).
4. For Instagram: hashtags go in the `first_comment` field, never in the main caption.
5. For LinkedIn: hashtags are appended at the end of the post body.
6. For X/Twitter: hashtags count toward the 280-character limit.

### Bilingual Posts

If the brand has `languages.bilingual_posts: true`:
1. Primary copy is generated in the primary language.
2. Secondary copy is structured for translation: `[TRANSLATE TO {lang}]: {primary_copy}`.
3. The `bilingual_format` field determines output structure:
   - `separate_posts` -- Two independent posts (one per language)
   - `bilingual_single_post` -- Both languages in one post (primary first, divider, secondary)
   - `language_per_platform` -- Different language per platform (e.g., English on LinkedIn, Hindi on Instagram)

### Cross-Posting Adaptation

When a post targets multiple platforms, `adapt_copy.py` generates separate copy files for each:
```
post-01-linkedin-copy.txt
post-01-instagram-copy.txt
post-01-instagram-first-comment.txt
post-01-facebook-copy.txt
```

Each file respects that platform's character limit, hashtag conventions, and link strategy. The core message is preserved; the structure and length vary.

---

## 8. Compliance Engine

**Script:** `compliance_check.py` -- deterministic rule matching

### What Gets Checked

| Check | How | Severity | Action |
|-------|-----|----------|--------|
| **Banned phrases (critical)** | Exact, contains, or regex match | Critical -> BLOCKS | Copy cannot proceed to approval |
| **Banned phrases (warning)** | Same matching | Warning -> FLAGS | Noted in status tracker, does not block |
| **Data claims** | Regex patterns: `\d+%`, `\$[\d,]+`, `\d+x` | Warning | "Source verification needed" |
| **Required disclaimers** | Trigger context in text -> check disclaimer present | Warning | "Add: {disclaimer_text}" |
| **Platform rules** | Max hashtags, forbidden content types | Critical/Warning | Blocks or flags |
| **Image compliance** | Rules from compliance-rules.json | Warning | "Manually verify before publishing" |

### How Matching Works

Each banned phrase entry in compliance-rules.json has a `match_type`:

- **`exact`**: The entire copy text must equal the phrase (rarely used).
- **`contains`**: The phrase appears anywhere in the copy as a substring. Case sensitivity controlled by `case_sensitive` field.
- **`regex`**: The phrase is treated as a regular expression pattern. Used for complex patterns like catching variations ("guarantee", "guaranteed", "guarantees").

### Processing Order

1. Load compliance-rules.json for the active brand.
2. For each copy text file in `production/week-{N}/{PostID}-.../copy/`:
   a. Run all banned phrase checks (critical first, then warnings).
   b. Scan for data claim patterns.
   c. Check if any trigger contexts require disclaimers and verify disclaimers are present.
   d. Check platform-specific rules (hashtag count, forbidden content types).
3. Generate a compliance report per post.
4. If any CRITICAL issue found: status set to BLOCKED, copy cannot proceed.
5. If only WARNING issues: status set to PENDING_REVIEW with warnings listed.

### Example: Pharma Brand Compliance

If compliance-rules.json contains:
```json
{
  "banned_phrases": [
    {"phrase": "cure", "match_type": "contains", "severity": "critical", "suggestion": "Use 'may help manage symptoms'"},
    {"phrase": "100% safe", "match_type": "exact", "severity": "critical"},
    {"phrase": "FDA approved", "match_type": "contains", "severity": "warning", "suggestion": "Specify which product and approval date"}
  ],
  "required_disclaimers": {
    "health_claims": {
      "disclaimer_text": "These statements have not been evaluated by the FDA.",
      "placement": "end_of_copy",
      "platforms": ["instagram", "facebook"]
    }
  }
}
```

Then a post saying "Our supplement can cure headaches" would be:
```
COMPLIANCE: BLOCKED
  Critical: "cure" found in copy (position: char 25)
  Suggestion: Use "may help manage symptoms"
```

The compliance engine is entirely deterministic. Same rules + same copy = same result every time.

---

## 9. Quality Evaluation System

**Agent:** quality-reviewer -- AI-driven scoring

### 5 Dimensions

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| Brand Consistency | 30% | Colors match brand-config, logo placed correctly, fonts correct, visual style aligned with style keywords and mood keywords |
| Visual Quality | 25% | Resolution adequate for platform, no AI artifacts, composition balanced, text readable at typical viewing size |
| Copy Quality | 20% | No spelling/grammar errors, tone matches brand voice, CTA clear and actionable, hashtags present where required |
| Platform Compliance | 15% | Correct dimensions for target platform, character limits respected, format appropriate (no video where static expected) |
| Compliance | 10% | No banned phrases, required disclaimers present, data claims flagged for sourcing |

### Scoring

- Each dimension is scored 1-10 by the quality-reviewer agent.
- Composite score = weighted average, rounded to 1 decimal place.
- **Pass threshold: 7.0 or above** (configurable per brand in brand-config.json).
- Below 7.0: the reviewer lists specific issues per dimension, suggests fixes, and holds the post from the approval queue.

### How Each Dimension Is Evaluated

**Brand Consistency (30%):**
The reviewer compares the generated image against concrete brand-config values. Are the primary/secondary brand colors present in the image? Is the logo in the correct position with correct opacity? Are brand fonts used in text overlays? Do the visual style keywords (e.g., "modern", "clean", "professional") describe this image? This dimension has the highest reliability because it checks against specific, defined values.

**Visual Quality (25%):**
The reviewer assesses overall image quality. Resolution must meet platform minimums (e.g., 1080x1350 for Instagram). No visible AI generation artifacts (distorted text, extra fingers, blurred edges). Composition follows basic principles (rule of thirds, visual hierarchy). Text overlays are readable against the background.

**Copy Quality (20%):**
Grammar and spelling are objective checks (high reliability). Tone matching is more subjective but is guided by brand voice descriptors from brand-config.json. CTA presence is binary. Hashtag correctness is verifiable against the brand's hashtag configuration.

**Platform Compliance (15%):**
Dimensions are verified against platform-specs.md (deterministic check). Character counts are deterministic. Format type is deterministic. This dimension is highly reliable.

**Compliance (10%):**
Cross-references the compliance_check.py output. If the compliance engine already flagged issues, this dimension scores low. If no compliance issues exist, it scores high.

### Scoring Is Non-Deterministic

The quality reviewer is an AI agent, not a script. Implications:
- Scores can vary by 0.5-1.0 points between runs for the same content.
- Brand Consistency and Platform Compliance are the most reliable dimensions (they check against concrete values).
- Visual Quality is the most subjective dimension.
- The numeric threshold (7.0) provides a consistent gate despite score variance.

---

## 10. Carousel Rendering Pipeline

**Script:** `render_carousel.py` -- fully deterministic (Playwright screenshot)

### How It Works

1. Select the HTML template based on `carousel_type` from calendar-data.json (8 templates available).
2. Inject brand CSS variables: `--brand-primary`, `--brand-secondary`, `--brand-accent`, `--brand-bg`, `--brand-text`, `--brand-font-heading`, `--brand-font-body` from brand-config.json.
3. For each slide: replace template placeholders (`{{slide_title}}`, `{{slide_body}}`, `{{data_point}}`) with content from the carousel slide briefs.
4. Render each slide at 1080x1080px (or custom dimensions) via Playwright headless Chromium -> PNG screenshot.
5. Assemble all PNGs into a single PDF using Pillow multi-page save.
6. Output: slide-01.png through slide-NN.png + carousel.pdf in production/carousels/post-{id}/.

### Template Types

| Template | Slides | Design | Use Case |
|----------|--------|--------|----------|
| generic-8slide | 8 | Gradient bg, centered title | General purpose, default choice |
| comparison-10slide | 10 | Two-column VS layout | Feature comparisons, A vs B |
| case-study-10slide | 10 | Hero metric + narrative | Client success stories |
| tips-5slide | 5 | Large number + tip text | Quick tips, listicles |
| playbook-8slide | 8 | Step badge circle | How-to guides, process walkthroughs |
| recap-6slide | 6 | Date bar + highlight | Event recaps, weekly summaries |
| data-infographic-6slide | 6 | Large stat on gradient | Data stories, research findings |
| quote-card-single | 1 | Quote mark + attribution | Quote posts, testimonials |

### Brand-Specific Template Overrides

If a brand has custom carousel templates in `brands/{slug}/carousel-templates/`, those take priority over the plugin's default templates. This allows agencies to use client-specific designs.

### Fully Deterministic

Same brand config + same slide content = same output every time. No AI involved. The rendering uses Playwright's headless Chromium which produces pixel-identical screenshots for identical HTML/CSS input.

### Dependencies

Requires `playwright` Python package and Chromium browser binary:
```
pip install playwright
playwright install chromium
```

If Playwright is not installed, the skill prompts the user to install it. There is no AI fallback for carousel rendering -- it is local-only.

---

## 11. Video Production Logic

**Script:** `generate_video.py` -- deterministic scripts + optional AI video

### Always Generated (Deterministic)

Every video post, regardless of whether AI video generation is available, produces:

1. **Script** -- Timestamped scene-by-scene narration/dialogue. Stored as `post-{id}-script.md` in the post's `keyframes/` directory (`production/week-{N}/{PostID}-.../keyframes/`).
2. **Storyboard** -- Shot-by-shot visual descriptions with camera directions (angle, movement, framing). Stored as `post-{id}-storyboard.md`.
3. **Thumbnail** -- A static image generated via the standard image production pipeline (ANCHOR_COMPOSE or STYLE_REFERENCED). Stored as `post-{id}-thumbnail.png`.

These three outputs are always delivered, even when no API key is configured.

### Optionally Generated (Non-Deterministic, --generate-video flag)

4. **AI video clip** -- Generated via Gemini Veo 3.1 or Kling API depending on duration.
5. **SRT subtitles** -- Derived from script timestamps, synced to the video duration.

### Post-Processing (via video_postprocess.py)

After AI video generation, clips are post-processed using ffmpeg via `imageio-ffmpeg`:

- **Logo watermark overlay** -- Brand logo composited at a configurable position and opacity
- **Platform resize** -- Output resized to 9 platform dimensions (Instagram Reel 1080x1920, TikTok 1080x1920, YouTube Shorts 1080x1920, LinkedIn 1920x1080, Facebook 1080x1080, X/Twitter 1920x1080, Pinterest 1000x1500, Story 1080x1920, Landscape 1920x1080) with no stretching (pad/crop)
- **SRT subtitle burning** -- Optional (user approves). Burns SRT file into the video using brand fonts and colors
- **Background music mixing** -- Optional (user approves). Mixes background audio track at reduced volume under the original video audio

### Duration-Based Routing

| Duration | Provider | Mode | Notes |
|----------|----------|------|-------|
| <=10s | Veo 3.1 | Fast preview | Quick social clips, animated product shots |
| 10-30s | Veo 3.1 | Standard | Reels, stories, short brand videos |
| 30s-3min | Kling (if configured) | Long form | Mini case studies, event recaps |
| >3min | Manual | -- | Script + storyboard only, too long for current AI video |

### Video Type Classification

The calendar's `video_details.video_type` field determines production approach:

- **hero_video**: Full production treatment. Multiple scenes, music considerations, high polish.
- **mini_case_study**: Interview/narrative structure. May require real footage.
- **short_reel**: 15-30 second vertical clip. Fast cuts, trending format.
- **story**: Ephemeral, 15 seconds max. Can be animated from a static image.
- **talking_head**: Requires real footage of a person. Script + teleprompter text only.

---

## 12. Approval State Machine

**Script:** `status_manager.py` -- deterministic state transitions

### 14 States

```
QUEUED -> ASSET_MATCHING -> GENERATING -> PENDING_REVIEW
                                            |
                          +-----------------+------------------+
                          v                 v                  v
                   APPROVED_INTERNAL  REVISION_REQUESTED  REJECTED
                          |                 |                  |
                          |                 +-> GENERATING     +-> QUEUED
                          v
                   PENDING_CLIENT (if required by tier)
                          |
              +-----------+-----------+
              v           v           v
       APPROVED_CLIENT  REV_REQ_CLI  REJECTED_CLI
              |           |                |
              |           +-> GENERATING   +-> QUEUED
              v
       PENDING_CEO (if required by tier)
              |
              v
       APPROVED_CEO -> FINAL
```

### Transition Rules

- **FINAL is write-protected** -- no transitions out of FINAL. Enforced by the status_manager.py VALID_TRANSITIONS dictionary. Any attempt to transition out of FINAL is rejected with an error.
- **Invalid transitions are blocked** -- status_manager.py maintains an explicit dictionary of which states can transition to which. Attempting QUEUED -> APPROVED_INTERNAL (skipping production) throws a validation error.
- **--force flag** -- Overrides validation for emergencies. Logs `force_finalized: true` in the status tracker. Intended for situations where a post must ship despite incomplete approvals.
- **Every transition is logged** -- actor (who triggered it), timestamp, notes, and the previous state are stored in `revision_history`.

### Per-Tier Approval Paths

| Tier | Required Path | Typical Posts |
|------|---------------|---------------|
| HERO | Internal -> Client -> CEO | Flagship campaigns, product launches, major announcements |
| HUB | Internal -> Client (optional) | Regular series content, thought leadership, curated posts |
| HYGIENE | Internal only (auto-approvable) | Routine posts, holiday greetings, industry news shares |

The approval-chain.json determines which tiers require client and CEO review. HYGIENE posts with `auto_flag_for_client: false` can potentially go straight from APPROVED_INTERNAL to FINAL if the approval chain allows it.

### Escalation Rules

If a post sits in PENDING_CLIENT for too long:
1. After `reminder_after_days` (e.g., 3 days): send reminder via Slack/email.
2. After `escalate_after_days` (e.g., 7 days): escalate to the role specified in `escalate_to`.
3. If `auto_publish_without_client: true` and the escalation period expires: the post can be finalized without client sign-off, with an audit note appended.

### Revision Handling

When a reviewer requests revision:
1. The post transitions to REVISION_REQUESTED (or REV_REQ_CLI for client revisions).
2. Feedback text is stored in `revision_history`.
3. The post transitions back to GENERATING for the specific elements that need changes.
4. A `max_revisions` limit (default 3) is enforced per tier. After max revisions, the post escalates.

---

## 13. Batch vs Individual Processing

### Batch: `/sf:generate-all`

Processes ALL posts in the calendar sequentially:

```
For each post (ordered by date):
  1. Load matched asset + creative mode from asset-matches.json
  2. Route to the appropriate production pipeline (ANCHOR/ENHANCE/STYLE/PURE)
  3. Generate image(s) -- 2-3 variants
  4. Show variants to user for selection/approval
  5. Adapt copy for each platform
  6. Run compliance check on all copy
  7. Generate platform preview mockups
  8. Update status-tracker.json -> PENDING_REVIEW
  9. Log cost to cost-log.json
  10. Show progress [N/total]
```

**Filters available:**
- `--week 2` -- Only posts in week 2
- `--tier HERO` -- Only HERO tier posts
- `--platform instagram` -- Only Instagram posts
- Filters can be combined: `--week 1 --tier HERO` processes only HERO posts in week 1

### Individual: `/sf:generate-post P03`

Same pipeline, single post. Used for:
- Regenerating after revision feedback
- Creating an A/B variant (`--variant b`)
- Testing creative direction before running the full batch
- Quick turnaround on a single urgent post

### Processing Order Within Batches

Posts are processed one at a time, not in parallel. The reason: each post requires user approval of the generated image before proceeding. The user sees each post's variants, selects or requests regeneration, and the pipeline moves to the next post.

For HYGIENE-tier posts with auto-approve configured in approval-chain.json, the pipeline can process without pausing for user approval at each post. The quality gate (score >= 7.0) still applies -- posts below threshold are flagged for later review.

### Full Pipeline: `/sf:full-pipeline`

Runs all 8 phases in sequence. Phases execute sequentially (Phase 0 -> 1 -> 2 -> ...). There is no parallel phase execution because each phase depends on the previous phase's output.

---

## 14. Folder Structure & File Organization

### Persistent Brand Data

```
${CLAUDE_PLUGIN_DATA}/socialforge/
+-- brands/
|   +-- greenleaf-organics/
|   |   +-- brand-config.json           <- Identity, colors, fonts, visual style, hashtags
|   |   +-- platform-config.json        <- Active platforms, posting times, content mix
|   |   +-- approval-chain.json         <- HERO/HUB/HYGIENE review rules + escalation
|   |   +-- compliance-rules.json       <- Banned phrases, disclaimers, platform rules
|   |   +-- asset-source.json           <- Where photos live (Drive URL, local path, Cloudinary)
|   |   +-- asset-index.json            <- AI analysis of every photo (tags, colors, mood)
|   |   +-- content-buckets.json        <- Content categories active for this brand
|   |   +-- style-references/           <- 2-8 brand DNA photos
|   |   +-- carousel-templates/         <- Brand-specific template overrides (optional)
|   |   +-- brand-assets/               <- Local copy of logos, avatars, fonts
|   |       +-- logo-primary.png
|   |       +-- logo-white.png
|   |       +-- logo-icon.png
|   |       +-- avatars/
+-- output/
|   +-- greenleaf-organics/
|   |   +-- 2026-04/                    <- April production
|   |   |   +-- calendar-data.json      <- Parsed calendar
|   |   |   +-- asset-matches.json      <- Asset-to-post matching results
|   |   |   +-- status-tracker.json     <- Per-post state machine
|   |   |   +-- cost-log.json           <- API cost tracking
|   |   |   +-- production/
|   |   |   |   +-- week-{N}/                              <- Week grouping
|   |   |   |   |   +-- {PostID}-{date}-{platforms}-{tier}-{type}/
|   |   |   |   |       +-- versions/                      <- Generated options
|   |   |   |   |       +-- final/                         <- Approved output
|   |   |   |   |       +-- copy/                          <- Platform copy
|   |   |   |   |       +-- keyframes/                     <- Video keyframes
|   |   |   |   +-- carousels/                             <- Rendered carousel slides + PDFs
|   |   |   +-- review/
|   |   |   |   +-- gallery.html        <- Interactive review gallery
|   |   |   +-- FINAL/                  <- Delivery package (after finalization)
|   |   |       +-- 00-Calendar-Document/
|   |   |       +-- 01-Ready-to-Publish/
|   |   |       |   +-- Week-{N}/
|   |   |       |       +-- {date}-Post{id}-{title}/
|   |   |       |           +-- {platform}/
|   |   |       |               +-- image-{WxH}.png
|   |   |       |               +-- copy.txt
|   |   |       |               +-- preview.png
|   |   |       +-- 02-Carousels/
|   |   |       +-- 03-Video-Production-Kit/
|   |   |       +-- 04-Stories-Shorts/
|   |   |       +-- 05-Review-Gallery/
|   |   |       +-- 06-Publishing-Schedule/
|   |   |       +-- 07-Production-Checklist/
+-- shared/
    +-- prompt-logs/                    <- Every AI prompt logged for debugging
```

### Month-over-Month

Each month gets its own directory under `output/{brand}/`:
```
output/greenleaf-organics/
+-- 2026-03/    <- March (archived)
+-- 2026-04/    <- April (current production)
+-- 2026-05/    <- May (can be set up in advance)
```

Previous months are preserved as archives. `/sf:new-month` creates a fresh directory structure -- it never overwrites or deletes old months.

### Per-Platform Organization (in FINAL/)

```
01-Ready-to-Publish/
+-- Week-1/
|   +-- 2026-04-01-P01-Avocado-Oil-Launch/
|   |   +-- linkedin/
|   |   |   +-- image-1200x627.png      <- Correct dimensions for LinkedIn
|   |   |   +-- copy.txt                 <- LinkedIn-adapted copy (3000 char, 5 hashtags)
|   |   |   +-- preview.png              <- How it looks in the LinkedIn feed
|   |   +-- instagram/
|   |   |   +-- image-1080x1350.png     <- 4:5 portrait for Instagram feed
|   |   |   +-- copy.txt                 <- Instagram copy (2200 char)
|   |   |   +-- first-comment.txt        <- Hashtags for first comment (not in caption)
|   |   |   +-- preview.png
|   |   +-- facebook/
|   |       +-- image-1200x630.png
|   |       +-- copy.txt
|   |       +-- preview.png
```

The FINAL/ folder is the delivery package. A social media manager can open Week-1/2026-04-01-P01-Avocado-Oil-Launch/linkedin/ and find everything needed to publish that specific post on that specific platform: the correctly-sized image, the platform-adapted copy, and a preview showing how it will look.

### Where Images Live vs Where Metadata Lives

Asset images (the brand's photography) stay in their original location -- Google Drive, Cloudinary, or a local folder. SocialForge stores only the AI-analyzed metadata index (`asset-index.json`), not copies of the images themselves. The `asset-source.json` file records where to find the originals.

Generated images (production output) are stored locally in the output directory under each post's directory: `production/week-{N}/{PostID}-{date}-{platforms}-{tier}-{type}/versions/` for generated options and `.../final/` for approved output. These are new files created by SocialForge.

---

## 15. Deterministic vs Non-Deterministic Steps

### Deterministic (Same Input = Same Output)

| Step | Script | Why Deterministic |
|------|--------|-------------------|
| Asset matching scoring | match_assets.py | Mathematical formula with fixed weights |
| Background removal | compose_image.py (rembg) | ML model but consistent for same image input |
| Compositing (layering) | compose_image.py | Pillow pixel operations |
| Shadow generation | compose_image.py | Calculated from alpha channel geometry |
| Edge feathering | compose_image.py | Gaussian blur filter, fixed parameters |
| Color temp matching | compose_image.py | RGB analysis + fixed 3% max shift |
| Text overlay | compose_text_overlay.py | Font rendering with brand config values |
| Logo watermark | compose_image.py | Alpha-blended paste at fixed position/opacity |
| Image resizing | resize_image.py | Lanczos resampling, deterministic algorithm |
| Carousel rendering | render_carousel.py | HTML -> Playwright screenshot, pixel-identical |
| PDF assembly | render_carousel.py | Pillow multi-page save |
| Copy truncation | adapt_copy.py | Character counting + sentence boundary detection |
| Hashtag processing | adapt_copy.py | List operations against brand config |
| Compliance checking | compliance_check.py | Regex/string matching against rules |
| Status transitions | status_manager.py | Validated state machine with explicit transition table |
| Cost tracking | cost_tracker.py | JSON append with timestamp |
| Preview rendering | render_preview.py | HTML template + Playwright screenshot |
| Gallery building | build_gallery.py | HTML template population |
| Brand color verification | verify_brand_colors.py | Hex code comparison |

### Non-Deterministic (AI-Dependent)

| Step | Provider | Why Non-Deterministic | Mitigation |
|------|----------|----------------------|-----------|
| AI image generation | Gemini/fal.ai/Replicate | Different output each call, even with identical prompt | Generate 2-3 variants, user selects. Quality scoring provides objective gate. |
| AI image editing | Gemini | Enhancement varies per call | SSIM check against original. Core preservation verified. User approval required. |
| Vision analysis (indexing) | Gemini | Descriptions and tags vary slightly between runs | Tags are consistent enough for matching (core subjects are always identified). |
| Quality scoring | Claude agent | Subjective judgment across 5 dimensions | 5-dimension framework with numeric weights. Threshold provides binary pass/fail. |
| Copy generation | Claude | Language varies between sessions | Compliance check enforces hard rules. Character limits enforce structure. |
| Calendar parsing | Claude | Interpretation of ambiguous calendar entries | User confirmation step before proceeding. |
| Video generation | Veo/Kling | Video output varies per call | Script provides deterministic structure. User approves or rejects result. |

### The Reliability Principle

SocialForge is designed so that non-deterministic steps are always sandwiched between deterministic gates. AI generates an image (non-deterministic), but the quality score threshold (deterministic gate) decides if it passes. AI writes copy (non-deterministic), but the compliance engine (deterministic) catches banned phrases. This means the system's reliability comes from its gates, not from the AI steps themselves.

---

## 16. API Keys & When They're Needed

### Setup Phase (No API Keys Needed)

| Step | API Key | Notes |
|------|---------|-------|
| Install plugin | None | Plugin files are static |
| Brand setup (`/sf:brand-setup`) | None | Configuration only, user provides values |
| Calendar parsing (`/sf:new-month`) | None | Claude reads the document directly |
| Asset matching (`/sf:generate-all` phase 1) | None | Uses existing index, pure math scoring |
| Copy adaptation | None | Claude handles text transformation |
| Compliance checking | None | Regex/string matching against local rules |
| Carousel rendering | None | Playwright is local (requires pip install) |
| Preview rendering | None | Playwright is local |
| Gallery building | None | Local HTML generation |
| Finalization | None | File organization only |

### Production Phase (API Keys Needed)

| Step | Key Required | How To Get | Estimated Cost |
|------|-------------|-----------|----------------|
| Asset indexing (AI analysis) | `GEMINI_API_KEY` | https://aistudio.google.com/apikey | ~$0.003/image |
| Image generation (Gemini) | `GEMINI_API_KEY` | Same | ~$0.02/image |
| Image generation (fal.ai) | fal.ai MCP connected | Connectors panel in Claude | ~$0.03/image |
| Image generation (Replicate) | Replicate MCP connected | Connectors panel | ~$0.025/image |
| Image editing | `GEMINI_API_KEY` | Same | ~$0.015/edit |
| Video generation (Veo) | `GEMINI_API_KEY` | Same | ~$0.10/clip |
| Video generation (Kling) | `KLING_API_KEY` | Kling API dashboard | Varies |

### No-API Fallback Behavior

If no API key is configured:

- **Asset indexing**: Creates a metadata-only index containing dimensions, filename, folder path, and file size. No AI analysis (no tags, descriptions, mood, or suitability data). Asset matching will fall back to filename/folder-based heuristics, which are significantly less accurate.
- **Image generation**: Placeholder images are generated locally using Pillow -- a gray rectangle with the generation prompt text overlaid. Posts are flagged for manual image creation.
- **Image editing**: Not available. Posts requiring ENHANCE_EXTEND mode are flagged for manual editing.
- **Video**: Script + storyboard are always generated (Claude writes these). No AI video clips without an API key.
- **Everything else works**: Copy adaptation, compliance checking, carousel rendering, platform previews, review gallery, approval management, and finalization all function without any API keys.

---

## 17. Cost Tracking

**Script:** `cost_tracker.py` -- logs every API call with estimated cost

### Per-Operation Costs

| Operation | Estimated Cost | Provider | Local? |
|-----------|---------------|----------|--------|
| Vision analysis (per image) | $0.003 | Gemini | No |
| Image generation | $0.020 | Gemini | No |
| Image editing | $0.015 | Gemini | No |
| fal.ai generation | $0.030 | fal.ai | No |
| Replicate generation | $0.025 | Replicate | No |
| Video generation (Veo) | $0.100 | Gemini | No |
| Background removal (rembg) | $0.000 | Local | Yes |
| Compositing (Pillow) | $0.000 | Local | Yes |
| Text overlay | $0.000 | Local | Yes |
| Carousel rendering (Playwright) | $0.000 | Local | Yes |
| Preview rendering (Playwright) | $0.000 | Local | Yes |
| Copy adaptation | $0.000 | Claude (subscription) | N/A |
| Compliance checking | $0.000 | Local | Yes |

### How Costs Are Logged

Every API call made by any script writes an entry to `cost-log.json`:

```json
{
  "timestamp": "2026-04-01T10:30:15Z",
  "operation": "image_generation",
  "model": "gemini-3.1-flash-image-preview",
  "post_id": 1,
  "reference_count": 5,
  "resolution": "1024",
  "estimated_cost_usd": 0.020,
  "success": true
}
```

Failed API calls are also logged (with `"success": false`) but are not counted toward cost totals because the provider typically does not charge for failed requests.

### Monthly Cost Report

The `/sf:cost-report` command reads cost-log.json and produces:

```
Total: $2.87 (28 posts)
  Image generation: $1.60 (80 generations x $0.02)
  Vision analysis: $0.14 (45 images x $0.003)
  Image editing: $0.45 (30 edits x $0.015)
  Video generation: $0.40 (4 clips x $0.10)
  Local operations: $0.00

Average per post: $0.10
Most expensive: P01 (HERO, 3 variants + 2 regenerations) -- $0.18
Least expensive: P22 (HYGIENE, text_only) -- $0.00
```

### Cost Drivers

The primary cost driver is the number of image generations. Each post typically requires:
- 2-3 variant generations ($0.04-0.06)
- 0-1 regenerations after quality review ($0.00-0.02)
- 0-1 edits for refinement ($0.00-0.015)

A 28-post month with mixed content types typically costs $2-5 in API charges. HERO posts cost more (more variants, more iterations). HYGIENE text-only posts cost nothing.

---

## 18. Cross-Platform Compatibility

### What Works Where

| Capability | Cowork | Claude Code |
|------------|--------|-------------|
| Brand setup | Yes | Yes |
| Calendar parsing | Yes | Yes |
| Asset indexing (Gemini Vision) | Yes (API call) | Yes (API call) |
| Asset source: Google Drive | Yes (platform integration) | Partial (download first) |
| Asset source: Local folder | Partial (session-only unless via plugin data) | Yes (persistent) |
| Asset source: Cloudinary | Yes (HTTP MCP) | Yes (HTTP MCP) |
| Image generation (Gemini) | Yes (API call) | Yes (API call) |
| Image generation (fal.ai/Replicate) | Yes (HTTP MCP) | Yes (HTTP MCP) |
| Background removal (rembg) | Partial (may fail on C-extension deps) | Yes (pip install rembg) |
| Carousel rendering (Playwright) | Partial (requires chromium install in VM) | Yes (pip install playwright) |
| Copy adaptation | Yes | Yes |
| Compliance checking | Yes | Yes |
| Preview rendering (Playwright) | Partial (same as carousel) | Yes |
| Brand configs persist | Yes (${CLAUDE_PLUGIN_DATA}) | Yes (${CLAUDE_PLUGIN_DATA}) |
| All 10 HTTP connectors | Yes | Yes |
| Document assembly (docx-js) | Yes (Node.js available in Cowork VM) | Yes |
| Scheduled production | Yes (Cowork scheduled tasks) | Yes (/schedule, /loop) |

### Cowork-Specific Notes

Cowork runs in a sandboxed VM with Python 3.10.12 and Node.js 22.22. Key considerations:

- **pip works** and pypi.org is allowlisted. Most pure-Python packages install fine.
- **C-extension packages** (like rembg, which depends on onnxruntime) may fail to build. The fallback for background removal is a simpler threshold-based approach (works for white/solid backgrounds, not for complex scenes).
- **Playwright chromium** requires a separate binary install step. If not available, carousel and preview rendering are skipped and posts are shown with raw images + copy in the conversation.
- **Filesystem is session-scoped** except for `${CLAUDE_PLUGIN_DATA}`, which persists. All brand configs and indexes use plugin data. Production outputs may need to be exported (to Drive, Cloudinary, or downloaded) before session ends.
- **Google Drive** is available as a platform-level integration (Settings -> Integrations). Assets stored in Drive can be accessed directly.

### Claude Code-Specific Notes

Claude Code runs on the user's local machine with full filesystem access:

- **All pip packages work** including C-extension dependencies.
- **Full persistent filesystem** -- production outputs are always available across sessions.
- **SSH and git work** -- can push/pull from repositories.
- **Google Drive** requires downloading assets to a local folder first (no platform-level Drive integration in Claude Code).
- **More flexible but less sandboxed** -- the user is responsible for environment management.

### HTTP MCP Connectors (Both Platforms)

All 10 HTTP connectors work identically on both platforms:

| Connector | URL | What It Enables |
|-----------|-----|-----------------|
| Notion | `https://mcp.notion.com/mcp` | Calendar database sync, brand guidelines storage |
| Canva | `https://mcp.canva.com/mcp` | Brand templates, design assets |
| Figma | `https://mcp.figma.com/mcp` | Design system access, brand assets |
| Slack | `https://mcp.slack.com/mcp` | Approval notifications, review requests |
| Gmail | `https://gmail.mcp.claude.com/mcp` | Delivery emails, approval reminders |
| Google Calendar | `https://gcal.mcp.claude.com/mcp` | Posting schedule sync |
| fal.ai | `https://mcp.fal.ai/mcp` | Alternative image generation (Flux 2, SDXL) |
| Replicate | `https://mcp.replicate.com/sse` | Alternative image generation |
| Asana | `https://mcp.asana.com/sse` | Post status tracking, publishing schedule |
| Cloudinary | `https://asset-management.mcp.cloudinary.com/mcp` | Professional DAM, CDN delivery, transformations |

All connectors are optional. The plugin works without any of them. `.mcp.json` contains only HTTP URLs (no credentials) and is safe to commit to version control.

### Asset Storage Strategy

| Storage Backend | Best For | How It Works |
|-----------------|----------|-------------|
| Google Drive | Agencies (natural client folder structure) | Connect at platform level (Cowork) or download locally (Claude Code). Index with `/sf:index-assets`. |
| Cloudinary | Professional DAM needs (tagging, CDN, transformations) | Connect via HTTP MCP. Index directly from Cloudinary URLs. |
| Local folder | Solo users, local workflows | Point `/sf:index-assets` at a local directory. Persistent in Claude Code, session-only in Cowork. |

The recommended agency setup:
```
Google Drive (asset images) -> /sf:index-assets (AI analysis) -> asset-index.json (persistent)
                                                                       |
Cloudinary (optional DAM) ---------------------------------> CDN delivery + transformations
```

---

## Hooks

SocialForge uses 4 hooks to enforce quality and brand consistency at the platform level:

### SessionStart
Runs `status_manager.py --action session-init` to restore session state, then displays the quick-start banner with available commands.

### PreToolUse (Write|Edit)
Fires before any file write or edit. If the content being written is social media copy or an image prompt, it checks:
1. No banned phrases from compliance-rules.json.
2. No fabricated statistics or unsourced claims.
3. Platform character limits respected.
4. Brand hashtags included where required.

### SubagentStart
Fires when any subagent is spawned. Loads the active brand-config.json and enforces:
1. Brand colors, fonts, and visual style must be respected.
2. Brand assets are sacred -- AI generates around them, never replaces them.
3. All generated images must be shown to user for approval.
4. The 4 creative modes must be followed.
5. Compliance rules must be respected.

### Stop
Fires when a task completes. Verifies:
1. All generated images were approved by the user.
2. Copy respects platform character limits.
3. Brand compliance was checked.
4. Logo overlay was applied where required.
5. Correct image dimensions for target platforms.

If any check fails, the hook lists the issues and asks how to proceed instead of silently completing.

---

## Prompt Logging

Every AI prompt sent to any provider is logged to `shared/prompt-logs/` with the filename format `{YYYY-MM-DD}-{brand}-{post-id}.json`. Each log entry contains:

- The full prompt text (all 5 layers for STYLE_REFERENCED, full instruction for edits)
- Reference image paths (not the images themselves, just paths)
- Model ID used
- Response metadata (success/failure, generation time, cost)
- Quality score (if evaluated)

This serves two purposes:
1. **Debugging** -- When an image does not match expectations, the prompt log reveals exactly what was requested.
2. **Learning** -- Over time, patterns emerge in which prompt structures produce better results. The prompt logs are the training data for improving prompt templates.

---

*SocialForge Technical Operations Reference -- v1.3*
