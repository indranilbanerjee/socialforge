#!/usr/bin/env python3
"""
generate_image.py — AI image generation via Google Vertex AI (Gemini).

Uses the unified google-genai SDK. Supports Vertex AI (production) with
AI Studio fallback. Reference images supported for style-guided generation.

Model selection: pass --model to override. Defaults pull from the curator
(scripts/model_registry.json) via the `latest-image-balanced-google` alias,
so a registry refresh propagates without touching this file. Run
`python scripts/resolve_model.py --list --modality image-gen` to see what's
available; `python scripts/resolve_model.py --check <id>` to validate one.

Setup (Vertex AI — recommended):
    1. gcloud services enable aiplatform.googleapis.com
    2. gcloud auth application-default login
    3. export GOOGLE_CLOUD_PROJECT=your-project-id
    4. export GOOGLE_CLOUD_LOCATION=us-central1
    5. pip install google-genai Pillow

Setup (AI Studio — fallback):
    export GEMINI_API_KEY=your-key
    pip install google-genai Pillow
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
if _plugin_data and Path(_plugin_data).exists():
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
    WORKSPACE = Path.home() / "socialforge-workspace"

# Add scripts dir to path for credential_manager + curator imports
sys.path.insert(0, str(Path(__file__).parent))

# Resolve default via the model curator (auto-updates as registry is refreshed)
try:
    from resolve_model import resolve as _resolve_model, check as _check_model
    DEFAULT_MODEL = _resolve_model("latest-image-balanced-google")
except (ImportError, KeyError, ValueError):  # pragma: no cover — fallback if curator missing
    _resolve_model = None
    _check_model = None
    DEFAULT_MODEL = "gemini-2.5-flash-image"


def _negotiate_model(user_value: str | None, alias: str) -> str:
    """If --model was supplied, validate via curator and warn on deprecation.
    Otherwise return the alias-resolved id."""
    if _resolve_model is None or _check_model is None:
        return user_value or alias  # curator unavailable, trust caller
    if user_value:
        status, replacement = _check_model(user_value)
        if status == "deprecated" and replacement:
            print(f"WARNING: model {user_value!r} is deprecated; using {replacement!r}", file=sys.stderr)
            return replacement
        if status == "unknown":
            print(f"WARNING: model {user_value!r} is not in the curated registry — proceeding without safety net", file=sys.stderr)
        return user_value
    return _resolve_model(alias)


def create_client():
    """Create a google-genai client via credential_manager (Vertex AI > env vars > AI Studio)."""
    try:
        from credential_manager import get_gemini_client
        client, backend = get_gemini_client()
        if client:
            return client, backend, None
        else:
            return None, None, backend  # backend contains error message when client is None
    except ImportError:
        # Fallback if credential_manager not available
        try:
            from google import genai
        except ImportError:
            try:
                from install_deps import ensure_package
                if ensure_package("google-genai"):
                    from google import genai
                else:
                    return None, None, "google-genai install failed. Run: pip install google-genai"
            except (ImportError, Exception):
                return None, None, "google-genai not installed. Run: pip install google-genai"

        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        api_key = os.environ.get("GEMINI_API_KEY")
        if project:
            try:
                client = genai.Client(vertexai=True, project=project,
                                      location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"))
                return client, "vertex-env", None
            except Exception:
                pass
        if api_key:
            try:
                return genai.Client(api_key=api_key), "aistudio", None
            except Exception as e:
                return None, None, f"AI Studio init failed: {e}"

        return None, None, "No credentials. Run /socialforge:setup or set GOOGLE_CLOUD_PROJECT."


def generate_image(prompt, output_path, reference_images=None, aspect_ratio="1:1", model=DEFAULT_MODEL):
    """Generate an image using Gemini via Vertex AI or AI Studio."""
    from google.genai import types

    client, backend, error = create_client()
    if error:
        return {"status": "FAILED", "error": error, "action_required": True}

    # Build content parts
    contents = []

    # Add reference images for style-guided generation
    if reference_images:
        for ref_path in reference_images[:14]:
            ref_file = Path(ref_path)
            if not ref_file.exists():
                continue
            img_bytes = ref_file.read_bytes()
            mime = "image/jpeg" if ref_file.suffix.lower() in (".jpg", ".jpeg") else "image/png"
            contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))

    contents.append(prompt)

    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        for part in response.parts:
            if part.inline_data is not None:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                try:
                    image = part.as_image()
                    image.save(output_path)
                except (AttributeError, TypeError):
                    import base64
                    img_bytes = base64.b64decode(part.inline_data.data) if isinstance(part.inline_data.data, str) else part.inline_data.data
                    Path(output_path).write_bytes(img_bytes)
                return {
                    "status": "success",
                    "provider": f"gemini-{backend}",
                    "model": model,
                    "output": str(output_path),
                    "aspect_ratio": aspect_ratio,
                    "references_used": len(reference_images) if reference_images else 0,
                }

        text_resp = ""
        for part in response.parts:
            if part.text:
                text_resp += part.text
        return {"status": "FAILED", "error": "No image in response", "text_response": text_resp}

    except Exception as e:
        primary_error = str(e)
        ws_result = generate_image_wavespeed(prompt, output_path, reference_images, aspect_ratio)
        if ws_result:
            ws_result["fallback_from"] = "vertex-ai"
            return ws_result
        hf_result = generate_image_higgsfield(prompt, output_path, aspect_ratio)
        if hf_result:
            hf_result["fallback_from"] = "vertex-ai+wavespeed"
            return hf_result
        return {"status": "FAILED", "error": f"All providers failed. Primary: {primary_error[:100]}", "action_required": True}


def generate_image_wavespeed(prompt, output_path, reference_images=None, aspect_ratio="1:1"):
    """Fallback: Generate image via WaveSpeed (Nano Banana models)."""
    try:
        from credential_manager import get_wavespeed_key
        ws_key = get_wavespeed_key()
    except ImportError:
        ws_key = os.environ.get("WAVESPEED_API_KEY")
    if not ws_key:
        return None
    try:
        from wavespeed import Client as WsClient
        client = WsClient(api_key=ws_key)
        payload = {"prompt": prompt, "aspect_ratio": aspect_ratio}
        output = client.run("kwaivgi/kling-image-v3/text-to-image", payload, timeout=120.0, poll_interval=3.0)
        img_url = output.get("outputs", [None])[0]
        if img_url:
            import urllib.request
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(img_url, output_path)
            return {"status": "success", "provider": "wavespeed-nanobanana", "output": str(output_path)}
    except Exception:
        pass
    return None


def generate_image_higgsfield(prompt, output_path, aspect_ratio="1:1"):
    """Fallback: Generate image via HiggsField (Soul / Nano Banana Pro)."""
    try:
        from credential_manager import get_higgsfield_auth
        api_key, api_secret = get_higgsfield_auth()
    except ImportError:
        api_key, api_secret = os.environ.get("HF_API_KEY"), os.environ.get("HF_API_SECRET")
    if not api_key or not api_secret:
        return None
    try:
        import requests as req
        import time as _time
        headers = {"Authorization": f"Key {api_key}:{api_secret}", "Content-Type": "application/json"}
        resp = req.post("https://platform.higgsfield.ai/higgsfield/soul-v2/text-to-image",
                       headers=headers, json={"prompt": prompt, "aspect_ratio": aspect_ratio}, timeout=30)
        if resp.status_code != 200:
            return None
        request_id = resp.json().get("request_id")
        for _ in range(60):
            _time.sleep(3)
            st = req.get(f"https://platform.higgsfield.ai/requests/{request_id}/status", headers=headers, timeout=15).json()
            if st.get("status") == "completed":
                img_url = st.get("image", {}).get("url") or (st.get("outputs", [None]) or [None])[0]
                if img_url:
                    import urllib.request
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    urllib.request.urlretrieve(img_url, output_path)
                    return {"status": "success", "provider": "higgsfield-soul", "output": str(output_path)}
            elif st.get("status") in ("failed", "nsfw"):
                return None
    except Exception:
        pass
    return None


def edit_image(image_path, edit_prompt, output_path, model=DEFAULT_MODEL):
    """Edit an existing image using Gemini's conversational editing."""
    from PIL import Image as PILImage

    client, backend, error = create_client()
    if error:
        return {"status": "FAILED", "error": error, "action_required": True}

    try:
        source = PILImage.open(image_path)
        chat = client.chats.create(model=model)
        response = chat.send_message([edit_prompt, source])

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                edited = part.as_image()
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                edited.save(output_path, format="PNG")
                return {
                    "status": "success",
                    "provider": f"gemini-{backend}",
                    "model": model,
                    "output": str(output_path),
                }

        return {"status": "FAILED", "error": "No image in edit response"}

    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


def generate_placeholder(prompt, output_path, width=1080, height=1080):
    """Generate a placeholder image — only when explicitly requested by user."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        try:
            from install_deps import ensure_package
            if ensure_package("Pillow"):
                from PIL import Image, ImageDraw, ImageFont
            else:
                return {"error": "Pillow install failed. Run: pip install Pillow"}
        except (ImportError, Exception):
            return {"error": "Pillow not installed. Run: pip install Pillow"}

    img = Image.new("RGB", (width, height), (240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(10, 10), (width - 10, height - 10)], outline=(200, 200, 200), width=2)
    text = f"[AI Image Placeholder]\n\n{prompt[:100]}..."
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except (IOError, OSError):
        font = ImageFont.load_default()
    draw.text((width // 2, height // 2), text, fill=(150, 150, 150), font=font, anchor="mm")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=95)
    return {
        "status": "placeholder",
        "provider": "pillow_placeholder",
        "output": str(output_path),
        "warning": "Placeholder only — not a real image. Replace before publishing."
    }


def _maybe_c2pa_sign(result, args):
    """If --c2pa-sign is on, embed a C2PA provenance manifest in the output
    asset (EU AI Act Article 50 compliance). Replaces the file in place so
    the caller's --output contract stays the same. Non-fatal on failure —
    the unsigned generated asset is left on disk and c2pa_error is recorded.
    """
    if not args.c2pa_sign or not args.brand or result.get("status") != "success":
        return result
    out_path = Path(args.output)
    if not out_path.exists():
        return result
    # Import c2pa_sign as a sibling module
    scripts_dir = Path(__file__).parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from c2pa_sign import sign_asset
        tmp_signed = out_path.with_suffix(".c2pa-tmp" + out_path.suffix)
        generator_name = f"{result.get('provider', 'unknown')} / {result.get('model', args.model)}"
        sign_result = sign_asset(
            in_path=str(out_path), out_path=str(tmp_signed),
            brand=args.brand, generator=generator_name,
            ai_claim="ai-generated-content",
            prompt=args.prompt, platform=args.platform,
            signing_cert=args.c2pa_signing_cert, signing_key=args.c2pa_signing_key,
        )
        out_path.unlink()
        tmp_signed.rename(out_path)
        result["c2pa_signed"] = True
        result["c2pa_active_manifest_id"] = sign_result.get("c2pa_active_manifest_id")
        result["c2pa_using_dev_cert"] = sign_result.get("using_dev_cert", False)
    except Exception as exc:
        result["c2pa_signed"] = False
        result["c2pa_error"] = f"{type(exc).__name__}: {exc}"
    return result


def main():
    parser = argparse.ArgumentParser(description="SocialForge Image Generator (Vertex AI + AI Studio)")
    parser.add_argument("--prompt", required=False, default="", help="Text prompt for image generation (required unless --list-models)")
    parser.add_argument("--output", required=False, default="", help="Output file path (required unless --list-models)")
    parser.add_argument("--references", nargs="*", default=None, help="Style reference image paths (max 14)")
    parser.add_argument("--model", default=None,
                        help=f"Image model id (default: registry alias `latest-image-balanced-google` -> {DEFAULT_MODEL}). "
                             f"Run `python scripts/resolve_model.py --list --modality image-gen` to see options. "
                             f"Deprecated ids auto-fall-forward to their replacement.")
    parser.add_argument("--list-models", action="store_true",
                        help="Print the curated image-generation models and exit")
    parser.add_argument("--aspect-ratio", default="1:1", choices=["1:1", "16:9", "9:16", "4:3", "3:4", "4:5"],
                        help="Output aspect ratio")
    parser.add_argument("--edit", default=None, help="Source image path for editing mode")
    parser.add_argument("--placeholder", action="store_true", help="Generate placeholder only (no AI)")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1080)
    # v1.6 — EU AI Act Article 50 compliance: optional C2PA provenance signing
    parser.add_argument("--c2pa-sign", action="store_true",
                        help="Embed C2PA provenance manifest in the output asset (EU AI Act Article 50 compliance). Requires --brand.")
    parser.add_argument("--brand", default=None,
                        help="Brand name for C2PA CreativeWork.author (required with --c2pa-sign)")
    parser.add_argument("--platform", default=None,
                        help="Target social platform for C2PA c2pa.published action: tiktok / instagram / linkedin / meta / youtube / x / threads")
    parser.add_argument("--c2pa-signing-cert", default=None,
                        help="PEM signing certificate (omit for dev 90-day self-signed cert; production use REQUIRES a real CAI-recognized cert)")
    parser.add_argument("--c2pa-signing-key", default=None,
                        help="PEM signing key (must accompany --c2pa-signing-cert)")
    args = parser.parse_args()

    if args.list_models:
        if _resolve_model is None:
            print("Model curator not available", file=sys.stderr)
            sys.exit(2)
        from resolve_model import list_models as _ll, get_registry as _gr
        reg = _gr()
        print(f"Image-generation models (registry last_updated: {reg.get('last_updated')})")
        for m in _ll(modality="image-gen", status="current"):
            print(f"  {m['id']:55s}  {m.get('vendor', '?'):10s}  {m.get('display_name', '')}")
        return

    if not args.prompt or not args.output:
        parser.error("--prompt and --output are required (unless --list-models is set)")

    # Resolve --model via curator (auto-falls-forward if user passed a deprecated id)
    model_id = _negotiate_model(args.model, "latest-image-balanced-google")

    # Some image flows need a higher-fidelity model for edits — prefer Pro when --edit is set
    if args.edit and not args.model and _resolve_model is not None:
        try:
            model_id = _resolve_model("latest-image-edit-google")
        except (KeyError, ValueError):
            pass  # fall back to balanced default

    if args.placeholder:
        result = generate_placeholder(args.prompt, args.output, args.width, args.height)
    elif args.edit:
        result = edit_image(args.edit, args.prompt, args.output, model_id)
    else:
        result = generate_image(args.prompt, args.output, args.references, args.aspect_ratio, model_id)

    # Optional: embed C2PA provenance manifest (EU AI Act Article 50)
    # Pass the resolved model_id back through args so _maybe_c2pa_sign records the real id
    args.model = model_id
    result = _maybe_c2pa_sign(result, args)

    # Log
    log_dir = WORKSPACE / "shared" / "prompt-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "prompt": args.prompt,
        "output": args.output,
        "provider": result.get("provider", "unknown"),
        "model": result.get("model", model_id),
        "references": args.references,
        "result": result.get("status", "unknown"),
        "c2pa_signed": result.get("c2pa_signed", False),
    }
    log_file = log_dir / f"{datetime.utcnow().strftime('%Y-%m-%d')}-generation.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
