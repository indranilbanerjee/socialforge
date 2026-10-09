---
name: full-pipeline
description: "Run the full pipeline for the month, from calendar parse to delivery, pausing between phases. \"produce the whole month\""
argument-hint: "[brand] [YYYY-MM] [calendar-source]"
effort: max
user-invocable: true
---

# /socialforge:full-pipeline — Complete Production Pipeline

> **Script location.** If your host does not set `${CLAUDE_PLUGIN_ROOT}`, the scripts are in this plugin's `scripts/` folder, next to `skills/`.

Run all phases sequentially with quality gates between each.

## Context efficiency

Asset-heavy skill. **Grep before Read** the asset catalog (`${CLAUDE_PLUGIN_DATA}/socialforge/brands/<brand>/asset-index.json`) — never list the asset directory. Reference generated images / videos by path, not by loading metadata. Brand profile loads once per session.

## Pipeline Phases

| Phase | Skill | Gate |
|-------|-------|------|
| -1 | credential-check | API credentials configured (Vertex AI and/or WaveSpeed) |
| 0 | parse-calendar | Calendar parsed, all required fields present |
| 1 | match-assets | Asset matches confirmed by user |
| 2 | compose-creative | All images/videos generated, quality scores ≥7.0 |
| 3 | adapt-copy | Copy adapted, compliance passed |
| 4 | create-previews | Previews rendered for all posts |
| 5 | build-review-gallery | Gallery built and accessible (images + video) |
| 6 | manage-reviews | All posts reviewed (async — pipeline pauses here) |
| 7 | finalize-month | All approved posts packaged for delivery |

## Phase -1: Credential Check

Before any production work begins, verify that the required API credentials are configured via `credential_manager.py`.

1. Run `credential_manager.py status` to check Vertex AI and WaveSpeed configuration
2. **Image generation** requires Vertex AI credentials configured via `/socialforge:setup`
3. **Video generation** requires WaveSpeed API key (only checked if calendar contains video posts)
4. If any required credential is missing, stop the pipeline and prompt the user:
   "Required credentials not configured. Run `/socialforge:setup` to configure API keys before starting production."
5. If all credentials are valid, proceed to Phase 0

## Phase 2: Compose Creative

Phase 2 operates in two distinct modes depending on how it is invoked.

### Interactive mode (`/socialforge:generate-post`)

Produces creative for a single post with full user control at each stage.

**Image posts — 4-stage approval:**
1. **Direction** — Review creative direction and prompt before generation
2. **Generate** — AI generates 2-3 variants; user picks the best or requests regeneration
3. **Composite** — Selected variant composited with brand asset, overlay, and logo; user approves
4. **Resize** — Platform-specific resizes produced; user confirms final set

**Video posts — 5-stage approval:**
1. **Direction** — Review video concept, storyboard outline, and scene descriptions
2. **Script** — Approve shot-by-shot script with timing and transitions
3. **Generate** — AI generates video clip; user reviews motion and pacing
4. **Composite** — Overlay, logo, and captions applied; user approves
5. **Resize** — Platform-specific aspect ratios produced; user confirms final set

### Batch mode (`/socialforge:generate-all`)

Produces creative for all posts in the calendar with minimal interruption.

#### Quote, then go (batch, before any paid call)

A batch fans out across the whole calendar and video is billed by the second, so the batch is quoted once, after the group directions are approved and before anything is generated. This skill states no price: `price_book.py` is the only source, and one unpriced item blocks the whole batch.

1. List what is about to be generated: for each paid call, the registry alias (`resolve_model.py --alias <alias>` gives the current model id), the provider, and the units (images, or seconds of video, plus any option that changes the price, such as synchronised audio). In a batch, list every paid generation of every post. Interactive mode (`/socialforge:generate-post`) does the same per post, in `/socialforge:compose-creative`.
2. Quote it:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/price_book.py" --action quote-batch --items '[{"model":"<resolved model id>","provider":"<provider>","units":<n>,"label":"<post id and stage>"}]'
```

   A single item can use `--action quote --model <id> --provider <provider> --units <n>`. If the quote exits non-zero or lists a blocked item, stop: run `/socialforge:price-check` to look the missing price up, then quote again.
3. Show the user the total, each line, its **source URL**, and how old the price is (a price older than 24 hours is stale and is refused; it must be looked up again):

```
Estimated cost: <total_usd> USD for <n> generations. Prices from <source>, <age_hours> h old (valid for 24 h).
Type "go" to generate. Anything else cancels.
```

4. Continue only on an explicit `go` for exactly this list. Anything else, including silence, cancels and nothing is generated. If the list changes (more posts, another model, an added option), quote again and ask again. A quote is never approval (`approved_to_run` is always `false`).

1. **Group-based direction** — Posts are grouped by creative mode (ANCHOR, ENHANCE, STYLE_REF, PURE). User approves creative direction per group rather than per post.
2. **Quote, then go, then auto-generate** — run the quote step above for the whole batch; only on an explicit `go` do all posts generate in sequence using the approved group directions. Progress is displayed per post with quality scores.
3. **Gallery review** — Once all posts are generated, a review gallery is built automatically so the user can review everything at once.
4. **Flagged regeneration** — User flags any posts that need rework. Flagged posts regenerate with adjusted prompts. Unflagged posts proceed as approved.

## Phase 5: Review Gallery

The review gallery (`/socialforge:review`) now supports both image and video content:
- **Image posts** display as before — preview thumbnail, quality score, copy, and compliance status
- **Video posts** display with side-by-side `<video>` tags showing the raw generated clip alongside the composited version with overlays, enabling direct comparison of motion, pacing, and brand overlay placement

## Progress

```
SocialForge Full Pipeline — AcmeCorp / April 2026

[pre] Credential Check ✓ — Vertex AI ready, WaveSpeed ready
[1/7] Parse Calendar ✓ — 28 posts extracted (24 image, 4 video)
[2/7] Match Assets ✓ — 8 ANCHOR, 5 ENHANCE, 9 STYLE_REF, 4 PURE, 2 CAROUSEL
[3/7] Compose Creative → IN PROGRESS
  Mode: batch (group-based direction)
  Groups approved: ANCHOR ✓ ENHANCE ✓ STYLE_REF ✓ PURE → awaiting direction
  Generated: 18/28 posts (~10 min remaining)
  Latest: P18 — STYLE_REFERENCED — Score: 8.4/10 ✓
  Videos: 2/4 generated — P07 Score: 7.8/10 ✓
[4/7] Adapt Copy — waiting
[5/7] Create Previews — waiting
[6/7] Review Gallery — waiting
[7/7] Finalize — waiting
```

## Rules
- Each phase must pass its gate before the next starts
- Phase -1 (Credential Check) is the first gate — no production without valid credentials
- Phase 6 (Review) is async — pipeline pauses for human review
- User can interrupt at any phase and resume later
- Status persists in status-tracker.json

## Async Review Gate (Phase 6)

Phase 6 (manage-reviews) is the only async gate — the pipeline pauses here because human review takes hours or days.

**When pipeline reaches Phase 6:**
1. Gallery is built and shared (Phase 5 output)
2. Pipeline shows: "Review gallery ready. Pipeline paused — resume after reviews complete."
3. User reviews posts via `/socialforge:review` or `/socialforge:manage-reviews`
4. To resume after reviews: run `/socialforge:full-pipeline --resume` or `/socialforge:finalize` directly

**Escalation (per approval-chain.json):**
- Reminder after N days (configurable per tier)
- Escalate to next reviewer after M days
- Auto-finalize HYGIENE tier after N days if configured

**Timeout:** No automatic timeout — Phase 6 stays paused until human action. The `/socialforge:status` command shows pending review counts.
