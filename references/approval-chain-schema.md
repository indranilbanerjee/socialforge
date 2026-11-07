# Approval Chain Schema Reference

JSON schema for `approval-chain.json` — defines who reviews content and when reminders and escalations go out.

## Location

```
${CLAUDE_PLUGIN_DATA}/socialforge/brands/<brand-slug>/approval-chain.json
```

When `CLAUDE_PLUGIN_DATA` is unset, the scripts fall back to:

```
~/socialforge-workspace/brands/<brand-slug>/approval-chain.json
```

## Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tiers` | object | Yes | Approval rules per content tier (HERO, HUB, HYGIENE) |
| `special_rules` | object | No | Override rules for specific content types |
| `escalation_rules` | object | No | What happens when reviews stall |
| `scheduled_reminders` | object | No | Automated nudge configuration |

## `tiers`

Each tier key (`HERO`, `HUB`, `HYGIENE`) contains:

| Sub-field | Type | Description |
|-----------|------|-------------|
| `reviewers` | array | List of reviewer roles (e.g., `["social-lead", "brand-manager"]`) |
| `client_approval` | boolean | Whether client must sign off |
| `ceo_approval` | boolean | Whether CEO/founder must sign off |
| `min_reviewers` | number | Minimum approvals needed before proceeding |
| `max_review_hours` | number | Hours before escalation triggers |

```json
{
  "tiers": {
    "HERO": {
      "reviewers": ["social-lead", "brand-manager", "creative-director"],
      "client_approval": true,
      "ceo_approval": true,
      "min_reviewers": 2,
      "max_review_hours": 48
    },
    "HUB": {
      "reviewers": ["social-lead", "brand-manager"],
      "client_approval": true,
      "ceo_approval": false,
      "min_reviewers": 1,
      "max_review_hours": 24
    },
    "HYGIENE": {
      "reviewers": ["social-lead"],
      "client_approval": false,
      "ceo_approval": false,
      "min_reviewers": 1,
      "max_review_hours": 12
    }
  }
}
```

## `special_rules`

Override tier defaults for specific content categories:

| Sub-field | Type | Description |
|-----------|------|-------------|
| `founder` | object | Posts quoting or featuring the founder |
| `case_study` | object | Customer case study content |
| `data_claims` | object | Posts containing statistics or data claims |

Each contains the same fields as a tier entry. Example:

```json
{
  "special_rules": {
    "founder": {
      "ceo_approval": true,
      "reviewers": ["brand-manager", "creative-director"]
    },
    "case_study": {
      "client_approval": true,
      "reviewers": ["social-lead", "legal"]
    },
    "data_claims": {
      "reviewers": ["social-lead", "data-analyst"],
      "min_reviewers": 2
    }
  }
}
```

## `escalation_rules`

| Sub-field | Type | Description |
|-----------|------|-------------|
| `reminder_after_hours` | number | Hours before first reminder is sent |
| `escalate_after_hours` | number | Hours before escalating to next reviewer |

### No approval-free path

Auto-publish is not supported. No post is finalized, delivered or published because a reviewer did not answer: an expired escalation period sends a reminder or escalates, and every post still needs its approvals before `/socialforge:finalize`, which the user runs and confirms with `yes`. An `auto_publish` block in an existing approval-chain.json is ignored.

```json
{
  "escalation_rules": {
    "reminder_after_hours": 4,
    "escalate_after_hours": 12
  }
}
```

## `scheduled_reminders`

| Sub-field | Type | Description |
|-----------|------|-------------|
| `enabled` | boolean | Whether to send scheduled reminder summaries |
| `frequency` | string | `"daily"` or `"twice_daily"` |
| `time` | string | Time in HH:MM format (24h) |
| `channel` | string | Delivery channel: `"slack"`, `"email"` |
| `include_overdue` | boolean | Highlight overdue items in reminder |

```json
{
  "scheduled_reminders": {
    "enabled": true,
    "frequency": "daily",
    "time": "09:00",
    "channel": "slack",
    "include_overdue": true
  }
}
```

## Behavior Notes

- Special rules merge with (not replace) the tier defaults.
- If `min_reviewers` exceeds the number of `reviewers`, all reviewers must approve.
- No tier finalizes without its approvals: HERO, HUB and HYGIENE all wait for sign-off, and an `auto_publish` block is ignored.
- Missing `approval-chain.json` defaults to single-reviewer approval on all tiers.
