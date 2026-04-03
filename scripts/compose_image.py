#!/usr/bin/env python3
"""
compose_image.py — Image compositing with Pillow.
Handles background removal, layering, shadow/reflection, and logo overlay.
"""

import argparse
import json
import os
import sys
from pathlib import Path

_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
if _plugin_data and Path(_plugin_data).exists():
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
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

    # Add drop shadow
    try:
        shadow = Image.new("RGBA", fg.size, (0, 0, 0, 0))
        shadow_data = fg.split()[3]  # Get alpha channel
        shadow_alpha = shadow_data.point(lambda p: min(int(p * 0.3), 80))  # Subtle shadow
        shadow.putalpha(shadow_alpha)
        # Offset shadow slightly down and right
        shadow_offset = (x + 4, y + 6)
        # Apply gaussian-like blur by pasting slightly offset multiple times
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                bg.paste(shadow, (shadow_offset[0] + dx, shadow_offset[1] + dy), shadow)
    except Exception:
        pass  # Shadow generation failed, continue without

    # Composite foreground on top of shadow
    bg.paste(fg, (x, y), fg)

    # Edge feathering — soften edges of composited foreground
    try:
        from PIL import ImageFilter
        # Create a mask from the alpha channel and blur edges
        if fg.mode == "RGBA":
            alpha = fg.split()[3]
            # Slight blur on the alpha edge (2px feather)
            feathered_alpha = alpha.filter(ImageFilter.GaussianBlur(radius=2))
            fg_feathered = fg.copy()
            fg_feathered.putalpha(feathered_alpha)
            # Re-composite with feathered edges
            bg_temp = bg.copy()
            bg_temp.paste(fg_feathered, (x, y), fg_feathered)
            bg = bg_temp
    except Exception:
        pass  # Feathering failed, continue with hard edges

    # Color temperature matching — adjust foreground warmth to match background
    try:
        from PIL import ImageStat
        # Sample background color temperature (average RGB)
        bg_crop = bg.crop((0, 0, bg.width, bg.height)).convert("RGB")
        bg_stat = ImageStat.Stat(bg_crop)
        bg_avg = bg_stat.mean  # [R, G, B] averages

        # Determine if background is warm (R>B) or cool (B>R)
        warmth = bg_avg[0] - bg_avg[2]  # Positive = warm, negative = cool

        # Apply subtle color shift to foreground region to match
        if abs(warmth) > 15:  # Only if noticeable difference
            from PIL import ImageEnhance
            fg_region = bg.crop((x, y, x + fg.size[0], y + fg.size[1]))
            # Subtle color balance: shift by 2-5% toward background temperature
            shift = 0.03 if warmth > 0 else -0.03
            enhancer = ImageEnhance.Color(fg_region)
            fg_adjusted = enhancer.enhance(1.0 + shift)
            bg.paste(fg_adjusted, (x, y))
    except Exception:
        pass  # Color matching failed, continue without

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    bg.convert("RGB").save(output_path, quality=95)

    return {
        "status": "success",
        "output": str(output_path),
        "bg_size": f"{bg.width}x{bg.height}",
        "fg_size": f"{new_w}x{new_h}",
        "position": position
    }


def add_reflection(image_path, output_path, surface_type="subtle"):
    """Add subtle surface reflection below the composited subject."""
    try:
        from PIL import Image, ImageFilter, ImageEnhance
    except ImportError:
        return {"error": "Pillow not installed"}

    img = Image.open(image_path).convert("RGBA")
    w, h = img.size

    # Create reflection: flip bottom 20% of image
    reflect_height = int(h * 0.15)
    bottom_strip = img.crop((0, h - reflect_height, w, h))
    reflected = bottom_strip.transpose(Image.FLIP_TOP_BOTTOM)

    # Fade the reflection
    gradient = Image.new("L", (w, reflect_height))
    for y_pos in range(reflect_height):
        opacity = int(60 * (1 - y_pos / reflect_height))  # Fade from 60 to 0
        for x_pos in range(w):
            gradient.putpixel((x_pos, y_pos), opacity)

    reflected.putalpha(gradient)

    # Blur reflection
    reflected_rgb = reflected.convert("RGB").filter(ImageFilter.GaussianBlur(radius=3))
    reflected_final = reflected_rgb.convert("RGBA")
    reflected_final.putalpha(gradient)

    # Extend canvas and paste reflection
    new_h = h + reflect_height
    canvas = Image.new("RGBA", (w, new_h), (0, 0, 0, 0))
    canvas.paste(img, (0, 0))
    canvas.paste(reflected_final, (0, h), reflected_final)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, quality=95)

    return {"status": "success", "output": str(output_path), "reflection": surface_type}


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

    # Reflection
    ref_parser = sub.add_parser("add-reflection", help="Add surface reflection")
    ref_parser.add_argument("--image", required=True)
    ref_parser.add_argument("--output", required=True)
    ref_parser.add_argument("--surface", default="subtle", choices=["subtle", "glass", "water"])

    args = parser.parse_args()

    if args.action == "remove-bg":
        result = remove_background(args.input, args.output)
    elif args.action == "composite":
        result = composite_layers(args.background, args.foreground, args.output, args.position, args.fg_scale)
    elif args.action == "add-logo":
        result = add_logo_overlay(args.image, args.logo, args.output, args.position, args.opacity, args.size_pct)
    elif args.action == "add-reflection":
        result = add_reflection(args.image, args.output, args.surface)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
