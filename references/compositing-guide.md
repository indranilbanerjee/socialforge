# Compositing Guide

How SocialForge's 4 creative modes work — when to use each, pipeline steps, and quality benchmarks.

## The 4 Creative Modes

| Mode | Input | Output | Best For |
|------|-------|--------|----------|
| `ASSET_ONLY` | Existing brand photo | Cropped/resized image | Product shots, team photos |
| `ANCHOR_COMPOSE` | Brand photo + text overlay | Composited branded image | Thought-leadership, announcements |
| `STYLE_REFERENCED` | Style ref + AI prompt | AI-generated image matching brand style | When no suitable asset exists |
| `AI_ORIGINAL` | AI prompt only | AI-generated image from scratch | Abstract concepts, illustrations |

## When to Use Each Mode

**ASSET_ONLY** — You have a strong brand photo that needs no enhancement. Just crop to platform dimensions.
- Tier: Any
- Risk: Low (no generation involved)

**ANCHOR_COMPOSE** — You have a good photo but need branded text overlays, logo placement, or gradient backgrounds.
- Tier: HUB and HERO preferred
- Risk: Low (deterministic compositing)

**STYLE_REFERENCED** — No existing asset fits, but you want the AI output to match your brand's visual identity.
- Tier: Any (with human approval)
- Risk: Medium (AI generation with style constraint)

**AI_ORIGINAL** — Fully AI-generated. No anchor image or style reference. Use sparingly.
- Tier: HYGIENE only (unless client opts in)
- Risk: Higher (less brand control)

## ANCHOR_COMPOSE Pipeline

1. **Select anchor image** — Pull from asset-index by `suitable_for` and `platforms_compatible`.
2. **Resize to target** — Crop/scale to platform dimensions (e.g., 1200x627 for LinkedIn feed).
3. **Apply gradient overlay** — Semi-transparent gradient using `colors.primary` or `colors.social_overlay`.
4. **Render text overlay** — Place `headline` and `subtext` using brand fonts with contrast-safe colors.
5. **Add logo** — Place logo per `logo_overlay` config (position, opacity, padding).
6. **Export variants** — Generate per-platform variants at correct dimensions.

### Prompt Construction for Text Overlay

```
headline: Keep under 6 words. All caps or title case per brand style.
subtext: 1 line max. Supporting context only.
```

Text placement follows a grid: headline at 40% vertical, subtext at 55% vertical, both left-aligned with 8% horizontal padding.

## STYLE_REFERENCED Pipeline

1. **Select style reference** — Choose an asset with `is_style_reference: true` from the index.
2. **Build generation prompt** — Combine the post's `visual.prompt` with style cues extracted from the reference (mood, lighting, color palette).
3. **Generate image** — Send to AI provider with the style reference attached.
4. **Quality check** — Verify no text artifacts, no real-person likenesses, brand color presence.
5. **Composite** — Apply logo overlay and any text overlays.
6. **Human approval gate** — AI-generated images always require explicit approval.

### Prompt Construction Tips

- Start with the subject, then describe the setting, mood, lighting, and color palette.
- Include "no text, no words, no letters, no watermarks" in every prompt.
- Reference brand colors by description, not hex (e.g., "deep blue and white" not "#1A73E8").
- Avoid named people, copyrighted characters, or competitor brands.

## Quality Benchmarks

| Criterion | Pass | Fail |
|-----------|------|------|
| Resolution | Meets platform minimum | Below minimum dimensions |
| Brand colors | Primary color visible in composition | No brand color presence |
| Text readability | Contrast ratio >= 4.5:1 | Text lost in background |
| Logo placement | Visible, not cropped, correct position | Cropped, obscured, or missing |
| AI artifacts | Clean edges, coherent subjects | Extra fingers, melted text, distortion |
| Aspect ratio | Matches platform spec exactly | Wrong ratio (will be cropped by platform) |

## Common Pitfalls

- **Text in AI images**: AI providers render text poorly. Always add text via compositing, never in the prompt.
- **Over-compositing**: Too many overlays make images look cluttered. One headline + logo is usually enough.
- **Ignoring safe zones**: Platforms crop differently in feeds vs. detail views. Keep key elements in the center 80%.
- **Style drift**: When using STYLE_REFERENCED across many posts, periodically verify consistency against the reference.
