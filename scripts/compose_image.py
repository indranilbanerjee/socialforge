#!/usr/bin/env python3
"""
compose_image.py — Image compositing with Pillow.
Handles background removal, layering, shadow/reflection, and logo overlay.
"""

import argparse
import json
import sys
from pathlib import Path

WORKSPACE = Path.home() / "socialforge-workspace"


def remove_background(input_path, output_path):
    """Remove background using rembg. Falls back to white-background detection if rembg unavailable."""
    try:
        from rembg import remove
        from PIL import Image
        img = Image.open(input_path)
        result = remove(img)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        result.save(output_path, format="PNG")
        return {"status": "success", "output": str(output_path), "method": "rembg", "has_alpha": True}
    except ImportError:
        # Fallback: if image has white/solid background, attempt basic threshold removal
        try:
            from PIL import Image
            img = Image.open(input_path).convert("RGBA")
            # Simple white-background removal (threshold-based)
            data = img.getdata()
            new_data = []
            for item in data:
                if item[0] > 240 and item[1] > 240 and item[2] > 240:
                    new_data.append((255, 255, 255, 0))  # Make white pixels transparent
                else:
                    new_data.append(item)
            img.putdata(new_data)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, format="PNG")
            return {"status": "success", "output": str(output_path), "method": "threshold_fallback", "has_alpha": True, "note": "Basic white-background removal. Install rembg for better results."}
        except ImportError:
            return {"error": "Neither rembg nor Pillow available. Run: pip install Pillow (minimum) or pip install rembg Pillow (recommended)"}


def composite_layers(background_path, foreground_path, output_path, position="center", fg_scale=0.5):
    """Composite foreground onto background."""
    try:
        from PIL import Image
    except ImportError:
        return {"error": "Pillow not installed. Run: pip install Pillow"}

    bg = Image.open(background_path).convert("RGBA")
    fg = Image.open(foreground_path).convert("RGBA")

    # Scale foreground
    new_w = int(bg.width * fg_scale)
    ratio = new_w / fg.width
    new_h = int(fg.height * ratio)
    fg = fg.resize((new_w, new_h), Image.LANCZOS)

    # Position
    if position == "center":
        x = (bg.width - new_w) // 2
        y = (bg.height - new_h) // 2
    elif position == "bottom-center":
        x = (bg.width - new_w) // 2
        y = bg.height - new_h - int(bg.height * 0.05)
    elif position == "left-center":
        x = int(bg.width * 0.05)
        y = (bg.height - new_h) // 2
    elif position == "right-center":
        x = bg.width - new_w - int(bg.width * 0.05)
        y = (bg.height - new_h) // 2
    else:
        x, y = (bg.width - new_w) // 2, (bg.height - new_h) // 2

    # Composite
    bg.paste(fg, (x, y), fg)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    bg.convert("RGB").save(output_path, quality=95)

    return {
        "status": "success",
        "output": str(output_path),
        "bg_size": f"{bg.width}x{bg.height}",
        "fg_size": f"{new_w}x{new_h}",
        "position": position
    }


def add_logo_overlay(image_path, logo_path, output_path, position="bottom-right", opacity=0.7, size_pct=8):
    """Add logo watermark to image."""
    try:
        from PIL import Image
    except ImportError:
        return {"error": "Pillow not installed"}

    img = Image.open(image_path).convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    # Scale logo
    logo_w = int(img.width * size_pct / 100)
    ratio = logo_w / logo.width
    logo_h = int(logo.height * ratio)
    logo = logo.resize((logo_w, logo_h), Image.LANCZOS)

    # Apply opacity
    alpha = logo.split()[3]
    alpha = alpha.point(lambda p: int(p * opacity))
    logo.putalpha(alpha)

    # Position
    margin = int(img.width * 0.03)
    positions = {
        "bottom-right": (img.width - logo_w - margin, img.height - logo_h - margin),
        "bottom-left": (margin, img.height - logo_h - margin),
        "top-right": (img.width - logo_w - margin, margin),
        "top-left": (margin, margin),
    }
    x, y = positions.get(position, positions["bottom-right"])

    img.paste(logo, (x, y), logo)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, quality=95)

    return {"status": "success", "output": str(output_path), "logo_position": position, "logo_size": f"{logo_w}x{logo_h}"}


def main():
    parser = argparse.ArgumentParser(description="SocialForge Image Compositor")
    sub = parser.add_subparsers(dest="action", required=True)

    # Remove background
    bg_parser = sub.add_parser("remove-bg", help="Remove image background")
    bg_parser.add_argument("--input", required=True)
    bg_parser.add_argument("--output", required=True)

    # Composite layers
    comp_parser = sub.add_parser("composite", help="Composite foreground onto background")
    comp_parser.add_argument("--background", required=True)
    comp_parser.add_argument("--foreground", required=True)
    comp_parser.add_argument("--output", required=True)
    comp_parser.add_argument("--position", default="center", choices=["center", "bottom-center", "left-center", "right-center"])
    comp_parser.add_argument("--fg-scale", type=float, default=0.5, help="Foreground scale relative to background (0.0-1.0)")

    # Logo overlay
    logo_parser = sub.add_parser("add-logo", help="Add logo watermark")
    logo_parser.add_argument("--image", required=True)
    logo_parser.add_argument("--logo", required=True)
    logo_parser.add_argument("--output", required=True)
    logo_parser.add_argument("--position", default="bottom-right")
    logo_parser.add_argument("--opacity", type=float, default=0.7)
    logo_parser.add_argument("--size-pct", type=float, default=8)

    args = parser.parse_args()

    if args.action == "remove-bg":
        result = remove_background(args.input, args.output)
    elif args.action == "composite":
        result = composite_layers(args.background, args.foreground, args.output, args.position, args.fg_scale)
    elif args.action == "add-logo":
        result = add_logo_overlay(args.image, args.logo, args.output, args.position, args.opacity, args.size_pct)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
