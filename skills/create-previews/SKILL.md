---
name: create-previews
description: Generate platform mockup previews showing how posts will look on each social platform.
argument-hint: "[--post <id>] [--all] [--platform <name>]"
effort: medium
user-invocable: true
disable-model-invocation: true
---

# /sf:create-previews — Preview Generator

Generate realistic platform mockups showing exactly how each post will appear when published.

## Process
1. For each post × each platform:
   - Load the generated/composed image
   - Load the adapted copy
   - Select platform preview template (assets/preview-templates/)
   - Inject: profile avatar, brand name, handle, image, copy, hashtags, timestamp
   - Render via Playwright → PNG preview
2. Save to `production/previews/post-{id}-{platform}-preview.png`

## Templates
- linkedin-post.html | linkedin-carousel.html
- instagram-feed.html | instagram-story.html
- twitter-post.html | facebook-post.html
- youtube-thumbnail.html

## Timeout & Fallback
- Per preview: 10-second timeout. If Playwright hangs, save raw image + copy as fallback.
