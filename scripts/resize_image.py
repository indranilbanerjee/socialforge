#!/usr/bin/env python3
"""
resize_image.py — Resize and crop images for social media platform specs.
Uses Pillow for image manipulation.
"""

import argparse
import json
import sys
from pathlib import Path

# Platform dimension specs
PLATFORM_SPECS = {
    "linkedin_feed": {"width": 1200, "height": 627, "ratio": "1.91:1"},
    "linkedin_square": {"width": 1080, "height": 1080, "ratio": "1:1"},
    "linkedin_carousel": {"width": 1080, "height": 1080, "ratio": "1:1"},
    "instagram_feed": {"width": 1080, "height": 1080, "ratio": "1:1"},
    "instagram_portrait": {"width": 1080, "height": 1350, "ratio": "4:5"},
    "instagram_story": {"width": 1080, "height": 1920, "ratio": "9:16"},
    "instagram_reel": {"width": 1080, "height": 1920, "ratio": "9:16"},
    "x_post": {"width": 1600, "height": 900, "ratio": "16:9"},
    "x_square": {"width": 1080, "height": 1080, "ratio": "1:1"},
    "facebook_feed": {"width": 1200, "height": 630, "ratio": "1.91:1"},
    "facebook_square": {"width": 1080, "height": 1080, "ratio": "1:1"},
    "facebook_story": {"width": 1080, "height": 1920, "ratio": "9:16"},
    "youtube_thumbnail": {"width": 1280, "height": 720, "ratio": "16:9"},
    "pinterest_pin": {"width": 1000, "height": 1500, "ratio": "2:3"},
}


def resize_image(input_path, output_path, platform, mode="cover"):
    """Resize image to platform specs."""
    try:
        from PIL import Image
    except ImportError:
        print(json.dumps({"error": "Pillow not installed. Run: pip install Pillow"}))
        sys.exit(1)

    if platform not in PLATFORM_SPECS:
        print(json.dumps({"error": f"Unknown platform: {platform}", "available": list(PLATFORM_SPECS.keys())}))
        sys.exit(1)

    spec = PLATFORM_SPECS[platform]
    target_w, target_h = spec["width"], spec["height"]

    img = Image.open(input_path)
    orig_w, orig_h = img.size

    if mode == "cover":
        # Scale to cover target, then center-crop
        scale = max(target_w / orig_w, target_h / orig_h)
        new_w, new_h = int(orig_w * scale), int(orig_h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        img = img.crop((left, top, left + target_w, top + target_h))
    elif mode == "contain":
        # Scale to fit within target, add padding
        scale = min(target_w / orig_w, target_h / orig_h)
        new_w, new_h = int(orig_w * scale), int(orig_h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

        canvas = Image.new("RGB", (target_w, target_h), (255, 255, 255))
        paste_x = (target_w - new_w) // 2
        paste_y = (target_h - new_h) // 2
        canvas.paste(img, (paste_x, paste_y))
        img = canvas

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=95)

    print(json.dumps({
        "input": str(input_path),
        "output": str(output_path),
        "platform": platform,
        "dimensions": f"{target_w}x{target_h}",
        "original": f"{orig_w}x{orig_h}",
        "mode": mode
    }))


def main():
    parser = argparse.ArgumentParser(description="SocialForge Image Resizer")
    parser.add_argument("--input", required=True, help="Input image path")
    parser.add_argument("--output", required=True, help="Output image path")
    parser.add_argument("--platform", required=True, help="Target platform spec")
    parser.add_argument("--mode", default="cover", choices=["cover", "contain"])
    parser.add_argument("--list-platforms", action="store_true")
    args = parser.parse_args()

    if args.list_platforms:
        print(json.dumps(PLATFORM_SPECS, indent=2))
        return

    resize_image(args.input, args.output, args.platform, args.mode)


if __name__ == "__main__":
    main()
