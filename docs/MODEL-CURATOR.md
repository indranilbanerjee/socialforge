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

Asset indexing (`index_assets.py`) is the exception, because it takes its model from the router described under "The model router" below: a deprecated id is kept with a warning, a retired one stops the run, and nothing is substituted silently.

---

## Aliases (the public API for "give me the latest X")

An alias names a capability kind, never a model id: `latest-<kind>-<vendor>`. The kinds in the registry today are `text`, `balanced`, `fast`, `vision`, `multimodal`, `image`, `image-balanced`, `image-edit`, `image-photoreal`, `image-character` and `video`, each under the vendors that offer one. Which id an alias resolves to changes every few weeks, so this page lists none (the table that used to be here went stale within a month).

`python scripts/resolve_model.py --aliases` prints the live mappings straight out of the registry and is the source of truth; nothing in the docs or skills should name the id.

---

## ⚠ Parameter compatibility — every Anthropic model (API version 2026-10-21)

**From Anthropic API version 2026-10-21, `temperature`, `top_p` and `top_k` are removed for every model:** a request that sends any of them returns HTTP 400, even at the default value. On the older 2023-06-01 version, Claude 4.7 and later already reject a non-default value (see the registry's `param_compatibility_notes.anthropic_sampling_parameters`).

Omit all three on every Anthropic call; use prompting to guide behaviour. Plugins call Anthropic models through aliases such as `resolve_model("latest-text-anthropic")`. Scan a file before shipping it:

```bash
python scripts/resolve_model.py --check-params scripts/some_script.py
```

The scan is textual, not AST-based: it triggers when a file references any `claude-…` model id or a `latest-*-anthropic` alias, then flags every `temperature` / `top_p` / `top_k` assignment in that file. It exits 1 on any finding, so it drops straight into a pre-commit check. Expect occasional false positives when the model target is computed dynamically — that's deliberate, one extra review beats a 400 in production.

Source: [Claude model deprecations — API parameter deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations).

---

## The model router (asset indexing)

The registry is reviewed by hand, so for a job that may float with the market the plugin no longer depends on it for the decision. `scripts/model_router.py` chooses a model by job from the provider's own list of the models a key can use, and the registry stays as the offline fallback.

- **One job today:** `index-assets.vision.google` in `scripts/model_hints.json` (the vision model that describes brand photos). The job names a provider, a model family (a pattern over ids) and the generation method it calls, never an id. Creative generation (images, video) stays on `model_book.py` and the registry, because a new model changes how a brand's output looks.
- **What the router picks:** from the models the key lists with `generateContent`, the newest in the job's family that is active (not shut down, not redirected), generally available (no preview, experimental, "latest" alias or dated snapshot) and at least 14 days old. The Gemini list reports no lifecycle and no release dates, so those come from the `deprecations.google` record in the hint book: what an agent read from Google's deprecations page, with its source and the date. A listed model the record does not know is held back, with a warning, until the record is re-read.
- **Re-reading the record:** open the page named in the record's `source`, copy every model row (release date, the earliest shutdown date, whether the page marks it already shut down, its replacement or the model it now routes to), and update `read_on`. The router warns in its output after 30 days, and `tests/test_model_registry_dates.py` fails the record 45 days after `read_on`.
- **Asked for by name** (a brand pin in `brand-config.json`, or `--model`): kept if active, kept with a warning if deprecated, refused with exit 2 if the page marks it shut down. The replacement is named either way.
- **Offline:** when the list cannot be read, `MODEL_ROUTER_OFFLINE=1` is set, or Vertex AI serves the run, the model is the registry alias `latest-vision-google`, tagged `offline`, and a named model is checked against the registry's lifecycle fields.
- **One file, many plugins:** `scripts/model_router.py` is the suite's canonical file copied byte for byte. `tests/test_vision_model_routing.py` keeps this copy identical to it; change the canonical file and copy it again, never edit this one.
- **Privacy:** the list call, its header and its cache are described in [PRIVACY.md](../PRIVACY.md).

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
