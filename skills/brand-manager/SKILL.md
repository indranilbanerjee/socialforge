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
Color temperature: warm | neutral | cool
Contrast level: high | medium | soft

Image rules (custom constraints):
  e.g., "Navy should appear in at least 30% of visual area"
  e.g., "Avoid generic stock photo aesthetics"
  e.g., "Always include subtle brand color accents"
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

```
Where are your brand photos?
  1. Google Drive folder URL — SocialForge will index assets from Drive
  2. Local folder path — Index from local filesystem
  3. I'll add later — Start with no assets (can only use PURE_CREATIVE mode)

Style reference photos:
  Select 2-8 photos that represent the brand's visual DNA.
  These guide AI generation in STYLE_REFERENCED mode.
```

### Step 8: Social Profiles

```
For each active platform:
  Display name: [brand name on platform]
  Handle: [@handle]
  Avatar: [file path — used in preview rendering]
  Profile headline: [used in preview rendering]
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

## Switching Brands

```
/sf:brand-setup --switch [brand-name]
```

Instantly reloads the brand context. All subsequent commands use the switched brand.
