# Channel Changes — May 2026 Reference

Platform-by-platform changes that affect SocialForge content as of May 2026. The existing `references/platform-specs.md` covers dimensions, character limits, and posting mechanics; this file covers the **policy, algorithm, and structural** changes that override or qualify those mechanics.

## TikTok (post-USDS Joint Venture, Jan 22 2026)

- **Ownership structure:** TikTok USDS Joint Venture LLC. Oracle + Silver Lake + MGX hold ~45%; ByteDance retains <20%. US data and recommendation algorithm are under USDS control.
- **AI creator labeling (mandatory):** AI-generated creators ("synthetic creators") are allowed only with disclosure. AI-generated content is **excluded from the Creator Rewards Program**. SocialForge-generated assets posted as creator content should carry both the C2PA manifest AND a visible AI-generation label in the post copy.
- **Daily shoppable-post limits** effective 11 May 2026. Brands hitting the cap should rotate which products get featured each day rather than batch-posting all SKUs.
- **Platform-specific recommendation:** when `--platform tiktok` is passed to image/video generation, set `ai-claim: ai-generated-content` and include "Created with AI" or equivalent in the caption.

## LinkedIn (March 12 2026 algorithm announcement)

- **Relevance-based distribution** + **"Generative Recommenders"** (LLM-backed). Followers no longer guarantee reach.
- **Depth Score** measures engagement duration on post (dwell time, comment depth, profile-click-through). This is now the dominant ranking signal — more than reactions or impressions.
- **External links penalized ~60%** vs in-platform content. Posts that drive clicks off-platform now reach significantly fewer people. Best practice: lead with substance in-post; link in first comment OR in a follow-up post.
- **Engagement bait penalized ~60%.** "Comment YES if you agree" / "Tag someone who needs this" patterns now suppressed.
- **What changed for SocialForge:** the existing 3000-char limit / 140-before-fold guidance still holds. But the recommended content shape has shifted from "hook + link + hashtags" to "complete story in-post with optional discussion prompt at end". Carousel posts (multi-page PDF) are favored by the new algorithm for B2B because they generate higher dwell time.

## Instagram / Meta family

- **Apple Mail Privacy Protection (MPP)** affects ~64% of B2C email opens — **email open rate is functionally dead as a primary KPI**. This affects creators using Meta's email-driven flows (e.g. promo code distribution). Switch to click + conversion tracking.
- **Meta Advantage+ shopping campaigns:** in-app checkout, AI product overlays (price/reviews on hover), retailer integrations now standard. Ad creative should be designed to work AT the product-tile scale, not full-frame.
- **Threads:** organic distribution improving rapidly through 2026. Worth considering as a primary post channel for text-led B2B (separate from Instagram visuals).

## YouTube

- Ad-tier reach continues expanding (Netflix and Amazon Prime Video ad tiers now hold majority of their subs). Connected TV measurement is becoming standard via attention-based metrics rather than impressions.
- Shorts policy: AI-generated Shorts now require explicit labeling in the description (auto-detected by YouTube AI; failure to label triggers reduced distribution).

## X (formerly Twitter)

- **Algorithm transparency reports** now published quarterly. Posts with images get ~30% more engagement than text-only; posts with native video get ~80% more than image posts.
- **AI-generated post labeling:** voluntary as of May 2026 but X reserves the right to auto-label.

## Sora deprecation (cross-cutting)

- Consumer Sora app: **shut down 26 Apr 2026**
- Sora API: **shut down 24 Sep 2026**
- If your generation pipeline previously called Sora, migrate to **Runway Gen-4 / Gen-4.5**, **Veo 3.x**, or **Kling 3.0** before Sep 24 2026. SocialForge's default video generator is Kling v3.0 via WaveSpeed (no Sora dependency).

## Third-party cookies (deprecation cancelled)

- Chrome formally abandoned the 3P cookie deprecation timeline in 2024 and abandoned the choice-prompt plan in April 2025. **Privacy Sandbox APIs are being retired** (only CHIPS, FedCM, Private State Tokens kept).
- Safari and Firefox already block 3P cookies by default. Net: assume cookies persist in Chrome but are unreliable for cross-site identity. First-party data + MMM + incrementality is the modern measurement stack.

## What to update in your brand profile

- Add `c2pa_auto_sign: true` if any of your target platforms or jurisdictions are EU (or you want a defensible audit trail even outside EU).
- Add `ai_disclosure_required: true` for TikTok / YouTube / EU markets so the caption-adapter inserts the required visible label.
- Verify your TikTok account is post-USDS (US-resident accounts as of Q1 2026) — affects which API endpoint SocialForge connectors talk to.

## Related

- `references/platform-specs.md` — dimensional + character-limit specs (still current)
- `references/eu-ai-act-article50.md` — EU AI Act technical compliance
- `skills/c2pa-sign/SKILL.md` — provenance signing
- DMP `skills/context-engine/compliance-rules.md` Sections 1.1b (EU AI Act), 1.3 (CCPA ADMT), 1.11 (DPDP) — jurisdictional rules
