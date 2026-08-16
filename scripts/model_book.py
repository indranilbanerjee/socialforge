#!/usr/bin/env python3
"""
model_book.py — Which model to call, discovered at run time rather than shipped.

WHY THIS EXISTS
---------------
A model id written into code is a claim about the day it was written, shipped to
someone who runs it much later. This plugin had six of them on the execution
path. One — a video fallback — was pinned to a generation that had been
superseded for roughly six months, and nothing in the system knew or could say
so. Another sat inline with no resolution layer at all.

The failure is quiet in the worst way. A retired id does not degrade; it returns
"model not found" at the exact moment two other providers have already failed and
the fallback is all that is left.

So the code no longer asks for a model. It asks for a **kind of model** — "the
current best text-to-image on this provider" — and something that looked recently
answers.

THE CONTRACT
------------
Identical in spirit to price_book.py, for the same reasons:

1. A model enters only via `record()`, which REQUIRES a source URL. No seeds, no
   defaults, no "this was true when I wrote it".
2. `resolve()` returns a status, never a bare id. Missing or older than the
   freshness window means it says so and names where to look.
3. Discovery is the agent's job. This is a plugin: it has no crawler and no
   server. The agent reads the provider's model list with its own web tools and
   records what is current, which is why the answer is as fresh as the last look
   rather than as old as the last release.

WHY THE TTL IS LONGER THAN THE PRICE BOOK'S
-------------------------------------------
Prices move without announcement; catalogues move in releases. Seven days keeps a
month's production run on one consistent choice while still catching a new
generation within a week of it landing.

Stdlib only. No network calls in here by design.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Every other script in this plugin reads CLAUDE_PLUGIN_DATA; these two read
# CLAUDE_PLUGIN_DATA_DIR. With only the common name set, price and model lookups
# resolved to a DIFFERENT workspace than the one costs were written to — so a
# price recorded by the user was invisible to the tracker that needed it. Accept
# the canonical name first and keep the old one as a fallback.
_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("CLAUDE_PLUGIN_DATA_DIR") or os.environ.get("PLUGIN_DATA")
if _plugin_data:
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
    WORKSPACE = Path.home() / "socialforge-workspace"

MODEL_BOOK = WORKSPACE / "model-book.json"

DEFAULT_MAX_AGE_DAYS = 7

# The capabilities SocialForge actually calls for. Kinds, not products — a kind
# outlives every model that has ever satisfied it, which is the whole point.
KINDS = {
    "image.text-to-image": "Generate a still from a prompt",
    "image.reference-guided": "Generate a still guided by reference images (brand assets)",
    "image.edit": "Modify an existing still — background, lighting, composition",
    "image.character-consistency": "Preserve a face or character across stills",
    "video.text-to-video": "Generate a clip from a prompt alone",
    "video.image-to-video": "Animate from a start frame (optionally to an end frame)",
}

# Where to look. These are catalogue pages, not price pages, and they are the
# slow-moving part — which provider exists changes far less often than what it
# sells.
DISCOVERY = {
    "wavespeed": {
        "models_url": "https://wavespeed.ai/models",
        "collections_url": "https://wavespeed.ai/collections",
        "note": "Model ids look like `vendor/model-version/task`, e.g. `.../image-to-video`.",
    },
    "vertex": {
        "models_url": "https://cloud.google.com/vertex-ai/generative-ai/docs/models",
        "note": "Retired ids keep resolving in docs for a while — check the retirement table.",
    },
    "higgsfield": {
        "models_url": "https://higgsfield.ai/",
        "note": "Takes TWO credentials (key id + secret). Model is a URL path segment.",
    },
    "fal": {
        "models_url": "https://fal.ai/models",
        "note": "Not wired into SocialForge — here for price comparison only.",
    },
    "kie": {
        "models_url": "https://kie.ai/",
        "note": "Blocks automated fetches (HTTP 403 measured 2026-08-11). Ask the user.",
    },
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load() -> dict:
    if not MODEL_BOOK.exists():
        return {"schema_version": 1, "entries": {}}
    try:
        return json.loads(MODEL_BOOK.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        # A corrupt book must not silently read as "nothing recorded" — the
        # stored discoveries may be recoverable from the damaged file.
        print(f"WARNING: model-book.json is unreadable ({type(e).__name__}) — treating as "
              f"empty; the file at {MODEL_BOOK} may be recoverable", file=sys.stderr)
        return {"schema_version": 1, "entries": {}}


def _save(book: dict) -> None:
    MODEL_BOOK.parent.mkdir(parents=True, exist_ok=True)
    tmp = MODEL_BOOK.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(book, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, MODEL_BOOK)


def _key(kind: str, provider: str) -> str:
    return f"{kind.strip().lower()}@{provider.strip().lower()}"


def record(kind: str, provider: str, model_id: str, source: str,
           notes: str | None = None, max_duration_s: float | None = None) -> dict:
    """Store the model that is currently best for a kind on a provider."""
    kind = kind.strip().lower()
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {sorted(KINDS)}, got {kind!r}")
    if not model_id or not model_id.strip():
        raise ValueError("model_id is required")
    if not source or not source.startswith(("http://", "https://")):
        raise ValueError(
            "a source URL is required — a model id with no provenance is the "
            "same guess this module exists to replace")

    entry = {
        "kind": kind,
        "provider": provider.strip().lower(),
        "model_id": model_id.strip(),
        "source": source,
        "discovered_at": _now().isoformat(),
    }
    if notes:
        entry["notes"] = notes
    if max_duration_s is not None:
        entry["max_duration_s"] = float(max_duration_s)

    book = _load()
    book["entries"][_key(kind, provider)] = entry
    _save(book)
    return entry


def age_days(entry: dict) -> float | None:
    try:
        found = datetime.fromisoformat(entry["discovered_at"])
    except (KeyError, ValueError):
        return None
    if found.tzinfo is None:
        found = found.replace(tzinfo=timezone.utc)
    return (_now() - found).total_seconds() / 86400.0


def resolve(kind: str, provider: str,
            max_age_days: float = DEFAULT_MAX_AGE_DAYS) -> dict:
    """Return {status, ...}. status is one of: ok | stale | unknown."""
    kind = kind.strip().lower()
    provider = provider.strip().lower()
    entry = _load()["entries"].get(_key(kind, provider))

    if not entry:
        guide = DISCOVERY.get(provider, {})
        out = {
            "status": "unknown",
            "kind": kind,
            "provider": provider,
            "action_required": (
                f"No model on record for {kind} on {provider}. Read the provider's "
                f"model list, pick the current best for this kind, and record it. "
                f"Do not fall back to an id from memory — that is what went stale."),
        }
        if guide.get("models_url"):
            out["discovery_url"] = guide["models_url"]
        if guide.get("note"):
            out["discovery_note"] = guide["note"]
        return out

    days = age_days(entry)
    if days is None or days > max_age_days:
        guide = DISCOVERY.get(provider, {})
        return {
            "status": "stale",
            **entry,
            "age_days": round(days, 1) if days is not None else None,
            "discovery_url": guide.get("models_url"),
            "action_required": (
                f"{entry['model_id']} was current {round(days, 1) if days is not None else '?'} "
                f"days ago (limit {max_age_days}). Re-check the provider's catalogue "
                f"before using it — a superseded id fails at call time, not now."),
        }
    return {"status": "ok", **entry, "age_days": round(days, 1)}


def resolve_for_execution(kind: str, provider: str, registry_alias: str | None = None,
                          max_age_days: float = DEFAULT_MAX_AGE_DAYS) -> dict:
    """The ladder a generation script climbs to find a model id.

    1. **A live discovery** — recorded recently, with a source. Use it.
    2. **The shipped registry alias** — usable, but it is a file with a release
       date, so it is returned with an explicit warning carrying its age. This
       rung exists so a first run works before anything has been discovered, not
       so it can be relied on.
    3. **Nothing.** Refuse, and say what to look up.

    What is deliberately absent is the rung that used to be here: a string
    written into the source. That is rung 3 pretending to be rung 1 — it always
    answers, and one day the answer is a model that no longer exists.

    Returns {model_id, basis, ...} or {model_id: None, basis: "unresolved", ...}.
    """
    live = resolve(kind, provider, max_age_days)
    if live["status"] == "ok":
        return {"model_id": live["model_id"], "basis": "live-discovery",
                "kind": kind, "provider": provider,
                "source": live["source"], "age_days": live["age_days"]}

    out: dict = {"kind": kind, "provider": provider}
    if live["status"] == "stale":
        out["stale_discovery"] = {"model_id": live["model_id"],
                                  "age_days": live.get("age_days")}

    if registry_alias:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from resolve_model import registry_age_days, resolve as registry_resolve
            model_id = registry_resolve(registry_alias)
        except Exception:
            model_id = None
        else:
            if model_id:
                try:
                    reg_age = registry_age_days()
                except Exception:
                    reg_age = None
                out.update(
                    model_id=model_id, basis="shipped-registry",
                    registry_alias=registry_alias, registry_age_days=reg_age,
                    warning=(
                        f"Using {model_id} from the shipped registry"
                        + (f", last reviewed {reg_age} days ago" if reg_age is not None else "")
                        + ". Nothing has been discovered live for "
                        f"{kind} on {provider}. Check the provider's catalogue and "
                        f"record the current model before a production run."),
                    discovery_url=DISCOVERY.get(provider, {}).get("models_url"))
                return out

    out.update(
        model_id=None, basis="unresolved",
        action_required=(
            f"No model resolved for {kind} on {provider}. Read the provider's "
            f"model list, pick the current best for this kind, and record it with "
            f"model_book.py --action record. Refusing to fall back to a model id "
            f"from memory."),
        discovery_url=DISCOVERY.get(provider, {}).get("models_url"))
    return out


def staleness_report(max_age_days: float = DEFAULT_MAX_AGE_DAYS) -> dict:
    entries = _load()["entries"]
    fresh, stale = [], []
    for entry in entries.values():
        days = age_days(entry)
        row = {"kind": entry["kind"], "provider": entry["provider"],
               "model_id": entry["model_id"],
               "age_days": round(days, 1) if days is not None else None}
        (stale if (days is None or days > max_age_days) else fresh).append(row)

    covered = {(e["kind"], e["provider"]) for e in entries.values()}
    return {
        "total": len(entries),
        "fresh": len(fresh),
        "stale": len(stale),
        "stale_entries": stale,
        "kinds_with_no_model": sorted(k for k in KINDS
                                      if not any(c[0] == k for c in covered)),
        "max_age_days": max_age_days,
        "model_book": str(MODEL_BOOK),
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description="Which model to call, discovered live. Ships no model ids of "
                    "its own — every answer comes from a recorded lookup.")
    p.add_argument("--action", required=True,
                   choices=["record", "resolve", "staleness", "kinds", "discovery"])
    p.add_argument("--kind", help=f"one of: {', '.join(sorted(KINDS))}")
    p.add_argument("--provider")
    p.add_argument("--model-id")
    p.add_argument("--source", help="URL the model list was read from (required to record)")
    p.add_argument("--notes")
    p.add_argument("--max-duration-s", type=float)
    p.add_argument("--max-age-days", type=float, default=DEFAULT_MAX_AGE_DAYS)
    args = p.parse_args()

    def need(*names):
        missing = [n for n in names if getattr(args, n.replace("-", "_")) in (None, "")]
        if missing:
            print(json.dumps({"error": f"--{' --'.join(missing)} required for "
                                       f"--action {args.action}"}))
            sys.exit(2)

    try:
        if args.action == "record":
            need("kind", "provider", "model-id", "source")
            print(json.dumps({"recorded": record(
                args.kind, args.provider, args.model_id, args.source,
                args.notes, args.max_duration_s)}, indent=2))
        elif args.action == "resolve":
            need("kind", "provider")
            result = resolve(args.kind, args.provider, args.max_age_days)
            print(json.dumps(result, indent=2))
            if result["status"] != "ok":
                return 3  # non-zero: a caller must not run on an unresolved model
        elif args.action == "staleness":
            print(json.dumps(staleness_report(args.max_age_days), indent=2))
        elif args.action == "kinds":
            print(json.dumps(KINDS, indent=2))
        elif args.action == "discovery":
            print(json.dumps(DISCOVERY, indent=2))
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
