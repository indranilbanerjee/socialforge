---
description: Create a reactive/trending post outside the planned calendar
argument-hint: "<topic> [--brand <name>] [--platform <name>]"
---

# Reactive Post

Create an unplanned post in response to a trending topic, news event, or opportunity.

## Process
1. Accept topic and context from user
2. Determine target platforms (default: all active)
3. If X/Twitter is a target platform and the topic depends on a live conversation, run the optional [X/Twitter research intake](../references/x-twitter-research-intake.md) before drafting
4. Assign as HYGIENE tier (fast approval) unless user specifies otherwise
5. Generate creative using STYLE_REFERENCED or PURE_CREATIVE mode
6. Adapt copy for platforms, using only reviewed research notes as evidence
7. Fast-track through compliance check
8. Add to calendar-data.json as an extra post
9. Show for immediate approval
