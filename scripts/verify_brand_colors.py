#!/usr/bin/env python3
"""
verify_brand_colors.py — Verify generated images contain brand colors.
Checks that brand palette is represented in the image.
"""

import argparse
import json
import sys
from pathlib import Path

WORKSPACE = Path.home() / "socialforge-workspace"


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def color_distance(c1, c2):
    """Euclidean distance between two RGB colors."""
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5


def verify_colors(image_path, brand, threshold=50, min_percentage=15):
    """Check if brand colors appear in the image."""
    try:
        from PIL import Image
    except ImportError:
        print(json.dumps({"error": "Pillow not installed. Run: pip install Pillow"}))
        sys.exit(1)

    config_path = WORKSPACE / "brands" / brand / "brand-config.json"
    if not config_path.exists():
        print(json.dumps({"error": f"Brand config not found: {brand}"}))
        sys.exit(1)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    brand_colors = []
    colors_config = config.get("colors", {})
    for key in ["primary", "secondary", "accent"]:
        if key in colors_config and colors_config[key]:
            brand_colors.append({"name": key, "hex": colors_config[key], "rgb": hex_to_rgb(colors_config[key])})

    if not brand_colors:
        print(json.dumps({"error": "No brand colors configured"}))
        sys.exit(1)

    img = Image.open(image_path).convert("RGB")
    pixels = list(img.getdata())
    total_pixels = len(pixels)

    color_matches = {c["name"]: 0 for c in brand_colors}

    # Sample every 10th pixel for performance
    for i in range(0, total_pixels, 10):
        pixel = pixels[i]
        for bc in brand_colors:
            if color_distance(pixel, bc["rgb"]) < threshold:
                color_matches[bc["name"]] += 1

    # Scale back up (we sampled every 10th)
    sampled_total = total_pixels // 10
    results = {}
    total_brand_percentage = 0
    for bc in brand_colors:
        pct = round((color_matches[bc["name"]] / max(sampled_total, 1)) * 100, 1)
        results[bc["name"]] = {"hex": bc["hex"], "percentage": pct, "pass": pct >= min_percentage / len(brand_colors)}
        total_brand_percentage += pct

    overall_pass = total_brand_percentage >= min_percentage

    print(json.dumps({
        "image": str(image_path),
        "brand": brand,
        "total_brand_color_percentage": round(total_brand_percentage, 1),
        "min_required_percentage": min_percentage,
        "overall_pass": overall_pass,
        "per_color": results
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description="SocialForge Brand Color Verifier")
    parser.add_argument("--image", required=True)
    parser.add_argument("--brand", required=True)
    parser.add_argument("--threshold", type=int, default=50, help="Color distance threshold (0-255)")
    parser.add_argument("--min-percentage", type=float, default=15, help="Minimum brand color percentage")
    args = parser.parse_args()

    verify_colors(args.image, args.brand, args.threshold, args.min_percentage)


if __name__ == "__main__":
    main()
