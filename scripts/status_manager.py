#!/usr/bin/env python3
"""
status_manager.py — SocialForge status tracking.
Manages pipeline state, post status transitions, and session initialization.
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


def utc_now():
    """Timezone-aware UTC timestamp in Zulu form."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


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


# Every status that may ever be written. All statuses appear as keys of
# VALID_TRANSITIONS, so the key set IS the vocabulary.
KNOWN_STATUSES = set(VALID_TRANSITIONS)


def update_status(brand, month, post_id, new_status, actor="system", notes="", force=False):
    """Transition a post's status in the tracker with validation."""
    tracker_path = WORKSPACE / "output" / brand / month / "status-tracker.json"
    if not tracker_path.exists():
        print(json.dumps({"error": f"Status tracker not found: {tracker_path}"}))
        sys.exit(1)

    # Vocabulary check comes before everything — --force overrides transition
    # RULES, never spelling. A status like "FINAL " (trailing space) or
    # "final" would freeze the post in a bucket no transition table knows.
    new_status = str(new_status).strip()
    if new_status not in KNOWN_STATUSES:
        print(json.dumps({
            "error": f"Unknown status '{new_status}'",
            "known_statuses": sorted(KNOWN_STATUSES),
            "hint": "--force overrides transition rules, not the status vocabulary",
        }))
        sys.exit(1)

    tracker = json.loads(tracker_path.read_text(encoding="utf-8"))
    post_key = str(post_id)

    if post_key not in tracker.get("posts", {}):
        # First transition for this post: legitimate only if the calendar
        # knows the id. Unconditional creation minted ghost posts — a typo'd
        # --post-id silently became a tracked post and polluted every summary.
        calendar_path = WORKSPACE / "output" / brand / month / "calendar-data.json"
        calendar_ids = set()
        if calendar_path.exists():
            try:
                calendar = json.loads(calendar_path.read_text(encoding="utf-8"))
                calendar_ids = {str(p.get("post_id")) for p in calendar.get("posts", [])}
            except (json.JSONDecodeError, OSError):
                pass
        if post_key not in calendar_ids:
            print(json.dumps({
                "error": f"Unknown post id '{post_key}' — not in the tracker and not in calendar-data.json",
                "known_post_ids": sorted(tracker.get("posts", {})) or sorted(calendar_ids),
                "hint": "Check the id; posts are created from the calendar, never from a status update",
            }))
            sys.exit(1)
        tracker.setdefault("posts", {})[post_key] = {"status": "QUEUED", "revision_history": [], "flags": []}

    old_status = tracker["posts"][post_key]["status"]

    # Validate transition
    allowed = VALID_TRANSITIONS.get(old_status, [])
    was_forced = force and new_status not in allowed and old_status != new_status
    if not force:
        if new_status not in allowed and old_status != new_status:
            print(json.dumps({
                "error": "Invalid state transition",
                "from": old_status,
                "to": new_status,
                "allowed": allowed,
                "hint": "Use --force to override (not recommended)"
            }))
            sys.exit(1)

    timestamp = utc_now()
    tracker["posts"][post_key]["status"] = new_status
    tracker["last_updated"] = timestamp

    # Log transition
    entry = {
        "from": old_status,
        "to": new_status,
        "actor": actor,
        "timestamp": timestamp,
        "notes": notes
    }
    if was_forced:
        # Audit trail — a gate was bypassed to reach this state
        entry["force_finalized"] = True
        tracker["posts"][post_key]["force_finalized"] = True
    tracker["posts"][post_key].setdefault("revision_history", []).append(entry)

    # Atomic write — this file is the approval/audit ledger; a crash mid-write
    # must never truncate the record of who approved what.
    tmp_path = tracker_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(tracker, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp_path, tracker_path)
    result = {"post_id": post_key, "old_status": old_status, "new_status": new_status}
    if was_forced:
        result["force_finalized"] = True
    print(json.dumps(result))


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


def _fs_component(value, fallback="unknown"):
    """Reduce a calendar-supplied value to filesystem-safe characters.

    Calendar data is parsed from client DOCX/XLSX/Notion — attacker-adjacent
    input. Anything outside [A-Za-z0-9_-] (including '.', '/', '\\') becomes
    '_' so no field can ever traverse out of the month tree.
    """
    import re as _re
    cleaned = _re.sub(r"[^A-Za-z0-9_-]", "_", str(value))
    return cleaned or fallback


def get_post_folder_name(post):
    """Generate descriptive folder name: P01-2026-04-07-linkedin-instagram-HERO-static"""
    pid = _fs_component(post.get("post_id", "P00"))
    date = _fs_component(post.get("date", "unknown"))
    platforms = "-".join(_fs_component(p.get("key") or p.get("name") or "") if isinstance(p, dict)
                         else _fs_component(p)
                         for p in post.get("platforms", []))
    tier = _fs_component(post.get("tier", "HUB"))
    ctype = _fs_component(post.get("content_type", "static"))
    return f"{pid}-{date}-{platforms}-{tier}-{ctype}"


def get_week_number(date_str):
    """Get week number within the month (1-5) from a date string."""
    try:
        from datetime import datetime as dt
        d = dt.strptime(date_str, "%Y-%m-%d")
        return (d.day - 1) // 7 + 1
    except (ValueError, TypeError):
        return 1


def init_post_folder(brand, month, post):
    """Create the post-specific folder structure."""
    month_dir = WORKSPACE / "output" / brand / month
    week = get_week_number(post.get("date", ""))
    folder_name = get_post_folder_name(post)
    post_dir = month_dir / "production" / f"week-{week}" / folder_name
    post_dir.mkdir(parents=True, exist_ok=True)
    (post_dir / "versions").mkdir(exist_ok=True)
    (post_dir / "final").mkdir(exist_ok=True)
    (post_dir / "copy").mkdir(exist_ok=True)
    ctype = post.get("content_type", "static")
    if ctype == "video":
        (post_dir / "keyframes").mkdir(exist_ok=True)
    if ctype == "carousel":
        (post_dir / "slides").mkdir(exist_ok=True)
    return str(post_dir)


def init_month(brand, month, force=False):
    """Initialize a new month's tracking.

    Existing status-tracker.json / cost-log.json are preserved so a re-run cannot
    destroy post state or cost history. Pass force=True to back them up and rebuild.
    """
    month_dir = WORKSPACE / "output" / brand / month
    month_dir.mkdir(parents=True, exist_ok=True)
    (month_dir / "production").mkdir(parents=True, exist_ok=True)
    (month_dir / "review").mkdir(parents=True, exist_ok=True)
    (month_dir / "FINAL").mkdir(parents=True, exist_ok=True)

    # Create post-specific folders if calendar exists
    calendar_path = month_dir / "calendar-data.json"
    if calendar_path.exists():
        calendar = json.loads(calendar_path.read_text(encoding="utf-8"))
        for post in calendar.get("posts", []):
            init_post_folder(brand, month, post)

    created_at = utc_now()
    tracker = {
        "brand": brand,
        "month": month,
        "created_at": created_at,
        "last_updated": created_at,
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

    cost_log = {"brand": brand, "month": month, "entries": [], "total_cost_usd": 0.0}

    preserved = []
    backed_up = []
    for path, payload in ((month_dir / "status-tracker.json", tracker),
                          (month_dir / "cost-log.json", cost_log)):
        if path.exists():
            if not force:
                preserved.append(path.name)
                continue
            backup = path.with_name(f"{path.stem}.{created_at.replace(':', '-')}.bak{path.suffix}")
            path.replace(backup)
            backed_up.append(backup.name)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    result = {"action": "init_month", "brand": brand, "month": month, "path": str(month_dir)}
    if preserved:
        result["preserved"] = preserved
        result["hint"] = "Existing state kept. Use --force to back it up and start fresh."
    if backed_up:
        result["backed_up"] = backed_up
    print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser(description="SocialForge Status Manager")
    parser.add_argument("--action", required=True, choices=["session-init", "update-status", "get-summary", "init-month", "get-post-folder"])
    parser.add_argument("--brand", default=None)
    parser.add_argument("--month", default=None)
    parser.add_argument("--post-id", default=None)
    parser.add_argument("--status", default=None)
    parser.add_argument("--actor", default="system")
    parser.add_argument("--notes", default="")
    parser.add_argument("--force", action="store_true",
                        help="Force state transition even if invalid; for init-month, back up and rebuild existing tracker/cost log")
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
        init_month(args.brand, args.month, args.force)
    elif args.action == "get-post-folder":
        if not all([args.brand, args.month, args.post_id]):
            print("Error: --brand, --month, --post-id required", file=sys.stderr)
            sys.exit(1)
        calendar_path = WORKSPACE / "output" / args.brand / args.month / "calendar-data.json"
        if not calendar_path.exists():
            print(json.dumps({"error": "Calendar not found"}))
            sys.exit(1)
        calendar = json.loads(calendar_path.read_text(encoding="utf-8"))
        post = next((p for p in calendar.get("posts", []) if str(p.get("post_id")) == str(args.post_id)), None)
        if not post:
            print(json.dumps({"error": f"Post {args.post_id} not found"}))
            sys.exit(1)
        post_dir = init_post_folder(args.brand, args.month, post)
        print(json.dumps({"post_id": args.post_id, "folder": post_dir, "name": get_post_folder_name(post)}))


if __name__ == "__main__":
    main()
