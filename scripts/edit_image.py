#!/usr/bin/env python3
"""
edit_image.py — AI-powered image editing.
Enhance, extend, and modify images while preserving core subjects.

Uses Gemini's conversational image editing. Model id is resolved via
scripts/model_registry.json through the `latest-image-edit-google` alias
(Nano Banana Pro by default); pass --model to override and the curator
will auto-fall-forward if a deprecated id is supplied. Run
`python scripts/resolve_model.py --list --modality image-edit` for options.
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

# Add scripts dir to path for credential_manager + curator imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from resolve_model import resolve as _resolve_model, check as _check_model
    DEFAULT_MODEL = _resolve_model("latest-image-edit-google")
except (ImportError, KeyError, ValueError):  # pragma: no cover
    _resolve_model = None
    _check_model = None
    DEFAULT_MODEL = "gemini-3-pro-image-preview"


def _negotiate_model(user_value):
    if _check_model is None or _resolve_model is None:
        return user_value or DEFAULT_MODEL
    if user_value:
        status, replacement = _check_model(user_value)
        if status == "deprecated" and replacement:
            print(f"WARNING: model {user_value!r} is deprecated; using {replacement!r}", file=sys.stderr)
            return replacement
        if status == "unknown":
            print(f"WARNING: model {user_value!r} not in curated registry", file=sys.stderr)
        return user_value
    return _resolve_model("latest-image-edit-google")


def edit_with_gemini(image_path, instruction, output_path, reference_images=None, model=None):
    """Edit image using Gemini API."""
    model = model or DEFAULT_MODEL
    try:
        from credential_manager import get_gemini_client
        client, backend = get_gemini_client()
        if not client:
            return {"status": "FAILED", "error": backend}
    except ImportError:
        # Fallback if credential_manager not available
        try:
            from google import genai
        except ImportError:
            return {"status": "FAILED", "error": "google-genai not installed. Run: pip install google-genai"}
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {"status": "FAILED", "error": "No credentials. Run /socialforge:setup"}
        client = genai.Client(api_key=api_key)
        backend = "ai-studio-fallback"

    from google.genai import types

    # Build content: image + instruction
    img_data = Path(image_path).read_bytes()
    mime = "image/jpeg" if Path(image_path).suffix.lower() in [".jpg", ".jpeg"] else "image/png"

    contents = [types.Part.from_bytes(data=img_data, mime_type=mime)]

    # Add style references if provided
    if reference_images:
        for ref in reference_images[:14]:  # Up to 14 style references
            if Path(ref).exists():
                ref_data = Path(ref).read_bytes()
                ref_mime = "image/jpeg" if Path(ref).suffix.lower() in [".jpg", ".jpeg"] else "image/png"
                contents.append(types.Part.from_bytes(data=ref_data, mime_type=ref_mime))

    contents.append(f"Edit this image: {instruction}. Preserve the core subject faithfully. Do not distort faces, products, or key elements.")

    config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        for part in response.parts:
            if part.inline_data is not None and part.inline_data.mime_type.startswith("image/"):
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                try:
                    image = part.as_image()
                    image.save(output_path)
                except (AttributeError, TypeError):
                    img_bytes = base64.b64decode(part.inline_data.data) if isinstance(part.inline_data.data, str) else part.inline_data.data
                    Path(output_path).write_bytes(img_bytes)
                return {
                    "status": "success",
                    "provider": f"gemini-edit-{backend}",
                    "model": model,
                    "output": str(output_path),
                    "instruction": instruction
                }

        return {"error": "No edited image in response"}

    except Exception as e:
        return {"error": f"Gemini edit failed: {str(e)}"}


def main():
    parser = argparse.ArgumentParser(description="SocialForge Image Editor")
    parser.add_argument("--image", required=True, help="Input image path")
    parser.add_argument("--instruction", required=True, help="Edit instruction")
    parser.add_argument("--output", required=True, help="Output image path")
    parser.add_argument("--references", nargs="*", default=None, help="Style reference images")
    parser.add_argument("--model", default=None,
                        help=f"Image edit model id (default: registry alias `latest-image-edit-google` -> {DEFAULT_MODEL}). "
                             f"Deprecated ids auto-fall-forward.")
    args = parser.parse_args()

    model_id = _negotiate_model(args.model)
    result = edit_with_gemini(args.image, args.instruction, args.output, args.references, model=model_id)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
