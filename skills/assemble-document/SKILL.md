---
name: assemble-document
description: Assemble the final calendar delivery document (DOCX) with all posts, images, and copy.
argument-hint: "[--brand <name>] [--format docx|pdf]"
effort: high
user-invocable: true
disable-model-invocation: true
---

# /sf:assemble-document — Document Assembler

Create the final delivery document containing the complete monthly calendar with images, copy, and metadata.

## Document Structure
1. Cover page (brand name, month, prepared by)
2. Table of contents
3. Monthly overview (post count, platform breakdown, tier distribution)
4. Weekly sections:
   - For each post: date, platform, image preview, copy text, hashtags, CTA, creative mode used, quality score
5. Appendix A: Publishing schedule (dates + times + platforms)
6. Appendix B: Production notes (asset gaps, compliance flags, revision history)
7. Appendix C: Cost report

## Process
1. Load all approved posts from status-tracker.json
2. Load images, copy, and metadata for each
3. Build DOCX using document-template structure
4. Embed images at appropriate resolution
5. Save to `output/{brand}/{month}/FINAL/00-Calendar-Document/`

## Timeout & Fallback
- Document assembly: 2-minute timeout for 30 posts. If images are too large, compress to 72 DPI.
