# Compositing Guide

How SocialForge's 4 creative modes work — when to use each, pipeline steps, and quality benchmarks.

## The 4 Creative Modes

| Mode | Input | Output | Best For |
|------|-------|--------|----------|
| `ANCHOR_COMPOSE` | Brand photo (untouched) + AI scene | Brand asset anchored in a generated scene | Product shots, team photos, announcements |
| `ENHANCE_EXTEND` | Brand photo as the base | Periphery extended/enhanced, core pixel-faithful | Reframing an asset to a new aspect ratio |
| `STYLE_REFERENCED` | Style ref + AI prompt | AI-generated image matching brand style | When no suitable asset exists |
| `PURE_CREATIVE` | AI prompt + brand colors/mood | AI-generated image from scratch | Abstract concepts, illustrations |

`scripts/match_assets.py` recommends the mode from the best asset match score: >0.8 → ANCHOR_COMPOSE, >0.5 → ENHANCE_EXTEND, >0.3 → STYLE_REFERENCED, otherwise PURE_CREATIVE. Carousel and text-only posts bypass the four modes entirely (CAROUSEL_TEMPLATE / TEXT_ONLY).

## When to Use Each Mode

**ANCHOR_COMPOSE** — You have a strong brand photo that should be the centerpiece. AI generates the scene around it; the asset itself stays untouched.
- Tier: HUB and HERO preferred
- Risk: Low (asset is pixel-faithful)

**ENHANCE_EXTEND** — The brand photo is right but the frame is wrong, or the periphery is weak. AI extends and enhances around the edges while the core subject stays faithful.
- Tier: Any
- Risk: Low-medium (generation confined to the periphery)

**STYLE_REFERENCED** — No existing asset fits, but you want the AI output to match your brand's visual identity via style reference photos.
- Tier: Any (with human approval)
- Risk: Medium (AI generation with style constraint)

**PURE_CREATIVE** — Fully AI-generated from a text prompt plus brand colors and mood. No anchor image or style reference. Use sparingly.
- Tier: HYGIENE only (unless client opts in)
- Risk: Higher (least brand control)

## ANCHOR_COMPOSE Pipeline

1. **Select anchor image** — Pull from asset-index by `suitable_for` and `platforms_compatible`.
2. **Isolate the asset** — Remove or mask the background so the subject can sit in a generated scene. The asset's pixels are never regenerated.
3. **Generate the surrounding scene** — Build the background/context from the post's `visual.prompt` plus brand colors and mood.
4. **Composite** — Place the untouched asset into the generated scene at platform dimensions (e.g., 1200x627 for LinkedIn feed).
5. **Render text overlay** — Place `headline` and `subtext` using brand fonts with contrast-safe colors.
6. **Add logo** — Place logo per `logo_overlay` config (position, opacity, padding).
7. **Export variants** — Generate per-platform variants at correct dimensions.

## ENHANCE_EXTEND Pipeline

1. **Select base image** — Same asset-index selection as ANCHOR_COMPOSE, but the photo carries the whole frame rather than sitting inside a new one.
2. **Define the protected core** — Mark the subject region that must remain pixel-faithful.
3. **Outpaint / enhance the periphery** — Extend the edges to the target aspect ratio and lift lighting or context outside the protected core.
4. **Verify fidelity** — Confirm the protected region is unchanged and the seam between original and generated pixels is invisible.
5. **Overlay + export** — Text overlay, logo, per-platform variants as above.

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

## PURE_CREATIVE Pipeline

1. **Build generation prompt** — The post's `visual.prompt` plus the brand's colors and mood described in words. No anchor asset, no style reference.
2. **Generate image** — Send to the AI provider at the target aspect ratio.
3. **Quality check** — Verify no text artifacts, no real-person likenesses, no competitor or third-party marks, brand color presence.
4. **Composite** — Apply logo overlay and any text overlays.
5. **Human approval gate** — Fully generated images always require explicit approval; flag the post for AI-disclosure handling (C2PA signing, and a visible label where the platform or jurisdiction requires one).

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
