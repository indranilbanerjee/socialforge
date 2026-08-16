#!/usr/bin/env python3
"""
delivery_audit.py — SocialForge month-delivery audit.

Re-derives a month's delivery claims from the ledger and the files on disk, so
"the tracker says FINAL" and "the disk proves FINAL" cannot drift apart
silently. The pattern follows the suite-wide run-audit discipline: every check
corresponds to a failure observed on a real run while each individual
artifact looked healthy.

What it verifies:
  A. The approval ledger's integrity — every post status in the vocabulary,
     revision history arithmetic consistent (last transition lands on the
     current status), no ghost posts (tracker ids the calendar never knew).
  B. Force-finalized posts surfaced LOUDLY — a gate that was bypassed is a
     fact the delivery reader deserves to see, not a flag buried in JSON.
  C. FINAL posts' files — every asset path referenced by a FINAL post's
     calendar entry exists and is non-empty (the render_preview lesson:
     a path that resolves to nothing becomes an empty rectangle a client
     approves).
  D. The failure log parses — structured failure records are only worth what
     a reader can load.
  E. The cost report runs and is honest about incompleteness — unpriced is
     not free, and totals must say when they are a lower bound.

A missing input downgrades a check to reported-N/A, never to silent-pass.

Usage:
    python delivery_audit.py --brand <brand> --month <YYYY-MM> [--strict] [--out FILE]

Writes ``delivery-audit.json`` into the month's output folder.
Exit codes: 0 clean · 1 violations (with --strict, N/A too) · 2 usage error.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Persistent storage: prefer ${CLAUDE_PLUGIN_DATA} (survives sessions/updates),
# fall back to ~/socialforge-workspace (legacy/local)
_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("PLUGIN_DATA") or ""
if _plugin_data and Path(_plugin_data).exists():
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
    WORKSPACE = Path.home() / "socialforge-workspace"

SCRIPTS = Path(__file__).resolve().parent

KNOWN_STATUSES = {"QUEUED", "ASSET_MATCHING", "GENERATING", "PENDING_REVIEW",
                  "APPROVED_INTERNAL", "PENDING_CLIENT", "REVISION_REQUESTED",
                  "REJECTED", "FINAL"}


class Audit:
    def __init__(self):
        self.checks = []

    def check(self, section, name, ok, detail=""):
        self.checks.append({"section": section, "name": name,
                            "result": "PASS" if ok else "FAIL",
                            "detail": detail or None})

    def na(self, section, name, reason):
        self.checks.append({"section": section, "name": name,
                            "result": "N/A", "detail": reason})

    def summary(self, strict=False):
        p = sum(1 for c in self.checks if c["result"] == "PASS")
        f = sum(1 for c in self.checks if c["result"] == "FAIL")
        n = sum(1 for c in self.checks if c["result"] == "N/A")
        verdict = "CLEAN" if f == 0 and (not strict or n == 0) else "VIOLATIONS"
        return {"pass": p, "fail": f, "na": n, "verdict": verdict}


def _json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def audit_month(brand: str, month: str, strict=False) -> dict:
    a = Audit()
    month_dir = WORKSPACE / "output" / brand / month

    tracker = _json(month_dir / "status-tracker.json")
    a.check("A ledger", "status tracker parses", tracker is not None,
            str(month_dir / "status-tracker.json"))
    if tracker is None:
        return {"brand": brand, "month": month, "checks": a.checks,
                **a.summary(strict)}

    posts = tracker.get("posts", {})
    calendar = _json(month_dir / "calendar-data.json")
    cal_posts = {str(p.get("post_id")): p
                 for p in (calendar or {}).get("posts", [])}

    bad_status = {pid: p.get("status") for pid, p in posts.items()
                  if p.get("status") not in KNOWN_STATUSES}
    a.check("A ledger", "every post status is in the vocabulary",
            not bad_status, str(bad_status))

    drift = []
    for pid, p in posts.items():
        hist = p.get("revision_history", [])
        if hist and hist[-1].get("to") != p.get("status"):
            drift.append(pid)
    a.check("A ledger", "history arithmetic lands on the current status",
            not drift, f"last transition disagrees with status for: {drift}")

    if calendar is not None:
        ghosts = sorted(set(posts) - set(cal_posts))
        a.check("A ledger", "no tracked post the calendar never knew",
                not ghosts, f"ghost posts: {ghosts}")
    else:
        a.na("A ledger", "ghost-post check", "no calendar-data.json")

    # ------------------------------------------------------------- B. forced
    forced = [pid for pid, p in posts.items() if p.get("force_finalized")]
    if forced:
        a.check("B forced", "no gate was bypassed on the way to delivery",
                False, f"force_finalized posts: {forced} — a bypassed gate is "
                       f"a decision the delivery reader must see")
    else:
        a.check("B forced", "no gate was bypassed on the way to delivery", True)

    # -------------------------------------------------------------- C. files
    final_ids = [pid for pid, p in posts.items() if p.get("status") == "FINAL"]
    if final_ids and calendar is not None:
        missing = []
        for pid in final_ids:
            entry = cal_posts.get(pid, {})
            for key in ("asset_path", "image_path", "file_path", "video_path"):
                val = entry.get(key)
                if val:
                    f = Path(val)
                    if not f.is_absolute():
                        f = month_dir / val
                    if not f.is_file() or f.stat().st_size == 0:
                        missing.append(f"{pid}:{key}={val}")
        a.check("C files", "every FINAL post's referenced file exists non-empty",
                not missing, f"missing/empty: {missing}")
    elif final_ids:
        a.na("C files", "FINAL file check", "no calendar to resolve paths from")
    else:
        a.na("C files", "FINAL file check", "no FINAL posts yet")

    # ---------------------------------------------------------- D. failure log
    flog = WORKSPACE / "shared" / "failure-log.jsonl"
    if flog.is_file():
        bad_lines = 0
        for line in flog.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    bad_lines += 1
        a.check("D failures", "failure log lines all parse", bad_lines == 0,
                f"{bad_lines} unreadable line(s) — a failure record nobody can "
                f"load protected nobody")
    else:
        a.na("D failures", "failure log", "no shared/failure-log.jsonl "
             "(no recorded provider failures)")

    # -------------------------------------------------------------- E. costs
    cost = SCRIPTS / "cost_tracker.py"
    if cost.is_file():
        proc = subprocess.run(
            [sys.executable, str(cost), "--action", "report",
             "--brand", brand, "--month", month],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        report = None
        try:
            report = json.loads(proc.stdout)
        except json.JSONDecodeError:
            pass
        crashed = "Traceback" in (proc.stderr or "")
        a.check("E costs", "cost report runs without crashing", not crashed,
                proc.stderr[:160])
        if report is not None and report.get("unpriced_calls"):
            a.check("E costs", "incomplete totals say they are a lower bound",
                    report.get("totals_complete") is False,
                    "unpriced calls present but totals_complete is not false")
    else:
        a.na("E costs", "cost report", "cost_tracker.py not found")

    return {"brand": brand, "month": month, "final_posts": len(final_ids),
            "total_posts": len(posts), "checks": a.checks, **a.summary(strict)}


def main():
    ap = argparse.ArgumentParser(description="Audit a month's delivery claims "
                                             "against the disk.")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--month", required=True, help="YYYY-MM")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    result = audit_month(args.brand, args.month, strict=args.strict)
    month_dir = WORKSPACE / "output" / args.brand / args.month
    out = Path(args.out).expanduser() if args.out else \
        month_dir / "delivery-audit.json"
    if out.parent.is_dir():
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
        result["written_to"] = str(out)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["verdict"] == "CLEAN" else 1)


if __name__ == "__main__":
    main()
