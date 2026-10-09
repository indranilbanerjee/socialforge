# SocialForge — Social Media Calendar Automation

> **Your client wants 30 days of social content across six platforms with brand-faithful imagery, AI-generated video, and provenance signed for EU markets. You have five days. The last calendar got rejected because the product photo got "AI-enhanced" beyond recognition.**

Run `/socialforge:new-month` → `/socialforge:generate-all` → `/socialforge:review`. Asset-first compositing keeps brand photos pixel-faithful while AI generates the scene around them. Per-platform copy adaptation handles Instagram + TikTok + LinkedIn + Threads + X + Facebook + YouTube Shorts in one pass. C2PA signing happens before review. No more "AI enhanced our logo into something else" disasters.

Open-source agency-grade social media production engine — **21 skills · 18 commands · 5 agents · 30 scripts · an opt-in catalog of 12 HTTP connectors (zero auto-connected) · 0 global hooks**. AI image (Vertex AI) and AI video (WaveSpeed), with models resolved live rather than hardcoded, and human-in-the-loop review galleries. Built for agencies and in-house teams running monthly content calendars. Installs on **Claude Code** (CLI + IDE), **Anthropic Cowork**, **OpenAI Codex**, **Cursor 2.5+**, **GitHub Copilot CLI**, **Google Antigravity 2.0**, **Hermes Agent**, **OpenClaw**, and **Grok** + 35+ Agent Skills platforms. Created by [Indranil Banerjee](https://indranil.in) · [LinkedIn](https://www.linkedin.com/in/askneelnow/) · [X](https://x.com/askneelnow).

[![Version](https://img.shields.io/badge/version-1.29.0-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/indranilbanerjee/socialforge?style=flat&logo=github&color=yellow)](https://github.com/indranilbanerjee/socialforge/stargazers)
[![Forks](https://img.shields.io/github/forks/indranilbanerjee/socialforge?style=flat&logo=github&color=blue)](https://github.com/indranilbanerjee/socialforge/network/members)
[![Issues](https://img.shields.io/github/issues/indranilbanerjee/socialforge?logo=github)](https://github.com/indranilbanerjee/socialforge/issues)
[![Last commit](https://img.shields.io/github/last-commit/indranilbanerjee/socialforge?logo=github)](https://github.com/indranilbanerjee/socialforge/commits/main)
[![Tests](https://img.shields.io/badge/tests-496%2F496%20passing-brightgreen.svg)](tests/)
[![Platforms](https://img.shields.io/badge/platforms-9%20native%20%2B%2035%20Agent%20Skills-success.svg)](#supported-surfaces-v1290)
[![Cowork](https://img.shields.io/badge/cowork-compatible-purple.svg)](#supported-surfaces-v1290)
[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Article%2050%20ready-darkred.svg)](references/c2pa-production-cert.md)
[![Sponsor](https://img.shields.io/badge/sponsor-%E2%9D%A4-ea4aaa?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/indranilbanerjee)

> 🆕 **Just shipped — v1.29.0 (October 10, 2026): nothing installs itself, keys stay out of the chat, and paid generation waits for a quote.** Reviewed for the Hermes Agent plugin catalog, SocialForge now never installs a Python package or a browser on its own (`scripts/install_deps.py` reports and prints pinned commands; `--install` is your go-ahead), setup takes API keys from your environment instead of the chat or the command line, `compose-creative`, `generate-video` and batch `full-pipeline` quote the run with `price_book.py` and wait for an explicit `go` before any paid call, and `--brand` / `--month`, provider URLs and slide text can no longer reach a path, a `file://` download or the page markup. **If you relied on the automatic install, run `python scripts/install_deps.py --install` once.**
>
> Previously — **v1.28.1 (October 10, 2026): the listing figures now count the workflow.** v1.28.0's numbers left out the `month-copy-preview` workflow, which Claude Code lists to the model like a skill; counted, SocialForge's listing went from 10,525 to 4,927 characters (not 10,305 to 4,745). `month-copy-preview` now follows the same 60-150 character rule, and the guard reads workflows. **v1.28.0 (October 9, 2026): every skill now reaches the model, and finalizing asks first.** Claude Code lists skills in a budget measured in characters, and SocialForge's descriptions were long enough that many were cut before the model saw them. They are now less than half the size: each says what the skill does, how it differs from its neighbour, and one phrase you would type. "Package the month for the client" and "show me how this will look" reached their skills only through a wrapper command, because the skills were hidden; each now has one visible entry that shows the scope and waits for your `yes`. Measured with trigger evals: nothing that worked before stopped working.
>
> Older releases: [CHANGELOG.md](CHANGELOG.md)

```bash
# Install in Claude Code:
/plugin marketplace add indranilbanerjee/neels-plugins
/plugin install socialforge@neels-plugins

# Install on Hermes Agent (Nous Research):
hermes plugins install indranilbanerjee/socialforge

# Install on OpenClaw:
openclaw plugins install git:github.com/indranilbanerjee/socialforge

# Install on Grok (xAI Build CLI):
grok plugin install indranilbanerjee/socialforge
```

> If SocialForge saves your team time, [give it a star ⭐](https://github.com/indranilbanerjee/socialforge/stargazers) — it's the single thing that helps other agencies find it.

**Status:** Production Ready · 21 skills · 18 commands · 5 agents · 30 scripts · an opt-in catalog of 12 HTTP connectors (zero auto-connected) · 0 global hooks

Agency-grade social media calendar automation with asset-first compositing and AI video generation. Takes monthly content calendars, matches brand assets, generates AI-composed creative, renders carousels, produces AI-generated video clips, adapts copy per platform, produces review galleries and delivery documents — with C2PA content provenance signed into every AI-generated image/video before delivery.

## Try this first

Install, run the one-time setup, then ask in plain words. Each of these kinds of request reached the right skill in our trigger tests.

| You type | What happens |
|---|---|
| "load this month's calendar" | Your calendar (DOCX, XLSX, Notion or pasted text) parsed into structured posts |
| "make the visual for this post" | The creative for one post: your brand photos kept faithful, AI image or video where needed, quoted before any paid call |
| "rewrite this caption for LinkedIn" | Copy adapted to the platform: character limits, hashtags, tone and the right call to action |
| "show how this will look" | Post mockups for LinkedIn, Instagram, X and TikTok; it shows the scope and waits for your `yes` |
| "produce the whole month" | The full pipeline from calendar to delivery, pausing between phases |
| "package the month for the client" | The delivery folder with copy files and a manifest, after a delivery audit; it waits for your `yes` |

### What SocialForge will never do

- **Spend on image or video generation before you see the price.** It quotes each paid item from a live price lookup and waits for "go"; anything else cancels.
- **Install a package or a browser on its own.** Setup shows what is missing and installs only when you say so.
- **Ask for an API key in the chat.** Keys come from environment variables.
- **Package or send the month without your `yes`,** and never before the client review.
- **Connect a service you did not set up.** No MCP server ships enabled and no hooks run.
- **Remove or hide AI watermarks.** AI involvement is disclosed, with C2PA provenance.

## Core Principle

**Brand assets are sacred. AI is the creative layer around them.**

Product photos, headshots, screenshots — these are the brand’s real visual identity. AI generates backgrounds, mood, and context around them. The brand asset stays pixel-faithful in every composition.

## How a month runs

![A SocialForge month: optional research and ideation, then parse the calendar, match brand assets (you confirm), quote the paid generation and wait for go, compose the creative, adapt the copy per platform with a compliance check, render previews, build the review gallery, pause for client review, and finalize with a delivery audit](docs/assets/month-pipeline.svg)

The amber steps are yours: nothing is spent before the quote is approved, and nothing is packaged before the client review.

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

> **Claude answers in chat instead of using a SocialForge skill?** Claude Code lists every installed skill in a budget of 1% of the context window. On a 200k window with several plugins installed, only skill names fit, so Claude can't see what each skill does. Add `"skillListingBudgetFraction": 0.05` to your Claude Code `settings.json`, or start a skill by name, e.g. `/socialforge:full-pipeline`.

## Supported surfaces (v1.29.0)

| Platform | Install command | Manifest path | Status |
|---|---|---|---|
| **Claude Code** CLI + IDE extensions | `/plugin install socialforge@neels-plugins` | `.claude-plugin/plugin.json` | Full support (canonical) |
| **Anthropic Cowork** | Plugins UI → Add marketplace → `indranilbanerjee/neels-plugins` → Install SocialForge | same `.claude-plugin/` files | Full support — no `/plugin` slash commands in Cowork (UI-only) |
| **OpenAI Codex** CLI + IDE + App | `codex plugin marketplace add indranilbanerjee/neels-plugins` then `codex plugin add socialforge@neels-plugins` | `.codex-plugin/plugin.json` (published OpenAI schema) | Full skills + MCP support |
| **Cursor 2.5+** | In any Cursor Agent chat: `/add-plugin socialforge@https://github.com/indranilbanerjee/socialforge` | `.cursor-plugin/plugin.json` (verified Cursor 2.5+ JSON Schema) | Full skills + agents + commands support |
| **GitHub Copilot CLI** | `copilot plugin marketplace add indranilbanerjee/neels-plugins` then `copilot plugin install socialforge@neels-plugins` | `.github/plugin/plugin.json` (Copilot also recognizes `.claude-plugin/plugin.json` as fallback) | Full skills + MCP support |
| **Google Antigravity 2.0** CLI + IDE | `agy plugin install https://github.com/indranilbanerjee/socialforge` | `gemini-extension.json` (at repo root, per Google's reference pattern) | Full skills + hooks support |
| **Hermes Agent** (Nous Research) — Desktop + CLI on macOS / Windows / Linux | `hermes plugins install indranilbanerjee/socialforge` | `plugin.yaml` + `__init__.py` at repo root (Hermes native spec) | Native plugin — adapter walks `skills/` at register time and exposes all 21 skills via `ctx.register_skill()`. Targets Hermes Desktop v0.15.2+ (public preview June 2 2026). |
| **OpenClaw** (formerly Clawdbot / Moltbot) | `openclaw plugins install git:github.com/indranilbanerjee/socialforge` | `openclaw.plugin.json` at repo root (also auto-detects `.claude-plugin/plugin.json` as Claude-compatible bundle) | Native plugin via `openclaw.plugin.json`; `skills` field points at `./skills`. |
| **Grok** (xAI Build CLI) | `grok plugin install indranilbanerjee/socialforge` — or `grok plugin marketplace add indranilbanerjee/neels-plugins` then `grok plugin install socialforge` (append `--trust` to skip the install confirmation) | `.grok-plugin/plugin.json` + `.grok-plugin/marketplace.json` ([Grok Build](https://docs.x.ai/build/features/skills-plugins-marketplaces) also reads the Claude Code manifests for compatibility; the native pair is the first-class lane) | Full skills support |

**Why this works:** Agent Skills became an open standard in December 2025 (41+ agent products by June 2026). All 21 SKILL.md files in SocialForge are platform-portable as written.

**Works on 35+ additional Agent Skills platforms** without per-platform manifests — Goose (Block), OpenHands, OpenCode (sst), Junie (JetBrains), Gemini CLI, Roo Code, Cline/Windsurf, Kiro, Amp, Letta, Mux, Factory, Workshop, Tabnine, Mistral Vibe, and more. Point any Agent-Skills-compatible client at `https://github.com/indranilbanerjee/socialforge/tree/main/skills` and all 21 SocialForge skills are immediately discoverable.

## Architecture

- **21 skills** — Calendar parsing, asset indexing, creative composition, copy adaptation, review management, C2PA signing
- **18 commands** — Monthly production, post generation, editing, review, approval, finalization
- **5 agents** — Image compositor, carousel builder, copy adapter, quality reviewer, compliance checker
- **30 scripts** — Deterministic execution (compositing, rendering, resizing, video post-processing, compliance checking, C2PA signing)
- **An opt-in catalog of 12 HTTP connectors** (zero auto-connected; enable from `.mcp.json.connectors-reference`) — Notion, Canva, Slack, Gmail, Google Calendar, Figma, fal.ai, Replicate, Asana, Cloudinary, Postiz (scheduler hand-off after finalize, only on your approval of the exact posts and times), and WhatsApp Business Tools (Meta beta, for development and testing)
- **0 global hooks** — As of v1.5.0. Prior hook config preserved at `hooks/hooks-reference.example.json`. Credential status now via `/socialforge:status` on demand. See the [release notes](#current-release-v1290) for the rationale.
- **Model curator (v1.8.2+)** — `scripts/model_registry.json` + `resolve_model.py` + `refresh_models.py`. Single source of truth for image / vision / video model ids; deprecated ids passed via `--model` / `--video-model` auto-fall-forward to their replacement; `refresh_models.py` polls live provider catalogs and reports drift. See [`docs/MODEL-CURATOR.md`](docs/MODEL-CURATOR.md).

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

1. **Google Cloud Vertex AI** — Used for AI image generation (the current Google image model, resolved live through the `latest-image-google` alias)
2. **WaveSpeed** — Used for AI video generation (the current Kling image-to-video model, resolved live through the `latest-video-wavespeed` alias)

Your admin provides you with:
- A **Google Cloud service account JSON key file** (for Vertex AI image generation)
- A **WaveSpeed API key** (for video generation)

`/socialforge:setup` copies these credentials to persistent storage (`${CLAUDE_PLUGIN_DATA}`), so they work across all sessions automatically. You only need to run it once.

**Without running `/socialforge:setup`, image and video generation will not work.** All other SocialForge features (calendar parsing, copy adaptation, review galleries, etc.) function normally without it.

### Updating to Latest Version

> **If you see "/plugin isn't available in this environment"** — you're in the standard **Claude chat app** (browser OR installed desktop app). The `/plugin` slash command is **only** supported in two environments: **Claude Code** (the developer CLI / IDE at [claude.com/code](https://claude.com/code), `npm install -g @anthropic-ai/claude-code`) and **Anthropic Cowork**. Everywhere else — `claude.ai` web chat, the Claude Desktop app, mobile — plugins are managed through the UI, not slash commands.
>
> The plugin IS installed (your SocialForge skills work); only the management command is unavailable. Fix:
>
> 1. **In the chat UI** — click the **Plugins** button at the bottom of the chat → **Manage plugins** → find SocialForge → look for Update / Refresh / Remove. If no Update button, **Remove** then **Add plugin** → re-install from `indranilbanerjee/neels-plugins`. The re-pull fetches the latest version.
> 2. **For slash-command management** — switch to Claude Code (CLI or IDE) or Cowork. The plugin runs identically across every Anthropic surface; you're choosing where to type management commands.
>
> Once you're in Claude Code or Cowork, the rest of this section applies.

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

**Force-reinstall (version unchanged but content changed):** delete the folder `~/.claude/plugins/cache/neels-plugins` (it holds only downloaded plugin copies), then:

```
/plugin install socialforge@neels-plugins
/reload-plugins
```

### Installs in Cowork

Cowork is the Anthropic Desktop computer-use product (macOS/Windows). It supports third-party plugins from custom marketplaces — same `/plugin marketplace add indranilbanerjee/neels-plugins` install pattern. Cowork has local filesystem access, so the full SocialForge pipeline including all 30 Python scripts (image generation, video generation, ffmpeg postprocessing, C2PA signing) runs natively. The only Cowork-specific limitation is **HTTP MCPs only** (no stdio/npx) — SocialForge's 10 connectors are all HTTP and fully Cowork-compatible.

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

**Cost:** Image generation is billed per image to the admin’s Google Cloud account. The price depends on the model and resolution and changes over time, so SocialForge stores no prices: before any paid run it quotes the planned generations from a live lookup (with the source URL and the price’s age) and waits for your `go`.

### WaveSpeed (Video Generation)

#### Step 1: Create a WaveSpeed Account
1. Open https://wavespeed.ai
2. Click "Sign Up" and create an account
3. Verify your email

#### Step 2: Add Credits
1. After logging in, go to your dashboard
2. Click "Top Up" or navigate to billing
3. Add credits (minimum top-up required to activate API access)
4. Pricing: WaveSpeed bills per second of video and the rate depends on the model. SocialForge quotes it from a live lookup (source URL and the price’s age shown) before every paid run and waits for your `go`.

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

#### Step 2: Get API Credentials
1. Log in at https://cloud.higgsfield.ai and open the API / Developer section of your dashboard
2. Create a new API key pair — you'll get an API Key AND an API Secret
3. Save both values

#### Step 3: Share with Your Team
Share both the API key AND secret with your team. Both are needed for authentication.

### What Team Members Do

Team members do NOT need any cloud accounts. The admin shares credentials, and the team member runs:

```
/socialforge:setup
```

The setup wizard first lists the Python packages that are missing and the exact pinned install command for each; it installs them only after you say `yes`. Then it asks for:
1. Path to the Google Cloud JSON file (for images) — give the file path
2. WaveSpeed API key (for video) — set `WAVESPEED_API_KEY` in your environment and say when it is set; never paste the key into the chat
3. HiggsField credentials (optional) — set `HF_API_KEY` and `HF_API_SECRET` the same way

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
3. **Keyframe generation** — the image model (via Vertex AI) generates the first and last frame as keyframe images
4. **Video animation** — WaveSpeed's image-to-video model animates the approved first frame into a fluid video clip (3-15 seconds) and, when that provider makes the clip, steers it toward the approved last frame (see [The last frame](#the-last-frame))

### Models

Models are resolved at run time through the model registry, so no version is written here — a version in a README is wrong on a timetable nobody controls.

| Component | Registry alias | Provider |
|-----------|----------------|----------|
| Keyframe images | `latest-image-google` | Google Cloud Vertex AI |
| Image-to-video | `latest-video-wavespeed` | WaveSpeed |

See which model each alias resolves to today with `python scripts/generate_video.py --list-models` (or `python scripts/resolve_model.py --aliases` for every alias).

### The last frame

`generate_video.py --last-image <path>` sends the approved last frame to the WaveSpeed rung as the clip's end image, so the clip is guided toward it. That rung is the only one with an end-frame input. With `--provider auto`, a supplied last frame makes the chain try that rung first. If another rung made the clip instead — because `--provider` named it, or the WaveSpeed key was missing or the call failed — the result says `last_frame_used: false` with a note, and the clip was **not** steered to the approved frame. Pass `--provider kling` when the clip must end on it. A `--last-image` path that does not exist is an error, never silently dropped.

### Post-Processing

After generation, videos are automatically post-processed with:
- **Brand logo watermark** overlay
- **Platform-specific resizing** (9 platform dimensions, no stretching)
- **Optional subtitle burning** (user approves — SRT with brand fonts)
- **Optional background music** (user approves — mixed at appropriate levels)

Post-processing is powered by ffmpeg, provided by the pinned `imageio-ffmpeg` Python package (`scripts/install_deps.py` prints the install command; nothing installs itself).

### Human-in-the-Loop

All video generation goes through human-in-the-loop approval. Videos are generated, previewed in the review gallery, and require explicit approval before finalization. Nothing ships without sign-off.

### Requirements

- WaveSpeed API key configured via `/socialforge:setup`
- Google Cloud Vertex AI credentials configured via `/socialforge:setup` (for keyframe generation)
- Python packages: `/socialforge:setup` lists what is missing and prints the exact pinned install command for each; it installs only after you say yes (`python scripts/install_deps.py` prints the same report)
- Video duration: 3-15 seconds per clip

Use `/socialforge:generate-video` to produce video for a specific post, or `/socialforge:generate-all` to include video posts in batch production.

## Connectors

SocialForge ships **an opt-in catalog of 12 HTTP connectors** that work in both Cowork and Claude Code — zero are auto-connected. no `.mcp.json` ships (it is gitignored), by design; to enable one, create a `.mcp.json` containing the entries you want from `.mcp.json.connectors-reference`:
Notion, Canva, Slack, Gmail, Google Calendar, Figma, fal.ai, Replicate, Asana, Cloudinary, Postiz, WhatsApp Business Tools (Meta beta).

The plugin works fully without connectors — all skills, agents, and creative production function with local assets and AI generation APIs.

## Storage

Brand configs and asset indexes persist across sessions via `${CLAUDE_PLUGIN_DATA}`. Asset images stay in Google Drive, Cloudinary, or local folders. See the [User Guide](docs/USER-GUIDE.md#13-where-your-data-lives) for details.

## Current Release (v1.29.0)

**v1.29.0:** nothing installs itself, keys stay out of the chat, paid generation waits for a quote. Fixes every point of a Hermes Agent catalog review: `install_deps.py` reports by default and installs only with `--install` (exact pins; the optional packages left the defaults); setup asks before installing and takes keys from the environment; c2pa signing raises a clear error instead of installing mid-run or exiting after a paid call; `compose-creative`, `generate-video` and batch `full-pipeline` quote with `price_book.py` and wait for `go`; `status_manager.py` refuses a path as `--brand` / `--month`; provider downloads are https only; slide text is escaped; the throwaway signing key and the README byte-order mark are gone; skills say where the scripts are when `${CLAUDE_PLUGIN_ROOT}` is unset; PRIVACY.md lists the timestamp request, the opt-in install and the other endpoints.

**v1.28.1:** the listing figures now count the workflow. v1.28.0 left `month-copy-preview` out of its figures: corrected, 10,525 → 4,965 as 1.28.0 shipped → 4,927 now (5,800 ceiling). The workflow's 185-character description is rewritten to the rule (147 characters, one review sheet for the month, pointer to `adapt-copy`), and `tests/test_description_density.py` now reads `workflows/*.js`, with a planted test that puts the old text back. Near-miss evals for the pair: 5/5 and 5/5 before and after.

**v1.28.0:** descriptions rewritten to fit Claude Code's character-based skill-listing budget (visible listing 10,305 → 4,745 characters), guarded by a rule test that records why. finalize-month and create-previews were hidden, reachable only through their wrapper commands; each now has one visible entry behind a typed `yes` gate, guarded. Trigger evals: 71/71 comparable cases before and after; near-miss pairs 5/5.

Older releases are in [CHANGELOG.md](CHANGELOG.md).

## Documentation

- **[User Guide](docs/USER-GUIDE.md)** — Complete walkthrough from setup to delivery (with real agency examples)
- **[Technical Operations](docs/OPERATIONS.md)** — Pipeline logic, scoring algorithms, AI models, folder structures, cost tracking
- **[Connectors](CONNECTORS.md)** — All 10 MCP connectors + storage architecture
- **[Testing Guide](TESTING-GUIDE.md)** — Full test plan with checklists
- **[X/Twitter Research Intake](references/x-twitter-research-intake.md)** - Optional, vendor-neutral evidence workflow for reactive posts and X copy — uses the harness's own web tools, any research tool the user has connected, or pasted threads
- **[Contributing](CONTRIBUTING.md)** — How to contribute to SocialForge
- **[Troubleshooting](references/troubleshooting.md)** — Common issues and fixes
- **[Changelog](CHANGELOG.md)** — Release history

## Star history

[![Star History Chart](https://api.star-history.com/svg?repos=indranilbanerjee/socialforge&type=Date)](https://star-history.com/#indranilbanerjee/socialforge&Date)

---

## About the maintainer

SocialForge is built and maintained by **[Indranil “Neel” Banerjee](https://indranil.in)** — a builder and systems thinker with roots in information security and a second act across growth marketing, enterprise digital operations, and AI transformation. This repository is one public implementation of a broader focus on trustworthy AI execution: preserve context, make evidence inspectable, and keep people at consequential decision points.

- 🌐 **Website:** [indranil.in](https://indranil.in)
- 💼 **LinkedIn:** [linkedin.com/in/askneelnow](https://www.linkedin.com/in/askneelnow)
- 🐦 **X / Twitter:** [@askneelnow](https://x.com/askneelnow)
- 💻 **GitHub:** [@indranilbanerjee](https://github.com/indranilbanerjee)
- 📦 **Other plugins:** [Digital Marketing Pro](https://github.com/indranilbanerjee/digital-marketing-pro) · [ContentForge](https://github.com/indranilbanerjee/contentforge)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/indranilbanerjee/socialforge/discussions)
- 🐛 **Bug reports:** [GitHub Issues](https://github.com/indranilbanerjee/socialforge/issues)
- 🔒 **Security:** [Private Security Advisory](https://github.com/indranilbanerjee/socialforge/security/advisories/new) (see [SECURITY.md](SECURITY.md))

If SocialForge saves your team time, [⭐ star the repo](https://github.com/indranilbanerjee/socialforge/stargazers). Sharing it on **LinkedIn** or **X** helps people discover the work too.

---

## Contributing

PRs welcome — especially on the four creative modes, platform-specific copy adaptation rules, and AI image/video model integrations. See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow, [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md) for the PR checklist, and [TESTING-GUIDE.md](TESTING-GUIDE.md) for the test plan. All contributors are expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md). Security issues: use [Private Security Advisories](https://github.com/indranilbanerjee/socialforge/security/advisories/new) per [SECURITY.md](SECURITY.md) — do not file public issues for vulnerabilities.

---

## Neelverse Marketing Suite

SocialForge is part of the **Neelverse Marketing Suite** by [Indranil Banerjee](https://indranil.in) — three plugins that work together for end-to-end marketing:

| Plugin | What It Does | Install |
|--------|-------------|---------|
| **[Digital Marketing Pro](https://github.com/indranilbanerjee/digital-marketing-pro)** | End-to-end engagement methodology — 12-Part Strategy Flow, Four Core Documents, Two-Views Model | `/plugin install digital-marketing-pro@neels-plugins` |
| **[ContentForge](https://github.com/indranilbanerjee/contentforge)** | Publication-ready content via 10-phase pipeline — research, fact-check, draft, SEO, humanize, `.docx` export with C2PA signing | `/plugin install contentforge@neels-plugins` |
| **SocialForge** (this plugin) | Social media calendar automation with AI image + video generation (Vertex AI + WaveSpeed, models resolved live), C2PA signing | `/plugin install socialforge@neels-plugins` |

**Use together:** Plan campaigns in DM Pro, produce articles with ContentForge, create social visuals and videos with SocialForge. They share a marketplace; each keeps its own brand setup, so set the brand up once in each plugin you use.

```
claude plugin marketplace add indranilbanerjee/neels-plugins
claude plugin install digital-marketing-pro@neels-plugins
claude plugin install contentforge@neels-plugins
claude plugin install socialforge@neels-plugins
```

## Sponsor this project

This plugin is MIT-licensed, free to use commercially, and collects no telemetry. What
sponsorship pays for is the unglamorous half of keeping it accurate: platform-API updates
when a vendor ships a breaking version, model-registry refreshes when a model is retired,
compliance passes when regulatory guidance moves, and issue triage.

If it saves your team time, you can [sponsor the work](https://github.com/sponsors/indranilbanerjee).
Sponsors from $25/mo are listed in [SPONSORS.md](SPONSORS.md).

[![Sponsor](https://img.shields.io/badge/sponsor%20on%20GitHub-%E2%9D%A4-ea4aaa?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/indranilbanerjee)

---

## License

MIT — see [LICENSE](LICENSE). Free to use commercially.

---

<sub>Made with care by [Indranil Banerjee](https://indranil.in) · MIT-licensed · [⭐ Star the repo](https://github.com/indranilbanerjee/socialforge) if it helps you</sub>
