---
name: price-check
description: "Look up what a generation actually costs right now, from the provider's live pricing page, and quote a run before spending anything. Use before any paid image or video generation."
argument-hint: "[--model <id>] [--provider <name>] [--compare] [--batch] [--staleness]"
effort: low
user-invocable: true
---

# /socialforge:price-check — What this run will cost, looked up today

Prices here are never remembered. They are looked up, recorded with the URL they
came from, and expire after 24 hours.

That is not caution for its own sake. On 2026-07-31 a major video model shipped
one day after this plugin's model registry was last reviewed, and the registry
never knew. In the same week, a provider already wired into SocialForge was
selling video at **$0.01/second** while the old cost table assumed **$0.40**. Any
price baked into a plugin is wrong on a timetable nobody controls.

## The rule

**Never state a cost you did not look up in this session or the last 24 hours.**

Not from this file. Not from the model registry. Not from what you remember a
model costing. If `price_book.py` says a price is `unknown` or `stale`, that is
the answer — go and read the provider's page, then record what you read.

## Looking a price up

1. Find where to look:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/price_book.py" --action providers
```

That returns each provider's pricing URL and its auth shape. Two things it will
tell you that save time:

- **Auth differs per provider.** `Authorization: Bearer …` for WaveSpeed and Kie,
  `Authorization: Key …` for fal.ai, application-default credentials for Vertex.
  Getting this wrong is the most common reason a first call fails.
- **Kie AI blocks automated fetches** (measured: HTTP 403). Do not report that as
  "no price found" — ask the user for the rate instead, and record it with the
  pricing page as the source.

2. Fetch the pricing page with your own web tools and read the actual number.

3. Record it, with the URL you read it from:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/price_book.py" --action record \
  --model "kling-3.0-std" --provider wavespeed \
  --unit second --price 0.084 --source https://wavespeed.ai/pricing
```

A record without a source URL is rejected. That is deliberate — a price with no
provenance is a guess wearing a number's clothes.

## Quoting before you spend

Single item:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/price_book.py" --action quote \
  --model "kling-3.0-std" --provider wavespeed --units 55
```

A whole planned run — **required before `/socialforge:generate-all`**, which fans
out across an entire monthly calendar and is the most expensive command in the
product:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/price_book.py" --action quote-batch --items '[
  {"model":"kling-3.0-std","provider":"wavespeed","units":5,"label":"post-01"},
  {"model":"seedance-2.0-fast","provider":"wavespeed","units":6,"label":"post-02"}
]'
```

Both exit non-zero when they cannot price the work, so a caller can never mistake
a refusal for a costed run.

**One unpriced item blocks the whole batch.** A total that quietly omits the three
clips nobody could price is worse than no total, because it reads as complete.

## Options that change the price

A base rate is not always the whole bill. On at least one wired video model,
asking for synchronised audio bills at **1.5× the base per-second rate** — and
SocialForge passes `sound` straight through to that API, so a quote taken without
it understates a 10-second clip by about half a dollar and a 28-post month by
roughly fifteen.

Look the surcharge up on the model's page, then pass it:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/price_book.py" --action quote \
  --model "kling-v3.0-pro" --provider wavespeed --units 10 \
  --multiplier 1.5 --multiplier-reason "sound=true"
```

In a batch, put it on the item: `{"model": …, "units": 10, "multiplier": 1.5,
"multiplier_reason": "sound=true"}`.

The quote then shows base, multiplier and reason separately, so the user can see
what the option cost them. Multipliers are provider facts and move — look them
up, do not carry them in your head.

## Then stop

A quote is not consent. `approved_to_run` is always `false`, even for a clean
batch. Show the user the number and wait for an explicit go.

**One approval covers one run.** If the user approves a batch and then changes
the calendar, re-quote and ask again.

## Comparing providers before you route

The same model genuinely costs different amounts in different places — Seedance
2.0 Fast has been seen at $0.10/s on one provider and $0.24/s on another. That is
a 2.4× difference for identical output.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/price_book.py" --action compare --model "seedance-2.0-fast"
```

Cheapest first, grouped by unit — a per-image price is never "cheaper" than a
per-second one, so they are never ranked against each other. If only one provider
is on record, the output says so: one price is not a comparison. Look up a second
before telling the user something is the cheapest option.

## Checking what has gone stale

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/price_book.py" --action staleness
```

Run this at the start of a production month. Anything listed as stale needs a
fresh lookup before it can appear in a quote.

## Draft cheap, finish properly

Iterating a rejected concept at hero-model rates is the quietest way to waste a
client's budget. Generate drafts on the cheapest capable model, and only re-run
the concept the user actually picked on the expensive one.

Route on a price you looked up, not on a tier name — tier labels in the registry
describe capability, not cost, and the two do not track each other reliably.

## What this skill will not do

- Quote from memory, from the registry, or from this file
- Present a partial total as the cost of a run
- Treat a quote as approval
- Call one provider cheapest on the strength of a single price
- Report a fetch failure as an absence of cost
