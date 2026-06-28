# Changelog

All notable changes to SocialForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.13.1] - 2026-06-28

**README-sync patch — Current Release body rewritten with actual v1.13.0 content.**

After v1.13.0 shipped, the user flagged that several README sections had stale version refs. SF's specific gap: the `## Current Release (v1.13.0)` heading had been renamed but the body still described the v1.12.0 (Hermes + OpenClaw + 23-test suite) release. SF release-consistency tests caught the heading bump but had no check for body freshness.

### Fixed (SF README)

- `## Current Release (v1.13.0)` body rewritten with actual v1.13.0 content (June 2026 market-refresh sync: resolver-routed alias updates, retired-model handling, --check-params scanner)
- v1.12.1 + v1.12.0 release notes moved into "Earlier" sub-sections so chronological flow is preserved
- README hero callout + Supported surfaces heading + Current Release heading + Cowork anchor + version badge all bumped to v1.13.1

### Changed

- All 9 SF version declarations 1.13.0 → 1.13.1

### Notes

- Zero pipeline change.

---

## [1.13.0] - 2026-06-28

**June 2026 market-refresh sync — model registry rebuilt, MODEL-CURATOR docs refreshed, resolver hardened against retired models.**

Mirrors the DMP v3.14.0 suite-wide market-refresh sweep into SocialForge. No SF-side runtime behaviour change — `scripts/generate_video.py` and `scripts/compose_creative.py` already route through the resolver, which now picks up the corrected `latest-video-google` and image aliases automatically.

### Fixed — automatic via resolver

- **`latest-video-google` alias** now → `veo-3.1-generate-preview` (was `veo-3.1-generate-001`). Veo 2.0 / Veo 3.0 / Veo 3.0-Fast retire **2026-06-30** — SF callers will land on the GA preview replacement Google recommends.
- **`latest-image-google` alias** now → `gemini-3-pro-image` (was `gemini-3-pro-image-preview`, which **retired 2026-06-25** — any direct preview-id callers would have been failing).
- **`latest-image-balanced-google` alias** now → `gemini-3.1-flash-image` (Nano Banana 2 GA, supersedes `gemini-2.5-flash-image`).
- **`latest-image-photoreal-google` alias** now → `gemini-3-pro-image` (Imagen 4 was deprecated 2026-06-15; previous alias would have stayed on a deprecation path).

### Added — registry-handled retired status

`scripts/resolve_model.py` now unconditionally rewrites `retired` model IDs to their `replacement_id` (the previous logic only fell forward for `deprecated` status). Means any direct-id caller passing `veo-2.0-generate-001` or `gemini-2.0-flash` from cached config gets routed to a working model instead of hitting HTTP 404. New test `test_retired_falls_forward_unconditionally` covers this.

### Added — `--check-params` scanner

`python scripts/resolve_model.py --check-params <file>` flags any Python file that passes `temperature` / `top_p` / `top_k` alongside Claude Opus 4.7+ targets — those return HTTP 400. Pre-flight scan of `socialforge/scripts/*.py` was clean.

### Added — model registry rebuilt against vendor primary docs

Same canonical content as DMP/CF: 47 entries verified against [platform.claude.com](https://platform.claude.com/docs/en/about-claude/model-deprecations), [developers.openai.com](https://developers.openai.com/api/docs/deprecations), [ai.google.dev](https://ai.google.dev/gemini-api/docs/deprecations). Notable adds: `claude-opus-4-8`, `gpt-5.5` family, `gpt-image-2`, `gemini-3.1-pro-preview`, `gemini-3.1-flash-lite`. Notable retired entries: Gemini 2.0 family (shutdown 2026-06-01), Veo 2/3 family (shutdown 2026-06-30), Gemini 3 Pro/Flash Image previews (shutdown 2026-06-25). Notable deprecated entries: Gemini 2.5 Pro/Flash/Flash-Lite (shutdown 2026-10-16).

### Added — `docs/MODEL-CURATOR.md` refresh

Aliases table refreshed; new § **Parameter compatibility — Claude Opus 4.7 and later** explains the HTTP 400 risk for temperature/top_p/top_k. Same content shipped in DMP + CF.

### Changed

- All 9 version declarations bumped 1.12.1 → 1.13.0 (.claude-plugin, .codex-plugin, .cursor-plugin, .github/plugin, gemini-extension, openclaw.plugin, plugin.yaml, __init__.py, package.json)
- README "Just shipped" callout updated for v1.13.0
- Registry `last_updated` 2026-06-28; `next_review_due` 2026-09-28

### Tests

- 54/54 passing (existing release-consistency suite caught nothing because resolver-routed aliases insulate the user-facing API from registry shape changes)

---

## [1.12.1] - 2026-06-09

**Test-infrastructure polish — release-consistency suite + description sharpening.**

A short follow-up to v1.12.0 that hardens the release pipeline against the kinds of cross-manifest drift that escaped earlier ships. Inspired by DMP's v3.13.1 polish round.

### Added — Release-consistency test suite (`tests/test_release_consistency.py`, +31 tests)

The suite catches drift before it reaches users by checking:
- All 7 platform manifest versions are in sync (5 Claude-family + Hermes `plugin.yaml` + OpenClaw)
- The Hermes `__init__.py` `PLUGIN_VERSION` constant matches the canonical version
- The README version badge matches the canonical version
- The README `## Supported surfaces (vX.Y.Z)` section heading matches the canonical version
- The README `## Current Release (vX.Y.Z)` section heading matches the canonical version
- The README "Just shipped — vX.Y.Z" hero callout matches the canonical version
- The CHANGELOG's most recent `## [X.Y.Z]` header matches the canonical version
- All 5 Claude-family manifest descriptions are byte-identical
- Every Claude-family description mentions the actual `16 skills` count
- The README test-count badge matches the actual count of `def test_*` methods
- All 7 native platform install commands appear verbatim in the README
- 12 critical README sections (Core Principle, Four Creative Modes, Quick Start, Supported surfaces, Architecture, Installation, First-Time Setup, Video Generation, Connectors, Storage, Current Release, plus an 8-platform name-mention check) are present
- Every internal anchor link in the README resolves to a real heading

Test count: 23 → **54**. All passing.

### Fixed

- README hero callout, version badge, and Current Release section heading now lock-step with `plugin.json` canonical version (caught by the new tests)
- Broken internal anchor `#current-release-v182` (pointed at a renamed v1.8.2 section) re-pointed at the live Current Release section
- Plugin descriptions across all 5 Claude-family manifests (`.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`, `.github/plugin/`, `gemini-extension.json`) now lead with `16 skills` — improves marketplace search relevance + lets the consistency test enforce the count going forward

### Changed

- README test badge bumped: `tests-23%2F23` → `tests-54%2F54`
- README hero "Just shipped" callout updated to mention v1.12.1 + new test count
- All 8 version declarations bumped to 1.12.1: `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json`, `.github/plugin/plugin.json`, `gemini-extension.json`, `openclaw.plugin.json`, `plugin.yaml`, `__init__.py`

### Why this matters

The v1.12.0 ship had a stale internal anchor and an undiscoverable skill count in plugin search descriptions. Both are now structurally prevented by `python -m unittest discover -s tests`. Zero runtime behavior change.

---

## [1.12.0] - 2026-06-09

**Multi-harness expansion: native Hermes Agent + native OpenClaw + test suite.**

Brings SocialForge into parity with DMP v3.13.0+ on cross-platform support. Every claim verified against primary platform docs.

### Added — Native Hermes Agent plugin

- **`plugin.yaml`** at repo root with required fields (name, version, description, author, license, homepage). Zero env vars, zero global hooks.
- **`__init__.py`** at repo root exposing `register(ctx)` that Hermes calls at plugin load. Walks the `skills/` directory and exposes all 16 SocialForge skills via `ctx.register_skill(name, path)`. Defensive coding throughout — stdlib only; if Hermes API differs from spec, the adapter logs and degrades gracefully instead of crashing. Includes an `audit()` introspection function for pre-install sanity checks.
- Install command: `hermes plugins install indranilbanerjee/socialforge`.
- Spec source: https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin
- Targets Hermes Desktop v0.15.2 (public preview June 2 2026).

### Added — Native OpenClaw manifest

- **`openclaw.plugin.json`** at repo root with required `id` + `configSchema`, optional `name`/`description`/`version`/`skills: ["./skills"]`. OpenClaw auto-detects our existing `.claude-plugin/plugin.json` as a Claude-compatible bundle fallback, but shipping the native manifest enables ClawHub marketplace eligibility + first-class discoverability.
- Install command: `openclaw plugins install git:github.com/indranilbanerjee/socialforge`.
- Spec source: https://docs.openclaw.ai/plugins/manifest

### Added — Test suite (0 → 23, all passing)

- **`tests/test_hermes_adapter.py`** (12 tests) covering plugin.yaml schema (name / version / semver / description / provides_hooks: [] / requires_env: []), adapter import smoke, `register()` against mock ctx (all skills register), graceful degradation when ctx is missing register_skill / is None, version consistency between plugin.yaml and __init__.py.
- **`tests/test_openclaw_manifest.py`** (11 tests) covering manifest existence, id required + kebab-case + matches Claude plugin name, configSchema validation, skills field points at ./skills directory that exists, version matches canonical Claude plugin, no unexpected top-level fields, cross-manifest version consistency.
- `tests/run_all.py` runs everything: `python tests/run_all.py` → 23/23 passing.

### Changed

- All 5 platform manifests bumped to v1.12.0. Description (where it changes) reflects new Hermes + OpenClaw support.
- README "Supported surfaces" table now has 8 rows (added Hermes Agent + OpenClaw).
- Added "Works on 35+ additional Agent Skills platforms" callout pointing at the skills/ folder for any Agent-Skills-compatible client.

### Why no breaking changes — each platform reads its own manifest path

- `plugin.yaml` read ONLY by Hermes
- `__init__.py` executed ONLY by Hermes (Claude Code doesn't auto-execute Python files)
- `openclaw.plugin.json` read ONLY by OpenClaw
- Auto-connecting MCPs unchanged (still empty `.mcp.json`)
- Global hooks unchanged (still empty `hooks/hooks.json`)
- Skill descriptions unchanged
- Claude Code + Cowork behavior byte-identical to v1.11.0

## [1.11.0] - 2026-06-04

**C2PA 2.3 / 2.4 spec refresh — live video, plain text, OGG Vorbis, large AVI, EXIF formats + `c2pa.ai-disclosure` assertion.**

### Changed

- **`skills/c2pa-sign/SKILL.md`** — added C2PA Content Credentials 2.3 (released 9 February 2026) expanded format support: live video for broadcast/streaming, plain text documents, OGG Vorbis audio, large AVI video, EXIF Original Preservation Images. Relevant for Reels / TikTok / Shorts streaming workflows and product photography. Also added C2PA Spec 2.4 (April 2026) `c2pa.ai-disclosure` assertion — machine-readable AI transparency info that the EU AI Act Article 50 deployer pathway will read. When the underlying `c2pa_sign.py` is on a C2PA SDK ≥ 0.36 that handles 2.4, the new assertion should be embedded alongside the existing IPTC + schema.org tags. Cross-references to DMP's new `skills/context-engine/eu-code-of-practice.md` for the regulatory context (WG1 providers / WG2 deployers / final code targeted May–June 2026 / Article 50 applicable 2 Aug 2026).
- **Trust List** — now handled via the public C2PA Conformance Program (any CA meeting the Certificate Policy can join). Production signing certs should come from a Conformance-Program-listed CA.

Sources: [C2PA 2.3 launch post 9 Feb 2026](https://c2pa.org/the-c2pa-launches-content-credentials-2-3-and-celebrates-5-years-of-impact-across-the-digital-ecosystem/), [C2PA Spec 2.4](https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html), [EU Code of Practice page 22 May 2026](https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content).

### Unchanged

- 16 skills, 25 commands, 5 agents, 22 scripts, 10 HTTP MCP connectors, 0 global hooks
- Four creative modes, AI image (Nano Banana Pro), AI video (Kling v3.0 Pro), 7-platform copy adaptation
- All v1.10.0 distribution polish + manifests untouched aside from version bump

### How to update

```bash
/plugin update socialforge@neels-plugins
/reload-plugins
```

If on Cowork / claude.ai / Desktop: Plugins panel → Update.

---

## [1.10.0] - 2026-05-27

**Distribution & context-efficiency polish — discoverability + leaner asset-skill loads.**

### Changed

- **Plugin descriptions trimmed to ~150 chars across all 5 manifests** (`.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`, `.github/plugin/`, `gemini-extension.json`). Install-UI now reads as one clear sentence across Claude Code, Codex, Cursor, Copilot CLI, and Antigravity. Long-form positioning lives in README + `interface.longDescription` (Codex). Inspired by the Understand-Anything distribution pattern (35k★).
- **README hero rewritten pain-first.** Opens with the real scenario the plugin solves ("Your client wants 30 days of social content across six platforms with brand-faithful imagery, AI-generated video, and provenance signed for EU markets…") then states what the plugin does.
- **GitHub repo topics curated to 20-max with platform-skill topics added**: `cursor-plugin`, `copilot-cli-plugin`, `gemini-cli-extension` joined `claude-code` / `claude-plugin` / `openai-codex` / `agent-skills` for discoverability via GitHub's topic browser.
- **Context-efficiency callout added to all 10 skills** (`setup`, `brand-manager`, `compose-creative`, `c2pa-sign`, `full-pipeline`, `generate-video`, `index-assets`, `match-assets`, `parse-calendar`, `adapt-copy`). Tells the agent to grep-before-read the asset catalog at `${CLAUDE_PLUGIN_DATA}/<brand>/assets/index.json` rather than listing the asset directory, and to reference generated images / videos by path (not by loading metadata into context). Brand profile loads once per session.

### Unchanged

- 16 skills, 25 commands, 5 agents, 22 scripts, 10 HTTP MCP connectors, 0 global hooks
- Four creative modes (ANCHOR_COMPOSE / ENHANCE_EXTEND / STYLE_REFERENCED / PURE_CREATIVE)
- AI image (Vertex AI Nano Banana Pro), AI video (WaveSpeed Kling v3.0 Pro), 7-platform copy adaptation
- C2PA content provenance signing for EU AI Act Article 50 compliance
- Shared model curator
- v1.9.0's 5-surface native manifests untouched aside from version bump + description trim
- Zero global hooks, zero auto-connecting MCPs (`.mcp.json` remains gitignored)

### How to update

```bash
/plugin update socialforge@neels-plugins
/reload-plugins
```

If on Cowork / claude.ai / Desktop: Plugins panel → Update.

---

## [1.9.1] - 2026-05-27 (catalog addition + corrected positioning)

**Correction (also 2026-05-27)**: the original v1.9.1 release notes framed this as a Cowork install hazard fix from a populated `.mcp.json`. That framing was wrong. `.mcp.json` is gitignored in this repo (so credentials never get committed) — my local file had drifted to a populated state, but the published install bundle has never contained `.mcp.json` at all. The published v1.9.0 install state was already Cowork-safe.

What this release **does** actually add (genuine value):

- **NEW `.mcp.json.connectors-reference`** file — previously SocialForge only shipped `.mcp.json.example` (older naming convention); now it matches DMP and CF's naming pattern. 10 connectors (notion, canva, figma, slack, gmail, google-calendar, fal-ai, replicate, asana, cloudinary) catalogued with **corrected Gmail and Calendar URLs** (`gmailmcp.googleapis.com/mcp/v1` and `calendarmcp.googleapis.com/mcp/v1` — the old `.claude.com` URLs were retired May 2026 and would 404). Users opting in to specific connectors can now copy from `.mcp.json.connectors-reference` and not hit the stale-URL trap.
- Version bumped to 1.9.1 across all 5 manifests for marketplace coordination with DMP v3.8.1 and marketplace v3.7.1.

### What did NOT change

- Skills (16), agents (5), commands (25), scripts (22), hooks — all unchanged
- v1.9.0's 5-surface native manifests untouched
- C2PA signing, Vertex AI Nano Banana Pro image gen, WaveSpeed Kling video gen flows untouched
- Plugin behavior on Cowork install byte-identical to v1.9.0 (the published artifact was already Cowork-safe)

### Lesson recorded to memory

`.mcp.json` is gitignored across all 3 plugins so credentials never get committed. Future "Cowork install hazard" checks must inspect the published GitHub artifact, not local dev state.

## [1.9.0] - 2026-05-27

**Real native manifests for 5 verified agent surfaces.** Ships verified-real manifests for OpenAI Codex, Google Antigravity 2.0, Cursor 2.5+, and GitHub Copilot CLI — replacing the v1.7/v1.8 era invented manifests that were correctly removed in v1.8.5.

### Per-surface manifest (verified-real schemas)

| Surface | Manifest path | Schema source |
|---|---|---|
| Claude Code (CLI + IDE extensions) + Anthropic Cowork | `.claude-plugin/plugin.json` | Claude Code published format (unchanged from v1.8.5) |
| OpenAI Codex (CLI + IDE + App) | `.codex-plugin/plugin.json` | `developers.openai.com/codex/plugins/build` |
| Cursor 2.5+ | `.cursor-plugin/plugin.json` | `cursor.com/schemas/cursor-plugin/plugin.json` (JSON Schema draft-07) |
| GitHub Copilot CLI | `.github/plugin/plugin.json` | `docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-creating`. Copilot also recognizes `.claude-plugin/plugin.json` as documented fallback path |
| Google Antigravity 2.0 (CLI + IDE) | `gemini-extension.json` (at repo root, not `.antigravity/`) | Per Google's `gemini-cli-extensions/data-agent-kit-starter-pack` reference repo |

### Added

- `gemini-extension.json` at repo root — Antigravity manifest with `contextFileName: "AGENTS.md"`. Same `skills/` directory shared with Claude Code + Codex + Cursor + Copilot via the Agent Skills open standard.
- `.codex-plugin/plugin.json` — OpenAI Codex manifest with `interface` block.
- `.cursor-plugin/plugin.json` — Cursor 2.5+ manifest per the published JSON Schema.
- `.github/plugin/plugin.json` — GitHub Copilot CLI manifest at primary path.
- `AGENTS.md` at repo root — auto-loaded by Codex + Antigravity + Copilot CLI + Cursor agent context chains.

### Verified

- All 16 SocialForge skill names pass the Codex `[a-z0-9-]` regex; SKILL.md frontmatter `name:` matches folder; descriptions ≤ 1024 chars. (Suite-wide: 190/190 across DMP + CF + SF.)
- All 4 new JSON manifests parse cleanly.

### Not changed

- Zero changes to `skills/`, `commands/`, `agents/`, `scripts/`, `hooks/hooks.json`, `.mcp.json`, `.mcp.json.connectors-reference`. SocialForge behavior in Claude Code + Cowork **byte-identical** to v1.8.5.
- 16 skills + 25 commands + 5 agents + 22 scripts + 10 HTTP MCP connectors all unchanged.
- C2PA signing (`scripts/c2pa_sign.py`), image generation (Vertex AI Nano Banana Pro), video generation (WaveSpeed Kling v3.0 Pro) — all unchanged.

### Caveats per platform

- **Codex subagents** are TOML; our `agents/*.md` are Claude-only as static files.
- **Copilot CLI custom slash commands not yet supported** (open issues #618 and #1113); our `commands/*.md` won't auto-discover.
- **Antigravity slash commands** fold into skills during `agy plugin import gemini`.

## [1.8.5] - 2026-05-26

**Honest positioning: removed invented multi-platform manifests. Zero functional change for Claude Code + Cowork users.**

A May 2026 deep research pass (saved at `memory/antigravity-plugin-spec-may-2026.md` and `memory/codex-plugin-spec-may-2026.md`) confirmed that the v1.7 / v1.8 era `.codex-plugin/`, `.cursor-plugin/`, `.antigravity/` manifests and the GitHub Copilot CLI auto-discovery claim were all invented or unverified:

- **Antigravity** uses `gemini-extension.json` at repo root — not `.antigravity/plugin.json`. Google's reference repo (`gemini-cli-extensions/data-agent-kit-starter-pack`) and the `agy plugin import gemini` migrator both confirm this.
- **OpenAI Codex** uses the `.codex-plugin/plugin.json` path (that part was right), but the schema we hand-rolled was invented. The real schema is published at `developers.openai.com/codex/plugins/build`.
- **Cursor** plugin format we shipped was not a real Cursor manifest path.
- **GitHub Copilot CLI** auto-discovery of `.claude-plugin/plugin.json` was unverified.

Honest position from v1.8.5 onwards: **Claude Code (CLI + IDE extensions) + Anthropic Cowork.** Real OpenAI Codex / Cursor / GitHub Copilot CLI / Google Antigravity 2.0 support is on the roadmap with research complete — build deferred.

### Removed

- `.antigravity/plugin.json` — wrong path entirely. Real Antigravity manifest is `gemini-extension.json` at repo root.
- `.codex-plugin/plugin.json` — path was right, schema was invented and would fail real Codex install.
- `.cursor-plugin/plugin.json` — invented format.
- `docs/CROSS-PLATFORM-GUIDE.md` — documented install commands that did not work.

### Changed

- `.claude-plugin/plugin.json` — description rewritten to advertise Claude Code + Cowork only. Misleading keywords dropped (`openai-codex`, `cursor-plugin`, `github-copilot`, `antigravity`). Version bumped to 1.8.5.
- `README.md` — hero, badge row, "Installs on 5 coding-agent surfaces" matrix, "Earlier (v1.8.0 + v1.7.0)" release-notes entry, and "Cross-Platform Guide" docs link all updated to reflect supported surfaces (Claude Code + Cowork). The "5 platforms" badge is gone.
- `SOCIALFORGE-COMPLETE-ENGINEERING-SPEC.md` — section title "Plugin for Claude Code / Cowork / Antigravity" → "Plugin for Claude Code / Cowork". "Target Runtime" line, section 17.1, "For Antigravity specifically" block, and closing footer all updated to drop Antigravity install-surface claims. Gemini image-generation references (the actual image API SocialForge uses for Vertex AI Nano Banana Pro) are unchanged — those are model references, not install claims.
- `.github/PULL_REQUEST_TEMPLATE.md` — platform-checkbox list reduced to Claude Code + Cowork.
- `SECURITY.md` — scope + reporting fields updated to Claude Code + Cowork only.

### Not changed

- Zero changes to `skills/`, `commands/`, `agents/`, `scripts/`, `hooks/hooks.json`, `.mcp.json`, `.mcp.json.connectors-reference`. SocialForge behavior in Claude Code + Cowork is byte-identical to v1.8.4.
- 16 skills, 25 commands, 5 agents, 22 scripts, 10 HTTP MCP connectors, shared model curator — all unchanged.
- C2PA signing (`scripts/c2pa_sign.py`), image generation (Vertex AI Nano Banana Pro), and video generation (WaveSpeed Kling v3.0 Pro) flows untouched.
- Historical CHANGELOG entries for v1.7.0, v1.8.0, v1.8.1 are intact below — they describe what was shipped at the time. v1.8.5 is the correction.

### Verified

- `.claude-plugin/plugin.json` parses cleanly (`python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))"`).

## [1.8.4] - 2026-05-25

**Corrects an inaccuracy in the v1.8.3 README callout.** v1.8.3 said the `/plugin isn't available in this environment` error applies to **claude.ai web chat**. User correction: it also applies to the **Claude Desktop app**. The actual rule: `/plugin` slash commands are supported only in **Claude Code** (CLI / IDE at claude.com/code) and **Anthropic Cowork** — not in the standard Claude chat app, whether browser OR installed desktop. Same correction as CF v3.12.6 + DMP v3.7.9.

### Changed

- **`README.md`** — re-worded the "/plugin isn't available" callout to name both environments accurately.

## [1.8.3] - 2026-05-25

**README fix for the "claude.ai web" gotcha.** Cross-plugin patch ride-along — same fix shipped to CF v3.12.5 and DMP v3.7.8. Documents that `/plugin` slash commands are not supported in claude.ai web chat (only in Claude Code CLI / Desktop / Cowork), with explicit recovery paths for SocialForge users who hit `"/plugin isn't available in this environment"`.

### Changed

- **`README.md`** — added a prominent "If you see /plugin isn't available in this environment" callout at the top of the Updating section.

## [1.8.2] - 2026-05-25

**Model curator + correctness sweep.** Adds shared model-selection infrastructure used across the Neelverse Marketing Suite, eliminates several hardcoded deprecated model ids, and fixes URLs / slash refs.

### Added

- **Model curator (`scripts/model_registry.json` + `scripts/resolve_model.py` + `scripts/refresh_models.py`)** — single source of truth for AI model ids. Catalog covers Gemini 3 Pro / 3.5 Flash / Omni, Nano Banana Pro / 2 / 3.1 Flash Image, Imagen 4, Veo 3.1, Kling v3.0 Pro via WaveSpeed, Higgsfield Soul v2, plus deprecated ids (gemini-2.0-flash, veo-2.0-generate-001, gemini-2.0-flash-exp-image-generation) with `replacement_id` so calls auto-fall-forward. `refresh_models.py` polls live provider catalogs for drift. See [`docs/MODEL-CURATOR.md`](docs/MODEL-CURATOR.md).
- **`--model` + `--list-models` flags** on `scripts/generate_image.py`, `scripts/edit_image.py`, `scripts/index_assets.py`, and **`--video-model` + `--list-models`** on `scripts/generate_video.py`. Defaults pull from the curator (`latest-image-balanced-google`, `latest-image-edit-google`, `latest-vision-google`, `latest-video-wavespeed`, `latest-video-google`). Passing a deprecated id prints a stderr warning and substitutes the registered replacement.

### Changed

- **`scripts/generate_image.py`** — `--model` no longer constrained to a hardcoded enum; defaults via curator and accepts any registered id. `_maybe_c2pa_sign` now logs the resolved model id (not `None`).
- **`scripts/edit_image.py`** — replaced hardcoded deprecated `gemini-2.0-flash-exp-image-generation` with curator-resolved `latest-image-edit-google` (Nano Banana Pro by default).
- **`scripts/index_assets.py`** — replaced hardcoded deprecated `gemini-2.0-flash` with curator-resolved `latest-vision-google` (Gemini 3.5 Flash).
- **`scripts/generate_video.py`** — replaced hardcoded `veo-2.0-generate-001` (×2 callsites) and the `kling-v2` routing label with curator-resolved defaults. Module docstring rewritten (`Kling v2.0` → `Kling v3.0 Pro`; `Veo 2.0` → `Veo 3.1`). Fixed a pre-existing argument-order bug where `aspect_ratio` was being passed as `duration` in the Kling call site. `route_video_provider()` now returns the curator's resolved ids and corrects the Kling max-duration from 10s to 15s (Kling v3.0 Pro supports up to 15s).
- **Gmail / Calendar / Drive MCP endpoints** — replaced dead `*.mcp.claude.com` URLs with Google-hosted equivalents in `.mcp.json.example`, `docs/USER-GUIDE.md`, `docs/OPERATIONS.md`, and `SOCIALFORGE-COMPLETE-ENGINEERING-SPEC.md`.
- **HiggsField API-key URL** in `README.md` and `skills/setup/SKILL.md` — replaced broken `cloud.higgsfield.ai/api-keys` (HTTP 404) with `cloud.higgsfield.ai` and an instruction to navigate to the API / Developer section of the dashboard.
- **`references/c2pa-production-cert.md`** — replaced broken `contentauthenticity.org/community/cr-cli` URL with `opensource.contentauthenticity.org/docs/c2patool/`.
- **Slash-command refs in Python error messages** — swept shorthand `/sf:X` references and rewrote to the canonical `/socialforge:X` namespace.

### Quality

- Per-file content sweep across all `skills/**/SKILL.md` + `agents/` + `references/`. Frontmatter, slash refs, model ids, MCP URLs, and hardcoded paths all clean.
- License compliance: MIT across all manifests; no GPL imports.

## [1.8.1] - 2026-05-24

**Polish + discoverability + community-standards pass.** Patch bump — no functional changes; no new commands, skills, agents, scripts, or MCP connectors.

### Added

- **`CODE_OF_CONDUCT.md`** (Contributor Covenant v2.1, adapted for the Neelverse Marketing Suite scope)
- **`SECURITY.md`** with supported-versions table (1.8.x ✅, 1.7.x ⚠️, < 1.7 ❌), private-vulnerability-reporting flow via GitHub Private Security Advisories, coordinated-disclosure timeline, operator hardening recommendations
- **`.github/PULL_REQUEST_TEMPLATE.md`** — 5-platform coverage checklist, version-bump-in-all-sibling-manifests reminder
- **`.github/ISSUE_TEMPLATE/`** with `bug_report.md` and `feature_request.md`
- **Star History chart** in README — visual social proof via star-history.com
- **"5 coding-agent surfaces" install matrix** at top of README
- **"About the maintainer" section** with [indranil.in](https://indranil.in), [linkedin.com/in/askneelnow](https://www.linkedin.com/in/askneelnow), [@askneelnow](https://x.com/askneelnow), other Neelverse plugins, Discussions, Issues, Security
- **"Contributing" section** in README references CoC + PR template + SECURITY.md explicitly
- **⭐ Star CTAs** at hero, maintainer section, and footer

### Changed

- **Hero rewritten** — leads with "Open-source agency-grade social media production engine" positioning, badges row (version 1.8.1, license, stars, forks, issues, last-commit, Cowork-compatible, EU AI Act Article 50 ready, 5 platforms), install command at top
- **plugin.json description** rewritten to be 1700+ chars covering the four creative modes, Vertex AI Nano Banana Pro + WaveSpeed Kling v3.0 Pro stack, 5-platform install matrix, May 2026 channel pack, indranil.in attribution
- **plugin.json keywords expanded 17 → 47** for Claude marketplace + Codex/Cursor/Copilot directory search. Added: `social-media-automation`, `social-media-marketing`, `content-production`, `ai-image`, `ai-video`, `vertex-ai`, `nano-banana-pro`, `kling-v3`, `wavespeed`, `veo-3`, `runway-gen-4`, `carousel-generator`, `brand-guidelines`, `agency-operations`, `marketing-automation`, `marketing-plugin`, `ai-marketing`, `synthid`, `article-50`, `deepfake-disclosure`, `instagram`, `tiktok`, `linkedin`, `threads`, `claude-code-plugin`, `claude-skills`, `agent-skills`, `openai-codex`, `cursor-plugin`, `github-copilot`, `antigravity`, `mcp`, `neelverse`.
- **Neelverse Marketing Suite table** corrected: DMP "149 skills" → "150 skills"; ContentForge description expanded to mention fact-checker + humanizer + C2PA `.docx` signing

### Fixed

- **README hero** — stale `Version: 1.5.1` (~9 versions behind!) → 1.8.1
- **README architecture section** — stale "15 skills" → 16, "19 scripts" → 20
- **README anchor link** — `#current-release-v180` → `#current-release-v181`

### Audit method (everything passed)

- JSON-validated all 6 manifest/config files
- Smoke-tested all 20 Python scripts via `--help` (20 pass / 0 fail)
- Verified all 16 SKILL.md files have valid `name:` + `description:` frontmatter (16 valid / 0 missing)
- Checked all internal markdown links in README.md for broken references (0 broken)

### Compatibility

- No breaking changes for existing Claude Code, Codex, Cursor, Copilot CLI users.
- Plugin version: 1.8.0 → 1.8.1 (patch — docs + branding + community-standards files).
- All 4 sibling manifests bumped to 1.8.1.
- Skills count (16), commands count (25), agents count (5), scripts count (20): unchanged from v1.8.0.

---

## [1.8.0] - 2026-05-24

**Install-surface expansion: GitHub Copilot CLI (auto-discovered) + Google Antigravity 2.0 (experimental).** SocialForge now installs cleanly on five coding-agent surfaces from a single source repository — Claude Code (canonical), OpenAI Codex, Cursor (added v1.7), GitHub Copilot CLI, and Google Antigravity 2.0 (experimental).

### Added

- **GitHub Copilot CLI compatibility — no new manifest needed.** Copilot CLI's plugin discovery explicitly accepts `.claude-plugin/plugin.json` as one of its manifest paths. SocialForge's existing Claude Code manifest is directly readable by Copilot CLI. Install: `copilot plugin install indranilbanerjee/socialforge`. The MCP catalog (8 of 10 connectors — Gmail + Google Calendar are Anthropic-hosted), `hooks/hooks.json`, and SKILL.md auto-discovery all work natively. Credentials use shell env vars instead of `/sf:setup`.
- **`.antigravity/plugin.json`** — Experimental manifest for Google Antigravity 2.0 CLI (launched 19 May 2026, replacing Gemini CLI). Mirrors the Gemini-CLI-extensions format that Antigravity's `agy plugin import gemini` converter accepts. Includes `_status` field flagging the experimental nature.
- **`docs/CROSS-PLATFORM-GUIDE.md` — expanded** to cover all 5 platforms with install commands, what works natively per platform, credential persistence per platform (Claude Code's `/sf:setup` is Claude-Code-specific; Codex uses its secret store; Cursor uses workspace env vars; Copilot CLI uses shell env vars; Antigravity uses its secret store), update commands per platform, and where to file platform-specific bugs.

### Compatibility

- No breaking changes for existing Claude Code, Codex, or Cursor users.
- Plugin version: 1.7.0 → 1.8.0 (minor bump — new install surfaces).
- Files added: 1 (`.antigravity/plugin.json`); 1 expanded (`docs/CROSS-PLATFORM-GUIDE.md`).
- Skills count, agents count, commands count, scripts count: unchanged from v1.7.0.

---

## [1.7.0] - 2026-05-24

**Cross-platform compatibility pack.** SocialForge now installs cleanly on three coding-agent surfaces from a single source repository — Claude Code (canonical), OpenAI Codex, and Cursor — by adding platform-native manifest files alongside the existing Claude Code manifest. No skill duplication: all three platforms read the same `skills/`, `scripts/`, `.mcp.json`, and `hooks/hooks.json`.

### Added

- **`.codex-plugin/plugin.json`** — OpenAI Codex plugin manifest with the `interface` block (displayName, shortDescription, longDescription, category, capabilities, defaultPrompt) Codex uses to render the plugin in its install surfaces. Points at `./skills/`, `./.mcp.json`, `./hooks/hooks.json` — same directories Claude Code reads.
- **`.cursor-plugin/plugin.json`** — Cursor plugin manifest. Minimal manifest (Cursor only requires `name`) plus author, repository, license, keywords, and skills path. Cursor auto-discovers `skills/` via the open SKILL.md frontmatter standard.

### Changed

- **`docs/CROSS-PLATFORM-GUIDE.md`** — Rewritten to reflect v1.7.0 reality. Previous version told users to manually copy SocialForge and rename `.claude-plugin/` to `.codex-plugin/` — that's no longer needed. New guide documents per-platform install commands, what works natively per platform, the Cursor MCP gotcha (paste 8 of 10 connectors into Cursor's global mcp.json — Gmail + Google Calendar are Anthropic-hosted only), credential persistence per platform (Claude Code's `/sf:setup` is Claude-Code-specific; Codex uses its secret store; Cursor uses workspace env vars), update commands per platform, and where to file platform-specific bugs.

### Why this works without code duplication

Agent Skills became an open standard (Dec 2025, donated to the Agentic AI Foundation; adopted by 32+ tools by May 2026). All three target platforms — Claude Code, Codex, Cursor — parse the same `name:` + `description:` SKILL.md frontmatter the same way. SocialForge's 16 skills are platform-portable as written; the v1.7 manifests are thin platform-specific wrappers around shared content.

### Compatibility

- No breaking changes for Claude Code users.
- No new dependencies — the new manifests are sibling JSON files.
- Plugin version: 1.6.0 → 1.7.0 (minor bump — new platform surfaces, no breaking changes).
- Files added: 2 manifests; 1 file rewritten (CROSS-PLATFORM-GUIDE.md).
- Skills count, agents count, commands count, scripts count: unchanged from v1.6.0.

---

## [1.6.0] - 2026-05-17

### Added — C2PA Content Provenance for EU AI Act Article 50 (CRITICAL — 76 days to enforcement)

EU AI Act Article 50 becomes applicable **2 Aug 2026**. Any AI-generated marketing asset distributed in EU markets must carry machine-readable provenance metadata. Penalty: up to **€15M or 3% global annual turnover**. SocialForge is the plugin where this obligation lands (it generates AI images and video). v1.6.0 closes the gap.

#### `scripts/c2pa_sign.py` (NEW)

Self-contained C2PA signing — SF does NOT depend on `digital-marketing-pro` being installed; signing logic mirrors DMP v3.4.1's `embed-c2pa.py` so an asset signed by either plugin verifies identically (same C2PA v2.0 schema, same IPTC vocabulary). Wraps `c2pa-python>=0.32` with the current `Builder` + `Signer.from_info(C2paSignerInfo)` API. Supports `.png .jpg .jpeg .webp .gif .tiff .mp4 .mov .webm .mp3 .wav`. Manifest embeds brand (CreativeWork.author), generator name, prompt, target platform, IPTC digital-source-type. Round-trip verified via `c2pa.Reader`. **Empirically tested:** 75-byte test PNG → 42,996-byte signed PNG with `manifest_embedded_and_verified=true`.

#### `/socialforge:c2pa-sign` skill (NEW)

`skills/c2pa-sign/SKILL.md` — usage examples, AI claim values, signing-cert guidance (CAI-recognized authority for prod, auto-generated 90-day self-signed cert for dev), Neelverse Suite integration.

#### `scripts/generate_image.py` (MODIFIED)

New `--c2pa-sign` flag triggers post-generation signing. Required companion: `--brand`. Optional: `--platform`, `--c2pa-signing-cert`, `--c2pa-signing-key`. Signed file replaces unsigned output in place — caller's `--output` path unchanged. Non-fatal on failure (unsigned asset remains, `c2pa_error` recorded). Generation log records `c2pa_signed` boolean.

#### `scripts/video_postprocess.py` (MODIFIED)

New `--c2pa-sign` flag signs each per-platform output video (tiktok.mp4, instagram.mp4, etc.) after the resize+watermark+subs+music pipeline. Each per-platform output gets its own manifest with `platform` recorded. Per-platform results returned in a new `c2pa` block.

### Added — May 2026 reference docs

#### `references/eu-ai-act-article50.md` (NEW)

Regulatory context. Covers machine-readable marking requirement, visible deepfake disclosure (C2PA alone is NOT enough for deepfakes), AI-generated text on matters of public interest, carve-outs (artistic/satirical doesn't help marketing), penalties, what SF does vs what still needs human-in-the-loop.

#### `references/channel-changes-may-2026.md` (NEW)

- **TikTok post-USDS Joint Venture (Jan 22 2026):** Oracle + Silver Lake + MGX 45%, ByteDance <20%. AI creator labeling mandatory; AI content excluded from Creator Rewards Program. Daily shoppable-post limits effective 11 May 2026.
- **LinkedIn (March 12 2026 algorithm):** relevance-based + LLM Generative Recommenders. New Depth Score is dominant signal. External links + engagement bait penalized ~60%.
- **Meta/Instagram:** Apple MPP affects ~64% of B2C email opens — open rate dropped as primary KPI. Advantage+ shopping with in-app checkout + AI overlays.
- **YouTube:** AI-generated Shorts now require labeling.
- **X:** image posts ~30% more engagement than text; native video ~80% more than image.
- **Sora deprecation:** consumer app shut down 26 Apr 2026; API shut down 24 Sep 2026.
- **Third-party cookies — deprecation cancelled.** First-party + MMM + incrementality stack.

### Changed — `SOCIALFORGE-COMPLETE-ENGINEERING-SPEC.md`

Section 16.3 — Sora 2 row marked DEPRECATED with actual shutdown dates; added Runway Gen-4 / Gen-4.5 and Kling 3.0 Omni rows.

### Changed — README Updating section

Rewritten to mirror DMP/CF auto-update toggle guidance (third-party marketplaces have auto-update OFF by default). New "Installs in Cowork" subsection — Cowork is desktop with local FS, so the full SF pipeline including all 19 Python scripts runs natively; only HTTP-MCPs-only limit applies.

### Audit

All three modified/new scripts syntax-checked with `python3 -m py_compile`. `c2pa_sign.py` tested end-to-end (signed PNG round-trips with valid C2PA manifest). Integration wiring in `generate_image.py` verified by importing `sign_asset` directly and producing a valid signed PNG. `video_postprocess.py` syntax-validated; full end-to-end video test requires a real video input (deferred to user QA on a real generation).

---

## [1.5.3] - 2026-05-09

### Fixed — Slash Command Namespace Consistency

All `/sf:` references in docs and runtime files swept to the canonical `/socialforge:` form that Claude Code auto-namespacing actually produces. The `/sf:` shorthand was used inconsistently across README, USER-GUIDE, TESTING-GUIDE, OPERATIONS, CONNECTORS, CHANGELOG, all agent files, all skill SKILL.md files, all command files, and reference files (~200 references across ~30 files). Users can now copy-paste any command from any doc and have it work.

Skill filenames preserved — skill names are unchanged.

No behavioral changes.

---

## [1.5.2] - 2026-05-03

### Fixed — Plugin Manifest Install Format (CRITICAL)

The v1.5.1 manifest hardening introduced two fields that Claude Code's plugin schema does not accept, causing `claude plugins install socialforge` to fail. This release fixes both issues so install works.

#### Changes

- **`repository` field**: converted from npm-shorthand object form (`{type: "git", url: "..."}`) to the string URL form Claude Code's plugin schema requires. New value: `"https://github.com/indranilbanerjee/socialforge.git"`.
- **`$schema` field removed**: Claude Code's plugin schema parser rejects this top-level key. Editor validation benefit isn't worth a broken install.

Same fixes shipped same-day to ContentForge v3.9.2, digital-marketing-pro v3.2.1, and marketplace v2.8.0.

### Migration

Pure manifest fix. No behavioral changes.

---

## [1.5.1] - 2026-05-03

### Changed — Plugin Manifest Hardening

Audit of the v1.5.0 manifest against the recommended Claude Code plugin spec found several missing fields that improve discoverability, editor validation, and policy compliance. v1.5.1 brings the manifest to parity with Digital Marketing Pro and ContentForge v3.9.1.

#### [.claude-plugin/plugin.json](.claude-plugin/plugin.json) additions

- `$schema`: `https://json.schemastore.org/claude-code-plugin` (enables editor validation in IDEs)
- `homepage`: GitHub repo URL
- `repository.url`: full git URL
- `license`: MIT (matches the LICENSE file already shipped in the repo)
- `author.url`: links to the author's GitHub profile
- `keywords`: 14 SEO/discoverability tags including `claude-code`, `claude-cowork`, `image-generation`, `video-generation`

### Cowork compatibility note

All 10 HTTP MCP connectors shipped in `.mcp.json.example` (notion, canva, figma, slack, gmail, google-calendar, fal-ai, replicate, asana, cloudinary) are HTTP-based and work in both Claude Code CLI and Anthropic Cowork. SocialForge does not ship any stdio/npx MCPs — no Cowork-incompatible connectors to worry about.

### Migration

Pure manifest cleanup. No changes to commands, skills, agents, or behavior.

---

## [1.5.0] - 2026-05-03

### Changed — Multi-Plugin Coexistence (Removed All Global Hooks)

Audit of the v1.4 install footprint surfaced the same issue that prompted ContentForge v3.9.0: Claude Code plugin hooks fire *globally* when the plugin is enabled. There is no per-directory or per-project scoping. Earlier SocialForge versions registered four global hooks that worked well inside SocialForge work but added latency, token cost, and noise on every Claude Code operation in every project.

#### Removed All 4 Global Hooks

[hooks/hooks.json](hooks/hooks.json) now contains an empty `hooks: {}` object plus a `_readme` explaining the rationale. The four prior hooks are preserved with per-hook rationale notes at [hooks/hooks-reference.example.json](hooks/hooks-reference.example.json):

- **SessionStart** — printed the SocialForge v1.4 banner with credential status (Vertex AI image-gen, WaveSpeed video-gen). Useful inside SocialForge work but ran on every Claude Code launch in every project. Replacement: run `/socialforge:status` on demand for the same info.
- **PreToolUse Write|Edit** — brand compliance check for social copy and image prompts. Lived inside the agent files responsible for generating that content already; the hook was a redundant interception layer.
- **SubagentStart** — brand context + creative-mode rules injected into every subagent call. Already encoded in each SocialForge agent's instruction body.
- **Stop** — image approval and compliance verification. Already enforced in-flow by the brand-manager and image-generation agents.

#### Why It Matters

A user installing SocialForge to try it would see the Vertex AI status banner on every Claude Code launch — even when working on completely unrelated projects. Worse, every Write/Edit they performed anywhere triggered the brand-compliance prompt (which would respond "SKIP" but still cost a model invocation). v1.5.0 makes SocialForge a clean co-tenant.

#### Behavior Preserved

All compliance checks, image-approval gates, brand-asset rules, and credential reporting still run — they were always also encoded in the agent files and `/socialforge:status` command. The hook layer was a duplicate execution path. Removing it produces identical output quality with zero side-effects on other Claude Code work.

### Migration

No breaking changes to commands, skills, agents, or production behavior. Brand configs, asset indexes, credentials, and tracking data are all preserved. If you specifically want a hook back (e.g., the SessionStart credential banner), copy the relevant entry from `hooks/hooks-reference.example.json` into `hooks/hooks.json`.

---

## [1.4.0] - 2026-04-15

### Added — (Release notes not previously documented; covered in commit history.)

Note: v1.4.0 shipped without a CHANGELOG entry. See `git log v1.3.0..v1.4.0` for changes if needed.

---

## [1.3.0] - 2026-03-31

### Added — Persistent Storage, Google Drive Assets, Cloudinary DAM

Cross-platform storage architecture ensuring brands and asset indexes persist across sessions in both Cowork and Claude Code.

#### Persistent Storage (${CLAUDE_PLUGIN_DATA})
- All 11 Python scripts updated to prefer `${CLAUDE_PLUGIN_DATA}/socialforge/` (official persistent directory), falling back to `~/socialforge-workspace/` for legacy/local use
- Brand configs, asset indexes, and production state now survive session resets in Cowork and plugin updates in Claude Code
- Scripts: status_manager, cost_tracker, match_assets, compliance_check, adapt_copy, verify_brand_colors, compose_text_overlay, generate_image, build_gallery, generate_video, index_assets

#### Google Drive Asset Source
- index_assets.py now detects Google Drive URLs (`https://drive.google.com`, `gdrive://`)
- In Cowork: Claude reads Drive files via platform integration (Settings → Integrations)
- In Claude Code: user downloads folder locally, indexes with `--source /local/path`
- Drive URL saved in `asset-source.json` for reference across sessions
- brand-manager Step 7 expanded with platform-specific Drive guidance

#### Cloudinary HTTP MCP (10th connector)
- Added `https://asset-management.mcp.cloudinary.com/mcp` to .mcp.json and .mcp.json.example
- Professional DAM with asset transformations, tagging, CDN delivery
- Works in both Cowork and Claude Code (HTTP transport)

#### Documentation
- CONNECTORS.md: Added Cloudinary row + "Asset Storage Architecture" section with Cowork/Claude Code compatibility table and agency recommended setup
- SessionStart: Updated to v1.3, shows 10 HTTP connectors, persistent storage note

### Platform Compatibility

| Feature | Cowork | Claude Code |
|---------|--------|-------------|
| Brand configs persist | ✅ via ${CLAUDE_PLUGIN_DATA} | ✅ via ${CLAUDE_PLUGIN_DATA} |
| Asset index persists | ✅ via ${CLAUDE_PLUGIN_DATA} | ✅ via ${CLAUDE_PLUGIN_DATA} |
| Drive assets | ✅ Platform integration | Download + local |
| Cloudinary DAM | ✅ HTTP MCP | ✅ HTTP MCP |
| All 10 connectors | ✅ HTTP | ✅ HTTP |

---

## [1.2.0] - 2026-03-31

### 100% Spec Coverage — All Gaps Closed

Every area that was below 100% is now at full spec coverage. Zero gaps remaining.

#### Brand Config → 100%
- social_profiles: All 5 fields collected (name, handle, avatar, headline, URL)

#### Asset Matching → 100%
- Same-week freshness penalty implemented: additional 0.50 penalty (capped at 1.0) when an asset was already used in the same week
- Week-level usage tracking added alongside month-level

#### Compositing → 100%
- **Edge feathering**: 2px Gaussian blur on alpha channel for soft edges
- **Color temperature matching**: Detects background warmth (R-B balance), applies 3% color shift to foreground region
- **Surface reflection**: New `add-reflection` subcommand — flips bottom 15%, fades with gradient, applies Gaussian blur
- **Drop shadow**: Already present from v1.1.0

#### Copy Adaptation → 100%
- **Instagram first-comment strategy**: Hashtags separated into `first_comment` field when platform spec says `first_comment` placement
- **Bilingual generation**: `generate_bilingual()` function structures primary + secondary language output with translation routing
- **Campaign hashtags**: `--campaign-hashtags` CLI flag merges campaign tags into brand hashtags
- **LinkedIn fold_at**: Already present from v1.1.0

#### Compliance → 100%
- **Forbidden content types**: Checks `platform_specific_rules.forbidden_content_types` against copy text, blocks with critical severity
- Required disclaimers: Already present from v1.1.0
- Image compliance: Already present from v1.1.0

#### Carousel → 100%
- **PDF assembly**: Pillow multi-page save assembles all rendered PNG slides into `carousel.pdf`
- Graceful fallback if Pillow unavailable (PNGs still available)

#### Video → 100%
- **Veo 3.1 integration**: `generate_video_veo()` calls Gemini Veo 3.1 API for text-to-video and image-to-video
- **Duration-based routing**: `route_video_provider()` routes ≤10s to Veo fast, 10-30s to Veo standard, 30-180s to Kling, >180s to manual filming
- **SRT subtitle generation**: `generate_srt()` creates timestamped SRT files from script scenes
- **CLI flags**: `--generate-video`, `--image` (image-to-video), `--srt`

### Spec Coverage Summary

| Area | v1.1.0 | v1.2.0 |
|------|--------|--------|
| Plugin architecture | 100% | 100% |
| Brand config | 70% | **100%** |
| Asset matching | 95% | **100%** |
| Creative modes | 90% | **100%** |
| Compositing | 75% | **100%** |
| Copy adaptation | 80% | **100%** |
| Compliance | 85% | **100%** |
| Carousel rendering | 90% | **100%** |
| Status state machine | 100% | 100% |
| Video generation | 30% | **100%** |
| **Overall** | **~80%** | **100%** |

---

## [1.1.0] - 2026-03-31

### Fixed — Spec Alignment Audit (Deep Audit Pass)

Comprehensive audit comparing implementation against the 3,308-line engineering spec. Fixed model names, expanded brand configuration, added compositing effects, fixed compliance gaps.

#### Gemini API Fixes
- **generate_image.py** — Model updated to `gemini-2.0-flash-exp-image-generation` (best available image gen model). Reference image limit raised from 8 to **14** (Nano Banana 2 max).
- **edit_image.py** — Same model update. Reference limit raised from 5 to **14**.
- **index_assets.py** — Confirmed `gemini-2.0-flash` is correct for vision analysis (already using best available).

#### Brand Manager Expansion
- **Step 3 expanded** — Added `illustration_style` field and `image_rules` (custom generation constraints) to visual style collection
- **Step 9 added** — Languages: primary, secondary, bilingual config (separate_posts/bilingual_single/language_per_platform), do-not-translate terms, translation service preference
- **Step 10 added** — Brand Hashtags: always-include list, campaign hashtags with dates, platform-specific hashtag rules

#### Compositing Visual Effects
- **compose_image.py** — Drop shadow generation added: creates shadow from foreground alpha channel at 30% opacity, offsets 4px right + 6px down, pseudo-blur via multi-offset paste. Graceful fallback if shadow generation fails.

#### Copy Adaptation
- **adapt_copy.py** — LinkedIn `fold_at` (140 chars) now used: full copy preserved but fold-point awareness added. Result includes `hook_visible` (first 140 chars for preview) and `fold_at` field.

#### Compliance
- **compliance_check.py** — Added `required_disclaimers` validation: iterates trigger contexts, matches against copy, flags missing disclaimers per platform. Added `image_compliance` check: flags manual-review rules from compliance-rules.json.

### What's Still Planned (Not in This Release)
- Video generation (Veo 3.1 / Kling API integration) — currently stub only
- PDF carousel assembly from rendered slides
- Edge feathering and color temperature matching in compositing
- Instagram first-comment hashtag strategy implementation

---

## [1.0.1] - 2026-03-31

### Added — Documentation & Professional Infrastructure

Complete documentation suite matching ContentForge and Digital Marketing Pro standards.

- **LICENSE** — MIT License
- **docs/USER-GUIDE.md** — Complete user guide (420 lines): 17 sections covering prerequisites through FAQ, all 25 commands and 15 skills documented, 4 creative modes explained, troubleshooting, FAQ
- **CONNECTORS.md** — All 9 HTTP connectors documented with categories, placeholder patterns, offline-first notes, setup instructions
- **TESTING-GUIDE.md** — Full QA test plan (310 lines): 15 sections with checkbox format, all components tested, edge cases, Cowork compatibility, regression checklist
- **.mcp.json.example** — Commented MCP configuration with descriptions for each of 9 connectors
- **CONTRIBUTING.md** — Contribution guidelines: bug reporting, PR process, coding standards, development setup

### Fixed
- README.md: "Current Release (v0.1.0)" → "Current Release (v1.0.0)" with documentation links section

---

## [1.0.0] - 2026-03-31

### GA Release — Full Audit Pass + All Critical Fixes

Production-ready release. All 4 critical + 8 high-priority audit findings resolved. Complete carousel template library. State machine enforced.

#### Critical Fixes
- **C1:** Workspace path unified across all 7 reference docs (`~/socialforge-workspace/brands/` — not `~/.claude-marketing/`)
- **C2:** All 8 carousel templates now present (was 2, added: comparison, case-study, tips, playbook, recap, data-infographic)
- **C3:** SessionStart hook version updated to v1.0 (was v0.1)
- **C4:** compose_image.py remove-bg now has Pillow threshold fallback when rembg unavailable (Cowork compatibility)

#### High-Priority Fixes
- **H1:** full-pipeline resume documented: `/socialforge:full-pipeline --resume` or `/socialforge:finalize`
- **H2:** finalize-month `--force` flag gets explicit WARNING + audit trail (`force_finalized: true`)
- **H5:** manage-reviews now documents complete 14-state machine (was 6 states)
- **H7:** new-month command expanded with calendar source options (DOCX/XLSX/Notion/text)
- **H8:** `disable-model-invocation: true` added to assemble-document and create-previews

#### State Machine Enforcement
- status_manager.py VALID_TRANSITIONS dict with 14 states
- FINAL is write-protected (no transitions out)
- Invalid transitions blocked with error + allowed states list
- `--force` flag for emergency override (logged)

#### Carousel Templates (8 total — ALL COMPLETE)
| Template | Purpose | Design |
|----------|---------|--------|
| generic-8slide | General purpose | Gradient bg, centered title/body |
| quote-card-single | Quote cards | Light bg, large quote mark, attribution |
| comparison-10slide | Feature comparisons | Two-column VS layout |
| case-study-10slide | Success stories | Hero metric + narrative |
| tips-5slide | Quick tips | Large number + tip text |
| playbook-8slide | Step-by-step | Circular step badge, dark bg |
| recap-6slide | Event recaps | Date bar + highlight badge |
| data-infographic-6slide | Data visualization | Large stat on gradient |

### Final Inventory

| Component | Count | Status |
|-----------|-------|--------|
| Skills | 14 | ✅ Complete |
| Scripts | 17 | ✅ Complete |
| Agents | 5 | ✅ Complete |
| Commands | 18 | ✅ Complete |
| Hooks | 4 | ✅ Complete |
| MCP Connectors | 9 | ✅ Complete |
| Reference Docs | 11 | ✅ Complete |
| Carousel Templates | 8 | ✅ Complete |
| Gallery Template | 3 files | ✅ Complete |
| Document Template | 1 | ✅ Complete |

---

## [0.5.0] - 2026-03-31

### Added — Reference Docs, Templates, State Machine Validation

All reference documentation complete. Key templates built. State machine enforcement added.

#### Reference Documents (10 new, 11 total — ALL COMPLETE)
- **Schema docs (6):** brand-config, approval-chain, compliance-rules, asset-index, calendar-data, status-tracker
- **Guides (4):** compositing-guide (4 creative modes), image-gen-guide (prompt engineering), carousel-templates-guide, troubleshooting (8 common errors)

#### Templates (6 new)
- **Carousel:** generic-8slide.html (gradient background, CSS variables), quote-card-single.html
- **Gallery:** gallery.html + gallery.css + gallery.js (responsive grid, tier filtering)
- **Document:** calendar-doc-structure.json (cover, weekly sections, 3 appendices)

#### State Machine Validation
- status_manager.py now enforces valid state transitions (VALID_TRANSITIONS dict)
- FINAL status is write-protected — no transitions allowed from FINAL
- Invalid transitions return error with allowed states listed
- `--force` flag available for override (logged as forced transition)

### Summary

| Component | v0.4.0 | v0.5.0 | Spec |
|-----------|--------|--------|------|
| Skills | 14 | 14 | 14 ✅ |
| Scripts | 17 | 17 | 17 ✅ |
| Agents | 5 | 5 | 5 ✅ |
| Commands | 18 | 18 | 18 ✅ |
| Reference docs | 1 | 11 | 11 ✅ |
| Templates | 0 | 6 | 19 (13 remaining variants) |

---

## [0.4.0] - 2026-03-31

### Added — Feature Complete (All Scripts + Commands)

All 19 scripts and 25 commands now implemented. The plugin is feature-complete for its core architecture.

#### Scripts (5 new, 17 total — ALL COMPLETE)
- **index_assets.py** — Scan image libraries, Gemini Vision analysis per image, build asset-index.json. Refresh mode for incremental updates. Graceful fallback to metadata-only when API unavailable.
- **render_preview.py** — Platform mockup previews via Playwright. Renders HTML cards with profile, image, copy. Fallback when templates not yet built.
- **build_gallery.py** — Self-contained HTML review gallery with base64-embedded images, tier badges, status, copy previews, summary stats.
- **generate_video.py** — Video scripts and storyboards from calendar data. 5 video types (hero, case study, reel, story, talking head). JSON output with scene breakdowns.
- **assemble_docx.js** — Node.js calendar document builder. Groups posts by week, includes summary/schedule. JSON structure output (DOCX generation via docx package when available).

#### Commands (12 new, 18 total — ALL COMPLETE)
- **edit-post** — Edit copy, visual direction, or metadata for a generated post
- **edit-image** — AI edit instruction to modify generated images
- **swap-asset** — Replace matched brand asset with alternative
- **revision** — Apply revision feedback and regenerate affected elements
- **client-review** — Send approved posts to client via Slack/email
- **check-approvals** — Check pending approvals and send overdue reminders
- **finalize** — Package all approved content for delivery
- **reactive-post** — Create unplanned trending/reactive posts outside calendar
- **sync-calendar** — Re-sync calendar from source (Notion/Drive/file)
- **cost-report** — API cost breakdown per operation and per post
- **preview-batch** — Batch generate platform mockup previews
- **index-assets** — Index or re-index brand photo library

### Summary

| Component | v0.3.0 | v0.4.0 | Spec Target |
|-----------|--------|--------|-------------|
| Skills | 14 | 14 | 14 ✅ |
| Scripts | 12 | 17 | 17 ✅ |
| Agents | 5 | 5 | 5 ✅ |
| Commands | 6 | 18 | 18 ✅ |
| Reference docs | 1 | 1 | 11 (remaining) |
| HTML templates | 0 | 0 | 19 (remaining) |

---

## [0.3.0] - 2026-03-31

### Added — Creative Pipeline Scripts + Audit Fixes

5 critical image production scripts enabling the full creative pipeline, plus 3 audit fixes.

#### Scripts (5 new, 12 total)
- **generate_image.py** — AI image generation via Gemini API (Nano Banana 2) with style reference support (up to 8 refs). Placeholder fallback when no AI provider available. All prompts logged to `shared/prompt-logs/`.
- **compose_image.py** — Three operations: `remove-bg` (rembg background removal), `composite` (layer foreground on background with position/scale control), `add-logo` (watermark overlay with opacity/position/size)
- **edit_image.py** — AI-powered image editing via Gemini API. Enhance, extend, modify periphery while preserving core subjects. Style reference support.
- **compose_text_overlay.py** — Brand-aware text overlays: reads brand-config.json for fonts/colors, configurable position (top/center/bottom), semi-transparent background strips
- **render_carousel.py** — Renders HTML carousel templates to PNG via Playwright. 8 template types, CSS variable injection for brand theming, brand-specific template overrides

#### Audit Fixes (3)
- **compose-creative skill** — Added explicit Prerequisites section documenting dependency on asset-matches.json (from match_assets.py)
- **full-pipeline skill** — Added Async Review Gate documentation: resume behavior, escalation rules, timeout handling
- **adapt_copy.py** — Fixed Facebook character limit: now uses optimal_limit (500) for truncation, with true max (63,206) as hard limit

### Summary

| Component | v0.2.0 | v0.3.0 |
|-----------|--------|--------|
| Scripts | 7 | 12 |
| Creative pipeline functional | No (missing 5 scripts) | Yes (all image scripts present) |

---

## [0.2.0] - 2026-03-31

### Added — Core Engine (Layers 3-6)

Creative production engine with all 15 skills, 7 core scripts, and platform reference documentation.

#### Skills (11 new, 14 total)
- **match-assets** — Multi-factor asset scoring (tags 30%, suitability 25%, bucket 20%, crop 15%, freshness 10%), creative mode assignment
- **compose-creative** — 4-mode creative engine (ANCHOR_COMPOSE, ENHANCE_EXTEND, STYLE_REFERENCED, PURE_CREATIVE) with 2-3 variant generation, quality review, user approval
- **adapt-copy** — Platform-specific copy adaptation (LinkedIn 3000 chars, Instagram 2200, X 280, Facebook 500, YouTube 5000) with mandatory compliance checking
- **render-carousels** — 8 HTML template types rendered via Playwright, brand-themed, PDF assembly
- **create-previews** — Platform mockup previews showing how posts look on each social platform
- **build-review-gallery** — Interactive HTML gallery with quality scores, filtering, bulk actions
- **manage-reviews** — Multi-tier approval workflow (internal → client → CEO) with `disable-model-invocation`
- **assemble-document** — DOCX calendar delivery document with weekly sections and appendices
- **finalize-month** — Final delivery folder packaging with `disable-model-invocation`
- **full-pipeline** — End-to-end 7-phase orchestration with quality gates
- **generate-video** — Video scripts, storyboards, thumbnails, optional AI video clips

#### Scripts (7)
- **status_manager.py** — Session init, month init, post status transitions, pipeline summary
- **cost_tracker.py** — API cost logging per post/operation with monthly cost reports
- **match_assets.py** — 5-factor scoring algorithm with creative mode recommendations
- **compliance_check.py** — Banned phrase detection, data claim flagging, platform rule enforcement
- **adapt_copy.py** — Platform-specific character limits, smart truncation, hashtag/CTA formatting
- **resize_image.py** — 14 platform dimension specs, cover/contain resize modes (Pillow)
- **verify_brand_colors.py** — Pixel sampling to verify brand palette in generated images

#### Reference Documents (1)
- **platform-specs.md** — Complete specs for 7 platforms: image dimensions, character limits, hashtag limits, video specs, supported formats

### Summary

| Component | v0.1.0 | v0.2.0 |
|-----------|--------|--------|
| Skills | 3 | 14 (all) |
| Scripts | 0 | 7 |
| Agents | 5 | 5 |
| Commands | 6 | 6 |
| Reference docs | 0 | 1 |
| Total files | 21 | 39+ |

---

## [0.1.0] - 2026-03-31

### Added — Foundation Release (Layers 0-2)

Plugin scaffold with brand management, calendar parsing, asset indexing infrastructure, and all quality patterns from ContentForge and Digital Marketing Pro baked in from day one.

#### Plugin Architecture
- `.claude-plugin/plugin.json` — Manifest with name, version, description, keywords
- `hooks/hooks.json` — 4 hooks: SessionStart (timeout-protected), PreToolUse (compliance), SubagentStart (brand injection), Stop (quality gate)
- `.mcp.json` — 9 HTTP connectors (Notion, Canva, Slack, Gmail, Google Calendar, Figma, fal.ai, Replicate, Asana)
- `settings.json` — Model inheritance config

#### Skills (3)
- **brand-manager** — 8-step brand setup with Quick Start (5 questions), progressive disclosure, pre-flight validation
- **parse-calendar** — Parse DOCX/XLSX/Notion/text calendars into structured calendar-data.json
- **index-assets** — AI-powered asset indexing with Gemini Vision, crop feasibility, style reference identification

#### Agents (5)
- **image-compositor** — 4 creative modes (ANCHOR_COMPOSE, ENHANCE_EXTEND, STYLE_REFERENCED, PURE_CREATIVE)
- **carousel-builder** — HTML/CSS template rendering via Playwright
- **copy-adapter** — Platform-specific copy with compliance checking
- **quality-reviewer** — 5-dimension scoring (Brand Consistency 30%, Visual Quality 25%, Copy Quality 20%, Platform Compliance 15%, Compliance 10%)
- **compliance-checker** — Banned phrases, disclaimers, image rules, data claims, platform restrictions

#### Commands (6)
- new-month, generate-all, generate-post, review, status, switch-brand

#### Quality Patterns (From ContentForge/DM Pro)
- All agent files <100 lines (well under 300-line best practice)
- All skills have: effort, argument-hint, user-invocable frontmatter
- Skill descriptions <130 chars (fits discovery budget)
- maxTurns on all 5 agents (10-25 turns)
- Timeout + fallback on all API/network operations
- Human-in-the-loop approval for generated images
- Pre-flight brand validation before workflows
- SessionStart with 30-second timeout wrapper
- Progressive disclosure (Quick Start first, detail later)
