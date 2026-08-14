#!/usr/bin/env python3
"""
price_book.py — What a generation will cost, from a live lookup, never from memory.

WHY THIS EXISTS
---------------
SocialForge used to price work from a hardcoded table: one flat rate per
*operation*, so a 3-second clip and a 15-second clip billed identically, and the
model registry carried no prices at all. Both went stale the moment a provider
shipped anything. On 2026-07-31 — one day after the registry's last review —
Seedance 2.5 launched, and the registry never knew. Meanwhile a provider already
wired into this plugin was selling video at $0.01/second while the cost table
assumed $0.40.

So this module holds no prices. Not one. It is a cache with provenance and a
quote engine, and every number in it was put there by a live lookup that
recorded where it came from.

THE CONTRACT
------------
1. A price enters only via `record()`, which REQUIRES a source URL. There is no
   default, no seed table, no "reasonable estimate" fallback.
2. `quote()` returns a status, never a bare number. If a price is missing or
   older than the freshness window it says so and names what to look up. It will
   not guess, and it will not quietly reuse a stale figure.
3. Price is a property of MODEL x PROVIDER, never of a model alone. The same
   model genuinely costs different amounts on different providers — Seedance 2.0
   Fast has been seen at $0.10/s on one and $0.24/s on another. A single global
   price for a model is always wrong somewhere.
4. Names are normalised on the way in, because one model has three spellings:
   `gemini-3.1-flash-image` (Google), `fal-ai/nano-banana` (fal.ai) and
   "Nano Banana 2" (WaveSpeed) are the same thing to a buyer.

HOW A PRICE GETS IN
-------------------
The agent looks it up — this is a plugin, there is no crawler and no server. It
fetches the provider's pricing page with its own web tools, then records what it
read:

    price_book.py --action record --model "kling-3.0-std" --provider wavespeed \\
        --unit second --price 0.084 --source https://wavespeed.ai/pricing

and asks for a quote before spending anything:

    price_book.py --action quote --model "kling-3.0-std" --provider wavespeed \\
        --units 55

Stdlib only. No network calls happen in here by design: the fetching layer is
the agent's, so the numbers are always as fresh as the lookup that found them
and never as stale as a table someone forgot to update.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Every other script in this plugin reads CLAUDE_PLUGIN_DATA; these two read
# CLAUDE_PLUGIN_DATA_DIR. With only the common name set, price and model lookups
# resolved to a DIFFERENT workspace than the one costs were written to — so a
# price recorded by the user was invisible to the tracker that needed it. Accept
# the canonical name first and keep the old one as a fallback.
_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("CLAUDE_PLUGIN_DATA_DIR")
if _plugin_data:
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
    WORKSPACE = Path.home() / "socialforge-workspace"

PRICE_BOOK = WORKSPACE / "price-book.json"

# How long a looked-up price stays usable before it must be re-checked.
# Provider pricing moves on no schedule at all, so this is deliberately short.
DEFAULT_MAX_AGE_HOURS = 24

VALID_UNITS = ("image", "second", "video", "megapixel", "1k-images")

# Providers we know how to talk about, with the page a lookup should read.
# This is NOT a price source — it is a map of where to go and how each one
# authenticates, which is the part that genuinely changes slowly.
PROVIDERS = {
    "wavespeed": {
        "pricing_url": "https://wavespeed.ai/pricing",
        "auth": "header:Authorization: Bearer {WAVESPEED_API_KEY}",
        "fetchable": True,
    },
    "fal": {
        "pricing_url": "https://fal.ai/pricing",
        "auth": "header:Authorization: Key {FAL_KEY}",
        "fetchable": True,
    },
    "vertex": {
        "pricing_url": "https://cloud.google.com/vertex-ai/generative-ai/pricing",
        "auth": "adc:google-application-credentials",
        "fetchable": True,
    },
    "kie": {
        "pricing_url": "https://kie.ai/pricing",
        "auth": "header:Authorization: Bearer {KIE_API_KEY}",
        # Measured 2026-08-11: returns HTTP 403 to automated fetches. A lookup
        # must fall back to asking the user rather than reporting a failure as
        # "no price exists".
        "fetchable": False,
        "fetch_note": "blocks automated fetches (403) — ask the user for the rate",
    },
    "higgsfield": {
        "pricing_url": "https://higgsfield.ai/pricing",
        "auth": "header:Authorization: Bearer {HIGGSFIELD_API_KEY}",
        "fetchable": True,
    },
}

# Same model, different spellings per provider. Normalising here is what lets a
# cross-provider comparison work at all.
_ALIASES = {
    "nano-banana": "nano-banana",
    "nanobanana": "nano-banana",
    "nano-banana-2": "nano-banana-2",
    "gemini-3.1-flash-image": "nano-banana-2",
    "gemini-3.1-flash-image-preview": "nano-banana-2",
    "fal-ai/nano-banana": "nano-banana",
    "gemini-3-pro-image": "nano-banana-pro",
    "nano-banana-pro": "nano-banana-pro",
}


def normalise(model: str) -> str:
    """Fold a provider's spelling of a model into one comparable key.

    Mirrors what TokenTracker's normalizeModelKey does for LLM spellings: strip
    the vendor path, lowercase, collapse separators, then apply known aliases.
    """
    key = (model or "").strip().lower()
    key = re.sub(r"^(fal-ai|kwaivgi|bytedance|openai|google)/", "", key)
    key = key.split("/")[0] if "/" in key and key.count("/") == 1 else key
    key = re.sub(r"[\s_]+", "-", key)
    key = re.sub(r"-+", "-", key).strip("-")
    return _ALIASES.get(key, key)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load() -> dict:
    if not PRICE_BOOK.exists():
        return {"schema_version": 1, "entries": {}}
    try:
        return json.loads(PRICE_BOOK.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        # A corrupt book must not silently read as "no prices on record" —
        # that advice ("record it") would overwrite the damaged file.
        print(f"WARNING: price-book.json is unreadable ({type(e).__name__}) — treating as "
              f"empty; the file at {PRICE_BOOK} may be recoverable", file=sys.stderr)
        return {"schema_version": 1, "entries": {}}


def _save(book: dict) -> None:
    PRICE_BOOK.parent.mkdir(parents=True, exist_ok=True)
    tmp = PRICE_BOOK.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(book, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, PRICE_BOOK)


def _key(model: str, provider: str) -> str:
    return f"{normalise(model)}@{provider.strip().lower()}"


def record(model: str, provider: str, unit: str, price: float, source: str,
           note: str | None = None) -> dict:
    """Store a price that was just looked up. `source` is required, on purpose."""
    if unit not in VALID_UNITS:
        raise ValueError(f"unit must be one of {VALID_UNITS}, got {unit!r}")
    if price < 0:
        raise ValueError("price cannot be negative")
    if not source or not source.startswith(("http://", "https://")):
        raise ValueError(
            "a source URL is required — a price with no provenance is a guess, "
            "and guesses are what this module exists to prevent")

    book = _load()
    entry = {
        "model": normalise(model),
        "model_as_given": model,
        "provider": provider.strip().lower(),
        "unit": unit,
        "price_usd": float(price),
        "source": source,
        "fetched_at": _now().isoformat(),
    }
    if note:
        entry["note"] = note
    book["entries"][_key(model, provider)] = entry
    _save(book)
    return entry


def age_hours(entry: dict) -> float | None:
    try:
        fetched = datetime.fromisoformat(entry["fetched_at"])
    except (KeyError, ValueError):
        return None
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=timezone.utc)
    return (_now() - fetched).total_seconds() / 3600.0


def lookup(model: str, provider: str, max_age_hours: float = DEFAULT_MAX_AGE_HOURS) -> dict:
    """Return {status, ...}. status is one of: ok | stale | unknown."""
    entry = _load()["entries"].get(_key(model, provider))
    if not entry:
        prov = PROVIDERS.get(provider.strip().lower(), {})
        out = {
            "status": "unknown",
            "model": normalise(model),
            "provider": provider.strip().lower(),
            "action_required": (
                f"No price on record for {normalise(model)} on {provider}. "
                f"Look it up, then record it with --action record."),
        }
        if prov.get("pricing_url"):
            out["lookup_url"] = prov["pricing_url"]
        if prov.get("fetchable") is False:
            out["lookup_note"] = prov.get("fetch_note", "not fetchable automatically")
        return out

    hrs = age_hours(entry)
    if hrs is None or hrs > max_age_hours:
        return {
            "status": "stale",
            **entry,
            "age_hours": round(hrs, 1) if hrs is not None else None,
            "action_required": (
                f"Price for {entry['model']} on {entry['provider']} is "
                f"{round(hrs, 1) if hrs is not None else 'unknown'}h old "
                f"(limit {max_age_hours}h). Re-check {entry['source']} before quoting."),
        }
    return {"status": "ok", **entry, "age_hours": round(hrs, 1)}


def quote(model: str, provider: str, units: float,
          max_age_hours: float = DEFAULT_MAX_AGE_HOURS,
          multiplier: float = 1.0, multiplier_reason: str | None = None) -> dict:
    """Cost for `units` of work. Never returns a number it had to invent.

    `multiplier` covers per-option surcharges that a base rate does not include.
    These are real and easy to miss: on at least one wired video model, asking
    for synchronised audio bills at 1.5x the base per-second rate. SocialForge
    passes `sound=True` straight through to that API, so a quote without the
    multiplier understates the bill by half.

    The multiplier is supplied by the caller, not stored here, for the same
    reason prices are not stored here — it is a provider fact that moves, and a
    number baked into this file would eventually be a confident lie. Pass
    `multiplier_reason` so the quote can say why it is not the base rate.
    """
    found = lookup(model, provider, max_age_hours)
    if found["status"] != "ok":
        return {**found, "quotable": False, "units": units}
    if multiplier <= 0:
        raise ValueError("multiplier must be positive")

    base = found["price_usd"] * float(units)
    total = round(base * float(multiplier), 4)
    out = {
        "quotable": True,
        "status": "ok",
        "model": found["model"],
        "provider": found["provider"],
        "unit": found["unit"],
        "unit_price_usd": found["price_usd"],
        "units": units,
        "total_usd": total,
        "source": found["source"],
        "priced_at": found["fetched_at"],
        "age_hours": found["age_hours"],
    }
    if multiplier != 1.0:
        out["base_usd"] = round(base, 4)
        out["multiplier"] = float(multiplier)
        out["multiplier_reason"] = multiplier_reason or "unspecified option surcharge"
    return out


def compare(model: str, max_age_hours: float = DEFAULT_MAX_AGE_HOURS) -> dict:
    """Every provider we hold a price for, cheapest first.

    This is the payoff for keying on model x provider: it makes "the same model
    is 2.4x cheaper over there" visible instead of invisible.
    """
    target = normalise(model)
    rows = []
    for entry in _load()["entries"].values():
        if entry.get("model") != target:
            continue
        hrs = age_hours(entry)
        rows.append({
            "provider": entry["provider"],
            "unit": entry["unit"],
            "price_usd": entry["price_usd"],
            "source": entry["source"],
            "age_hours": round(hrs, 1) if hrs is not None else None,
            "fresh": hrs is not None and hrs <= max_age_hours,
        })
    # Only compare like with like — a per-image price is not cheaper than a
    # per-second one, it is a different question.
    by_unit: dict[str, list] = {}
    for row in rows:
        by_unit.setdefault(row["unit"], []).append(row)
    for unit_rows in by_unit.values():
        unit_rows.sort(key=lambda r: r["price_usd"])

    out = {"model": target, "by_unit": by_unit, "provider_count": len(rows)}
    if not rows:
        out["action_required"] = (
            f"No prices on record for {target} on any provider. Look up at least "
            f"two before claiming one is cheapest.")
    elif len(rows) == 1:
        out["note"] = (
            "Only one provider priced — this is not a comparison. Look up the "
            "others before routing on cost.")
    return out


def quote_batch(items: list[dict], max_age_hours: float = DEFAULT_MAX_AGE_HOURS) -> dict:
    """Price a whole planned run before any of it executes.

    This is the gate for `/generate-all`, which fans out across an entire monthly
    calendar and is far and away the most expensive keystroke in the product. It
    used to fire with no number shown at all.

    One unpriced item blocks the whole batch. That is deliberate: a total that
    silently omits the three clips nobody could price is worse than no total,
    because it reads as complete.

    Each item: {"model": str, "provider": str, "units": float, "label": str?,
                "multiplier": float?, "multiplier_reason": str?}
    """
    priced, blocked = [], []
    total = 0.0
    for i, item in enumerate(items):
        label = item.get("label") or f"item-{i + 1}"
        result = quote(item["model"], item["provider"], item["units"], max_age_hours,
                       multiplier=item.get("multiplier", 1.0),
                       multiplier_reason=item.get("multiplier_reason"))
        if result.get("quotable"):
            total += result["total_usd"]
            priced.append({"label": label, **result})
        else:
            blocked.append({
                "label": label,
                "model": result.get("model"),
                "provider": result.get("provider"),
                "status": result.get("status"),
                "action_required": result.get("action_required"),
                "lookup_url": result.get("lookup_url"),
            })

    out = {
        "items": len(items),
        "priced": len(priced),
        "blocked": len(blocked),
        "subtotal_usd": round(total, 4),
        "breakdown": priced,
    }
    if blocked:
        out["approved_to_run"] = False
        out["blocked_items"] = blocked
        out["total_usd"] = None
        out["action_required"] = (
            f"{len(blocked)} of {len(items)} items have no usable price. Look them "
            f"up and record them, then re-quote. Refusing to show a partial total "
            f"as if it were the cost of the run.")
    else:
        out["approved_to_run"] = False  # a price is not an approval
        out["total_usd"] = round(total, 4)
        out["action_required"] = (
            f"Quoted ${round(total, 4)} for {len(items)} generations. This is a "
            f"quote, not consent — get the user's explicit go before running. "
            f"One approval covers one run.")
    return out


def staleness_report(max_age_hours: float = DEFAULT_MAX_AGE_HOURS) -> dict:
    entries = _load()["entries"]
    fresh, stale = [], []
    for entry in entries.values():
        hrs = age_hours(entry)
        row = {"model": entry["model"], "provider": entry["provider"],
               "age_hours": round(hrs, 1) if hrs is not None else None}
        (stale if (hrs is None or hrs > max_age_hours) else fresh).append(row)
    return {
        "total": len(entries),
        "fresh": len(fresh),
        "stale": len(stale),
        "stale_entries": stale,
        "max_age_hours": max_age_hours,
        "price_book": str(PRICE_BOOK),
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description="Live price book for SocialForge generations. Holds no prices "
                    "of its own — every figure comes from a recorded lookup.")
    p.add_argument("--action", required=True,
                   choices=["record", "lookup", "quote", "quote-batch", "compare",
                            "staleness", "providers"])
    p.add_argument("--items", help='JSON list for --action quote-batch, e.g. '
                                   '\'[{"model":"kling-3.0-std","provider":"wavespeed",'
                                   '"units":5,"label":"post-01"}]\'. Use @path to read a file.')
    p.add_argument("--model")
    p.add_argument("--provider")
    p.add_argument("--unit", choices=VALID_UNITS)
    p.add_argument("--price", type=float)
    p.add_argument("--source", help="URL the price was read from (required to record)")
    p.add_argument("--note")
    p.add_argument("--units", type=float, help="How many units to quote for")
    p.add_argument("--multiplier", type=float, default=1.0,
                   help="Option surcharge on the base rate, e.g. 1.5 when synchronised "
                        "audio is enabled. Look it up on the model's page — this is a "
                        "provider fact, not something this tool knows.")
    p.add_argument("--multiplier-reason", help='Why, e.g. "sound=true"')
    p.add_argument("--max-age-hours", type=float, default=DEFAULT_MAX_AGE_HOURS)
    args = p.parse_args()

    def need(*names):
        missing = [n for n in names if getattr(args, n) in (None, "")]
        if missing:
            print(json.dumps({"error": f"--{' --'.join(missing)} required for "
                                       f"--action {args.action}"}))
            sys.exit(2)

    try:
        if args.action == "record":
            need("model", "provider", "unit", "price", "source")
            print(json.dumps({"recorded": record(
                args.model, args.provider, args.unit, args.price, args.source, args.note)},
                indent=2))
        elif args.action == "lookup":
            need("model", "provider")
            print(json.dumps(lookup(args.model, args.provider, args.max_age_hours), indent=2))
        elif args.action == "quote":
            need("model", "provider", "units")
            result = quote(args.model, args.provider, args.units, args.max_age_hours,
                           multiplier=args.multiplier,
                           multiplier_reason=args.multiplier_reason)
            print(json.dumps(result, indent=2))
            if not result.get("quotable"):
                return 3  # non-zero so a caller cannot mistake it for a priced run
        elif args.action == "quote-batch":
            need("items")
            raw = args.items
            if raw.startswith("@"):
                raw = Path(raw[1:]).read_text(encoding="utf-8")
            try:
                items = json.loads(raw)
            except json.JSONDecodeError as exc:
                print(json.dumps({"error": f"--items is not valid JSON: {exc}"}))
                return 2
            if not isinstance(items, list) or not items:
                print(json.dumps({"error": "--items must be a non-empty JSON list"}))
                return 2
            result = quote_batch(items, args.max_age_hours)
            print(json.dumps(result, indent=2))
            if result["blocked"]:
                return 3
        elif args.action == "compare":
            need("model")
            print(json.dumps(compare(args.model, args.max_age_hours), indent=2))
        elif args.action == "staleness":
            print(json.dumps(staleness_report(args.max_age_hours), indent=2))
        elif args.action == "providers":
            print(json.dumps(PROVIDERS, indent=2))
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
