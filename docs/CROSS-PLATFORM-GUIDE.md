# Cross-platform install guide

SocialForge v1.7.0 ships **three platform-native manifests** alongside the Claude Code manifest, so the same 16 Agent Skills, 20 Python scripts, and 10 HTTP MCP connectors install cleanly on:

| Platform | Manifest path | Status |
|---|---|---|
| **Claude Code** (CLI + Desktop) + **Anthropic Cowork** | `.claude-plugin/plugin.json` | Full support — agents, skills, commands, hooks, MCP, scripts |
| **OpenAI Codex** (CLI) | `.codex-plugin/plugin.json` | Skills + MCP + hooks + scripts; commands and agents via Codex-native invocation patterns |
| **Cursor** (IDE + CLI) | `.cursor-plugin/plugin.json` | Skills + hooks + scripts; MCP via Cursor's global mcp.json (see below) |

> **What changed in v1.7.0:** Earlier versions of this guide told users to manually copy SocialForge and rename `.claude-plugin/` to `.codex-plugin/` or similar. That's no longer needed. v1.7.0 ships all three manifests in-repo so users install via their platform's native plugin manager — no copy, no rename, no fork.

The key insight: **Agent Skills are an open standard.** The `name:` + `description:` SKILL.md frontmatter is interpreted the same way by every major coding agent surface as of May 2026. SocialForge reuses the same `skills/` directory across all three platform manifests — no skill duplication, no maintenance fork.

---

## Install on Claude Code (canonical)

```bash
/plugin marketplace add indranilbanerjee/neels-plugins
/plugin install socialforge@neels-plugins
```

See the [main README](../README.md) for the full Claude Code experience plus one-time `/sf:setup` to store Vertex AI + WaveSpeed credentials.

---

## Install on OpenAI Codex

```bash
codex plugin install indranilbanerjee/socialforge
```

After install, restart your Codex session. Try:

```
"Run today's SocialForge calendar for brand acme."
"Generate three Instagram carousel concepts for our Q3 product launch."
"Compose a 9:16 video for TikTok with our brand template overlay."
```

**What works on Codex:**
- All 16 Agent Skills (auto-discovered via SKILL.md frontmatter — same open standard as Claude Code)
- 8 of 10 HTTP MCP connectors work universally; 2 (Gmail + Google Calendar) are Anthropic-hosted endpoints — use a platform-native alternative on Codex (OpenAI's own Google integrations, or self-host these connectors)
- All 20 Python scripts (`generate_image.py`, `video_postprocess.py`, `c2pa_sign.py`, etc.) run when Python 3.10+ is present
- `hooks/hooks.json` (empty by default — zero global hooks, matches Claude Code v1.5+ behaviour)
- **Credentials**: Codex uses its own secret-store mechanism. Re-create your Vertex AI service-account JSON path + WaveSpeed API key as Codex secrets (the `/sf:setup` skill is Claude-Code-specific — but it just writes to `~/.claude/plugins/data/socialforge/credentials.json`, which Codex won't read)

**What's Claude-Code-native and isn't auto-invoked on Codex:**
- Slash commands in `commands/` are Claude Code's `/sf:*` syntax. On Codex, invoke the underlying workflow via natural language and the SKILL.md routing picks up the same handler
- 5 specialist sub-agents in `agents/*.md` use Claude Code's specific sub-agent format. Codex has its own sub-agent / app concept; skills embed the relevant agent instructions inline so outputs are equivalent

---

## Install on Cursor

```bash
cursor plugin install indranilbanerjee/socialforge
```

After install, restart Cursor (or `Cursor: Reload Window`).

**What works on Cursor:**
- All 16 Agent Skills auto-discovered via SKILL.md frontmatter
- `hooks/hooks.json` empty by default
- All 20 Python scripts run from Cursor's terminal context
- **Credentials**: Cursor doesn't have a plugin-scoped secret store. Configure Vertex AI service-account path + WaveSpeed API key as workspace environment variables in your shell profile or a `.env` file at the workspace root

**MCP on Cursor — manual one-time configuration:**

Cursor reads MCP servers from a global `mcp.json` (no leading dot). To enable any of SocialForge's HTTP connectors on Cursor:

1. Open Cursor → Settings → MCP Servers
2. Copy the 8 cross-platform connector entries from SocialForge's `.mcp.json` (Notion, Canva, Slack, Webflow, Figma, etc.) into Cursor's MCP configuration
3. Skip Gmail + Google Calendar (Anthropic-hosted only — use Cursor's own Google integration or a self-hosted MCP)
4. Set required env vars per connector

This is a Cursor platform constraint, not a SocialForge limitation. Cursor's plugin-scoped MCP is not yet GA (May 2026).

**What's Claude-Code-native and isn't auto-invoked on Cursor:**
- Slash commands (`/sf:*`) — Cursor Agent picks the right skill from natural-language intent
- 5 specialist sub-agents — Cursor has rules and modes instead of sub-agents

---

## What's portable vs platform-specific

| Component | Claude Code | Codex | Cursor | Notes |
|---|---|---|---|---|
| **Skills** (`skills/<name>/SKILL.md`) | yes | yes | yes | Open Agent Skills standard |
| **Python scripts** (`scripts/*.py`) | yes | yes | yes | Run when Python 3.10+ present |
| **HTTP MCP catalog** (`.mcp.json`) | yes (auto-loaded) | yes (auto-loaded) | manual paste into Cursor global mcp.json | 8 of 10 connectors are universal; 2 (Gmail + Google Calendar) are Claude-hosted |
| **Hooks** (`hooks/hooks.json`) | yes | yes | yes | Empty by default — zero global hooks |
| **Slash commands** (`commands/*.md`) | yes | partial | n/a (natural language) | |
| **Sub-agents** (`agents/*.md`) | yes | partial | n/a | Skills embed agent instructions inline |
| **Credential persistence** | `/sf:setup` writes to Claude Code plugin data dir | Codex secrets store | workspace env vars / `.env` | Each platform owns its own secret persistence pattern |

---

## Updating

| Platform | Update command |
|---|---|
| Claude Code | `/plugin update socialforge@neels-plugins` |
| Codex | `codex plugin update socialforge` |
| Cursor | `cursor plugin update socialforge` |

All three platforms pull from the same GitHub `main` branch — no version drift between platform builds.

---

## Reporting platform-specific bugs

| Platform | Where to file |
|---|---|
| Claude Code platform bug | https://github.com/anthropics/claude-code/issues |
| Codex platform bug | https://github.com/openai/codex/issues |
| Cursor platform bug | https://github.com/cursor/plugins/issues |
| SocialForge skill/content bug (any platform) | https://github.com/indranilbanerjee/socialforge/issues |
