---
description: Generate creative assets for all posts in the current month's calendar
argument-hint: "[--brand <name>] [--week <N>] [--tier HERO|HUB|HYGIENE] [--platform <name>]"
---

# Generate All

Produce images, carousels, copy, and previews for every post in the calendar.

This is the most expensive command in SocialForge. It fans out across a whole
month, and video is billed by the second. **Quote it before you run it.**

## Step 0 — Price the run and get a go (required)

Build the item list from the calendar (one entry per paid generation, `units` =
seconds for video, images for stills), then:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/price_book.py" --action quote-batch --items @/tmp/run-plan.json
```

- Exits non-zero if anything cannot be priced. **Do not proceed** — run
  `/socialforge:price-check` to look the missing models up, then re-quote.
- A clean quote still returns `approved_to_run: false`. Show the user the total
  and wait for an explicit go. One approval covers one run; if the calendar
  changes afterwards, re-quote and ask again.

## Process
1. Load calendar-data.json and asset-matches.json
2. For each post (ordered by date):
   - Determine creative mode (ANCHOR_COMPOSE, ENHANCE_EXTEND, STYLE_REFERENCED, PURE_CREATIVE)
   - Generate image(s) via image-compositor agent
   - Render carousel if content_type = carousel
   - Adapt copy for each target platform
   - Run compliance check
   - Generate platform previews
   - Run quality review
3. Show progress: `[12/28] Generating Post P12 — carousel (8 slides) for LinkedIn...`
4. At completion: show summary card with quality scores, issues, and next steps

## Filters
- `--week 2` — Only generate posts for week 2
- `--tier HERO` — Only generate HERO tier posts
- `--platform instagram` — Only generate for Instagram

Filters change the item list, so they change the quote. Re-price after applying
one — a total for 28 posts is not the price of the 6 you actually ran.

## Signing

Every generated asset is signed with a C2PA manifest carrying the
`c2pa.ai-disclosure` assertion (EU AI Act Article 50, enforceable since
2026-08-02). Once a post clears its approval queue, pass the approver through so
the manifest records who signed it off:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/c2pa_sign.py" ... \
  --reviewed-by "<approver name>" --model-id "<exact generating model id>"
```

Without `--reviewed-by` the manifest honestly records `human_oversight:
none-recorded`. Never pass a name that did not actually approve the asset.
