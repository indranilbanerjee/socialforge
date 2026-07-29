---
name: assemble-document
description: Assemble the final calendar delivery manifest (structured JSON) with all posts, copy, and metadata.
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

## Producing a DOCX (manual/optional)

No DOCX is generated automatically — the script reports `docx package not available` and emits JSON only. To produce a Word document, hand the manifest JSON to a document tool of your choice, or lay it out against `assets/document-template/`. Image previews are referenced by path in the manifest rather than embedded.

## Timeout & Fallback
- Manifest assembly: 2-minute timeout for 30 posts.
