---
description: Generate preview mockups for all posts in batch
argument-hint: "[--brand <name>] [--platform <name>]"
---

# Preview Batch

Generate platform mockup previews for all generated posts.

## Process
1. Find all posts with generated images
2. For each post x each platform: render preview via render_preview.py
3. Save all previews to production/previews/
4. Show progress: [12/28] Rendering P12 for LinkedIn...
5. Summary: "28 posts x 3 platforms = 84 previews generated"
