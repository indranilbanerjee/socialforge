# SocialForge — agent context

This file is auto-loaded by OpenAI Codex, Google Antigravity, GitHub Copilot CLI, Cursor (when in the agent context chain), and other Agent Skills runtimes. Equivalent of `CLAUDE.md` for non-Claude surfaces.

## What this plugin is

SocialForge is an open-source agency-grade social media production engine — calendar parsing, asset-first compositing (brand assets are sacred, AI is the creative layer around them), AI image generation (Vertex AI Nano Banana Pro), AI video generation (WaveSpeed Kling v3.0 Pro), multi-platform copy adaptation, human-in-the-loop review galleries, and C2PA content provenance signing for EU AI Act Article 50 compliance. **16 skills · 25 commands · 5 agents · 22 scripts · 10 HTTP MCP connectors · 0 global hooks.**

**Supported surfaces (v1.9.0):** Claude Code (CLI + IDE extensions), Anthropic Cowork, OpenAI Codex (CLI + IDE + App), Google Antigravity 2.0 (CLI + IDE).

## Core principle

**Brand assets are sacred. AI is the creative layer around them.** Product photos, headshots, screenshots — these are the brand's real visual identity. AI generates backgrounds, mood, and context around them. The brand asset stays pixel-faithful in every composition.

## Four creative modes

| Mode | When | What happens |
|---|---|---|
| ANCHOR_COMPOSE | Brand photo is the centerpiece | AI generates scene around the untouched asset |
| ENHANCE_EXTEND | Brand photo is the base | AI extends/enhances periphery, core stays faithful |
| STYLE_REFERENCED | No specific asset needed | AI generates using brand's style reference photos as visual DNA |
| PURE_CREATIVE | Generic/abstract content | AI generates from text prompt + brand colors/mood |

## How to use it as an agent

1. **Discover skills by description.** 16 skills auto-discover via SKILL.md frontmatter.
2. **Skill bodies reference Python scripts at `scripts/<name>.py`** — invoke via Bash. Key: `generate_image.py`, `edit_image.py`, `index_assets.py`, `parse_calendar.py`, `c2pa_sign.py`.
3. **Image/video APIs require credentials.** Vertex AI for Nano Banana Pro (image); WaveSpeed for Kling v3.0 Pro (video). Run `setup` skill once to store credentials in plugin persistent data.
4. **C2PA signing happens automatically before delivery** when `--c2pa-sign` flag is on (recommended for EU campaigns).
5. **Human-in-the-loop review is mandatory** before delivery — `build-review-gallery` + `manage-reviews` skills surface posts for client approval.

## Canonical entry points

| User intent | Run skill |
|---|---|
| "Configure a new brand" | `brand-manager` |
| "Index brand photo library" | `index-assets` |
| "Start a monthly production cycle" | `parse-calendar` then `full-pipeline` |
| "Generate creative for posts" | `compose-creative` |
| "Generate video clips" | `generate-video` |
| "Render carousels" | `render-carousels` |
| "Adapt copy per platform" | `adapt-copy` |
| "Build review gallery" | `build-review-gallery` |
| "Finalize and package for delivery" | `finalize-month` + `assemble-document` |
| "Sign assets with C2PA" | `c2pa-sign` |

## Files in this repo

- `skills/<name>/SKILL.md` — 16 Agent Skills.
- `agents/<name>.md` — 5 specialist agent definitions.
- `commands/<name>.md` — 25 Claude Code slash commands (`/socialforge:<name>`).
- `scripts/*.py` — 22 Python helpers.
- `hooks/hooks.json` — `{"hooks":{}}` (zero global hooks).
- `.mcp.json` — `{"mcpServers":{}}` (zero auto-connecting MCPs).
- `assets/` + `references/` + `templates/` + `settings.json` — brand assets, channel-pack references, post templates.

## May 2026 channel pack

- TikTok USDS Joint Venture (post-Jan 22 2026; AI creator labeling mandatory, AI content excluded from Creator Rewards Program)
- LinkedIn March 12 2026 algorithm + Depth Score (external links and engagement bait penalized ~60%)
- Apple MPP affects ~64% of B2C opens (open rate dropped as primary KPI)
- YouTube AI Shorts labeling
- Sora deprecation (consumer app 26 Apr 2026, API 24 Sep 2026) → defaults to Runway Gen-4 / Veo 3.x / Kling 3.0

## Cross-platform notes

- **Skills portable** across all supported surfaces (Agent Skills open standard).
- **Subagents Claude-only** as `agents/*.md`; convert to Codex TOML if Codex subagent is needed.
- **Slash commands Claude-only** as `commands/*.md`; invoke by natural-language intent on other surfaces.

## Identity / authority

Built and maintained by Indranil Banerjee (https://indranil.in). MIT-licensed. No telemetry. Part of the Neelverse Marketing Suite alongside Digital Marketing Pro and ContentForge.
