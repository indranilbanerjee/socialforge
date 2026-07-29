---
description: Edit a generated image — adjust background, lighting, colors, or composition
argument-hint: "<post-id> <instruction>"
---

# Edit Image

Send an AI edit instruction to modify a generated image while preserving the core subject.

## Process
1. Load the current image for the post
2. Show image to user with current state
3. Accept edit instruction (e.g., "make the background warmer", "extend the left side")
4. Call the editor with the instruction plus any style references:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/edit_image.py" --image <current> --instruction "<text>" --output <new> [--references <img> ...] [--model <id>]
   ```
   `--image`, `--instruction`, and `--output` are required.
5. Show edited result for approval
6. If approved: replace the variant, re-run quality review
7. If rejected: try different instruction or revert
