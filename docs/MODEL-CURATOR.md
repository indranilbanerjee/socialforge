# Model Curator

`scripts/model_registry.json` is the single source of truth for every AI model id that the plugin's scripts hand to a provider SDK. The resolver `scripts/resolve_model.py` reads the registry and answers three questions for the rest of the plugin:

1. "What's the current best model for X?" → `resolve("latest-fast-anthropic")` returns the concrete id.
2. "Is this model id still good?" → `check("claude-sonnet-4-5-20250929")` returns `("deprecated", <the replacement id>)`.
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
# Default — generate_image.py resolves the latest-image-balanced-google alias
python scripts/generate_image.py --prompt "product on marble" --output out.png

# Override to a specific id
python scripts/generate_image.py --prompt "product on marble" --output out.png --model <any id from --list-models>

# Pass a retired id — the resolver warns and substitutes the replacement
python scripts/generate_image.py --prompt "product on marble" --output out.png --model <a retired id>
# WARNING (google): <the retired id> is retired, using <its replacement> instead

# See what's curated
python scripts/generate_image.py --list-models
python scripts/resolve_model.py --alias latest-image-google
python scripts/resolve_model.py --check <a model id>
python scripts/resolve_model.py --registry-age
python scripts/resolve_model.py --list --vendor google --status current
```

---

## Aliases (the public API for "give me the latest X")

An alias names a capability kind, never a model id: `latest-<kind>-<vendor>`. The kinds in the registry today are `text`, `balanced`, `fast`, `vision`, `multimodal`, `image`, `image-balanced`, `image-edit`, `image-photoreal`, `image-character` and `video`, each under the vendors that offer one. Which id an alias resolves to changes every few weeks, so this page lists none (the table that used to be here went stale within a month).

`python scripts/resolve_model.py --aliases` prints the live mappings straight out of the registry and is the source of truth; nothing in the docs or skills should name the id.

---

## ⚠ Parameter compatibility — Claude Opus 4.7 and later

**Claude Opus 4.7 and Opus 4.8 reject `temperature`, `top_p`, and `top_k` with HTTP 400** when set to a non-default value. The Anthropic SDK still accepts these parameters in request types (for type-check compatibility), but the runtime returns a 400.

If your script calls Opus 4.7+ via the SDK, **omit** these parameters entirely — let the system default apply. Use prompting to guide model behavior instead.

Plugins call Opus 4.7+ via `resolve_model("latest-text-anthropic")`. Run `python scripts/resolve_model.py --check-params script.py` to scan a file for unsafe param use before shipping — it exits 1 if any call passes `temperature` / `top_p` / `top_k` alongside an Opus 4.7+ target.

Source: [Claude model deprecations — API parameter deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations).

---

## Keeping the registry fresh

Frontier model landscape shifts roughly every 6 weeks. Treat any entry older than 3 months as suspect.

```bash
# Check how stale the registry is
python scripts/resolve_model.py --registry-age
# -> last_updated: <YYYY-MM-DD> (<N> days ago). next_review_due: <YYYY-MM-DD>

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
  "replacement_id": "claude-sonnet-5"
}
```
