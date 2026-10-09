---
description: "Produce one post end to end by ID: image, approval, copy, compliance, previews; visual only -> compose-creative. \"do post P04\""
argument-hint: "<post-id> [--variant b]"
---

# Generate Post

Produce the complete creative package for one post.

> **Script location.** If your host does not set `${CLAUDE_PLUGIN_ROOT}`, the scripts are in this plugin's `scripts/` folder, next to `skills/`.

## Quote, then go (before any paid call)

Generating the image or video is a paid call, so it is quoted first. This command states no price: `price_book.py` is the only source.

1. List what is about to be generated: for each paid call, the registry alias (`resolve_model.py --alias <alias>` gives the current model id), the provider, and the units (images, or seconds of video, plus any option that changes the price, such as synchronised audio). For an image post that is the planned variants (typically 2-3); for a video post, both keyframe rounds and the clip.
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

4. Continue only on an explicit `go` for exactly this list. Anything else, including silence, cancels and nothing is generated. If the list changes (a regeneration, another model, an added option), quote again and ask again. A quote is never approval (`approved_to_run` is always `false`); only the user's `go` is.

## Process
1. Load post from calendar-data.json by ID (e.g., P04)
2. Load matched asset from asset-matches.json
3. Generate the image using the assigned creative mode, only after the go above (hand the approved quote to the image-compositor agent: it refuses to generate without one)
4. Show generated image to user for approval
5. If approved: adapt copy, run compliance, generate previews
6. If rejected: regenerate with adjusted prompt or different asset
7. Update status-tracker.json

## Variants
`/socialforge:generate-post P04 --variant b` generates an alternative version for A/B testing.
