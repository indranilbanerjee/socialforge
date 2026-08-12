---
name: ingest-performance
description: "Feed last month's real numbers into next month's plan: ingest a platform analytics export (CSV from Instagram Insights, LinkedIn analytics, TikTok Studio, X analytics — any export with a post-id column) into per-post performance records, then rank the month's wins with sample floors and margin rules so ideation compounds measured winners, not remembered ones. Triggers on \"/ingest-performance\", \"here are last month's numbers\", \"import analytics\", \"which posts performed best\", \"engagement report\", \"what worked last month\", or whenever ideate-month needs its wins rung fed. Writes performance.json next to the month's tracker; /socialforge:ideate-month reads it and labels every win measured vs anecdotal."
argument-hint: "--brand <name> --month <YYYY-MM> [--csv <export.csv>] [--source <label>]"
user-invocable: true
---

# /socialforge:ingest-performance — real numbers into the wins rung

`/socialforge:ideate-month` compounds "what worked last month." Before this
skill, that meant whatever someone remembered in the planning call — and
memory favors the post that felt good, not the one that performed. This skill
turns the platform's own export into the record ideation reads.

## Step 1 — Get the export

Ask the user for the analytics export covering the month. Any CSV works if it
has a column identifying the post (`post_id`, `post`, `id`) that matches the
calendar's post ids, plus whichever metrics the platform provides
(impressions/views, likes/reactions, comments, shares/reposts, saves, clicks,
follows — header aliases are normalized automatically). If the export keys
posts by URL or caption instead of the calendar id, help the user add a
`post_id` column first — matching is by calendar id, deliberately: wins must
map back to the topics and pillars that produced them.

## Step 2 — Ingest

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/ingest_performance.py --action ingest \
    --brand {brand} --month {YYYY-MM} --csv {export.csv} --source "{platform} export"
```

- Rows matching calendar post ids are stored in
  `output/{brand}/{month}/performance.json` (repeat ingests append — one CSV
  per platform is normal).
- **Unmatched rows are listed in the output, never silently dropped.** Show
  the user the unmatched list; a typo'd id is data lost from the wins rung.
- Exit 3 = nothing matched. Stop and reconcile ids before proceeding.

## Step 3 — Rank the wins

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/ingest_performance.py --action wins \
    --brand {brand} --month {YYYY-MM}
```

The ranking is deliberately conservative:

- **Sample floor** (default 100 impressions): a post nobody saw cannot be a
  win, only noise. Below-floor posts are reported as `unranked` with the reason.
- **Margin rule** (default 1.5× the month's median engagement rate): a "win"
  must beat the month, not merely top a flat list.
- **Unmeasured is not zero**: missing impressions → `engagement_rate: null`,
  and the post lands in `unranked`, not at the bottom of the ranking.
- A flat month returns `"status": "no_clear_wins"` — report that honestly.
  Compounding a non-win manufactures a false signal for next month's plan.

## Step 4 — Hand off to ideation

Relay the wins output to `/socialforge:ideate-month` (its "last month's
results" input). Winners carry their topic, pillar, tier, and
`vs_month_median` multiple, so ideation can design follow-ups that compound
the validated angle — and label each one `measured` in "What last month
validated". Anything the client reports that is NOT in the ranked output is
still usable, labeled `anecdotal`.

## Pairs with

- `/socialforge:ideate-month` — consumes the wins output; measured beats remembered
- `/socialforge:finalize-month` — closing a month is the natural moment to ingest its numbers
