---
name: finalize-month
description: "Finalize the month: package approved content into the delivery folder with copy files and manifest. \"package the month for the client\""
argument-hint: "[--brand <name>] [--force]"
effort: high
user-invocable: true
disable-model-invocation: false
---

# /socialforge:finalize-month — Month Finalizer

> **Script location.** If your host does not set `${CLAUDE_PLUGIN_ROOT}`, the scripts are in this plugin's `scripts/` folder, next to `skills/`.

Package all approved posts into the organized delivery folder structure.

## Execution gate

Packaging copies and renames files, and steps 5-6 can upload to a Drive and send a completion message. After the Step 0 delivery audit passes, show an Execution Summary (posts packaged, any force-finalized posts, destination folder, whether a Drive upload and a notification will happen and to whom) and proceed only on an explicit `yes`; any other reply cancels with nothing written or sent. `--force` still needs the user to have typed it.

## Pre-Finalization Check

**Step 0 — run the delivery audit, before any packaging:**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/delivery_audit.py" --brand {brand} --month {YYYY-MM}
```

It re-derives the month's claims from the ledger and the disk: every status in the vocabulary, revision history landing on the recorded status, no ghost posts the calendar never knew, no gate bypassed on the way to delivery (`force_finalized` is surfaced loudly, not left as a buried flag), every FINAL post's referenced file existing and non-empty, the failure log loadable, and cost totals honest about incompleteness. **Exit 1 means the delivery is claiming something the disk does not support — resolve the findings before packaging, never around them.** The verdict lands in `delivery-audit.json` beside the tracker.

Then:
- All posts must be FINAL status (or --force to skip unapproved)
  **WARNING:** `--force` bypasses ALL approval gates. Use only in emergencies, and **only when the user has typed `--force` (or explicitly said to force-finalize) in this conversation** — never add it on your own initiative, including when this skill was invoked without the user typing its command (hosts such as Codex ignore `disable-model-invocation`). All force-finalized posts are logged with `force_finalized: true` in status-tracker.json for audit trail — and the delivery audit reports every one of them as a violation the client-facing record must acknowledge.
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
8. Only if the user asks: the optional scheduler hand-off below

## Optional: hand off to a scheduler (opt-in)

Finalizing is complete without this. Offer it only when the user asks and a scheduler connector (`~~scheduler`) is already connected; the catalog entry is `postiz` in `.mcp.json.connectors-reference`, and nothing connects by default. SocialForge never schedules or publishes on its own initiative.

1. **Preconditions.** The Step 0 delivery audit passed and every post to be handed off is FINAL. A post that was force-finalized is handed off only after the user re-confirms that post by id.
2. **Show the exact batch before any scheduler call**: per post, the id, the channel/account, the date and time, the copy exactly as it will post, the media file, and which posts used AI generation so the platform-native AI-content label is set where it applies (`references/content-credentials-by-platform.md`).
3. **Explicit approval for exactly that batch.** The approval names the posts and the times. Changing any post, channel or time is a new approval, and "the folder looks good" is not approval to schedule.
4. **Say which action you are asking for.** The Postiz MCP's scheduling tool can schedule, save a draft, or publish immediately ([docs.postiz.com/mcp/introduction](https://docs.postiz.com/mcp/introduction), checked 2026-10-04). Default to a draft or a scheduled post; publish immediately only for a post the user named and said to publish now.
5. **Record what the scheduler returned** (post ids, channel, time) next to `06-Publishing-Schedule/`. If a call fails, report the failure; never retry blind and never say "scheduled" for a post whose call did not return success.

Connector facts, checked 2026-10-04: Postiz is open source and self-hostable (AGPL-3.0, [github.com/gitroomhq/postiz-app](https://github.com/gitroomhq/postiz-app)), connects to Claude through OAuth at the URL in the catalog entry ([postiz.com/claude](https://postiz.com/claude)), and is listed in Anthropic's plugin directory ([claude.com/plugins/postiz](https://claude.com/plugins/postiz)). Postiz's directory connector leaves out its media-generation tools, per Postiz's own page; SocialForge does not use them.
