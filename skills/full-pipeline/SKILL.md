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
| 0 | parse-calendar | Calendar parsed, all required fields present |
| 1 | match-assets | Asset matches confirmed by user |
| 2 | compose-creative | All images generated, quality scores ≥7.0 |
| 3 | adapt-copy | Copy adapted, compliance passed |
| 4 | create-previews | Previews rendered for all posts |
| 5 | build-review-gallery | Gallery built and accessible |
| 6 | manage-reviews | All posts reviewed (async — pipeline pauses here) |
| 7 | finalize-month | All approved posts packaged for delivery |

## Progress

```
SocialForge Full Pipeline — AcmeCorp / April 2026

[1/7] Parse Calendar ✓ — 28 posts extracted
[2/7] Match Assets ✓ — 8 ANCHOR, 5 ENHANCE, 9 STYLE_REF, 4 PURE, 2 CAROUSEL
[3/7] Compose Creative → IN PROGRESS (12/28 posts, ~16 min remaining)
  Latest: P12 — STYLE_REFERENCED — Score: 8.4/10 ✓
[4/7] Adapt Copy — waiting
[5/7] Create Previews — waiting
[6/7] Review Gallery — waiting
[7/7] Finalize — waiting
```

## Rules
- Each phase must pass its gate before the next starts
- Phase 6 (Review) is async — pipeline pauses for human review
- User can interrupt at any phase and resume later
- Status persists in status-tracker.json

## Async Review Gate (Phase 6)

Phase 6 (manage-reviews) is the only async gate — the pipeline pauses here because human review takes hours or days.

**When pipeline reaches Phase 6:**
1. Gallery is built and shared (Phase 5 output)
2. Pipeline shows: "Review gallery ready. Pipeline paused — resume after reviews complete."
3. User reviews posts via `/sf:review` or `/sf:manage-reviews`
4. To resume: `/sf:full-pipeline --resume` or manually run Phase 7 (`/sf:finalize`)

**Escalation (per approval-chain.json):**
- Reminder after N days (configurable per tier)
- Escalate to next reviewer after M days
- Auto-finalize HYGIENE tier after N days if configured

**Timeout:** No automatic timeout — Phase 6 stays paused until human action. The `/sf:status` command shows pending review counts.
