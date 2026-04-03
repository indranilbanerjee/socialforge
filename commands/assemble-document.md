---
description: Assemble the final delivery document (DOCX) with all approved posts, images, and copy
argument-hint: "[--brand <name>] [--month <YYYY-MM>]"
---

# Assemble Document

Package all approved posts into a professional delivery document.

## Process
1. Load all approved posts from status-tracker.json
2. Collect final images, videos, and copy from post folders
3. Generate DOCX with branded formatting
4. Include: post calendar view, individual post pages with visuals and copy, platform specs
5. Save to FINAL/ folder

## Prerequisites
- Posts must be approved (status: APPROVED_INTERNAL or higher)
- Run after /sf:finalize or as part of the full pipeline
