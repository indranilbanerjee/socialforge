# SocialForge — Social Media Calendar Automation

**Version:** 1.5.1
**Platform:** Claude Code & Cowork
**Status:** Production Ready (15 skills, 19 scripts, 5 agents, 25 commands, 10 HTTP connectors, 0 global hooks)

Agency-grade social media calendar automation with asset-first compositing and AI video generation. Takes monthly content calendars, matches brand assets, generates AI-composed creative, renders carousels, produces AI-generated video clips, adapts copy per platform, produces review galleries and delivery documents.

## Core Principle

**Brand assets are sacred. AI is the creative layer around them.**

Product photos, headshots, screenshots — these are the brand’s real visual identity. AI generates backgrounds, mood, and context around them. The brand asset stays pixel-faithful in every composition.

## The Four Creative Modes

| Mode | When | What Happens |
|------|------|-------------|
| ANCHOR_COMPOSE | Brand photo is the centerpiece | AI generates scene around the untouched asset |
| ENHANCE_EXTEND | Brand photo is the base | AI extends/enhances periphery, core stays faithful |
| STYLE_REFERENCED | No specific asset needed | AI generates using brand’s style reference photos as visual DNA |
| PURE_CREATIVE | Generic/abstract content | AI generates from text prompt + brand colors/mood |

## Quick Start

```
1. /socialforge:brand-setup [brand-name]    — Configure brand (5-10 min)
2. /socialforge:index-assets [brand-name]   — Index brand photo library
3. /socialforge:new-month [brand] [YYYY-MM] — Start monthly production
4. /socialforge:generate-all                — Produce all creative
5. /socialforge:review                      — Review and approve
6. /socialforge:finalize                    — Package for delivery
```

## Architecture

- **15 skills** — Calendar parsing, asset indexing, creative composition, copy adaptation, review management
- **25 commands** — Monthly production, post generation, editing, review, approval, finalization
- **5 agents** — Image compositor, carousel builder, copy adapter, quality reviewer, compliance checker
- **19 scripts** — Deterministic execution (compositing, rendering, resizing, video post-processing, compliance checking)
- **10 HTTP connectors** — Notion, Canva, Slack, Gmail, Google Calendar, Figma, fal.ai, Replicate, Asana, Cloudinary (all Cowork-compatible)
- **0 global hooks** — As of v1.5.0. Prior hook config preserved at `hooks/hooks-reference.example.json`. Credential status now via `/socialforge:status` on demand. See [Current Release](#current-release-v180) for the rationale.

## Installation

### Option A: From Marketplace (recommended)
```
/plugin marketplace add indranilbanerjee/neels-plugins
/plugin install socialforge@neels-plugins
```

### Option B: Direct from GitHub
```
claude plugins add github:indranilbanerjee/socialforge
```

### Option C: From Local Directory
```
claude plugins add /path/to/socialforge
```

## First-Time Setup (Required)

After installing the plugin, run the setup command in Claude Code:

```
/socialforge:setup
```

This configures two external API services that power SocialForge’s image and video generation:

1. **Google Cloud Vertex AI** — Used for AI image generation (Gemini Nano Banana 2 / Pro models)
2. **WaveSpeed** — Used for AI video generation (Kling v3.0 Pro model)

Your admin provides you with:
- A **Google Cloud service account JSON key file** (for Vertex AI image generation)
- A **WaveSpeed API key** (for video generation)

`/socialforge:setup` copies these credentials to persistent storage (`${CLAUDE_PLUGIN_DATA}`), so they work across all sessions automatically. You only need to run it once.

**Without running `/socialforge:setup`, image and video generation will not work.** All other SocialForge features (calendar parsing, copy adaptation, review galleries, etc.) function normally without it.

### Updating to Latest Version

**Third-party marketplaces — including this one — have auto-update OFF by default in Claude Code.** When v1.6.0 is the marketplace's latest and you're still on v1.5.3, nothing tells you. There is no banner, no badge, no notification.

**Option 1 (recommended) — turn auto-update on, once:**

Open `/plugin`, go to the **Marketplaces** tab, find `neels-plugins`, and toggle **Enable auto-update**. From then on, Claude Code refreshes the catalog at startup and pulls new SocialForge releases automatically. After an auto-update fires, run `/reload-plugins` when prompted to apply changes mid-session — no full restart, conversation context preserved.

**Option 2 — manual update each time:**

```
/plugin marketplace update neels-plugins
/plugin uninstall socialforge@neels-plugins
/plugin install socialforge@neels-plugins
/reload-plugins
```

`/plugin marketplace update` only refreshes the catalog — it does not bump installed plugin versions. The uninstall + reinstall is what actually pulls the new version.

**Force-reinstall (version unchanged but content changed):**

```
rm -rf ~/.claude/plugins/cache/neels-plugins
/plugin install socialforge@neels-plugins
/reload-plugins
```

### Installs in Cowork

Cowork is the Anthropic Desktop computer-use product (macOS/Windows). It supports third-party plugins from custom marketplaces — same `/plugin marketplace add indranilbanerjee/neels-plugins` install pattern. Cowork has local filesystem access, so the full SocialForge pipeline including all 19 Python scripts (image generation, video generation, ffmpeg postprocessing, C2PA signing) runs natively. The only Cowork-specific limitation is **HTTP MCPs only** (no stdio/npx) — SocialForge's 10 connectors are all HTTP and fully Cowork-compatible.

### Pre-Requisites for Image Generation

SocialForge uses **Google Cloud Vertex AI** for image generation. Without it, image generation will fail (it will NOT silently create placeholders).

**Setup via /socialforge:setup (recommended):**
1. Your admin provides a Google Cloud service account JSON key file with Vertex AI access
2. Run `/socialforge:setup` and point it to the JSON key file
3. Credentials are stored persistently — no need to set environment variables manually

**Alternative — Direct environment variable:**
If you prefer manual configuration, set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to your service account JSON file:
```
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

**Alternative — fal.ai or Replicate:** Connect via Connectors panel after installation for third-party image generation.

Run `/socialforge:status` to verify image and video generation credentials are configured. (As of v1.5.0, credential status is reported on demand instead of via a SessionStart banner that fired on every Claude Code launch in every project.)

## Admin Setup (One-Time)

Admins configure the cloud accounts once. Team members then just run `/socialforge:setup` with the credentials the admin shares.

### Google Cloud (Vertex AI — Image Generation)

#### Step 1: Create a Google Cloud Project
1. Open https://console.cloud.google.com/
2. If you don’t have an account, click "Get started for free" and follow registration
3. Click the project dropdown at the top of the page (next to "Google Cloud")
4. Click "NEW PROJECT"
5. Enter a project name (e.g., "socialforge-production")
6. Click "CREATE"
7. Wait for the project to be created (30 seconds), then select it from the dropdown

#### Step 2: Enable Billing
1. Go to https://console.cloud.google.com/billing
2. Click "LINK A BILLING ACCOUNT"
3. If you don’t have a billing account, click "CREATE BILLING ACCOUNT"
4. Add a payment method (credit card)
5. New accounts get $300 free credits for 90 days

#### Step 3: Enable Vertex AI API
1. Go to https://console.cloud.google.com/apis/library
2. Search for "Vertex AI API"
3. Click on it, then click "ENABLE"
4. Wait for it to activate (takes a few seconds)

#### Step 4: Create a Service Account
1. Go to https://console.cloud.google.com/iam-admin/serviceaccounts
2. Click "+ CREATE SERVICE ACCOUNT"
3. Service account name: `socialforge-image-gen`
4. Description: `SocialForge AI image generation`
5. Click "CREATE AND CONTINUE"
6. In "Grant this service account access to project":
   - Click the "Select a role" dropdown
   - Type "Vertex AI User" in the search box
   - Select "Vertex AI User"
7. Click "CONTINUE", then "DONE"

#### Step 5: Download the JSON Key File
1. In the service accounts list, click on `socialforge-image-gen`
2. Go to the "KEYS" tab
3. Click "ADD KEY" then "Create new key"
4. Select "JSON" and click "CREATE"
5. A .json file downloads automatically — this is your credential file
6. Save it somewhere safe on your computer

#### Step 6: Share with Your Team
Share the downloaded JSON file with your team via:
- Slack DM (not in a public channel)
- Email (encrypted if possible)
- Shared company drive (restricted access)

NEVER commit this file to Git. NEVER share it publicly.

**Cost:** Image generation costs approximately $0.01-0.04 per image depending on resolution and model. All costs go to the admin’s billing account.

### WaveSpeed (Kling v3.0 — Video Generation)

#### Step 1: Create a WaveSpeed Account
1. Open https://wavespeed.ai
2. Click "Sign Up" and create an account
3. Verify your email

#### Step 2: Add Credits
1. After logging in, go to your dashboard
2. Click "Top Up" or navigate to billing
3. Add credits (minimum top-up required to activate API access)
4. Pricing: approximately $0.08-0.11 per second of video
   - A 5-second video costs roughly $0.40-0.56
   - A 10-second video costs roughly $0.84-1.12

#### Step 3: Create an API Key
1. Go to https://wavespeed.ai/accesskey
2. Click "Create API Key"
3. Copy the key (it’s a long string of letters and numbers)
4. Save it somewhere safe

#### Step 4: Share with Your Team
Share the API key string with your team via:
- Slack DM
- Password manager (recommended)
- Email (encrypted if possible)

NEVER commit this key to Git or paste it in public forums.

**Cost:** All video generation costs go to the admin’s WaveSpeed account. Monitor usage at https://wavespeed.ai/dashboard

### HiggsField (Optional Fallback — Video + Image)

HiggsField provides additional resilience. If both Vertex AI and WaveSpeed are down, HiggsField can generate images and videos.

#### Step 1: Create a HiggsField Account
1. Open https://higgsfield.ai
2. Click "Sign Up" and create an account
3. New accounts get 150 free credits

#### Step 2: Get API Credentials
1. Go to https://cloud.higgsfield.ai/api-keys
2. Create a new API key pair — you’ll get an API Key AND an API Secret
3. Save both values

#### Step 3: Share with Your Team
Share both the API key AND secret with your team. Both are needed for authentication.

### What Team Members Do

Team members do NOT need any cloud accounts. The admin shares credentials, and the team member runs:

```
/socialforge:setup
```

The setup wizard asks for:
1. Path to the Google Cloud JSON file (for images) — paste the file path
2. WaveSpeed API key (for video) — paste the key
3. HiggsField credentials (optional) — paste key and secret if provided

Credentials are stored in the plugin’s persistent data directory. They survive across sessions, restarts, and plugin updates.

**Where credentials are stored per platform:**
- Windows: `%APPDATA%\Claude\plugins\data\socialforge-neels-plugins\socialforge\`
- macOS: `~/Library/Application Support/Claude/plugins/data/socialforge-neels-plugins/socialforge/`
- Linux: `~/.config/Claude/plugins/data/socialforge-neels-plugins/socialforge/`

Or if using the fallback workspace: `~/socialforge-workspace/`

## Video Generation

SocialForge produces short-form AI-generated video clips for video content posts (Reels, TikTok, Shorts, etc.).

### Pipeline

1. **Post context** — The calendar post’s theme, copy, and visual direction inform the video
2. **Script generation** — AI writes a short video script with scene descriptions
3. **Keyframe generation** — Gemini (via Vertex AI) generates the first and last frame as keyframe images
4. **Video animation** — WaveSpeed sends the keyframes to **Kling v3.0 Pro** (image-to-video), which animates them into a fluid video clip (3-15 seconds)

### Models

| Component | Model | Provider |
|-----------|-------|----------|
| Keyframe images | Gemini Nano Banana 2 / Pro | Google Cloud Vertex AI |
| Image-to-video | Kling v3.0 Pro | WaveSpeed |

### Post-Processing

After generation, videos are automatically post-processed with:
- **Brand logo watermark** overlay
- **Platform-specific resizing** (9 platform dimensions, no stretching)
- **Optional subtitle burning** (user approves — SRT with brand fonts)
- **Optional background music** (user approves — mixed at appropriate levels)

Post-processing is powered by ffmpeg, auto-installed via the `imageio-ffmpeg` Python package.

### Human-in-the-Loop

All video generation goes through human-in-the-loop approval. Videos are generated, previewed in the review gallery, and require explicit approval before finalization. Nothing ships without sign-off.

### Requirements

- WaveSpeed API key configured via `/socialforge:setup`
- Google Cloud Vertex AI credentials configured via `/socialforge:setup` (for keyframe generation)
- Python dependencies: `pip install google-genai wavespeed Pillow imageio-ffmpeg`
- Video duration: 3-15 seconds per clip

Use `/socialforge:generate-video` to produce video for a specific post, or `/socialforge:generate-all` to include video posts in batch production.

## Connectors

SocialForge ships with **10 HTTP connectors** that work in both Cowork and Claude Code:
Notion, Canva, Slack, Gmail, Google Calendar, Figma, fal.ai, Replicate, Asana, Cloudinary.

The plugin works fully without connectors — all skills, agents, and creative production function with local assets and AI generation APIs.

## Storage

Brand configs and asset indexes persist across sessions via `${CLAUDE_PLUGIN_DATA}`. Asset images stay in Google Drive, Cloudinary, or local folders. See the [User Guide](docs/USER-GUIDE.md#11-where-your-data-lives) for details.

## Current Release (v1.8.0)

**Install-surface expansion to 5 platforms.** SocialForge now installs cleanly on Claude Code + Cowork (canonical), OpenAI Codex, Cursor, **GitHub Copilot CLI** (no new manifest — Copilot CLI auto-discovers `.claude-plugin/plugin.json` as one of its accepted manifest paths; install: `copilot plugin install indranilbanerjee/socialforge`), and **Google Antigravity 2.0** (experimental `.antigravity/plugin.json` mirroring the Gemini-CLI-extensions importer format Antigravity's `agy plugin import gemini` accepts; will be updated against the v2-native spec when Google publishes it). Single `skills/`, single `scripts/`, single MCP catalog. Full per-platform install guide at [`docs/CROSS-PLATFORM-GUIDE.md`](docs/CROSS-PLATFORM-GUIDE.md). No breaking changes for existing Claude Code users.

### Earlier (v1.7.0)

**Cross-platform compatibility pack.** SocialForge added native manifests for **OpenAI Codex** and **Cursor** alongside the canonical Claude Code manifest, via two new sibling manifest files (`.codex-plugin/plugin.json` and `.cursor-plugin/plugin.json`) — same `skills/` directory, same `scripts/`, same `.mcp.json`, same `hooks/hooks.json`. Works because Agent Skills are an open standard (Dec 2025).

### Earlier (v1.6.0)

**EU AI Act Article 50 readiness** (applicable 2 Aug 2026). New `scripts/c2pa_sign.py` wraps `c2pa-python>=0.32` to embed machine-readable provenance manifests in AI-generated assets — brand (CreativeWork.author), generator name, prompt, target platform, IPTC digital-source-type. New `/socialforge:c2pa-sign` skill exposes it. Optional `--c2pa-sign` flag on `generate_image.py` (post-image-generation step) and `video_postprocess.py` (post-per-platform-resize step) auto-signs before delivery. Empirically tested: 75-byte test PNG → ~43 KB signed PNG with `manifest_embedded_and_verified=true`. Production deployment requires a CAI-recognized signing certificate (Adobe Content Credentials, Truepic, Numbers Protocol, or Microsoft Azure Confidential Ledger) — see `references/c2pa-production-cert.md`.

**May 2026 channel pack** added at `references/channel-changes-may-2026.md` — TikTok USDS Joint Venture (post-Jan 22 2026; AI creator labeling mandatory, AI content excluded from Creator Rewards Program, daily shoppable-post limits May 11 2026), LinkedIn March 12 2026 algorithm + Depth Score (external links and engagement bait penalized ~60%), Apple MPP affects ~64% of B2C opens (open rate dropped as primary KPI), YouTube AI Shorts labeling, Sora deprecation timeline (consumer app 26 Apr 2026, API 24 Sep 2026 → default to Runway Gen-4 / Veo 3.x / Kling 3.0). Third-party cookies deprecation cancelled.

**Engineering spec correction** — SOCIALFORGE-COMPLETE-ENGINEERING-SPEC.md section 16.3: Sora 2 row marked DEPRECATED; Runway Gen-4 and Kling 3.0 Omni added as replacements.

**README correctness** — Updating section rewritten to mirror DMP/CF pattern; explicit two-option flow since third-party marketplaces have auto-update OFF by default in Claude Code; new "Installs in Cowork" subsection clarifying that the full SF pipeline including all 20 Python scripts runs natively in Cowork.

### Earlier (v1.5.x)

v1.5.0 removed all 4 global hooks (SessionStart credential banner, PreToolUse Write/Edit compliance check, SubagentStart brand-context injection, Stop image-approval verification) that previously fired on every Claude Code operation in every project. Credential status reported on demand via `/socialforge:status`. v1.5.1 hardened the plugin manifest. v1.5.2 fixed manifest install format. v1.5.3 swept all `/sf:` shorthand to canonical `/socialforge:` across ~200 references.

### Earlier (v1.3–1.4)

100% spec coverage. Persistent storage via `${CLAUDE_PLUGIN_DATA}`, Google Drive asset source, Cloudinary DAM, Veo 3.1 video generation, edge feathering, color temp matching, PDF carousel assembly, Instagram first-comment strategy, bilingual copy support.

## Documentation

- **[User Guide](docs/USER-GUIDE.md)** — Complete walkthrough from setup to delivery (with real agency examples)
- **[Cross-Platform Guide](docs/CROSS-PLATFORM-GUIDE.md)** — Use SocialForge on Codex, Cursor, Gemini CLI, Copilot, Windsurf
- **[Technical Operations](docs/OPERATIONS.md)** — Pipeline logic, scoring algorithms, AI models, folder structures, cost tracking
- **[Connectors](CONNECTORS.md)** — All 10 MCP connectors + storage architecture
- **[Testing Guide](TESTING-GUIDE.md)** — Full test plan with checklists
- **[Contributing](CONTRIBUTING.md)** — How to contribute to SocialForge
- **[Troubleshooting](references/troubleshooting.md)** — Common issues and fixes
- **[Changelog](CHANGELOG.md)** — Release history

## Neelverse Marketing Suite

SocialForge is part of the **Neelverse Marketing Suite** — three plugins that work together for end-to-end marketing:

| Plugin | What It Does | Install |
|--------|-------------|---------|
| **[Digital Marketing Pro](https://github.com/indranilbanerjee/digital-marketing-pro)** | End-to-end engagement methodology — 12-Part Strategy Flow, Four Core Documents, Two-Views Model. 149 skills, 25 agents, 10 commands, 14 HTTP connectors | `claude plugin install digital-marketing-pro@neels-plugins` |
| **[ContentForge](https://github.com/indranilbanerjee/contentforge)** | Publication-ready content via 10-phase pipeline — research, draft, fact-check, SEO, humanize | `claude plugin install contentforge@neels-plugins` |
| **SocialForge** (this plugin) | Social media calendar automation with AI image + video generation (Vertex AI + Kling v3.0) | `claude plugin install socialforge@neels-plugins` |

**Use together:** Plan campaigns in DM Pro, produce articles with ContentForge, create social visuals and videos with SocialForge. All share the same brand profiles and marketplace.

```
claude plugin marketplace add indranilbanerjee/neels-plugins
claude plugin install digital-marketing-pro@neels-plugins
claude plugin install contentforge@neels-plugins
claude plugin install socialforge@neels-plugins
```

## License

MIT
