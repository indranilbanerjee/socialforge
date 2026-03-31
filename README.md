# SocialForge — Social Media Calendar Automation

**Version:** 1.3.0
**Platform:** Claude Code & Cowork
**Status:** Production Ready (14 skills, 17 scripts, 5 agents, 18 commands, 10 HTTP connectors, 100% spec coverage)

Agency-grade social media calendar automation with asset-first compositing. Takes monthly content calendars, matches brand assets, generates AI-composed creative, renders carousels, adapts copy per platform, produces review galleries and delivery documents.

## Core Principle

**Brand assets are sacred. AI is the creative layer around them.**

Product photos, headshots, screenshots — these are the brand's real visual identity. AI generates backgrounds, mood, and context around them. The brand asset stays pixel-faithful in every composition.

## The Four Creative Modes

| Mode | When | What Happens |
|------|------|-------------|
| ANCHOR_COMPOSE | Brand photo is the centerpiece | AI generates scene around the untouched asset |
| ENHANCE_EXTEND | Brand photo is the base | AI extends/enhances periphery, core stays faithful |
| STYLE_REFERENCED | No specific asset needed | AI generates using brand's style reference photos as visual DNA |
| PURE_CREATIVE | Generic/abstract content | AI generates from text prompt + brand colors/mood |

## Quick Start

```
1. /sf:brand-setup [brand-name]    — Configure brand (5-10 min)
2. /sf:index-assets [brand-name]   — Index brand photo library
3. /sf:new-month [brand] [YYYY-MM] — Start monthly production
4. /sf:generate-all                — Produce all creative
5. /sf:review                      — Review and approve
6. /sf:finalize                    — Package for delivery
```

## Architecture

- **14 skills** — Calendar parsing, asset indexing, creative composition, copy adaptation, review management
- **18 commands** — Monthly production, post generation, editing, review, approval, finalization
- **5 agents** — Image compositor, carousel builder, copy adapter, quality reviewer, compliance checker
- **17 scripts** — Deterministic execution (compositing, rendering, resizing, compliance checking)
- **10 HTTP connectors** — Notion, Canva, Slack, Gmail, Google Calendar, Figma, fal.ai, Replicate, Asana, Cloudinary
- **4 hooks** — SessionStart, PreToolUse (compliance), SubagentStart (brand injection), Stop (quality gate)

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

## Connectors

SocialForge ships with **10 HTTP connectors** that work in both Cowork and Claude Code:
Notion, Canva, Slack, Gmail, Google Calendar, Figma, fal.ai, Replicate, Asana, Cloudinary.

The plugin works fully without connectors — all skills, agents, and creative production function with local assets and AI generation APIs.

## Storage

Brand configs and asset indexes persist across sessions via `${CLAUDE_PLUGIN_DATA}`. Asset images stay in Google Drive, Cloudinary, or local folders. See the [User Guide](docs/USER-GUIDE.md#11-where-your-data-lives) for details.

## Current Release (v1.3.0)

100% spec coverage. Persistent storage, Google Drive asset source, Cloudinary DAM, Veo 3.1 video generation, edge feathering, color temp matching, PDF carousel assembly, Instagram first-comment strategy, bilingual copy support.

## Documentation

- **[User Guide](docs/USER-GUIDE.md)** — Complete walkthrough from setup to delivery (with real agency examples)
- **[Technical Operations](docs/OPERATIONS.md)** — How everything works: pipeline logic, scoring algorithms, AI models, deterministic vs non-deterministic steps, folder structures, evaluation parameters, cost tracking
- **[Connectors](CONNECTORS.md)** — All 10 MCP connectors + storage architecture
- **[Testing Guide](TESTING-GUIDE.md)** — Full test plan with checklists
- **[Contributing](CONTRIBUTING.md)** — How to contribute to SocialForge
- **[Troubleshooting](references/troubleshooting.md)** — Common issues and fixes
- **[Changelog](CHANGELOG.md)** — Release history

## License

MIT
