---
name: create-previews
description: "Create a preview card per platform: post copy, image and badge, to check copy and crop. \"show how this will look\""
argument-hint: "[--post <id>] [--all] [--platform <name>]"
effort: medium
user-invocable: true
disable-model-invocation: false
---

# /socialforge:create-previews — Preview Generator

Generate a preview card per platform (post copy, image, platform badge) to check copy, line breaks and crop before publishing. The card is one built-in layout with the platform named; it is not a replica of the platform's feed.

## Execution gate

Rendering writes preview images under `production/previews/`. State the scope (posts x platforms, destination) and proceed only on an explicit `yes`; any other reply cancels with nothing written.

## Process
1. For each post × each platform:
   - Load the generated/composed image
   - Load the adapted copy
   - Use the built-in card (or `assets/preview-templates/<platform>.html` if you supplied one; none ship)
   - Inject: brand name and handle, platform badge, image and the post copy (hashtags included in the copy passed in)
   - Render via Playwright → PNG preview
2. Save to `production/previews/post-{id}-{platform}-preview.png`

## Layouts
One built-in card serves every platform. To get a platform-specific layout, put `<platform>.html` in `assets/preview-templates/` using the placeholders `{{name}}`, `{{handle}}`, `{{platform}}`, `{{image_uri}}` and `{{copy}}`. No templates ship.

## Timeout & Fallback
- Per preview: 10-second timeout. If Playwright hangs, save raw image + copy as fallback.
