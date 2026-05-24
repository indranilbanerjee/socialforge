#!/usr/bin/env python3
"""
resolve_model.py — Model curator: resolve aliases, check deprecation, list models.

Single source of truth for what model IDs to pass to provider SDKs across the
Neelverse Marketing Suite. Scripts MUST NOT hardcode model strings; they should
call resolve() (or the CLI) so a single registry edit propagates everywhere
and deprecated IDs surface as warnings instead of silent 404s.

Usage (CLI):
    python resolve_model.py --alias latest-fast-anthropic
    python resolve_model.py --check gemini-2.0-flash
    python resolve_model.py --list
    python resolve_model.py --list --vendor anthropic
    python resolve_model.py --list --modality image-gen --status current
    python resolve_model.py --json --list
    python resolve_model.py --registry-age      # days since last_updated

Usage (Python):
    from resolve_model import resolve, check, list_models, get_registry
    model_id = resolve("latest-fast-anthropic")
    status, replacement = check("gemini-2.0-flash")
    for m in list_models(vendor="google", modality="image-gen"):
        print(m["id"], m["status"])

Exit codes (CLI):
    0  resolved / current / list returned
    1  alias unknown OR model deprecated (with --check)
    2  registry file missing / malformed
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

REGISTRY_FILENAME = "model_registry.json"


def _find_registry() -> Path:
    """Locate model_registry.json. Search order:
    1. $MODEL_REGISTRY env var (explicit override)
    2. Same directory as this script
    3. Parent ../scripts/
    4. Plugin scripts/ via CLAUDE_PLUGIN_ROOT/scripts/
    """
    override = os.environ.get("MODEL_REGISTRY")
    if override:
        p = Path(override)
        if p.exists():
            return p
    here = Path(__file__).resolve().parent
    candidates = [
        here / REGISTRY_FILENAME,
        here.parent / "scripts" / REGISTRY_FILENAME,
    ]
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        candidates.append(Path(plugin_root) / "scripts" / REGISTRY_FILENAME)
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        f"{REGISTRY_FILENAME} not found. Searched: "
        + ", ".join(str(c) for c in candidates)
    )


_REGISTRY_CACHE: dict[str, Any] | None = None


def get_registry(force_reload: bool = False) -> dict[str, Any]:
    """Load and cache the model registry."""
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is not None and not force_reload:
        return _REGISTRY_CACHE
    path = _find_registry()
    try:
        _REGISTRY_CACHE = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed {REGISTRY_FILENAME} at {path}: {exc}") from exc
    return _REGISTRY_CACHE


def _model_index() -> dict[str, dict[str, Any]]:
    reg = get_registry()
    return {m["id"]: m for m in reg.get("models", [])}


def resolve(alias_or_id: str, *, allow_deprecated: bool = False) -> str:
    """Resolve an alias (e.g. "latest-fast-anthropic") OR an exact model ID
    to a concrete model ID. If the input is itself a current model ID, returns
    it unchanged. If it's a deprecated model ID, returns the replacement (and
    raises if allow_deprecated=False AND no replacement exists)."""
    reg = get_registry()
    aliases = reg.get("aliases", {})
    if alias_or_id in aliases:
        return aliases[alias_or_id]
    idx = _model_index()
    if alias_or_id in idx:
        m = idx[alias_or_id]
        status = m.get("status", "current")
        if status == "deprecated":
            replacement = m.get("replacement_id")
            if replacement and not allow_deprecated:
                return replacement
            if not replacement:
                raise ValueError(
                    f"Model {alias_or_id} is deprecated with no replacement_id in registry."
                )
        return alias_or_id
    raise KeyError(
        f"{alias_or_id!r} is neither a known alias nor a known model id. "
        f"Run `resolve_model.py --list` to see what's available."
    )


def check(model_id: str) -> tuple[str, str | None]:
    """Return (status, replacement_id) for a model ID.
    status is one of: current, supported, preview, deprecated, unknown."""
    idx = _model_index()
    if model_id not in idx:
        return ("unknown", None)
    m = idx[model_id]
    return (m.get("status", "current"), m.get("replacement_id"))


def list_models(
    vendor: str | None = None,
    modality: str | None = None,
    status: str | None = None,
    tier: str | None = None,
) -> list[dict[str, Any]]:
    reg = get_registry()
    out = []
    for m in reg.get("models", []):
        if vendor and m.get("vendor") != vendor:
            continue
        if modality and modality not in (m.get("modality") or []):
            continue
        if status and m.get("status") != status:
            continue
        if tier and m.get("tier") != tier:
            continue
        out.append(m)
    return out


def registry_age_days() -> int | None:
    reg = get_registry()
    s = reg.get("last_updated")
    if not s:
        return None
    try:
        d = datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (date.today() - d).days


def _print(obj: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(obj, indent=2, ensure_ascii=False))
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                line = f"{item.get('id'):60s}  {item.get('status', '?'):12s}  {item.get('vendor', '?'):10s}  {item.get('display_name', '')}"
                print(line)
            else:
                print(item)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            print(f"{k}: {v}")
    else:
        print(obj)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve, check, and list curated AI models for the Neelverse Marketing Suite."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--alias", help="Resolve an alias (e.g. latest-fast-anthropic) OR a model id")
    group.add_argument("--check", help="Report status (current/deprecated/supported/preview/unknown) for a model id")
    group.add_argument("--list", action="store_true", help="List models (filter with --vendor / --modality / --status / --tier)")
    group.add_argument("--registry-age", action="store_true", help="Print days since last_updated")
    group.add_argument("--registry-path", action="store_true", help="Print path to the loaded registry file")
    group.add_argument("--aliases", action="store_true", help="Print all aliases and their resolutions")

    parser.add_argument("--vendor")
    parser.add_argument("--modality")
    parser.add_argument("--status")
    parser.add_argument("--tier")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--allow-deprecated", action="store_true",
                        help="With --alias, return the deprecated id instead of its replacement")
    args = parser.parse_args()

    try:
        if args.alias:
            try:
                resolved = resolve(args.alias, allow_deprecated=args.allow_deprecated)
                if args.json:
                    print(json.dumps({"input": args.alias, "resolved": resolved}))
                else:
                    print(resolved)
                return 0
            except (KeyError, ValueError) as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1

        if args.check:
            status, replacement = check(args.check)
            payload = {"model": args.check, "status": status, "replacement_id": replacement}
            if args.json:
                print(json.dumps(payload))
            else:
                line = f"{args.check}: {status}"
                if replacement:
                    line += f" (use {replacement})"
                print(line)
            return 1 if status in {"deprecated", "unknown"} else 0

        if args.list:
            models = list_models(args.vendor, args.modality, args.status, args.tier)
            _print(models, args.json)
            return 0

        if args.registry_age:
            age = registry_age_days()
            if age is None:
                print("UNKNOWN — no last_updated in registry", file=sys.stderr)
                return 2
            reg = get_registry()
            if args.json:
                print(json.dumps({"last_updated": reg.get("last_updated"), "age_days": age,
                                  "next_review_due": reg.get("next_review_due")}))
            else:
                print(f"last_updated: {reg.get('last_updated')} ({age} days ago). "
                      f"next_review_due: {reg.get('next_review_due')}")
            return 0

        if args.registry_path:
            print(_find_registry())
            return 0

        if args.aliases:
            reg = get_registry()
            aliases = reg.get("aliases", {})
            if args.json:
                print(json.dumps(aliases, indent=2))
            else:
                for alias, target in aliases.items():
                    print(f"{alias:42s}  ->  {target}")
            return 0

    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
