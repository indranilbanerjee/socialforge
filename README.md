# SocialForge — Social Media Calendar Automation

**Version:** 0.3.0
**Platform:** Claude Code & Cowork
**Status:** Creative Pipeline Release (Layers 0-8)

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
- **9 HTTP connectors** — Notion, Canva, Slack, Gmail, Google Calendar, Figma, fal.ai, Replicate, Asana
- **4 hooks** — SessionStart, PreToolUse (compliance), SubagentStart (brand injection), Stop (quality gate)

## Installation

### From Marketplace
```
claude plugin marketplace add github:indranilbanerjee/socialforge
claude plugin install socialforge@socialforge
```

### From Local Directory
```
claude plugins add /path/to/socialforge
```

## Connectors

SocialForge ships with **9 HTTP connectors** that work in both Cowork and Claude Code:
Notion, Canva, Slack, Gmail, Google Calendar, Figma, fal.ai, Replicate, Asana.

The plugin works fully without connectors — all skills, agents, and creative production function with local assets and AI generation APIs.

## Current Release (v0.1.0)

Foundation release — plugin scaffold, brand management, calendar parsing, asset indexing, all 5 agents, 6 commands, hooks, and MCP connectors.

## License

MIT
