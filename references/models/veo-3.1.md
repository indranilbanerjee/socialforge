# Veo 3.1

SocialForge's primary video path. Strongest motion quality of the wired options,
and the most expensive per second — quote before running, always.

| Field | Value |
|---|---|
| Model ID | `veo-3.1-generate-preview` (see `DEFAULT_VEO_MODEL`) |
| Provider | vertex |
| Method | **Async** — returns a long-running operation you poll |
| Type | video |
| Auth | Application default credentials, **not** a header |
| Docs | https://cloud.google.com/vertex-ai/generative-ai/docs/video/generate-videos |
| Reference images | one optional start frame (image-to-video) |
| Max duration | **8 seconds, hard** — longer requests are clamped, not rejected |
| Verified | 2026-08-11 (against `scripts/generate_video.py`) |

No price here. Video is billed per second and the rate has moved more than once
this year: `price_book.py --action quote --model veo-3.1 --provider vertex --units <seconds>`.

## Call

```python
gen_config = types.GenerateVideosConfig(
    number_of_videos=1,
    duration_seconds=min(duration, 8),   # the clamp is load-bearing
    aspect_ratio=aspect_ratio,
)
operation = client.models.generate_videos(model=model, prompt=prompt, config=gen_config)
```

Pass a start frame for image-to-video; omit it for text-to-video. Both go through
the same operation shape.

## Response — the async part people get wrong

`generate_videos` returns an **operation, not a video**. Reading its body
immediately gets you a job handle and nothing else.

```python
while not operation.done and (time.time() - start) < timeout:
    time.sleep(poll_interval)
    operation = client.operations.get(operation)   # re-fetch; the old object never changes

if operation.result and operation.result.generated_videos:
    video = operation.result.generated_videos[0]
```

Two traps in that loop:

1. `client.operations.get(operation)` must be **reassigned**. The original object
   is a snapshot and its `.done` will stay `False` forever if you poll it in
   place — which looks exactly like a model that hangs.
2. `operation.done` being true does not guarantee `operation.result` has videos.
   A completed operation with an empty result is a real outcome (usually a
   content refusal). Check both before indexing.

## Failure modes

- **Duration over 8s** — silently clamped. If a brief asks for a 15-second hero
  clip, this model cannot deliver it in one call; do not promise the client 15
  seconds and quietly ship 8.
- **Timeout with `done == False`** — the job may still complete server-side. That
  is a poll timeout, not a generation failure, and re-submitting bills twice.
- **Content refusal** — arrives as a completed operation with no generated
  videos, not as an exception.

## Notes

Veo 3.1 is the current generation; `veo-2.0`, `veo-3.0` and `veo-3.0-fast` were
all retired on 2026-06-30. A "model not found" here almost always means a retired
id survived somewhere in config — check `model_registry.json` for a
`replacement_id` rather than guessing a new string.

A faster, cheaper Veo 3.1 variant exists on at least one other provider. Compare
before routing a whole month through this one:
`price_book.py --action compare --model veo-3.1`.
