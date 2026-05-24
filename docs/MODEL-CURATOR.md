# Model Curator

`scripts/model_registry.json` is the single source of truth for every AI model id that the plugin's scripts hand to a provider SDK. The resolver `scripts/resolve_model.py` reads the registry and answers three questions for the rest of the plugin:

1. "What's the current best model for X?" → `resolve("latest-fast-anthropic")` returns the concrete id.
2. "Is this model id still good?" → `check("claude-sonnet-4-5-20250929")` returns `("deprecated", "claude-sonnet-4-6")`.
3. "What's available?" → `list_models(vendor="google", modality="image-gen")` returns the matching catalog.

This means a single edit to `model_registry.json` propagates to every script the next time it runs — no grep-and-replace across the plugin when a model is deprecated.

---

## Why it exists

Hardcoding model strings like `claude-sonnet-4-5-20250929`, `gemini-2.0-flash`, or `veo-2.0-generate-001` across dozens of scripts means that when a provider deprecates a model the script silently returns 404, the user blames the plugin, and the maintainer has to grep three repos to fix it. The curator removes that failure mode.

---

## How users override the model

Every script that calls a provider model accepts `--model` (or `--openai-model` / `--anthropic-model` for scripts that hit two providers). Pass any id from the registry — or any id, even one the registry doesn't know about. The resolver will:

- **Current id** → pass it through unchanged.
- **Deprecated id** → print a `WARNING` to stderr and silently substitute the registered `replacement_id`.
- **Unknown id** → print a `WARNING` and pass the id through (the call may still work; you just lose the deprecation safety net).
- **No `--model`** → resolve via the script's default alias (e.g. `latest-balanced-anthropic`).

```bash
# Default — uses the registry's latest-balanced-anthropic alias (claude-sonnet-4-6 today)
python scripts/ai-visibility-checker.py --brand acme --mode api

# Override to a specific id
python scripts/ai-visibility-checker.py --brand acme --mode api --anthropic-model claude-opus-4-7

# Pass a deprecated id — script warns and substitutes claude-sonnet-4-6
python scripts/ai-visibility-checker.py --brand acme --mode api --anthropic-model claude-sonnet-4-5-20250929
# WARNING (anthropic): claude-sonnet-4-5-20250929 is deprecated, using claude-sonnet-4-6 instead

# See what's curated
python scripts/ai-visibility-checker.py --list-models
python scripts/resolve_model.py --list --vendor anthropic --status current
```

---

## Aliases (the public API for "give me the latest X")

| Alias | What it resolves to today |
|---|---|
| `latest-text-anthropic` | Claude Opus 4.7 (frontier) |
| `latest-balanced-anthropic` | Claude Sonnet 4.6 |
| `latest-fast-anthropic` | Claude Haiku 4.5 |
| `latest-text-openai` | GPT-5 |
| `latest-balanced-openai` | GPT-5 mini |
| `latest-text-google` | Gemini 3 Pro |
| `latest-balanced-google` | Gemini 3.5 Flash |
| `latest-vision-google` | Gemini 3.5 Flash |
| `latest-image-google` | Nano Banana Pro (gemini-3-pro-image-preview) |
| `latest-image-balanced-google` | Nano Banana 2 (gemini-2.5-flash-image) |
| `latest-image-edit-google` | Nano Banana Pro (for higher-fidelity edits) |
| `latest-image-photoreal-google` | Imagen 4 |
| `latest-video-google` | Veo 3.1 |
| `latest-video-wavespeed` | Kling v3.0 Pro |
| `latest-image-character-higgsfield` | Higgsfield Soul v2 |

Run `python scripts/resolve_model.py --aliases` to list the live mappings.

---

## Keeping the registry fresh

Frontier model landscape shifts roughly every 6 weeks. Treat any entry older than 3 months as suspect.

```bash
# Check how stale the registry is
python scripts/resolve_model.py --registry-age
# -> last_updated: 2026-05-25 (0 days ago). next_review_due: 2026-08-25

# Poll the provider catalogs and report drift (no writes)
ANTHROPIC_API_KEY=... OPENAI_API_KEY=... GEMINI_API_KEY=... python scripts/refresh_models.py

# After a manual curation pass, bump the timestamp
python scripts/refresh_models.py --bump-timestamp
```

The drift report shows:
- **NEW** — model ids the provider lists that are not in your registry (triage and add).
- **STALE** — model ids in your registry marked `current` that the provider no longer lists.

The script never auto-rewrites entries; curation is a human decision.

---

## Adding a new model

Edit `scripts/model_registry.json`. Minimum fields:

```json
{
  "id": "claude-opus-4-8",
  "vendor": "anthropic",
  "family": "claude",
  "display_name": "Claude Opus 4.8",
  "tier": "frontier",
  "modality": ["text", "vision"],
  "status": "current",
  "released": "2026-07",
  "best_for": ["complex reasoning", "agentic workflows"]
}
```

Then either point the relevant alias at the new id, or leave the alias alone and let users opt in via `--model`.

## Deprecating a model

Change `status` to `"deprecated"` and add `replacement_id`. The resolver will auto-fall-forward for any script that resolves through an alias OR through `--model` validation.

```json
{
  "id": "claude-sonnet-4-6",
  "vendor": "anthropic",
  "status": "deprecated",
  "replacement_id": "claude-sonnet-4-7"
}
```
