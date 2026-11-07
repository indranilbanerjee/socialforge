# Security Policy

## Supported Versions

The latest minor release of SocialForge receives security fixes. Older minor versions are not patched — please update first.

| Version | Supported |
|---------|-----------|
| 1.31.x  | ✅ |
| 1.30.x  | ⚠️ Security fixes only when trivially backportable |
| < 1.30  | ❌ Please upgrade |

## Reporting a Vulnerability

**Do NOT open a public GitHub Issue for security vulnerabilities.** Public Issues expose users before a fix is available.

### How to report

Use GitHub's [Private Security Advisory](https://github.com/indranilbanerjee/socialforge/security/advisories/new) feature to report privately. The maintainer will be notified directly and can collaborate with you on a fix before disclosure.

If you cannot use Private Security Advisories, contact the maintainer via the email listed on [indranil.in](https://indranil.in) with the subject line `[SF Security]`.

### What to include

- A clear description of the vulnerability and its impact
- Steps to reproduce (with example commands, payloads, or files if applicable)
- Affected version(s) and surface (Claude Code CLI or IDE extension / Anthropic Cowork / OpenAI Codex / Cursor 2.5+ / GitHub Copilot CLI / Google Antigravity 2.0 / Hermes Agent / OpenClaw)
- Suggested remediation if you have one
- Whether you'd like credit in the security advisory (and how you'd like to be named)

### What you can expect

- **Acknowledgement within 48 hours** that we've received your report
- **Initial assessment within 7 days** with severity classification and tentative timeline
- **Coordinated disclosure** — we'll work with you on a disclosure date that gives users time to update
- **Credit in the published advisory** unless you prefer to remain anonymous
- **No bug bounty program** — this is an open-source project maintained by an individual. We deeply appreciate responsible disclosure.

## Scope

In scope:
- The SF plugin itself (skills, scripts, agents, manifests, MCP catalog)
- The example C2PA signing flow (`scripts/c2pa_sign.py`)
- The Python scripts (any path traversal, command injection, or unsafe deserialization)
- Plugin manifest parsing edge cases that could be exploited

Out of scope:
- Vulnerabilities in Claude Code or Anthropic Cowork themselves — please report to Anthropic
- Vulnerabilities in third-party MCP servers (Slack, HubSpot, etc.) — please report to those vendors
- Vulnerabilities in upstream Python dependencies — please report to those projects (and let us know so we can upgrade)
- Anthropic Claude model behavior issues — please report via Anthropic's official channels
- Reports from automated scanners without proof of exploitability

## Coordinated Disclosure Timeline

For valid reports:
- **Day 0** — Report received, acknowledged within 48 hours
- **Day 7** — Initial severity assessment shared with reporter
- **Day 7–30** — Fix developed, tested, and a patch release prepared
- **Day 30** — Fix released to GitHub `main` and bumped on the marketplace; security advisory drafted
- **Day 30–45** — Coordinated disclosure window (lets users update)
- **Day 45** — Public advisory published with full details and credit

We may move faster than this timeline for actively-exploited issues. We will not move slower without explicit reporter agreement.

## Hardening Recommendations for Operators

If you are running SF in a sensitive environment (multi-tenant agency setup, regulated industry brands):

1. **Never commit `.mcp.json` with real API keys.** Use env vars or a secret manager — `.mcp.json.example` is the safe template.
2. **Treat brand data at `${CLAUDE_PLUGIN_DATA}/socialforge/brands/<brand-slug>/` as sensitive** (fallback `~/socialforge-workspace/brands/<brand-slug>/`). It contains client strategy documents, brand assets, and compliance rules. Apply filesystem ACLs as you would any client PII.
3. **Keep provider keys in environment variables.** `/socialforge:setup` records only the variable names (`WAVESPEED_API_KEY`, `HF_API_KEY`, `HF_API_SECRET`) in `credentials.json` and reads the values at run time, so the keys are never written by SocialForge. The Vertex AI service-account JSON is used where you keep it (its path is recorded; no copy is made since 1.31.0, and an older `gcp-credentials.json` copy is reported until you delete it). A key piped in with `--api-key-stdin` or typed at `--prompt` goes to the OS keychain when the optional `keyring` package is installed (`install_deps.py --groups keyring`); without it, it is written to `credentials.json` in plain text and setup warns you. `--api-key` / `--api-secret` on the command line are refused.
4. **Know what the file permissions do.** On macOS and Linux SocialForge's credential files are `chmod 600`. On Windows chmod is a no-op for this (it only sets the read-only flag), so setup runs `icacls <file> /inheritance:r /grant:r <you>:F` on `credentials.json`; anyone with administrator rights on the machine can still read it. The credential folder is `${CLAUDE_PLUGIN_DATA}/socialforge/`, or `~/socialforge-workspace/` when the host sets no data folder.
5. **Rotate generation-provider API keys quarterly.** SocialForge consumes Gemini / Vertex AI keys for image generation and WaveSpeed keys for video — rotate those at the provider. Use `/socialforge:cost-report` to monitor for anomalous consumption.
6. **Review SKILL.md edits in PRs.** Skills run with whatever permissions Claude Code has. Treat skill modifications like code review for production systems.
7. **Pin the plugin version in agency environments.** Don't auto-update production agencies on the same day as release — let community testing happen first.
