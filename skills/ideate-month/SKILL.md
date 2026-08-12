---
name: ideate-month
description: "Plan next month's content calendar from a theme, raw signals, and last month's results — before any calendar exists. Triggers on \"/ideate-month\", \"/plan-month\", \"what should we post next month\", \"plan the calendar\", \"ideas for next month\", \"month theme\", \"content ideas for [brand]\", \"build a calendar from scratch\", or any time a brand needs a month planned and no client calendar has arrived. Outputs a calendar-data.json-compatible draft — series arcs, one-off posts, tiers, platforms — that feeds straight into /socialforge:parse-calendar and the production pipeline. Reads the brand profile for pillars and voice; mines pasted news/trends/notes into on-pillar angles; compounds last month's measured wins (fed by /socialforge:ingest-performance, with anecdotal reports labeled as such) instead of starting from zero."
argument-hint: "[--brand <name>] [--month <YYYY-MM>] [--theme <text>] [--signals <pasted material>]"
effort: high
user-invocable: true
---

# /socialforge:ideate-month — the month before the calendar exists

SocialForge's pipeline starts at `parse-calendar` — someone hands it a calendar.
This skill is for when nobody has: the client asks "what should this month be
about?", and that question is the actual work they are paying for.

The output is a **draft calendar in the exact shape `parse-calendar` ingests**,
so an approved plan flows into production with zero re-typing.

## Inputs — use whichever exist, say which were missing

1. **The brand profile** (required) — pillars, voice, platforms, compliance
   rules from `brand-config.json`. No profile → stop and run
   `/socialforge:brand-setup` first. Ideating without pillars produces generic
   content for nobody.
2. **A theme or business context** (optional) — a launch, a season, a campaign
   the client named.
3. **Raw signals** (optional) — pasted news, industry threads, competitor
   moves, sales-call notes, community questions. Mine them; never use them as
   filler. Every signal either maps to a pillar and a concrete angle, or it is
   dropped and listed as dropped, with the reason.
4. **Last month's results** (optional) — measured first, anecdote second:
   - **Measured**: run
     `python ${CLAUDE_PLUGIN_ROOT}/scripts/ingest_performance.py --action wins --brand {brand} --month {last-month}`.
     If a `performance.json` exists (built by `/socialforge:ingest-performance`
     from the platform's own analytics export), this returns winners ranked
     with a sample floor and a margin over the month's median engagement rate —
     plus an honest `no_clear_wins` when the month was flat. A win here is
     validated audience demand: plan its compounding follow-ups.
   - **Anecdotal**: the review gallery, status tracker, or anything the client
     reports as having worked. Usable, but labeled — see the output rules.
   - If the measured path has no data, say so and offer to ingest an export
     first; a two-minute CSV ingest upgrades the whole plan's foundation.

## Process

1. Read the brand profile. List pillars, platforms, posting cadence.
2. Check the measured path first (`ingest_performance.py --action wins`), then
   fold in anecdotal reports. Identify the 1–3 clear wins and design
   **follow-ups that compound them** — the deeper dive, the objection it
   raised, the adjacent question it opened. Not a repost of the same idea.
   Honesty rules: a `no_clear_wins` verdict is itself a finding — plan from
   pillars and signals and say the wins rung had nothing; never promote an
   `unranked` post (below the sample floor) to a win because it felt good.
3. Mine any signals into angles, each tagged with its pillar. Drop what does
   not map — and say so.
4. Design 1–2 **series** — connected multi-part sequences with an arc (setup →
   develop → payoff), each part standing alone but rewarding the follower. A
   month of disconnected posts is a feed; a series builds a habit.
5. Fill the remaining cadence with one-off posts across pillars.
6. Assign every post a tier honestly: HERO (heavy production, big swing), HUB
   (core pillar content), HYGIENE (light, frequent presence).
7. Balance platforms per the brand's platform config — not everything
   everywhere.

## Output structure

```
# Month plan — {brand}, {YYYY-MM}

## The month's spine
[2-3 sentences: the theme, the wins being compounded, what the month should
have achieved by its last post]

## Series ({n})
### Series A: [name] — [pillar]
Arc: [what part 1 sets up, how it develops, where it pays off]
Parts: [P03, P07, P11] — see calendar below

## What last month validated (if performance was provided)
- [win — measured: 4.1% ER, 2.3x month median] → [the compounding follow-up now on the calendar, with post id]
- [win — anecdotal: client-reported] → [follow-up, labeled so the client knows the basis differs]

## Signals used / dropped (if signals were provided)
- USED: [signal] → [P05: the angle]
- DROPPED: [signal] — [why it does not serve this brand's pillars]

## Draft calendar (calendar-data.json compatible)
​```json
{
  "month": "YYYY-MM",
  "brand": "{brand}",
  "status": "DRAFT — needs client approval",
  "posts": [
    {
      "post_id": "P01",
      "date": "YYYY-MM-DD",
      "platform": "linkedin",
      "content_type": "carousel",
      "tier": "HUB",
      "topic": "[specific enough that a stranger could brief a designer from it]",
      "pillar": "[brand pillar]",
      "series": "[series name or null]",
      "rationale": "[one line: why this post, why this day]"
    }
  ]
}
​```

## What I did not have
[Which optional inputs were missing and what they would have improved]
```

## Critical rules

- **Every post traces to a pillar, a win, or a signal.** A post that traces to
  none of them is filler; cut it and say the cadence target was not met rather
  than padding.
- **Topics must be briefable.** "5 mistakes agencies make with reporting
  (carousel, one mistake per slide)" is a topic. "Engagement post" is not.
- **At least one series per month.** Disconnected posts build reach at best; a
  series builds return visits.
- **Wins get follow-ups, not reposts.** The follow-up answers what the win
  opened, from the validated angle — never the same post again slightly
  reworded.
- **Tier honestly.** A month of all-HERO is a burnout plan; all-HYGIENE is
  invisible. Typical shape: 1–2 HERO, 40–50% HUB, the rest HYGIENE.
- **The draft is a draft.** Output carries `status: DRAFT` and this skill never
  writes calendar-data.json to the workspace itself — the client approves, then
  `/socialforge:parse-calendar` ingests it as the approved source of truth.
- **State what was missing.** A plan built without performance data or signals
  is a weaker plan; the client should know that, not discover it.

## Pairs with

- `/socialforge:ingest-performance` — feeds the wins rung from the platform's own numbers; run it on last month before planning this one
- `/socialforge:parse-calendar` — ingests the approved draft verbatim
- `/socialforge:reactive-post` — mid-month trend response; this skill plans, that one reacts
- `/socialforge:price-check` — quote the month's video load before the client approves it
