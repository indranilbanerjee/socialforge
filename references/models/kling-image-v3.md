# Kling Image v3 (text-to-image)

SocialForge's image fallback when Vertex is unavailable or refuses a job. Handles
aspect ratios natively, which matters because platform crops are the whole game
in social creative.

| Field | Value |
|---|---|
| Model ID | `kwaivgi/kling-image-v3/text-to-image` |
| Provider | wavespeed |
| Method | **Async** — the SDK's `run()` submits and polls for you |
| Type | image |
| Auth | `WAVESPEED_API_KEY` via `Authorization: Bearer` |
| Docs | https://wavespeed.ai/models |
| Reference images | not used on this path — the text-to-image variant takes prompt only |
| Verified | 2026-08-11 (against `scripts/generate_image.py`) |

No price here. `price_book.py --action quote --model kling-image-v3 --provider wavespeed`.

## Call

The `wavespeed` SDK wraps submit-and-poll in one call:

```python
from wavespeed import Client as WsClient
client = WsClient(api_key=ws_key)
output = client.run(
    "kwaivgi/kling-image-v3/text-to-image",
    {"prompt": prompt, "aspect_ratio": aspect_ratio},
    timeout=120.0,
    poll_interval=3.0,
)
```

## Response

`output["outputs"]` is a list; the image URL is `outputs[0]`.

**Download it immediately.** The returned URL is a temporary artifact link, not
storage — persist the bytes, never the link.

```python
img_url = output.get("outputs", [None])[0]
urllib.request.urlretrieve(img_url, output_path)
```

## Failure modes

- **No key** → `get_wavespeed_key()` raises `ImportError` or returns nothing, and
  the caller falls through to the next provider. A missing key is not an error
  worth surfacing until every provider has been tried.
- **Timeout** — the 120s ceiling is the SDK's, not the model's. A busy queue can
  exceed it; that is a retry, not a failure of the prompt.
- **Empty `outputs`** — a completed job with no asset. Treat as failure and fall
  through; do not retry the same payload, it will return empty again.

## Notes

`aspect_ratio` is a string like `"1:1"`, `"4:5"`, `"9:16"` — not width/height.
Match it to the target platform spec in `resize_image.py` before generating,
rather than generating square and cropping, which throws away pixels you paid
for.
