# SocialForge — Directory Submission Bundle

Prepared 2026-08-16. Items marked **[owner action]** need the account holder.

## Targets

| Directory | Route | Status |
|---|---|---|
| Anthropic official plugin directory | [submission form](https://clau.de/plugin-directory-submission) | bundle ready — **[owner action]** submit |
| OpenAI universal Plugins Directory (ChatGPT + Codex) | [submission portal](https://developers.openai.com/plugins/deploy/submission) | bundle ready — **[owner action]** verified identity, then submit as **skills-only** |

**Name (immutable once listed):** `socialforge`.

## Listing metadata

- **Display name:** SocialForge
- **Category:** Social media / Creative
- **Short description:** Social media creative pipeline — 20 skills and 5
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
  pipeline degrades honestly (placeholders + failure records, never fake
  success).
- Scripts require Python 3.10+; rendering needs Playwright for carousels.
