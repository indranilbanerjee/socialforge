# C2PA Production Signing Certificate

**Master guide:** lives in the DMP repo at `digital-marketing-pro/docs/c2pa-production-cert-guide.md` — read that first.
**Short version for SocialForge users below.**

## TL;DR

`scripts/c2pa_sign.py` ships with a dev-only path that auto-generates a 90-day self-signed certificate. Production deployment requires a certificate from a **CAI-recognized signing authority**. Without one, signed assets verify as "signer not in trust list" at contentcredentials.org/verify and won't pass EU AI Act Article 50 review.

## Four recognized authorities (May 2026)

| Option | Best for | Cost |
|---|---|---|
| **Adobe Content Credentials** | Brands on Creative Cloud | Free basic identity in Creative Cloud; partner / API-signing certificates via the Content Authenticity Initiative — start at https://contentauthenticity.org/ and use the open-source `c2patool` CLI documented at https://opensource.contentauthenticity.org/docs/c2patool/ |
| **Truepic** | High-volume API-first signing (SocialForge production pipelines) | Tiered SaaS — contact for quote |
| **Numbers Protocol** | Brands wanting on-chain anchoring | Free tier exists |
| **Microsoft Azure Confidential Ledger** | Azure shops with KMS policy | Azure consumption pricing |

## Using a production cert with SocialForge

```bash
# Direct sign
python3 scripts/c2pa_sign.py \
    --input asset.png --output signed.png \
    --brand "Acme Corp" --generator "Vertex AI Nano Banana Pro" \
    --ai-claim ai-generated-content --platform instagram \
    --signing-cert /secure/c2pa-prod-cert.pem \
    --signing-key /secure/c2pa-prod-key.pem

# Auto-sign via image generation hook
python3 scripts/generate_image.py \
    --prompt "..." --output asset.png --model gemini-3-pro-image-preview \
    --c2pa-sign --brand "Acme Corp" --platform instagram \
    --c2pa-signing-cert /secure/c2pa-prod-cert.pem \
    --c2pa-signing-key /secure/c2pa-prod-key.pem

# Auto-sign every per-platform video output
python3 scripts/video_postprocess.py \
    --input source.mp4 --output-dir processed/ --brand acme-corp \
    --c2pa-sign \
    --c2pa-generator "WaveSpeed Kling v3.0 Pro" \
    --c2pa-signing-cert /secure/c2pa-prod-cert.pem \
    --c2pa-signing-key /secure/c2pa-prod-key.pem
```

## Key handling rules

1. Never commit cert + key to git
2. Don't bake the path into agent files
3. Use a secret store for team environments (Vault / AWS Secrets / GCP Secret Manager / Azure Key Vault)
4. Rotate annually (most CAI certs are 1-year)
5. Revoke immediately if compromised

## Timeline

EU AI Act Article 50 enforcement: **2 August 2026** (~76 days from 17 May 2026). Start the application this week — Adobe is typically 1–5 business days; Truepic onboarding is faster.

## Full reference

See `digital-marketing-pro/docs/c2pa-production-cert-guide.md` for the detailed walkthrough, verification testing, deepfake disclosure caveats, and editorial-responsibility claim discussion.
