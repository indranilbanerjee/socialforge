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


def _http_get(url: str, headers: dict[str, str], timeout: int = 15) -> tuple[dict | None, str | None]:
    """Fetch JSON, returning (data, error). The error string names the actual
    cause — a 401 bad key, a 429 rate limit, and a DNS failure are three
    different problems, and a drift report that conflates them cannot be
    acted on."""
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        return None, f"http-{e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return None, f"network: {e.reason}"
    except json.JSONDecodeError as e:
        return None, f"malformed-json: {e}"


def list_anthropic() -> tuple[set[str] | None, str | None]:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None, "no-key: ANTHROPIC_API_KEY not set"
    data, err = _http_get(
        "https://api.anthropic.com/v1/models",
        {"x-api-key": key, "anthropic-version": "2023-06-01"},
    )
    if err:
        return None, err
    if not data:
        return None, "empty-response: provider returned no body"
    return {m.get("id") for m in data.get("data", []) if m.get("id")}, None


def list_openai() -> tuple[set[str] | None, str | None]:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None, "no-key: OPENAI_API_KEY not set"
    data, err = _http_get(
        "https://api.openai.com/v1/models",
        {"Authorization": f"Bearer {key}"},
    )
    if err:
        return None, err
    if not data:
        return None, "empty-response: provider returned no body"
    return {m.get("id") for m in data.get("data", []) if m.get("id")}, None


def list_gemini() -> tuple[set[str] | None, str | None]:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None, "no-key: GEMINI_API_KEY not set"
    data, err = _http_get(
        f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
        {},
    )
    if err:
        return None, err
    if not data:
        return None, "empty-response: provider returned no body"
    return {
        m.get("name", "").replace("models/", "")
        for m in data.get("models", [])
        if m.get("name")
    }, None


def diff(registry_statuses: dict[str, str], live_ids: set[str]) -> dict[str, list[str]]:
    """Status-aware drift.

    `missing_from_live` is partitioned so a "current" model the provider stopped
    listing (a real problem) is not reported alongside a "deprecated" or "retired"
    one that is expected to disappear.
    """
    registry_ids = set(registry_statuses)
    gone = registry_ids - live_ids
    return {
        "missing_from_registry": sorted(live_ids - registry_ids),
        "missing_from_live": sorted(gone),
        "current_missing_from_live": sorted(
            i for i in gone if registry_statuses.get(i, "current") in ("current", "supported", "preview")),
        "retired_missing_from_live": sorted(
            i for i in gone if registry_statuses.get(i, "current") in ("deprecated", "retired")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Report model-registry drift")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--bump-timestamp",
        action="store_true",
        help="Set last_updated to today (use after a manual curation pass)",
    )
    parser.add_argument(
        "--force-bump",
        action="store_true",
        help="Allow --bump-timestamp even when no vendor could actually be checked",
    )
    args = parser.parse_args()

    reg = get_registry()
    reg_path = _find_registry()
    by_vendor: dict[str, dict[str, str]] = {}
    for m in reg.get("models", []):
        by_vendor.setdefault(m.get("vendor", ""), {})[m.get("id")] = m.get("status", "current")

    report: dict[str, dict] = {
        "registry_path": str(reg_path),
        "registry_last_updated": reg.get("last_updated"),
        "registry_next_review_due": reg.get("next_review_due"),
    }

    vendors_checked = 0
    for vendor, fetcher in (
        ("anthropic", list_anthropic),
        ("openai", list_openai),
        ("google", list_gemini),
    ):
        live, err = fetcher()
        if live is None:
            # "skipped" = deliberately not checkable (no key configured);
            # "error" = SHOULD have been checkable but the fetch failed.
            kind = "skipped" if err and err.startswith("no-key") else "error"
            report[vendor] = {"status": kind, "reason": err}
            continue
        vendors_checked += 1
        d = diff(by_vendor.get(vendor, {}), live)
        report[vendor] = {
            "status": "checked",
            "live_count": len(live),
            "registry_count": len(by_vendor.get(vendor, {})),
            **d,
        }
    report["vendors_checked"] = vendors_checked

    bump_refused = False
    if args.bump_timestamp:
        if vendors_checked == 0 and not args.force_bump:
            # Stamping a review that checked nothing turns the freshness date
            # into a lie — every downstream staleness gate trusts it.
            bump_refused = True
            report["timestamp_bump_refused"] = (
                "no vendor was actually checked (see per-vendor reasons) — "
                "refusing to stamp last_updated over an unverified registry. "
                "Fix the reasons or pass --force-bump to override.")
        else:
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
        if "timestamp_bump_refused" in report:
            print(f"  !! BUMP REFUSED: {report['timestamp_bump_refused']}")
        for v in ("anthropic", "openai", "google"):
            r = report.get(v, {})
            status_line = r.get("status", "?")
            if r.get("reason"):
                status_line += f" — {r['reason']}"
            print(f"\n{v.upper()}: {status_line}")
            if r.get("status") == "checked":
                if r["missing_from_registry"]:
                    print("  NEW (not in registry, may need to add):")
                    for m in r["missing_from_registry"]:
                        print(f"    + {m}")
                if r["current_missing_from_live"]:
                    print("  STALE (marked current in registry, not in provider list):")
                    for m in r["current_missing_from_live"]:
                        print(f"    - {m}")
                if r["retired_missing_from_live"]:
                    print("  EXPECTED (deprecated/retired in registry, provider stopped serving):")
                    for m in r["retired_missing_from_live"]:
                        print(f"    . {m}")
                if not r["missing_from_registry"] and not r["missing_from_live"]:
                    print("  no drift")
        print(f"\nVendors actually checked: {report['vendors_checked']}/3")
    return 2 if bump_refused else 0


if __name__ == "__main__":
    sys.exit(main())
