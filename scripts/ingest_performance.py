#!/usr/bin/env python3
"""
ingest_performance.py — turn platform analytics exports into the numbers
ideate-month compounds.

The ideation ladder's "compound the wins" rung is only as good as its input.
Before this script, "last month's results" meant whatever someone remembered
in the planning call — and memory favors the post that felt good, not the one
that performed. This ingests the platform's own export (CSV rows keyed to the
calendar's post ids), stores per-post metrics, and ranks wins with sample
floors and margin requirements, so a flat month says "no clear wins" instead
of crowning noise.

Doctrine (matches the suite's measurement ladder):
- missing impressions -> engagement_rate is None, never 0.0 (unmeasured != zero)
- a "win" needs BOTH a sample floor (default >= 100 impressions) AND a margin
  (>= 1.5x the month's median rate) — otherwise it is reported as unranked
- unmatched CSV rows are listed, never silently dropped
- every payload carries basis: "platform-export" + the source label + timestamp

Usage:
    python ingest_performance.py --action ingest --brand acme --month 2026-07 \
        --csv july-export.csv --source "linkedin-analytics"
    python ingest_performance.py --action wins --brand acme --month 2026-07
Exit codes: 0 ok, 1 bad input/paths, 3 ingest matched zero rows.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("PLUGIN_DATA") or ""
if _plugin_data and Path(_plugin_data).exists():
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
    WORKSPACE = Path.home() / "socialforge-workspace"

# Header aliases across platform exports (case/space-insensitive).
COLUMN_ALIASES = {
    "post_id": {"post_id", "post", "id", "postid", "post id"},
    "platform": {"platform", "channel", "network"},
    "date": {"date", "published", "publish_date", "publish date", "posted"},
    "impressions": {"impressions", "views", "reach", "plays", "video views", "video_views"},
    "likes": {"likes", "reactions", "favorites", "hearts"},
    "comments": {"comments", "replies"},
    "shares": {"shares", "reposts", "retweets", "sends"},
    "saves": {"saves", "bookmarks", "saved"},
    "clicks": {"clicks", "link_clicks", "link clicks", "website clicks"},
    "follows": {"follows", "new_followers", "new followers", "follower_gain"},
}
ENGAGEMENT_FIELDS = ("likes", "comments", "shares", "saves")


def _month_dir(brand, month):
    return WORKSPACE / "output" / brand / month


def _perf_path(brand, month):
    return _month_dir(brand, month) / "performance.json"


def _normalize_header(name):
    key = str(name).strip().lower()
    for canonical, aliases in COLUMN_ALIASES.items():
        if key in aliases:
            return canonical
    return None


def _to_int(value):
    """Parse a metric cell. Absent/unparseable -> None (unmeasured), never 0."""
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _load_calendar_ids(brand, month):
    calendar_path = _month_dir(brand, month) / "calendar-data.json"
    if not calendar_path.exists():
        return None, {}
    try:
        calendar = json.loads(calendar_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"WARNING: calendar-data.json unreadable ({type(e).__name__}) — "
              "rows cannot be matched to posts", file=sys.stderr)
        return None, {}
    meta = {}
    for p in calendar.get("posts", []):
        pid = str(p.get("post_id", "")).strip().upper()
        if pid:
            meta[pid] = {k: p.get(k) for k in ("topic", "title", "pillar", "tier",
                                               "series", "content_type", "date")}
    return set(meta), meta


def ingest(brand, month, csv_path, source_label):
    known_ids, _ = _load_calendar_ids(brand, month)
    if known_ids is None:
        print(json.dumps({"error": f"No calendar-data.json for {brand}/{month} — "
                          "ingest matches rows to calendar post ids; run the month "
                          "setup (or check --brand/--month) first"}))
        return 1

    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(json.dumps({"error": f"CSV not found: {csv_path}"}))
        return 1

    with open(csv_file, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        field_map = {}
        for raw in reader.fieldnames or []:
            canonical = _normalize_header(raw)
            if canonical and canonical not in field_map:
                field_map[canonical] = raw
        if "post_id" not in field_map:
            print(json.dumps({
                "error": "CSV has no recognizable post-id column",
                "seen_headers": reader.fieldnames,
                "accepted_post_id_headers": sorted(COLUMN_ALIASES["post_id"]),
            }, indent=2))
            return 1
        rows = list(reader)

    entries = {}
    unmatched = []
    for row in rows:
        pid = str(row.get(field_map["post_id"], "")).strip().upper()
        if pid not in known_ids:
            unmatched.append(pid or "(empty)")
            continue
        entry = {"platform": (row.get(field_map.get("platform", ""), "") or "").strip().lower()
                 or "unspecified"}
        for metric in ("impressions", "likes", "comments", "shares", "saves",
                       "clicks", "follows"):
            if metric in field_map:
                entry[metric] = _to_int(row.get(field_map[metric]))
        entries.setdefault(pid, []).append(entry)

    if not entries:
        print(json.dumps({
            "error": "No CSV row matched a calendar post id — nothing ingested",
            "unmatched_row_ids": unmatched[:20],
            "calendar_post_ids": sorted(known_ids),
        }, indent=2))
        return 3

    perf_path = _perf_path(brand, month)
    existing = {}
    if perf_path.exists():
        try:
            existing = json.loads(perf_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            print(f"WARNING: existing performance.json unreadable — rebuilding from "
                  f"this ingest only (damaged file at {perf_path})", file=sys.stderr)
    posts = existing.get("posts", {})
    for pid, new_rows in entries.items():
        posts.setdefault(pid, []).extend(new_rows)
    sources = existing.get("sources", [])
    sources.append({"label": source_label or csv_file.name,
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                    "rows_matched": sum(len(v) for v in entries.values()),
                    "rows_unmatched": len(unmatched)})

    _atomic_write(perf_path, {
        "brand": brand, "month": month, "basis": "platform-export",
        "sources": sources, "posts": posts,
    })

    result = {
        "status": "success",
        "output": str(perf_path),
        "posts_with_data": len(posts),
        "rows_matched": sum(len(v) for v in entries.values()),
        "rows_unmatched": len(unmatched),
    }
    if unmatched:
        # Unmatched rows are named — silent drops would misreport coverage.
        result["unmatched_row_ids"] = unmatched[:20]
    print(json.dumps(result, indent=2))
    return 0


def _post_totals(rows):
    """Aggregate a post's platform rows. None-safe: unmeasured stays None."""
    totals = {}
    for metric in ("impressions", "likes", "comments", "shares", "saves",
                   "clicks", "follows"):
        vals = [r[metric] for r in rows if r.get(metric) is not None]
        totals[metric] = sum(vals) if vals else None
    eng_vals = [totals[f] for f in ENGAGEMENT_FIELDS if totals.get(f) is not None]
    totals["engagement"] = sum(eng_vals) if eng_vals else None
    if totals.get("impressions") and totals.get("engagement") is not None:
        totals["engagement_rate"] = round(totals["engagement"] / totals["impressions"], 4)
    else:
        totals["engagement_rate"] = None  # unmeasured is not zero
    return totals


def wins(brand, month, min_impressions, top_k, margin):
    perf_path = _perf_path(brand, month)
    if not perf_path.exists():
        print(json.dumps({
            "status": "no_data",
            "note": (f"No performance.json for {brand}/{month} — ingest a platform "
                     "export first (--action ingest --csv <file>). Ideation can still "
                     "run, but its wins rung will be anecdotal and should say so."),
        }, indent=2))
        return 1
    try:
        perf = json.loads(perf_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(json.dumps({"error": f"performance.json unreadable: {type(e).__name__}: {e}"}))
        return 1
    _, calendar_meta = _load_calendar_ids(brand, month)

    scored = []
    unranked = []
    for pid, rows in perf.get("posts", {}).items():
        totals = _post_totals(rows)
        item = {"post_id": pid, **totals, **{
            k: v for k, v in (calendar_meta.get(pid) or {}).items() if v is not None}}
        rate = totals["engagement_rate"]
        impressions = totals.get("impressions")
        if rate is None or impressions is None:
            item["unranked_reason"] = "missing impressions or engagement — rate unmeasurable"
            unranked.append(item)
        elif impressions < min_impressions:
            item["unranked_reason"] = (f"only {impressions} impressions — below the "
                                       f"{min_impressions} sample floor; too noisy to rank")
            unranked.append(item)
        else:
            scored.append(item)

    scored.sort(key=lambda i: i["engagement_rate"], reverse=True)
    month_median = round(median(i["engagement_rate"] for i in scored), 4) if scored else None

    winners = []
    if month_median and month_median > 0:
        for item in scored[:top_k]:
            multiple = round(item["engagement_rate"] / month_median, 2)
            if multiple >= margin:
                winners.append({**item, "vs_month_median": f"{multiple}x"})
    elif scored:
        # median of 0 -> any nonzero engagement leads, but say what that means
        winners = [{**i, "vs_month_median": "n/a (month median is 0)"}
                   for i in scored[:top_k] if i["engagement_rate"] > 0]

    underperformers = [
        {**i, "vs_month_median": f"{round(i['engagement_rate'] / month_median, 2)}x"}
        for i in scored if month_median and i["engagement_rate"] <= month_median * 0.5
    ]

    verdict = "clear_wins" if winners else (
        "no_clear_wins" if scored else "nothing_rankable")
    print(json.dumps({
        "status": verdict,
        "basis": "platform-export",
        "sources": perf.get("sources", []),
        "month_median_engagement_rate": month_median,
        "sample_floor_impressions": min_impressions,
        "win_margin_vs_median": f"{margin}x",
        "winners": winners,
        "underperformers": underperformers,
        "unranked": unranked,
        "note": (None if winners else
                 "No post cleared the sample floor AND the margin — engagement was "
                 "flat. Compounding a non-win manufactures a false signal; plan from "
                 "pillars and signals instead, and say the wins rung had nothing."),
    }, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(description="SocialForge performance ingestion")
    parser.add_argument("--action", required=True, choices=["ingest", "wins"])
    parser.add_argument("--brand", required=True)
    parser.add_argument("--month", required=True, help="YYYY-MM (the month the numbers are FROM)")
    parser.add_argument("--csv", default=None, help="Platform analytics export (ingest)")
    parser.add_argument("--source", default=None, help="Label for where the export came from")
    parser.add_argument("--min-impressions", type=int, default=100,
                        help="Sample floor below which a post is not ranked (default 100)")
    parser.add_argument("--top", type=int, default=3, help="Max winners to report (default 3)")
    parser.add_argument("--margin", type=float, default=1.5,
                        help="Required multiple of the month-median rate to call a win (default 1.5)")
    args = parser.parse_args()

    if args.action == "ingest":
        if not args.csv:
            parser.error("--csv is required for --action ingest")
        sys.exit(ingest(args.brand, args.month, args.csv, args.source))
    sys.exit(wins(args.brand, args.month, args.min_impressions, args.top, args.margin))


if __name__ == "__main__":
    main()
