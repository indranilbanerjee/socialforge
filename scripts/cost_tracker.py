#!/usr/bin/env python3
"""
cost_tracker.py — Track API costs per post and per month.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Persistent storage: prefer ${CLAUDE_PLUGIN_DATA} (survives sessions/updates),
# fall back to ~/socialforge-workspace (legacy/local)
_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
if _plugin_data and Path(_plugin_data).exists():
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
    WORKSPACE = Path.home() / "socialforge-workspace"

# Operations that genuinely cost nothing, because they run locally.
#
# This is the only cost knowledge left in this file. There used to be a table of
# per-operation dollar figures here, and it was wrong in three ways at once:
# it was keyed by operation rather than by model, so a 3-second clip and a
# 15-second clip logged the same amount; it assumed $0.40/sec for video while a
# provider already wired into this plugin was selling at a fraction of that; and
# it went stale silently, because nothing about a hardcoded number announces its
# own age.
#
# Paid work is now priced by price_book.py, which holds no figures of its own and
# only reports what a live lookup recorded, with the URL it came from. Pass
# --cost with the real amount, or let this module ask the price book.
FREE_OPERATIONS = {
    "background_removal",  # local rembg
    "compositing",         # local Pillow
    "carousel_render",     # local Playwright
    "resize",              # local Pillow
}


def write_json_atomic(path, data):
    """Write JSON via a temp file + os.replace so a crash can't truncate the cost log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def log_cost(brand, month, post_id, operation, actual_cost=None,
             model=None, provider=None, units=None, multiplier=1.0):
    """Log an API cost entry.

    Three ways a figure can get here, in descending order of trust:

    1. `actual_cost` — what was really invoiced. Always preferred.
    2. A live price-book quote, when `model`, `provider` and `units` are given.
       That figure came from a recorded lookup with a source URL and an expiry.
    3. Nothing. The operation is logged with a null cost and flagged `unpriced`.

    What no longer happens is the fourth option: inventing a plausible number
    from a table. A month's report built on guesses looks exactly like one built
    on invoices, and a client cannot tell them apart.
    """
    cost_path = WORKSPACE / "output" / brand / month / "cost-log.json"
    if not cost_path.exists():
        print(json.dumps({"error": "Cost log not found. Run init-month first."}))
        sys.exit(1)

    cost_log = json.loads(cost_path.read_text(encoding="utf-8"))

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "post_id": post_id,
        "operation": operation,
    }

    if actual_cost is not None:
        entry.update(cost_usd=float(actual_cost), basis="actual")
    elif operation in FREE_OPERATIONS:
        entry.update(cost_usd=0.0, basis="local-no-api-cost")
    elif model and provider and units is not None:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import price_book
            q = price_book.quote(model, provider, float(units), multiplier=multiplier)
        except Exception as exc:  # price book unavailable — say so, don't guess
            entry.update(cost_usd=None, basis="unpriced",
                         note=f"price book unavailable: {exc}")
        else:
            if q.get("quotable"):
                entry.update(cost_usd=q["total_usd"], basis="price-book-quote",
                             model=q["model"], provider=q["provider"],
                             unit_price_usd=q["unit_price_usd"], units=float(units),
                             source=q["source"], priced_at=q["priced_at"])
                if multiplier != 1.0:
                    entry["multiplier"] = multiplier
            else:
                entry.update(cost_usd=None, basis="unpriced",
                             note=q.get("action_required"))
    else:
        entry.update(cost_usd=None, basis="unpriced",
                     note="no --cost given and no --model/--provider/--units to quote from")

    if entry.get("cost_usd") is None:
        print(f"WARNING: {operation!r} logged with no cost. Recording it as unpriced "
              f"rather than $0.00 — a zero would quietly understate the month. "
              f"Pass --cost, or --model/--provider/--units to quote it.", file=sys.stderr)

    cost_log["entries"].append(entry)
    priced = [e for e in cost_log["entries"] if e.get("cost_usd") is not None]
    unpriced = len(cost_log["entries"]) - len(priced)
    cost_log["total_cost_usd"] = round(sum(e["cost_usd"] for e in priced), 4)
    cost_log["unpriced_entries"] = unpriced
    if unpriced:
        cost_log["total_is_complete"] = False
        cost_log["total_note"] = (
            f"{unpriced} entr{'y' if unpriced == 1 else 'ies'} could not be priced. "
            f"The total below covers only what could.")
    else:
        cost_log["total_is_complete"] = True
        cost_log.pop("total_note", None)

    write_json_atomic(cost_path, cost_log)
    print(json.dumps({"logged": entry, "total": cost_log["total_cost_usd"],
                      "total_is_complete": cost_log["total_is_complete"]}))


def get_report(brand, month):
    """Get cost report for the month."""
    cost_path = WORKSPACE / "output" / brand / month / "cost-log.json"
    if not cost_path.exists():
        print(json.dumps({"error": "No cost log found"}))
        sys.exit(1)

    cost_log = json.loads(cost_path.read_text(encoding="utf-8"))

    # Aggregate by operation
    by_operation = {}
    by_post = {}
    # An unpriced entry carries cost_usd: None on purpose — the plugin refuses
    # to invent a price it did not look up. Summing that raised TypeError, so
    # `--action report` crashed in precisely the situation that produces
    # unpriced entries: no credentials, or a model with no recorded price.
    # Count them separately; unpriced is not zero, and must never read as zero.
    unpriced = 0
    for entry in cost_log["entries"]:
        op = entry["operation"]
        cost = entry.get("cost_usd")
        pid = entry.get("post_id", "unknown")
        if cost is None:
            unpriced += 1
            by_operation.setdefault(op, 0.0)
            by_post.setdefault(pid, 0.0)
            continue
        by_operation[op] = by_operation.get(op, 0.0) + cost
        by_post[pid] = by_post.get(pid, 0.0) + cost

    print(json.dumps({
        "brand": brand,
        "month": month,
        "total_cost_usd": cost_log["total_cost_usd"],
        "total_api_calls": len(cost_log["entries"]),
        "by_operation": {k: round(v, 4) for k, v in sorted(by_operation.items(), key=lambda x: -x[1])},
        "by_post": {k: round(v, 4) for k, v in sorted(by_post.items(), key=lambda x: -x[1])[:10]},
        # Surfaced so a total can never be mistaken for a complete total.
        "unpriced_calls": unpriced,
        "totals_complete": unpriced == 0,
        "note": (None if unpriced == 0 else
                 f"{unpriced} call(s) have no recorded price, so every total above is a "
                 f"LOWER BOUND. Record the missing prices with price_book.py --action record. "
                 f"Unpriced is not the same as free."),
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description="SocialForge Cost Tracker")
    parser.add_argument("--action", required=True, choices=["log", "report"])
    parser.add_argument("--brand", required=True)
    parser.add_argument("--month", required=True)
    parser.add_argument("--post-id", default=None)
    parser.add_argument("--operation", default=None)
    parser.add_argument("--cost", type=float, default=None,
                        help="The real invoiced amount. Always preferred over a quote.")
    parser.add_argument("--model", default=None,
                        help="With --provider and --units, price this entry from the "
                             "live price book instead of leaving it unpriced.")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--units", type=float, default=None,
                        help="Seconds for video, images for stills.")
    parser.add_argument("--multiplier", type=float, default=1.0,
                        help="Option surcharge, e.g. 1.5 when sound is enabled.")
    args = parser.parse_args()

    if args.action == "log":
        if not args.operation:
            print("Error: --operation required for log action", file=sys.stderr)
            sys.exit(1)
        log_cost(args.brand, args.month, args.post_id or "system", args.operation,
                 args.cost, model=args.model, provider=args.provider,
                 units=args.units, multiplier=args.multiplier)
    elif args.action == "report":
        get_report(args.brand, args.month)


if __name__ == "__main__":
    main()
