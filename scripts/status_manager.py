#!/usr/bin/env python3
"""
status_manager.py — SocialForge status tracking.
Manages pipeline state, post status transitions, and session initialization.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path.home() / "socialforge-workspace"


def session_init():
    """Initialize workspace on session start."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "brands").mkdir(exist_ok=True)
    (WORKSPACE / "output").mkdir(exist_ok=True)
    (WORKSPACE / "shared" / "prompt-logs").mkdir(parents=True, exist_ok=True)

    # List active brands
    brands_dir = WORKSPACE / "brands"
    brands = [d.name for d in brands_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]

    result = {"workspace": str(WORKSPACE), "brands": brands, "brand_count": len(brands)}
    print(json.dumps(result, indent=2))


VALID_TRANSITIONS = {
    "QUEUED": ["ASSET_MATCHING"],
    "ASSET_MATCHING": ["GENERATING", "QUEUED"],
    "GENERATING": ["PENDING_REVIEW", "QUEUED"],
    "PENDING_REVIEW": ["APPROVED_INTERNAL", "REVISION_REQUESTED", "REJECTED"],
    "APPROVED_INTERNAL": ["PENDING_CLIENT", "FINAL"],
    "REVISION_REQUESTED": ["GENERATING"],
    "REJECTED": ["QUEUED"],
    "PENDING_CLIENT": ["APPROVED_CLIENT", "REVISION_REQ_CLIENT", "REJECTED_CLIENT"],
    "APPROVED_CLIENT": ["PENDING_CEO", "FINAL"],
    "REVISION_REQ_CLIENT": ["GENERATING"],
    "REJECTED_CLIENT": ["QUEUED"],
    "PENDING_CEO": ["APPROVED_CEO", "REJECTED"],
    "APPROVED_CEO": ["FINAL"],
    "FINAL": [],  # Write-protected — no transitions allowed
}


def update_status(brand, month, post_id, new_status, actor="system", notes="", force=False):
    """Transition a post's status in the tracker with validation."""
    tracker_path = WORKSPACE / "output" / brand / month / "status-tracker.json"
    if not tracker_path.exists():
        print(json.dumps({"error": f"Status tracker not found: {tracker_path}"}))
        sys.exit(1)

    tracker = json.loads(tracker_path.read_text(encoding="utf-8"))
    post_key = str(post_id)

    if post_key not in tracker.get("posts", {}):
        tracker.setdefault("posts", {})[post_key] = {"status": "QUEUED", "revision_history": [], "flags": []}

    old_status = tracker["posts"][post_key]["status"]

    # Validate transition
    if not force:
        allowed = VALID_TRANSITIONS.get(old_status, [])
        if new_status not in allowed and old_status != new_status:
            print(json.dumps({
                "error": "Invalid state transition",
                "from": old_status,
                "to": new_status,
                "allowed": allowed,
                "hint": "Use --force to override (not recommended)"
            }))
            sys.exit(1)

    tracker["posts"][post_key]["status"] = new_status
    tracker["last_updated"] = datetime.utcnow().isoformat() + "Z"

    # Log transition
    tracker["posts"][post_key].setdefault("revision_history", []).append({
        "from": old_status,
        "to": new_status,
        "actor": actor,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "notes": notes
    })

    tracker_path.write_text(json.dumps(tracker, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"post_id": post_key, "old_status": old_status, "new_status": new_status}))


def get_summary(brand, month):
    """Get pipeline status summary."""
    tracker_path = WORKSPACE / "output" / brand / month / "status-tracker.json"
    if not tracker_path.exists():
        print(json.dumps({"error": "No active month found"}))
        sys.exit(1)

    tracker = json.loads(tracker_path.read_text(encoding="utf-8"))
    posts = tracker.get("posts", {})

    status_counts = {}
    for p in posts.values():
        s = p.get("status", "UNKNOWN")
        status_counts[s] = status_counts.get(s, 0) + 1

    print(json.dumps({
        "brand": brand,
        "month": month,
        "total_posts": len(posts),
        "status_distribution": status_counts,
        "last_updated": tracker.get("last_updated", "never")
    }, indent=2))


def init_month(brand, month):
    """Initialize a new month's tracking."""
    month_dir = WORKSPACE / "output" / brand / month
    month_dir.mkdir(parents=True, exist_ok=True)
    (month_dir / "production" / "images").mkdir(parents=True, exist_ok=True)
    (month_dir / "production" / "carousels").mkdir(parents=True, exist_ok=True)
    (month_dir / "production" / "previews").mkdir(parents=True, exist_ok=True)
    (month_dir / "production" / "copy").mkdir(parents=True, exist_ok=True)
    (month_dir / "production" / "video").mkdir(parents=True, exist_ok=True)
    (month_dir / "review").mkdir(parents=True, exist_ok=True)
    (month_dir / "FINAL").mkdir(parents=True, exist_ok=True)

    tracker = {
        "brand": brand,
        "month": month,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "pipeline_status": {
            "phase_0_parse": "not_started",
            "phase_1_asset_match": "not_started",
            "phase_2_production": "not_started",
            "phase_3_copy": "not_started",
            "phase_4_previews": "not_started",
            "phase_5_review_gallery": "not_started",
            "phase_6_approval": "not_started",
            "phase_7_finalized": "not_started"
        },
        "posts": {},
        "approval_summary": {
            "total_posts": 0, "finalized": 0, "approved_internal": 0,
            "pending_client": 0, "pending_ceo": 0, "revision_requested": 0,
            "rejected": 0, "blocked": 0
        }
    }

    tracker_path = month_dir / "status-tracker.json"
    tracker_path.write_text(json.dumps(tracker, indent=2, ensure_ascii=False), encoding="utf-8")

    cost_log = {"brand": brand, "month": month, "entries": [], "total_cost_usd": 0.0}
    (month_dir / "cost-log.json").write_text(json.dumps(cost_log, indent=2), encoding="utf-8")

    print(json.dumps({"action": "init_month", "brand": brand, "month": month, "path": str(month_dir)}))


def main():
    parser = argparse.ArgumentParser(description="SocialForge Status Manager")
    parser.add_argument("--action", required=True, choices=["session-init", "update-status", "get-summary", "init-month"])
    parser.add_argument("--brand", default=None)
    parser.add_argument("--month", default=None)
    parser.add_argument("--post-id", default=None)
    parser.add_argument("--status", default=None)
    parser.add_argument("--actor", default="system")
    parser.add_argument("--notes", default="")
    parser.add_argument("--force", action="store_true", help="Force state transition even if invalid")
    args = parser.parse_args()

    if args.action == "session-init":
        session_init()
    elif args.action == "update-status":
        if not all([args.brand, args.month, args.post_id, args.status]):
            print("Error: --brand, --month, --post-id, --status required", file=sys.stderr)
            sys.exit(1)
        update_status(args.brand, args.month, args.post_id, args.status, args.actor, args.notes, args.force)
    elif args.action == "get-summary":
        if not all([args.brand, args.month]):
            print("Error: --brand and --month required", file=sys.stderr)
            sys.exit(1)
        get_summary(args.brand, args.month)
    elif args.action == "init-month":
        if not all([args.brand, args.month]):
            print("Error: --brand and --month required", file=sys.stderr)
            sys.exit(1)
        init_month(args.brand, args.month)


if __name__ == "__main__":
    main()
