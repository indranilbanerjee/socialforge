---
name: adapt-copy
description: "Adapt post copy per platform: character limits, hashtags, tone and the right CTA mechanism. \"rewrite this caption for LinkedIn\""
argument-hint: "[--post <id>] [--all] [--platform <name>]"
effort: medium
user-invocable: true
---

# /socialforge:adapt-copy — Copy Adapter

> **Script location.** If your host does not set `${CLAUDE_PLUGIN_ROOT}`, the scripts are in this plugin's `scripts/` folder, next to `skills/`.

Transform a single caption brief into platform-optimized copy for each target platform.

## Context efficiency

Asset-heavy skill. **Grep before Read** the asset catalog (`${CLAUDE_PLUGIN_DATA}/socialforge/brands/<brand>/asset-index.json`) — never list the asset directory. Reference generated images / videos by path, not by loading metadata. Brand profile loads once per session.

## Process (Per Post x Per Platform)

1. Load post brief (topic, caption_brief, CTA, hashtags, campaign)
2. Load brand-config.json (tone, hashtags, language settings)
3. Load compliance-rules.json (banned phrases, disclaimers)
4. For X/Twitter posts with live-source context, read the optional [X/Twitter research intake](../../references/x-twitter-research-intake.md) note and use only reviewed evidence
5. Write platform-specific copy (tone and structure per platform, within these limits):

| Platform | Tone | Limit | Hashtags: aim / script cap | Link |
|----------|------|-------|----------------------------|------|
| LinkedIn | Professional | 3,000 chars (140 before fold) | 3-5 / 5 | Direct URL |
| Instagram | Conversational | 2,200 chars | 3-5 / 5 (first comment) | Link in bio |
| X/Twitter | Punchy, concise | 280, counted by weight (emoji and CJK 2, any URL 23) | 1-2 / 2 | Direct URL |
| Facebook | Casual | 500 chars optimal (63,206 hard limit) | 1-3 / 3 | Direct URL |
| YouTube | Description format | 5,000 chars | 3-5 / 5 | Direct URLs |
| TikTok | Casual, trend-aware | 2,200 chars | 3-5 / 10 (trending + branded) | Link in bio |
| Pinterest | Search-friendly description | 800 chars | 5-10 / 20 | Direct URL |
| Threads | Conversational | 500 chars | 1 / 1 | Direct URL |
| Bluesky | Concise, community-first | 300 chars | 1-2 / 2 (via tag facets) | Direct URL |

**The limits are data, and not all of them are confirmed.** `scripts/platform_limits.json` records every number with its source URL, the date it was checked and a status: confirmed (a primary platform page says it), differs, or unsourced (SocialForge's working value, no readable primary page). On 2026-10-04 the character limits for Instagram, Facebook and TikTok were unsourced (third-party pages report 4,000 for TikTok; unconfirmed, so 2,200 stays as the safe cap), as is every fold position. Run `python "${CLAUDE_PLUGIN_ROOT}/scripts/adapt_copy.py" --sources` before telling anyone a limit is official; platforms change limits without notice. "Aim" is a working range from SocialForge's platform notes, not a platform rule. The script cap is how many hashtags `adapt_copy.py` keeps.

6. Measure and fit every variant with `adapt_copy.py` (see "Run the adapter" below)
7. Apply brand hashtags (always_include + campaign-specific), up to each platform's cap, and tell the user which ones the cap dropped
8. Run compliance check - flag banned phrases, add disclaimers
9. Handle bilingual posts if configured
10. Save to `production/copy/post-{id}-{platform}-copy.txt`

**No significance markers.** Never write a line whose only job is to announce that the next line matters: "here's the thing", "the thing is,", "here's the kicker", "here's where it gets interesting", "that's the part that got me", "let that sink in", "read that again". They read as machine-written, and on a 280-character platform they spend budget the point needs. Lead with the specific instead — "Approvals went from 14 days to 31" beats "Here's the thing about approval timelines". Same for stacked soft adverbs (honestly / genuinely / truly / literally / actually / basically): at most one per caption, never two in a sentence.

This is a writing rule enforced by the copy-adapter agent, not a scan. SocialForge ships no AI-tell scanner on purpose — caption-length copy has no document structure to measure, and per-1000-word metrics are noise at 280 characters.

When the post's CTA is a conversation (a keyword that opens a DM, a WhatsApp or Messenger thread), read [conversational-commerce.md](../../references/conversational-commerce.md): opt-in and 24-hour-window rules, and playbooks for the post, the first reply, the handoff, and templates.

## Run the adapter

Write each variant **without** the CTA and without hashtags, then measure and fit it:

```
python "${CLAUDE_PLUGIN_ROOT}/scripts/adapt_copy.py" --text "<the variant>" --platform x --brand <slug> --cta "<CTA wording and URL>" --campaign-hashtags "#Tag1" "#Tag2"
```

Read these fields of the JSON it prints:

- `within_limit`, `char_count`, `char_limit` - the variant measured against the limit. `count_method` says how it was counted: `code_points` (plain characters) everywhere except X, which is `x_weighted`: emoji and CJK characters count 2 and every URL counts 23 however long it is, so X's `char_count` is not `len(copy)`. If `within_limit` is false, shorten the copy or the CTA.
- `copy` - the variant with the CTA turned into the platform's mechanism. If it is shorter than what you wrote, the script cut it mechanically: tighten the prose and run it again rather than shipping the cut.
- `hashtags`, `first_comment` - what to post and where (Instagram: first comment).
- `hashtags_dropped` - the hashtags the platform's cap left out, in the order given (an empty list when none). **Tell the user which hashtags were dropped, per platform**; a cap must never remove a tag without saying so. Put the tags that must survive first.

What the script does not measure: Threads counts emoji as UTF-8 bytes (more than 1 each), Bluesky's limit is 300 graphemes (code points can only over-count), and a bare domain without `http://`, `https://` or `www.` counts as plain text although X links it. Keep a margin on X and Threads when the copy has emoji or bare domains.

## Compliance Check (Mandatory)

Before saving any copy:
- Scan against compliance-rules.json banned_phrases
- Check data claims against data_claim_rules
- Add required disclaimers per platform
- Verify platform-specific rules (link policy, hashtag limits)
- For X/Twitter source notes, verify quotes, public metrics, and dates before using them as claims
- AI-generation labels: `adapt_copy.py` adds no label to any caption, and `compliance_check.py` only reports a required disclaimer that is missing (when its trigger word appears in the copy) and suggests the text; neither inserts anything. Caption-level AI labels belong to each platform's native disclosure toggle, flagged at publish handoff. If the brand's rules want visible wording in a caption, add it by hand

**Critical violations BLOCK** — copy cannot proceed.
**Warnings are noted** but don't block.

## Output

```
Copy adapted: Post P04
  LinkedIn: 847 chars (under 3000) ✓ | 4 hashtags ✓ | CTA: direct link ✓
  Instagram: 1,203 chars ✓ | 5 hashtags (first comment) ✓ | CTA: link in bio ✓
  X: 267 weighted chars (under 280) ✓ | 2 hashtags ✓ | CTA: direct link ✓
  Hashtags dropped by the cap: X: #CustomerSuccess | LinkedIn: none | Instagram: none
  Compliance: PASSED (0 critical, 1 warning: "consider adding source for 47% claim")
```

## Timeout & Fallback
- Copy generation: 30-second timeout per platform variant
- Compliance check: 10-second timeout. If fails, flag for manual review
