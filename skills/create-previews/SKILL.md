---
name: create-previews
description: "Generate platform-accurate mockup previews — the post as it will actually render on LinkedIn, Instagram, X, TikTok — before anything is published. Triggers on \"/create-previews\", \"preview this post\", \"how will it look\", \"platform mockup\", \"show it on Instagram\", \"preview batch\", or after creative and copy exist and stakeholders need to see the assembled post in context before approval."
argument-hint: "[--post <id>] [--all] [--platform <name>]"
effort: medium
user-invocable: true
disable-model-invocation: true
---

# /socialforge:create-previews — Preview Generator

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
