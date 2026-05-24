#!/usr/bin/env python3
"""
refresh_models.py — Poll provider APIs and report drift against the registry.

Reads model_registry.json, calls the provider list endpoints where available,
and prints:
  • Models in the provider catalog that are NOT in the registry (additions to triage)
  • Models in the registry marked "current" that the provider no longer lists
  • Models in the registry marked "deprecated" that the provider has stopped serving
  • A simple summary + next_review_due reminder

By default this is REPORT-ONLY. Pass --bump-timestamp to update last_updated
to today after a manual review pass. The script never silently rewrites model
entries; curation is a human decision.

Requires (per provider) one or more of:
  ANTHROPIC_API_KEY   — calls https://api.anthropic.com/v1/models
  OPENAI_API_KEY      — calls https://api.openai.com/v1/models
  GEMINI_API_KEY      — calls https://generativelanguage.googleapis.com/v1beta/models

Usage:
    python refresh_models.py            # report drift
    python refresh_models.py --json     # machine-readable
    python refresh_models.py --bump-timestamp  # set last_updated to today
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from resolve_model import _find_registry, get_registry  # noqa: E402


def _http_get(url: str, headers: dict[str, str], timeout: int = 15) -> dict | None:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return None


def list_anthropic() -> set[str] | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    data = _http_get(
        "https://api.anthropic.com/v1/models",
        {"x-api-key": key, "anthropic-version": "2023-06-01"},
    )
    if not data:
        return None
    return {m.get("id") for m in data.get("data", []) if m.get("id")}


def list_openai() -> set[str] | None:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    data = _http_get(
        "https://api.openai.com/v1/models",
        {"Authorization": f"Bearer {key}"},
    )
    if not data:
        return None
    return {m.get("id") for m in data.get("data", []) if m.get("id")}


def list_gemini() -> set[str] | None:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    data = _http_get(
        f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
        {},
    )
    if not data:
        return None
    return {
        m.get("name", "").replace("models/", "")
        for m in data.get("models", [])
        if m.get("name")
    }


def diff(registry_ids: set[str], live_ids: set[str]) -> dict[str, list[str]]:
    return {
        "missing_from_registry": sorted(live_ids - registry_ids),
        "missing_from_live": sorted(registry_ids - live_ids),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Report model-registry drift")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--bump-timestamp",
        action="store_true",
        help="Set last_updated to today (use after a manual curation pass)",
    )
    args = parser.parse_args()

    reg = get_registry()
    reg_path = _find_registry()
    by_vendor: dict[str, set[str]] = {}
    for m in reg.get("models", []):
        by_vendor.setdefault(m.get("vendor", ""), set()).add(m.get("id"))

    report: dict[str, dict] = {
        "registry_path": str(reg_path),
        "registry_last_updated": reg.get("last_updated"),
        "registry_next_review_due": reg.get("next_review_due"),
    }

    for vendor, fetcher in (
        ("anthropic", list_anthropic),
        ("openai", list_openai),
        ("google", list_gemini),
    ):
        live = fetcher()
        if live is None:
            report[vendor] = {"status": "skipped (no API key or fetch failed)"}
            continue
        d = diff(by_vendor.get(vendor, set()), live)
        report[vendor] = {
            "status": "checked",
            "live_count": len(live),
            "registry_count": len(by_vendor.get(vendor, set())),
            **d,
        }

    if args.bump_timestamp:
        reg["last_updated"] = date.today().isoformat()
        reg_path.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
        report["timestamp_bumped"] = reg["last_updated"]

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Registry: {report['registry_path']}")
        print(f"Last updated: {report['registry_last_updated']}  "
              f"(next review due: {report['registry_next_review_due']})")
        if "timestamp_bumped" in report:
            print(f"  -> timestamp bumped to {report['timestamp_bumped']}")
        for v in ("anthropic", "openai", "google"):
            r = report.get(v, {})
            print(f"\n{v.upper()}: {r.get('status')}")
            if r.get("status") == "checked":
                if r["missing_from_registry"]:
                    print(f"  NEW (not in registry, may need to add):")
                    for m in r["missing_from_registry"]:
                        print(f"    + {m}")
                if r["missing_from_live"]:
                    print(f"  STALE (in registry, not in provider list):")
                    for m in r["missing_from_live"]:
                        print(f"    - {m}")
                if not r["missing_from_registry"] and not r["missing_from_live"]:
                    print("  no drift")
    return 0


if __name__ == "__main__":
    sys.exit(main())
