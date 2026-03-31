# Connectors

## How tool references work

Plugin files use `~~category` as a placeholder for whatever tool the user connects in that category. For example, `~~calendar` might mean Google Calendar, Notion, or any other scheduling tool with an MCP server.

Plugins are **tool-agnostic** — they describe workflows in terms of categories (calendar, design, image gen, etc.) rather than specific products. The `.mcp.json` pre-configures specific MCP servers, but any MCP server in that category works.

## Connectors for this plugin

| Category | Placeholder | Included server | Other options | Workflow impact |
|----------|-------------|-----------------|---------------|----------------|
| Calendar | `~~calendar` | Google Calendar | Notion, Asana | Posting schedule, content calendar sync |
| Knowledge base | `~~knowledge base` | Notion | Confluence, Google Drive | Calendar databases, brand guidelines, asset library |
| Design | `~~design` | Canva, Figma | Adobe Creative Cloud | Brand templates, design assets, carousel generation |
| Image generation | `~~image gen` | fal.ai, Replicate | Stability AI (npx), Gemini (npx) | AI-composed creative for all 4 modes |
| Chat | `~~chat` | Slack | Microsoft Teams | Approval notifications, review requests, delivery alerts |
| Email | `~~email` | Gmail | Outlook | Finalized document delivery, approval reminders |
| Project management | `~~project` | Asana | Monday.com, Linear | Post status tracking, publishing schedule |

## The plugin works without connectors

**All 14 skills, 5 agents, 17 scripts, and 18 commands work immediately** without any connectors. Connectors add live data and execution capabilities:

- Without Notion: Parse calendars from DOCX/XLSX/text (no Notion database sync)
- Without fal.ai/Replicate: Use Gemini API directly for image generation (requires GEMINI_API_KEY)
- Without Slack/Gmail: Review in-conversation, deliver files locally
- Without Google Calendar: Manually set posting dates and times

## Platform-level integrations

Some services are connected at the **Claude platform level** rather than through MCP:

| Service | Platform integration | MCP alternative |
|---------|---------------------|-----------------|
| Google Drive | Yes — connect in Settings → Integrations | Also available via npx |
| Google Docs | Yes — connect in Settings → Integrations | Also available via npx |

## Managing connectors

| Command | What it does |
|---------|-------------|
| `/sf:status` | Shows which connectors are active and what they enable |
| `/sf:new-month` | Checks for required connectors at pipeline start |

## Advanced configuration (Claude Code)

For Claude Code CLI users who want to customize the MCP configuration:

```bash
cp .mcp.json.example .mcp.json
```

Edit `.mcp.json` to add, remove, or reconfigure connectors. All servers use HTTP transport (no npx required).
