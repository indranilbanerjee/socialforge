---
name: full-pipeline
description: Run the complete end-to-end production pipeline — parse, match, compose, copy, preview, review, finalize.
argument-hint: "[brand] [YYYY-MM] [calendar-source]"
effort: max
user-invocable: true
---

# /sf:full-pipeline — Complete Production Pipeline

Run all phases sequentially with quality gates between each.

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
2. **Image generation** requires Vertex AI (service account JSON) or GEMINI_API_KEY fallback
3. **Video generation** requires WaveSpeed API key (only checked if calendar contains video posts)
4. If any required credential is missing, stop the pipeline and prompt the user:
   "Required credentials not configured. Run `/sf:setup` to configure API keys before starting production."
5. If all credentials are valid, proceed to Phase 0

## Phase 2: Compose Creative

Phase 2 operates in two distinct modes depending on how it is invoked.

### Interactive mode (`/sf:generate-post`)

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

### Batch mode (`/sf:generate-all`)

Produces creative for all posts in the calendar with minimal interruption.

1. **Group-based direction** — Posts are grouped by creative mode (ANCHOR, ENHANCE, STYLE_REF, PURE). User approves creative direction per group rather than per post.
2. **Auto-generate** — All posts generate in sequence using the approved group directions. Progress is displayed per post with quality scores.
3. **Gallery review** — Once all posts are generated, a review gallery is built automatically so the user can review everything at once.
4. **Flagged regeneration** — User flags any posts that need rework. Flagged posts regenerate with adjusted prompts. Unflagged posts proceed as approved.

## Phase 5: Review Gallery

The review gallery (`/sf:review`) now supports both image and video content:
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
3. User reviews posts via `/sf:review` or `/sf:manage-reviews`
4. To resume after reviews: run `/sf:full-pipeline --resume` or `/sf:finalize` directly

**Escalation (per approval-chain.json):**
- Reminder after N days (configurable per tier)
- Escalate to next reviewer after M days
- Auto-finalize HYGIENE tier after N days if configured

**Timeout:** No automatic timeout — Phase 6 stays paused until human action. The `/sf:status` command shows pending review counts.
