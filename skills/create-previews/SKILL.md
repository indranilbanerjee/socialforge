---
name: create-previews
description: "Create platform previews: post mockups on LinkedIn, Instagram, X and TikTok before publishing. \"show how this will look\""
argument-hint: "[--post <id>] [--all] [--platform <name>]"
effort: medium
user-invocable: true
disable-model-invocation: false
---

# /socialforge:create-previews — Preview Generator

Generate realistic platform mockups showing exactly how each post will appear when published.

## Execution gate

Rendering writes preview images under `production/previews/`. State the scope (posts x platforms, destination) and proceed only on an explicit `yes`; any other reply cancels with nothing written.

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
