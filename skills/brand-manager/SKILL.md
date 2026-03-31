---
name: brand-manager
description: Set up and manage brand profiles. Use when: configuring a new brand, updating brand config, or switching brands.
argument-hint: "[brand-name] [--update] [--switch]"
effort: medium
user-invocable: true
---

# /sf:brand-setup — Brand Manager

Set up a new brand profile or update an existing one. Brand profiles control visual identity, platform config, compliance rules, approval chains, and asset sources for all SocialForge workflows.

## Quick Start (5-10 minutes)

Most users only need these 5 things to get started:

1. **Brand name** — Your company or client name
2. **Industry** — pharma, bfsi, real-estate, saas, retail, healthcare, edtech, legal, manufacturing, hospitality, automotive, media, other
3. **Brand colors** — Primary (hex), secondary (hex), accent (hex)
4. **Active platforms** — Which social media platforms (LinkedIn, Instagram, X, Facebook, YouTube, etc.)
5. **Asset source** — Where are brand photos? (Google Drive folder URL, local path, or "I'll add later")

That's it. Run `/sf:brand-setup [brand-name]` and answer these 5 questions. SocialForge creates a working brand profile.

**Add more later:** Logo files, fonts, visual style, compliance rules, approval chain, posting times, hashtags → `/sf:brand-setup --update [brand]`

## Full Setup

### Step 1: Core Identity

```
Brand name: [required]
Brand slug: [auto-generated from name, e.g., "acme-corp"]
Tagline: [optional]
Industry: [required — select from list]
Website: [optional]
```

### Step 2: Visual Identity

```
Colors:
  Primary: [hex, e.g., #1B4F72] (required)
  Secondary: [hex] (required)
  Accent: [hex] (optional, defaults to primary)
  Background light: [defaults to #FFFFFF]
  Background dark: [defaults to #1A1A1A]
  Text primary: [defaults to #333333]
  Gradient: enabled? start/end/direction (optional)

Logo files:
  Primary logo: [file path or "skip for now"]
  White/reversed logo: [optional]
  Icon version: [optional]
  Logo overlay position: bottom-right (default) | bottom-left | top-right | top-left
  Logo overlay opacity: 0.7 (default)

Fonts:
  Heading font: [filename or Google Font name, defaults to Montserrat-Bold]
  Body font: [defaults to OpenSans-Regular]
```

### Step 3: Visual Style (For AI Generation)

```
Style keywords: [e.g., "modern", "clean", "professional", "enterprise"]
Mood keywords: [e.g., "confident", "innovative", "authoritative"]
Photography style: warm natural light | studio professional | candid editorial | corporate clean
Illustration style: flat vector | isometric | hand-drawn | 3D render | minimal line art | none
Color temperature: warm | neutral | cool
Contrast level: high | medium | soft

Image rules (array of custom constraints):
  e.g., "Navy should appear in at least 30% of visual area"
  e.g., "Avoid generic stock photo aesthetics"
  e.g., "Always include subtle brand color accents"
  e.g., "No text overlays on product photography"
```

### Step 4: Platform Configuration

```
For each active platform, configure:
  Platform: linkedin | instagram | x | facebook | youtube | tiktok | pinterest
  Profile type: company | personal | creator
  Posting frequency: daily | 3-4/week | 2/week | weekly
  Optimal posting times: [day + time + timezone]
  Supported formats: static | carousel | video | story | reel | short | text_only
  Content mix: video % | carousel % | static % | text_only %
  Cross-posting: from which platform? (e.g., LinkedIn → Facebook)
```

### Step 5: Compliance Rules

```
Banned phrases: [list of phrases that must never appear in copy]
Required disclaimers: [triggers and disclaimer text per platform]
Data claim rules: require source verification? max claim age?
Platform-specific rules: link policy, max hashtags, forbidden content types
```

If user skips: Log warning — "Compliance rules empty. Copy will not be checked for restricted content."

### Step 6: Approval Chain

```
Content tiers:
  HERO (flagship content): Who reviews? Client approval required?
  HUB (regular series): Who reviews?
  HYGIENE (routine posts): Auto-approve or light review?

Escalation: Reminder after N days? Auto-publish without client approval after N days?
```

If user skips: Default to single-tier (all content requires user approval before finalization).

### Step 7: Asset Source

Where are your brand photos stored?

1. **Local folder** — Provide the full path (e.g., /Users/photos/acme-corp/)
   Works in: Claude Code (persistent) | Cowork (session-only, re-provide each session)

2. **Google Drive folder** — Provide the Drive folder URL
   Works in: Cowork (via Settings → Integrations → Google Drive) | Claude Code (download first or mount)
   In Cowork: Claude reads Drive files directly through platform integration
   In Claude Code: Download the folder locally, then index with --source /local/path

3. **I'll add later** — Start with no assets (PURE_CREATIVE mode only)

The asset source is saved in `asset-source.json`. You can change it anytime.

**Recommended for agencies:** Use Google Drive as the source of truth. Each brand gets a Drive folder. SocialForge indexes the photos and stores the index in persistent plugin storage (survives sessions).

```
Style reference photos:
  Select 2-8 photos that represent the brand's visual DNA.
  These guide AI generation in STYLE_REFERENCED mode.
```

### Step 8: Social Profiles

For each active platform configured in Step 4:

```
Platform: [platform name]
  Display name: [brand name as it appears on the platform]
  Handle: [@handle or username]
  Avatar: [file path to avatar/profile photo — used in preview rendering]
  Profile headline: [bio or tagline shown on the platform]
  Profile URL: [full URL to the profile page]
```

This data powers preview rendering (showing exactly how posts look on each platform).

If user skips: Previews will use brand name and placeholder avatar. Recommend filling in for accurate mockups.

### Step 9: Languages

```
Primary language: [e.g., en-US, hi-IN, es-MX]
Secondary languages: [list, e.g., es-MX, fr-FR]
Bilingual config:
  Mode: separate_posts | bilingual_single_post | language_per_platform
  Primary ratio: [percentage of content in primary language, e.g., 80]
Do-not-translate terms: [brand names, product names, taglines to keep in original language]
Translation service preference: manual | ai_with_review | ai_auto
```

### Step 10: Brand Hashtags

```
Always include (every post):
  e.g., #BrandName, #BrandTagline

Campaign hashtags (active campaigns only):
  Campaign name: [hashtag list + start/end dates]
  e.g., "Summer Launch": ["#SummerWith{Brand}", "#LaunchDay"] (2026-06-01 to 2026-08-31)

Platform-specific hashtag rules:
  LinkedIn: max 3-5 hashtags, professional tone
  Instagram: up to 15-20, mix of branded + discovery
  X: max 2-3, integrated into copy
  TikTok: trending + branded mix
```

## Output

Creates these files in `~/socialforge-workspace/brands/{brand-slug}/`:
- `brand-config.json` — Core identity, colors, fonts, visual style, logo, hashtags
- `platform-config.json` — Active platforms, posting times, content mix, cross-posting
- `approval-chain.json` — Review tiers, escalation rules
- `compliance-rules.json` — Banned phrases, disclaimers, platform rules
- `asset-source.json` — Where assets live
- `style-references/` — Style reference photos (copied or linked)

## Pre-Flight Validation

Before any SocialForge workflow starts, the brand profile is validated:
- Brand name and slug set
- At least one platform configured
- Colors (primary + secondary) set
- Asset source configured (or explicitly skipped)

Missing fields trigger a warning with options to continue or fix.

## Timeout & Interruption Handling

- If user closes or interrupts during multi-step setup: save whatever was collected so far. On next `/sf:brand-setup [brand]`, detect the partial profile and ask: "Resume setup from Step {N}? Or start fresh?"
- Each step saves incrementally — no data is lost on interruption.
- If brand-config.json write fails: retry once, then save to `~/socialforge-workspace/brands/{slug}/brand-config.partial.json` and inform user.

## Switching Brands

```
/sf:brand-setup --switch [brand-name]
```

Instantly reloads the brand context. All subsequent commands use the switched brand.
