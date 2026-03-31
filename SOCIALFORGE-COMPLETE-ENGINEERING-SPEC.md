# SOCIALFORGE — COMPLETE ENGINEERING SPECIFICATION

## Plugin for Claude Code / Cowork / Antigravity
## Social Media Calendar Automation with Asset-First Compositing

**Spec Version:** 1.0.0
**Target Runtime:** Claude Code (Antigravity), Claude Cowork, Claude Code Terminal
**Author:** Neel (Indranil Banerjee)
**Date:** March 2026

---

# TABLE OF CONTENTS

```
PART 1:  VISION & ARCHITECTURE OVERVIEW
PART 2:  PLUGIN MANIFEST & DIRECTORY STRUCTURE
PART 3:  DATA SCHEMAS (ALL JSON SCHEMAS)
PART 4:  CORE CONCEPT — ASSET-FIRST COMPOSITING
PART 5:  SKILL SPECIFICATIONS (ALL 14 SKILLS)
PART 6:  COMMAND SPECIFICATIONS (ALL 18 COMMANDS)
PART 7:  AGENT SPECIFICATIONS (ALL 5 AGENTS)
PART 8:  HOOKS CONFIGURATION (COMPLETE hooks.json)
PART 9:  MCP CONNECTORS (.mcp.json)
PART 10: SETTINGS (settings.json)
PART 11: SCRIPT LOGIC (ALL 17 SCRIPTS)
PART 12: REFERENCE DOCUMENTS
PART 13: TEMPLATE SPECIFICATIONS
PART 14: PIPELINE ORCHESTRATION (DETERMINISTIC WORKFLOWS)
PART 15: NON-DETERMINISTIC SCENARIOS & EDGE CASES
PART 16: PLATFORM SPECIFICATIONS (COMPLETE REFERENCE)
PART 17: API INTEGRATION DETAILS
PART 18: CROSS-PLATFORM DEPLOYMENT
PART 19: IMPLEMENTATION ORDER & DEPENDENCY GRAPH
```

---

# PART 1: VISION & ARCHITECTURE OVERVIEW

## 1.1 What SocialForge Does

SocialForge takes a monthly social media content calendar (DOCX, XLSX, Notion database, or structured text) and produces ready-to-publish creative assets for multiple brands across multiple platforms. It operates at agency scale — multiple brands, multiple clients, multiple social media managers using it simultaneously.

## 1.2 The Fundamental Principle

**Brand assets are sacred. AI is the creative layer around them.**

A product photo, a lab image, a platform screenshot, a founder portrait, an office interior — these are the brand's real visual identity. AI never replaces them. AI generates backgrounds, mood, context, atmosphere around them. The brand asset stays pixel-faithful in the final composition.

When no brand asset applies (abstract concepts, generic wishes, trend visuals), AI generates from scratch using the brand's style reference photography as visual DNA guides.

## 1.3 The Four Creative Modes

Every post is assigned one of four modes. The mode determines how brand assets and AI generation interact.

**MODE 1: ANCHOR_COMPOSE**
The brand asset is the untouchable center of the composition. AI generates everything around it.
- Input: Core brand asset (product photo, headshot, screenshot) + creative brief
- Process: Background removal/masking of asset → AI generates surrounding scene → composite asset onto scene → add text/logo overlay → resize per platform
- Output: Final composed image with real asset at center, AI-generated context around it
- Example: Razor product photo on AI-generated marble bathroom counter with morning light
- Example: Dashboard screenshot composited into AI-generated modern desk workspace
- Example: Founder portrait with AI-generated professional conference stage background

**MODE 2: ENHANCE_EXTEND**
The brand asset is the foundation. AI modifies the periphery — extends background, adjusts lighting, adds atmospheric effects. Core subject stays recognizable and faithful.
- Input: Complete brand photograph + edit instructions
- Process: Feed real image to Gemini edit API → AI extends/enhances while preserving core → add overlay → resize
- Output: Enhanced version of the real photo
- Example: Office photo with AI-extended ceiling and dramatic overhead lighting added
- Example: Team group photo with background extended and subtle branded gradient added
- Example: Product shot with AI-generated lifestyle scene fading outward from product edges

**MODE 3: STYLE_REFERENCED**
No specific brand asset is composited. The brand's curated style reference photos guide the AI's visual generation. The output is entirely AI-generated but matches the brand's visual DNA.
- Input: Text prompt + 2-8 brand style reference images + brand config
- Process: Feed style references to Nano Banana 2 as reference images → AI generates new image absorbing the visual DNA → quality review → overlay → resize
- Output: AI-generated image that looks like it belongs in the brand's photo library
- Example: Abstract tech visualization matching the brand's navy/warm palette and clean composition style
- Example: Conceptual "three worlds" illustration for a positioning campaign — no real photo could capture this
- Example: Motivational background for a quote card — no specific brand photo needed but should feel on-brand

**MODE 4: PURE_CREATIVE**
Full AI generation with only text prompt and brand color/mood config. No reference images fed. Weakest visual consistency but appropriate for generic content.
- Input: Text prompt + brand-config.json colors/mood/style
- Process: Text-only generation → quality review → overlay → resize
- Output: AI-generated image guided only by text and brand config
- Example: Festival greeting (Diwali, Christmas, Eid) — generic festive visual with brand colors
- Example: Industry news reaction — abstract representation of a trending topic
- Example: Seasonal content — monsoon, summer, new year — where brand identity isn't the focus

## 1.4 The Pipeline Flow (High-Level)

```
CALENDAR INPUT → PARSE → ASSET MATCH → CREATIVE PRODUCTION → COPY ADAPT → PREVIEWS → REVIEW GALLERY → APPROVAL → FINALIZE
```

Each phase has defined inputs, outputs, gates (human approval points), and hooks (deterministic enforcement).

## 1.5 Multi-Brand, Multi-User, Agency-Scale

- Multiple brands with isolated configs, assets, approval chains, compliance rules
- Multiple social media managers can work on different brands simultaneously
- Parallel processing across brands using sub-agents
- All brand state (assets, status, output) strictly isolated — enforced by hooks
- Switching brands is instant context reload

## 1.6 Technology Stack

| Component | Technology | Role |
|---|---|---|
| Orchestration | Claude Code / Cowork sub-agents | Pipeline management, creative reasoning |
| Image Generation | Gemini API (Nano Banana 2: gemini-3.1-flash-image-preview) | AI image generation with reference image support (up to 14 refs) |
| Image Editing | Gemini API (same model) | Iterative image editing, enhancement, extension |
| Asset Indexing | Gemini API (gemini-3-flash for vision) | Understanding what's in each brand photo |
| Video Generation | Gemini API (Veo 3.1: veo-3.1-generate-preview) | Short-form video clips, image-to-video animation |
| Video (longer) | Kling API (optional, separate key) | Character-consistent longer videos (30s-3min) |
| Compositing | Python Pillow + rembg | Background removal, layering, text overlay, resize |
| Carousel Rendering | Playwright (headless Chromium) | HTML/CSS templates → PNG screenshots |
| Document Assembly | Node.js docx-js | Word document creation |
| Connectors | MCP protocol | Google Drive, Slack, Notion, Canva, Gmail |
| Storage | Local filesystem (+ cloud sync via Drive) | All assets and outputs |

## 1.7 Key Capability: Nano Banana 2 Reference Images

Nano Banana 2 (gemini-3.1-flash-image-preview) accepts up to 14 reference images per request. This is the technical foundation for style-referenced generation. When generating a new image, feeding the brand's real photography as references causes the AI to absorb the visual DNA — lighting style, color temperature, composition patterns, mood. The output is a new image that looks like it belongs in the same photo library.

This single capability transforms the plugin from "AI generates random images with brand colors" to "AI generates images that look like the brand's own photography."

---

# PART 2: PLUGIN MANIFEST & DIRECTORY STRUCTURE

## 2.1 plugin.json

```json
{
  "name": "socialforge",
  "description": "Agency-grade social media calendar automation with asset-first compositing. Takes monthly content calendars, matches brand assets, generates AI-composed creative, renders carousels, adapts copy per platform, produces review galleries and delivery documents. Supports multiple brands, async approval workflows, and scheduled automation. Use this plugin for any social media content production, calendar automation, brand asset management, post generation, carousel creation, or social media workflow task.",
  "version": "1.0.0",
  "author": {
    "name": "INT TechShu Digital",
    "url": "https://intglobal.com"
  },
  "keywords": [
    "social-media", "content-calendar", "image-generation", "compositing",
    "carousel", "brand-assets", "marketing", "automation", "agency",
    "multi-brand", "approval-workflow"
  ]
}
```

## 2.2 Complete Directory Structure

```
socialforge/
│
├── .claude-plugin/
│   └── plugin.json
│
├── skills/
│   ├── brand-manager/
│   │   └── SKILL.md
│   ├── index-assets/
│   │   └── SKILL.md
│   ├── parse-calendar/
│   │   └── SKILL.md
│   ├── match-assets/
│   │   └── SKILL.md
│   ├── compose-creative/
│   │   └── SKILL.md
│   ├── render-carousels/
│   │   └── SKILL.md
│   ├── adapt-copy/
│   │   └── SKILL.md
│   ├── generate-video/
│   │   └── SKILL.md
│   ├── create-previews/
│   │   └── SKILL.md
│   ├── build-review-gallery/
│   │   └── SKILL.md
│   ├── manage-reviews/
│   │   └── SKILL.md
│   ├── assemble-document/
│   │   └── SKILL.md
│   ├── finalize-month/
│   │   └── SKILL.md
│   └── full-pipeline/
│       └── SKILL.md
│
├── commands/
│   ├── new-month.md
│   ├── index-assets.md
│   ├── generate-all.md
│   ├── generate-post.md
│   ├── edit-post.md
│   ├── edit-image.md
│   ├── swap-asset.md
│   ├── review.md
│   ├── revision.md
│   ├── client-review.md
│   ├── check-approvals.md
│   ├── finalize.md
│   ├── switch-brand.md
│   ├── reactive-post.md
│   ├── sync-calendar.md
│   ├── status.md
│   ├── cost-report.md
│   └── preview-batch.md
│
├── agents/
│   ├── image-compositor.md
│   ├── carousel-builder.md
│   ├── copy-adapter.md
│   ├── quality-reviewer.md
│   └── compliance-checker.md
│
├── hooks/
│   └── hooks.json
│
├── references/
│   ├── platform-specs.md
│   ├── compositing-guide.md
│   ├── image-gen-guide.md
│   ├── carousel-templates-guide.md
│   ├── brand-config-schema.md
│   ├── approval-chain-schema.md
│   ├── compliance-rules-schema.md
│   ├── asset-index-schema.md
│   ├── calendar-data-schema.md
│   ├── status-tracker-schema.md
│   └── troubleshooting.md
│
├── scripts/
│   ├── index_assets.py
│   ├── match_assets.py
│   ├── generate_image.py
│   ├── compose_image.py
│   ├── edit_image.py
│   ├── resize_image.py
│   ├── compose_text_overlay.py
│   ├── render_carousel.py
│   ├── render_preview.py
│   ├── build_gallery.py
│   ├── assemble_docx.js
│   ├── adapt_copy.py
│   ├── compliance_check.py
│   ├── verify_brand_colors.py
│   ├── cost_tracker.py
│   ├── status_manager.py
│   └── generate_video.py
│
├── assets/
│   ├── carousel-templates/
│   │   ├── generic-8slide.html
│   │   ├── comparison-10slide.html
│   │   ├── case-study-10slide.html
│   │   ├── tips-5slide.html
│   │   ├── playbook-8slide.html
│   │   ├── recap-6slide.html
│   │   ├── data-infographic-6slide.html
│   │   └── quote-card-single.html
│   ├── preview-templates/
│   │   ├── linkedin-post.html
│   │   ├── linkedin-carousel.html
│   │   ├── instagram-feed.html
│   │   ├── instagram-story.html
│   │   ├── twitter-post.html
│   │   ├── facebook-post.html
│   │   └── youtube-thumbnail.html
│   ├── gallery-template/
│   │   ├── gallery.html
│   │   ├── gallery.css
│   │   └── gallery.js
│   ├── document-template/
│   │   └── calendar-doc-structure.json
│   └── default-fonts/
│       ├── Montserrat-Bold.ttf
│       ├── Montserrat-SemiBold.ttf
│       ├── OpenSans-Regular.ttf
│       └── OpenSans-Light.ttf
│
├── .mcp.json
├── settings.json
├── CHANGELOG.md
└── README.md
```

## 2.3 Runtime Directory Structure (Created Per Brand)

```
~/socialforge-workspace/                    (or user-configured root)
├── brands/
│   ├── {brand-slug}/
│   │   ├── brand-config.json
│   │   ├── platform-config.json
│   │   ├── approval-chain.json
│   │   ├── compliance-rules.json
│   │   ├── content-buckets.json
│   │   ├── asset-index.json
│   │   ├── asset-source.json              (where assets live: drive path, local path, etc.)
│   │   ├── style-references/
│   │   │   ├── STYLE_GUIDE.md
│   │   │   └── style-ref-*.jpg/png
│   │   ├── carousel-templates/            (brand-specific overrides, optional)
│   │   └── brand-assets/                  (local copy of logos, avatars, fonts)
│   │       ├── logo-primary.png
│   │       ├── logo-white.png
│   │       ├── logo-icon.png
│   │       └── avatars/
│   └── {another-brand-slug}/
│       └── ...
│
├── output/
│   ├── {brand-slug}/
│   │   ├── {YYYY-MM}/
│   │   │   ├── calendar-data.json         (parsed calendar)
│   │   │   ├── asset-matches.json         (asset matching results)
│   │   │   ├── status-tracker.json        (per-post status state machine)
│   │   │   ├── cost-log.json              (API cost tracking)
│   │   │   ├── production/                (intermediate production files)
│   │   │   │   ├── images/
│   │   │   │   │   ├── post-{id}-variant-a.png
│   │   │   │   │   ├── post-{id}-variant-b.png
│   │   │   │   │   └── post-{id}-composed-{platform}.png
│   │   │   │   ├── carousels/
│   │   │   │   │   └── post-{id}/
│   │   │   │   │       ├── slide-01.png ... slide-NN.png
│   │   │   │   │       └── carousel.pdf
│   │   │   │   ├── previews/
│   │   │   │   │   └── post-{id}-{platform}-preview.png
│   │   │   │   ├── copy/
│   │   │   │   │   └── post-{id}-{platform}-copy.txt
│   │   │   │   └── video/
│   │   │   │       ├── post-{id}-script.md
│   │   │   │       ├── post-{id}-storyboard.md
│   │   │   │       └── post-{id}-thumbnail.png
│   │   │   ├── review/
│   │   │   │   └── gallery.html
│   │   │   └── FINAL/                     (only populated after finalization)
│   │   │       ├── 00-Calendar-Document/
│   │   │       ├── 01-Ready-to-Publish/
│   │   │       │   └── Week-{N}/
│   │   │       │       └── {date}-Post{id}-{title}/
│   │   │       │           └── {platform}/
│   │   │       │               ├── image-{WxH}.png
│   │   │       │               ├── copy.txt
│   │   │       │               └── preview.png
│   │   │       ├── 02-Carousels/
│   │   │       ├── 03-Video-Production-Kit/
│   │   │       ├── 04-Stories-Shorts/
│   │   │       ├── 05-Review-Gallery/
│   │   │       ├── 06-Publishing-Schedule/
│   │   │       └── 07-Production-Checklist/
│   │   └── {YYYY-MM-previous}/           (archived months)
│   └── {another-brand-slug}/
│
└── shared/
    └── prompt-logs/                       (all AI prompts logged for debugging/learning)
        └── {YYYY-MM-DD}-{brand}-{post-id}.json
```

---

# PART 3: DATA SCHEMAS

## 3.1 brand-config.json

```json
{
  "$schema": "socialforge/brand-config",
  "version": "1.0",
  
  "brand_name": "string — Display name of the brand",
  "brand_slug": "string — URL/folder-safe identifier (lowercase, hyphens)",
  "tagline": "string — Brand tagline, used in document headers and some templates",
  "industry": "string — pharma | bfsi | real-estate | saas | retail | healthcare | edtech | legal | manufacturing | hospitality | automotive | media | other",
  "website": "string — Brand's primary website URL",
  
  "logo_files": {
    "primary": "string — relative path to primary logo file",
    "white": "string — relative path to white/reversed logo",
    "icon": "string — relative path to icon/favicon version",
    "primary_dimensions": {"width": "number", "height": "number"},
    "min_clear_space_px": "number — minimum padding around logo"
  },
  
  "colors": {
    "primary": "string — hex color code (e.g., '#1B4F72')",
    "secondary": "string — hex color code",
    "accent": "string — hex color code",
    "background_light": "string — hex, typically '#FFFFFF'",
    "background_dark": "string — hex",
    "text_primary": "string — hex",
    "text_secondary": "string — hex",
    "text_on_primary": "string — hex, text color when on primary background",
    "text_on_dark": "string — hex, typically '#FFFFFF'",
    "gradient": {
      "enabled": "boolean",
      "start": "string — hex",
      "end": "string — hex",
      "direction": "string — 'to-right' | 'to-bottom' | 'to-bottom-right'"
    }
  },
  
  "fonts": {
    "heading": "string — font filename (e.g., 'Montserrat-Bold.ttf')",
    "subheading": "string",
    "body": "string",
    "accent": "string",
    "font_source": "string — 'bundled' (in brand-assets/) | 'google-fonts' | 'system'"
  },
  
  "visual_style": {
    "style_keywords": ["string array — e.g., 'modern', 'clean', 'professional', 'enterprise'"],
    "mood_keywords": ["string array — e.g., 'confident', 'innovative', 'authoritative'"],
    "photography_style": "string — 'warm natural light' | 'studio professional' | 'candid editorial' | 'corporate clean' | etc.",
    "illustration_style": "string — 'modern editorial' | 'flat design' | 'isometric' | 'hand-drawn' | 'none'",
    "color_temperature": "string — 'warm' | 'neutral' | 'cool'",
    "contrast_level": "string — 'high' | 'medium' | 'soft'"
  },
  
  "image_rules": [
    "string array — specific rules for image generation",
    "Example: 'No text overlay on AI-generated images (text added via compositing)'",
    "Example: 'Navy (#1B4F72) should appear in at least 30% of visual area'",
    "Example: 'Avoid generic stock photo aesthetics'",
    "Example: 'Always include subtle brand color accents'"
  ],
  
  "logo_overlay": {
    "enabled": "boolean",
    "position": "string — 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left'",
    "opacity": "number — 0.0 to 1.0 (e.g., 0.7)",
    "size_percentage": "number — logo width as % of image width (e.g., 8)",
    "platforms": ["string array — platforms where logo overlay is applied"],
    "exclude_platforms": ["string array — platforms where logo is NOT added"],
    "exclude_types": ["string array — content types excluded, e.g., 'carousel_slide', 'story'"]
  },
  
  "social_profiles": {
    "{platform_key}": {
      "name": "string — display name on the platform",
      "handle": "string — @handle",
      "avatar": "string — relative path to avatar image",
      "headline": "string — profile headline/bio (for preview rendering)",
      "url": "string — profile URL"
    }
  },
  
  "languages": {
    "primary": "string — ISO 639-1 code (e.g., 'en')",
    "secondary": "string | null",
    "bilingual_posts": "boolean",
    "bilingual_format": "string — 'primary_then_secondary' | 'secondary_then_primary' | 'separate_posts'",
    "platform_language_map": {
      "{platform_key}": "string — language code for this platform"
    }
  },
  
  "brand_hashtags": {
    "always_include": ["string array — hashtags added to every post, e.g., '#INTGlobal'"],
    "campaign_hashtags": {
      "{campaign_name}": ["string array — hashtags for this campaign"]
    }
  }
}
```

## 3.2 platform-config.json

```json
{
  "$schema": "socialforge/platform-config",
  
  "active_platforms": [
    {
      "key": "string — internal identifier (e.g., 'linkedin_company')",
      "name": "string — display name (e.g., 'LinkedIn Company Page')",
      "platform": "string — 'linkedin' | 'instagram' | 'x' | 'facebook' | 'youtube' | 'tiktok' | 'pinterest'",
      "profile_type": "string — 'company' | 'personal' | 'creator' | null",
      "enabled": "boolean",
      "posting_frequency": "string — 'daily' | '3-4/week' | '2/week' | 'weekly'",
      "optimal_posting_times": [
        {
          "day_of_week": "string — 'monday' | 'tuesday' | etc. | 'weekday' | 'weekend'",
          "time_utc": "string — 'HH:MM'",
          "time_local": "string — 'HH:MM {timezone}'",
          "note": "string — reason for this time"
        }
      ],
      "supported_formats": ["string array — 'static' | 'carousel' | 'video' | 'story' | 'reel' | 'short' | 'text_only' | 'poll' | 'document'"],
      "content_mix": {
        "video_percentage": "number — target % of video content",
        "carousel_percentage": "number",
        "static_percentage": "number",
        "text_only_percentage": "number"
      },
      "cross_post_from": "string | null — platform key to cross-post from (e.g., 'linkedin_company' for facebook)"
    }
  ],
  
  "cross_posting_rules": {
    "linkedin_to_facebook": {
      "enabled": "boolean",
      "adaptation": "string — 'direct_copy' | 'adapted' | 'manual'",
      "exclude_formats": ["string array — formats not cross-posted"]
    }
  }
}
```

## 3.3 approval-chain.json

```json
{
  "$schema": "socialforge/approval-chain",
  
  "tiers": {
    "HERO": {
      "internal_reviewers": ["string array — roles: 'social_media_manager', 'content_lead', 'strategy_lead', 'designer'"],
      "requires_ceo_approval": "boolean",
      "requires_client_approval": "boolean",
      "auto_flag_for_client": "boolean — automatically add to client review queue",
      "max_revisions": "number — maximum revision cycles before escalation (default: 3)"
    },
    "HUB": {
      "internal_reviewers": ["string array"],
      "requires_ceo_approval": "boolean",
      "requires_client_approval": "boolean",
      "auto_flag_for_client": "boolean"
    },
    "HYGIENE": {
      "internal_reviewers": ["string array"],
      "requires_ceo_approval": "boolean (typically false)",
      "requires_client_approval": "boolean (typically false)",
      "auto_flag_for_client": "boolean (typically false)"
    }
  },
  
  "special_rules": {
    "founder_content": {
      "requires_founder_approval": "boolean",
      "notify": ["string array — email addresses"]
    },
    "case_study": {
      "requires_client_subject_approval": "boolean — the featured client must approve",
      "note": "string"
    },
    "data_claims": {
      "requires_research_verification": "boolean",
      "note": "string"
    }
  },
  
  "escalation_rules": {
    "{tier}": {
      "reminder_after_days": "number",
      "reminder_channel": "string — 'slack' | 'email' | 'both'",
      "reminder_message_template": "string — supports {post_count}, {brand_name}, {month}",
      "escalate_after_days": "number",
      "escalate_to": "string — role",
      "auto_publish_without_client": "boolean",
      "auto_publish_note": "string — appended to status tracker when auto-published"
    }
  },
  
  "scheduled_reminders": {
    "enabled": "boolean",
    "check_frequency": "string — 'daily_9am' | 'twice_daily' | 'weekdays_only'",
    "channels": ["string array — 'slack', 'email'"],
    "timezone": "string — IANA timezone (e.g., 'Asia/Kolkata')"
  }
}
```

## 3.4 compliance-rules.json

```json
{
  "$schema": "socialforge/compliance-rules",
  
  "industry": "string — industry identifier",
  
  "banned_phrases": [
    {
      "phrase": "string — exact phrase or regex pattern",
      "match_type": "string — 'exact' | 'contains' | 'regex'",
      "case_sensitive": "boolean",
      "severity": "string — 'critical' (blocks) | 'warning' (flags)",
      "reason": "string — why this phrase is banned",
      "suggestion": "string — recommended alternative"
    }
  ],
  
  "required_disclaimers": {
    "{trigger_context}": {
      "disclaimer_text": "string",
      "placement": "string — 'end_of_copy' | 'beginning' | 'separate_comment'",
      "platforms": ["string array — which platforms need this disclaimer"]
    }
  },
  
  "image_compliance": [
    {
      "rule": "string — description of the image rule",
      "severity": "string — 'critical' | 'warning'",
      "check_method": "string — 'ai_review' | 'manual_flag'"
    }
  ],
  
  "data_claim_rules": {
    "require_source": "boolean — flag any statistic for source verification",
    "max_claim_age_months": "number — how old a stat can be before flagging as stale",
    "patterns_to_flag": ["string array — regex patterns, e.g., '\\d+%', '\\$[\\d,]+']"
  },
  
  "platform_specific_rules": {
    "{platform_key}": {
      "link_policy": "string — 'allowed' | 'link_in_bio' | 'no_links'",
      "max_hashtags": "number",
      "mandatory_hashtags": ["string array"],
      "forbidden_content_types": ["string array — e.g., 'before_after' for pharma on IG"]
    }
  }
}
```

## 3.5 asset-index.json

```json
{
  "$schema": "socialforge/asset-index",
  
  "brand": "string — brand slug",
  "indexed_at": "string — ISO 8601 timestamp",
  "source": "string — 'google-drive' | 'local' | 'dropbox' | 'url'",
  "source_path": "string — the root path/URL of the asset library",
  "total_assets": "number",
  
  "assets": [
    {
      "id": "string — unique identifier (e.g., 'asset_001')",
      "filename": "string",
      "path": "string — full path to the file",
      "relative_path": "string — path relative to asset library root",
      "folder": "string — the subfolder category (e.g., 'people/founder')",
      
      "dimensions": {"width": "number", "height": "number"},
      "aspect_ratio": "string — e.g., '3:2'",
      "file_size_mb": "number",
      "format": "string — 'jpeg' | 'png' | 'webp'",
      
      "ai_description": "string — Gemini Vision's natural language description of the image",
      
      "tags": ["string array — categorization tags derived from AI analysis"],
      
      "detected_colors": ["string array — hex codes of dominant colors"],
      "dominant_mood": "string",
      "lighting": "string — 'natural' | 'studio' | 'ambient' | 'dramatic' | etc.",
      "setting": "string — 'indoor' | 'outdoor' | 'studio' | 'office' | etc.",
      "subjects": ["string array — what's in the image: 'person', 'product', 'office', etc."],
      
      "suitable_for": [
        "string array — natural language descriptions of what posts this image suits"
      ],
      
      "platforms_compatible": {
        "{platform_key}": {
          "crop_feasible": "boolean — can this be cropped to the platform's required ratio without losing key content",
          "recommended_crop": {
            "x": "number", "y": "number", "width": "number", "height": "number"
          }
        }
      },
      
      "usage_history": [
        {
          "month": "string — YYYY-MM",
          "post_ids": ["number array"],
          "platforms": ["string array"],
          "date": "string — ISO 8601"
        }
      ],
      
      "has_transparency": "boolean — PNG with alpha channel",
      "has_background": "boolean — true if the image has a real background (not product-on-white)",
      "background_removable": "boolean — is the subject clearly separable from background",
      
      "is_style_reference": "boolean — part of the style reference set",
      "style_reference_context": "string | null — when to use this style reference"
    }
  ]
}
```

## 3.6 calendar-data.json

```json
{
  "$schema": "socialforge/calendar-data",
  
  "brand": "string — brand slug",
  "month": "string — YYYY-MM",
  "fiscal_context": "string — e.g., 'Month 1 of FY 2026-27, Q1'",
  "campaign": {
    "name": "string | null",
    "hashtag": "string | null",
    "active_weeks": ["number array — which weeks the campaign is active"],
    "phase_per_week": {"1": "string", "2": "string"}
  },
  
  "summary": {
    "total_posts": "number",
    "total_primary_posts": "number",
    "total_adapted_posts": "number",
    "posts_per_platform": {"{platform_key}": "number"},
    "tier_distribution": {"HERO": "number", "HUB": "number", "HYGIENE": "number"},
    "content_type_distribution": {
      "static": "number",
      "carousel": "number",
      "video": "number",
      "text_only": "number",
      "poll": "number",
      "story": "number",
      "short_reel": "number"
    },
    "generation_routing": {
      "anchor_compose": "number",
      "enhance_extend": "number",
      "style_referenced": "number",
      "pure_creative": "number",
      "needs_real_asset": "number",
      "carousel_template": "number",
      "text_only": "number"
    }
  },
  
  "special_dates": [
    {
      "date": "string — YYYY-MM-DD",
      "occasion": "string",
      "relevance": "string — why this matters for the brand",
      "content_action": "string — what to post or not post",
      "posting_restriction": "string | null — e.g., 'no promotional content'"
    }
  ],
  
  "content_buckets": [
    {
      "id": "string",
      "name": "string",
      "category": "string — e.g., 'Cat 1: Business'",
      "posts_this_month": "number",
      "rationale": "string — why this bucket is active this month"
    }
  ],
  
  "posts": [
    {
      "post_id": "number — unique sequential ID",
      "date": "string — YYYY-MM-DD",
      "day_of_week": "string",
      "week_number": "number — 1-5",
      "title": "string — short descriptive title",
      
      "content_bucket": "string — bucket name or ID",
      "category": "string",
      "tier": "string — 'HERO' | 'HUB' | 'HYGIENE'",
      "series_id": "string | null — e.g., '#CTOPlaybook Ep.1'",
      
      "platforms": [
        {
          "key": "string — platform key from platform-config",
          "name": "string — display name",
          "format": "string — 'static' | 'carousel' | 'video' | etc.",
          "is_primary": "boolean — is this the primary platform for this post or adapted",
          "aspect_ratio": "string — e.g., '16:9'",
          "image_size": "string — e.g., '1200x627'",
          "char_limit": "number",
          "hashtag_limit": "number"
        }
      ],
      
      "copy": {
        "option_a": "string — primary copy text",
        "option_b": "string | null — alternate copy text",
        "first_comment": "string | null — text for first comment (LinkedIn strategy)",
        "hashtags": ["string array — suggested hashtags"]
      },
      
      "visual": {
        "direction_a": "string — primary visual direction/brief",
        "direction_b": "string | null — alternate visual direction",
        "asset_reference": "string | null — if the brief references a specific asset by name/file",
        "creative_mode_hint": "string | null — 'ANCHOR_COMPOSE' | 'ENHANCE_EXTEND' | 'STYLE_REFERENCED' | 'PURE_CREATIVE' if specified in the brief"
      },
      
      "content_type": "string — 'static' | 'carousel' | 'video' | 'text_only' | 'poll' | 'story' | 'short_reel'",
      "carousel_details": {
        "slide_count": "number | null",
        "slide_briefs": ["string array | null — per-slide content descriptions"],
        "carousel_type": "string | null — 'comparison' | 'case_study' | 'tips' | 'playbook' | 'recap' | 'data' | 'generic'"
      },
      "video_details": {
        "duration_seconds": "number | null",
        "video_type": "string | null — 'hero_video' | 'mini_case_study' | 'short_reel' | 'story' | 'talking_head'",
        "production_brief": "string | null",
        "animation_fallback": "boolean — can this be done as animation if live footage unavailable"
      },
      
      "production": {
        "creative_mode": "string — assigned after asset matching: 'ANCHOR_COMPOSE' | 'ENHANCE_EXTEND' | 'STYLE_REFERENCED' | 'PURE_CREATIVE' | 'CAROUSEL_TEMPLATE' | 'NEEDS_REAL_ASSET' | 'TEXT_ONLY'",
        "matched_asset_id": "string | null — from asset-index, the primary matched asset",
        "matched_asset_score": "number | null — 0.0 to 1.0",
        "alternative_assets": ["string array | null — asset IDs of ranked alternatives"],
        "style_references": ["string array | null — style reference asset IDs to use for generation"],
        "generation_prompt": "string | null — the constructed prompt (populated after Phase 2)"
      },
      
      "boosting": {
        "recommended": "boolean",
        "budget_range": "string — e.g., '$50-$75'",
        "target_audience": "string",
        "key_metric": "string — e.g., 'save rate' | 'reach' | 'engagement'"
      },
      
      "dependencies": ["string array — things needed before this post can be produced"],
      "production_notes": "string | null — additional context for the production team",
      "cross_channel_notes": "string | null — notes about how to adapt across channels"
    }
  ]
}
```

## 3.7 status-tracker.json

```json
{
  "$schema": "socialforge/status-tracker",
  
  "brand": "string",
  "month": "string — YYYY-MM",
  "created_at": "string — ISO 8601",
  "last_updated": "string — ISO 8601",
  
  "pipeline_status": {
    "phase_0_parse": "string — 'not_started' | 'complete'",
    "phase_1_asset_match": "string — 'not_started' | 'in_progress' | 'complete' | 'confirmed'",
    "phase_2_production": "string — 'not_started' | 'in_progress' | 'complete'",
    "phase_3_copy": "string",
    "phase_4_previews": "string",
    "phase_5_review_gallery": "string",
    "phase_6_approval": "string — 'in_progress' (always async)",
    "phase_7_finalized": "string"
  },
  
  "posts": {
    "{post_id}": {
      "status": "string — state machine value (see below)",
      "creative_mode": "string — the assigned mode",
      "asset_used": "string | null — asset ID from index",
      "image_variants": [
        {
          "variant_id": "string — 'a', 'b', 'c'",
          "path": "string — file path to the generated image",
          "generation_method": "string — 'anchor_compose' | 'enhance_extend' | 'style_ref' | 'pure_ai' | 'direct_use'",
          "prompt_used": "string | null — reference to prompt log",
          "quality_score": "number | null — from quality reviewer",
          "selected": "boolean — is this the chosen variant"
        }
      ],
      "copy_selected": "string — 'option_a' | 'option_b' | 'custom'",
      "copy_custom_text": "string | null — if custom copy was written",
      "copy_edited": "boolean",
      
      "internal_reviewer": "string | null",
      "internal_review_date": "string | null — ISO 8601",
      "internal_notes": "string | null",
      
      "client_review_status": "string — 'not_required' | 'pending' | 'sent' | 'approved' | 'revision_requested' | 'rejected'",
      "client_reviewer": "string | null",
      "client_review_date": "string | null",
      "client_feedback": "string | null",
      
      "ceo_approval_status": "string — 'not_required' | 'pending' | 'approved' | 'rejected'",
      
      "revision_history": [
        {
          "revision_number": "number",
          "requested_by": "string — 'internal' | 'client' | 'ceo'",
          "request_date": "string — ISO 8601",
          "feedback": "string",
          "what_changed": "string — description of what was regenerated",
          "completed_date": "string | null"
        }
      ],
      
      "flags": ["string array — 'hero_content', 'needs_ceo_approval', 'needs_photography', 'needs_video_production', 'data_claim_unverified', 'compliance_warning'"],
      
      "finalized": "boolean",
      "finalized_date": "string | null"
    }
  },
  
  "approval_summary": {
    "total_posts": "number",
    "finalized": "number",
    "approved_internal": "number",
    "pending_client": "number",
    "pending_ceo": "number",
    "revision_requested": "number",
    "rejected": "number",
    "blocked": "number"
  }
}
```

**Status State Machine (per post):**

```
QUEUED → ASSET_MATCHING → GENERATING → PENDING_REVIEW
                                            │
                          ┌─────────────────┼─────────────────┐
                          │                 │                 │
                          ▼                 ▼                 ▼
                   APPROVED_INTERNAL  REVISION_REQUESTED  REJECTED
                          │                 │
                          │                 └→ GENERATING (specific elements only)
                          │
                          ▼ (if client review required)
                   PENDING_CLIENT
                          │
              ┌───────────┼───────────┐
              │           │           │
              ▼           ▼           ▼
       APPROVED_CLIENT  REVISION_REQ_CLIENT  REJECTED_CLIENT
              │           │
              │           └→ GENERATING (specific elements only)
              │
              ▼ (if CEO approval required)
       PENDING_CEO
              │
              ▼
       APPROVED_CEO
              │
              ▼
          FINAL (write-protected by hook)
```

Transitions are logged with timestamp, actor, and notes.

---

# PART 4: CORE CONCEPT — ASSET-FIRST COMPOSITING (DETAILED)

## 4.1 The Priority Chain

For every post, before any generation:

```
PRIORITY 1: Does the calendar brief reference a specific asset by name?
  YES → Load that asset → Assign creative mode based on brief language
  NO  → Continue to Priority 2

PRIORITY 2: Does the asset index have a high-confidence match (score > 0.8)?
  YES → Recommend ANCHOR_COMPOSE or ENHANCE_EXTEND
  NO  → Continue to Priority 3

PRIORITY 3: Does the asset index have partial matches (score 0.3-0.8)?
  YES → Recommend STYLE_REFERENCED (use matches as reference images)
  NO  → Continue to Priority 4

PRIORITY 4: No relevant brand assets found
  → Assign PURE_CREATIVE (or CAROUSEL_TEMPLATE for carousels)
  → If content_type is 'video', assign NEEDS_REAL_ASSET + generate script/storyboard
```

## 4.2 The Asset Matching Algorithm

```
INPUTS:
  post_data: the parsed post from calendar-data.json
  asset_index: the brand's indexed asset library
  current_month_usage: which assets have been used this month and how often

STEP 1: KEYWORD EXTRACTION
  Extract from post_data:
    - Content bucket keywords
    - Visual direction keywords (subjects, settings, moods)
    - Post description keywords (topics, themes)
    - Format requirements (portrait, landscape, square)
    - Explicit asset references ("use the product hero shot")

STEP 2: CANDIDATE SEARCH
  For each asset in the index:
    Calculate multi-factor score:
    
    TAG_OVERLAP (weight: 0.30)
      Overlap between post keywords and asset tags
      Normalized: overlap_count / total_post_keywords
    
    SUITABILITY_MATCH (weight: 0.25)
      How many of the asset's "suitable_for" descriptions match the post context
      Semantic matching, not just keyword
    
    CONTENT_BUCKET_MATCH (weight: 0.20)
      Does the asset explicitly suit this content bucket?
      Exact match: full score. Partial: half score.
    
    CROP_FEASIBILITY (weight: 0.15)
      Can the asset be cropped to ALL required platform ratios without losing the subject?
      All platforms feasible: full score. Some: partial. None: zero.
    
    FRESHNESS (weight: 0.10, acts as penalty)
      How many times was this asset used this month?
      0 uses: no penalty
      1 use: score × 0.85
      2 uses: score × 0.60
      3+ uses: score × 0.30
      Same week as a previous use: additional penalty × 0.50
    
    FINAL_SCORE = (TAG × 0.30) + (SUIT × 0.25) + (BUCKET × 0.20) + (CROP × 0.15) - FRESHNESS_PENALTY

STEP 3: RANKING AND RECOMMENDATION
  Sort candidates by final score descending
  
  Top candidate score > 0.8 → Recommend ANCHOR_COMPOSE or ENHANCE_EXTEND
    (ANCHOR if asset needs new background/scene; ENHANCE if asset is fine but needs tweaking)
  
  Top candidate score 0.5-0.8 → Recommend ENHANCE_EXTEND or STYLE_REFERENCED
    (depends on how closely the asset matches the brief's scene description)
  
  Top candidate score 0.3-0.5 → Recommend STYLE_REFERENCED
    (asset isn't suitable for direct use but can guide AI generation)
  
  Top candidate score < 0.3 or no candidates → Recommend PURE_CREATIVE
  
  Always return top 5 candidates regardless of score (user may override)

STEP 4: STYLE REFERENCE SELECTION
  Regardless of the per-post asset match, also select style reference images:
  - Load all assets marked is_style_reference: true
  - Filter by relevance to post mood/setting (warm refs for warm posts, etc.)
  - Select 2-5 style references for this post's generation
  - These are ALWAYS fed to Nano Banana 2 alongside the text prompt
    (even in ANCHOR_COMPOSE mode, they guide the background generation)

OUTPUT:
  {
    "post_id": number,
    "recommendation": "ANCHOR_COMPOSE" | "ENHANCE_EXTEND" | "STYLE_REFERENCED" | "PURE_CREATIVE",
    "primary_asset": {asset_id, score, reasons},
    "alternatives": [{asset_id, score, reasons}, ...],  // top 5
    "style_references": [asset_ids],
    "gap_flag": boolean,  // true if no suitable asset and this post SHOULD have one
    "gap_note": string    // e.g., "This is a founder post but no founder photos available"
  }
```

## 4.3 The Compositing Pipeline (ANCHOR_COMPOSE Mode)

```
INPUT: 
  core_asset: the brand's image (product photo, headshot, screenshot)
  scene_brief: the calendar's creative direction describing the desired scene
  brand_config: colors, style, mood
  style_references: 2-5 brand style reference photos
  platform_specs: required dimensions per platform

STEP 1: ASSET ANALYSIS
  Determine if the asset has:
  a) Transparent background → ready for compositing
  b) White/solid background → needs background removal
  c) Complex background → may use ENHANCE_EXTEND instead, or mask the subject
  
  If background removal needed:
    Use rembg (Python library) to remove background
    Output: asset with alpha channel (PNG)
    Verify: check that removal didn't clip important parts of the subject
    If removal quality is poor → flag for manual masking

STEP 2: SCENE GENERATION
  Construct the AI prompt:
  
  LAYER 1 — BRAND CONTEXT:
    "Generate a professional background scene for compositing."
    "Brand: {brand_name}"
    "Visual style: {style_keywords}"
    "Color palette: primary {primary_hex}, secondary {secondary_hex}, accent {accent_hex}"
    "Color temperature: {warm/neutral/cool}"
    "The composition must leave clear space at {position} for a {asset_type} 
     that will be composited in. The asset dimensions are approximately 
     {width}x{height} pixels and should occupy {30-50}% of the canvas width."
  
  LAYER 2 — SCENE BRIEF:
    "{scene_brief from calendar}"
    Example: "Modern bathroom counter, marble surface, morning sunlight 
     streaming from the left. Minimalist, clean. A single green plant 
     in the background."
  
  LAYER 3 — TECHNICAL:
    "Aspect ratio: {master_aspect_ratio}"
    "NO text, typography, or words anywhere in the image"
    "The area where the product will be placed should have a clear, 
     uncluttered surface/background suitable for compositing"
    "High resolution, clean edges, no artifacts"
  
  Feed style reference images alongside this prompt to Nano Banana 2.
  
  Generate 2-3 scene variants.

STEP 3: COMPOSITING
  For each scene variant:
    a) Determine placement position based on brief 
       (centered, rule-of-thirds, left-aligned, etc.)
    b) Scale the core asset to the appropriate size 
       (maintain aspect ratio, target size from prompt)
    c) Place asset onto generated background
    d) Add natural shadow/reflection:
       - Drop shadow (subtle, matching the scene's light direction)
       - Surface reflection if the surface is reflective (glass, marble)
    e) Edge blending:
       - Subtle feathering at asset edges to prevent "cut-out" look
       - Color temperature matching between asset and scene
    f) Quality check:
       - Asset not distorted, compressed, or cropped
       - Asset sits naturally in the scene (not floating)
       - Light direction on asset matches scene lighting

STEP 4: BRAND OVERLAY
  Apply brand elements on top of the composed image:
  a) Logo watermark (per logo_overlay config)
  b) Text overlay (headline, CTA, data points — per creative brief)
     Using compose_text_overlay.py with brand fonts and colors
  c) Brand frame/border (if brand template requires it)

STEP 5: PLATFORM VARIANTS
  From the composed master:
  a) Crop/resize for each target platform's specs
  b) Ensure the core asset is still fully visible in every crop
     (if a crop would cut the product, adjust composition)
  c) For story/vertical (9:16): may need to recompose — 
     generate a separate vertical scene or use AI to extend the composition vertically

OUTPUT:
  - post-{id}-variant-{a/b/c}-master.png (full resolution composed image)
  - post-{id}-variant-{a/b/c}-{platform}.png (per-platform crops)
  - post-{id}-composition-metadata.json (what asset was used, where placed, what was generated)
```

## 4.4 The Enhancement Pipeline (ENHANCE_EXTEND Mode)

```
INPUT:
  brand_asset: the complete brand photograph (with its own background)
  edit_instructions: derived from the calendar brief
  brand_config: colors, style
  platform_specs: required dimensions

STEP 1: DETERMINE EDIT TYPE
  Parse the brief for what kind of enhancement is needed:
  
  a) BACKGROUND_EXTENSION: Image is the right subject but wrong aspect ratio,
     or needs more visual breathing room.
     Action: Use Gemini image editing to extend edges.
  
  b) MOOD_ENHANCEMENT: Image is correct but mood doesn't match the post.
     Action: Edit instructions for color grading, lighting changes.
     Example: "Make this office photo feel warmer, golden hour light"
  
  c) ELEMENT_ADDITION: Image needs additional visual elements.
     Action: Edit instructions to add specific elements.
     Example: "Add a subtle bokeh effect to the background"
     Example: "Add a laptop showing a dashboard on the desk"
  
  d) STYLE_TRANSFER: Image needs to look more polished/branded.
     Action: Edit instructions for style modification.
     Example: "Make this look more like a professional editorial photo"

STEP 2: EXECUTE EDIT
  Send the brand asset + edit instructions to Gemini's image editing API.
  
  For Nano Banana 2 editing:
    Feed the real image as the first content part.
    Feed the edit instruction as the text part.
    Include style reference images if mood matching is needed.
  
  Generate 2 variants (original edit + slight variation).

STEP 3: VERIFY CORE PRESERVATION
  Compare the edited image against the original:
  - Core subject must be recognizable and faithful
  - No distortion of products, faces, or key elements
  - Colors of the core subject shouldn't shift dramatically
  - If verification fails → flag for human review

STEP 4: OVERLAY AND RESIZE
  Same as ANCHOR_COMPOSE steps 4-5.
```

## 4.5 The Generation Pipeline (STYLE_REFERENCED Mode)

```
INPUT:
  text_prompt: the creative brief from the calendar
  style_references: 2-8 brand style reference photos
  brand_config: colors, style, mood, image_rules
  platform_specs: required dimensions

STEP 1: CONSTRUCT PROMPT
  Build the 5-layer prompt:
  
  LAYER 1 — BRAND IDENTITY:
    Brand name, visual style keywords, mood keywords,
    color palette with hex codes, color temperature, contrast level
  
  LAYER 2 — POST CONTEXT:
    Content bucket, tier, campaign theme (if any),
    emotional tone, target audience
  
  LAYER 3 — CREATIVE DIRECTION:
    The calendar's visual direction text (the scene description)
  
  LAYER 4 — IMAGE RULES:
    All rules from brand_config.image_rules[]
    Always includes: "NO text, typography, words, or letters in the image"
  
  LAYER 5 — TECHNICAL:
    Aspect ratio, resolution target, platform name

STEP 2: FEED REFERENCES + PROMPT TO NANO BANANA 2
  Contents array:
    [style_ref_1_image, style_ref_2_image, ..., text_prompt]
  
  Add instruction:
    "Match the visual style, lighting, and color temperature of the 
     reference images. The generated image should look like it belongs 
     in the same photo library as these references."
  
  Config:
    response_modalities: ['TEXT', 'IMAGE']
  
  Generate 2-3 variants.

STEP 3: QUALITY REVIEW
  Run quality-reviewer agent on each variant:
  - Brand color percentage (>20% of image should contain brand palette)
  - Mood alignment with brief
  - Text-free verification (no phantom text from AI)
  - Stock photo check (should NOT look generic)
  - Brief alignment (does it match what was described?)
  
  Score each variant. Flag any below threshold.
  Auto-regenerate once if quality score < 3.0 (with strengthened prompt).

STEP 4: OVERLAY AND RESIZE
  Same as previous modes — logo, text, platform crops.
```

## 4.6 The Generation Pipeline (PURE_CREATIVE Mode)

Same as STYLE_REFERENCED but without reference images in the API call. Only the text prompt + brand config text guides the generation. Used when no style references are defined or for generic content where brand visual DNA isn't critical.

## 4.7 User Control Per Post

The creative mode is a RECOMMENDATION. The user can always override:

**At asset matching stage (Phase 1):**
- "Use this specific asset for Post #5" → overrides the matched asset
- "Don't use any brand asset for this post, go full AI" → switches to STYLE_REF or PURE_CREATIVE
- "I want to use this asset but keep its background, just enhance the lighting" → switches to ENHANCE_EXTEND

**At review stage (Phase 5):**
- "The composition is good but I want a different background" → regenerate background only, keep asset placement
- "Swap the product photo for a different angle" → re-run compositing with new asset
- "This AI-generated one looks better than the composed version" → select the AI variant
- "Edit: make the background warmer" → send to edit API
- "Upload a completely new image for this post" → bypass all generation, use uploaded image directly

**The mode is stored in status-tracker.json per post.** If the user overrides, the override is logged with reason.

---

# PART 5: SKILL SPECIFICATIONS

Each skill is a SKILL.md file that Claude loads when the skill triggers. The SKILL.md contains instructions that Claude follows.

## 5.1 brand-manager

```yaml
---
name: brand-manager
description: >
  Register, configure, switch, and manage brand profiles in SocialForge.
  Trigger when user says: "add brand", "new brand", "register brand",
  "switch brand", "change client", "set up brand", "configure brand",
  "update brand config", "show brands", "list brands", "brand settings".
  Also trigger when /socialforge:add-brand or /socialforge:switch-brand
  commands are invoked.
---
```

**Responsibilities:**
1. Register a new brand: Create the brand directory structure, prompt user for brand config values (or accept a brand-config.json upload), validate config against schema, create empty asset-index.json and status files.
2. Switch active brand: Save current brand state, load the requested brand's config, asset index, and any active month's status tracker. Update the session's active brand context.
3. Update brand config: Modify specific fields in brand-config.json. Validate changes. If colors changed, note that existing generated assets may need regeneration.
4. List all registered brands: Show brand name, slug, industry, last active month, asset count.
5. Delete brand: Confirm twice (destructive). Archive, don't delete. Move to `brands/_archived/`.

**Validation rules:**
- brand_slug must be unique, lowercase, alphanumeric + hyphens only
- At least primary color must be defined
- At least one platform must be configured
- Logo file paths must point to existing files
- Fonts must be either bundled (file exists) or marked as google-fonts/system

**Data flow:**
- Creates/reads/updates: `brands/{slug}/brand-config.json`, `brands/{slug}/platform-config.json`, `brands/{slug}/approval-chain.json`, `brands/{slug}/compliance-rules.json`
- Session state: Sets `SOCIALFORGE_ACTIVE_BRAND` environment context

## 5.2 index-assets

```yaml
---
name: index-assets
description: >
  Scan, analyze, and index a brand's visual asset library using Gemini Vision.
  Trigger when: "index assets", "scan assets", "analyze images", "update asset library",
  "add new images", "connect asset folder", "set up assets", "reindex",
  or when /socialforge:index-assets is invoked.
  Also trigger automatically when a brand is first registered and an asset
  source is provided, or when sync-calendar detects new images in the source folder.
---
```

**Responsibilities:**
1. Connect to asset source: Accept a local folder path, Google Drive path (via Drive MCP), or URL. Store connection info in `brands/{slug}/asset-source.json`.
2. Scan for images: Walk the folder tree, identify all image files (jpg, jpeg, png, webp, gif). Record file paths, dimensions, file sizes.
3. Analyze each image: For each image, call Gemini Vision (gemini-3-flash or similar) with a structured prompt requesting:
   - Natural language description of the image
   - Subject identification (person, product, office, event, abstract, etc.)
   - Detected colors (dominant hex codes)
   - Mood/atmosphere
   - Lighting conditions
   - Setting/environment
   - What kinds of social media posts this would be suitable for
   - Whether the background is removable (clear subject vs complex scene)
4. Build the asset index: Create/update `brands/{slug}/asset-index.json` per schema.
5. Detect new images: Compare current file list against existing index. Only analyze new/changed files. Skip already-indexed files.
6. Flag low-quality images: Images below 800px in either dimension are flagged as unsuitable for social media.
7. Categorize: Auto-assign folder categories based on AI analysis + folder names.
8. Style reference suggestion: After indexing, recommend 5-8 images that would make good style references based on quality, variety, and brand representativeness. User confirms or adjusts.

**Prompt for Gemini Vision analysis (per image):**
```
Analyze this brand asset image for a social media automation system.

Provide a JSON response with these fields:
{
  "description": "2-3 sentence natural language description of what's in the image",
  "subjects": ["array of main subjects: 'person', 'product', 'office', 'lab', 'event', 'nature', 'abstract', 'food', 'vehicle', 'building', etc."],
  "tags": ["15-20 descriptive tags covering subject, setting, mood, style, colors, composition"],
  "dominant_colors_hex": ["top 5 hex color codes"],
  "mood": "1-3 word mood description",
  "lighting": "type of lighting: natural/studio/ambient/dramatic/mixed",
  "setting": "indoor/outdoor/studio/mixed + specific setting if identifiable",
  "suitable_for": ["3-5 descriptions of what social media posts this would work for"],
  "background_type": "transparent/solid_white/solid_color/simple/complex",
  "background_removable": true/false,
  "quality_assessment": "high/medium/low",
  "style_reference_worthy": true/false
}
```

**Rate limiting:** Gemini Vision free tier allows ~500 requests/day. For large libraries (200+ images), batch over multiple sessions or use rate limiting with 2-second delays.

**Incremental indexing:** The `--new-only` flag skips already-indexed files. Uses file modification timestamps to detect changes.

## 5.3 parse-calendar

```yaml
---
name: parse-calendar
description: >
  Parse a social media content calendar document into structured data.
  Supports DOCX, XLSX, Notion database, or structured text input.
  Trigger when: "upload calendar", "parse calendar", "read calendar",
  "load calendar", "import calendar", "process the calendar",
  or when /socialforge:new-month is invoked with a calendar input.
  Also trigger when user uploads a DOCX/XLSX file that appears to be a content calendar.
---
```

**Responsibilities:**
1. Detect input format: DOCX (use pandoc to markdown), XLSX (use openpyxl), Notion (use Notion MCP connector), or plain text/markdown.
2. Extract all posts: Identify every individual post in the calendar. Handle multi-post days. Handle cross-platform posts (one post going to multiple platforms).
3. Structure each post into the calendar-data.json schema (Part 3.6).
4. Extract metadata: Campaign info, special dates, content bucket definitions, distribution matrices, budget info.
5. Detect content types: Classify each post as static/carousel/video/text_only/poll/story/short based on format column and visual direction text.
6. Detect carousel details: If carousel, extract slide count, per-slide content descriptions.
7. Detect video details: If video, extract duration, type, production notes.
8. Parse visual directions: Extract both option A and option B visual directions. Identify explicit asset references in the brief.
9. Parse copy options: Extract option A and option B copy text.
10. Detect dependencies: Scan for phrases like "needs approval", "requires filming", "client permission needed" and extract as dependency items.
11. Present summary for confirmation: Show the parsed summary (total posts, platform distribution, tier breakdown, content type mix, detected dependencies) and wait for user confirmation before proceeding.

**Parsing logic for DOCX calendars:**
The INT. Global calendar format has a specific structure:
- Weekly calendar grids in tables (Day/Date, Post #, Content Bucket, Tier, Format, Channel, Post Hint)
- Post-by-post creative briefs in sections (Section 1-7 per post)
- Summary tables for remaining posts
- Stories/Shorts plans in separate sections

The parser should handle:
- Table extraction from converted markdown
- Section header detection for creative briefs
- Multi-format content extraction (tables + prose + lists)
- Robust handling of inconsistent formatting

**For XLSX:**
Expected columns: Day, Date, Platform, Post Description, Image Description, Content Bucket, Tier, Format
May vary — the parser should be flexible and ask the user to confirm column mapping if uncertain.

**For Notion:**
Use the Notion MCP connector to query the database.
Expected properties: Date, Platform, Copy, Image Brief, Content Bucket, Tier, Status
Map Notion properties to the calendar-data schema.

**Output:** `output/{brand}/{month}/calendar-data.json`

## 5.4 match-assets

```yaml
---
name: match-assets
description: >
  Match brand assets to parsed calendar posts and assign creative modes.
  Runs after parse-calendar. Uses the asset index to find the best brand
  asset for each post, recommends the creative mode (ANCHOR_COMPOSE,
  ENHANCE_EXTEND, STYLE_REFERENCED, PURE_CREATIVE), and produces an
  asset coverage report.
  Trigger when: "match assets", "find images for posts", "asset matching",
  "what images should we use", "asset coverage", "run asset matching",
  or automatically as part of the full pipeline after calendar parsing.
---
```

**Responsibilities:**
1. Load the parsed calendar and asset index for the active brand.
2. For each post, run the asset matching algorithm (Part 4.2).
3. Assign a creative mode per post.
4. Select style reference images per post.
5. Generate the asset coverage report:
   - % of posts with direct asset matches (ANCHOR/ENHANCE)
   - % using style-referenced generation
   - % needing pure AI generation
   - List of asset gaps (posts that SHOULD have brand assets but don't)
6. Generate an asset request list (what the team should photograph/source).
7. Present the matching results for user confirmation/override.
8. After confirmation, update calendar-data.json with production routing info.
9. Save `output/{brand}/{month}/asset-matches.json`.

**User override interface:**
For each post, allow:
- Accept recommendation
- Select a different asset from the library
- Change creative mode
- Upload a new asset on the spot
- Mark as "skip asset matching — I'll handle this manually"

## 5.5 compose-creative

```yaml
---
name: compose-creative
description: >
  The core creative production engine. Takes the asset matching results and
  produces visual assets for each post according to its assigned creative mode.
  Handles all four modes: ANCHOR_COMPOSE, ENHANCE_EXTEND, STYLE_REFERENCED,
  PURE_CREATIVE. Also handles direct-use assets (resize + overlay only).
  Trigger when: "generate images", "create visuals", "produce assets",
  "run production", or as part of the full pipeline after asset matching.
  Also triggers for single-post generation or regeneration.
---
```

**Responsibilities:**
1. Route each post to the correct production pipeline based on creative_mode.
2. Execute the compositing pipeline (Part 4.3) for ANCHOR_COMPOSE posts.
3. Execute the enhancement pipeline (Part 4.4) for ENHANCE_EXTEND posts.
4. Execute the style-referenced generation pipeline (Part 4.5) for STYLE_REFERENCED posts.
5. Execute the pure creative pipeline (Part 4.6) for PURE_CREATIVE posts.
6. For DIRECT_USE posts (asset score > 0.9, no modification needed): just resize + overlay.
7. Generate 2-3 variants per post (where applicable).
8. Run quality reviewer on each variant.
9. Auto-regenerate once if quality score is below threshold (3.0/5.0).
10. Apply text overlay (brand fonts, colors) per the creative brief.
11. Apply logo watermark per brand config.
12. Generate platform-specific crops/resizes.
13. Log the exact prompt used for each generation to `shared/prompt-logs/`.
14. Update status-tracker.json: post status → PENDING_REVIEW.
15. Track API costs in cost-log.json.

**For single-post generation/regeneration:**
Accept a specific post ID. Only process that post. Preserve all other posts' assets.
If regenerating after revision feedback, incorporate the feedback into the prompt.

**Sub-agent delegation (in Cowork):**
For batch processing, spawn sub-agents:
- Image Compositor agent: handles ANCHOR_COMPOSE and ENHANCE_EXTEND posts
- Creative Generator agent: handles STYLE_REFERENCED and PURE_CREATIVE posts
- These run in parallel. Both respect the shared API rate limit queue.

**Scripts called:**
- `generate_image.py` — Gemini API image generation
- `compose_image.py` — background removal, compositing, shadow, edge blending
- `edit_image.py` — Gemini API image editing
- `resize_image.py` — multi-platform resize/crop
- `compose_text_overlay.py` — text + logo overlay
- `verify_brand_colors.py` — brand color percentage check

## 5.6 render-carousels

```yaml
---
name: render-carousels
description: >
  Render multi-slide carousels using HTML/CSS templates and Playwright.
  Takes carousel post data, selects the appropriate template, populates
  with content and brand assets, renders each slide to PNG, and assembles
  into PDF for LinkedIn document upload.
  Trigger when: processing carousel posts in the pipeline, or
  "render carousel", "create slides", "build carousel for post X".
---
```

**Responsibilities:**
1. Identify carousel type from post data (comparison, case_study, tips, playbook, recap, data, generic).
2. Select the appropriate HTML template from `assets/carousel-templates/` or brand-specific overrides.
3. For each slide:
   a. Populate template variables (title, body text, data points, statistics)
   b. Apply brand colors, fonts (via CSS variables)
   c. If the slide needs a background image: run asset matching for that slide specifically, then compose or generate
   d. If the slide has data visualization: render charts/graphs in the HTML
4. Render each slide to PNG using Playwright (headless Chromium screenshot).
5. Assemble all slide PNGs into a PDF (for LinkedIn document upload format).
6. Generate a carousel preview (thumbnail of first slide + slide count indicator).

**Template structure (HTML/CSS):**
Each template is a single HTML file with CSS variables for brand customization:
```html
<!-- Template variables replaced at render time -->
<style>
  :root {
    --brand-primary: {{brand_primary}};
    --brand-secondary: {{brand_secondary}};
    --brand-accent: {{brand_accent}};
    --brand-bg-light: {{brand_bg_light}};
    --brand-bg-dark: {{brand_bg_dark}};
    --brand-text: {{brand_text}};
    --font-heading: '{{font_heading}}';
    --font-body: '{{font_body}}';
  }
</style>
```

**Slide dimensions:** 1080×1080 (Instagram/LinkedIn standard). Can be configured per brand.

**Scripts called:**
- `render_carousel.py` — Playwright rendering
- `compose_image.py` — if carousel slides need asset compositing
- `generate_image.py` — if carousel slides need AI background imagery

**Canva MCP upgrade path:**
If the Canva connector is active and `settings.carousel.fallback_renderer` is set to `canva_mcp`, route carousel generation through Canva's API instead of HTML templates. This produces higher-quality designs using Canva's design engine and the brand's Canva brand kit.

## 5.7 adapt-copy

```yaml
---
name: adapt-copy
description: >
  Adapt post copy for each target platform's requirements.
  Handles character limits, hashtag optimization, CTA format,
  link handling, language adaptation, and platform-specific best practices.
  Trigger when: processing copy in the pipeline, or "adapt copy",
  "optimize text", "adjust for platform", "fix hashtags".
---
```

**Responsibilities:**
1. For each post × each platform:
   a. Check character limit. If copy exceeds:
      - Smart truncation: cut at the last complete sentence that fits
      - For LinkedIn: truncation at ~140 chars for the "see more" fold
      - For X: strict 280 char limit, may need complete rewrite
   b. Optimize hashtags:
      - LinkedIn: 3-5 hashtags max, brand hashtag always included
      - Instagram: 8-10 hashtags, can be more, in comment or caption
      - X: 2-3 hashtags max (count toward char limit)
      - Facebook: 1-3 hashtags
   c. Adjust CTA format:
      - Instagram: no clickable links → "Link in bio" or remove URL
      - LinkedIn: link in first comment (algorithm preference)
      - X: shortened URL
   d. Add mandatory hashtags from brand config
   e. Add campaign hashtags if the post is in an active campaign
   f. For bilingual brands: generate the secondary language version
2. Run compliance check on adapted copy (see compliance-checker agent).
3. Save adapted copy to `production/copy/post-{id}-{platform}-copy.txt`.

**Scripts called:**
- `adapt_copy.py` — copy adaptation logic
- `compliance_check.py` — compliance scanning

## 5.8 generate-video

```yaml
---
name: generate-video
description: >
  Generate AI video clips, animate brand photos into video, or produce
  video production materials (scripts, storyboards, shot lists).
  Supports Veo 3.1 (same Gemini API key), Veo 3.1 Fast, and Kling 2.6.
  Trigger when: "generate video for post X", "create reel", "animate this image",
  "make a short", "video generation", or when explicitly requested.
  This module is OPT-IN — it generates scripts/storyboards automatically
  but only generates actual video on explicit command.
---
```

**Responsibilities:**
1. For every video post in the calendar: ALWAYS generate script, storyboard, shot list, and talking points. Save to `production/video/post-{id}-*.md`.
2. Generate video thumbnail (follows the image compositing pipeline).
3. On explicit user request, generate actual video:
   a. Route by duration:
      - Under 10 seconds → Veo 3.1 Fast (cheapest, fastest)
      - 10-30 seconds → Veo 3.1 (best quality for short-form)
      - 30 seconds - 3 minutes → Kling 2.6 (character consistency)
   b. Route by input type:
      - Text-to-video: prompt with brand style references
      - Image-to-video: feed brand photo(s) → animate into video clip
      - Video extension: extend a previously generated clip
   c. Aspect ratio:
      - YouTube Shorts / IG Reels / Stories → 9:16 portrait
      - LinkedIn / YouTube long-form → 16:9 landscape
   d. Before generating, show estimated cost and wait for confirmation.
4. Generate subtitle/caption file (SRT) if video has dialogue.
5. Log cost to cost tracker.

**Video prompt construction:**
Same 5-layer prompt as images, plus:
- LAYER 6: Motion direction (camera movement, subject action, pacing)
- LAYER 7: Audio direction (if Veo 3.1 — music mood, ambient sounds)
- LAYER 8: Duration and technical specs

**Scripts called:**
- `generate_video.py` — Veo 3.1 / Kling API calls

## 5.9 create-previews

```yaml
---
name: create-previews
description: >
  Render platform-specific post preview mockups showing how each post
  will appear when published. Uses HTML templates for each platform.
  Trigger when: "create previews", "show how it looks", "platform mockups",
  or automatically as part of the pipeline after creative production.
---
```

**Responsibilities:**
1. For each post × each platform, render a preview mockup showing:
   - Platform header (profile picture, name, headline from brand social profiles)
   - Post text (truncated per platform rules, with "...see more" where applicable)
   - The generated/composed image in the platform's image card format
   - Engagement bar (Like, Comment, Repost/Share icons)
   - Timestamp placeholder
2. Carousel posts: show carousel preview (first slide with navigation dots)
3. Story posts: show story frame with progress bar
4. Video posts: show video player frame with play button + duration indicator
5. Render previews to PNG using Playwright.

**Scripts called:**
- `render_preview.py` — Playwright rendering of preview templates

## 5.10 build-review-gallery

```yaml
---
name: build-review-gallery
description: >
  Build the interactive HTML review gallery that the social media manager
  uses to review, select variants, approve/reject posts.
  Trigger when: "build gallery", "show review", "open gallery",
  or automatically as part of the pipeline after previews are generated.
  Also triggered by /socialforge:review command.
---
```

**Responsibilities:**
1. Generate a single HTML file with embedded CSS/JS.
2. For each post, display:
   - Post metadata (date, title, bucket, tier, series)
   - Image variants side by side with selection radio buttons
   - Copy options A/B with selection + inline edit capability
   - Platform previews (clickable thumbnails → full-size)
   - Brand asset used (with "swap" button)
   - Creative mode indicator
   - Production notes, dependency flags
   - Status indicator
   - Action buttons: Approve / Revise / Reject
   - Notes field (internal notes)
   - Client review flag toggle
3. Filtering controls:
   - By week (Week 1-5)
   - By platform
   - By content bucket
   - By tier (Hero/Hub/Hygiene)
   - By status (pending/approved/revision/rejected)
   - By creative mode
4. Summary dashboard at top:
   - Total posts, approved, pending, revisions, rejected
   - Progress bar
   - Asset coverage breakdown
5. The gallery writes user selections/actions back to status-tracker.json.
6. Export options: "Generate Client Review Package" (filtered gallery), "Generate Word Document"

**Scripts called:**
- `build_gallery.py` — gallery generation

## 5.11 manage-reviews

```yaml
---
name: manage-reviews
description: >
  Manage the approval and revision workflow. Handle status transitions,
  revision requests, client review package generation, approval reminders.
  Trigger when: "approve post", "reject post", "request revision",
  "send to client", "check approvals", "approval status",
  or when approval-related commands are invoked.
---
```

**Responsibilities:**
1. Status transitions: move posts through the state machine (Part 3.7).
2. Revision handling: when a revision is requested, record the feedback, set status to REVISION_REQUESTED, and trigger compose-creative for only the specific post.
3. Client review package: generate a filtered gallery containing only posts flagged for client review. Generate a PDF or Word doc summary.
4. Approval reminders: check all brands for posts with status PENDING_CLIENT or PENDING_CEO past their reminder threshold. Send notifications via Slack/email.
5. Auto-publish logic: for HUB posts past the auto-publish threshold (per approval-chain.json), transition to FINAL with note "Auto-published with internal approval only."
6. Block logic: HERO posts past threshold → escalate, never auto-publish.
7. Bulk operations: "approve all Hygiene posts" → transition all HYGIENE-tier posts from PENDING_REVIEW to APPROVED_INTERNAL.

**Scripts called:**
- `status_manager.py` — status tracker read/write

## 5.12 assemble-document

```yaml
---
name: assemble-document
description: >
  Assemble the final Word document — the Social Media Monthly Calendar.
  Contains cover page, executive summary, content strategy, calendar grid,
  per-post details with images/previews, and appendices.
  Trigger when: "build document", "create the calendar doc", "assemble word doc",
  or as part of finalization.
---
```

**Responsibilities:**
1. Create a comprehensive Word document using docx-js with this structure:
   - Cover Page: Month, brand name/logo, document title
   - Table of Contents
   - Executive Summary: monthly theme, KPIs, targets, budget
   - Content Strategy: bucket breakdown, posting frequency, platform mix
   - Monthly Calendar Grid: visual 30-day overview
   - Weekly Sections: for each week:
     - Weekly overview
     - Per-post details: image (embedded), copy (both options with selected highlighted), platform, bucket, tier, creative mode used, production notes
   - Appendix A: Full Image Gallery
   - Appendix B: Content Bucket Definitions
   - Appendix C: Brand Guidelines Quick Reference
   - Appendix D: Publishing Schedule
   - Appendix E: Production Checklist (human action items)
2. Embed images at appropriate sizes (not full resolution — compressed for doc size).
3. Apply brand colors to document styling (headers, accent colors).
4. Generate as `output/{brand}/{month}/FINAL/00-Calendar-Document/`.

**Scripts called:**
- `assemble_docx.js` — docx-js document creation

## 5.13 finalize-month

```yaml
---
name: finalize-month
description: >
  Final assembly of all approved posts into the delivery folder structure.
  Organizes assets per week, per post, per platform. Generates the
  publishing schedule and production checklist. Uploads to Google Drive
  if connected. Notifies team via Slack.
  Trigger when: "finalize", "complete the calendar", "deliver",
  or when /socialforge:finalize is invoked.
---
```

**Responsibilities:**
1. Verify: all posts that should be finalized ARE finalized (or have approved exceptions).
2. For each finalized post:
   a. Copy the selected image variant to the FINAL folder (platform-specific)
   b. Copy adapted copy to the FINAL folder
   c. Copy preview mockup to the FINAL folder
   d. For carousels: copy PDF + individual slide PNGs
   e. For video posts: copy script, storyboard, thumbnail
3. Organize into the FINAL folder structure (Part 2.3).
4. Generate publishing-schedule.json with optimal posting times per platform per post.
5. Generate production-checklist.md listing all items that need human work (video production, photography, pending approvals).
6. Assemble the Word document (calls assemble-document skill).
7. Build the final gallery (filtered to show only selected variants).
8. If Google Drive connector is active: upload FINAL folder to the brand's Drive location.
9. If Slack connector is active: notify the team channel.
10. If Notion connector is active: update post statuses in Notion.
11. Log final statistics: total posts, API costs, production time, asset usage.
12. Write-protect FINAL folder (via status tracker — all posts set to FINAL state, protected by hooks).

## 5.14 full-pipeline

```yaml
---
name: full-pipeline
description: >
  End-to-end orchestration of the complete SocialForge pipeline.
  Runs all phases in sequence with proper dependency management,
  human gates, and error recovery.
  Trigger when: "run the full pipeline", "generate everything",
  "process this calendar", or when /socialforge:generate-all is invoked.
  Can run for a single brand or all brands (--all-brands flag).
---
```

**Responsibilities:**
1. Verify prerequisites: active brand loaded, calendar uploaded/synced, API keys available.
2. Execute phases in order:
   - Phase 0: Parse calendar (calls parse-calendar)
   - GATE: User confirms parsed summary
   - Phase 1: Asset matching (calls match-assets)
   - GATE: User confirms/overrides asset assignments
   - Phase 2: Creative production (calls compose-creative, render-carousels, generate-video [scripts only])
   - Phase 3: Copy adaptation (calls adapt-copy)
   - Phase 4: Preview generation (calls create-previews)
   - Phase 5: Build review gallery (calls build-review-gallery)
   - GATE: Human review required (async — pipeline pauses here)
   - Phase 6: Approval management (calls manage-reviews — ongoing/async)
   - Phase 7: Finalization (calls finalize-month — after all approvals received)
3. For `--all-brands`: queue all brands, process with parallel sub-agents for local work, shared API queue for image generation. Show progress dashboard for all brands.
4. Error recovery: if any phase fails, save state and allow resume with `/socialforge:resume-generation`. Don't lose completed work.
5. Progress reporting: show real-time progress with phase indicators, post counts, estimated time remaining.

---

# PART 6: COMMAND SPECIFICATIONS

Each command is a .md file in the `commands/` directory. Commands are invoked via `/socialforge:{command-name}` in Claude Code or Cowork.

## 6.1 new-month.md

```markdown
---
description: Start a new month's calendar production for a brand.
---

# /socialforge:new-month

Start a new month's social media calendar production.

Arguments:
  --brand "Brand Name" (optional — uses active brand if not specified)
  --from-drive (optional — search Google Drive for the calendar)
  --from-notion (optional — read calendar from Notion database)

## Workflow:
1. If --brand specified, switch to that brand (calls brand-manager skill)
2. If no brand active, prompt user to select or register a brand
3. Create the month directory: output/{brand}/{YYYY-MM}/
4. Accept calendar input:
   a. If --from-drive: search Drive for calendar file, show matches, user selects
   b. If --from-notion: search Notion for content calendar database, user confirms
   c. Otherwise: prompt user to upload DOCX/XLSX or paste structured text
5. Parse the calendar (calls parse-calendar skill)
6. Run asset matching (calls match-assets skill)
7. Display summary and wait for confirmation before proceeding
```

## 6.2 through 6.18 (Command Definitions)

Each command follows the same pattern — description, arguments, workflow steps, and which skills/scripts it invokes. Commands are thin wrappers that orchestrate skill invocations.

**generate-all.md:** Runs full-pipeline skill. Accepts `--all-brands` flag.

**generate-post.md:** `--id {post_id}`. Routes to compose-creative for a single post. If the post hasn't been asset-matched yet, runs match-assets first for that post only.

**edit-post.md:** `--id {post_id} --what "description of changes"`. Parses the change description. Routes to the appropriate action: regenerate image, regenerate background only, change copy, swap asset, re-render carousel slide.

**edit-image.md:** `--post {id} --variant {a/b/c} --instruction "edit instructions"`. Sends the existing generated image to Gemini edit API with the instructions. Creates a new variant. Preserves originals.

**swap-asset.md:** `--post {id} --new-asset "path/to/asset"`. Indexes the new asset (if not already in library), re-runs the compositing pipeline for this post with the new asset. Same creative mode, new core image.

**review.md:** Builds and opens the review gallery. If the gallery already exists and is current, just opens it. Otherwise rebuilds.

**revision.md:** `--post {id} --feedback "revision feedback" [--slides 4,7,9 for carousels]`. Records the feedback, updates status, triggers regeneration of specific elements.

**client-review.md:** `--hero-only | --hero-and-hub | --all`. Generates the client review package (filtered gallery + optional Word doc). Can specify which tiers to include.

**check-approvals.md:** `--all-brands | --brand "name"`. Scans all pending approvals, sends reminders where thresholds are exceeded. Shows approval status dashboard.

**finalize.md:** Runs finalize-month skill. Checks that all required approvals are in place. Warns if some posts are still pending.

**switch-brand.md:** `--brand "name"`. Saves current state, loads new brand context.

**reactive-post.md:** `--date YYYY-MM-DD --topic "topic description" [--tier HYGIENE] [--platforms "linkedin,x"]`. Creates a new post entry in the calendar data, runs asset matching, generation, and adds to the review gallery.

**sync-calendar.md:** `--from-drive | --from-notion`. Re-reads the calendar from the source, detects changes, shows diff, asks user whether to regenerate changed posts.

**status.md:** `--all-brands | --brand "name"`. Shows production status dashboard — posts by status, pipeline phase, approval progress, cost report.

**cost-report.md:** Shows API costs per brand per month — image generation, vision analysis, video generation, editing. Total spend.

**preview-batch.md:** `--count {N}`. Generates N sample posts before committing to the full batch. Picks representative posts (one from each tier/content type).

---

# PART 7: AGENT SPECIFICATIONS

Agents are sub-agents that can be spawned in Cowork for parallel processing.

## 7.1 image-compositor.md

```markdown
# Image Compositor Agent

You are a specialized sub-agent for compositing brand assets into creative scenes.

## Your Job:
Process a batch of posts assigned ANCHOR_COMPOSE or ENHANCE_EXTEND creative mode.
For each post:
1. Load the brand asset from the asset index
2. Follow the compositing pipeline (ANCHOR_COMPOSE) or enhancement pipeline (ENHANCE_EXTEND)
3. Generate 2-3 variants
4. Save variants to the production/images/ directory
5. Update the status tracker for each post

## Rules:
- NEVER modify the core brand asset (product photo, headshot, etc.)
- For ANCHOR_COMPOSE: the asset must remain pixel-perfect in the final composition
- For ENHANCE_EXTEND: the core subject must remain recognizable and undistorted
- Always log the prompt used to shared/prompt-logs/
- Respect the API rate limit (2-second delay between generation calls)
- If generation fails after 3 retries, mark the post as GENERATION_FAILED and continue with the next

## Scripts You Use:
- generate_image.py
- compose_image.py
- edit_image.py
- resize_image.py
- compose_text_overlay.py
- verify_brand_colors.py
```

## 7.2 carousel-builder.md

```markdown
# Carousel Builder Agent

You are a specialized sub-agent for rendering carousel posts.

## Your Job:
Process all posts with content_type = "carousel".
For each:
1. Identify the carousel type and select the HTML template
2. Populate template with content from calendar data
3. For slides needing imagery: coordinate with the image compositor or generate backgrounds
4. Render each slide to PNG using render_carousel.py
5. Assemble into PDF
6. Save to production/carousels/post-{id}/

## Rules:
- If a brand has custom carousel templates, use those instead of defaults
- Apply brand colors via CSS variables — never hardcode colors
- Each slide must be exactly 1080x1080px (or brand-configured size)
- Text must be legible: minimum 24px font size for body, 36px for headlines
- Maximum 30% of slide area should be text
- Carousel PDF page order must match slide order
```

## 7.3 copy-adapter.md

```markdown
# Copy Adapter Agent

You are a specialized sub-agent for adapting post copy across platforms.

## Your Job:
For each post × each platform:
1. Apply character limit (smart truncation at sentence boundary)
2. Optimize hashtag count per platform
3. Adjust CTA format per platform
4. Add brand hashtags and campaign hashtags
5. Run compliance check
6. Save to production/copy/post-{id}-{platform}-copy.txt

## Rules:
- Never add content that wasn't in the original copy — only adapt/truncate
- For X/Twitter: if copy exceeds 280 chars, REWRITE as a shorter version (don't just truncate)
- For Instagram: replace URLs with "Link in bio 👆" or remove
- For LinkedIn founder posts: maintain first-person voice
- For LinkedIn company posts: maintain third-person/brand voice
- Always preserve the core message even when shortening
- Flag any compliance violations immediately
```

## 7.4 quality-reviewer.md

```markdown
# Quality Reviewer Agent

You are a brand consistency reviewer.

## Your Job:
After images are generated/composed, evaluate each against brand standards.

## Review Criteria:
1. BRAND_COLOR (score 1-5): Brand colors present in 20%+ of image area
   Use verify_brand_colors.py for objective measurement
2. MOOD_ALIGNMENT (score 1-5): Does the image mood match the brief?
3. PLATFORM_FIT (score 1-5): Correct aspect ratio? Works on mobile?
4. TEXT_FREE (score 1-5): No phantom text/characters from AI generation?
5. NON_STOCK (score 1-5): Doesn't look like generic stock photography?
6. BRIEF_ALIGNMENT (score 1-5): Matches the calendar's visual direction?
7. ASSET_INTEGRITY (score 1-5, for ANCHOR/ENHANCE modes only):
   Is the core brand asset undistorted, properly placed, naturally composited?

## Scoring:
- Average score < 3.0: REJECT — flag for regeneration
- Average score 3.0-3.5: WARNING — suggest regeneration, user decides
- Average score > 3.5: PASS

## Output:
JSON report per post per variant with all scores, flags, and recommendations.
```

## 7.5 compliance-checker.md

```markdown
# Compliance Checker Agent

You are an industry compliance reviewer for social media content.

## Your Job:
After copy or images are generated, check against the brand's compliance rules.

## Checks:
1. BANNED_PHRASES: Scan copy for any phrase in compliance-rules.json banned_phrases[]
   - Critical matches: BLOCK — copy must be revised before proceeding
   - Warning matches: FLAG — mark for human review

2. DATA_CLAIMS: Detect statistics, percentages, dollar amounts, "X+ clients" patterns
   - Flag each for source verification
   - Note the specific claim and suggest where a source could be cited

3. REQUIRED_DISCLAIMERS: Check if the post context triggers any disclaimer requirement
   - If product mention + pharma brand → add medical disclaimer
   - If financial claim + BFSI brand → add regulatory disclaimer

4. PLATFORM_RULES: Check platform-specific compliance
   - Instagram: no clickable links in caption
   - LinkedIn: character limit respected
   - Industry-specific: no before/after for pharma on certain platforms

5. IMAGE_COMPLIANCE: For generated images, check against image_compliance rules
   - Feed the image to Gemini Vision with the compliance rules as context
   - Ask: "Does this image violate any of these rules? [rules]"

## Output:
Compliance report per post with:
- Pass/Fail status
- List of violations with severity and remediation suggestions
- List of flags for human review
```

---

# PART 8: HOOKS CONFIGURATION

## 8.1 Complete hooks.json

```json
{
  "hooks": {
    
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python ${CLAUDE_PLUGIN_ROOT}/scripts/status_manager.py --action load-session",
            "timeout": 10
          }
        ]
      }
    ],
    
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python ${CLAUDE_PLUGIN_ROOT}/scripts/validate_brand_config.py --check-active",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python ${CLAUDE_PLUGIN_ROOT}/scripts/guard_output_path.py",
            "timeout": 5
          }
        ]
      }
    ],
    
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python ${CLAUDE_PLUGIN_ROOT}/scripts/cost_tracker.py --log-if-api-call",
            "timeout": 5
          },
          {
            "type": "command",
            "command": "python ${CLAUDE_PLUGIN_ROOT}/scripts/compliance_check.py --check-last-output-if-copy",
            "timeout": 10
          }
        ]
      }
    ],
    
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python ${CLAUDE_PLUGIN_ROOT}/scripts/status_manager.py --action update-from-subagent",
            "timeout": 5
          }
        ]
      }
    ],
    
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python ${CLAUDE_PLUGIN_ROOT}/scripts/notify_team.py",
            "timeout": 10
          }
        ]
      }
    ],
    
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Before finishing this SocialForge task, verify: (1) Has the status tracker been updated for all posts processed? (2) Are there posts stuck in GENERATING that should be PENDING_REVIEW? (3) If this was a finalize operation, is the production checklist generated? (4) If API calls were made, is the cost log updated? Report any issues. If everything is consistent, allow stop.",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

## 8.2 Hook Script Logic

**validate_brand_config.py (PreToolUse):**
- Check if `SOCIALFORGE_ACTIVE_BRAND` is set in the session
- If not set, exit code 2 (BLOCK) with message: "No active brand loaded. Run /socialforge:switch-brand first."
- If set, validate the brand-config.json exists and has required fields
- Exit code 0 (allow) if valid

**guard_output_path.py (PreToolUse for Write/Edit):**
- Read the file path being written to from stdin (JSON input)
- Check: is this path within `output/{active_brand_slug}/`?
- If writing to a different brand's folder → exit 2 (BLOCK): "Cannot write to {other_brand}'s folder. Active brand is {active_brand}."
- If writing to `FINAL/` directory: check status-tracker.json — are all posts in that write batch marked as FINAL?
- If any post is not FINAL → exit 2 (BLOCK): "Cannot write to FINAL directory. {N} posts are not yet finalized."
- Exit 0 if all checks pass

**cost_tracker.py (PostToolUse):**
- Read the tool input from stdin
- Check if the command was an API call (contains 'generativelanguage.googleapis.com' or known API endpoints)
- If yes: log the call to `output/{brand}/{month}/cost-log.json` with timestamp, model used, estimated cost
- Always exit 0 (non-blocking)

**compliance_check.py (PostToolUse):**
- Read the tool output from stdin
- Check if the output contains generated copy text
- If yes: load the active brand's compliance-rules.json
- Scan for banned phrases, check character limits, flag data claims
- If critical violation found: exit 0 but write a systemMessage alerting Claude to the violation
- Non-blocking (PostToolUse can't block, but can provide feedback)

**status_manager.py (SubagentStop):**
- Read the subagent completion info from stdin
- Update the appropriate phase status in status-tracker.json
- Update any post statuses that changed during the subagent's work
- Exit 0

**notify_team.py (Notification):**
- Read the notification content from stdin
- If Slack MCP connector is available: format and send to configured channel
- If not available: log to a local notification-log.json
- Exit 0

---

# PART 9: MCP CONNECTORS

## 9.1 .mcp.json

```json
{
  "mcpServers": {
    "google-drive": {
      "url": "https://drive.mcp.claude.com/mcp",
      "description": "Read calendar files from Drive. Connect to brand asset libraries in Drive. Upload final assets to Drive.",
      "required": false,
      "fallback": "Manual file upload/download"
    },
    "slack": {
      "url": "https://mcp.slack.com/mcp",
      "description": "Phase completion notifications. Review-ready alerts. Approval reminders.",
      "required": false,
      "fallback": "Console/log notifications only"
    },
    "notion": {
      "url": "https://mcp.notion.com/mcp",
      "description": "Read calendars from Notion databases. Update post statuses in Notion.",
      "required": false,
      "fallback": "DOCX/XLSX calendar input only"
    },
    "canva": {
      "url": "https://mcp.canva.com/mcp",
      "description": "Generate carousels and designs using Canva's design engine.",
      "required": false,
      "fallback": "HTML template rendering via Playwright"
    },
    "gmail": {
      "url": "https://gmail.mcp.claude.com/mcp",
      "description": "Draft and send client review packages via email.",
      "required": false,
      "fallback": "Manual email with attachments"
    },
    "google-calendar": {
      "url": "https://gcal.mcp.claude.com/mcp",
      "description": "Create publishing schedule events. Production deadline reminders.",
      "required": false,
      "fallback": "Schedule exported as JSON/XLSX only"
    }
  }
}
```

**All connectors are optional.** The plugin works fully without any connectors — file I/O is local, notifications go to console/log, calendars are uploaded manually. Connectors enhance the workflow but aren't required.

---

# PART 10: SETTINGS

## 10.1 settings.json

```json
{
  "workspace_root": "~/socialforge-workspace",
  
  "image_generation": {
    "provider": "gemini",
    "model": "gemini-3.1-flash-image-preview",
    "fallback_model": "gemini-2.5-flash-image",
    "variants_per_post": 2,
    "max_variants": 3,
    "default_resolution": "1024",
    "rate_limit_delay_ms": 2000,
    "retry_attempts": 3,
    "retry_delay_ms": 5000,
    "fallback_to_prompt_export": true,
    "max_reference_images": 8,
    "thinking_mode": "high"
  },
  
  "image_editing": {
    "provider": "gemini",
    "model": "gemini-3.1-flash-image-preview"
  },
  
  "asset_indexing": {
    "vision_model": "gemini-3-flash-preview",
    "batch_delay_ms": 1000,
    "min_image_dimension": 800,
    "auto_index_on_sync": true
  },
  
  "compositing": {
    "background_removal_tool": "rembg",
    "shadow_enabled": true,
    "shadow_opacity": 0.3,
    "edge_feather_px": 2,
    "color_matching": true
  },
  
  "carousel": {
    "renderer": "playwright",
    "fallback_renderer": "canva_mcp",
    "default_slide_size": {"width": 1080, "height": 1080},
    "export_as_pdf": true,
    "min_font_size_body": 24,
    "min_font_size_heading": 36,
    "max_text_area_percentage": 30
  },
  
  "video": {
    "enabled": false,
    "always_generate_scripts": true,
    "provider": "gemini",
    "model_short": "veo-3.1-fast-generate-preview",
    "model_standard": "veo-3.1-generate-preview",
    "model_long": "kling-2.6",
    "short_threshold_seconds": 10,
    "standard_threshold_seconds": 30,
    "require_cost_confirmation": true
  },
  
  "copy_adaptation": {
    "maintain_source_hashtags": true,
    "auto_add_brand_hashtag": true,
    "truncation_method": "smart_sentence",
    "x_rewrite_if_over_limit": true
  },
  
  "review": {
    "default_review_mode": "gallery",
    "auto_flag_hero_for_client": true,
    "auto_flag_hub_for_client": true,
    "auto_flag_hygiene_for_client": false,
    "require_internal_before_client": true,
    "gallery_embed_images_base64": false,
    "gallery_use_file_references": true
  },
  
  "quality": {
    "min_quality_score": 3.0,
    "auto_regenerate_below": 3.0,
    "max_auto_regenerations": 1,
    "brand_color_min_percentage": 20,
    "verify_text_free": true,
    "verify_asset_integrity": true
  },
  
  "output": {
    "generate_word_document": true,
    "generate_html_gallery": true,
    "generate_production_checklist": true,
    "generate_publishing_schedule": true,
    "compress_images_for_document": true,
    "document_image_max_width_px": 800
  },
  
  "connectors": {
    "slack_notifications": true,
    "slack_channel_override": null,
    "google_drive_upload": true,
    "google_drive_asset_sync": true,
    "notion_status_sync": false,
    "canva_carousel_generation": false,
    "gmail_client_reviews": false,
    "gcal_publishing_events": false
  },
  
  "parallel_processing": {
    "max_concurrent_brands": 5,
    "api_queue_strategy": "round_robin",
    "local_work_parallel": true
  }
}
```

---

# PART 11: SCRIPT LOGIC

Detailed pseudocode and logic for each script. These are Python unless otherwise noted.

## 11.1 index_assets.py

```
PURPOSE: Scan a folder of brand images and create/update the asset index using Gemini Vision.

INPUTS:
  --brand-dir: path to the brand's directory
  --source-path: path to the image folder (local, Drive, etc.)
  --new-only: boolean — skip already-indexed files
  --batch-size: number of images to process per run (default: all)

LOGIC:
  1. Walk the source folder tree recursively
  2. Collect all image files (jpg, jpeg, png, webp) with paths and metadata
  3. If --new-only: load existing asset-index.json, filter out already-indexed files
  4. For each new image:
     a. Open with Pillow, get dimensions, file size, format
     b. Check minimum dimension (skip if < 800px)
     c. Convert to base64 for API call
     d. Call Gemini Vision with the structured analysis prompt
     e. Parse the JSON response
     f. Construct the asset entry per schema
     g. Auto-detect platform crop feasibility:
        For each platform's required aspect ratio:
          Calculate if the image can be cropped to that ratio
          without losing more than 20% of the image area
     h. Detect if background is removable (from AI analysis)
     i. Rate limit: wait batch_delay_ms between API calls
  5. Merge new entries into existing index (or create new)
  6. Sort assets by folder path
  7. Write asset-index.json
  8. Return summary: total indexed, new, skipped, flagged

ERROR HANDLING:
  - API call fails: retry 3 times with exponential backoff
  - Image file corrupt: skip, log error
  - API rate limit: pause for 60 seconds, resume
  - Partial completion: save progress after every 10 images
```

## 11.2 match_assets.py

```
PURPOSE: For each post in calendar-data.json, find the best matching brand assets.

INPUTS:
  --calendar: path to calendar-data.json
  --asset-index: path to asset-index.json
  --month: YYYY-MM (for usage tracking)
  --post-id: optional — match a single post only

LOGIC:
  1. Load calendar data and asset index
  2. Load current month's usage data from status-tracker.json (if exists)
  3. For each post (or single post if --post-id specified):
     a. KEYWORD EXTRACTION:
        - Split content_bucket into words, lowercase, remove stop words
        - Split visual.direction_a into descriptive words
        - Split copy.option_a into topic keywords
        - Extract explicit asset references (filenames, descriptions)
        - Combine into keyword set
     b. CANDIDATE SCORING:
        For each asset in the index:
          Calculate TAG_OVERLAP score (0-0.30)
          Calculate SUITABILITY_MATCH score (0-0.25)
          Calculate CONTENT_BUCKET_MATCH score (0-0.20)
          Calculate CROP_FEASIBILITY score (0-0.15)
          Apply FRESHNESS_PENALTY (0 to -0.20)
          FINAL_SCORE = sum of all components
     c. SORT candidates by score descending
     d. DETERMINE recommendation:
        If explicit asset reference in brief → use that asset, mode = ANCHOR_COMPOSE
        Elif top score > 0.8 → ANCHOR_COMPOSE or ENHANCE_EXTEND
        Elif top score > 0.5 → ENHANCE_EXTEND or STYLE_REFERENCED
        Elif top score > 0.3 → STYLE_REFERENCED
        Else → PURE_CREATIVE
     e. SELECT style references:
        Load all is_style_reference assets
        Filter by relevance to post mood
        Select 2-5 references
     f. DETECT gaps:
        If the post SHOULD have a brand asset (founder post, product post, office post)
        but no good match found → flag as gap
  4. Save results to asset-matches.json
  5. Generate coverage report:
     - % direct use, % enhance, % style-ref, % pure AI
     - List of gaps with suggestions
  6. Generate asset request list (what to photograph/source)

OUTPUT: asset-matches.json per schema
```

## 11.3 generate_image.py

```
PURPOSE: Call Gemini API to generate an image from a prompt + optional reference images.

INPUTS:
  --prompt: text prompt (the full constructed prompt)
  --references: comma-separated paths to reference images
  --output: output file path
  --model: model ID (default from settings)
  --resolution: '1024' | '2048' | '4096'
  --aspect-ratio: '1:1' | '16:9' | '9:16' | '3:2' | '4:3'

LOGIC:
  1. Load API key from environment variable GEMINI_API_KEY
  2. Initialize Gemini client
  3. Build contents array:
     a. For each reference image: read file, convert to base64, add as image content part
     b. Add the text prompt as the final content part
  4. Set config: response_modalities = ['TEXT', 'IMAGE']
  5. Call client.models.generate_content()
  6. Parse response:
     a. Find the image part (inline_data with mime_type image/*)
     b. Decode base64 to bytes
     c. Open with Pillow
     d. Verify dimensions match expected aspect ratio
     e. Save to output path
  7. Return: success boolean, file path, generation metadata

ERROR HANDLING:
  - 429 (rate limit): wait rate_limit_delay_ms, retry up to retry_attempts
  - 400 (invalid prompt): log error, return failure with message
  - 500 (server error): retry with exponential backoff
  - Content policy block: log, return failure with "content policy violation" message
  - No image in response: retry once, if still no image → return failure
  - Timeout: retry once with increased timeout

COST LOGGING:
  After successful generation, log to cost-log.json:
  {
    "timestamp": ISO 8601,
    "model": model ID,
    "resolution": resolution used,
    "reference_count": number of reference images,
    "estimated_cost_usd": calculated based on model + resolution pricing
  }
```

## 11.4 compose_image.py

```
PURPOSE: Composite a brand asset onto an AI-generated background.

INPUTS:
  --asset: path to the brand asset (product photo, headshot, etc.)
  --background: path to the AI-generated background scene
  --output: output file path
  --position: 'center' | 'left_third' | 'right_third' | 'custom:X,Y'
  --asset-scale: percentage of canvas width the asset should occupy (default: 40)
  --shadow: boolean (default from settings)
  --edge-feather: pixels of feathering (default from settings)
  --color-match: boolean — adjust asset color temperature to match background

LOGIC:
  1. Open background image with Pillow
  2. Open brand asset with Pillow
  3. BACKGROUND REMOVAL (if asset doesn't have transparency):
     a. Use rembg library to remove background
     b. Verify removal quality:
        - Check that the subject is fully preserved
        - Check that edges are clean
        - If removal has artifacts → log warning, proceed with best effort
     c. Result: RGBA image with transparent background
  4. SCALING:
     a. Calculate target asset width = background.width × (asset_scale / 100)
     b. Scale asset maintaining aspect ratio
  5. POSITIONING:
     a. Calculate X,Y based on position parameter
     b. Center: (bg_w - asset_w) / 2, (bg_h - asset_h) / 2
     c. Left third: bg_w * 0.33 - asset_w / 2, centered vertically
     d. Right third: bg_w * 0.67 - asset_w / 2, centered vertically
     e. Custom: use provided X,Y
  6. COLOR MATCHING (if enabled):
     a. Sample average color temperature of background
     b. Sample average color temperature of asset
     c. If difference exceeds threshold: apply subtle color correction to asset edges
  7. SHADOW (if enabled):
     a. Create a shadow layer from the asset's alpha channel
     b. Offset by 3-5 pixels down and right (matching typical light direction)
     c. Apply Gaussian blur
     d. Set opacity per settings
     e. Paste shadow onto background before asset
  8. COMPOSITING:
     a. Paste the asset onto the background at calculated position
     b. Use the alpha channel for smooth blending
  9. EDGE FEATHERING (if edge_feather_px > 0):
     a. Apply subtle feathering at the asset edges
     b. This prevents hard "cut-out" edges
  10. QUALITY VERIFICATION:
      a. Verify asset dimensions in the composition match expected size
      b. Verify asset is not distorted (compare aspect ratios)
      c. Verify asset is fully within canvas bounds
  11. Save composed image

OUTPUT: Composed image file + composition metadata JSON
```

## 11.5 edit_image.py

```
PURPOSE: Edit an existing image using Gemini's image editing capabilities.

INPUTS:
  --image: path to the image to edit
  --instruction: natural language edit instruction
  --output: output file path
  --references: optional reference images for style guidance
  --model: model ID

LOGIC:
  1. Load the image, convert to base64
  2. Build contents array:
     a. Image as first content part
     b. Optional reference images
     c. Edit instruction as text: "Edit this image: {instruction}. Preserve the core subject. Do not add text."
  3. Call Gemini API
  4. Save the edited image
  5. VERIFICATION:
     a. Compare edited image to original using structural similarity (SSIM)
     b. If SSIM < 0.3 (too different — core subject may be lost): warn
     c. Check that the edited image has same dimensions as original

OUTPUT: Edited image file
```

## 11.6 resize_image.py

```
PURPOSE: Resize/crop a master image to platform-specific dimensions.

INPUTS:
  --input: path to master image
  --platforms: comma-separated platform keys
  --output-dir: directory to save resized images
  --preserve-subject: boolean — use smart crop that keeps the subject centered

LOGIC:
  1. Open master image with Pillow
  2. For each platform:
     a. Look up required dimensions from platform-specs
     b. Calculate if the master aspect ratio matches the target
     c. If aspect ratio matches: simple resize
     d. If aspect ratio differs:
        - If preserve-subject: detect the subject area (center of interest) 
          and crop to include it
        - Otherwise: center crop
     e. Resize to exact target dimensions
     f. Verify: no important content cut off (if subject detection available)
     g. Save as: {input_stem}-{platform_key}-{WxH}.png

OUTPUT: Per-platform image files
```

## 11.7 compose_text_overlay.py

```
PURPOSE: Add text and logo overlays to an image.

INPUTS:
  --image: path to the base image
  --text-elements: JSON array of text elements to add
  --logo: path to logo file (optional)
  --logo-config: JSON object with position, opacity, size (from brand config)
  --output: output file path
  --brand-config: path to brand-config.json (for fonts and colors)

TEXT ELEMENT SCHEMA:
  {
    "text": "string",
    "position": {"x": number, "y": number} | "top-center" | "bottom-center" | etc.,
    "font_role": "heading" | "subheading" | "body" | "accent",
    "size": number (px),
    "color": "hex" | null (uses brand text color),
    "max_width": number | null (for text wrapping),
    "alignment": "left" | "center" | "right",
    "background": {"color": "hex", "opacity": number, "padding": number} | null
  }

LOGIC:
  1. Open base image with Pillow
  2. Create an overlay layer (RGBA, same dimensions)
  3. For each text element:
     a. Load the brand font (from brand config fonts + bundled font files)
     b. Calculate text dimensions
     c. If max_width specified and text exceeds: wrap text
     d. If background specified: draw semi-transparent rectangle behind text
     e. Draw text with anti-aliasing
     f. Position according to the position parameter
  4. If logo specified:
     a. Open logo file
     b. Scale to logo_config.size_percentage of image width
     c. Apply opacity
     d. Position per logo_config.position
     e. Paste onto overlay layer
  5. Composite overlay onto base image
  6. Save

OUTPUT: Image with text/logo overlays
```

## 11.8 render_carousel.py

```
PURPOSE: Render an HTML carousel template to PNG slides using Playwright.

INPUTS:
  --template: path to HTML template file
  --data: JSON object with template variables (brand colors, slide content)
  --output-dir: directory for individual slide PNGs
  --slide-count: number of slides to render
  --width: pixel width (default 1080)
  --height: pixel height (default 1080)
  --assemble-pdf: boolean — also create a combined PDF

LOGIC:
  1. Read the HTML template
  2. Replace template variables ({{brand_primary}}, {{slide_title}}, etc.)
  3. For each slide:
     a. Set the template's active slide (via data attribute or JS)
     b. Launch Playwright headless browser
     c. Load the HTML
     d. Wait for rendering to complete (fonts loaded, images loaded)
     e. Screenshot at exact dimensions
     f. Save as slide-{NN}.png
  4. If assemble-pdf:
     a. Use Pillow or reportlab to combine all PNGs into a single PDF
     b. Save as carousel.pdf

DEPENDENCIES: playwright (pip install playwright && playwright install chromium)

OUTPUT: Individual slide PNGs + assembled PDF
```

## 11.9 render_preview.py

```
PURPOSE: Render platform-specific post preview mockups.

INPUTS:
  --template: path to platform preview HTML template
  --data: JSON object with: profile info, post text, image path, engagement counts
  --output: output PNG file path
  --platform: platform key (determines which template to use)
  --width: preview width (default: 600)

LOGIC:
  1. Select the correct preview template based on platform
  2. Populate template variables:
     - Profile avatar, name, headline (from brand social profiles)
     - Post text (truncated per platform rules, with "...see more" if applicable)
     - Post image (embedded or referenced)
     - Engagement bar icons
     - Timestamp ("2h" placeholder)
  3. Render with Playwright, screenshot
  4. Save as preview PNG

OUTPUT: Preview mockup PNG
```

## 11.10 build_gallery.py

```
PURPOSE: Generate the interactive HTML review gallery.

INPUTS:
  --calendar: path to calendar-data.json
  --status: path to status-tracker.json
  --production-dir: path to production/ directory (images, carousels, previews, copy)
  --output: output HTML file path
  --template: path to gallery template directory
  --embed-images: boolean — base64 embed images vs file references

LOGIC:
  1. Load calendar data, status tracker, and all production assets
  2. Read the gallery HTML/CSS/JS template
  3. For each post:
     a. Collect all variants (image files)
     b. Collect copy options
     c. Collect platform previews
     d. Collect asset matching data (which brand asset was used, creative mode)
     e. Collect status and approval info
     f. Build the HTML card for this post
  4. Build the filtering controls (week, platform, bucket, tier, status, mode)
  5. Build the summary dashboard (counts, progress bar)
  6. If embed-images: convert all images to base64 data URIs
  7. Assemble the complete HTML file
  8. Save

The gallery's JavaScript handles:
  - Filtering
  - Variant selection (radio buttons → writes to status-tracker.json via callback)
  - Copy selection
  - Approve/Revise/Reject buttons
  - Notes field
  - Client review flag toggle
  - Print-friendly CSS mode

NOTE: In Claude Code/Cowork context, the gallery opens in the default browser.
User interactions in the browser need to be communicated back to Claude
(e.g., "I approved posts 1-15, Post 8 needs revision with this feedback").
The gallery generates a summary of actions that can be copy-pasted back.
Alternatively, the user communicates approvals via commands.

OUTPUT: Single HTML file (self-contained with embedded CSS/JS)
```

## 11.11 assemble_docx.js

```
PURPOSE: Create the final Word document using docx-js.

NODE.JS SCRIPT (not Python — docx-js is the recommended document creation library)

INPUTS: (via command line arguments or JSON config file)
  --calendar: path to calendar-data.json
  --status: path to status-tracker.json
  --production-dir: path to production/ directory
  --brand-config: path to brand-config.json
  --output: output .docx file path

LOGIC:
  1. Load all input data
  2. Create Document with:
     - A4 size, 1-inch margins
     - Brand-styled heading formats (brand primary color for headings)
     - Table of contents
  3. BUILD SECTIONS:
     a. Cover Page: brand name, month, "Social Media Content Calendar", logo
     b. Executive Summary: 1-page overview with key stats table
     c. Content Strategy: bucket breakdown table, platform mix chart description
     d. Monthly Calendar Grid: table with dates × platforms showing post counts
     e. For each week:
        - Week header with date range and campaign phase
        - For each post in the week:
          * Post header (number, date, title, bucket, tier)
          * Embedded image (selected variant, compressed for doc)
          * Copy text (selected option, with platform adaptations noted)
          * Creative mode used + brand asset referenced
          * Production notes and dependencies
          * Platform previews (small thumbnails)
     f. Appendix A: Image Gallery (all final images, larger format)
     g. Appendix B: Content Bucket Definitions
     h. Appendix C: Brand Guidelines Quick Reference
     i. Appendix D: Publishing Schedule table
     j. Appendix E: Production Checklist (human action items)
  4. Validate the document
  5. Save to output path

DEPENDENCIES: npm install docx

NOTE: Images are read from the production directory and embedded as ImageRun.
Compress images to max 800px width before embedding to keep file size reasonable.

OUTPUT: .docx file
```

## 11.12-11.17 (Remaining Scripts)

**adapt_copy.py:** Platform-specific copy adaptation. Inputs: original copy, platform specs, brand config, compliance rules. Logic: check char limits, truncate at sentence boundary (or rewrite for X), optimize hashtags, add brand/campaign hashtags, replace links per platform rules, add disclaimers if triggered.

**compliance_check.py:** Compliance scanning. Inputs: text content, brand's compliance-rules.json. Logic: regex scan for banned phrases, detect data claims (patterns: `\d+%`, `\$[\d,]+`, `\d+\+\s*(clients|projects|users)`), check required disclaimers, platform-specific rules. Output: JSON report with pass/fail + violations.

**verify_brand_colors.py:** Pixel-level brand color verification. Inputs: image path, brand-config.json, threshold percentage. Logic: load image, sample all pixels, for each pixel calculate Euclidean distance to brand colors (tolerance: 60), count matching pixels, calculate percentage. Output: JSON with percentage, pass/fail, dominant colors.

**cost_tracker.py:** API cost logging. Inputs: API call metadata. Logic: determine cost based on model + resolution pricing table, append to cost-log.json. Output: updated cost log.

**status_manager.py:** Status tracker operations. Actions: load-session, update-post-status, update-from-subagent, get-summary, check-approvals, transition (validates state machine rules). All writes are atomic (write to temp file, rename).

**generate_video.py:** Video generation via Veo 3.1 or Kling API. Similar structure to generate_image.py but uses the video generation endpoint. Polls for completion (video gen is async — takes 30-120 seconds). Supports text-to-video, image-to-video (feeds brand photos as first/last frame), and video extension.

---

# PART 12: REFERENCE DOCUMENTS

## 12.1 platform-specs.md

### Image Dimensions

| Platform | Post Type | Dimensions (px) | Aspect Ratio | Notes |
|---|---|---|---|---|
| LinkedIn | Single image | 1200 × 627 | 1.91:1 | Also works 1200×1200 (1:1) |
| LinkedIn | Carousel/Document | 1080 × 1080 per slide | 1:1 | Upload as PDF, max 300 pages |
| LinkedIn | Story | 1080 × 1920 | 9:16 | |
| LinkedIn | Profile banner | 1584 × 396 | 4:1 | |
| Instagram | Feed (square) | 1080 × 1080 | 1:1 | Most common |
| Instagram | Feed (portrait) | 1080 × 1350 | 4:5 | Higher engagement |
| Instagram | Feed (landscape) | 1080 × 566 | 1.91:1 | Least common |
| Instagram | Story / Reel | 1080 × 1920 | 9:16 | |
| Instagram | Carousel | 1080 × 1080 per slide | 1:1 | Max 20 slides |
| X (Twitter) | Single image | 1200 × 675 | 16:9 | Also 1200×1200 (1:1) |
| X (Twitter) | Profile banner | 1500 × 500 | 3:1 | |
| Facebook | Post image | 1200 × 630 | 1.91:1 | |
| Facebook | Story | 1080 × 1920 | 9:16 | |
| Facebook | Cover | 820 × 312 | ~2.63:1 | |
| YouTube | Thumbnail | 1280 × 720 | 16:9 | |
| YouTube | Shorts | 1080 × 1920 | 9:16 | |
| YouTube | Banner | 2560 × 1440 | 16:9 | Safe area: 1546×423 center |
| TikTok | Video | 1080 × 1920 | 9:16 | |
| Pinterest | Pin | 1000 × 1500 | 2:3 | |

### Text Limits

| Platform | Max Characters | Truncation Point | Hashtag Best Practice | Link Behavior |
|---|---|---|---|---|
| LinkedIn | 3,000 | ~140 chars before "see more" fold | 3-5 | Clickable. Algorithm deprioritizes posts with links in body; better in first comment |
| Instagram | 2,200 | ~125 chars before "...more" | 5-10 (max 30) | NOT clickable in captions. Use "Link in bio" |
| X (Twitter) | 280 | Hard limit | 2-3 (count toward char limit) | Clickable. URLs auto-shortened (~23 chars) |
| Facebook | 63,206 | ~400 chars before "See More" | 1-3 | Clickable |
| YouTube (title) | 100 | ~60-70 visible in search | 0 in title | N/A |
| YouTube (description) | 5,000 | ~120 visible before expand | 3-5 | Clickable |
| TikTok | 4,000 | ~150 visible | 3-5 | Limited, one link in bio |
| Pinterest | 500 | ~100 visible on pin | 0-2 | Clickable (pin links to URL) |

### Carousel Specifics

| Platform | Max Slides | Slide Format | Upload Format | Notes |
|---|---|---|---|---|
| LinkedIn | 300 | 1080×1080 or custom | PDF document upload | Each PDF page = one slide |
| Instagram | 20 | 1080×1080 (1:1) or 1080×1350 (4:5) | Individual images | All slides same ratio |
| Facebook | 10 | 1080×1080 | Individual images | |
| X | 4 | 1200×675 | Individual images | Not true carousel, image grid |

### Video Specifics

| Platform | Max Duration | Recommended | Aspect Ratio | Max File Size |
|---|---|---|---|---|
| LinkedIn | 10 min | 30-90 sec | 16:9 or 1:1 | 5 GB |
| Instagram Feed | 60 min | 15-60 sec | 1:1 or 4:5 | 4 GB |
| Instagram Reel | 90 sec | 15-30 sec | 9:16 | 4 GB |
| Instagram Story | 60 sec | 15 sec | 9:16 | 4 GB |
| YouTube | 12 hr | 7-15 min | 16:9 | 256 GB |
| YouTube Short | 3 min | 15-60 sec | 9:16 | N/A |
| X | 2:20 | 15-45 sec | 16:9 | 512 MB |
| Facebook | 240 min | 15-60 sec | 16:9 or 1:1 | 10 GB |
| TikTok | 10 min | 15-60 sec | 9:16 | N/A |

---

# PART 13: TEMPLATE SPECIFICATIONS

## 13.1 Carousel Templates

Each template is an HTML file with CSS variables for brand customization. Templates support:

- Brand color injection via CSS custom properties
- Font injection via @font-face or Google Fonts reference
- Per-slide content injection via data attributes or template tags
- Responsive scaling (renders at exact pixel dimensions via Playwright)

**Templates to build:**

1. **generic-8slide.html**: Title slide + 6 content slides + CTA slide. Each content slide: heading + body text + optional icon/image area.

2. **comparison-10slide.html**: Title slide + 8 comparison slides (3-column layout: option A | option B | featured option) + CTA slide. Color-coded columns (red/amber/green).

3. **case-study-10slide.html**: Title + Challenge + Why Others Said No + Our Approach + Architecture + Timeline + Results + Client Quote + Campaign Connection + CTA.

4. **tips-5slide.html**: Title + 3-4 numbered tips (each with icon, heading, 1-2 sentences) + CTA.

5. **playbook-8slide.html**: Title + Problem + Framework (2×2 matrix or decision tree) + 4 quadrant deep-dives + Checklist + CTA.

6. **recap-6slide.html**: Title + 4 stat cards (big number + label + context) + Preview/teaser slide.

7. **data-infographic-6slide.html**: Title + 4 data visualization slides (bar chart, pie chart, timeline, comparison) + CTA. Charts rendered via CSS (no external charting library needed for simple visualizations).

8. **quote-card-single.html**: Single slide — testimonial quote with attribution, branded background, quotation mark decoration. Used for standalone quote card posts.

## 13.2 Preview Templates

HTML templates that mimic each platform's post appearance:

**linkedin-post.html**: LinkedIn's card layout — round avatar, name, headline, follower count, timestamp, post text (with "...see more" at 140 chars), image in 1.91:1 card, engagement bar (Like, Comment, Repost, Send with icons).

**instagram-feed.html**: Instagram's feed layout — header (avatar, handle, ...), image (1:1 square frame), engagement bar (heart, comment, share, save), caption area below.

**twitter-post.html**: X's tweet layout — avatar + name + handle, tweet text, image card below, engagement bar (reply, retweet, like, share).

**facebook-post.html**: Facebook's post card — profile link, post text, image card, engagement reactions + comment + share.

**youtube-thumbnail.html**: YouTube video card — thumbnail image with play button overlay, title, channel name, view count, timestamp.

---

# PART 14: PIPELINE ORCHESTRATION

## 14.1 Deterministic Workflows

These workflows always follow the same steps in the same order:

**Full Pipeline (single brand):**
```
parse-calendar → [GATE: confirm] → match-assets → [GATE: confirm] → 
compose-creative + render-carousels + adapt-copy (parallel) → 
create-previews → build-review-gallery → [GATE: human review] → 
manage-reviews (async) → [GATE: all approvals received] → 
finalize-month
```

**Single Post Generation:**
```
If post not in calendar-data → prompt user for post details → add to calendar
Load post data → match-assets (single post) → compose-creative (single post) → 
adapt-copy (single post) → create-previews (single post) → 
update review gallery → update status tracker
```

**Revision:**
```
Load revision feedback → update status to REVISION_REQUESTED → 
determine what changed (image? copy? slide? all?) → 
regenerate ONLY the changed elements → 
update the post's assets in production/ → preserve old versions → 
update review gallery → update status tracker → PENDING_REVIEW
```

**Brand Switch:**
```
Save current brand's session state → 
clear active brand context → 
load new brand's config + asset index + active month status → 
set SOCIALFORGE_ACTIVE_BRAND → 
confirm to user
```

**Asset Reindex:**
```
Connect to asset source → scan for files → 
diff against existing index → 
analyze only new/changed files → 
merge into index → 
save → report summary
```

## 14.2 Non-Deterministic Scenarios

These require judgment and may branch differently each time:

**Asset matching ambiguity:** Multiple assets score similarly (within 0.05). Present all to user. User decides.

**Creative mode edge cases:** Brief says "use our office photo" but the photo is too low-resolution for the target platform. Options: upscale (AI enhancement), use a different office photo, or generate AI-based on the photo as reference.

**Calendar format variations:** Different clients structure their calendars differently — some in DOCX with tables, some in XLSX with columns, some in Notion databases, some as plain text in email. The parser needs to handle all formats and ask for clarification when structure is ambiguous.

**Prompt engineering iteration:** If the first generation doesn't match the brief, the system should adjust the prompt — add more specific color instructions, change the style keywords, add negative instructions ("NOT corporate stock photo"). This is Claude's judgment call, not a deterministic algorithm.

**Compliance edge cases:** A phrase might be flagged by regex but be acceptable in context (e.g., "cure" in "curious about AI" shouldn't trigger pharma compliance). The compliance checker flags it, but Claude or the human decides if it's a real violation.

**Client feedback interpretation:** "Make it pop more" → needs to be translated into specific generation parameters (increase contrast? more vibrant colors? larger text? different composition?). Claude interprets and executes.

**Cross-platform adaptation tension:** A post that works great on LinkedIn (long-form thought leadership) might not adapt well to X (280 chars). For some posts, the X version needs to be fundamentally different, not just truncated. Claude decides whether to truncate or rewrite.

---

# PART 15: NON-DETERMINISTIC SCENARIOS & EDGE CASES

## 15.1 Complete Edge Case Catalog

| # | Scenario | What Happens | Resolution |
|---|---|---|---|
| 1 | Client changes brand colors mid-month | Some assets already generated with old colors | User updates brand-config.json. `/socialforge:regenerate --all-pending` regenerates unfinalised posts. FINAL posts are protected unless explicitly unlocked. |
| 2 | Trending topic — inject reactive post | Need a new post not in original calendar | `/socialforge:reactive-post` creates a new entry, runs through asset match → generate → review → approve. |
| 3 | Client rejects specific carousel slides | Slides 4, 7, 9 need changes, others are fine | `/socialforge:revision --post 12 --slides 4,7,9 --feedback "..."`. Only specified slides re-rendered. Carousel PDF reassembled. |
| 4 | Founder photo unavailable, calendar requires it | Calendar brief specifies founder portrait | Asset gap detected at Phase 1. Two options: use the brief's alternate visual direction (if provided), or generate AI image with available style references. User decides. |
| 5 | API rate limit hit mid-batch | Gemini returns 429 at image 45 of 94 | Hook detects error. Pauses generation for 60s. Retries. After 3 consecutive failures: stops, saves state, notifies user. `/socialforge:resume-generation` continues from where it stopped. |
| 6 | Same asset used too many times | Founder has 4 photos, 16 posts need founder imagery | Usage tracking penalizes reuse. After 2 uses in the same month, penalty kicks in. After same-week reuse, heavy penalty. System recommends alternatives and flags to user. |
| 7 | Post goes to 4 platforms with different specs | One source, four different dimension/format/char requirements | Generate master image at highest resolution. Platform-specific crops + resizes. Copy adapted separately per platform. Previews generated per platform. |
| 8 | Calendar updated in Drive after production started | Content strategist changes 5 posts | `/socialforge:sync-calendar --from-drive` detects changes, shows diff, asks user which posts to regenerate. Only changed posts are re-processed. |
| 9 | No brand assets at all (new brand) | Empty asset library | All posts default to PURE_CREATIVE or STYLE_REFERENCED (if even a few images exist). Asset gap analysis recommends what to photograph. |
| 10 | Generated image has phantom text | AI generated "SALE" text in the background | Quality reviewer's TEXT_FREE check catches this. Auto-regeneration triggered with strengthened "NO TEXT" instruction. |
| 11 | Background removal fails | rembg can't cleanly separate subject from background | Flag for manual masking. Provide the raw image + a mask estimate. Designer refines the mask. Or switch to ENHANCE_EXTEND mode instead. |
| 12 | Brand has strict compliance (pharma) | Generated copy includes banned phrase "cure" | Compliance checker blocks (critical severity). Claude suggests alternative phrasing. Post stays in REVISION_REQUESTED until compliant copy is provided. |
| 13 | User wants to use a specific image not in the library | "Use this photo I just received for Post #23" | User uploads via `/socialforge:swap-asset`. System indexes the new image, adds to library, re-runs compositing for that post. |
| 14 | Multiple social media managers working on same brand | Priya works on posts 1-25, Ritu works on 26-47 | Status tracker handles concurrent access. Each post has its own status. No cross-post interference. Last-write-wins for the same post (with conflict warning). |
| 15 | Campaign postponed — shift all campaign posts by one week | "The Sweet Middle" launch moves from Week 2 to Week 3 | Manual adjustment in calendar data. User edits dates in calendar-data.json (or re-uploads updated calendar). Publishing schedule auto-adjusts. |
| 16 | Client wants bilingual posts (English + Hindi) | Brand serves Indian market | Platform language map in brand config determines which platform gets which language. Copy adapter generates the secondary language version. |
| 17 | Carousel template doesn't exist for the brief's type | Calendar calls for a "timeline" carousel, no template matches | Options: closest match template, Canva MCP generation, flag for designer, or create a new template for reuse. |
| 18 | Generated video costs more than expected | Veo 3.1 pricing varies with resolution | Cost estimation shown BEFORE generation. User confirms. If over budget: suggest lower resolution or Veo 3.1 Fast. |
| 19 | Google Drive connection lost mid-upload | Upload fails at file 35 of 47 | Retry logic with exponential backoff. If Drive stays unavailable: save locally, notify user, retry upload later. |
| 20 | User wants ALL posts AI-generated, no brand assets | Deliberate choice for conceptual/abstract feed | User sets creative mode to PURE_CREATIVE or STYLE_REFERENCED for all posts at the asset matching confirmation stage. System respects the override. |

---

# PART 16: API INTEGRATION DETAILS

## 16.1 Gemini API (Primary)

**Single API key covers:** Image generation (Nano Banana 2), image editing, vision analysis (asset indexing), and video generation (Veo 3.1).

**Setup:**
```bash
# Environment variable
export GEMINI_API_KEY="AIzaSy-your-key-here"

# Or .env file
echo 'GEMINI_API_KEY=AIzaSy-your-key-here' > .env
```

**Models used:**
| Purpose | Model ID | Pricing |
|---|---|---|
| Image generation | gemini-3.1-flash-image-preview | $0.039-0.151/image |
| Image editing | gemini-3.1-flash-image-preview | Same |
| Vision analysis | gemini-3-flash-preview | ~$0.001/request |
| Video (fast) | veo-3.1-fast-generate-preview | ~$0.06/sec |
| Video (standard) | veo-3.1-generate-preview | ~$0.40/sec |
| Text (copy, analysis) | gemini-3-flash-preview | ~$0.001/request |

**Free tier:** ~500 image gen requests/day, sufficient for most agency volumes.

**Key SDK pattern:**
```python
from google import genai
client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

# Image generation with references
response = client.models.generate_content(
    model='gemini-3.1-flash-image-preview',
    contents=[
        # Reference images (up to 14)
        {'inline_data': {'mime_type': 'image/jpeg', 'data': ref_b64}},
        # Text prompt
        'Generate a professional social media image...'
    ],
    config={'response_modalities': ['TEXT', 'IMAGE']}
)

# Video generation
operation = client.models.generate_videos(
    model='veo-3.1-generate-preview',
    prompt='...',
    config={'resolution': '1080p', 'aspect_ratio': '9:16'}
)
# Poll until done
while not operation.done:
    time.sleep(10)
    operation = client.operations.get_videos_operation(operation)
```

## 16.2 Kling API (Optional, for longer video)

**Separate API key required.** Enterprise-level pricing (~$4,200 for 30,000 units).

Only used when video generation is explicitly enabled AND the video duration exceeds 30 seconds. For most social media content, Veo 3.1 is sufficient.

**Integration:** REST API with polling pattern (similar to Veo). Script `generate_video.py` handles both Veo and Kling based on duration routing.

## 16.3 Other potential API integrations (future)

| API | Purpose | When to Add |
|---|---|---|
| Sora 2 (OpenAI) | Alternative video generation | If Veo 3.1 quality is insufficient |
| Flux (Replicate) | Alternative image generation | If Gemini has content policy issues with certain prompts |
| ElevenLabs | AI voiceover for video scripts | When video production module matures |
| Buffer / Hootsuite / Later API | Auto-publishing to platforms | Future module — currently out of scope |

---

# PART 17: CROSS-PLATFORM DEPLOYMENT

## 17.1 Claude Code (Terminal) + Antigravity

The primary development and execution environment.

**Installation:**
```bash
# Clone or install the plugin
claude plugin install --local ./socialforge
# Or from marketplace
claude plugin marketplace add [publisher]/socialforge
claude plugin install socialforge@[marketplace]
```

**For Antigravity specifically:**
Add to the project's CLAUDE.md:
```markdown
## SocialForge Plugin
This project uses the SocialForge social media calendar automation plugin.
Read the complete specification in `socialforge/SPEC.md` before building or modifying.
Skills are in `socialforge/skills/`.
Scripts are in `socialforge/scripts/`.
Templates are in `socialforge/assets/`.
```

**All features work:** Skills, commands, agents, hooks, scripts. Gallery opens in browser.

## 17.2 Claude Cowork (Desktop)

Install via Cowork's Customize → Browse Plugins → Add custom plugin.

**Additional features vs Claude Code:**
- Sub-agents for parallel processing
- Scheduled tasks (`/schedule`)
- Dispatch (trigger from mobile)
- Connectors UI (easier setup than manual .mcp.json)

## 17.3 Claude.ai (Web) — Fallback

Paste skill instructions as context. Run scripts in sandbox. Download outputs.
No hooks, no sub-agents, no persistence, no scheduling.
Useful for: one-off generation, testing, or when desktop isn't available.

---

# PART 18: IMPLEMENTATION ORDER & DEPENDENCY GRAPH

```
LAYER 0 (Foundation — no dependencies):
├── Plugin scaffold (manifest, directory structure)
├── settings.json
├── brand-config schema + validation
├── platform-specs.md reference
└── status-tracker module (status_manager.py)

LAYER 1 (Core — depends on Layer 0):
├── brand-manager skill (register, switch, validate)
├── parse-calendar skill (DOCX + XLSX parsing)
└── calendar-data schema

LAYER 2 (Asset Intelligence — depends on Layer 1):
├── index-assets skill + index_assets.py (Gemini Vision)
├── match-assets skill + match_assets.py (matching algorithm)
├── asset-index schema
└── Style reference system

LAYER 3 (Creative Production — depends on Layer 2):
├── generate_image.py (Gemini API caller)
├── compose_image.py (background removal + compositing)
├── edit_image.py (Gemini editing)
├── resize_image.py (multi-platform crops)
├── compose_text_overlay.py (text + logo)
├── verify_brand_colors.py (quality check)
└── compose-creative skill (orchestrates all above)

LAYER 4 (Carousel — depends on Layer 3):
├── 8 HTML carousel templates
├── render_carousel.py (Playwright rendering)
└── render-carousels skill

LAYER 5 (Copy & Compliance — depends on Layer 1):
├── adapt_copy.py
├── compliance_check.py
├── compliance-rules schema
├── adapt-copy skill
└── compliance-checker agent

LAYER 6 (Presentation — depends on Layers 3-5):
├── Preview HTML templates (6 platforms)
├── render_preview.py
├── create-previews skill
├── Gallery HTML template
├── build_gallery.py
└── build-review-gallery skill

LAYER 7 (Review & Approval — depends on Layer 6):
├── manage-reviews skill
├── approval-chain schema
└── Approval reminder logic

LAYER 8 (Output — depends on Layer 7):
├── assemble_docx.js (Word document)
├── assemble-document skill
├── finalize-month skill
└── Folder structure organization

LAYER 9 (Orchestration — depends on all above):
├── full-pipeline skill
├── All 18 commands
├── hooks.json
├── .mcp.json connector definitions
└── All 5 agent definitions

LAYER 10 (Extensions — independent, add later):
├── generate-video skill + generate_video.py
├── Canva MCP carousel integration
├── Scheduled automation setup
├── Multi-brand parallel processing
└── Marketplace packaging
```

**Build sequence:** Layer 0 → 1 → 2 → 3 → (4 + 5 in parallel) → 6 → 7 → 8 → 9 → 10

Minimum viable plugin: Layers 0-3 + 5 + 6 (basic gallery) = single brand, static images, copy adaptation, simple gallery. ~2-3 weeks.

Full plugin: All layers. ~10-13 weeks.

---

*END OF SPECIFICATION*

*This document contains everything needed for Claude Code (inside Antigravity or standalone) to build the complete SocialForge plugin: every schema, every skill body, every script's logic, every hook configuration, every template specification, every edge case, every workflow, and the complete implementation dependency graph. Feed this to Claude Code as the project specification.*
