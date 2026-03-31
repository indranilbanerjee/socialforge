# Status Tracker Schema Reference

JSON schema for `status-tracker.json` — tracks every post through the 8-phase pipeline with full revision history.

## Location

```
~/.claude-marketing/<brand-slug>/status-tracker.json
```

## Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `pipeline_status` | object | Phase completion status (see below) |
| `posts` | object | Per-post tracking keyed by `post_id` (see below) |
| `approval_summary` | object | Aggregate approval statistics (see below) |

## `pipeline_status`

Tracks completion of the 8 pipeline phases:

```json
{
  "pipeline_status": {
    "phase_1_brand_context": "complete",
    "phase_2_calendar": "complete",
    "phase_3_copy": "complete",
    "phase_4_visuals": "in_progress",
    "phase_5_review": "pending",
    "phase_6_compliance": "pending",
    "phase_7_gallery": "pending",
    "phase_8_export": "pending"
  }
}
```

Values: `"pending"`, `"in_progress"`, `"complete"`, `"blocked"`.

## Post Status State Machine

```
planned → drafting → copy_review → visual_production → visual_review
    → compliance_check → approved → gallery_ready → exported
                                ↘ revision_requested → drafting
```

- `revision_requested` loops back to `drafting` with revision notes.
- `blocked` can occur at any stage (compliance failure, missing asset, etc.).

## Post Object

Each post in the `posts` object is keyed by `post_id`:

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Current state (see state machine above) |
| `tier` | string | `"HERO"`, `"HUB"`, or `"HYGIENE"` |
| `platforms` | array | Target platforms |
| `image_variants` | array | Generated image variant paths |
| `copy_selected` | string | The approved copy variant identifier |
| `review` | object | Review status per tier (see below) |
| `revision_history` | array | Revision records (see below) |
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

| Field | Type | Description |
|-------|------|-------------|
| `version` | number | Revision number (1, 2, 3...) |
| `changed_by` | string | Who requested the change |
| `changes` | string | Description of what changed |
| `timestamp` | string | ISO 8601 timestamp |
| `previous_copy` | string | Snapshot of copy before revision |

## `approval_summary`

| Field | Type | Description |
|-------|------|-------------|
| `total_posts` | number | Total posts in pipeline |
| `approved` | number | Posts fully approved |
| `pending_review` | number | Posts awaiting review |
| `revision_requested` | number | Posts sent back for changes |
| `blocked` | number | Posts blocked by compliance or other issues |
| `exported` | number | Posts exported and ready to publish |

## Example

```json
{
  "pipeline_status": {
    "phase_1_brand_context": "complete",
    "phase_2_calendar": "complete",
    "phase_3_copy": "in_progress"
  },
  "posts": {
    "post-2026-04-07-lin-001": {
      "status": "copy_review",
      "tier": "HUB",
      "platforms": ["linkedin", "x"],
      "image_variants": [],
      "copy_selected": null,
      "review": {
        "social-lead": { "status": "pending" }
      },
      "revision_history": [],
      "flags": [],
      "finalized": false
    }
  },
  "approval_summary": {
    "total_posts": 20,
    "approved": 0,
    "pending_review": 1,
    "revision_requested": 0,
    "blocked": 0,
    "exported": 0
  }
}
```
