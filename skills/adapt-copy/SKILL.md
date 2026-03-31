---
name: adapt-copy
description: Adapt post copy per platform — character limits, hashtags, CTAs, tone, and compliance checking.
argument-hint: "[--post <id>] [--all] [--platform <name>]"
effort: medium
user-invocable: true
---

# /sf:adapt-copy — Copy Adapter

Transform a single caption brief into platform-optimized copy for each target platform.

## Process (Per Post x Per Platform)

1. Load post brief (topic, caption_brief, CTA, hashtags, campaign)
2. Load brand-config.json (tone, hashtags, language settings)
3. Load compliance-rules.json (banned phrases, disclaimers)
4. Generate platform-specific copy:

| Platform | Tone | Limit | Hashtags | Link |
|----------|------|-------|----------|------|
| LinkedIn | Professional | 3,000 chars (140 before fold) | 3-5 | Direct URL |
| Instagram | Conversational | 2,200 chars | 20-30 (first comment) | Link in bio |
| X/Twitter | Punchy, concise | 280 chars | 1-2 | Direct URL |
| Facebook | Casual | 500 chars optimal | 1-3 | Direct URL |
| YouTube | Description format | 5,000 chars | 3-5 | Direct URLs |

5. Apply brand hashtags (always_include + campaign-specific)
6. Run compliance check — flag banned phrases, add disclaimers
7. Handle bilingual posts if configured
8. Save to `production/copy/post-{id}-{platform}-copy.txt`

## Compliance Check (Mandatory)

Before saving any copy:
- Scan against compliance-rules.json banned_phrases
- Check data claims against data_claim_rules
- Add required disclaimers per platform
- Verify platform-specific rules (link policy, hashtag limits)

**Critical violations BLOCK** — copy cannot proceed.
**Warnings are noted** but don't block.

## Output

```
Copy adapted: Post P04
  LinkedIn: 847 chars (under 3000) ✓ | 4 hashtags ✓ | CTA: direct link ✓
  Instagram: 1,203 chars ✓ | 25 hashtags (first comment) ✓ | CTA: link in bio ✓
  X: 267 chars (under 280) ✓ | 2 hashtags ✓ | CTA: direct link ✓
  Compliance: PASSED (0 critical, 1 warning: "consider adding source for 47% claim")
```

## Timeout & Fallback
- Copy generation: 30-second timeout per platform variant
- Compliance check: 10-second timeout. If fails, flag for manual review
