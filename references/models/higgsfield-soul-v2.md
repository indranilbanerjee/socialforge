# Higgsfield Soul v2 (text-to-image)

SocialForge's second image fallback, after WaveSpeed. Aesthetic-led photographic
model with a large preset library — useful when a brief calls for a specific
photographic look rather than a literal scene.

| Field | Value |
|---|---|
| Model ID | `higgsfield/soul-v2/text-to-image` (path segment, not a body field) |
| Provider | higgsfield |
| Method | **Async** — submit returns `request_id`, poll a status endpoint |
| Type | image |
| Auth | **Two credentials**: key id + secret, via `get_higgsfield_auth()` |
| Docs | https://higgsfield.ai/soul-intro |
| Reference images | supports an image reference for style and composition |
| Max output | 2048×1536 |
| Verified | 2026-08-11 |

## Auth is the odd one out

Every other wired provider takes a single key. Higgsfield takes **two** — a key
id and a secret — which `credential_manager.setup_higgsfield(api_key, api_secret)`
stores as a pair and `get_higgsfield_auth()` returns as a tuple. Code that
assumes one value per provider breaks here.

## Endpoint

```
POST https://platform.higgsfield.ai/higgsfield/soul-v2/text-to-image
```

Status:

```
GET https://platform.higgsfield.ai/requests/{request_id}/status
```

## Response — the async part

The submit response carries `request_id`, not an image. Poll the status endpoint
until it reports completion, then read the asset URL from the completed payload
and download it.

SocialForge's implementation treats any non-200 on submit as "this provider is
unavailable" and falls through to the next one, rather than raising. That is
deliberate: an image fallback that throws would abort a whole month's run over
one provider being briefly unreachable.

## Failure modes

- **Missing either half of the credential pair** → falls through silently to the
  next provider. Check `/socialforge:status` if Higgsfield never seems to be used.
- **Completed status with no asset** — a refusal, not a transport error. Do not
  retry the same prompt.
- **Polling forever** — the loop needs its own ceiling; a status endpoint that
  never reaches a terminal state will otherwise hang the whole post.

## Notes

Soul is aesthetics-first. For a brief that needs an exact product or a legible
logo, prefer a compositing path over a text prompt — asking any generative model
to draw a known mark is the reliable way to get a wrong one. Composite the real
asset from the brand library instead.
