# C2PA Production Signing Certificate

Everything a SocialForge operator needs to move from the dev-only self-signed path to a production signing certificate.

## TL;DR

`scripts/c2pa_sign.py` ships with a dev-only path that auto-generates a 90-day self-signed certificate. Production deployment requires a certificate from a **CAI-recognized signing authority**. Without one, signed assets verify as "signer not in trust list" at contentcredentials.org/verify and won't pass EU AI Act Article 50 review.

## Four recognized authorities (July 2026)

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
    --prompt "..." --output asset.png --model gemini-3-pro-image \
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

## Production key management

- **Storage.** Keep the private key in a secret manager, never on a developer laptop and never in the brand workspace. Mount it into the run at execution time and pass the mounted path via `--signing-key` / `--c2pa-signing-key`.
- **Permissions.** `chmod 600` on the key file wherever it lands. Restrict read access to the service account that runs the generation pipeline.
- **Separation.** Use a distinct cert per brand if you sign on behalf of multiple clients — the manifest carries the signer identity, and a shared cert makes one client's provenance indistinguishable from another's.
- **Rotation + revocation.** Diary the expiry (most CAI certs are 1-year). Assets signed before a revocation stay valid if the CA supports timestamping; ask your authority to enable RFC 3161 timestamping so a later revocation does not invalidate historical manifests.
- **Audit.** Log every signing run (asset, brand, generator, platform, timestamp). `scripts/c2pa_sign.py` prints a JSON record per run — persist it alongside the month's cost log.

## Verification testing

After the first production sign, confirm the chain actually resolves:

1. Upload the signed asset to [contentcredentials.org/verify](https://contentcredentials.org/verify).
2. Confirm the signer name matches your organization and there is **no** "signer not in trust list" warning. A self-signed dev cert always trips that warning — that is the signal you are still on the dev path.
3. Confirm the recorded fields survived: brand (`CreativeWork.author`), generator name, prompt, target platform, timestamp, and the IPTC digital-source-type tag.
4. Re-verify after your platform pipeline (re-encode, resize, format conversion). Some platforms strip metadata on upload; if the manifest is lost, keep the signed original as the durable provenance record and note the stripping platform in the brand profile.
5. Re-run this check after every certificate rotation.

## Deepfake visible-disclosure caveat

A C2PA manifest is machine-readable marking only. If the asset is synthetic audio, image, or video resembling a real person, object, place, or event, EU AI Act Article 50 additionally requires a **visible** disclosure — a text overlay, watermark, or audio cue. SocialForge does not generate that overlay automatically; a human must add it before delivery. Signing alone is necessary but not sufficient for deepfakes.

## Editorial-responsibility note

AI-generated **text** on matters of public interest must be disclosed unless it was human-reviewed and the brand assumes full editorial responsibility for it. That is a brand-side decision, not a signing-pipeline one: if you rely on the editorial-responsibility route, record who reviewed the copy and when. The C2PA manifest documents how the asset was made — it does not by itself establish that a human took editorial responsibility for the claims in it.

## Timeline

EU AI Act Article 50 applies from **2 August 2026**. The final Code of Practice on Transparency of AI-Generated Content was published **10 June 2026** (superseding the earlier drafts), along with the standardized EU disclosure icons. The initial-signatory window closed **22 July 2026**.

Apply for a production certificate before you need it — Adobe is typically 1–5 business days; Truepic onboarding is faster.
