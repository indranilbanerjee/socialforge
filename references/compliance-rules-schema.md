# Compliance Rules Schema Reference

JSON schema for `compliance-rules.json` — enforces banned phrases, required disclaimers, and platform-specific content policies.

`scripts/compliance_check.py` is the enforcing implementation and the source of truth for the shapes below.

## Location

```
${CLAUDE_PLUGIN_DATA}/socialforge/brands/<brand-slug>/compliance-rules.json
```

When `CLAUDE_PLUGIN_DATA` is unset, the script falls back to:

```
~/socialforge-workspace/brands/<brand-slug>/compliance-rules.json
```

## Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `industry` | string | Yes | Industry vertical for default rule loading |
| `banned_phrases` | array | No | Phrases that must not appear in content |
| `required_disclaimers` | object or array | No | Disclaimers that must be included when triggered |
| `image_compliance` | array or object | No | Rules for visual content |
| `data_claim_rules` | object | No | Rules for statistical or data claims |
| `platform_specific_rules` | object | No | Per-platform overrides |

## `banned_phrases`

Each entry in the array:

| Sub-field | Type | Description |
|-----------|------|-------------|
| `phrase` | string | The banned text |
| `match_type` | string | `"exact"`, `"contains"`, or `"regex"` |
| `severity` | string | `"block"` or `"critical"` (both hard stops) — anything else, including `"warn"` / `"warning"`, is advisory. Defaults to `"warning"`. |
| `case_sensitive` | boolean | Match case-sensitively (default `false`) |
| `reason` | string | Why the phrase is banned — surfaced in the violation record |
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

Two forms are accepted. `compliance_check.py` normalizes both to `(trigger, disclaimer text, platforms)`.

**Mapping form (preferred)** — an object keyed by trigger:

| Sub-field | Type | Description |
|-----------|------|-------------|
| `disclaimer_text` | string | Text that must be included (`disclaimer` also accepted) |
| `platforms` | array | Platforms where this applies (empty or absent = all) |

```json
{
  "required_disclaimers": {
    "financial": {
      "disclaimer_text": "Not financial advice. Past performance does not guarantee future results.",
      "platforms": ["linkedin", "x", "facebook"]
    },
    "affiliate": {
      "disclaimer_text": "#ad #sponsored",
      "platforms": []
    }
  }
}
```

**Array form** — a list of objects, each carrying its trigger inline:

| Sub-field | Type | Description |
|-----------|------|-------------|
| `trigger` | string | Keyword that activates the disclaimer (entries without one are skipped) |
| `disclaimer` | string | Text that must be included (`disclaimer_text` also accepted) |
| `placement` | string | `"footer"`, `"inline"`, or `"first_comment"` — advisory metadata; not enforced by the checker |
| `platforms` | array | Platforms where this applies (empty = all) |

```json
{
  "required_disclaimers": [
    {
      "trigger": "financial",
      "disclaimer": "Not financial advice. Past performance does not guarantee future results.",
      "placement": "footer",
      "platforms": ["linkedin", "x", "facebook"]
    }
  ]
}
```

A missing disclaimer is raised as a **warning**, never a hard stop.

## `image_compliance`

Text-based flagging only — the checker does not analyze image pixels. Two forms are accepted.

**Array form** — a list of rule objects. Only rules with `check_method: "manual_flag"` are surfaced:

| Sub-field | Type | Description |
|-----------|------|-------------|
| `rule` | string | Human-readable description shown in the flag |
| `check_method` | string | Must be `"manual_flag"` to be emitted |
| `severity` | string | Defaults to `"warning"` |

```json
{
  "image_compliance": [
    { "rule": "Images must not depict identifiable real people", "check_method": "manual_flag", "severity": "warning" }
  ]
}
```

**Object form** — boolean/number switches, expanded into the same manual-review flags:

| Sub-field | Type | Description |
|-----------|------|-------------|
| `no_real_people` | boolean | Flag images of identifiable real people |
| `no_competitor_logos` | boolean | Flag images containing competitor branding |
| `require_alt_text` | boolean | Flag missing alt text for accessibility |
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

- `"block"` and `"critical"` severities both halt the pipeline and require human override. The checker returns `status: "BLOCKED"` when any is triggered.
- Any other severity (`"warn"`, `"warning"`) flags the issue but allows progression with acknowledgment. The checker returns `status: "WARNING"`.
- Forbidden content types matched via `platform_specific_rules.<platform>.forbidden_content_types` are always critical.
- Data-claim matches, hashtag-limit overruns, missing disclaimers, and image rules are always warnings.
- With no violations and no warnings the checker returns `status: "PASSED"`.
- A missing `compliance-rules.json` returns `status: "SKIPPED"` — no rules are applied and nothing is blocked.
