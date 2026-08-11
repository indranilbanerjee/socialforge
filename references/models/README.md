# Model recipes

One file per model, holding everything needed to call it: endpoint, auth shape,
request body, response handling, and — the field that causes the most wasted
time — whether the call is **sync or async**.

## Why these exist

Until now, every provider's call shape lived inside `generate_image.py` and
`generate_video.py` as Python. Adding a model meant editing code, running the
suite and cutting a release. A model shipped on 2026-07-31, one day after the
registry's last review, and could not be used until someone changed a script.

A recipe is markdown. Adding a model is writing one file.

## What a recipe is not

It is **not** a price list. Prices belong to `price_book.py`, which only holds
figures that were looked up live and stamped with the URL they came from. A price
written into a recipe is stale the moment a provider changes it, and worse, it
looks authoritative. If you find a price in a recipe file, delete it.

Capability belongs here. Cost does not.

## The template

Copy `_TEMPLATE.md`, fill it in from the provider's own docs, name it after the
model. Ten minutes, once per model.

## The one field people get wrong

`Method: Sync` or `Method: Async`.

Sync returns the finished result in the first response. Async returns a task id
you must poll until it reports done, then download from a URL that often expires
within hours. Guessing wrong is the single most common reason a first attempt
appears to hang forever — the code is waiting for a result that already arrived,
or reading a body that only contains a job id.

Write it down, per model, from the docs. Do not infer it from a sibling model:
providers mix both within one catalogue.

## Auth shapes differ per provider

Three providers, three shapes. Get it right once per provider and every model on
that provider works:

| Provider | Shape |
|---|---|
| WaveSpeed | `Authorization: Bearer {WAVESPEED_API_KEY}` |
| Kie AI | `Authorization: Bearer {KIE_API_KEY}` |
| fal.ai | `Authorization: Key {FAL_KEY}` — the word is `Key`, not `Bearer` |
| Vertex AI | Application default credentials, not a header |

`price_book.py --action providers` prints this same map at runtime.

## Keeping them honest

A recipe describes a model that exists today. When a provider retires or renames
one, the recipe is wrong and should be deleted or corrected in the same change —
not left behind "just in case". A stale recipe is worse than a missing one,
because the agent will try to use it.
