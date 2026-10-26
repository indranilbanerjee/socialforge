# Veo 3.1

The Google video option, and **Vertex AI only**. Strong motion quality and the most
expensive per second of the wired options: quote before running, always.

| Field | Value |
|---|---|
| Model ID | `veo-3.1-generate-001` (resolved from the alias `latest-video-google`; see `DEFAULT_VEO_MODEL`) |
| Provider | Vertex AI (Google's current docs call the product "Gemini Enterprise Agent Platform") |
| Not available on | The Gemini API (an AI Studio key). Its Veo 3.1 previews shut down on **2026-10-22**, and `veo-3.1-generate-001` is not in its model list. The Gemini API's video model is Gemini Omni (`gemini-omni-1.1-flash`), which uses a different call (`client.interactions.create`) and is **not wired** in SocialForge |
| Lifecycle | GA since 2025-11-17. Google lists retirement as **2026-11-17 or later**, so check the model-versions page before relying on it after that date |
| Method | **Async**: returns a long-running operation you poll |
| Type | video |
| Auth | A stored service-account profile (`/socialforge:setup`) or `GOOGLE_CLOUD_PROJECT` with application default credentials, **not** a header |
| Docs | https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/veo/3-1-generate |
| Reference images | one optional start frame (image-to-video); no end frame on this rung |
| Durations | **4, 6 or 8 seconds only.** Anything else is rounded up to the next of those, capped at 8, and the result carries `requested_duration` and `duration_note` |
| Aspect ratios | `9:16` and `16:9` |
| Verified | 2026-10-27 against the two Google pages above and Google's model-versions page (updated 2026-10-26) |

No price here. Video is billed per second and the rate has moved more than once
this year: `price_book.py --action quote --model <resolved id> --provider vertex --units <seconds>`.

## When this rung is available

Routing and the quote name Veo only when Vertex AI is set up. A `GEMINI_API_KEY` alone
covers images, not Veo clips: `generate_video.py` lists Veo under `routing.unavailable`
with that reason, never routes to it, and the chain never runs it unquoted. To use Veo,
add a service account with `/socialforge:setup` or set `GOOGLE_CLOUD_PROJECT`.

## Call

```python
gen_config = types.GenerateVideosConfig(
    number_of_videos=1,
    duration_seconds=veo_duration(duration),   # 4, 6 or 8: rounded up, capped at 8
    aspect_ratio=aspect_ratio,
)
operation = client.models.generate_videos(model=model, prompt=prompt, config=gen_config)
```

Pass a start frame (`image=`) for image-to-video; omit it for text-to-video. Both go
through the same operation shape.

The `prompt=` and `image=` arguments of `generate_videos` are deprecated from
google-genai 2.14.0 (2026-07-22) and removed in the next major version; the replacement is
a `GenerateVideosSource(prompt=..., image=...)` passed as `source=`. SocialForge pins
google-genai 1.70.0, so move the call when the pin moves.

## Response: the async part people get wrong

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
   place, which looks exactly like a model that hangs.
2. `operation.done` being true does not guarantee `operation.result` has videos.
   A completed operation with an empty result is a real outcome (usually a
   content refusal). Check both before indexing.

## Failure modes

- **A length Veo does not take** (3 s, 5 s, 7 s, over 8 s) is rounded up to 4, 6 or 8
  and never sent as asked. If a brief asks for a 15-second hero clip, this model cannot
  deliver it in one call; do not promise the client 15 seconds and quietly ship 8.
- **No Vertex AI** (a Gemini API key only, or nothing) records `unavailable-backend` or
  `no-credentials` for the `veo` rung and spends nothing.
- **Timeout with `done == False`**: the job may still complete server-side. That
  is a poll timeout, not a generation failure, and re-submitting bills twice.
- **Content refusal** arrives as a completed operation with no generated
  videos, not as an exception.

## Notes

Veo 3.1 is the current generation; `veo-2.0` and `veo-3.0` were retired on
2026-06-30, and every Veo 3.1 *preview* id shut down on 2026-10-22. A "model not found"
here almost always means a retired id survived somewhere in config: check
`model_registry.json` for a `replacement_id` rather than guessing a new string.

A faster, cheaper Veo 3.1 variant (`veo-3.1-fast-generate-001`) is listed on Vertex AI.
Compare before routing a whole month through this one:
`price_book.py --action compare --model veo-3.1`.
