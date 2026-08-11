# Gemini Flash Image ("Nano Banana")

SocialForge's **primary** image path. Fast, strong with reference images, and the
default every generation starts from unless a brief overrides it.

| Field | Value |
|---|---|
| Model ID | resolved from the registry alias `latest-image-balanced-google` (currently `gemini-3.1-flash-image`) |
| Provider | vertex — or AI Studio, depending on which credential is configured |
| Method | **Sync** — the image comes back in the first response |
| Type | image |
| Auth | application default credentials (Vertex) or an API key (AI Studio); **not** a bearer header |
| Reference images | yes — this is the path to use when brand assets must be honoured |
| Verified | 2026-08-11 |

## The one model here that is synchronous

Every other wired generator is async. This one is not: `generate_content` returns
the image inline, so there is nothing to poll. Writing a polling loop around it
waits forever for a result that already arrived — the exact failure the recipe
system exists to prevent.

## Two backends, one code path

`create_client()` returns a `backend` alongside the client, and the result is
tagged `gemini-{backend}`. Vertex and AI Studio take different credentials but
the same call, so a working prompt does not prove which one is configured.
Read the `provider` field of the result when debugging.

## Request

```python
response = client.models.generate_content(
    model=model,
    contents=parts,                                   # prompt + any reference images
    config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
)
```

`response_modalities=["IMAGE"]` is load-bearing. Without it the model is free to
answer with text, which is exactly what the failure path below reports.

## Response

Walk `response.parts` and take the first part with `inline_data`. The payload may
arrive as raw bytes or as a base64 string, so both are handled:

```python
img_bytes = (base64.b64decode(part.inline_data.data)
             if isinstance(part.inline_data.data, str)
             else part.inline_data.data)
Path(output_path).write_bytes(img_bytes)
```

## Failure modes

- **No image in the response** — the model replied in text instead, usually a
  refusal or a prompt it read as a question. SocialForge returns
  `{"status": "FAILED", "error": "No image in response", "text_response": ...}`;
  the text is the actual explanation, so surface it rather than retrying blind.
- **Falls through to WaveSpeed then Higgsfield** on exception, with
  `fallback_from` recorded on the result. If output quality suddenly changes,
  check that field before suspecting the prompt.
- **Retired model id** — the registry resolves the alias, so a hardcoded id in a
  brief can outlive the model. Prefer the alias.

## Naming

The same model appears as `gemini-3.1-flash-image` (Google), `fal-ai/nano-banana`
(fal.ai) and "Nano Banana 2" (WaveSpeed). `price_book.normalise()` folds all
three to one key so a cross-provider price comparison is possible at all.
