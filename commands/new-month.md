---
description: Start a new month's social media calendar production for a brand
argument-hint: "<brand-name> <YYYY-MM>"
---

# New Month

Start monthly content calendar production. Initializes the output directory, loads brand config, and begins the production pipeline.

## Steps
1. Verify brand profile exists and is complete (pre-flight validation)
2. Create output directory: `~/socialforge-workspace/output/{brand}/{YYYY-MM}/`
3. Initialize status-tracker.json and cost-log.json
4. Ask for calendar source:
   - **DOCX** — Upload a Word document with the monthly calendar
   - **XLSX** — Upload an Excel spreadsheet (one row per post)
   - **Notion** — Provide Notion database URL (requires Notion connector)
   - **Structured text** — Paste or describe the calendar content
5. Parse calendar → `/sf:parse-calendar`
6. Match assets → `/sf:match-assets`
7. Show production plan and estimated API costs
8. Begin creative production on approval

## After Initialization
"Calendar loaded with {N} posts. Ready to generate creative. Run `/sf:generate-all` to produce all posts, or `/sf:generate-post P01` for a single post."
