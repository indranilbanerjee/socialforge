# SocialForge v1.3 — Complete User Guide

**From zero to delivered calendar.** This guide walks you through every step of using SocialForge to produce a month's worth of social media content for a brand.

---

## Prerequisites

Before you start, make sure you have:

- **Claude Code CLI** or **Claude Desktop with Code tab** (any plan)
- **API credentials configured via `/sf:setup`** (one-time setup):
  - **Google Cloud service account JSON file** -- for Vertex AI image generation
  - **WaveSpeed API key** -- for Kling v3.0 video generation
- **Python dependencies installed:**
  ```
  pip install google-genai wavespeed Pillow
  ```

Get both credentials from your admin. If you ARE the admin, see the [Admin Setup Guide](#19-admin-setup-guide) at the end of this document.

---

## Table of Contents

0. [Prerequisites](#prerequisites)
1. [What You Need](#1-what-you-need)
2. [Installation](#2-installation)
3. [Setting Up API Credentials (/sf:setup)](#3-setting-up-api-credentials-sfsetup)
4. [Your First Brand Setup](#4-your-first-brand-setup)
5. [Indexing Brand Assets](#5-indexing-brand-assets)
6. [Starting a New Month](#6-starting-a-new-month)
7. [Understanding the 4 Creative Modes](#7-understanding-the-4-creative-modes)
8. [Producing Content -- Images](#8-producing-content----images)
9. [Producing Content -- Video](#9-producing-content----video)
10. [Reviewing and Approving](#10-reviewing-and-approving)
11. [Finalizing and Delivering](#11-finalizing-and-delivering)
12. [Working with Multiple Brands](#12-working-with-multiple-brands)
13. [Where Your Data Lives](#13-where-your-data-lives)
14. [All 18 Commands](#14-all-18-commands)
15. [All 14 Skills](#15-all-14-skills)
16. [Connectors](#16-connectors)
17. [Troubleshooting](#17-troubleshooting)
18. [FAQ](#18-faq)
19. [Admin Setup Guide](#19-admin-setup-guide)

---

## 1. What You Need

**Required:**
- Claude Code or Claude Cowork (any plan)
- Brand photos (at least 5-10 images — products, people, office, events)
- A monthly content calendar (DOCX, XLSX, Notion database, or just text)

**For AI image generation (recommended):**
- Google Cloud Vertex AI credentials (configured via `/sf:setup`)
- fal.ai account -- connected via Connectors panel (HTTP, works in Cowork)
- Replicate account -- connected via Connectors panel (HTTP, works in Cowork)

**For AI video generation:**
- **WaveSpeed API key via `/sf:setup`** -- powers Kling v3.0 video generation

**Optional (enhances workflow):**
- Google Drive — store brand assets (connects automatically in Cowork via Settings > Integrations)
- Slack — approval notifications
- Notion — calendar databases
- Cloudinary — professional DAM

---

## Setting Up API Credentials

Run this once after installing the plugin:

```
/sf:setup
```

Step 1 — Image generation (Google Cloud Vertex AI):
- Your admin gives you a service account JSON file
- When prompted, provide the file path
- Models: Nano Banana 2 (gemini-2.5-flash-image), Nano Banana Pro (gemini-3-pro-image-preview)

Step 2 — Video generation (WaveSpeed / Kling v3.0):
- Your admin gives you a WaveSpeed API key
- When prompted, paste the key
- Models: Kling v3.0 Pro (image-to-video, text-to-video, 3-15 seconds)

Credentials are stored persistently. You never need to run /sf:setup again unless credentials change.

Check status anytime: `/sf:setup --status`

---


## 2. Installation

### Recommended: From Marketplace

```
/plugin marketplace add github:indranilbanerjee/neels-plugins
/plugin install socialforge@neels-plugins
```

### Alternative: Direct from GitHub

```
/plugin install github:indranilbanerjee/socialforge
```

### Verify Installation

After installing, you should see:

```
SocialForge v1.3 loaded

Quick Start:
  1. /sf:brand-setup   — Configure a brand (do this first, 5-10 min)
  2. /sf:index-assets  — Index brand photo library (Drive or local)
  3. /sf:new-month     — Start monthly calendar production

Already set up? /sf:status | /sf:switch-brand <name>

Connectors: 10 HTTP (Notion, Canva, Figma, Slack, Gmail, Calendar, fal.ai, Replicate, Asana, Cloudinary)
Storage: persistent via plugin data directory
```

---

## 3. Setting Up API Credentials (/sf:setup)

Before generating images or video, configure your API credentials. This is a one-time setup -- credentials persist across all sessions.

### Step-by-Step

Run the setup command:

```
/sf:setup
```

SocialForge walks you through two steps:

```
SocialForge Credential Setup
=============================

Step 1 of 2: Google Cloud (Vertex AI -- Image Generation)
  Provide the path to your Google Cloud service account JSON file.
  This enables Vertex AI image generation (Imagen 3, Gemini Vision).

  Path to JSON file: > /path/to/my-service-account.json

  Validating... OK
  Project: my-project-123
  Service account: socialforge@my-project-123.iam.gserviceaccount.com
  Vertex AI API: enabled

Step 2 of 2: WaveSpeed (Kling v3.0 -- Video Generation)
  Paste your WaveSpeed API key.
  This enables Kling v3.0 video generation for Reels, Shorts, and TikTok.

  API key: > wvs_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

  Validating... OK
  Account: team@agency.com
  Credits remaining: 847

Setup complete. Credentials saved to plugin data directory.
Both persist across sessions -- you won't need to do this again.
```

### Checking Credential Status

```
/sf:setup --status
```

```
SocialForge Credentials
  Vertex AI:  CONFIGURED (project: my-project-123)
  WaveSpeed:  CONFIGURED (847 credits remaining)
```

### Updating Credentials

Run `/sf:setup` again at any time to replace either credential. The new values overwrite the old ones immediately.

### Credential Management

All API credentials are managed through `/sf:setup`. Run it anytime to configure or update your Vertex AI service account or WaveSpeed API key.

---

## 4. Your First Brand Setup

Let's set up a real brand. Say you're an agency working with **GreenLeaf Organics**, a premium organic food brand.

### Quick Setup (3 minutes)

```
/sf:brand-setup GreenLeaf
```

SocialForge asks you 5 questions:

```
1. Brand name: GreenLeaf Organics
2. Industry: retail
3. Brand colors:
   Primary: #2D5016 (forest green)
   Secondary: #F4E9D1 (warm cream)
   Accent: #D4A853 (golden)
4. Active platforms: LinkedIn, Instagram, Facebook
5. Asset source: https://drive.google.com/drive/folders/1ABC...  (or local path)
```

**Done.** Your brand profile is created and persists across sessions.

### Adding More Detail Later

Anytime, run `/sf:brand-setup --update GreenLeaf` to add:

- **Visual style** — "warm natural light, rustic, earthy, farm-to-table aesthetic"
- **Image rules** — "Always include natural green tones", "Avoid plastic packaging in any visual"
- **Compliance** — Banned phrases: "100% organic" (requires certification), "all-natural" (FDA regulated)
- **Approval chain** — HERO posts need client approval, HYGIENE posts auto-approve internally
- **Social profiles** — LinkedIn: @GreenLeafOrganics, Instagram: @greenleaf.official
- **Brand hashtags** — Always: #GreenLeafOrganics #OrganicLiving
- **Languages** — Primary: English, Secondary: Spanish (bilingual posts for Instagram)

### What Gets Created

```
${CLAUDE_PLUGIN_DATA}/socialforge/brands/greenleaf-organics/
  brand-config.json       <- Colors, fonts, visual style, hashtags
  platform-config.json    <- LinkedIn, Instagram, Facebook settings
  approval-chain.json     <- HERO/HUB/HYGIENE review rules
  compliance-rules.json   <- Banned phrases, disclaimers
  asset-source.json       <- Google Drive URL
  style-references/       <- 2-8 photos representing brand DNA
```

---

## 5. Indexing Brand Assets

GreenLeaf has a Google Drive folder with 45 photos: products, farm scenes, team photos, packaging shots, recipe images.

```
/sf:index-assets GreenLeaf
```

**What happens:**

```
[1/4] Scanning asset source...
  Google Drive folder detected. Reading files via platform integration...
  Found: 45 images (32 .jpg, 10 .png, 3 .webp)

[2/4] Analyzing images with AI Vision...
  Each image analyzed by Gemini Vision for: subjects, mood, colors, setting,
  what posts it's suitable for, whether background is removable.

  Analyzed: 15/45 (33%) — ~2 min remaining
  Analyzed: 30/45 (67%) — ~1 min remaining
  Analyzed: 45/45 (100%)

[3/4] Building asset index...
  Tags generated: 287 unique tags across 45 assets
  Categories: products (12), farm/agriculture (8), team (6), recipes (7),
              packaging (5), lifestyle (4), events (3)

[4/4] Identifying style reference candidates...
  Top 6 candidates selected (warm lighting, earthy tones, natural settings)

Asset Index Complete: greenleaf-organics
  Total: 45 assets | Background-removable: 18 | Style references: 6
  Estimated cost: $0.14 (Gemini Vision)
```

**Now the system knows:**
- Photo #12 is "organic avocado product packaging on wooden table" — suitable for product launch posts
- Photo #23 is "farm team harvesting vegetables at sunrise" — suitable for team culture, sustainability posts
- Photo #37 is "founder portrait, professional, warm lighting" — suitable for leadership, about-us posts

### Google Drive as Asset Source

When you provide a Google Drive folder URL during brand setup, SocialForge uses the platform integration (Cowork) or local download (Claude Code) to read files. Your photos stay in Drive — nothing is duplicated. The asset index stores metadata only.

To use Drive in Cowork: Settings > Integrations > Google Drive > Connect. No API key needed.

### Updating Assets

When GreenLeaf adds new photos to their Drive folder:

```
/sf:index-assets GreenLeaf --refresh
```

Only analyzes new/changed images. Existing index preserved.

---

## 6. Starting a New Month

GreenLeaf's social media manager sends you the April 2026 calendar as a Word document (DOCX). It has 28 posts across LinkedIn, Instagram, and Facebook.

```
/sf:new-month GreenLeaf 2026-04
```

SocialForge asks for the calendar source:

```
Calendar source? (Upload DOCX, XLSX, paste Notion URL, or describe posts)
> [Upload: GreenLeaf-April-2026-Calendar.docx]
```

**Parsing:**

```
Calendar parsed: 28 posts for April 2026
  LinkedIn: 12 posts (4 carousels, 6 static, 2 video)
  Instagram: 10 posts (3 carousels, 4 reels, 3 static)
  Facebook: 6 posts (all static)

  Tier breakdown: 4 HERO | 14 HUB | 10 HYGIENE

Issues: 2
  - P14: Missing visual_brief (will ask during production)
  - P22: Weekend post — confirm intentional?
```

**Asset matching:**

```
Asset Matching Complete: 28 posts
  ANCHOR_COMPOSE: 8 posts (direct brand asset as centerpiece)
  ENHANCE_EXTEND: 5 posts (brand photo enhanced with AI)
  STYLE_REFERENCED: 9 posts (AI gen guided by brand photo DNA)
  PURE_CREATIVE: 4 posts (full AI, brand colors only)
  CAROUSEL_TEMPLATE: 2 posts (HTML template rendering)

  Asset gaps: 1 (P14: "New product launch" but no new product photos indexed)
```

You can override any match: "Use photo #12 for P14 instead" or "Make P22 STYLE_REFERENCED"

### Supported Calendar Formats

| Format | How to Provide | Best For |
|--------|---------------|----------|
| DOCX | Upload or file path | Agency handoff documents |
| XLSX | Upload or file path | Structured spreadsheets with columns |
| Notion | Paste page URL (requires Notion MCP) | Teams already on Notion |
| Text | Paste directly or .txt file | Quick/informal calendars |

### Tier Definitions

- **HERO** — Flagship content (launches, campaigns, major announcements). Highest approval scrutiny, ANCHOR_COMPOSE or STYLE_REFERENCED mode.
- **HUB** — Regular recurring content (tips, how-tos, thought leadership). Standard review, any creative mode.
- **HYGIENE** — Always-on content (quotes, reposts, community engagement). Lightweight review, often PURE_CREATIVE.

---

## 7. Understanding the 4 Creative Modes

Every post gets assigned one of four creative modes during asset matching. Each mode defines how the final visual is produced — specifically, how much of the image comes from the brand's own photography versus AI generation.

### Mode 1: ANCHOR_COMPOSE (8 posts this month)

**When:** The brand has a perfect photo for the post — a product shot, headshot, or screenshot.

**Example:** Post P03 "Meet our new Avocado Oil product line"
- Brand asset: `product-avocado-oil-bottle.jpg` (product on white background)
- What SocialForge does:
  1. Removes the white background (rembg)
  2. Generates an AI scene: "Rustic wooden kitchen counter, morning sunlight, fresh avocados beside the bottle"
  3. Composites the product onto the generated scene
  4. Adds drop shadow and edge feathering for natural placement
  5. Overlays brand logo (bottom-right, 70% opacity)
  6. Resizes for LinkedIn (1200x627), Instagram (1080x1350), Facebook (1200x630)

**The product photo is UNTOUCHED. AI only creates the world around it.**

### Mode 2: ENHANCE_EXTEND (5 posts)

**When:** The brand has a good photo but it needs enhancement — extend the background, improve lighting, adjust mood.

**Example:** Post P09 "Our farm at golden hour"
- Brand asset: `farm-sunrise.jpg` (beautiful but too tightly cropped for LinkedIn landscape)
- What SocialForge does:
  1. Feeds the photo to Gemini with instruction: "Extend the left and right edges to create a wider landscape view. Keep the central farmhouse and sunrise untouched."
  2. Verifies core subject is preserved
  3. Overlays brand logo and resizes for each platform

**The core photo stays faithful. AI only extends/enhances the edges.**

### Mode 3: STYLE_REFERENCED (9 posts)

**When:** No specific brand photo fits, but the AI should generate something that looks like the brand's own photography.

**Example:** Post P18 "5 Tips for Organic Living" (carousel — abstract concept, no specific product)
- No matching brand asset
- SocialForge feeds 6 style reference photos (selected from the brand's best images) to Gemini alongside the prompt
- The AI generates a new image that absorbs the brand's visual DNA — warm lighting, earthy tones, natural textures
- Result looks like it was shot by the brand's photographer, not stock AI

**No brand photo is composited. But the output matches the brand's visual identity.**

### Mode 4: PURE_CREATIVE (4 posts)

**When:** Generic content where brand visual DNA isn't critical — festival greetings, trending topics, abstract concepts.

**Example:** Post P25 "Happy Earth Day from GreenLeaf"
- Full AI generation with brand colors (#2D5016 green, #F4E9D1 cream, #D4A853 gold)
- No reference images fed — only text prompt + brand colors/mood
- Quick, low-cost, suitable for HYGIENE tier content

### How Modes Are Assigned

The `match-assets` skill scores each post against the asset index using five factors: subject relevance, mood alignment, color compatibility, composition fit, and resolution adequacy. Posts with a strong asset match get ANCHOR_COMPOSE. Posts with a partial match get ENHANCE_EXTEND. Posts with no match but strong brand aesthetic needs get STYLE_REFERENCED. Everything else gets PURE_CREATIVE.

Override any assignment:

```
/sf:swap-asset P18 --mode ANCHOR_COMPOSE --asset asset_023
```

---

## 8. Producing Content -- Images

Image production uses a **4-stage human-in-the-loop flow**. You stay in control at every step.

| Stage | What Happens | Your Input |
|-------|-------------|------------|
| 1. Creative direction | 2-3 creative direction options | Pick one (or describe your own) |
| 2. Confirm details | Full prompt, asset match, platform specs | Confirm or adjust |
| 3. Generate versions | 2-3 image versions shown inline | Pick the best, regenerate, or refine |
| 4. Post-process and save | Resize, logo, compliance check | Approve final output |

### Example: Single Image Post

```
/sf:generate-post P03
```

**Stage 1 -- Creative Direction:**
```
P03 "Meet our new Avocado Oil product line"
Mode: ANCHOR_COMPOSE | Asset: product-avocado-oil-bottle.jpg

Option A: Rustic kitchen -- warm wooden counter, morning sunlight
Option B: Farm-to-table -- outdoor dining table, olive grove backdrop
Option C: Minimal clean -- solid warm cream background, centered product

Which direction? (A / B / C / describe your own) > A
```

**Stage 2 -- Confirm Details:**
```
Direction: Rustic kitchen
Prompt: "Product bottle on rustic kitchen counter, warm morning light..."
Asset: product-avocado-oil-bottle.jpg (background removed)
Platforms: LinkedIn (1200x627), Instagram (1080x1350), Facebook (1200x630)
Confirm? (yes / adjust) > yes
```

**Stage 3 -- Generate Versions:**
```
Generating via Vertex AI...
[Version 1 shown inline]  [Version 2 shown inline]  [Version 3 shown inline]
Pick a version? (1 / 2 / 3 / regenerate / refine "instructions") > 2
```

**Stage 4 -- Post-process and Save:**
```
Compositing product onto scene... done
Logo overlay, resizing, compliance check... done
Quality score: 8.6/10
Saved to: output/greenleaf-organics/2026-04/posts/P03/
Approve? (yes / regenerate / skip) > yes
```

### Generate All Posts

```
/sf:generate-all
```

```
Runs the 4-stage flow for each post. You approve each before moving on.
For posts where you trust the defaults, type "auto" to skip interactive stages.

Production complete: 28/28 posts generated
  Average quality: 8.1/10
  API cost: $2.87
  Time: 42 minutes
```

### Generate a Single Post

```
/sf:generate-post P03
```

Useful for reactive content, fixing individual posts, or testing different creative directions before committing to a full run.

### Generate by Week

```
/sf:generate-all --week 1
```

Produces only Week 1 posts (April 1-7). Handy when you need the first week delivered immediately while the rest of the month is still in planning.

### Copy Adaptation

Copy is automatically adapted for each platform during generation:

```
Post P03 copy adapted:
  LinkedIn: 847 chars (under 3000) | 4 hashtags | Direct link CTA
  Instagram: 1,203 chars | 20 hashtags (first comment) | Link in bio
  Facebook: 423 chars | 3 hashtags | Direct link
  Compliance: PASSED (0 issues)
```

The adapter handles character limits, hashtag placement strategy, CTA style (link-in-bio vs direct), tone shifts (professional for LinkedIn, conversational for Instagram), and bilingual formatting if configured.

### Edit After Generation

```
/sf:edit-image P03 "Make the background warmer, more golden light"
/sf:edit-post P03 --copy "Updated headline: Introducing our new Avocado Oil..."
/sf:swap-asset P03 --asset asset_015
```

Each edit regenerates only the affected element — not the entire post.

### Generate Variants for A/B Testing

```
/sf:generate-post P03 --variant b
```

Creates an alternative version. Both variants appear side-by-side in the review gallery so you or the client can pick the winner.

### Reactive Posts (Outside the Calendar)

A trending topic or breaking news warrants an unplanned post:

```
/sf:reactive-post "Earth Day celebration" --brand GreenLeaf --platform instagram
```

Creates a one-off post with the same quality pipeline (asset matching, creative mode, copy adaptation, compliance check) but outside the planned calendar.

---

## 8. Reviewing and Approving

### Open the Review Gallery

```
/sf:review
```

This builds an interactive HTML gallery showing all 28 posts with:
- Image preview + platform mockup (how it will actually look on LinkedIn, Instagram, Facebook)
- Copy text for each platform variant
- Quality score and compliance status
- Tier badge (HERO red, HUB blue, HYGIENE green)

**Filter by tier, platform, or status:**

```
/sf:review --tier HERO
/sf:review --platform instagram
```

### Approve or Request Revisions

Bulk approve posts that look good:

```
/sf:manage-reviews --approve P01 P02 P03 P04 P05
```

Flag posts that need changes:

```
/sf:manage-reviews --revise P06 "The background color doesn't match our brand green"
```

The revision command regenerates only the affected elements:

```
/sf:revision P06 "Use darker green (#2D5016) in the background, keep the product placement"
```

### Tiered Approval Workflow

The approval chain is configured per brand during setup:

| Tier | Internal Review | Client Approval | Auto-Approve Option |
|------|----------------|-----------------|---------------------|
| HERO | Social lead + Creative director | Yes (required) | No |
| HUB | Social lead | Yes (optional) | No |
| HYGIENE | Social lead | No | Yes (configurable) |

### Send to Client (HERO Content)

```
/sf:client-review --tier HERO
```

Sends the 4 HERO posts to the client via Slack (if connected) or packages them for email delivery. The client reviews and responds with approve/revise per post.

### Check Status Anytime

```
/sf:status
```

```
SocialForge Status — GreenLeaf Organics / April 2026

Posts: 28 total | 28 generated | 22 approved | 4 pending client | 2 in revision
Quality: Avg 8.1/10 | Lowest: P14 (7.0)
Compliance: 27 passed | 1 flagged (P09: needs "non-GMO" disclaimer)
Cost: $2.87 total

By Tier:
  HERO: 4 generated, 2 approved-internal, 2 pending-client
  HUB: 14 generated, 14 approved
  HYGIENE: 10 generated, 10 approved (auto-approved per config)
```

### Send Reminders for Overdue Reviews

```
/sf:check-approvals --send-reminders
```

Nudges reviewers who have pending approvals past the configured deadline.

---

## 9. Finalizing and Delivering

Once all posts are approved:

```
/sf:finalize
```

```
Pre-finalization check:
  28/28 posts FINAL status
  All compliance checks passed
  Calendar document assembled
  All approval gates satisfied

Packaging...

FINAL/
  00-Calendar-Document/
    GreenLeaf-Organics-April-2026-Calendar.docx
  01-Ready-to-Publish/
    Week-1/
      2026-04-01-P01-Avocado-Oil-Launch/
        linkedin/
          image-1200x627.png
          copy.txt
          preview.png
        instagram/
          image-1080x1350.png
          copy.txt
          preview.png
        facebook/
          image-1200x630.png
          copy.txt
          preview.png
      ...
    Week-2/ ...
    Week-3/ ...
    Week-4/ ...
  02-Carousels/
  03-Video-Production-Kit/
  04-Stories-Shorts/
  05-Review-Gallery/
  06-Publishing-Schedule/
  07-Production-Checklist/

Finalized: 28 posts across 3 platforms
Files organized in delivery folder
Calendar document generated
```

### What the Delivery Contains

- **Calendar Document** — A DOCX with every post laid out: date, platform, image thumbnail, copy, hashtags, CTA, and scheduling notes. This is what the client signs off on.
- **Ready-to-Publish** — Platform-specific folders with final-resolution images and copy files. Hand these to whoever schedules posts.
- **Carousels** — Rendered carousel slides as individual PNGs plus combined PDFs.
- **Video Production Kit** — Storyboards, scripts, and any AI-generated video clips for posts tagged as video.
- **Review Gallery** — The HTML gallery for archival reference.
- **Publishing Schedule** — A CSV/JSON schedule compatible with scheduling tools (Buffer, Hootsuite, Later).
- **Production Checklist** — What was approved, by whom, and when.

### Force Finalize

If you need to deliver before all approvals are complete:

```
/sf:finalize --force
```

Use sparingly — this bypasses the approval chain and logs that it was force-finalized.

---

## 10. Working with Multiple Brands

Agencies handle multiple clients. Switch between them instantly:

```
/sf:switch-brand ClientB
```

Now all commands operate on ClientB's brand config, assets, and calendar:

```
/sf:new-month ClientB 2026-04
/sf:generate-all
/sf:finalize
```

Switch back:

```
/sf:switch-brand GreenLeaf
```

Each brand has completely isolated:
- Config, assets, compliance rules, approval chains
- Monthly production output
- Status tracking and cost accounting

There is no limit on the number of brands. A typical agency runs 5-15 brands through SocialForge simultaneously.

### Checking Across Brands

```
/sf:status --brand GreenLeaf
/sf:status --brand ClientB
/sf:cost-report --brand all
```

---

## 11. Where Your Data Lives

### Persistent Storage (Survives Sessions)

All SocialForge data lives under the plugin data directory, which persists across sessions on both Claude Code and Cowork.

| Data | Location | Persists? |
|------|----------|-----------|
| Brand configs | `${CLAUDE_PLUGIN_DATA}/socialforge/brands/{slug}/` | Yes |
| Asset indexes | `${CLAUDE_PLUGIN_DATA}/socialforge/brands/{slug}/asset-index.json` | Yes |
| Monthly output | `${CLAUDE_PLUGIN_DATA}/socialforge/output/{slug}/{month}/` | Yes |
| Prompt logs | `${CLAUDE_PLUGIN_DATA}/socialforge/shared/prompt-logs/` | Yes |
| Cost tracking | `${CLAUDE_PLUGIN_DATA}/socialforge/shared/cost-tracker.json` | Yes |

The `${CLAUDE_PLUGIN_DATA}` variable resolves automatically on both platforms. You never need to know the absolute path.

### Asset Images (External)

Your actual photos stay where they are — SocialForge only stores metadata:
- **Google Drive** — Claude reads via platform integration (Cowork) or local download (Claude Code). Photos remain in Drive.
- **Cloudinary** — Professional DAM, connected via HTTP MCP. Assets accessed by URL.
- **Local folder** — Works in Claude Code (persistent). In Cowork, local files are session-only unless stored in the plugin data directory.

### Generated Images

AI-generated visuals are stored in the monthly output directory:

```
${CLAUDE_PLUGIN_DATA}/socialforge/output/greenleaf-organics/2026-04/
  posts/
    P01/
      source-asset.jpg        <- Original brand photo (copy)
      generated-scene.png     <- AI-generated background
      composited-final.png    <- Final composite
      linkedin-1200x627.png   <- Platform-sized final
      instagram-1080x1350.png
      facebook-1200x630.png
    P02/ ...
  carousels/
  gallery/
  delivery/
```

---

## 12. All 18 Commands

| Command | What It Does | Example |
|---------|-------------|---------|
| `/sf:brand-setup` | Configure a brand profile | `/sf:brand-setup GreenLeaf` |
| `/sf:index-assets` | Index brand photo library | `/sf:index-assets GreenLeaf --source /path` |
| `/sf:new-month` | Start monthly production | `/sf:new-month GreenLeaf 2026-04` |
| `/sf:generate-all` | Produce all posts | `/sf:generate-all --week 1` |
| `/sf:generate-post` | Produce one post | `/sf:generate-post P03` |
| `/sf:edit-post` | Edit copy/visual/metadata | `/sf:edit-post P03 --copy "new headline"` |
| `/sf:edit-image` | AI edit a generated image | `/sf:edit-image P03 "warmer background"` |
| `/sf:swap-asset` | Change the matched asset | `/sf:swap-asset P03 --asset asset_015` |
| `/sf:review` | Open review gallery | `/sf:review --tier HERO` |
| `/sf:revision` | Apply revision feedback | `/sf:revision P06 "fix background color"` |
| `/sf:manage-reviews` | Bulk approve/revise posts | `/sf:manage-reviews --approve P01 P02 P03` |
| `/sf:client-review` | Send to client for review | `/sf:client-review --tier HERO` |
| `/sf:check-approvals` | Check pending approvals | `/sf:check-approvals --send-reminders` |
| `/sf:finalize` | Package for delivery | `/sf:finalize` |
| `/sf:switch-brand` | Switch active brand | `/sf:switch-brand ClientB` |
| `/sf:reactive-post` | Create unplanned post | `/sf:reactive-post "Earth Day" --brand GreenLeaf` |
| `/sf:sync-calendar` | Re-read calendar source | `/sf:sync-calendar` |
| `/sf:status` | Show production dashboard | `/sf:status` |
| `/sf:cost-report` | API cost breakdown | `/sf:cost-report --brand GreenLeaf` |

---

## 13. All 14 Skills

Skills are the internal engines that commands invoke. You rarely call them directly, but understanding them helps when troubleshooting or customizing behavior.

| Skill | Effort | What It Does |
|-------|--------|-------------|
| brand-manager | medium | Set up and manage brand profiles, visual identity, compliance rules |
| index-assets | high | AI-powered brand photo library indexing via Gemini Vision |
| parse-calendar | medium | Parse DOCX/XLSX/Notion/text calendars into structured post data |
| match-assets | high | Score and match assets to posts using 5-factor algorithm, assign creative modes |
| compose-creative | max | Core 4-mode creative production engine (ANCHOR, ENHANCE, STYLE, PURE) |
| adapt-copy | medium | Platform-specific copy with character limits, hashtags, CTAs, compliance |
| render-carousels | high | HTML template to PNG slides via Playwright (8 templates) |
| generate-video | high | Video scripts, storyboards, AI video clips for Reels/Shorts |
| create-previews | medium | Platform mockup previews showing how posts will actually appear |
| build-review-gallery | medium | Interactive HTML review gallery with filtering and actions |
| manage-reviews | medium | Multi-tier approval workflow with escalation and reminders |
| assemble-document | high | DOCX calendar delivery document with images, copy, and schedule |
| finalize-month | high | Final packaging, compliance verification, and delivery folder creation |
| full-pipeline | max | End-to-end orchestration running all 7 production phases in sequence |

### Effort Levels

- **medium** — Completes in seconds, minimal API cost
- **high** — May take 1-5 minutes, moderate API cost
- **max** — Extended operation (10-45 minutes for full pipeline), highest API cost

---

## 14. Connectors

10 HTTP connectors ship with SocialForge. All work in both Cowork and Claude Code — no local server installation required.

| Connector | URL | What For | Required? |
|-----------|-----|----------|-----------|
| Notion | `https://mcp.notion.com/mcp` | Calendar databases, brand guidelines | Optional |
| Canva | `https://mcp.canva.com/mcp` | Design templates, brand kit | Optional |
| Figma | `https://mcp.figma.com/mcp` | Brand design files | Optional |
| Slack | `https://mcp.slack.com/mcp` | Approval notifications, delivery | Optional |
| Gmail | `https://gmail.mcp.claude.com/mcp` | Email delivery, reminders | Optional |
| Google Calendar | `https://gcal.mcp.claude.com/mcp` | Posting schedule | Optional |
| fal.ai | `https://fal.ai/mcp` | AI image generation | Recommended |
| Replicate | `https://replicate.com/mcp` | Alternative AI image gen | Optional |
| Asana | `https://mcp.asana.com/sse` | Production task tracking | Optional |
| Cloudinary | `https://mcp.cloudinary.com/mcp` | Professional DAM | Optional |

**The plugin works fully without any connectors.** All skills function with local assets and direct Gemini API calls. Connectors add convenience — pull calendars from Notion, send reviews via Slack, access assets from Cloudinary — but are entirely optional.

### Google Drive

Google Drive is a platform-level integration, not an HTTP connector. In Cowork, connect it via Settings > Integrations > Google Drive. In Claude Code, use local file paths or download assets manually. There is no `.mcp.json` entry for Drive.

### Connecting a Connector

Most connectors activate through the Connectors panel in Claude's settings. For Slack, Notion, Canva, and Figma, you authorize via OAuth — no API keys to manage. For fal.ai and Replicate, you connect your account through their respective dashboards.

---

## 15. Troubleshooting

### "Brand not found"

**Cause:** The command requires an active brand, but none is set or the name doesn't match.
**Fix:** Run `/sf:brand-setup [name]` to create the brand profile, or `/sf:switch-brand [name]` if it already exists. Brand names are stored as lowercase-kebab-case slugs (e.g., "GreenLeaf Organics" becomes `greenleaf-organics`).

### "No assets indexed"

**Cause:** The brand has no asset index. Creative modes that depend on brand photos (ANCHOR_COMPOSE, ENHANCE_EXTEND, STYLE_REFERENCED) cannot run.
**Fix:** Run `/sf:index-assets [brand] --source /path/to/photos` or provide a Google Drive folder URL. Need at least 5 images for meaningful matching.

### "Image generation failed"

**Cause:** No image generation API is available.
**Fix:** Run `/sf:setup --status` to verify Vertex AI credentials. If not configured, run `/sf:setup` to configure. The pipeline supports resuming — fix the credentials and rerun `/sf:generate-all`.

### "Video generation failed"

**Cause:** WaveSpeed API key is missing or invalid.
**Fix:** Check WaveSpeed API key via `/sf:setup --status`. Verify credits at wavespeed.ai. If not configured, run `/sf:setup`.

### "Credentials not found"

**Cause:** API credentials have not been configured or were removed.
**Fix:** Run `/sf:setup` again to reconfigure.

### "Playwright not installed"

**Cause:** Carousel rendering and gallery builds require Playwright with Chromium.
**Fix:** `pip install playwright && playwright install chromium`. In restricted environments, also run `playwright install-deps`.

### "Quality score below 7.0"

**Cause:** Usually a vague visual brief or weak asset match.
**Fix:** Try a more specific prompt, a different brand asset, or switch to STYLE_REFERENCED mode. You can also regenerate: `/sf:generate-post P14 --regenerate`.

### "Compliance blocked"

**Cause:** A post triggered a block-severity rule in the brand's `compliance-rules.json`.
**Fix:** Read the error for the specific banned phrase. Edit the copy to remove or rephrase it: `/sf:edit-post P09 --copy`. If the rule is a false positive, update the compliance config via `/sf:brand-setup --update [brand]`.

### "Calendar parse failed"

**Cause:** The DOCX/XLSX structure wasn't recognized.
**Fix:** Ensure the calendar has columns or rows for: date, platform, topic/title. Tier and copy are optional. If the format is unusual, paste the calendar as structured text instead.

### Posts Not Persisting Across Sessions

**Cause:** Data may have been written to a temporary directory instead of the plugin data directory.
**Fix:** Verify the plugin is installed (not just loaded from local path). Installed plugins use `${CLAUDE_PLUGIN_DATA}` which persists. Run `/sf:status` to confirm the storage path shown is under the plugin data directory.

---

## 16. FAQ

**Q: How much does it cost per month?**
A: For a 28-post calendar: ~$2-4 in Gemini API calls. Carousels and previews are free (local rendering via Playwright). Video generation costs more (~$0.10-0.50 per clip via fal.ai/Replicate). Run `/sf:cost-report` for exact figures.

**Q: Can I use my own images instead of AI generation?**
A: Yes. Upload your pre-made image and it bypasses all generation — just gets resized, overlaid with logo, and adapted per platform. Set the post's creative mode to ANCHOR_COMPOSE and provide the image directly.

**Q: Does it work offline?**
A: Partially. Brand setup, calendar parsing, asset matching, copy adaptation, compliance checking, and carousel rendering all work offline. Image generation requires an API connection (Gemini, fal.ai, or Replicate).

**Q: Can multiple people work on the same brand?**
A: Yes. Brand configs persist in the shared plugin data directory. Multiple team members can work on different months or handle different tiers of the same month simultaneously.

**Q: What calendar formats are supported?**
A: DOCX (Word tables), XLSX (Excel rows with column headers), Notion databases (via Notion MCP connector), and structured text/markdown.

**Q: How long does it take to produce a full month?**
A: For 28 posts across 3 platforms: approximately 45 minutes total. Brand setup: 5 min (one-time). Asset indexing: 5 min (one-time). Production: 30 min. Review: 5 min. Subsequent months for the same brand are faster since setup and indexing are already done.

**Q: What if my calendar changes mid-month?**
A: Run `/sf:sync-calendar` to re-parse. Existing approved posts are preserved. New posts enter the pipeline. Removed posts are flagged for your confirmation before deletion.

**Q: Do I need all 10 connectors?**
A: No. SocialForge works fully without any connectors. They add convenience (pull calendars from Notion, send reviews via Slack, access Cloudinary assets) but every core feature works with local files and direct API calls.

**Q: Can I customize carousel templates?**
A: Yes. The 8 built-in HTML templates live in `assets/carousel-templates/`. Edit them directly or create new ones following the same variable injection pattern. Brand colors, fonts, and logos are injected automatically.

**Q: How do I add a reactive/trending post not in the calendar?**
A: Run `/sf:reactive-post "topic" --platform instagram --brand GreenLeaf`. It creates a one-off post outside the planned calendar with the same quality pipeline.

**Q: What platforms are supported?**
A: LinkedIn, Instagram, Facebook, X/Twitter, YouTube (thumbnails), Pinterest, and TikTok. Each has its own dimension specs and character limits configured in the copy adapter.

**Q: Can I use SocialForge without any AI image generation?**
A: Yes. ANCHOR_COMPOSE mode works with brand assets alone using Pillow for compositing. Carousel rendering uses Playwright (no AI). You can also provide pre-made visuals for every post and skip generation entirely. Only STYLE_REFERENCED and PURE_CREATIVE modes require an image generation API.

**Q: Where do I set API keys?**
A: Run `/sf:setup` to configure all credentials. They are stored securely in the plugin data directory. For fal.ai and Replicate, connect via the Connectors panel instead of managing keys manually.

---

*SocialForge v1.3 — Built for agencies who produce content at scale without compromising brand identity.*
