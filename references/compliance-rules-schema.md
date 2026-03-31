# Compliance Rules Schema Reference

JSON schema for `compliance-rules.json` — enforces banned phrases, required disclaimers, and platform-specific content policies.

## Location

```
~/socialforge-workspace/brands/<brand-slug>/compliance-rules.json
```

## Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `industry` | string | Yes | Industry vertical for default rule loading |
| `banned_phrases` | array | No | Phrases that must not appear in content |
| `required_disclaimers` | array | No | Disclaimers that must be included when triggered |
| `image_compliance` | object | No | Rules for visual content |
| `data_claim_rules` | object | No | Rules for statistical or data claims |
| `platform_specific_rules` | object | No | Per-platform overrides |

## `banned_phrases`

Each entry in the array:

| Sub-field | Type | Description |
|-----------|------|-------------|
| `phrase` | string | The banned text |
| `match_type` | string | `"exact"`, `"contains"`, or `"regex"` |
| `severity` | string | `"block"` (hard stop) or `"warn"` (flag for review) |
| `suggestion` | string | Recommended replacement text |

```json
{
  "banned_phrases": [
    {
      "phrase": "guaranteed results",
      "match_type": "contains",
      "severity": "block",
      "suggestion": "proven track record"
    },
    {
      "phrase": "\\b100%\\b",
      "match_type": "regex",
      "severity": "warn",
      "suggestion": "Use specific metrics instead of absolute claims"
    }
  ]
}
```

## `required_disclaimers`

Each entry:

| Sub-field | Type | Description |
|-----------|------|-------------|
| `trigger` | string | Keyword or pattern that activates the disclaimer |
| `disclaimer` | string | Text that must be included |
| `placement` | string | `"footer"`, `"inline"`, or `"first_comment"` |
| `platforms` | array | Platforms where this applies (empty = all) |

```json
{
  "required_disclaimers": [
    {
      "trigger": "financial",
      "disclaimer": "Not financial advice. Past performance does not guarantee future results.",
      "placement": "footer",
      "platforms": ["linkedin", "x", "facebook"]
    },
    {
      "trigger": "affiliate",
      "disclaimer": "#ad #sponsored",
      "placement": "inline",
      "platforms": []
    }
  ]
}
```

## `image_compliance`

| Sub-field | Type | Description |
|-----------|------|-------------|
| `no_real_people` | boolean | Block AI-generated images of identifiable real people |
| `no_competitor_logos` | boolean | Block images containing competitor branding |
| `require_alt_text` | boolean | Require alt text for accessibility |
| `min_diversity_score` | number | 0-1 score for representation diversity across campaigns |
| `banned_imagery` | array | Subjects to never depict (e.g., `["violence", "alcohol"]`) |

## `data_claim_rules`

| Sub-field | Type | Description |
|-----------|------|-------------|
| `require_source` | boolean | All statistics must include a source |
| `max_age_months` | number | Maximum age of cited data in months |
| `require_review` | boolean | Data claims must go through additional review |
| `allowed_sources` | array | Whitelisted data sources |

```json
{
  "data_claim_rules": {
    "require_source": true,
    "max_age_months": 12,
    "require_review": true,
    "allowed_sources": ["internal-analytics", "statista", "gartner"]
  }
}
```

## `platform_specific_rules`

Per-platform overrides keyed by platform name:

| Sub-field | Type | Description |
|-----------|------|-------------|
| `additional_banned` | array | Extra banned phrases for this platform |
| `required_hashtags` | array | Hashtags required on this platform |
| `max_hashtags` | number | Maximum hashtag count |
| `require_disclosure` | boolean | Require partnership/ad disclosure |
| `content_warnings` | array | Topics requiring content warnings |

```json
{
  "platform_specific_rules": {
    "instagram": {
      "max_hashtags": 15,
      "required_hashtags": ["#AcmeCorp"]
    },
    "linkedin": {
      "additional_banned": [
        { "phrase": "hustle culture", "match_type": "contains", "severity": "warn", "suggestion": "growth mindset" }
      ]
    }
  }
}
```

## Enforcement Behavior

- `"block"` severity halts the pipeline and requires human override.
- `"warn"` severity flags the issue but allows progression with acknowledgment.
- Compliance checking runs during Phase 5 (Review & Approval) and again at Phase 7 (Gallery Build).
- Missing `compliance-rules.json` applies industry-standard defaults.
