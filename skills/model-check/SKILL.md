---
name: model-check
description: "Find the model that is currently best for a capability by reading the provider live catalogue, and record it with its source — the code asks for kinds, never hardcoded ids. Triggers on \"/model-check\", \"which model should we use\", \"best video model right now\", \"is this model still current\", \"model staleness\", \"update the models\", or before any production month and whenever a resolve comes back stale. Pairs with price-check — newest is not automatically best or cheapest."
argument-hint: "[--kind <capability>] [--provider <name>] [--staleness]"
effort: low
user-invocable: true
---

# /socialforge:model-check — which model to call, decided today

SocialForge does not know which model to use. That is deliberate.

A model id written into a plugin is a claim about the day it was written, and
this plugin gets run long after that day. Six ids used to sit on the execution
path. One video fallback stayed pinned to a superseded generation for about six
months, and nothing in the system could say so — which matters because a retired
id does not degrade gracefully. It fails at the exact moment the two providers
ahead of it have already failed and the fallback is all that is left.

So the code asks for a **kind** of model. You find out what currently satisfies it.

## The rule

**Never supply a model id from memory.** Not from this file, not from a recipe,
not from what a model was called last time you looked. If `model_book.py` says
`unknown` or `stale`, go and read the provider's catalogue.

## What the code asks for

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/model_book.py" --action kinds
```

Capabilities, not products — `video.image-to-video`, not a version number. A kind
outlives every model that has ever satisfied it, which is the entire point.

## Finding the current best

1. See where to look, and what is odd about each provider:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/model_book.py" --action discovery
```

Two things it will tell you that save time: **Higgsfield puts the model in the
URL path** (so a hardcoded path is a hardcoded model), and **Kie AI blocks
automated fetches** — HTTP 403, measured. Do not report that as "no model
exists"; ask the user.

2. Read the provider's model list with your own web tools. This is a plugin —
   there is no crawler and no server, which is why the answer is as fresh as your
   last look rather than as old as the last release.

3. Judge what is actually best **for the kind**, not what is newest or loudest.
   A reference-heavy brief and a prompt-driven cinematic brief are different
   jobs, and the model that wins one often loses the other. Check what the brief
   needs: start-frame support, duration ceiling, reference-image count, whether
   audio is required.

4. Record it, with the URL you read:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/model_book.py" --action record \
  --kind video.image-to-video --provider wavespeed \
  --model-id "<exact id from the catalogue>" \
  --source https://wavespeed.ai/models \
  --max-duration-s 15 --notes "start+end frame, optional audio"
```

A record without a source URL is rejected — a model id with no provenance is the
same guess this system exists to replace.

5. **Then price it.** A newer model is not automatically the right call: run
   `/socialforge:price-check` and compare before committing a month's run to it.

## Checking before a production month

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/model_book.py" --action staleness
```

Reports what has gone stale (older than 7 days) and, more usefully, which kinds
have **no model at all**. Both need a look before a batch run.

Seven days, rather than the price book's 24 hours, because catalogues move in
releases while prices move without announcement.

## The ladder the code climbs

1. **A live discovery** you recorded recently → used.
2. **The shipped registry alias** → used, but always with a warning naming its
   age. This rung exists so a first run works before anything is discovered, not
   so anyone can rely on it.
3. **Nothing** → the generation refuses and falls through to the next provider,
   rather than calling an id that may have been retired.

If you see the rung-2 warning during a real run, that is the signal to do a
discovery pass. It is not an error, but it means the plugin is answering from a
file rather than from the world.

## What this skill will not do

- Supply a model id from memory, from a recipe file, or from this document
- Record a model without the URL it was read from
- Treat "newest" as "best" without checking the brief's actual requirements
- Report a blocked fetch as an absence of models
- Let a generation proceed on an unresolved model
