---
name: assemble-document
description: "Assemble the final month-end delivery manifest — every approved post with its copy, creative files, platform variants, and metadata in one structured JSON handoff. Triggers on \"/assemble-document\", \"assemble the delivery\", \"final document\", \"package the month\", \"client handoff file\", \"delivery manifest\", or when all posts are approved and the month needs packaging. Runs after finalize-month; the output is what the client receives."
argument-hint: "[--brand <name>] [--month <YYYY-MM>]"
effort: high
user-invocable: true
disable-model-invocation: true
---

# /socialforge:assemble-document — Document Assembler

Create the final delivery manifest — a structured JSON file describing the complete monthly calendar, its posts, copy, and metadata. The manifest is the deliverable this skill produces; a formatted DOCX is a manual/optional step downstream (see below).

## Manifest Structure

`assemble_docx.js` emits these sections into the JSON manifest:

1. Title block (brand name, month, generation timestamp)
2. Monthly overview (post count, platform breakdown, tier distribution, content-type distribution)
3. Weekly sections:
   - For each post: post id, date, title, tier, platforms, content type, copy option A, visual direction, creative mode, status
4. Publishing schedule (date, day of week, post id, title, platforms)

## Process
1. Load calendar-data.json and status-tracker.json for the brand + month
2. Group posts by week and merge in each post's tracked status and creative mode
3. Build the manifest structure
4. Save to `${CLAUDE_PLUGIN_DATA}/socialforge/output/{brand}/{month}/FINAL/00-Calendar-Document/{brand}-{month}-calendar.json` (falls back to `~/socialforge-workspace/output/...` when `${CLAUDE_PLUGIN_DATA}` is unset)

## AI-assistance note (delivery manifest)

Read `ai_disclosure` from brand-config.json (missing block = `{"mode": "claude-surfaces", "text": null}`) and decide whether the manifest carries the AI-assistance note:

1. Run `python ${CLAUDE_PLUGIN_ROOT}/scripts/detect_surface.py --mode {mode}` — its `disclosure_applies` field IS the decision. Fail-safe: an `uncertain` surface applies the note in claude-surfaces mode; skipping requires an AFFIRMATIVE non-Claude fingerprint. Never override the script's answer.
2. When it applies, add to the manifest metadata: `"ai_assistance_note": "Creative produced with AI assistance under human review and brand approval gates."` (or the brand's custom `text` verbatim). The default wording is vendor-neutral and claims only the review this pipeline actually performs — every post passed the approval chain.
3. Record the decision either way: `"disclosure": {"applied": true|false, "mode": ..., "surface": ...}` in the manifest — an unapplied note is a recorded choice, not an omission.
4. Remind the user at handoff: platform-native AI-content labels (Instagram/TikTok/YouTube toggles) are the right place for per-post disclosure — flag which posts used AI generation so whoever publishes can set them.

## Producing a DOCX (manual/optional)

No DOCX is generated automatically — the script reports `docx package not available` and emits JSON only. To produce a Word document, hand the manifest JSON to a document tool of your choice, or lay it out against `assets/document-template/`. Image previews are referenced by path in the manifest rather than embedded.

## Timeout & Fallback
- Manifest assembly: 2-minute timeout for 30 posts.
