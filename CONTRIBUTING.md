# Contributing to SocialForge

Thank you for your interest in contributing to SocialForge!

## Code of Conduct

- Be respectful and collaborative
- Be inclusive of diverse perspectives
- Focus on what's best for the project and its users
- Keep discussions constructive

## How to Contribute

### Reporting Bugs

1. Check existing [GitHub Issues](https://github.com/indranilbanerjee/socialforge/issues) first
2. Create a new issue with:
   - **What happened** (actual behavior)
   - **What you expected** (expected behavior)
   - **Steps to reproduce**
   - **Environment** (Claude Code / Cowork, OS, Python version)
   - **Error messages** (full text, not screenshots)

### Suggesting Features

1. Open a GitHub Issue with the `enhancement` label
2. Describe the use case, not just the feature
3. Explain how it fits the asset-first compositing principle

### Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make changes following the coding standards below
4. Test your changes (see TESTING-GUIDE.md)
5. Submit a PR with a clear description of changes

## Development Setup

```bash
git clone https://github.com/indranilbanerjee/socialforge.git
cd socialforge
pip install Pillow  # Minimum for image scripts
# Optional: pip install rembg playwright google-genai imageio-ffmpeg
```

## Coding Standards

### Skills
- Description under 130 characters
- `effort` frontmatter on every skill (low/medium/high/max)
- `argument-hint` showing usage pattern
- `disable-model-invocation: true` on the destructive/irreversible execution skills only — currently `manage-reviews`, `create-previews`, `finalize-month`, `assemble-document`. Most skills omit it so they stay model-discoverable.
- Timeout + fallback documented for every network operation

### Agents
- Under 300 lines (current average: ~73 lines)
- `maxTurns` on every agent
- `name` + `description` in YAML frontmatter

### Scripts
- `#!/usr/bin/env python3` shebang
- Triple-quote docstring
- `argparse` for CLI arguments
- JSON output via `print(json.dumps(...))`
- Graceful import fallback for external packages (`try/except ImportError`)
- No hardcoded paths — resolve the workspace with the standard two-tier lookup: prefer `${CLAUDE_PLUGIN_DATA}/socialforge` when the env var is set and the directory exists, else fall back to `~/socialforge-workspace`

  ```python
  _plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
  if _plugin_data and Path(_plugin_data).exists():
      WORKSPACE = Path(_plugin_data) / "socialforge"
  else:
      WORKSPACE = Path.home() / "socialforge-workspace"
  ```

### Commands
- `description` + `argument-hint` in YAML frontmatter
- Clear step-by-step process
- Output example shown

## Testing

See [TESTING-GUIDE.md](TESTING-GUIDE.md) for the complete test plan.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
