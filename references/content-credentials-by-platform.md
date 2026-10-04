# Content Credentials (C2PA) by platform — who reads them, who shows them, who drops them

**Checked 2026-10-04.** Every platform claim below carries a source grade:

- **[P] Primary** — the platform's or standard body's own page, opened and read on 2026-10-04.
- **[S] Secondary only** — a news or trade article, or a search-engine excerpt of the platform's page. Treat as "reported", and test before you promise a client anything.
- **[?] Not researched** — no source opened, so no claim is made.

`scripts/c2pa_sign.py` writes the manifest; this file says what each platform does with it afterwards. For *what* to sign and *why* (EU AI Act Article 50, certificates), see `references/eu-ai-act-article50.md` and `references/c2pa-production-cert.md`. Platform behavior changes without notice — re-check before relying on any row.

## At a glance

| Platform | Reads a manifest on upload | What viewers see | Source |
|---|---|---|---|
| **YouTube** | Yes — at least for the "fully generative" case below | A prominent AI label (under the player for long-form, an overlay on Shorts). **Permanent** — the creator cannot remove it — when C2PA metadata indicates fully generative AI | [P] |
| **Facebook, Instagram, Threads** (Meta) | Yes — C2PA and IPTC "AI generated" indicators | An "AI info" label; for content only *edited* with AI the label sits in the post's menu | [P], but dated 2024 and not re-confirmed for 2026 |
| **TikTok** | Reported yes — automatic AI label for content uploaded with Content Credentials | An AI-generated label | [S] |
| **LinkedIn** | Reported yes, for images | A small "CR" icon; clicking shows who made it, when, and with what tools | [S] |
| **Google Ads** | Not a C2PA feature. The page does not mention C2PA, Content Credentials, metadata or SynthID | An AI label that the advertiser adds, or the "AI label setting" | [P] |
| X, Pinterest, Snapchat, Bluesky, others | — | — | [?] |

## YouTube [P]

Source: YouTube Team, "Improving AI labels for viewers and creators", 2026-05-27 — https://blog.youtube/news-and-events/improving-ai-labels-viewers-creators/ (checked 2026-10-04).

- Label placement: "For Long-form Videos: The label will now appear directly below the video player, above the description." "For Shorts: The label will appear as an overlay on the video itself."
- Automatic application: "If a creator doesn't specify whether or not they used AI, but our systems detect significant photorealistic AI use, we will now automatically apply a label."
- Permanence: "However, disclosures will remain permanent in a handful of cases, including:" (a) "Content created using YouTube's own AI tools, like Veo or Dream Screen." and (b) "Content containing C2PA metadata indicating they were fully generative AI."
- Outside the permanent cases: "If a creator thinks their content was incorrectly identified as AI-generated, they can update the disclosure status in YouTube Studio."
- Reach: "a disclosure label alone does not change how a video is recommended or whether it's eligible to earn money."

What that means for SocialForge output (an inference, not something YouTube states): a video that `c2pa_sign.py` signs with `ai-generated-content` — the claim for fully generated output, i.e. `PURE_CREATIVE` — is the manifest most likely to meet "fully generative AI", so plan for a permanent label on it. Do not downgrade the claim to dodge the label. `ai-assisted-edits` is the honest claim for a brand asset that AI only extended (ANCHOR_COMPOSE, ENHANCE_EXTEND), and whether YouTube treats that as "fully generative" is not stated. Check with an unlisted test upload before the month ships.

Also from YouTube's help page for its own tools (https://support.google.com/youtube/answer/15627549, checked 2026-10-04): content made with YouTube's AI tools gets a C2PA manifest, and "that platform can access this metadata" when you share it elsewhere. The page does not describe how YouTube treats manifests on ordinary uploads.

## Meta — Facebook, Instagram, Threads [P, dated]

Sources (both checked 2026-10-04):

- "Labeling AI-Generated Images on Facebook, Instagram and Threads", 2024-02-06, updated 2025-04-01 — https://about.fb.com/news/2024/02/labeling-ai-generated-images-on-facebook-instagram-and-threads/ . Meta says it is "building industry-leading tools that can identify invisible markers at scale – specifically, the 'AI generated' information in the C2PA and IPTC technical standards," and will "label images that users post to Facebook, Instagram and Threads when we can detect industry standard indicators that they are AI-generated." At that date video and audio were not detectable, so Meta asked people to disclose.
- "Our Approach to Labeling AI-Generated Content and Manipulated Media", 2024-04-05 with later update notes — https://about.fb.com/news/2024/04/metas-approach-to-labeling-ai-generated-content-and-manipulated-media/ . The "Made with AI" label is "based on our detection of industry-shared signals of AI images or people self-disclosing"; it was renamed "AI info" on 2024-07-01; on 2024-09-12 Meta moved the label to the post's menu "for content that we detect was only modified or edited by AI tools".

Not confirmed: whether those 2024 statements still describe current behavior in 2026, and which video formats are covered today. No newer Meta primary statement was found.

## TikTok [S]

- NBC News, 2024-05-09 — https://www.nbcnews.com/tech/tech-news/tiktok-will-automatically-label-ai-generated-content-rcna151446 : TikTok "will begin automatically labeling artificial intelligence-generated content (AIGC) uploaded from other platforms", and "will be attaching content credentials to AI-generated content created on the app in the coming months."
- TikTok's own announcement is at https://newsroom.tiktok.com/en-us/partnering-with-our-industry-to-advance-ai-transparency-and-literacy . It returned HTTP 503 to the fetcher on 2026-10-04, so it was NOT read directly; a search-engine excerpt of it said TikTok attaches Content Credentials to content made with its AI tools (retained on download) and adds invisible watermarks to such content and to uploads that carry Content Credentials. Treat that excerpt as secondary.

`references/channel-changes-may-2026.md` (an older file in this plugin) separately says TikTok requires an AI-creator disclosure and excludes AI content from its creator-rewards program. That file does not cite a source for those points, and this file did not verify them.

## LinkedIn [S]

- Digital Camera World, 2025-10-31 — https://www.digitalcameraworld.com/tech/social-media/new-linkedin-feature-helps-you-prove-authorship-of-your-photographs : LinkedIn shows a small icon on images posted with Content Credentials; "clicking it reveals who made the image, when it was created and what tools were used along the way." The credential has to be applied before upload — it is not created inside LinkedIn.
- Not confirmed: whether video is covered (the article's text is about images), and whether LinkedIn's delivered image still carries the signed manifest after its own re-encode. One secondary source claims LinkedIn strips manifests before publication while others describe it as displaying them; the two accounts have not been reconciled here. Run the test below.

## Google Ads [P] — an AI label, not a C2PA reader

Source: "Updates to AI labeling requirements (July 2026)" — https://support.google.com/adspolicy/answer/17257106 (checked 2026-10-04).

- "AI regulations in the European Union, India, and New York require that ads with certain AI-generated or edited assets include disclosures and/or labels that inform consumers that the ads were made with AI."
- "Advertisers can add these labels directly to their creatives or use the AI label setting, which will launch gradually throughout July in Google Ads, Display & Video 360, Campaign Manager 360, Merchant Center, and Ads Editor." "Google Ads may also automatically apply labels to certain assets generated by Google AI tools."
- "Use of the AI label setting in Google's advertising products doesn't guarantee compliance with specific regulations."
- The page **does not mention** C2PA, Content Credentials, metadata or SynthID. Do not tell a client that signing an ad creative satisfies, or triggers, Google's AI label — on this evidence the label is something the advertiser applies, either as visible text in the creative or through the setting.

## What to do with this in a SocialForge month

1. **Sign truthfully.** The claim in the manifest (`ai-generated-content`, `ai-assisted-edits`, `ai-no-substantive-changes`) must describe what happened. A permanent label on a fully generated asset is the platform doing its job, not a defect to engineer around.
2. **Treat the manifest as one layer.** It is machine-readable. Where a visible label is required (EU deepfake-class assets, ad AI-label rules), a human still adds it to the asset or sets the platform control. See `references/eu-ai-act-article50.md`.
3. **Keep the signed original.** Manifests can be removed: the C2PA explainer answers "Can it be removed?" with "Yes it can", and describes durable Content Credentials that add a soft binding (watermarking or fingerprinting) so a removed credential can be rediscovered (https://spec.c2pa.org/specifications/specifications/2.2/explainer/Explainer.html, [P], checked 2026-10-04). A platform that re-encodes on upload may not hand back the file you signed.
4. **Test per platform, once per brand.** Upload a signed test asset as private or unlisted, note what label (if any) the platform shows, download the published file and check it again in the Content Credentials verify tool (https://contentcredentials.org/verify). Record the outcome in the brand profile so the next month does not guess.
5. **Never promise survival.** Tell the client what the platform is documented to do, at which source grade, and what you tested.

## Source ledger

| Claim area | URL | Grade | Checked |
|---|---|---|---|
| YouTube labels and permanence | https://blog.youtube/news-and-events/improving-ai-labels-viewers-creators/ | P | 2026-10-04 |
| YouTube's own tools add C2PA | https://support.google.com/youtube/answer/15627549 | P | 2026-10-04 |
| Meta detection of C2PA/IPTC | https://about.fb.com/news/2024/02/labeling-ai-generated-images-on-facebook-instagram-and-threads/ | P (dated) | 2026-10-04 |
| Meta "AI info" label | https://about.fb.com/news/2024/04/metas-approach-to-labeling-ai-generated-content-and-manipulated-media/ | P (dated) | 2026-10-04 |
| TikTok automatic labeling | https://www.nbcnews.com/tech/tech-news/tiktok-will-automatically-label-ai-generated-content-rcna151446 | S | 2026-10-04 |
| TikTok announcement | https://newsroom.tiktok.com/en-us/partnering-with-our-industry-to-advance-ai-transparency-and-literacy | not readable (HTTP 503) | 2026-10-04 |
| LinkedIn CR icon | https://www.digitalcameraworld.com/tech/social-media/new-linkedin-feature-helps-you-prove-authorship-of-your-photographs | S | 2026-10-04 |
| Google Ads AI label | https://support.google.com/adspolicy/answer/17257106 | P | 2026-10-04 |
| C2PA manifest removal and durability | https://spec.c2pa.org/specifications/specifications/2.2/explainer/Explainer.html | P | 2026-10-04 |
