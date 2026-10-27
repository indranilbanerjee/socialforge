# SocialForge — Directory Submission Bundle

Prepared 2026-08-16; checked again on 2026-10-27 against Anthropic's plugin pre-submission checklist (claude.com/docs/directory). Items marked **[owner action]** need the account holder.

## Targets

| Directory | Route | Status |
|---|---|---|
| Anthropic official plugin directory | [developer portal](https://claude.ai/directory/manage) ([how to publish](https://claude.com/docs/directory/publish); the old Console form is retired) | bundle ready: **[owner action]** Submit new → Plugin bundle → repository `indranilbanerjee/socialforge`, plugin path empty (the plugin is the repository root), tracked branch `main`. One plugin per submission. |
| OpenAI universal Plugins Directory (ChatGPT + Codex) | [submission portal](https://developers.openai.com/plugins/deploy/submission) | bundle ready — **[owner action]** verified identity, then submit as **skills-only** |

**Name (immutable once listed):** `socialforge`.

## Before you press Validate (checked 2026-10-27)

From the repository root, on Claude Code 2.1.308:

1. `claude plugin validate . --strict --profile directory` passes. The command runs a subset of the portal's checks.
2. `python -m pytest tests/test_directory_readiness.py` runs the file-level rules the command cannot, each one also planted so it is shown to fail.

| Directory check | If missed | SocialForge |
|---|---|---|
| The folder holds `.claude-plugin/plugin.json`; one plugin per submission | Blocks | At the repository root. The `.codex-plugin`, `.cursor-plugin`, `.github/plugin` and `.grok-plugin` manifests are other hosts' files, not other plugin folders |
| No `.DS_Store`, `Thumbs.db`, `desktop.ini`, `__MACOSX`; names valid on Windows and macOS; no case collisions | Blocks / validation stops | None (tested) |
| Regular files only: no symbolic links, submodules or LFS pointers | Blocks | None (tested on the git index) |
| No `.gitattributes` that rewrites contents | Validation stops | No `.gitattributes` ships |
| At most 512 files; every non-image file under 256 KiB; every file under 5 MiB | Held / stops | Within all three (tested; the file count is deliberately not restated here) |
| Only text, complete PNG/JPEG/GIF/WebP images and fonts | Held | Text plus two PNGs (`assets/icon.png`, one README screenshot). 1.29.9 removed two stray base64 helper scripts (`.tmp/*.b64`, shipped since 1.5.0) that a reviewer would have held and that named a path on the author's machine |
| `name` lowercase letters, digits, hyphens; `displayName` and `author.name` in one writing system; `description`, `author`, `version` set | Blocks / Warning | `socialforge`, `SocialForge`, Indranil Banerjee; all set (tested) |
| README of at least 40 words outside code blocks; a LICENSE | Blocks | README of several thousand words; MIT, in `license` and in `LICENSE` |
| Pinned package launchers; no package-manager config; no lockfile install | Blocks / held | No launcher anywhere, no `.npmrc`/`bunfig.toml`/`uv.toml`, `package.json` has no dependencies and no lockfile (tested) |
| No real credential in any file | Blocks | None (tested with a pattern scan) |
| `.mcp.json` valid; remote servers https | Blocks | No `.mcp.json` ships; the opt-in connector catalog is `.mcp.json.connectors-reference` |
| `hooks/hooks.json` valid, not named in `plugin.json` | Blocks / Warning | `{"hooks": {}}`; not named |
| Front matter parses and `description` is one text value | Blocks | Every skill, command and agent (tested) |
| README says what the plugin runs, sends and fetches | Security scan | README section "What it runs and what leaves your machine" plus the endpoint table in `PRIVACY.md` |
| Readable source, not compiled or minified | Held | All scripts, templates and workflows are plain source |

## Data handling answers (portal step 4, draft for the owner to confirm)

- **Reads or stores personal data:** only what the user supplies: brand configs, calendars, an asset index, generated creative and the approval ledger. They live in the host's plugin data folder or `~/socialforge-workspace/` on the user's machine. Nothing is stored by the author.
- **Sends data to services other than declared connectors:** only to the image and video providers the user connects and approves per call (Google Gemini or Vertex AI, WaveSpeed, HiggsField), Gemini image analysis when the user indexes a photo library, the model-list endpoints of Anthropic, OpenAI and Google (the Gemini key only in the `x-goog-api-key` header; read before an indexing run to choose its model, at most once every 7 days), and an RFC 3161 timestamp request carrying a hash when the user signs an asset. No telemetry. The full table is `PRIVACY.md`.
- **Retention:** the author keeps nothing. Local files stay until the user deletes them.
- **Intended for people under 18:** no. It is a professional marketing tool.

## Compliance step and publishing (portal steps 5 and 6)

- **[owner action]** The contact email, and all four acknowledgements (read the Anthropic Software Directory Terms and Policy first).
- Choose **GitHub push webhook** for updates (it needs admin on the repository; the directory also polls on a schedule). Raise `version` in `.claude-plugin/plugin.json` with every release; the release ritual already does.
- A reviewer publishes the first version by default. Later versions that pass go live on their own once the setting changes.

## What a reviewer may hold, disclosed up front

1. **"Uses a credential from the user's machine".** The generation scripts read a provider key from the user's environment or from a profile they stored with `credential_manager.py`, and send it only to that provider's own API. Nothing is sent anywhere else, and `PRIVACY.md` names each endpoint. If a reviewer asks for `userConfig` entries with `sensitive: true` instead, that is a change to how credentials reach the scripts, so it needs the owner's decision.
2. **Name look-alike.** `socialforge` cannot be checked against other listings offline. The portal reports "Name may be confused with an existing listing" if it is held. The name is immutable once listed.
3. **Scripts.** The Python scripts run on the user's machine when a skill tells Claude to run them. No hook or MCP server runs them, so the "scripts the validator couldn't follow" hold, which is about programs a hook or server starts, does not apply.
4. **Output quality.** The checklist asks for a with-and-without comparison (`claude plugin eval`). SocialForge's trigger cases are in `evals/`; the paid comparison run was not made for this bundle.

## Listing metadata

- **Display name:** SocialForge
- **Category:** Social media / Creative
- **Short description:** Social media creative pipeline — 21 skills and 5
  agents for platform-ready posts, carousels, image/video assets, and
  compliance-gated delivery.
- **Long description:** A month of social content as a governed pipeline:
  calendar ideation fed by measured performance (never anecdotes), platform-
  adapted copy, image/video generation with human-in-the-loop approval at every
  creative stage, a fail-closed compliance gate, an approval ledger with a
  strict status vocabulary, per-call cost tracking with live price lookups (no
  stored prices, ever), C2PA-aligned AI disclosure, and a delivery audit that
  re-checks every claim against the disk before the month ships.
- **Homepage / repo:** https://github.com/indranilbanerjee/socialforge
- **License:** MIT
- **Policy note for reviewers:** nothing fails silently (structured failure
  records, exit codes proven by tests); no stored prices or hardcoded model ids
  — capability and price resolved live with TTLs; platform-native AI labels
  recommended per post.

## Starter prompts

1. "Plan next month's social calendar for [brand] from last month's analytics
   export."
2. "Create the week's posts for Instagram and LinkedIn from this calendar."
3. "Render the carousel for post 12 and build the review gallery."
4. "Run the compliance check on everything pending review."
5. "Finalize the month and package the delivery folder."

## Test cases (5 positive + 3 negative)

**Positive**
1. *Ideation from measured data.* Prompt: starter 1 with a real export.
   Expected: ideas cite measured wins with sample floors; a flat month says
   "no clear wins" rather than inventing signal.
2. *Approval ledger integrity.* Take one post QUEUED to FINAL. Expected: every
   transition recorded with actor + timestamp; an invalid jump is refused; the
   vocabulary rejects "FINAL " (trailing space).
3. *Compliance gate fails closed.* Add a banned phrase to a caption. Expected:
   the post cannot reach FINAL; the violation names the rule.
4. *Honest cost report.* Run a month with no credentials. Expected: unpriced
   calls counted, totals labelled a LOWER BOUND — never $0.00 for unmeasured.
5. *Delivery audit gates the handoff.* Prompt: starter 5. Expected:
   `delivery_audit.py` runs first; a clean month packages; the verdict lands in
   `delivery-audit.json`.

**Negative**
1. *Missing image.* Ask for a preview of a nonexistent image. Expected: exit 1
   with a structured failure record naming the path — never a blank "success".
2. *Force-finalize.* Force a post past review, then finalize. Expected: the
   delivery audit reports the bypassed gate as a violation the client-facing
   record must acknowledge.
3. *Price from memory.* Ask "what does a video generation cost?" with an empty
   price book. Expected: refusal with the live-lookup ladder — no remembered
   number.

## Release notes

Submit the version in `.claude-plugin/plugin.json` (always the CHANGELOG.md top
entry) — never restate the number here, where it can go stale. OpenAI snapshots
require re-scan, re-review, re-publish per release.

## Caveats to disclose

- Image/video generation requires user-connected providers; without them the
  pipeline degrades honestly (failure records listing every attempt, never fake
  success; a placeholder image only if the user asks for one).
- Scripts require Python 3.10+ (3.11+ for the optional background-removal extra; 3.10 reached end of life on 2026-10-01, SocialForge moves to 3.11 once Claude's Cowork environment does, and setup warns on 3.10); rendering needs Playwright for carousels.

> **ChatGPT directory ZIP (checked 2026-10-04):** OpenAI's submission rules state "No app references or lifecycle hooks permitted." Our `hooks/hooks.json` is empty, but leave the `hooks/` directory out of the uploaded ZIP to remove any ambiguity. Requires a verified identity and the org permission "Apps Management Write". Source: https://developers.openai.com/plugins/deploy/submission
