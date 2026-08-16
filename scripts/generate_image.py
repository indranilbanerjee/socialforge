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
from datetime import datetime, timezone
from pathlib import Path

_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("PLUGIN_DATA") or ""
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
    # Deliberately no hardcoded id — see model_book.resolve_for_execution. A
    # string here would always answer, and one day the answer is a retired model.
    DEFAULT_MODEL = None


def _resolve_execution_model(kind, provider, registry_alias=None):
    """Model id for a capability, discovered live where possible.

    Returns None rather than a guess when nothing can be resolved, so the caller
    falls through to the next provider instead of calling a model that may have
    been retired.
    """
    try:
        from model_book import resolve_for_execution
    except ImportError:
        return None
    result = resolve_for_execution(kind, provider, registry_alias)
    if result.get("warning"):
        print(f"NOTE: {result['warning']}", file=sys.stderr)
    elif result.get("action_required"):
        print(f"NOTE: {result['action_required']}", file=sys.stderr)
    return result.get("model_id")


def _negotiate_model(user_value: str | None, alias: str) -> str:
    """If --model was supplied, validate via curator and warn on deprecation.
    Otherwise return the alias-resolved id."""
    if _resolve_model is None or _check_model is None:
        # Curator unavailable: honour an explicit user id, but never hand the
        # alias string itself to the SDK as a model id.
        return user_value or None
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
            except Exception:
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
    """Generate an image via the provider chain: Gemini -> WaveSpeed -> HiggsField.

    Every rung that cannot run records WHY into `attempts` — a fully-failed
    chain reports what was tried and what to do next, never a bare failure.
    A missing Gemini credential no longer aborts the chain: a user with only
    a fallback provider's key still generates.
    """
    from provider_failures import record, failure_payload
    attempts = []

    client, backend, error = create_client()
    if error:
        record(attempts, "gemini", "credentials", "no-credentials", error)
    elif model is None:
        record(attempts, "gemini", "model-resolution", "unresolved-model",
               "no image model id could be resolved (curator missing and no --model given)")
    else:
        try:
            from google.genai import types

            # Build content parts (+ reference images for style-guided generation)
            contents = []
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
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )

            image_saved = False
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
                    image_saved = True
                    break
            if image_saved:
                return {
                    "status": "success",
                    "provider": f"gemini-{backend}",
                    "model": model,
                    "output": str(output_path),
                    "aspect_ratio": aspect_ratio,
                    "references_used": len(reference_images) if reference_images else 0,
                }

            text_resp = "".join(part.text for part in response.parts if part.text)
            record(attempts, f"gemini-{backend}", "response", "bad-response",
                   f"no image in response; text: {text_resp[:200]}" if text_resp else "no image in response")
        except ImportError as e:
            record(attempts, "gemini", "dependencies", "dependency-missing",
                   f"google-genai not importable: {e}")
        except Exception as e:
            record(attempts, f"gemini-{backend}", "request", "request-error", str(e))

    ws_result = generate_image_wavespeed(prompt, output_path, reference_images, aspect_ratio,
                                         attempts=attempts)
    if ws_result:
        ws_result["fallback_from"] = "vertex-ai"
        ws_result["earlier_attempts"] = attempts
        return ws_result
    hf_result = generate_image_higgsfield(prompt, output_path, aspect_ratio, attempts=attempts)
    if hf_result:
        hf_result["fallback_from"] = "vertex-ai+wavespeed"
        hf_result["earlier_attempts"] = attempts
        return hf_result
    return failure_payload(attempts, context="image generation")


def generate_image_wavespeed(prompt, output_path, reference_images=None, aspect_ratio="1:1",
                             attempts=None):
    """Fallback: Generate image via WaveSpeed. Records every abandoned attempt
    into `attempts` — a rung that cannot run says why, never a bare None."""
    from provider_failures import record
    try:
        from credential_manager import get_wavespeed_key
        ws_key = get_wavespeed_key()
    except ImportError:
        ws_key = os.environ.get("WAVESPEED_API_KEY")
    if not ws_key:
        record(attempts, "wavespeed", "credentials", "no-credentials",
               "WAVESPEED_API_KEY not set and no key in the credential profile")
        return None
    try:
        from wavespeed import Client as WsClient
    except ImportError as e:
        record(attempts, "wavespeed", "dependencies", "dependency-missing",
               f"wavespeed SDK not importable: {e}")
        return None
    try:
        client = WsClient(api_key=ws_key)
        payload = {"prompt": prompt, "aspect_ratio": aspect_ratio}
        # Ask for the KIND, not a product. This line used to name a specific
        # model version inline with no resolution at all, so it could only ever
        # be as current as the last release of this file.
        model_id = _resolve_execution_model("image.text-to-image", "wavespeed",
                                            "latest-image-wavespeed")
        if not model_id:
            record(attempts, "wavespeed", "model-resolution", "unresolved-model",
                   "no current model id for kind image.text-to-image on wavespeed")
            return None  # unresolved — caller falls through to the next provider
        output = client.run(model_id, payload, timeout=120.0, poll_interval=3.0)
        img_url = output.get("outputs", [None])[0]
        if img_url:
            import urllib.request
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(img_url, output_path)
            return {"status": "success", "provider": "wavespeed-kling-image-v3", "output": str(output_path)}
        record(attempts, "wavespeed", "response", "bad-response",
               "provider returned no output URL")
    except Exception as e:
        record(attempts, "wavespeed", "request", "request-error", str(e))
    return None


def generate_image_higgsfield(prompt, output_path, aspect_ratio="1:1", attempts=None):
    """Fallback: Generate image via HiggsField. Records every abandoned attempt
    into `attempts` — a rung that cannot run says why, never a bare None."""
    from provider_failures import record
    try:
        from credential_manager import get_higgsfield_auth
        api_key, api_secret = get_higgsfield_auth()
    except ImportError:
        api_key, api_secret = os.environ.get("HF_API_KEY"), os.environ.get("HF_API_SECRET")
    if not api_key or not api_secret:
        record(attempts, "higgsfield", "credentials", "no-credentials",
               "HF_API_KEY/HF_API_SECRET not set and no auth in the credential profile")
        return None
    try:
        import requests as req
        import time as _time
        headers = {"Authorization": f"Key {api_key}:{api_secret}", "Content-Type": "application/json"}
        # The model is a URL path segment on this provider, so a hardcoded path
        # is a hardcoded model. Resolve the kind instead.
        hf_path = _resolve_execution_model("image.text-to-image", "higgsfield",
                                           "latest-image-higgsfield")
        if not hf_path:
            record(attempts, "higgsfield", "model-resolution", "unresolved-model",
                   "no current model path for kind image.text-to-image on higgsfield")
            return None
        resp = req.post(f"https://platform.higgsfield.ai/{hf_path}",
                       headers=headers, json={"prompt": prompt, "aspect_ratio": aspect_ratio}, timeout=30)
        if resp.status_code != 200:
            record(attempts, "higgsfield", "request", "request-error",
                   f"HTTP {resp.status_code} from generation endpoint")
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
                record(attempts, "higgsfield", "response", "bad-response",
                       "job completed but no image URL in status payload")
                return None
            elif st.get("status") == "nsfw":
                record(attempts, "higgsfield", "content-policy", "content-rejected",
                       "provider flagged the prompt/content (nsfw)")
                return None
            elif st.get("status") == "failed":
                record(attempts, "higgsfield", "response", "bad-response",
                       "provider reported the generation job failed")
                return None
        record(attempts, "higgsfield", "request", "timeout",
               "job did not complete within 180s of polling")
    except Exception as e:
        record(attempts, "higgsfield", "request", "request-error", str(e))
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
        except Exception:
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
        # Atomic swap — never unlink the original before the signed copy is in place
        os.replace(tmp_signed, out_path)
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

    if args.c2pa_sign and not args.brand:
        parser.error("--c2pa-sign requires --brand (used for the C2PA CreativeWork.author)")

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
    failed = str(result.get("status", "")).upper() == "FAILED"
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt": args.prompt,
        "output": args.output,
        # On failure the in-memory record knows exactly which providers were
        # tried and why. Writing "unknown" here threw that away and left the
        # only durable trace less informative than the one that scrolled past.
        "provider": result.get("provider") or ("none-succeeded" if failed else "unknown"),
        # Do not record a model id on a run where no model was ever called —
        # a log that names a model implies it ran.
        "model": None if failed else result.get("model", model_id),
        "model_requested": model_id,
        "references": args.references,
        "result": result.get("status", "unknown"),
        "c2pa_signed": result.get("c2pa_signed", False),
    }
    if failed:
        log_entry["providers_tried"] = result.get("providers_tried", [])
        log_entry["attempts"] = result.get("attempts", [])
        log_entry["error"] = result.get("error")
    log_file = log_dir / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-generation.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

    print(json.dumps(result, indent=2))

    # Exit codes are a contract. This returned 0 after every provider failed,
    # so any `&&` chain, CI step or batch loop read total failure as success —
    # while price_book.py exits 3 and compliance_check.py exits 1 in the same
    # situation. 0 = image produced, 4 = placeholder only, 1 = nothing produced.
    status = str(result.get("status", "")).lower()
    sys.exit(0 if status == "success" else (4 if status == "placeholder" else 1))


if __name__ == "__main__":
    main()
