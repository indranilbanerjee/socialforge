---
name: finalize-month
description: Package all approved content into the final delivery folder structure for handoff.
argument-hint: "[--brand <name>] [--force]"
effort: high
user-invocable: true
disable-model-invocation: true
---

# /sf:finalize-month — Month Finalizer

Package all approved posts into the organized delivery folder structure.

## Pre-Finalization Check
- All posts must be FINAL status (or --force to skip unapproved)
  **WARNING:** `--force` bypasses ALL approval gates. Use only in emergencies. All force-finalized posts are logged with `force_finalized: true` in status-tracker.json for audit trail.
- All compliance checks passed
- All required approvals obtained per approval-chain.json
- Calendar document assembled

If any posts are not FINAL: "3 posts still pending approval. Finalize anyway with --force, or resolve pending items first."

## Final Folder Structure
```
FINAL/
├── 00-Calendar-Document/
│   └── {Brand}-{Month}-Calendar.docx
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
