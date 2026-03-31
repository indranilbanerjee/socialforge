# AI Image Generation Guide

Best practices for generating images in SocialForge — prompt engineering, reference selection, quality review, and provider comparison.

## 5-Layer Prompt Structure

Build generation prompts in this order:

```
Layer 1 — Subject:     What is in the image (e.g., "a modern glass office building")
Layer 2 — Setting:     Environment and context (e.g., "surrounded by green trees, city skyline behind")
Layer 3 — Mood:        Emotional tone (e.g., "optimistic, aspirational, clean")
Layer 4 — Lighting:    Light quality (e.g., "golden hour, soft natural light from left")
Layer 5 — Style:       Visual treatment (e.g., "editorial photography, shallow depth of field, 35mm lens")
```

### Example Prompt

```
A diverse group of professionals collaborating at a standing desk with colorful sticky notes,
in a bright modern coworking space with floor-to-ceiling windows,
energetic and productive mood,
natural daylight with soft shadows,
editorial photography style, Canon 50mm f/1.4, slight bokeh background
--no text, no words, no letters, no watermarks, no logos
```

## Negative Prompts (Always Include)

Every prompt must end with exclusions:

```
--no text, no words, no letters, no numbers, no watermarks, no logos,
no distorted hands, no extra fingers, no blurry faces
```

## Reference Image Selection

When using STYLE_REFERENCED mode, choose references that:

- Have `is_style_reference: true` in the asset index
- Match the target mood and lighting conditions
- Feature the brand's color palette naturally
- Are high resolution (2x the target output minimum)

Avoid references that:
- Contain text (AI will try to reproduce it, poorly)
- Have complex multi-subject compositions
- Are heavily filtered or post-processed

## What to Avoid

| Do Not | Why | Instead |
|--------|-----|---------|
| Generate text in images | AI renders text illegibly | Add text via compositing pipeline |
| Depict real people | Likeness rights / legal risk | Use generic, non-identifiable subjects |
| Include brand logos | AI distorts logos | Overlay logos in compositing step |
| Use competitor names in prompts | May generate trademarked content | Describe generically |
| Request photorealistic faces | Uncanny valley risk | Use medium shots, turned heads, or silhouettes |
| Over-specify details | Reduces generation quality | Focus on mood and style, not pixel-level control |

## Quality Review Checklist

Before approving any AI-generated image:

- [ ] No text artifacts or letter-like shapes anywhere in the image
- [ ] No distorted anatomy (hands, fingers, faces)
- [ ] Brand colors are present or compatible
- [ ] Mood matches the post's intent
- [ ] No identifiable real people or copyrighted content
- [ ] Resolution meets platform minimum (check platform-specs.md)
- [ ] Background is clean — no nonsensical objects or floating elements
- [ ] Aspect ratio is correct for the target platform

## Provider Comparison

| Feature | Gemini (Imagen) | fal.ai | Replicate |
|---------|----------------|--------|-----------|
| Speed | Fast (~5s) | Fast (~3-8s) | Variable (~5-30s) |
| Quality | High | High | Model-dependent |
| Style control | Good | Very good | Excellent (model choice) |
| Reference support | Limited | Yes (IP-Adapter) | Yes (multiple methods) |
| Cost | Per-request | Per-request | Per-second |
| Best for | Quick generation | Style transfer | Advanced control |

### Provider Selection Logic

1. **ASSET_ONLY / ANCHOR_COMPOSE** — No AI provider needed (compositing only).
2. **STYLE_REFERENCED** — Prefer fal.ai (IP-Adapter support) or Replicate (ControlNet).
3. **AI_ORIGINAL** — Use Gemini for speed, Replicate for quality, fal.ai for balance.

## Batch Generation Tips

- Generate 2-3 variants per post and let the human reviewer choose.
- Vary the mood or lighting between variants, not the subject.
- Cache style reference embeddings to speed up batch runs.
- Always generate at 2x target resolution and downscale.
