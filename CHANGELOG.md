# Changelog

All notable changes to SocialForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.4.0] - 2026-03-31

### Added — Feature Complete (All Scripts + Commands)

All 17 scripts and 18 commands now implemented. The plugin is feature-complete for its core architecture.

#### Scripts (5 new, 17 total — ALL COMPLETE)
- **index_assets.py** — Scan image libraries, Gemini Vision analysis per image, build asset-index.json. Refresh mode for incremental updates. Graceful fallback to metadata-only when API unavailable.
- **render_preview.py** — Platform mockup previews via Playwright. Renders HTML cards with profile, image, copy. Fallback when templates not yet built.
- **build_gallery.py** — Self-contained HTML review gallery with base64-embedded images, tier badges, status, copy previews, summary stats.
- **generate_video.py** — Video scripts and storyboards from calendar data. 5 video types (hero, case study, reel, story, talking head). JSON output with scene breakdowns.
- **assemble_docx.js** — Node.js calendar document builder. Groups posts by week, includes summary/schedule. JSON structure output (DOCX generation via docx package when available).

#### Commands (12 new, 18 total — ALL COMPLETE)
- **edit-post** — Edit copy, visual direction, or metadata for a generated post
- **edit-image** — AI edit instruction to modify generated images
- **swap-asset** — Replace matched brand asset with alternative
- **revision** — Apply revision feedback and regenerate affected elements
- **client-review** — Send approved posts to client via Slack/email
- **check-approvals** — Check pending approvals and send overdue reminders
- **finalize** — Package all approved content for delivery
- **reactive-post** — Create unplanned trending/reactive posts outside calendar
- **sync-calendar** — Re-sync calendar from source (Notion/Drive/file)
- **cost-report** — API cost breakdown per operation and per post
- **preview-batch** — Batch generate platform mockup previews
- **index-assets** — Index or re-index brand photo library

### Summary

| Component | v0.3.0 | v0.4.0 | Spec Target |
|-----------|--------|--------|-------------|
| Skills | 14 | 14 | 14 ✅ |
| Scripts | 12 | 17 | 17 ✅ |
| Agents | 5 | 5 | 5 ✅ |
| Commands | 6 | 18 | 18 ✅ |
| Reference docs | 1 | 1 | 11 (remaining) |
| HTML templates | 0 | 0 | 19 (remaining) |

---

## [0.3.0] - 2026-03-31

### Added — Creative Pipeline Scripts + Audit Fixes

5 critical image production scripts enabling the full creative pipeline, plus 3 audit fixes.

#### Scripts (5 new, 12 total)
- **generate_image.py** — AI image generation via Gemini API (Nano Banana 2) with style reference support (up to 8 refs). Placeholder fallback when no AI provider available. All prompts logged to `shared/prompt-logs/`.
- **compose_image.py** — Three operations: `remove-bg` (rembg background removal), `composite` (layer foreground on background with position/scale control), `add-logo` (watermark overlay with opacity/position/size)
- **edit_image.py** — AI-powered image editing via Gemini API. Enhance, extend, modify periphery while preserving core subjects. Style reference support.
- **compose_text_overlay.py** — Brand-aware text overlays: reads brand-config.json for fonts/colors, configurable position (top/center/bottom), semi-transparent background strips
- **render_carousel.py** — Renders HTML carousel templates to PNG via Playwright. 8 template types, CSS variable injection for brand theming, brand-specific template overrides

#### Audit Fixes (3)
- **compose-creative skill** — Added explicit Prerequisites section documenting dependency on asset-matches.json (from match_assets.py)
- **full-pipeline skill** — Added Async Review Gate documentation: resume behavior, escalation rules, timeout handling
- **adapt_copy.py** — Fixed Facebook character limit: now uses optimal_limit (500) for truncation, with true max (63,206) as hard limit

### Summary

| Component | v0.2.0 | v0.3.0 |
|-----------|--------|--------|
| Scripts | 7 | 12 |
| Creative pipeline functional | No (missing 5 scripts) | Yes (all image scripts present) |

---

## [0.2.0] - 2026-03-31

### Added — Core Engine (Layers 3-6)

Creative production engine with all 14 skills, 7 core scripts, and platform reference documentation.

#### Skills (11 new, 14 total)
- **match-assets** — Multi-factor asset scoring (tags 30%, suitability 25%, bucket 20%, crop 15%, freshness 10%), creative mode assignment
- **compose-creative** — 4-mode creative engine (ANCHOR_COMPOSE, ENHANCE_EXTEND, STYLE_REFERENCED, PURE_CREATIVE) with 2-3 variant generation, quality review, user approval
- **adapt-copy** — Platform-specific copy adaptation (LinkedIn 3000 chars, Instagram 2200, X 280, Facebook 500, YouTube 5000) with mandatory compliance checking
- **render-carousels** — 8 HTML template types rendered via Playwright, brand-themed, PDF assembly
- **create-previews** — Platform mockup previews showing how posts look on each social platform
- **build-review-gallery** — Interactive HTML gallery with quality scores, filtering, bulk actions
- **manage-reviews** — Multi-tier approval workflow (internal → client → CEO) with `disable-model-invocation`
- **assemble-document** — DOCX calendar delivery document with weekly sections and appendices
- **finalize-month** — Final delivery folder packaging with `disable-model-invocation`
- **full-pipeline** — End-to-end 7-phase orchestration with quality gates
- **generate-video** — Video scripts, storyboards, thumbnails, optional AI video clips

#### Scripts (7)
- **status_manager.py** — Session init, month init, post status transitions, pipeline summary
- **cost_tracker.py** — API cost logging per post/operation with monthly cost reports
- **match_assets.py** — 5-factor scoring algorithm with creative mode recommendations
- **compliance_check.py** — Banned phrase detection, data claim flagging, platform rule enforcement
- **adapt_copy.py** — Platform-specific character limits, smart truncation, hashtag/CTA formatting
- **resize_image.py** — 14 platform dimension specs, cover/contain resize modes (Pillow)
- **verify_brand_colors.py** — Pixel sampling to verify brand palette in generated images

#### Reference Documents (1)
- **platform-specs.md** — Complete specs for 7 platforms: image dimensions, character limits, hashtag limits, video specs, supported formats

### Summary

| Component | v0.1.0 | v0.2.0 |
|-----------|--------|--------|
| Skills | 3 | 14 (all) |
| Scripts | 0 | 7 |
| Agents | 5 | 5 |
| Commands | 6 | 6 |
| Reference docs | 0 | 1 |
| Total files | 21 | 39+ |

---

## [0.1.0] - 2026-03-31

### Added — Foundation Release (Layers 0-2)

Plugin scaffold with brand management, calendar parsing, asset indexing infrastructure, and all quality patterns from ContentForge and Digital Marketing Pro baked in from day one.

#### Plugin Architecture
- `.claude-plugin/plugin.json` — Manifest with name, version, description, keywords
- `hooks/hooks.json` — 4 hooks: SessionStart (timeout-protected), PreToolUse (compliance), SubagentStart (brand injection), Stop (quality gate)
- `.mcp.json` — 9 HTTP connectors (Notion, Canva, Slack, Gmail, Google Calendar, Figma, fal.ai, Replicate, Asana)
- `settings.json` — Model inheritance config

#### Skills (3)
- **brand-manager** — 8-step brand setup with Quick Start (5 questions), progressive disclosure, pre-flight validation
- **parse-calendar** — Parse DOCX/XLSX/Notion/text calendars into structured calendar-data.json
- **index-assets** — AI-powered asset indexing with Gemini Vision, crop feasibility, style reference identification

#### Agents (5)
- **image-compositor** — 4 creative modes (ANCHOR_COMPOSE, ENHANCE_EXTEND, STYLE_REFERENCED, PURE_CREATIVE)
- **carousel-builder** — HTML/CSS template rendering via Playwright
- **copy-adapter** — Platform-specific copy with compliance checking
- **quality-reviewer** — 5-dimension scoring (Brand Consistency 30%, Visual Quality 25%, Copy Quality 20%, Platform Compliance 15%, Compliance 10%)
- **compliance-checker** — Banned phrases, disclaimers, image rules, data claims, platform restrictions

#### Commands (6)
- new-month, generate-all, generate-post, review, status, switch-brand

#### Quality Patterns (From ContentForge/DM Pro)
- All agent files <100 lines (well under 300-line best practice)
- All skills have: effort, argument-hint, user-invocable frontmatter
- Skill descriptions <130 chars (fits discovery budget)
- maxTurns on all 5 agents (10-25 turns)
- Timeout + fallback on all API/network operations
- Human-in-the-loop approval for generated images
- Pre-flight brand validation before workflows
- SessionStart with 30-second timeout wrapper
- Progressive disclosure (Quick Start first, detail later)
