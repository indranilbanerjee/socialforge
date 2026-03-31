#!/usr/bin/env python3
"""
compose_text_overlay.py — Add text overlays to images with brand fonts and colors.
Handles headlines, CTAs, data points, and brand frames.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Persistent storage: prefer ${CLAUDE_PLUGIN_DATA} (survives sessions/updates),
# fall back to ~/socialforge-workspace (legacy/local)
_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
if _plugin_data and Path(_plugin_data).exists():
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
    WORKSPACE = Path.home() / "socialforge-workspace"


def add_text_overlay(image_path, output_path, text, brand=None, position="bottom", font_size=48, color="#FFFFFF", bg_color=None, opacity=0.85):
    """Add text overlay to an image with optional background strip."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return {"error": "Pillow not installed. Run: pip install Pillow"}

    img = Image.open(image_path).convert("RGBA")

    # Load brand config for fonts/colors if provided
    font_path = None
    if brand:
        config_path = WORKSPACE / "brands" / brand / "brand-config.json"
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding="utf-8"))
            fonts = config.get("fonts", {})
            heading_font = fonts.get("heading", "")
            if heading_font:
                brand_font_path = WORKSPACE / "brands" / brand / "brand-assets" / heading_font
                if brand_font_path.exists():
                    font_path = str(brand_font_path)
            # Use brand colors if not overridden
            if color == "#FFFFFF" and config.get("colors", {}).get("text_on_dark"):
                color = config["colors"]["text_on_dark"]
            if bg_color is None and config.get("colors", {}).get("primary"):
                bg_color = config["colors"]["primary"]

    # Load font
    try:
        if font_path:
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.truetype("arial.ttf", font_size)
    except (IOError, OSError):
        font = ImageFont.load_default()

    # Create overlay layer
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Calculate text size
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    padding = 20

    # Position
    if position == "bottom":
        strip_y = img.height - text_h - padding * 3
        text_x = (img.width - text_w) // 2
        text_y = strip_y + padding
    elif position == "top":
        strip_y = 0
        text_x = (img.width - text_w) // 2
        text_y = padding
    elif position == "center":
        strip_y = (img.height - text_h - padding * 2) // 2
        text_x = (img.width - text_w) // 2
        text_y = strip_y + padding
    else:
        strip_y = img.height - text_h - padding * 3
        text_x = (img.width - text_w) // 2
        text_y = strip_y + padding

    # Draw background strip if bg_color is set
    if bg_color:
        r, g, b = int(bg_color[1:3], 16), int(bg_color[3:5], 16), int(bg_color[5:7], 16)
        a = int(opacity * 255)
        draw.rectangle(
            [(0, strip_y), (img.width, strip_y + text_h + padding * 2)],
            fill=(r, g, b, a)
        )

    # Draw text
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    draw.text((text_x, text_y), text, fill=(r, g, b, 255), font=font)

    # Composite
    result = Image.alpha_composite(img, overlay)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    result.convert("RGB").save(output_path, quality=95)

    return {
        "status": "success",
        "output": str(output_path),
        "text": text,
        "position": position,
        "font_size": font_size
    }


def main():
    parser = argparse.ArgumentParser(description="SocialForge Text Overlay")
    parser.add_argument("--image", required=True, help="Input image path")
    parser.add_argument("--output", required=True, help="Output image path")
    parser.add_argument("--text", required=True, help="Overlay text")
    parser.add_argument("--brand", default=None, help="Brand slug for fonts/colors")
    parser.add_argument("--position", default="bottom", choices=["top", "center", "bottom"])
    parser.add_argument("--font-size", type=int, default=48)
    parser.add_argument("--color", default="#FFFFFF", help="Text color (hex)")
    parser.add_argument("--bg-color", default=None, help="Background strip color (hex)")
    parser.add_argument("--opacity", type=float, default=0.85, help="Background strip opacity")
    args = parser.parse_args()

    result = add_text_overlay(args.image, args.output, args.text, args.brand, args.position, args.font_size, args.color, args.bg_color, args.opacity)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
