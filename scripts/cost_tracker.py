#!/usr/bin/env python3
"""
cost_tracker.py — Track API costs per post and per month.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Persistent storage: prefer ${CLAUDE_PLUGIN_DATA} (survives sessions/updates),
# fall back to ~/socialforge-workspace (legacy/local)
_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
if _plugin_data and Path(_plugin_data).exists():
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
    WORKSPACE = Path.home() / "socialforge-workspace"

# Approximate costs per API call (USD)
COST_ESTIMATES = {
    "gemini_vision_analysis": 0.003,
    "gemini_image_generation": 0.02,
    "gemini_image_edit": 0.015,
    "gemini_video_generation": 0.10,
    "fal_ai_generation": 0.03,
    "replicate_generation": 0.025,
    "background_removal": 0.0,  # local rembg, free
    "compositing": 0.0,  # local Pillow, free
    "carousel_render": 0.0,  # local Playwright, free
}


def log_cost(brand, month, post_id, operation, actual_cost=None):
    """Log an API cost entry."""
    cost_path = WORKSPACE / "output" / brand / month / "cost-log.json"
    if not cost_path.exists():
        print(json.dumps({"error": "Cost log not found. Run init-month first."}))
        sys.exit(1)

    cost_log = json.loads(cost_path.read_text(encoding="utf-8"))

    cost = actual_cost if actual_cost is not None else COST_ESTIMATES.get(operation, 0.0)

    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "post_id": post_id,
        "operation": operation,
        "cost_usd": cost
    }

    cost_log["entries"].append(entry)
    cost_log["total_cost_usd"] = round(sum(e["cost_usd"] for e in cost_log["entries"]), 4)

    cost_path.write_text(json.dumps(cost_log, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"logged": entry, "total": cost_log["total_cost_usd"]}))


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
    for entry in cost_log["entries"]:
        op = entry["operation"]
        by_operation[op] = by_operation.get(op, 0.0) + entry["cost_usd"]
        pid = entry.get("post_id", "unknown")
        by_post[pid] = by_post.get(pid, 0.0) + entry["cost_usd"]

    print(json.dumps({
        "brand": brand,
        "month": month,
        "total_cost_usd": cost_log["total_cost_usd"],
        "total_api_calls": len(cost_log["entries"]),
        "by_operation": {k: round(v, 4) for k, v in sorted(by_operation.items(), key=lambda x: -x[1])},
        "by_post": {k: round(v, 4) for k, v in sorted(by_post.items(), key=lambda x: -x[1])[:10]},
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description="SocialForge Cost Tracker")
    parser.add_argument("--action", required=True, choices=["log", "report"])
    parser.add_argument("--brand", required=True)
    parser.add_argument("--month", required=True)
    parser.add_argument("--post-id", default=None)
    parser.add_argument("--operation", default=None)
    parser.add_argument("--cost", type=float, default=None)
    args = parser.parse_args()

    if args.action == "log":
        if not args.operation:
            print("Error: --operation required for log action", file=sys.stderr)
            sys.exit(1)
        log_cost(args.brand, args.month, args.post_id or "system", args.operation, args.cost)
    elif args.action == "report":
        get_report(args.brand, args.month)


if __name__ == "__main__":
    main()
