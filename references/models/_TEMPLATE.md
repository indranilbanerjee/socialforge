# <Model display name>

One line on what this model is best at and when to reach for it over the others.

| Field | Value |
|---|---|
| Model ID | `<exact id the API expects>` |
| Provider | wavespeed / fal / kie / vertex / higgsfield |
| Method | **Sync** (result in the first response) or **Async** (submit, poll, download) |
| Type | image / video |
| Auth | `.env` key name + header shape, e.g. `WAVESPEED_API_KEY` via `Authorization: Bearer` |
| Docs | <link to the provider's page for this exact model> |
| Reference images | how many it accepts, and in what form (URL / base64 / upload id) |
| Max duration | video only — the hard ceiling, e.g. 8s |
| Verified | YYYY-MM-DD you last confirmed this against the provider's docs |

No price field. Prices live in `price_book.py`, looked up live — see
`references/models/README.md`.

## Endpoint

```
POST https://...
```

## Request

```json
{
  "prompt": "...",
  "...": "the exact body from the provider's docs, with the aspect-ratio, resolution and reference-image fields named as that provider names them"
}
```

## Response

**Sync:** where the asset actually is in the reply — a base64 field, or a URL to
download. Name the exact JSON path.

**Async:** the status endpoint, the field that signals completion, the polling
interval the provider recommends, and where the file URL appears once done.
Note how long that URL stays valid — many expire in hours, so download
immediately rather than storing the link.

## Failure modes

What this model rejects and how it says so: content restrictions, max input
size, rate limits, and any error that looks like success (an HTTP 200 carrying an
error body is worth calling out explicitly).

## Notes

Anything that surprised you. Quirks belong here rather than in a commit message
nobody will find again.
