---
name: finalize-month
description: "Package all approved content into the final delivery folder — files renamed per convention, per-platform copy files, manifest included — ready for client handoff. Triggers on \"/finalize-month\", \"finalize the month\", \"package everything\", \"prepare the delivery\", \"close out the month\", \"handoff folder\", or when every post has cleared its approval queue and the month ships to the client."
argument-hint: "[--brand <name>] [--force]"
effort: high
user-invocable: true
disable-model-invocation: true
---

# /socialforge:finalize-month — Month Finalizer

Package all approved posts into the organized delivery folder structure.

## Pre-Finalization Check

**Step 0 — run the delivery audit, before any packaging:**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/delivery_audit.py" --brand {brand} --month {YYYY-MM}
```

It re-derives the month's claims from the ledger and the disk: every status in the vocabulary, revision history landing on the recorded status, no ghost posts the calendar never knew, no gate bypassed on the way to delivery (`force_finalized` is surfaced loudly, not left as a buried flag), every FINAL post's referenced file existing and non-empty, the failure log loadable, and cost totals honest about incompleteness. **Exit 1 means the delivery is claiming something the disk does not support — resolve the findings before packaging, never around them.** The verdict lands in `delivery-audit.json` beside the tracker.

Then:
- All posts must be FINAL status (or --force to skip unapproved)
  **WARNING:** `--force` bypasses ALL approval gates. Use only in emergencies. All force-finalized posts are logged with `force_finalized: true` in status-tracker.json for audit trail — and the delivery audit reports every one of them as a violation the client-facing record must acknowledge.
- All compliance checks passed
- All required approvals obtained per approval-chain.json
- Calendar document assembled

If any posts are not FINAL: "3 posts still pending approval. Finalize anyway with --force, or resolve pending items first."

## Final Folder Structure
```
FINAL/
├── 00-Calendar-Document/
│   └── {brand}-{month}-calendar.json   # delivery manifest; DOCX conversion is a manual step
├── 01-Ready-to-Publish/
│   └── Week-{N}/
│       └── {date}-Post{id}-{title}/
│           └── {platform}/
│               ├── image-{WxH}.png
│               ├── copy.txt
│               └── preview.png
├── 02-Carousels/
├── 03-Video-Production-Kit/
├── 04-Stories-Shorts/
├── 05-Review-Gallery/
├── 06-Publishing-Schedule/
└── 07-Production-Checklist/
```

## Process
1. Verify all approval gates
2. Organize files into folder structure
3. Generate publishing schedule (dates + times + platforms)
4. Generate production checklist (remaining manual tasks)
5. Upload to Google Drive (if connected)
6. Send completion notification via Slack/email
7. Remind the user: once the month has run, ingest its analytics export with
   `/socialforge:ingest-performance` — that is what lets next month's
   `/socialforge:ideate-month` compound measured wins instead of memory
