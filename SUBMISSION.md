# Anthropic Software Directory — Submission Packet

**Plugin:** SocialForge
**Version at submission:** 1.6.0
**Submitter:** Indranil Banerjee — neel@neelverse.com
**Repository:** https://github.com/indranilbanerjee/socialforge
**Marketplace:** https://github.com/indranilbanerjee/neels-plugins
**Last updated:** 2026-05-17

This file is the submission packet for the Anthropic Software Directory. It is **not** the directory listing — that is submitted via https://platform.claude.com/plugins/submit. This packet pre-stages every input the form will ask for so submission takes ~5 minutes.

## 1. One-line description

> Agency-grade social media calendar automation with asset-first compositing, AI image generation (Vertex AI Nano Banana Pro), and AI video generation (WaveSpeed Kling v3.0 Pro). C2PA content provenance for EU AI Act Article 50 compliance.

## 2. Long description

SocialForge is a social media calendar and creative production system for marketing agencies and in-house teams running multi-brand, multi-platform social calendars. It parses content calendars, matches brand assets, generates AI-composed creative, renders carousels, adapts copy per platform, post-processes video with ffmpeg, and produces approval-ready review galleries.

**v1.6.0** adds end-to-end-tested C2PA content provenance for AI-generated assets — the EU AI Act Article 50 obligation that applies from 2 August 2026 falls squarely on SocialForge (it's the plugin generating AI images and video). New `scripts/c2pa_sign.py` wraps `c2pa-python>=0.32` with the current Builder + Signer.from_info API. New `/socialforge:c2pa-sign` skill exposes it. Optional auto-sign hooks in `scripts/generate_image.py` (post-image-generation) and `scripts/video_postprocess.py` (post-per-platform-resize) embed machine-readable provenance manifests with brand, generator, prompt, target-platform metadata before assets hit delivery. Plus a May 2026 channel-pack reference covering TikTok USDS Joint Venture (post-Jan 2026), LinkedIn March 2026 algorithm + Depth Score, Apple MPP B2C open-rate decline, Meta Advantage+ shopping, YouTube AI labeling, Sora deprecation timeline.

Image generation defaults to Google Vertex AI (Gemini Nano Banana 2 / 3 Pro) with WaveSpeed and HiggsField fallbacks. Video generation defaults to WaveSpeed Kling v3.0 Pro with Vertex AI Veo and HiggsField fallbacks. All AI-generated visuals require explicit user approval before use — SocialForge is built around human-in-the-loop creative review, not autonomous publishing.

25 commands, 16 skills, 5 agents, 20 Python scripts, 10 HTTP MCP connectors (Notion, Canva, Slack, Gmail, Google Calendar, Figma, fal.ai, Replicate, Asana, Cloudinary — all Cowork-compatible). Multi-plugin coexistence by design (zero global hooks).

## 3. Category

`Marketing & Sales` (primary) · `Productivity` (secondary)

## 4. Target audience

- Social media agencies producing 50–500 posts/month across 5–50 brands
- In-house social teams running multi-platform calendars
- Creator-led brands that need agency-grade creative output without an in-house creative team
- Brands subject to EU AI Act Article 50 (any brand distributing AI-generated visuals into EU markets after 2 Aug 2026)

## 5. Working use cases (Anthropic policy requirement: 3+)

### Use case 1 — Generate an EU-compliant AI image

```
/socialforge:setup    # one-time admin credential setup
/socialforge:brand-setup acme-corp

python3 scripts/generate_image.py \
    --prompt "minimalist product hero shot, soft natural lighting" \
    --output assets/acme/q3-hero.png \
    --model gemini-3-pro-image-preview \
    --aspect-ratio 1:1 \
    --c2pa-sign --brand "Acme Corp" --platform instagram
```

The script generates the image via Vertex AI, then post-processes through `c2pa_sign.py` which embeds a C2PA manifest (brand = Acme Corp organization, generator = "vertex_ai / gemini-3-pro-image-preview", target platform = Instagram, IPTC `TRAINED_ALGORITHMIC_MEDIA` digital-source-type). Resulting PNG verifies at contentcredentials.org/verify. Article 50 compliant.

**Empirically tested:** 75-byte test PNG → 42,996-byte signed PNG with `manifest_embedded_and_verified=true`, active manifest ID `urn:c2pa:...`.

### Use case 2 — Multi-platform video pipeline with per-platform C2PA

```
python3 scripts/generate_video.py \
    --prompt "30-second product launch teaser" \
    --output campaigns/q3-launch.mp4 \
    --model kling-v3-pro

python3 scripts/video_postprocess.py \
    --input campaigns/q3-launch.mp4 \
    --output-dir campaigns/processed/ \
    --brand acme-corp \
    --platforms tiktok,instagram,linkedin,youtube \
    --burn-subs --srt campaigns/captions.srt \
    --c2pa-sign \
    --c2pa-generator "WaveSpeed Kling v3.0 Pro" \
    --c2pa-prompt "30-second product launch teaser"
```

`video_postprocess.py` resizes for each platform (TikTok 1080×1920, Instagram 1080×1080, LinkedIn 1200×627, YouTube 1280×720), burns subtitles, watermarks with brand logo, then signs each per-platform output with its own C2PA manifest. The per-platform manifest records `platform: tiktok` / `platform: instagram` etc. — different distributions, separately verifiable.

### Use case 3 — Monthly content calendar with asset-first compositing

```
/socialforge:new-month acme-corp 2026-06
/socialforge:index-assets acme-corp
/socialforge:generate-all
/socialforge:review
/socialforge:finalize
```

Parses the month's calendar, matches each post slot to brand assets (up to 14 reference images per AI generation for style continuity), generates the creative, produces a review gallery with platform previews, and packages for delivery. Multi-brand teams run this once per client per month.

### Use case 4 — Carousel rendering for LinkedIn (post-March-2026 algo favors B2B carousels)

```
/socialforge:render-carousels acme-corp june-2026/linkedin-thought-leadership-series
```

Renders multi-page LinkedIn carousels (PDF) with consistent brand application, optimized for the post-March-2026 LinkedIn algorithm's Depth Score signal (longer dwell time → wider distribution).

## 6. Testing account / sample data

**Testing account:** Reviewers install from `indranilbanerjee/neels-plugins` and use `references/brand-config-schema.md` as the brand profile template. The plugin requires Google Cloud Vertex AI credentials and a WaveSpeed API key for the AI generation paths; `references/image-gen-guide.md` and the README's Admin Setup section walk through credential acquisition. For evaluation without API keys, the `--placeholder` mode in `generate_image.py` produces a Pillow-rendered placeholder demonstrating the workflow shape without making external API calls.

**Sample worked output:** the `assets/` directory in the repo contains a small example brand asset library demonstrating the asset-first compositing pattern.

## 7. Ownership verification

- **Repo:** github.com/indranilbanerjee/socialforge — owned by @indranilbanerjee
- **Marketplace:** github.com/indranilbanerjee/neels-plugins — same owner
- **Third-party services referenced:** Google Cloud (Vertex AI / Gemini), WaveSpeed (Kling), HiggsField (Soul / Kling fallback), fal.ai (Flux + 100s of models), Replicate (fallback), Notion, Canva, Slack, Gmail, Google Calendar, Figma, Asana, Cloudinary. All accessed via official endpoints; no scraping, no credential interception.
- **Trademarks:** "SocialForge" is the submitter's mark.

## 8. Compliance with Anthropic Software Directory Policy

| Policy area | Status |
|---|---|
| No High-Risk Use Cases | ✓ Social media creative generation; not biometric, not employment-screening, not financial advice. AI-generated creators must be disclosed per platform rules (TikTok, YouTube) — plugin documents this requirement. |
| No Usage Policy violation | ✓ Generates legitimate marketing creative. Brand guardrails mechanism + human-in-the-loop approval prevent autonomous publishing of non-approved content. |
| Testing account + sample data + 3+ use cases | ✓ Sections 5, 6. |
| Ownership of APIs/domains/UIs | ✓ Section 7. |
| Maintenance commitment | ✓ v1.5.0 (May 2026) → v1.5.1 → v1.5.2 → v1.5.3 (May 9) → v1.6.0 (May 17). |
| Issue response timeframe | ✓ <72 hours acknowledgement, <7 days security/correctness patches. |
| Software Directory Terms agreement | ☐ Agreed at submission time. |
| Design guidelines | ✓ Canonical `/socialforge:<command>` namespace per v1.5.3 sweep; README onboarding-first per v1.6.0 restructure. |

## 9. Cowork compatibility statement

- All 10 HTTP MCP connectors work in both Claude Code and Cowork.
- All Python scripts (including `c2pa_sign.py`, `generate_image.py`, `generate_video.py`, `video_postprocess.py`) run natively in Cowork — Cowork is the Anthropic Desktop computer-use product with local filesystem access. ffmpeg is bundled via `imageio-ffmpeg` (no system install needed).
- Plugin ships zero global hooks and zero auto-connecting MCP servers.
- For services without first-party HTTP MCPs (TikTok Business API for direct publishing, etc.), `.mcp.json.connectors-reference` documents Pipedream / Composio / Zapier / Make aggregator paths.

## 10. Verified-badge eligibility

SocialForge qualifies based on:
- v1.6.0 C2PA Article 50 compliance path (end-to-end empirically verified: 75-byte test PNG → 42,996-byte signed PNG, manifest round-trips)
- Asset-first compositing pattern (reduces hallucinated brand-asset risk vs purely-generative approaches)
- Human-in-the-loop approval gate before publishing
- Zero global hooks (multi-plugin coexistence)

If applying for Verified, additional materials:
- Security review of `c2pa_sign.py` signing-key handling
- Privacy review of brand-config schema (handles brand IP — confirm no PII transmission outside Claude API)
- Code review of `video_postprocess.py` (ffmpeg pipeline; security implications of subtitle / watermark / audio inputs)

## 11. Screenshots to include with submission

Capture before submitting:
1. A C2PA-signed AI image verified at contentcredentials.org/verify (shows Article 50 compliance in action)
2. A multi-platform video output gallery (one source → 4 per-platform outputs each with C2PA)
3. The asset-first compositing UX (reference assets + AI-generated composition side-by-side)
4. `/socialforge:review` approval gallery showing the human-in-the-loop gate
5. A monthly content calendar in `/socialforge:new-month` mode showing brand × platform × slot grid

## 12. Submission steps

1. Open https://platform.claude.com/plugins/submit
2. Plugin name: `socialforge`
3. Marketplace source: `github.com/indranilbanerjee/neels-plugins` (custom marketplace) OR `github.com/indranilbanerjee/socialforge` (direct repo)
4. Paste section 1 into Short description
5. Paste section 2 into Description
6. Category: Marketing & Sales (primary), Productivity (secondary)
7. Upload screenshots from section 11
8. Confirm testing-account + sample-data declaration (sections 5, 6)
9. Confirm ownership (section 7)
10. Check the Software Directory Terms box
11. Submit

Expected review timeline: 1–2 weeks basic, 4–6 weeks Verified.

---

**Maintained in the repo so it can be refreshed each release before re-submission.**
