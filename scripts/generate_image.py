#!/usr/bin/env python3
"""
generate_image.py — AI image generation with multi-provider support.
Generates images from text prompts, optionally with style reference images.
Supports: Gemini Nano Banana 2 (direct API), fal.ai (MCP), Replicate (MCP).
"""

import argparse
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path.home() / "socialforge-workspace"


def generate_with_gemini(prompt, output_path, reference_images=None, aspect_ratio="1:1"):
    """Generate image using Gemini API (Nano Banana 2)."""
    try:
        import google.generativeai as genai
    except ImportError:
        return {"error": "google-generativeai not installed. Run: pip install google-generativeai"}

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY not set. Get one at https://aistudio.google.com/apikey"}

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash-exp-image-generation")

    # Build content parts
    contents = []

    # Add reference images if provided (style-referenced mode)
    if reference_images:
        for ref_path in reference_images[:14]:  # Max 14 references (Nano Banana 2 limit)
            ref_file = Path(ref_path)
            if ref_file.exists():
                img_data = ref_file.read_bytes()
                mime = "image/jpeg" if ref_file.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
                contents.append({"mime_type": mime, "data": base64.b64encode(img_data).decode()})

    contents.append(prompt)

    try:
        response = model.generate_content(
            contents,
            generation_config={"response_modalities": ["TEXT", "IMAGE"]}
        )

        # Extract image from response
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data.mime_type.startswith("image/"):
                img_bytes = base64.b64decode(part.inline_data.data)
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                Path(output_path).write_bytes(img_bytes)
                return {
                    "status": "success",
                    "provider": "gemini",
                    "output": str(output_path),
                    "prompt_length": len(prompt),
                    "references_used": len(reference_images) if reference_images else 0
                }

        return {"error": "No image in Gemini response", "text_response": response.text if response.text else ""}

    except Exception as e:
        return {"error": f"Gemini generation failed: {str(e)}"}


def generate_placeholder(prompt, output_path, width=1080, height=1080):
    """Generate a placeholder image when no AI provider is available."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return {"error": "No AI provider available and Pillow not installed for placeholder"}

    img = Image.new("RGB", (width, height), (240, 240, 240))
    draw = ImageDraw.Draw(img)

    # Draw border
    draw.rectangle([(10, 10), (width - 10, height - 10)], outline=(200, 200, 200), width=2)

    # Add text
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
        "note": "No AI provider available. Placeholder generated. Replace with real image."
    }


def main():
    parser = argparse.ArgumentParser(description="SocialForge Image Generator")
    parser.add_argument("--prompt", required=True, help="Text prompt for image generation")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--references", nargs="*", default=None, help="Style reference image paths")
    parser.add_argument("--provider", default="gemini", choices=["gemini", "placeholder"],
                        help="AI provider (gemini or placeholder)")
    parser.add_argument("--aspect-ratio", default="1:1", help="Aspect ratio (1:1, 16:9, 4:5, 9:16)")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1080)
    args = parser.parse_args()

    if args.provider == "gemini":
        result = generate_with_gemini(args.prompt, args.output, args.references, args.aspect_ratio)
        if "error" in result:
            # Fallback to placeholder
            result = generate_placeholder(args.prompt, args.output, args.width, args.height)
    else:
        result = generate_placeholder(args.prompt, args.output, args.width, args.height)

    # Log the prompt
    log_dir = WORKSPACE / "shared" / "prompt-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "prompt": args.prompt,
        "output": args.output,
        "provider": result.get("provider", "unknown"),
        "references": args.references,
        "result": result.get("status", "unknown")
    }
    log_file = log_dir / f"{datetime.utcnow().strftime('%Y-%m-%d')}-generation.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
