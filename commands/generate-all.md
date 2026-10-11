---
description: "Generate creative, copy and previews for every calendar post (generation step only). \"generate all the posts\""
argument-hint: "[--brand <name>] [--week <N>] [--tier HERO|HUB|HYGIENE] [--platform <name>]"
---

# Generate All

> **Script location.** If your host does not set `${CLAUDE_PLUGIN_ROOT}`, the scripts are in this plugin's `scripts/` folder, next to `skills/`. Run them with Python 3.10 or newer: `python`, or `python3` where `python` is not found (macOS, many Linux systems).

Produce images, carousels, copy, and previews for every post in the calendar.

This is the most expensive command in SocialForge. It fans out across a whole
month, and video is billed by the second.

## Quote, then go (before any paid call)

Generation spends provider credits, so the first paid call waits for a quote and an explicit go. This command states no price: `price_book.py` is the only source, and it refuses rather than guesses.

1. List what is about to be generated: one entry per paid generation, with the registry alias (`resolve_model.py --alias <alias>` gives the current model id), the provider, and the units (images for stills, seconds for video, plus any option that changes the price, such as synchronised audio). Build the list after any filter is applied: a total for 28 posts is not the price of the 6 you run.
2. Write that list as a JSON array to `run-plan.json` in the month's output folder (`${CLAUDE_PLUGIN_DATA}/socialforge/output/{brand}/{YYYY-MM}/`, or `~/socialforge-workspace/output/{brand}/{YYYY-MM}/` when `${CLAUDE_PLUGIN_DATA}` is unset), not in a shared temp folder: on Windows the shell and Python do not resolve the same `/tmp`. Then quote it, passing the absolute path:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/price_book.py" --action quote-batch --items "@<month folder>/run-plan.json"
```

   If the quote exits non-zero or lists a blocked item, stop: run `/socialforge:price-check` to look the missing price up, then quote again. A JSON `error` about the plan file (exit 2: missing, unreadable or not valid JSON) means the path or the contents are wrong: fix the file and quote again.
3. Show the user the total, each line, its **source URL**, and how old the price is (a price older than 24 hours is stale and is refused; it must be looked up again):

```
Estimated cost: <total_usd> USD for <n> generations. Prices from <source>, <age_hours> h old (valid for 24 h).
Type "go" to generate. Anything else cancels.
```

4. Continue only on an explicit `go` for exactly this list. Anything else, including silence, cancels and nothing is generated. One approval covers one run; if the calendar, a filter, a model or an option changes afterwards, quote again and ask again. A quote is never approval (`approved_to_run` is always `false`); only the user's `go` is.

## Process
1. Load calendar-data.json and asset-matches.json
2. For each post (ordered by date):
   - Determine creative mode (ANCHOR_COMPOSE, ENHANCE_EXTEND, STYLE_REFERENCED, PURE_CREATIVE)
   - Generate image(s) via image-compositor agent, handing it the approved quote from the Quote, then go section above (the agent refuses to run a paid call without one)
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

Filters change the item list, so they change the quote: apply them first, then quote and ask for `go`.

## Signing

Every generated asset is signed with a C2PA manifest carrying the
`c2pa.ai-disclosure` assertion (EU AI Act Article 50, enforceable since
2026-08-02). Once a post clears its approval queue, pass the approver through so
the manifest records who signed it off:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/c2pa_sign.py" ... \
  --reviewed-by "<approver name>" --model-id "<exact generating model id>"
```

Without `--reviewed-by` the manifest honestly records `human_oversight:
none-recorded`. Never pass a name that did not actually approve the asset.
