---
description: Swap the brand asset used for a post's image composition
argument-hint: "<post-id> [--asset <asset-id>] [--browse]"
---

# Swap Asset

Replace the matched brand asset for a post with a different one from the library.

## Process
1. Show current asset match for the post
2. If --browse: show top 10 alternatives from asset-index.json with scores
3. If --asset: use the specified asset ID
4. Re-assign creative mode based on new asset
5. Re-run compose-creative for this post with new asset
6. Show result for approval
