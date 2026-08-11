# Kling v3.0 Pro (image-to-video)

SocialForge's primary video path on WaveSpeed. Highest fidelity in the V3.0
family, takes a start frame and optionally an end frame, and can generate
synchronised audio.

| Field | Value |
|---|---|
| Model ID | `kwaivgi/kling-v3.0-pro/image-to-video` |
| Provider | wavespeed |
| Method | **Async** — submit returns a prediction id, poll until terminal |
| Type | video |
| Auth | `WAVESPEED_API_KEY` via `Authorization: Bearer` |
| Docs | https://wavespeed.ai/models/kwaivgi/kling-v3.0-pro/image-to-video |
| Reference images | one required start frame; optional `end_image` |
| Duration | **3–15 seconds**, default 5 |
| Verified | 2026-08-11 |

## Endpoint

```
POST https://api.wavespeed.ai/api/v3/kwaivgi/kling-v3.0-pro/image-to-video
```

## Request

| Field | Type | Notes |
|---|---|---|
| `image` | URL | **Required.** Must be publicly reachable — a local path will not work |
| `prompt` | string | Motion description |
| `duration` | int | 3–15, default 5 |
| `negative_prompt` | string | optional |
| `cfg_scale` | float | prompt adherence, default 0.5 |
| `end_image` | URL | optional end frame for a guided transition |
| `sound` | bool | synchronised audio, default off — **see cost note** |
| `shot_type` | string | `intelligent` or `customize` |
| `multi_prompt` | string | additional prompts across a transition |
| `element_list` | array | elements to hold consistent |

`image` needing a public URL is why `scripts/generate_video.py` calls
`_ws_client.upload(first_frame_path)` first — the upload returns the URL the API
will actually accept. Skipping that step is the usual cause of a rejected job.

## Cost note — `sound` is not free

Enabling `sound` bills at **1.5× the base per-second rate**. SocialForge passes
`sound` straight through, so a quote taken without it understates a 10-second
clip by about half a dollar, and a 28-post month by roughly fifteen.

Quote it explicitly:

```bash
python3 scripts/price_book.py --action quote \
  --model kling-v3.0-pro --provider wavespeed --units 10 \
  --multiplier 1.5 --multiplier-reason "sound=true"
```

The multiplier is a provider fact and moves; look it up on the model page rather
than trusting this line.

## Response

Asynchronous. Submit returns a prediction id; poll the result endpoint roughly
every 2 seconds until a terminal status appears, then download the video URL
immediately — result links are temporary artifacts, not storage.

The `wavespeed` SDK's `run()` wraps submit-and-poll; SocialForge uses it with a
300-second timeout and a 3-second poll interval.

## Failure modes

- **Local path passed as `image`** — rejected. Upload first.
- **Duration outside 3–15** — SocialForge clamps with `min(max(duration, 3), 15)`
  before sending, so an out-of-range brief silently becomes an in-range clip.
  If a brief asks for 30 seconds, say so rather than shipping 15.
- **Poll timeout** — the job may still be running server-side. Re-submitting
  bills a second time for the same clip.

## Related models on the same provider

- `kwaivgi/kling-v3.0-std/image-to-video` — cheaper standard tier
- `kwaivgi/kling-v3.0-4k/image-to-video` — 4K variant
- `kwaivgi/kling-video-o3-pro/image-to-video` — a different architecture (MVL),
  aimed at reference-heavy work and subject-identity consistency rather than
  prompt-driven cinematics. Materially more expensive.

Compare before routing a month through any of them:
`price_book.py --action compare --model kling-v3.0-pro`
