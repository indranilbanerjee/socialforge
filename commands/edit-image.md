---
description: "Edit a generated image: background, lighting, colors or composition. \"change the background on this image\""
argument-hint: "<post-id> <instruction>"
---

# Edit Image

> **Script location.** If your host does not set `${CLAUDE_PLUGIN_ROOT}`, the scripts are in this plugin's `scripts/` folder, next to `skills/`. Run them with Python 3.10 or newer: `python`, or `python3` where `python` is not found (macOS, many Linux systems).

Send an AI edit instruction to modify a generated image while preserving the core subject.

## Quote, then go (before any paid call)

An AI edit is a paid call, so it is quoted first. This command states no price: `price_book.py` is the only source, and it refuses rather than guesses.

1. Say what is about to be edited: one edit, the model (the registry alias `latest-image-edit-google` unless `--model` names another; `resolve_model.py --alias latest-image-edit-google` gives the current model id), the provider, and one unit (one image).
2. Quote it:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/price_book.py" --action quote --model <resolved model id> --provider <provider> --units 1
```

   If the quote exits non-zero or lists a blocked item, stop: run `/socialforge:price-check` to look the missing price up, then quote again.
3. Show the user the total, its **source URL**, and how old the price is (a price older than 24 hours is stale and is refused; it must be looked up again):

```
Estimated cost: <total_usd> USD for 1 edit. Price from <source>, <age_hours> h old (valid for 24 h).
Type "go" to generate. Anything else cancels.
```

4. Continue only on an explicit `go` for exactly this edit. Anything else, including silence, cancels and nothing is edited. Every new instruction, and every retry after a rejection, is a new paid call: quote again and ask again. A quote is never approval (`approved_to_run` is always `false`); only the user's `go` is.

The approval in step 5 below is a different decision: it says whether the edited image replaces the variant. It does not pay for the edit.

## Process
1. Load the current image for the post
2. Show image to user with current state
3. Accept edit instruction (e.g., "make the background warmer", "extend the left side")
4. Only after the go above, call the editor with the instruction plus any style references:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/edit_image.py" --image <current> --instruction "<text>" --output <new> [--references <img> ...] [--model <id>]
   ```
   `--image`, `--instruction`, and `--output` are required.
5. Show edited result for approval
6. If approved: replace the variant, re-run quality review
7. If rejected: try different instruction or revert
