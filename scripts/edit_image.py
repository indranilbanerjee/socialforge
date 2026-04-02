#!/usr/bin/env python3
"""
edit_image.py — AI-powered image editing.
Enhance, extend, and modify images while preserving core subjects.
Uses Gemini API for AI editing.
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

# Add scripts dir to path for credential_manager import
sys.path.insert(0, str(Path(__file__).parent))


def edit_with_gemini(image_path, instruction, output_path, reference_images=None):
    """Edit image using Gemini API."""
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
            return {"status": "FAILED", "error": "No credentials. Run /sf:setup"}
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
            model="gemini-2.0-flash-exp-image-generation",
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
    args = parser.parse_args()

    result = edit_with_gemini(args.image, args.instruction, args.output, args.references)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
