# Status Tracker Schema Reference

JSON schema for `status-tracker.json` — the per-month production ledger: coarse progress markers, per-post state, and full transition history.

`scripts/status_manager.py` writes and validates this file and is the source of truth for everything below.

## Location

```
${CLAUDE_PLUGIN_DATA}/socialforge/output/<brand-slug>/<month>/status-tracker.json
```

When `CLAUDE_PLUGIN_DATA` is unset, the script falls back to:

```
~/socialforge-workspace/output/<brand-slug>/<month>/status-tracker.json
```

Created by `python3 scripts/status_manager.py --action init-month --brand <slug> --month <YYYY-MM>`.

## Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `brand` | string | Brand slug |
| `month` | string | Target month (`YYYY-MM`) |
| `created_at` | string | ISO 8601 timestamp of `init-month` |
| `last_updated` | string | ISO 8601 timestamp of the most recent status write |
| `pipeline_status` | object | Coarse progress markers (see below) |
| `posts` | object | Per-post tracking keyed by `post_id` (see below) |
| `approval_summary` | object | Aggregate approval counters (see below) |

## `pipeline_status`

A flat set of **storage keys** for coarse progress reporting. These are bookkeeping markers written into the tracker file — they are not a pipeline the runtime enforces, and nothing gates on them. `init-month` writes all eight keys as `"not_started"`.

```json
{
  "pipeline_status": {
    "phase_0_parse": "not_started",
    "phase_1_asset_match": "not_started",
    "phase_2_production": "not_started",
    "phase_3_copy": "not_started",
    "phase_4_previews": "not_started",
    "phase_5_review_gallery": "not_started",
    "phase_6_approval": "not_started",
    "phase_7_finalized": "not_started"
  }
}
```

Values: `"not_started"`, `"in_progress"`, `"complete"`.

## Post Status State Machine

Post states are UPPERCASE. `status_manager.py` enforces the transitions in its `VALID_TRANSITIONS` table — an unlisted transition exits non-zero unless `--force` is passed.

| From | Allowed next states |
|------|---------------------|
| `QUEUED` | `ASSET_MATCHING` |
| `ASSET_MATCHING` | `GENERATING`, `QUEUED` |
| `GENERATING` | `PENDING_REVIEW`, `QUEUED` |
| `PENDING_REVIEW` | `APPROVED_INTERNAL`, `REVISION_REQUESTED`, `REJECTED` |
| `APPROVED_INTERNAL` | `PENDING_CLIENT`, `FINAL` |
| `REVISION_REQUESTED` | `GENERATING` |
| `REJECTED` | `QUEUED` |
| `PENDING_CLIENT` | `APPROVED_CLIENT`, `REVISION_REQ_CLIENT`, `REJECTED_CLIENT` |
| `APPROVED_CLIENT` | `PENDING_CEO`, `FINAL` |
| `REVISION_REQ_CLIENT` | `GENERATING` |
| `REJECTED_CLIENT` | `QUEUED` |
| `PENDING_CEO` | `APPROVED_CEO`, `REJECTED` |
| `APPROVED_CEO` | `FINAL` |
| `FINAL` | — (write-protected, terminal) |

```
QUEUED → ASSET_MATCHING → GENERATING → PENDING_REVIEW → APPROVED_INTERNAL
    → PENDING_CLIENT → APPROVED_CLIENT → PENDING_CEO → APPROVED_CEO → FINAL
                    ↘ REVISION_REQUESTED / REVISION_REQ_CLIENT → GENERATING
                    ↘ REJECTED / REJECTED_CLIENT → QUEUED
```

- New posts are created at `QUEUED`.
- Both revision states loop back to `GENERATING` with notes recorded in `revision_history`.
- `APPROVED_INTERNAL` and `APPROVED_CLIENT` can short-circuit straight to `FINAL` when the brand's approval chain doesn't require the later gates.
- `FINAL` is terminal — no onward transitions.
- Transitioning a post to its current status is always permitted (idempotent no-op transition, still logged).

## Post Object

Each post in the `posts` object is keyed by `post_id`:

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Current UPPERCASE state (see state machine above). Defaults to `"QUEUED"` when the post is first written. |
| `tier` | string | `"HERO"`, `"HUB"`, or `"HYGIENE"` |
| `platforms` | array | Target platforms |
| `image_variants` | array | Generated image variant paths |
| `copy_selected` | string | The approved copy variant identifier |
| `review` | object | Review status per reviewer (see below) |
| `revision_history` | array | Transition records (see below) |
| `flags` | array | Active flags (e.g., `["compliance-warning", "low-quality-score"]`) |
| `finalized` | boolean | Whether the post is locked for export |
| `finalized_at` | string | ISO 8601 timestamp of finalization |

## `review`

Review status follows the approval chain:

| Field | Type | Description |
|-------|------|-------------|
| `reviewer` | string | Reviewer role or name |
| `status` | string | `"pending"`, `"approved"`, `"rejected"`, `"changes_requested"` |
| `comment` | string | Reviewer feedback |
| `reviewed_at` | string | ISO 8601 timestamp |

```json
{
  "review": {
    "social-lead": { "status": "approved", "reviewed_at": "2026-04-03T14:00:00Z" },
    "brand-manager": { "status": "changes_requested", "comment": "Soften the CTA" },
    "client": { "status": "pending" }
  }
}
```

## `revision_history` Entry

Appended by `status_manager.py` on every status write, including forced ones.

| Field | Type | Description |
|-------|------|-------------|
| `from` | string | State before the transition |
| `to` | string | State after the transition |
| `actor` | string | Who made the change (`--actor`, defaults to `"system"`) |
| `timestamp` | string | ISO 8601 timestamp |
| `notes` | string | Free-text reason (`--notes`, defaults to empty) |

```json
{
  "revision_history": [
    { "from": "PENDING_REVIEW", "to": "REVISION_REQUESTED", "actor": "brand-manager", "timestamp": "2026-04-03T14:00:00Z", "notes": "Soften the CTA" }
  ]
}
```

## `approval_summary`

Counters initialized to 0 by `init-month`.

| Field | Type | Description |
|-------|------|-------------|
| `total_posts` | number | Total posts in the month |
| `finalized` | number | Posts at `FINAL` |
| `approved_internal` | number | Posts at `APPROVED_INTERNAL` |
| `pending_client` | number | Posts at `PENDING_CLIENT` |
| `pending_ceo` | number | Posts at `PENDING_CEO` |
| `revision_requested` | number | Posts at `REVISION_REQUESTED` or `REVISION_REQ_CLIENT` |
| `rejected` | number | Posts at `REJECTED` or `REJECTED_CLIENT` |
| `blocked` | number | Posts blocked by compliance or other issues |

`--action get-summary` recomputes a live `status_distribution` from the `posts` object rather than reading these counters.

## Example

```json
{
  "brand": "acme-corp",
  "month": "2026-04",
  "created_at": "2026-04-01T09:00:00Z",
  "last_updated": "2026-04-03T14:00:00Z",
  "pipeline_status": {
    "phase_0_parse": "complete",
    "phase_1_asset_match": "complete",
    "phase_2_production": "in_progress",
    "phase_3_copy": "not_started",
    "phase_4_previews": "not_started",
    "phase_5_review_gallery": "not_started",
    "phase_6_approval": "not_started",
    "phase_7_finalized": "not_started"
  },
  "posts": {
    "post-2026-04-07-lin-001": {
      "status": "PENDING_REVIEW",
      "tier": "HUB",
      "platforms": ["linkedin", "x"],
      "image_variants": [],
      "copy_selected": null,
      "review": {
        "social-lead": { "status": "pending" }
      },
      "revision_history": [
        { "from": "GENERATING", "to": "PENDING_REVIEW", "actor": "system", "timestamp": "2026-04-03T14:00:00Z", "notes": "" }
      ],
      "flags": [],
      "finalized": false
    }
  },
  "approval_summary": {
    "total_posts": 20,
    "finalized": 0,
    "approved_internal": 0,
    "pending_client": 0,
    "pending_ceo": 0,
    "revision_requested": 0,
    "rejected": 0,
    "blocked": 0
  }
}
```
