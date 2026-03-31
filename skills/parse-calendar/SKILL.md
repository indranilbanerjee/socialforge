---
name: parse-calendar
description: Parse monthly content calendars from DOCX, XLSX, Notion, or text into structured calendar-data.json.
argument-hint: "[file-path or Notion URL]"
effort: medium
user-invocable: true
---

# /sf:parse-calendar — Calendar Parser

Parse a monthly social media content calendar into structured JSON that drives the entire production pipeline.

## Supported Formats

| Format | How It Works |
|--------|-------------|
| DOCX | Read tables and structured text from Word documents |
| XLSX | Read rows from Excel spreadsheets (one row per post) |
| Notion | Read from Notion database via MCP (requires Notion connector) |
| Structured text | Parse markdown or plain text with consistent formatting |

## Required Fields Per Post

Every post in the calendar must have (or the system will ask for missing ones):

| Field | Required | Description |
|-------|----------|-------------|
| post_id | Auto-generated | Unique identifier (e.g., P01, P02) |
| date | Yes | Publishing date (YYYY-MM-DD) |
| platform | Yes | Target platform(s) — linkedin, instagram, x, facebook, etc. |
| content_type | Yes | static, carousel, video, story, reel, text_only |
| tier | Yes | HERO, HUB, or HYGIENE |
| topic | Yes | What the post is about |
| caption_brief | Yes | Brief description of the copy direction |
| visual_brief | Recommended | What the image should show |
| hashtags | Optional | Post-specific hashtags (brand hashtags added automatically) |
| cta | Optional | Call-to-action text or link |
| campaign | Optional | Campaign this post belongs to |
| notes | Optional | Special instructions |

## Process

1. **Detect format** — Check file extension or URL pattern
2. **Extract posts** — Parse each post entry from the source
3. **Validate fields** — Check required fields present. For missing fields, ask the user.
4. **Normalize** — Standardize dates, platform names, content types to schema format
5. **Assign post IDs** — Sequential (P01, P02, ...) if not already present
6. **Cross-reference platforms** — Check all platforms exist in brand's platform-config.json
7. **Flag issues** — Duplicate dates, missing briefs, unsupported content types
8. **Save** — Write calendar-data.json to `~/socialforge-workspace/output/{brand}/{YYYY-MM}/`

## Output

```
Calendar parsed: 28 posts for April 2026
  LinkedIn: 12 posts (4 carousels, 6 static, 2 video)
  Instagram: 10 posts (3 carousels, 4 reels, 3 static)
  X: 6 posts (all text+image)

Issues found: 2
  - P14: Missing visual_brief (will need manual input during asset matching)
  - P22: Date falls on Sunday — confirm intentional weekend post?

Calendar saved: ~/socialforge-workspace/output/acme-corp/2026-04/calendar-data.json
```

## After Parsing

Ask: "Would you like to:
- Match assets to posts? (`/sf:match-assets`)
- Review the parsed calendar first? (I'll show the full post list)
- Fix issues? (I'll walk through each flagged item)"

## Timeout & Fallback

- DOCX/XLSX parsing: 30-second timeout. If file is too large, suggest splitting by week.
- Notion: 60-second timeout per database query. If Notion is slow, offer to export and parse locally.
- If format is unrecognized: Ask user to describe the structure, then parse adaptively.
