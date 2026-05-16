#!/usr/bin/env python3
"""
c2pa_sign.py
============
Embeds a C2PA (Coalition for Content Provenance and Authenticity) manifest
into a SocialForge-generated marketing asset (image / video / audio) so the
asset carries machine-readable provenance + a visible AI-generation claim.

This is the technical mechanism for EU AI Act Article 50 compliance
(applicable 2 Aug 2026; penalty up to EUR 15M or 3% global turnover for
generative-AI content distributed in EU markets without machine-readable
marking).

This script is self-contained — SocialForge does NOT depend on
digital-marketing-pro being installed. The signing logic mirrors DMP's
embed-c2pa.py exactly so an asset signed here verifies identically.

Usage (standalone):
    python3 c2pa_sign.py \
        --input path/to/generated.png \
        --output path/to/signed.png \
        --brand "Acme Corp" \
        --generator "Vertex AI Nano Banana Pro" \
        --ai-claim ai-generated-content \
        [--prompt "the prompt used"] \
        [--platform tiktok|instagram|linkedin|meta|youtube|x] \
        [--signing-cert /path/cert.pem --signing-key /path/key.pem]

Usage (auto-called from SocialForge pipeline):
    Set `c2pa_auto_sign: true` in brand-profile.json or pass
    --c2pa-sign on a generate_image / generate_video call. The pipeline
    calls this script as a finalization step.

Tested with c2pa-python 0.32.6 — uses the current Builder + Signer.from_info
API. Empirically verified end-to-end as part of DMP v3.4.1.

Exit codes:
    0  success
    2  c2pa-python install failed
    3  unsupported asset format
    4  signing failure
    5  invalid arguments
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SUPPORTED_FORMATS = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".tiff": "image/tiff",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
}

AI_CLAIM_TO_C2PA_TYPE = {
    "ai-generated-content":      "TRAINED_ALGORITHMIC_MEDIA",
    "ai-assisted-edits":         "COMPOSITE_WITH_TRAINED_ALGORITHMIC_MEDIA",
    "ai-no-substantive-changes": "HUMAN_EDITS",
}


def ensure_c2pa():
    try:
        import c2pa
        return c2pa
    except ImportError:
        pass
    print("Installing c2pa-python...", file=sys.stderr)
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "c2pa-python>=0.32"]
        )
        import c2pa
        return c2pa
    except Exception as exc:
        print(f"ERROR: could not install c2pa-python: {exc}", file=sys.stderr)
        sys.exit(2)


def build_manifest(brand, generator, ai_claim, created, prompt, platform, asset_format):
    actions = [
        {
            "action": "c2pa.created",
            "when": created,
            "softwareAgent": {
                "name": generator,
                "version": "1.0",
            },
        }
    ]
    if prompt:
        actions.append({
            "action": "c2pa.opened",
            "when": created,
            "parameters": {"description": f"Source prompt: {prompt}"},
        })
    if platform:
        actions.append({
            "action": "c2pa.published",
            "when": created,
            "parameters": {"description": f"Target platform: {platform}"},
        })

    creative_work = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "author": [{"@type": "Organization", "name": brand}],
        "dateCreated": created,
    }
    if platform:
        creative_work["publishingPrinciples"] = f"Distributed via SocialForge to {platform}"

    return {
        "claim_generator_info": [{
            "name": "SocialForge",
            "version": "1.6.0",
        }],
        "title": f"{brand} — AI-generated social asset",
        "format": SUPPORTED_FORMATS[asset_format],
        "assertions": [
            {"label": "c2pa.actions.v2", "data": {"actions": actions}},
            {"label": "stds.schema-org.CreativeWork", "data": creative_work},
        ],
    }


def generate_self_signed_cert(tmp_dir):
    """C2PA-conformant self-signed cert (DEV ONLY).

    C2PA enforces specific cert extensions per the spec — without them
    the library rejects with 'the certificate is invalid'. See DMP's
    embed-c2pa.py for the same logic.
    """
    from cryptography import x509
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from datetime import timedelta

    key = ec.generate_private_key(ec.SECP256R1())
    public_key = key.public_key()
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "SocialForge Dev Self-Signed C2PA"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SocialForge"),
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=90))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=False,
                crl_sign=False, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.EMAIL_PROTECTION]), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(public_key), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(public_key), critical=False)
        .sign(key, hashes.SHA256())
    )
    cert_path = Path(tmp_dir) / "sf-dev-c2pa-cert.pem"
    key_path = Path(tmp_dir) / "sf-dev-c2pa-key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return str(cert_path), str(key_path)


def sign_asset(in_path, out_path, brand, generator, ai_claim, prompt=None, platform=None,
               signing_cert=None, signing_key=None, created=None):
    """Programmatic entry point for SocialForge pipeline integration.
    Returns the result dict (or raises on failure)."""
    in_path = Path(in_path)
    out_path = Path(out_path)
    if not in_path.exists():
        raise FileNotFoundError(f"input not found: {in_path}")
    ext = in_path.suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        raise ValueError(f"unsupported format {ext}; supported: {sorted(SUPPORTED_FORMATS)}")

    created = created or datetime.now(timezone.utc).isoformat()
    manifest = build_manifest(brand, generator, ai_claim, created, prompt, platform, ext)
    c2pa = ensure_c2pa()

    using_dev_cert = False
    if not (signing_cert and signing_key):
        import tempfile
        tmpdir = tempfile.mkdtemp(prefix="sf-c2pa-")
        signing_cert, signing_key = generate_self_signed_cert(tmpdir)
        using_dev_cert = True

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cert_bytes = open(signing_cert, "rb").read()
    key_bytes = open(signing_key, "rb").read()

    signer_info = c2pa.C2paSignerInfo(
        alg=b"es256", sign_cert=cert_bytes, private_key=key_bytes,
        ta_url=b"http://timestamp.digicert.com",
    )
    signer = c2pa.Signer.from_info(signer_info)
    builder = c2pa.Builder(manifest)
    ds_type_name = AI_CLAIM_TO_C2PA_TYPE[ai_claim]
    ds_type = getattr(c2pa.C2paDigitalSourceType, ds_type_name)
    try:
        builder.set_intent(c2pa.C2paBuilderIntent.CREATE, ds_type)
    except Exception as exc:
        print(f"NOTE: set_intent failed ({exc}); proceeding", file=sys.stderr)
    builder.sign_file(str(in_path), str(out_path), signer=signer)

    # Round-trip verify
    manifest_present = False
    active_id = None
    try:
        with open(out_path, "rb") as fh:
            with c2pa.Reader(SUPPORTED_FORMATS[ext], fh) as reader:
                m = json.loads(reader.json())
                manifest_present = bool(m.get("active_manifest"))
                active_id = m.get("active_manifest")
    except Exception as exc:
        print(f"NOTE: read-back failed ({exc})", file=sys.stderr)

    return {
        "status": "success",
        "input": str(in_path),
        "output": str(out_path),
        "size_bytes": out_path.stat().st_size,
        "brand": brand,
        "generator": generator,
        "ai_claim": ai_claim,
        "c2pa_digital_source_type": ds_type_name,
        "platform": platform,
        "created": created,
        "manifest_embedded_and_verified": manifest_present,
        "c2pa_active_manifest_id": active_id,
        "using_dev_cert": using_dev_cert,
        "verify_url": "https://contentcredentials.org/verify",
    }


def main():
    parser = argparse.ArgumentParser(description="Embed a C2PA manifest in a SocialForge AI-generated asset.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--brand", required=True)
    parser.add_argument("--generator", required=True, help='e.g. "Vertex AI Nano Banana Pro", "WaveSpeed Kling v3.0 Pro"')
    parser.add_argument("--ai-claim", default="ai-generated-content", choices=sorted(AI_CLAIM_TO_C2PA_TYPE.keys()))
    parser.add_argument("--created", help="ISO-8601 timestamp (default: now)")
    parser.add_argument("--prompt", help="Generation prompt (optional)")
    parser.add_argument("--platform", help="Target social platform (tiktok / instagram / linkedin / meta / youtube / x / threads)")
    parser.add_argument("--signing-cert", help="PEM cert (omit for dev self-signed)")
    parser.add_argument("--signing-key", help="PEM key (must accompany --signing-cert)")
    args = parser.parse_args()

    try:
        result = sign_asset(
            in_path=args.input, out_path=args.output,
            brand=args.brand, generator=args.generator,
            ai_claim=args.ai_claim, prompt=args.prompt, platform=args.platform,
            signing_cert=args.signing_cert, signing_key=args.signing_key,
            created=args.created,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(5)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(3)
    except Exception as exc:
        print(f"ERROR: C2PA signing failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(4)

    if result.get("using_dev_cert"):
        result["warning"] = (
            "Signed with self-signed dev cert (90-day validity). "
            "PRODUCTION USE REQUIRES a real signing certificate from a CAI-recognized authority."
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
