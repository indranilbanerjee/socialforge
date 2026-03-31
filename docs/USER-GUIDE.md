# SocialForge User Guide

**Version:** 1.0.0
**Last Updated:** 2026-03-31

A practical guide to producing agency-grade social media calendars with SocialForge. Every section helps you do something — no filler.

---

## 1. Before You Start

**What SocialForge does:** Takes a monthly content calendar, matches brand assets, generates AI-composed creative, renders carousels, adapts copy per platform, and produces review galleries and delivery documents.

**What you need:**

- Claude Code or Cowork environment
- A brand asset folder (product photos, logos, headshots) — at least 5-10 images
- A monthly content calendar (DOCX, XLSX, Notion page, or structured text)
- API keys for AI image generation (at least one): `FAL_KEY`, `REPLICATE_API_TOKEN`, or `GEMINI_API_KEY`

**Optional but recommended:**

- Playwright installed (`pip install playwright && playwright install chromium`) for carousel rendering and gallery builds
- `python-docx` installed for DOCX delivery document export
- MCP connectors configured (Notion, Canva, Slack, etc.) for workflow integration

**Where files live:**

```
~/socialforge-workspace/brands/<brand-slug>/   # Brand config, assets, calendar, outputs
~/socialforge-workspace/brands/<brand-slug>/assets/   # Brand image library
~/socialforge-workspace/brands/<brand-slug>/output/    # Generated creative
```

---

## 2. Installation

### Method A: From Marketplace (recommended)

```
claude plugin marketplace add github:indranilbanerjee/socialforge
claude plugin install socialforge@socialforge
```

### Method B: From GitHub

```
claude plugin install github:indranilbanerjee/socialforge
```

### Method C: From Local Directory

```
claude plugins add /path/to/socialforge
```

After installation, restart your Claude session. You should see the SocialForge welcome message confirming version and available commands.

**Verify installation:** Run `/sf:status`. If you see "No active brand," installation succeeded.

---

## 3. Quick Start

The full workflow in 6 commands:

```
1. /sf:brand-setup acme-corp        — Configure brand profile (5-10 min)
2. /sf:index-assets acme-corp       — Index the brand's photo library
3. /sf:new-month acme-corp 2026-04  — Start April production
4. /sf:generate-all                 — Produce all creative
5. /sf:review                       — Review and approve posts
6. /sf:finalize                     — Package for delivery
```

That's it. For most months, this is the entire workflow. The sections below explain each step in detail and cover the edge cases.

---

## 4. Brand Setup

Run `/sf:brand-setup [brand-name]` to create a new brand profile. The setup wizard walks you through:

1. **Brand identity** — Name, slug, tagline, website, industry
2. **Visual identity** — Primary/secondary colors (hex), fonts, logo file path
3. **Voice and tone** — Communication style, vocabulary preferences, tone markers
4. **Platform config** — Which platforms to post on, posting cadence, hashtag strategy
5. **Compliance rules** — Banned phrases, required disclaimers, data claim policy
6. **Approval chain** — Who reviews what tier (HERO/HUB/HYGIENE), escalation timelines

**Output:** A `brand-config.json` file at `~/socialforge-workspace/brands/<brand-slug>/`.

**Tips:**

- Brand slugs must be lowercase-kebab-case (e.g., `acme-corp`, not `Acme Corp`)
- You can update any section later with `/sf:brand-setup acme-corp --update`
- Switch between brands with `/sf:switch-brand <name>`
- Compliance rules are enforced automatically by the PreToolUse hook — set them once, forget them

---

## 5. Calendar Parsing

SocialForge accepts calendars in four formats:

| Format | How to Provide | Best For |
|--------|---------------|----------|
| DOCX | File path | Agency handoff documents |
| XLSX | File path | Structured spreadsheets with columns |
| Notion | Notion page URL (requires Notion MCP) | Teams already on Notion |
| Text | Paste directly or provide .txt file | Quick/informal calendars |

**Required fields per post:**

| Field | Required | Example |
|-------|----------|---------|
| Date | Yes | 2026-04-07 |
| Platform(s) | Yes | LinkedIn, Instagram |
| Topic/Title | Yes | "Q1 Results Infographic" |
| Tier | Recommended | HERO, HUB, or HYGIENE |
| Copy/Caption | Optional | Can be generated later |
| Visual direction | Optional | "Product flat-lay, warm tones" |

**How it works:** The `parse-calendar` skill reads your source document, extracts post entries, normalizes dates and platform names, assigns tiers if missing (based on content type heuristics), and writes `calendar-data.json`.

Run: `/sf:sync-calendar` to parse or re-sync from source.

**Tier definitions:**

- **HERO** — Flagship content (launches, campaigns, major announcements). Gets highest approval scrutiny.
- **HUB** — Regular recurring content (tips, how-tos, thought leadership). Standard review.
- **HYGIENE** — Always-on content (quotes, reposts, community engagement). Lightweight review.

---

## 6. Asset Indexing

Run `/sf:index-assets <brand-name>` to scan and catalog the brand's image library.

**What happens:**

1. The indexer scans the brand's `assets/` directory for `.jpg`, `.jpeg`, `.png`, and `.webp` files
2. Each image is analyzed using AI vision to generate descriptions, dominant colors, detected objects, mood tags, and suitability scores
3. Results are written to `asset-index.json` with per-image metadata

**Cost expectations:**

- AI vision analysis costs approximately $0.01-0.03 per image depending on provider
- A typical brand library of 50-100 images costs $0.50-3.00 to index
- Re-indexing with `--refresh` only processes new/changed files

**Tips:**

- Organize assets into subfolders (products/, team/, lifestyle/, logos/) for better matching
- Include at least 3-5 style reference images for the STYLE_REFERENCED creative mode
- Supported formats: JPG, PNG, WEBP. Minimum resolution: 800x800 recommended
- Use `--source <path>` to index from a non-standard directory

---

## 7. The 4 Creative Modes

SocialForge uses four modes to generate visuals. Each post is assigned a mode during asset matching.

### ANCHOR_COMPOSE

**When to use:** The brand photo IS the content — a product shot, headshot, or screenshot.

**What happens:** The brand asset is placed as the untouched centerpiece. AI generates a complementary scene around it — backgrounds, decorative elements, mood lighting. The brand photo's pixels are never modified.

**Example:** A product bottle on a plain white background becomes a product bottle on a marble countertop with soft morning light and botanical elements.

### ENHANCE_EXTEND

**When to use:** The brand photo needs more canvas or context but should remain dominant.

**What happens:** AI extends the image periphery — adding more background, filling edges, or expanding the scene. The core of the brand photo stays pixel-faithful.

**Example:** A tight headshot is extended into a wider frame with a blurred office background.

### STYLE_REFERENCED

**When to use:** No specific asset is needed, but the visual should match the brand's aesthetic.

**What happens:** AI generates an entirely new image using the brand's style reference photos as visual DNA — matching color palette, mood, composition style.

**Example:** A motivational quote post where the background is generated to match the brand's warm, minimal aesthetic.

### PURE_CREATIVE

**When to use:** Generic or abstract content where brand photos aren't relevant.

**What happens:** AI generates from a text prompt combined with brand colors and mood guidelines. No brand assets are composited.

**Example:** An abstract background for a holiday greeting or event announcement.

**How modes are assigned:** The `match-assets` skill automatically assigns modes based on post type and available assets. Override with `/sf:swap-asset <post-id>` or by editing the post's visual config.

---

## 8. Running the Production Pipeline

### Full pipeline (recommended)

```
/sf:generate-all
```

This runs all production phases in sequence:

1. **Calendar parse** — Validate and structure the calendar data
2. **Asset match** — Assign brand assets and creative modes to each post
3. **Visual production** — Generate images using the 4 creative modes
4. **Copy generation** — Write or refine copy for each post
5. **Copy adaptation** — Adapt copy per platform (character limits, hashtags, CTAs)
6. **Compliance check** — Verify all content against brand rules
7. **Preview generation** — Create platform mockup previews
8. **Gallery build** — Assemble the interactive review gallery

### Single post generation

```
/sf:generate-post <post-id>
```

Generates creative for one post only. Useful for reactive content or fixing individual posts.

### Generating variants

```
/sf:generate-post <post-id> --variant b
```

Creates an alternative version for A/B testing or client choice.

### Resuming after failure

The pipeline tracks progress in `status-tracker.json`. If it fails mid-run, just run `/sf:generate-all` again — it picks up from where it stopped. You rarely need to restart from scratch.

---

## 9. Approval Workflows

SocialForge has a tiered approval system based on content tier:

| Tier | Default Reviewers | Client Approval | CEO Approval |
|------|-------------------|-----------------|--------------|
| HERO | Social lead + Brand manager + Creative director | Yes | Yes |
| HUB | Social lead + Brand manager | Yes | No |
| HYGIENE | Social lead | No | No |

**How it works:**

1. After generation, posts enter the review queue
2. Run `/sf:review` to open the review gallery and approve, reject, or request revisions
3. Posts meeting the minimum reviewer threshold advance to client review (if required)
4. Use `/sf:client-review` to send approved posts to the client via Slack or email
5. Escalation triggers automatically when reviews exceed `max_review_hours`

**Customizing the approval chain:**

Edit `approval-chain.json` in the brand directory. You can set per-tier reviewers, minimum approval counts, and escalation timelines.

**Check approval status:**

```
/sf:check-approvals              # See what's pending
/sf:check-approvals --send-reminders  # Nudge overdue reviewers
```

---

## 10. Carousel Rendering

SocialForge includes 8 HTML carousel templates rendered via Playwright:

| Template | Slides | Best For |
|----------|--------|----------|
| `tips-5slide` | 5 | Tip lists, how-tos |
| `recap-6slide` | 6 | Event recaps, weekly roundups |
| `data-infographic-6slide` | 6 | Data-driven content |
| `generic-8slide` | 8 | General multi-point content |
| `playbook-8slide` | 8 | Step-by-step guides |
| `comparison-10slide` | 10 | Before/after, product comparisons |
| `case-study-10slide` | 10 | Client success stories |
| `quote-card-single` | 1 | Single quote or testimonial |

**How to use:**

1. Posts tagged as carousels in the calendar are automatically routed to the carousel builder
2. The template is selected based on content type and slide count
3. Brand colors, fonts, and logo are injected automatically
4. Override the template: `/sf:generate-post <post-id> --template case-study-10slide`

**Customizing templates:**

Templates live in `assets/carousel-templates/`. They are HTML/CSS files that accept brand variables. Edit them to match your brand's specific design system.

**Requirements:** Playwright with Chromium must be installed. Run `playwright install chromium` if you haven't already.

---

## 11. Copy Adaptation

The copy adapter adjusts post text for each target platform automatically.

**What it handles:**

- **Character limits** — LinkedIn (3,000), X/Twitter (280), Instagram (2,200), Facebook (63,206)
- **Hashtag strategy** — Platform-appropriate hashtag count and placement
- **CTA style** — Link-in-bio for Instagram, direct links for LinkedIn/X
- **Tone shifts** — Professional for LinkedIn, conversational for Instagram, concise for X
- **Bilingual formatting** — If the brand requires dual-language posts

**How it works:**

1. The adapter takes the master copy from the calendar
2. It generates platform-specific variants respecting each platform's constraints
3. Compliance rules are checked on every variant (banned phrases, required disclaimers)
4. All variants are stored in the post's `copy` object for review

**Manual copy editing:**

```
/sf:edit-post <post-id> --copy      # Edit the master copy
/sf:edit-post <post-id> --visual    # Edit visual direction
```

---

## 12. Review and Gallery

The review gallery is an interactive HTML page showing all generated posts.

**Opening the gallery:**

```
/sf:review                          # All posts
/sf:review --tier HERO              # HERO posts only
/sf:review --brand acme-corp        # Specific brand
```

**What you can do in review:**

- **Approve** — Post moves to the next approval stage (or finalization if fully approved)
- **Request revision** — Specify what to change; the post returns to production
- **Reject** — Post is removed from the month's output
- **Swap asset** — Change the brand photo used: `/sf:swap-asset <post-id>`
- **Edit image** — Adjust background, lighting, or composition: `/sf:edit-image <post-id> <instruction>`

**Applying revisions:**

```
/sf:revision <post-id> "Make the background warmer and add the brand tagline"
```

The revision command regenerates only the affected elements (image, copy, or both) without restarting the full pipeline.

---

## 13. Finalization

Once all posts are approved:

```
/sf:finalize
```

**What finalize does:**

1. Verifies all posts have complete approvals per their tier's approval chain
2. Generates final-resolution images in all required platform dimensions
3. Assembles the delivery DOCX with all posts, copy, images, and scheduling metadata
4. Creates the organized delivery folder structure:

```
output/2026-04-final/
  images/          # All final images, named by post ID and platform
  carousels/       # Rendered carousel PDFs/PNGs
  copy/            # Per-platform copy files
  calendar.docx    # Complete delivery document
  summary.json     # Machine-readable summary
```

**Force finalize** (skip approval checks):

```
/sf:finalize --force
```

Use sparingly — this bypasses the approval chain.

---

## 14. Command Reference

| Command | Description | Key Arguments |
|---------|-------------|---------------|
| `/sf:brand-setup` | Configure a new brand profile | `[brand-name] [--update]` |
| `/sf:switch-brand` | Switch active brand context | `<brand-name>` |
| `/sf:index-assets` | Index brand photo library | `<brand-name> [--source] [--refresh]` |
| `/sf:new-month` | Start a new month's production | `<brand> <YYYY-MM>` |
| `/sf:sync-calendar` | Parse or re-sync the content calendar | `[--source <path-or-url>]` |
| `/sf:generate-all` | Generate creative for all posts | `[--brand] [--week <N>]` |
| `/sf:generate-post` | Generate creative for one post | `<post-id> [--variant b]` |
| `/sf:edit-post` | Edit a post's copy, visual, or metadata | `<post-id> [--copy] [--visual]` |
| `/sf:edit-image` | Edit a generated image | `<post-id> <instruction>` |
| `/sf:swap-asset` | Swap the brand asset for a post | `<post-id> [--asset <id>] [--browse]` |
| `/sf:preview-batch` | Generate platform mockup previews | `[--brand] [--platform]` |
| `/sf:review` | Open the review gallery | `[--brand] [--tier HERO\|HUB\|HYGIENE]` |
| `/sf:revision` | Apply revision feedback and regenerate | `<post-id> <feedback>` |
| `/sf:check-approvals` | Check pending approvals and send reminders | `[--brand] [--send-reminders]` |
| `/sf:client-review` | Send approved posts to client | `[--tier HERO\|HUB] [--all-approved]` |
| `/sf:finalize` | Package all approved content for delivery | `[--brand] [--force]` |
| `/sf:reactive-post` | Create a post outside the planned calendar | `<topic> [--brand] [--platform]` |
| `/sf:status` | Show current production status | `[--brand]` |
| `/sf:cost-report` | Show API cost breakdown | `[--brand] [--month]` |

---

## 15. Skill Reference

| Skill | Description | Effort |
|-------|-------------|--------|
| `brand-manager` | Set up and manage brand profiles | medium |
| `parse-calendar` | Parse calendars from DOCX, XLSX, Notion, or text | medium |
| `index-assets` | Index brand photo library using AI vision | high |
| `match-assets` | Match brand assets to calendar posts and assign creative modes | high |
| `compose-creative` | Core creative engine — 4 modes with AI compositing | max |
| `adapt-copy` | Adapt copy per platform (limits, hashtags, CTAs, compliance) | medium |
| `render-carousels` | Render multi-slide carousels via Playwright | high |
| `create-previews` | Generate platform mockup previews | medium |
| `manage-reviews` | Handle approval workflows and revision requests | medium |
| `build-review-gallery` | Build the interactive HTML review gallery | medium |
| `finalize-month` | Package approved content for delivery | high |
| `assemble-document` | Assemble the final delivery DOCX | high |
| `full-pipeline` | Run the complete end-to-end production pipeline | max |
| `generate-video` | Generate short-form video scripts and AI clips | high |

---

## 16. Troubleshooting

### "Brand not found"

Most commands require an active brand. Run `/sf:brand-setup` to create one, or `/sf:switch-brand <name>` if it already exists. Check exact slug with `ls ~/socialforge-workspace/brands/`.

### "No assets indexed"

Run `/sf:index-assets <brand-name>`. Verify image files exist in the brand's `assets/` folder in supported formats (JPG, PNG, WEBP). Minimum 5-10 images recommended.

### "Image generation failed"

Check `.env` for API keys (`FAL_KEY`, `REPLICATE_API_TOKEN`, or `GEMINI_API_KEY`). Check provider status pages. The pipeline supports resuming — just rerun after fixing the key.

### "Playwright not installed"

Required for carousels and galleries. Fix: `pip install playwright && playwright install chromium`. In restricted environments, also run `playwright install-deps`.

### "Compliance blocked"

A post triggered a block-severity rule in `compliance-rules.json`. Read the error for the specific phrase. Edit the copy using the suggested replacement, or adjust the rule if it is a false positive.

---

## 17. FAQ

**Q: Can I use SocialForge without any AI image generation API keys?**
A: Yes. ANCHOR_COMPOSE mode works with brand assets alone (compositing via Pillow). STYLE_REFERENCED and PURE_CREATIVE modes require an image generation API. You can also provide pre-made images and skip generation entirely.

**Q: How much does a typical month cost in API calls?**
A: Varies by volume. A 30-post calendar with AI generation typically costs $5-15 in API credits. Asset indexing is a one-time cost of $0.50-3.00. Run `/sf:cost-report` for exact figures.

**Q: Can I use SocialForge for multiple brands?**
A: Yes. Each brand has its own profile, asset library, and calendar. Switch between them with `/sf:switch-brand <name>`.

**Q: What if my calendar changes mid-month?**
A: Run `/sf:sync-calendar` to re-parse. Existing approved posts are preserved. New posts enter the pipeline; removed posts are flagged for review.

**Q: Do I need all 9 MCP connectors?**
A: No. SocialForge works fully offline. Connectors add convenience (pull calendars from Notion, send reviews via Slack, etc.) but are entirely optional.

**Q: Can I customize carousel templates?**
A: Yes. Templates are HTML/CSS files in `assets/carousel-templates/`. Edit them directly or create new ones following the same variable injection pattern.

**Q: How do I add a reactive/trending post not in the calendar?**
A: Run `/sf:reactive-post "topic" --platform instagram`. It creates a one-off post outside the planned calendar with the same quality pipeline.

**Q: What platforms are supported?**
A: LinkedIn, Instagram, X/Twitter, Facebook, YouTube (thumbnails), Pinterest, and TikTok. Each has its own dimension and character limit specs.

---

*For schema references, see the `references/` directory. For troubleshooting beyond this guide, see `references/troubleshooting.md`.*
