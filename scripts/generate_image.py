#!/usr/bin/env python3
"""
generate_image.py — AI image generation via Google Vertex AI (Gemini).

Uses the unified google-genai SDK. Supports Vertex AI (production) with
AI Studio fallback. Reference images supported for style-guided generation.

Models: gemini-2.5-flash-image (Nano Banana 2), gemini-3-pro-image-preview (Nano Banana Pro)

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

DEFAULT_MODEL = "gemini-2.5-flash-image"


def create_client():
    """Create a google-genai client. Vertex AI preferred, AI Studio fallback."""
    try:
        from google import genai
    except ImportError:
        return None, None, "google-genai not installed. Run: pip install google-genai"

    # Try Vertex AI first
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    if project:
        try:
            client = genai.Client(vertexai=True, project=project, location=location)
            return client, "vertex", None
        except Exception as e:
            pass  # Fall through to AI Studio

    # Fall back to AI Studio
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            return client, "aistudio", None
        except Exception as e:
            return None, None, f"AI Studio init failed: {e}"

    return None, None, (
        "No Gemini credentials configured. "
        "For Vertex AI: set GOOGLE_CLOUD_PROJECT + run 'gcloud auth application-default login'. "
        "For AI Studio: set GEMINI_API_KEY (get at https://aistudio.google.com/apikey)."
    )


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
                image = part.as_image()
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                image.save(output_path, format="PNG", quality=95)
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
        return {"status": "FAILED", "error": str(e), "action_required": True}


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


def main():
    parser = argparse.ArgumentParser(description="SocialForge Image Generator (Vertex AI + AI Studio)")
    parser.add_argument("--prompt", required=True, help="Text prompt for image generation")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--references", nargs="*", default=None, help="Style reference image paths (max 14)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        choices=["gemini-2.5-flash-image", "gemini-3-pro-image-preview", "gemini-3.1-flash-image"],
                        help="Gemini model for image generation")
    parser.add_argument("--aspect-ratio", default="1:1", choices=["1:1", "16:9", "9:16", "4:3", "3:4", "4:5"],
                        help="Output aspect ratio")
    parser.add_argument("--edit", default=None, help="Source image path for editing mode")
    parser.add_argument("--placeholder", action="store_true", help="Generate placeholder only (no AI)")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1080)
    args = parser.parse_args()

    if args.placeholder:
        result = generate_placeholder(args.prompt, args.output, args.width, args.height)
    elif args.edit:
        result = edit_image(args.edit, args.prompt, args.output, args.model)
    else:
        result = generate_image(args.prompt, args.output, args.references, args.aspect_ratio, args.model)

    # Log
    log_dir = WORKSPACE / "shared" / "prompt-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "prompt": args.prompt,
        "output": args.output,
        "provider": result.get("provider", "unknown"),
        "model": result.get("model", args.model),
        "references": args.references,
        "result": result.get("status", "unknown"),
    }
    log_file = log_dir / f"{datetime.utcnow().strftime('%Y-%m-%d')}-generation.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
