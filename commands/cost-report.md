---
description: Show API cost breakdown for the current month's production
argument-hint: "--brand <name> --month <YYYY-MM>"
---

# Cost Report

Display the API cost breakdown from cost-log.json.

## Contract

Both `--brand` and `--month` are required. The skill runs:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cost_tracker.py" --action report --brand <name> --month <YYYY-MM>
```

The script returns JSON — `total_cost_usd`, `total_api_calls`, `by_operation`, and `by_post` (top 10). Render it for the user as below.

## Output
```
Cost Report — AcmeCorp / April 2026
  Total: $3.47 across 96 API calls

  By Operation:
    gemini_image_generation: $1.80
    gemini_image_edit: $0.75
    gemini_vision_analysis: $0.47
    <operation>: $<amount>
    carousel_render: $0.00 (local Playwright, free)

  By Post (top 10):
    P01: $0.85
    P07: $0.45
    ...
```

Operation names come straight from the cost log. Only operations with a built-in estimate are priced automatically (vision analysis, image generation, image edit, fal.ai, Replicate; local compositing, background removal, and carousel rendering are $0.00). Video generation through WaveSpeed has no built-in estimate — log its actual cost with `--action log --cost <usd>`.
