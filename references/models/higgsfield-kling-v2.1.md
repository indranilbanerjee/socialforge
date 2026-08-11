# Higgsfield Kling v2.1 Pro (video) — ⚠ two generations behind

SocialForge's last-resort video fallback, after WaveSpeed Kling and Veo.

| Field | Value |
|---|---|
| Model ID | `kling-video/v2.1/pro/image-to-video` / `.../text-to-video` |
| Provider | higgsfield |
| Method | **Async** — submit returns `request_id`, poll status |
| Type | video |
| Auth | key id + secret pair via `get_higgsfield_auth()` |
| Duration | clamped `min(max(duration, 3), 15)` before send |
| Verified | 2026-08-11 |

## ⚠ The version is stale, deliberately flagged

This path is pinned to **Kling v2.1**. The Kling 3.0 family shipped in
**February 2026**, and an O3 Pro line exists on top of it. This fallback has been
a generation behind for roughly six months.

It has not been bumped here because that is a runtime decision with a cost
attached, not a docs fix:

- The primary WaveSpeed path already runs v3.0 Pro, so this only fires when
  WaveSpeed **and** Veo are both unavailable — rare enough that the quality gap
  usually costs nothing.
- Higgsfield's own catalogue for a v3.0-equivalent path needs checking against
  their current docs before the string is changed. Guessing a model id produces a
  "model not found" at the worst possible moment: when two providers have
  already failed.
- The newer generation is priced differently. Changing the id silently changes
  the bill, and this plugin's whole cost posture is that no price moves without
  being looked up.

**Action when you next touch this:** check Higgsfield's model list, and if a v3.0
path exists, update the id here and in `scripts/generate_video.py`, then record
the new rate in the price book before the first run.

## Endpoint

```
POST https://platform.higgsfield.ai/{model_path}
GET  https://platform.higgsfield.ai/requests/{request_id}/status
```

`model_path` switches on whether a start frame was supplied:

```python
model_path = ("kling-video/v2.1/pro/image-to-video" if image_path
              else "kling-video/v2.1/pro/text-to-video")
```

## Request

The start frame is sent **base64-encoded in the body**, not as an uploaded URL —
the opposite of the WaveSpeed path, which requires a public URL. Two providers,
two conventions, same conceptual input. This is the single most common thing to
get wrong when adding a provider.

`sound` is accepted and passed through. Check whether it carries a surcharge on
this provider before quoting; it does on at least one other.

## Failure modes

- **Non-200 on submit** → returns `None` and the caller reports that every
  provider failed. Since this is last in the chain, its failure is the one the
  user sees, even when the real cause was upstream.
- **Missing credential pair** → same silent fall-through as the Soul path.
