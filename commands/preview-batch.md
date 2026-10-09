---
description: "Render preview mockups for all generated posts in one batch. \"preview all the posts\""
argument-hint: "[--brand <name>] [--platform <name>]"
disable-model-invocation: true
---

# Preview Batch

Generate platform mockup previews for all generated posts.

## Process
1. Find all posts with generated images
2. For each post x each platform: render preview via render_preview.py
3. Save all previews to production/previews/
4. Show progress: [12/28] Rendering P12 for LinkedIn...
5. Summary: "28 posts x 3 platforms = 84 previews generated"
