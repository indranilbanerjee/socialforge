# SocialForge — Social Media Calendar Automation

**Open-source agency-grade social media production engine** — calendar parsing, asset-first compositing, **AI image generation (Vertex AI Nano Banana Pro)**, **AI video generation (WaveSpeed Kling v3.0 Pro)**, multi-platform copy adaptation, human-in-the-loop review galleries, and **C2PA content provenance signing for EU AI Act Article 50 compliance** (applicable 2 Aug 2026). **16 skills · 25 commands · 5 agents · 20 scripts · 10 HTTP MCP connectors · 0 global hooks.** Installs on **5 coding-agent surfaces**: Claude Code, Claude Cowork, OpenAI Codex, Cursor, GitHub Copilot CLI, and Google Antigravity 2.0 (experimental).

Built for agencies and in-house teams running monthly content calendars across Instagram, TikTok, LinkedIn, Threads, X, Facebook, YouTube Shorts. Created by [Indranil Banerjee](https://indranil.in).

[![Version](https://img.shields.io/badge/version-1.8.1-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/indranilbanerjee/socialforge?style=flat&logo=github&color=yellow)](https://github.com/indranilbanerjee/socialforge/stargazers)
[![Forks](https://img.shields.io/github/forks/indranilbanerjee/socialforge?style=flat&logo=github&color=blue)](https://github.com/indranilbanerjee/socialforge/network/members)
[![Issues](https://img.shields.io/github/issues/indranilbanerjee/socialforge?logo=github)](https://github.com/indranilbanerjee/socialforge/issues)
[![Last commit](https://img.shields.io/github/last-commit/indranilbanerjee/socialforge?logo=github)](https://github.com/indranilbanerjee/socialforge/commits/main)
[![Cowork](https://img.shields.io/badge/cowork-compatible-purple.svg)](docs/CROSS-PLATFORM-GUIDE.md)
[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Article%2050%20ready-darkred.svg)](references/c2pa-production-cert.md)
[![5 platforms](https://img.shields.io/badge/installs%20on-5%20platforms-success.svg)](docs/CROSS-PLATFORM-GUIDE.md)

```bash
# Install — one line on any of 5 supported platforms
/plugin marketplace add indranilbanerjee/neels-plugins
/plugin install socialforge@neels-plugins
```

> If SocialForge saves your team time, [give it a star ⭐](https://github.com/indranilbanerjee/socialforge/stargazers) — it's the single thing that helps other agencies find it.

**Status:** Production Ready · 16 skills · 25 commands · 5 agents · 20 scripts · 10 HTTP MCP connectors · 0 global hooks

Agency-grade social media calendar automation with asset-first compositing and AI video generation. Takes monthly content calendars, matches brand assets, generates AI-composed creative, renders carousels, produces AI-generated video clips, adapts copy per platform, produces review galleries and delivery documents — with C2PA content provenance signed into every AI-generated image/video before delivery.

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

## Installs on 5 coding-agent surfaces (one repo, no fork)

| Platform | Install command | Status |
|---|---|---|
| **Claude Code** CLI + Desktop + **Anthropic Cowork** | `/plugin install socialforge@neels-plugins` | Full support (canonical) |
| **OpenAI Codex** CLI | `codex plugin install indranilbanerjee/socialforge` | Skills + MCP + scripts |
| **Cursor** IDE + CLI | `cursor plugin install indranilbanerjee/socialforge` | Skills + scripts; MCP via Cursor's global `mcp.json` (paste 8 of 10 connectors — Gmail + Google Calendar are Anthropic-hosted only) |
| **GitHub Copilot CLI** | `copilot plugin install indranilbanerjee/socialforge` | Full support — auto-discovers `.claude-plugin/plugin.json` |
| **Google Antigravity 2.0** CLI | `agy plugin install indranilbanerjee/socialforge` | **Experimental** — manifest will firm up as Antigravity publishes v2-native spec |

Agent Skills became an open standard (Dec 2025; adopted by 32+ tools by May 2026), so the same 16 SKILL.md files work everywhere. Full per-platform install guide: [`docs/CROSS-PLATFORM-GUIDE.md`](docs/CROSS-PLATFORM-GUIDE.md).

## Architecture

- **16 skills** — Calendar parsing, asset indexing, creative composition, copy adaptation, review management, C2PA signing
- **25 commands** — Monthly production, post generation, editing, review, approval, finalization
- **5 agents** — Image compositor, carousel builder, copy adapter, quality reviewer, compliance checker
- **20 scripts** — Deterministic execution (compositing, rendering, resizing, video post-processing, compliance checking, C2PA signing)
- **10 HTTP connectors** — Notion, Canva, Slack, Gmail, Google Calendar, Figma, fal.ai, Replicate, Asana, Cloudinary (all Cowork-compatible)
- **0 global hooks** — As of v1.5.0. Prior hook config preserved at `hooks/hooks-reference.example.json`. Credential status now via `/socialforge:status` on demand. See [Current Release](#current-release-v181) for the rationale.

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

## Current Release (v1.8.1)

**Polish + discoverability + community-standards pass.** Patch bump — no functional changes. Adds Star History, community-standards files (`CODE_OF_CONDUCT.md`, `SECURITY.md`, PR + Issue templates), rewrites the README hero with social-proof badges + 5-platform install matrix + maintainer block ([indranil.in](https://indranil.in) + [linkedin.com/in/askneelnow](https://www.linkedin.com/in/askneelnow) + [@askneelnow](https://x.com/askneelnow)), fixes stale asset counts (15→16 skills, 19→20 scripts) across README, and expands `plugin.json` keywords from 17 → 47 for marketplace search.

### Earlier (v1.8.0)

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

## Star history

[![Star History Chart](https://api.star-history.com/svg?repos=indranilbanerjee/socialforge&type=Date)](https://star-history.com/#indranilbanerjee/socialforge&Date)

---

## About the maintainer

SocialForge is built and maintained by **[Indranil Banerjee](https://indranil.in)** — a digital marketing practitioner shipping social-creative automation as code. The asset-first compositing principle ("brand assets are sacred, AI is the creative layer around them") and the four creative modes come from real agency work producing monthly content calendars at scale.

- 🌐 **Website:** [indranil.in](https://indranil.in)
- 💼 **LinkedIn:** [linkedin.com/in/askneelnow](https://www.linkedin.com/in/askneelnow)
- 🐦 **X / Twitter:** [@askneelnow](https://x.com/askneelnow)
- 💻 **GitHub:** [@indranilbanerjee](https://github.com/indranilbanerjee)
- 📦 **Other plugins:** [Digital Marketing Pro](https://github.com/indranilbanerjee/digital-marketing-pro) · [ContentForge](https://github.com/indranilbanerjee/contentforge)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/indranilbanerjee/socialforge/discussions)
- 🐛 **Bug reports:** [GitHub Issues](https://github.com/indranilbanerjee/socialforge/issues)
- 🔒 **Security:** [Private Security Advisory](https://github.com/indranilbanerjee/socialforge/security/advisories/new) (see [SECURITY.md](SECURITY.md))

If SocialForge saves your team time, [⭐ star the repo](https://github.com/indranilbanerjee/socialforge/stargazers). Sharing on **LinkedIn** ([linkedin.com/in/askneelnow](https://www.linkedin.com/in/askneelnow)) or **X** ([@askneelnow](https://x.com/askneelnow)) helps too — tag me, I'll re-share.

---

## Contributing

PRs welcome — especially on the four creative modes, platform-specific copy adaptation rules, and AI image/video model integrations. See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow, [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md) for the PR checklist, and [TESTING-GUIDE.md](TESTING-GUIDE.md) for the test plan. All contributors are expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md). Security issues: use [Private Security Advisories](https://github.com/indranilbanerjee/socialforge/security/advisories/new) per [SECURITY.md](SECURITY.md) — do not file public issues for vulnerabilities.

---

## Neelverse Marketing Suite

SocialForge is part of the **Neelverse Marketing Suite** by [Indranil Banerjee](https://indranil.in) — three plugins that work together for end-to-end marketing:

| Plugin | What It Does | Install |
|--------|-------------|---------|
| **[Digital Marketing Pro](https://github.com/indranilbanerjee/digital-marketing-pro)** | End-to-end engagement methodology — 12-Part Strategy Flow, Four Core Documents, Two-Views Model. 150 skills, 25 agents, 10 commands, 14 HTTP connectors | `/plugin install digital-marketing-pro@neels-plugins` |
| **[ContentForge](https://github.com/indranilbanerjee/contentforge)** | Publication-ready content via 11-phase pipeline — research, fact-check, draft, SEO, humanize, `.docx` export with C2PA signing | `/plugin install contentforge@neels-plugins` |
| **SocialForge** (this plugin) | Social media calendar automation with AI image + video generation (Vertex AI Nano Banana Pro + WaveSpeed Kling v3.0 Pro), C2PA signing | `/plugin install socialforge@neels-plugins` |

**Use together:** Plan campaigns in DM Pro, produce articles with ContentForge, create social visuals and videos with SocialForge. All share the same brand profiles and marketplace.

```
claude plugin marketplace add indranilbanerjee/neels-plugins
claude plugin install digital-marketing-pro@neels-plugins
claude plugin install contentforge@neels-plugins
claude plugin install socialforge@neels-plugins
```

## License

MIT — see [LICENSE](LICENSE). Free to use commercially.

---

<sub>Made with care by [Indranil Banerjee](https://indranil.in) · MIT-licensed · [⭐ Star the repo](https://github.com/indranilbanerjee/socialforge) if it helps you</sub>
