# Cross-Platform Guide: Using SocialForge on Other AI Coding Tools

SocialForge is built as a Claude Code plugin, but its core components follow the open Agent Skills standard (SKILL.md) and Model Context Protocol (MCP), making it portable to other AI coding tools.

## What Works Everywhere (Zero Changes)

| Component | Count | Works On |
|-----------|-------|----------|
| Skills (SKILL.md) | 15 | Codex, Cursor, Gemini CLI, Copilot, Windsurf |
| Python scripts | 18 | Any platform with Python 3.10+ |
| MCP connectors | 8 of 10 | Any MCP-compatible platform |
| Reference docs | 11 | Universal |

## What Needs Adaptation Per Platform

| Component | Change Needed | Effort |
|-----------|--------------|--------|
| Plugin manifest dir | Rename `.claude-plugin/` | 2 min |
| Environment variables | `CLAUDE_PLUGIN_ROOT` / `CLAUDE_PLUGIN_DATA` | 10 min |
| Hooks (lifecycle) | Platform-specific event names | 1-2 hours |
| 2 MCP connectors | Gmail + Calendar are Claude-hosted | 5 min (remove) |

---

## OpenAI Codex CLI

**Compatibility: HIGH** -- Codex plugins are intentionally cross-compatible with Claude Code.

### Porting Steps

1. **Copy the plugin:**
   ```
   cp -r socialforge socialforge-codex
   cd socialforge-codex
   ```

2. **Rename plugin directory:**
   ```
   mv .claude-plugin .codex-plugin
   ```

3. **Replace environment variables:**
   - In `hooks/hooks.json`: replace `CLAUDE_PLUGIN_ROOT` with `CODEX_PLUGIN_ROOT`
   - In `scripts/*.py`: replace `CLAUDE_PLUGIN_DATA` with `CODEX_PLUGIN_DATA`
   
   Linux/macOS:
   ```bash
   sed -i 's/CLAUDE_PLUGIN_ROOT/CODEX_PLUGIN_ROOT/g' hooks/hooks.json
   find scripts/ -name "*.py" -exec sed -i 's/CLAUDE_PLUGIN_DATA/CODEX_PLUGIN_DATA/g' {} +
   ```
   
   Windows (PowerShell):
   ```powershell
   (Get-Content hooks/hooks.json) -replace 'CLAUDE_PLUGIN_ROOT','CODEX_PLUGIN_ROOT' | Set-Content hooks/hooks.json
   Get-ChildItem scripts/*.py | ForEach-Object { (Get-Content $_) -replace 'CLAUDE_PLUGIN_DATA','CODEX_PLUGIN_DATA' | Set-Content $_ }
   ```

4. **Remove Claude-specific MCP connectors** from `.mcp.json`:
   - Remove `gmail` entry (gmail.mcp.claude.com)
   - Remove `google-calendar` entry (gcal.mcp.claude.com)
   - Keep all 8 other connectors (Notion, Canva, Slack, Figma, fal.ai, Replicate, Asana, Cloudinary)

5. **Install:** `codex plugin add ./socialforge-codex`

### What Works in Codex

| Feature | Status |
|---------|--------|
| All 15 skills | Works |
| All 18 Python scripts | Works |
| All 5 agents | Works |
| 8 MCP connectors | Works |
| Hooks (lifecycle events) | Likely works (similar lifecycle) |
| Gmail and Calendar connectors | Does NOT work (Claude-hosted) |

---

## Cursor

**Compatibility: HIGH** -- Very similar plugin architecture.

### Porting Steps

1. Copy and rename: `mv .claude-plugin .cursor-plugin`
2. Replace `CLAUDE_PLUGIN_ROOT` with `CURSOR_PLUGIN_ROOT` in hooks.json
3. Replace `CLAUDE_PLUGIN_DATA` with `CURSOR_PLUGIN_DATA` in scripts
4. Remove Claude-specific MCP connectors (Gmail, Calendar)
5. Optionally add `.mdc` rules files for Cursor-specific brand compliance rules
6. Install via Cursor marketplace or `cursor plugin add ./socialforge-cursor`

### Cursor-Specific Addition

Cursor supports `.mdc` rules files. You can add `rules/brand-compliance.mdc` for brand enforcement during development.

---

## Google Gemini CLI

**Compatibility: MEDIUM** -- Skills and agents work. Different manifest format.

### Porting Steps

1. Copy the plugin
2. Create `gemini-extension.json` in the root:
   ```json
   {
     "name": "socialforge",
     "version": "1.4.0",
     "description": "Social media calendar automation with AI image and video generation",
     "skills": "skills/",
     "agents": "agents/"
   }
   ```
3. Skills (SKILL.md) work as-is -- same Agent Skills standard
4. Remove Claude-specific MCP connectors
5. Hooks will be ignored (Gemini CLI has a different lifecycle system)

### Limitations

- No hook lifecycle events (compliance checks will not auto-run)
- Extension spec is still evolving
- Multi-agent orchestration may work differently

---

## GitHub Copilot CLI

**Compatibility: MEDIUM** -- Skills work. Agents need renaming.

### Porting Steps

1. Copy the plugin
2. Rename agent files from `*.md` to `*.agent.md`:
   ```bash
   cd agents
   for f in *.md; do mv "$f" "${f%.md}.agent.md"; done
   ```
3. Create `plugin.json` in root (not in `.claude-plugin/`)
4. Move MCP config: `cp .mcp.json .github/mcp.json`
5. Remove Claude-specific connectors from `.github/mcp.json`

### Limitations

- Multi-agent orchestration support is limited
- SubagentStart hook may not exist
- Agent files require `.agent.md` suffix

---

## Windsurf (Codeium)

**Compatibility: LOW** -- Skills only. No full plugin packaging.

### Porting Steps

1. Copy skills to your project:
   ```bash
   mkdir -p .windsurf/skills
   cp -r socialforge/skills/* .windsurf/skills/
   ```
2. Windsurf discovers skills automatically from `.windsurf/skills/`
3. No hooks, commands, or agent files supported
4. Scripts must be invoked manually through skill instructions

---

## Universal Installation via OpenSkills

For the simplest cross-platform experience:
```bash
npm install -g openskills
openskills install socialforge
```

OpenSkills places SKILL.md files in the correct location for your AI tool (Claude, Codex, Cursor, Windsurf, Gemini, Aider).

Note: installs skills only, not the full plugin (no agents, hooks, scripts, or MCP connectors).

---

## Compatibility Matrix

| Feature | Claude Code | Codex | Cursor | Gemini CLI | Copilot | Windsurf |
|---------|------------|-------|--------|------------|---------|----------|
| Skills (SKILL.md) | Full | Full | Full | Full | Full | Full |
| Agents | Full | Full | Full | Partial | Rename .agent.md | No |
| Commands | Full | Partial | Full | Partial | Partial | No |
| Hooks | Full | Likely | Different events | No | Partial | No |
| MCP connectors | 10/10 | 8/10 | 8/10 | 8/10 | 8/10 | 8/10 |
| Python scripts | Full | Full | Full | Full | Full | Full |
| Image generation | Full | Full | Full | Full | Full | Full |
| Video generation | Full | Full | Full | Full | Full | Full |
| Full pipeline | Full | Full | Likely | Partial | Partial | No |

---

## Resources

- Agent Skills specification: https://agentskills.io/specification
- OpenSkills (universal installer): https://github.com/numman-ali/openskills
- SocialForge repo: https://github.com/indranilbanerjee/socialforge
- Claude Code plugin docs: https://code.claude.com/docs/en/plugins
