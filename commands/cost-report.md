---
description: "Report this month's generation cost by provider and post. \"what have we spent so far\""
argument-hint: "--brand <name> --month <YYYY-MM>"
---

# Cost Report

> **Script location.** If your host does not set `${CLAUDE_PLUGIN_ROOT}`, the scripts are in this plugin's `scripts/` folder, next to `skills/`.

Display the API cost breakdown from cost-log.json.

## Contract

Both `--brand` and `--month` are required. The skill runs:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cost_tracker.py" --action report --brand <name> --month <YYYY-MM>
```

The script returns JSON — `total_cost_usd`, `total_api_calls`, `by_operation`, `by_post` (top 10), `unpriced_calls`, `totals_complete` and, when something is unpriced, a `note`. Render it for the user as below, with the figures from the JSON and none from memory.

## Output
```
Cost Report — <brand> / <month>
  Total: <total_cost_usd> across <total_api_calls> API calls

  By Operation:
    <operation>: <amount>
    <local operation>: free (runs locally)

  By Post (top 10):
    <post id>: <amount>
    ...

  Unpriced calls: <unpriced_calls> — every total above is a LOWER BOUND
```

Operation names come straight from the cost log. Local operations (compositing, background removal, resizing, carousel rendering) cost nothing. Paid work carries a figure only when it was logged with the real invoiced amount (`--cost`) or with `--model`, `--provider` and `--units`, which asks `price_book.py` for a live, sourced quote — there is no built-in price table. A call logged without either is `unpriced`: when `unpriced_calls` is above zero (`totals_complete` is false) show the `note`, say the totals are a lower bound, and point to `/socialforge:price-check` to record the missing prices. Unpriced is not free.
