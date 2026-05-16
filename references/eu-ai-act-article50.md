# EU AI Act Article 50 — Generative AI Transparency Obligations

**Status as of May 2026:** Applicable from **2 August 2026** (76 days from this revision).
**Plugin coverage:** v1.6.0+ via the C2PA signing path (see `scripts/c2pa_sign.py` and `skills/c2pa-sign/SKILL.md`).

## What Article 50 actually requires

Article 50 of [Regulation (EU) 2024/1689](https://artificialintelligenceact.eu/article/50/) imposes transparency obligations on providers AND deployers of certain AI systems. For SocialForge users, the deployer-side obligations are:

1. **Machine-readable marking of AI-generated content.** Any image, video, audio, or text generated or substantially manipulated by an AI system that is distributed in EU markets must carry a marking that is:
   - In a machine-readable format
   - Using open, interoperable standards (C2PA is the emerging backbone)
   - Technically robust enough to survive routine processing (re-encoding, resizing, format conversion)

2. **Visible deepfake disclosure.** Synthetic audio / image / video resembling real persons, objects, places, or events must additionally carry a *visible* disclosure (text overlay, audio cue, or platform-native label). Machine-readable marking alone is not enough for deepfakes.

3. **AI-generated text on matters of public interest** must be disclosed unless human-reviewed and the brand assumes full editorial responsibility.

## Penalties

Non-compliance with Article 50 transparency: up to **€15 million or 3% of global annual turnover**, whichever is higher.

High-risk-system breaches (separate from Article 50): up to **€35 million or 7%**.

## Carve-outs

Genuine artistic, satirical, or fictional works are narrowly exempt. Marketing content does **not** qualify for the artistic carve-out.

## What SocialForge does

When the brand profile sets `c2pa_auto_sign: true` (or any image/video generation call passes `--c2pa-sign --brand <name>`), the generation pipeline calls `scripts/c2pa_sign.py` as a post-step. The script:

- Embeds a C2PA manifest in the output asset
- Records: brand (CreativeWork.author), generator name + version, prompt, target platform, timestamp
- Records the IPTC digital-source-type tag: `TRAINED_ALGORITHMIC_MEDIA` for `ai-generated-content`, `COMPOSITE_WITH_TRAINED_ALGORITHMIC_MEDIA` for `ai-assisted-edits`, `HUMAN_EDITS` for `ai-no-substantive-changes`
- Round-trips the manifest through `c2pa.Reader` to verify embedding succeeded before returning

The signing logic is shared in spirit (not in implementation) with Digital Marketing Pro's `embed-c2pa.py` — both produce interoperable manifests verifiable at [contentcredentials.org/verify](https://contentcredentials.org/verify).

## What SocialForge does NOT do (and why you still need a human-in-the-loop)

- **It does not generate the visible deepfake overlay automatically.** If your asset is a deepfake (synthetic audio/image/video of a real person, object, place, or event), a human must apply a visible text label, watermark, or audio cue. The machine-readable C2PA manifest is necessary but not sufficient.
- **It does not provide legal certification.** Use of an open standard like C2PA is the *technical* mechanism. Whether your specific deployment satisfies Article 50 in your specific market is a legal question your counsel answers.
- **Self-signed dev certificates do not verify in production.** The script generates a 90-day self-signed cert when no production cert is supplied — this signs successfully but verifies as "signer not in trust list". Production deployment REQUIRES a certificate from a CAI-recognized authority (Adobe, Truepic, Numbers Protocol, Microsoft Azure Confidential Ledger).

## Quick reference

| Scenario | What to do |
|---|---|
| Generating AI image for an EU campaign | `generate_image.py --c2pa-sign --brand "X" --platform <p>` OR enable `c2pa_auto_sign: true` in brand profile |
| Generating AI video for an EU campaign | `video_postprocess.py --c2pa-sign --c2pa-generator "..."` (signs each per-platform output) |
| Signing an already-generated asset retroactively | `/socialforge:c2pa-sign --input <path> --output <signed_path> --brand "X" --generator "..." --platform <p>` |
| Asset is a deepfake | C2PA manifest + visible disclosure overlay (human-added) + brand-side legal sign-off |
| Asset is for a non-EU market | C2PA signing optional; check local regulations (NY synthetic-performer law June 2026, FTC May 2026 endorsement guidance, etc.) |

## Related references

- [EU AI Act Article 50 official text](https://artificialintelligenceact.eu/article/50/)
- [C2PA Specification v2.0](https://c2pa.org/specifications/specifications/2.0/specs/C2PA_Specification.html)
- [Content Authenticity Initiative — Signing manifests](https://opensource.contentauthenticity.org/docs/manifest/signing-manifests/)
- [Bria.ai — Article 50 enterprise guide](https://bria.ai/blog/article-50-of-the-eu-ai-act-what-enterprises-need-to-change-before-august-2-2026)
- DMP `skills/context-engine/compliance-rules.md` Section 1.1b (jurisdictional rule pack)
