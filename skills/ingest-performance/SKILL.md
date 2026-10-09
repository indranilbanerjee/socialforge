---
name: ingest-performance
description: "Turn a platform analytics export into per-post performance records and ranked winners. \"which of last month's posts worked\""
argument-hint: "--brand <name> --month <YYYY-MM> [--csv <export.csv>] [--source <label>] [--replace]"
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
  `output/{brand}/{month}/performance.json`, each row tagged with its source
  label, and each source records the sha256 of its CSV. Different files append —
  one CSV per platform is normal.
- **The same file twice is a no-op.** Identical bytes answer
  `"status": "already_ingested"` (exit 0) and name the earlier source; nothing
  is added. That is not an error — report "no new export".
- **Cumulative exports use `--replace`.** If the platform's new file repeats
  the posts of last week's (month-to-date totals), ingest every snapshot under
  one constant `--source` label with `--replace`: rows previously ingested under
  that label are removed first, so only the latest snapshot counts. Other
  labels are untouched. Ingest only the **newest** export under `--replace`: it
  trusts the file it is given, so an older file ingested after a newer one
  replaces the newer numbers. `--replace` refuses a label ingested before rows
  carried their source label (use a new label or re-ingest the month), and a
  file that matches no calendar post leaves the old snapshot in place.
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
