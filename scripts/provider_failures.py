#!/usr/bin/env python3
"""
provider_failures.py — structured failure records for provider fallback chains.

The generation scripts try providers in order (e.g. Vertex AI -> WaveSpeed ->
HiggsField). Before this module, every rung that couldn't run collapsed its
reason into a bare `return None`, so a fully-failed chain could only say
"All providers failed" — the user had no way to tell a missing API key from a
retired model id from a content-policy rejection, and each of those has a
different fix.

The contract now: a provider function NEVER fails silently. Every abandoned
attempt is recorded with who was tried, at which stage it stopped, a
machine-readable reason, and a human-readable detail. The chain's terminal
FAILED payload carries the full attempt list plus a per-reason next step, so
the error message is itself the diagnosis.

Stages (where in the attempt it stopped):
    credentials       — no key/auth material available
    dependencies      — required SDK/package not importable
    model-resolution  — no current model id could be resolved for the kind
    request           — the provider call itself errored (network/HTTP/SDK)
    response          — provider answered but the answer was unusable
    content-policy    — provider refused the content (e.g. flagged prompt)

Reasons are kebab-case and stable — tests and docs may pin them.
"""

from __future__ import annotations

# What the user should do about each failure reason. Surfaced verbatim in the
# terminal payload — keep these actionable and product-neutral.
NEXT_STEPS = {
    "no-credentials": "Run /socialforge:setup to add credentials for this provider, or skip it.",
    "dependency-missing": "Install the named package (see detail) and retry.",
    "unresolved-model": "Run `python scripts/refresh_models.py` to update the model registry, then retry.",
    "request-error": "Transient or configuration error — check the detail; retry may succeed.",
    "bad-response": "The provider answered without a usable asset — retry, or try another provider.",
    "content-rejected": "The provider refused this prompt — rephrase it; no retry will succeed unchanged.",
    "timeout": "The provider did not finish in time — retry, or try a faster model.",
    "bad-input": "A required input was missing or unusable (see detail) — supply it and retry.",
}


def record(attempts, provider, stage, reason, detail=""):
    """Append one failure record. `attempts` may be None (caller opted out) —
    then this is a no-op, so provider functions can be called standalone."""
    if attempts is None:
        return
    attempts.append({
        "provider": provider,
        "stage": stage,
        "reason": reason,
        "detail": str(detail)[:300],
    })


def failure_payload(attempts, context=""):
    """Terminal FAILED payload for a chain where every provider was exhausted.

    Never returns a bare message: the attempt list IS the error. Each distinct
    reason contributes its next step, deduplicated, in attempt order.
    """
    attempts = attempts or []
    tried = []
    for a in attempts:
        if a["provider"] not in tried:
            tried.append(a["provider"])
    next_steps = []
    for a in attempts:
        step = NEXT_STEPS.get(a["reason"])
        if step and step not in next_steps:
            next_steps.append(step)
    summary = "; ".join(
        f"{a['provider']}: {a['reason']} ({a['stage']})" for a in attempts
    ) or "no providers were attempted"
    error = f"All providers failed — {summary}"
    if context:
        error = f"{context}: {error}"
    return {
        "status": "FAILED",
        "error": error,
        "attempts": attempts,
        "providers_tried": tried,
        "next_steps": next_steps,
        "action_required": True,
    }
