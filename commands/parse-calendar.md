---
description: Parse monthly content calendars from DOCX, XLSX, Notion, or text into structured calendar-data.json
argument-hint: "[file-path | notion-url | --paste]"
---

# Parse Calendar

Import and parse a monthly social media calendar into SocialForge format.

## Process
1. Accept calendar from file upload (DOCX, XLSX), Notion URL, or pasted text
2. Extract all posts with dates, platforms, tiers, content types, and briefs
3. Validate required fields, flag issues
4. Save as calendar-data.json in the month output folder
5. Show summary: post count, platform breakdown, tier breakdown, any issues

## Supported Formats
- DOCX — Agency handoff documents
- XLSX — Structured spreadsheets
- Notion — Page URL (requires Notion connector)
- Text — Paste directly or provide .txt file path
