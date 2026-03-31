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


def edit_with_gemini(image_path, instruction, output_path, reference_images=None):
    """Edit image using Gemini API."""
    try:
        import google.generativeai as genai
    except ImportError:
        return {"error": "google-generativeai not installed. Run: pip install google-generativeai"}

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY not set"}

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash-preview-image-generation")

    # Build content: image + instruction
    img_data = Path(image_path).read_bytes()
    mime = "image/jpeg" if Path(image_path).suffix.lower() in [".jpg", ".jpeg"] else "image/png"

    contents = [{"mime_type": mime, "data": base64.b64encode(img_data).decode()}]

    # Add style references if provided
    if reference_images:
        for ref in reference_images[:5]:
            if Path(ref).exists():
                ref_data = Path(ref).read_bytes()
                ref_mime = "image/jpeg" if Path(ref).suffix.lower() in [".jpg", ".jpeg"] else "image/png"
                contents.append({"mime_type": ref_mime, "data": base64.b64encode(ref_data).decode()})

    contents.append(f"Edit this image: {instruction}. Preserve the core subject faithfully. Do not distort faces, products, or key elements.")

    try:
        response = model.generate_content(
            contents,
            generation_config={"response_modalities": ["TEXT", "IMAGE"]}
        )

        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data.mime_type.startswith("image/"):
                img_bytes = base64.b64decode(part.inline_data.data)
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                Path(output_path).write_bytes(img_bytes)
                return {
                    "status": "success",
                    "provider": "gemini_edit",
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
