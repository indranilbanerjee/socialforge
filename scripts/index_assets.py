#!/usr/bin/env python3
"""
index_assets.py — Index brand visual assets using AI vision analysis.
Scans image libraries, analyzes each with Gemini Vision, builds asset-index.json.
"""

import argparse
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Persistent storage: prefer ${CLAUDE_PLUGIN_DATA} (survives sessions/updates),
# fall back to ~/socialforge-workspace (legacy/local)
_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
if _plugin_data and Path(_plugin_data).exists():
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
    WORKSPACE = Path.home() / "socialforge-workspace"
SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".webp"}

VISION_PROMPT = """Analyze this brand asset image for a social media automation system.

Provide a JSON response with these fields:
{
  "description": "2-3 sentence description of what's in the image",
  "subjects": ["main subjects: person, product, office, event, nature, abstract, etc."],
  "tags": ["15-20 descriptive tags"],
  "dominant_colors_hex": ["top 5 hex color codes"],
  "mood": "1-3 word mood description",
  "lighting": "natural/studio/ambient/dramatic/mixed",
  "setting": "indoor/outdoor/studio/mixed + specific setting",
  "suitable_for": ["3-5 descriptions of what social posts this suits"],
  "background_type": "transparent/solid_white/solid_color/simple/complex",
  "background_removable": true/false,
  "quality_assessment": "high/medium/low",
  "style_reference_worthy": true/false
}"""


def scan_images(source_path):
    """Find all image files in the source directory.
    Supports local paths and Google Drive paths.
    Google Drive: In Cowork, Drive is available via platform integration.
    In Claude Code, files must be downloaded or Drive path must be mounted.
    """
    source = Path(source_path)

    # Handle Google Drive URLs (strip to local path if available)
    source_str = str(source_path)
    if source_str.startswith("https://drive.google.com") or source_str.startswith("gdrive://"):
        # In Cowork: Claude can read Drive files via platform integration
        # In Claude Code: user must download or mount Drive
        # Return empty with helpful message — actual files accessed by Claude reading Drive
        return {"source_type": "google_drive", "url": source_str, "files": [],
                "note": "Google Drive source detected. Claude will read files via platform integration. Index will be built from files Claude can access."}

    if not source.exists():
        return []

    images = []
    for f in sorted(source.rglob("*")):
        if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS:
            images.append(f)
    return images


def analyze_image_gemini(image_path):
    """Analyze a single image with Gemini Vision."""
    try:
        import google.generativeai as genai
    except ImportError:
        return None

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    img_data = image_path.read_bytes()
    mime = "image/jpeg" if image_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"

    try:
        response = model.generate_content([
            {"mime_type": mime, "data": base64.b64encode(img_data).decode()},
            VISION_PROMPT
        ])
        # Parse JSON from response
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(text)
    except Exception:
        return None


def build_basic_entry(image_path, source_root, asset_id):
    """Build a basic index entry from file metadata only."""
    try:
        from PIL import Image
        img = Image.open(image_path)
        w, h = img.size
    except Exception:
        w, h = 0, 0

    return {
        "id": asset_id,
        "filename": image_path.name,
        "path": str(image_path),
        "relative_path": str(image_path.relative_to(source_root)),
        "folder": str(image_path.parent.relative_to(source_root)),
        "dimensions": {"width": w, "height": h},
        "file_size_mb": round(image_path.stat().st_size / (1024 * 1024), 2),
        "format": image_path.suffix.lstrip(".").lower(),
        "ai_description": "",
        "tags": [],
        "detected_colors": [],
        "dominant_mood": "",
        "lighting": "",
        "setting": "",
        "subjects": [],
        "suitable_for": [],
        "has_background": True,
        "background_removable": False,
        "is_style_reference": False,
        "usage_history": [],
        "platforms_compatible": {}
    }


def index_all(brand, source_path, refresh=False):
    """Index all images for a brand."""
    brand_dir = WORKSPACE / "brands" / brand
    index_path = brand_dir / "asset-index.json"

    # Load existing index for refresh mode
    existing = {}
    if refresh and index_path.exists():
        old_index = json.loads(index_path.read_text(encoding="utf-8"))
        for asset in old_index.get("assets", []):
            existing[asset.get("path", "")] = asset

    images = scan_images(source_path)

    # Handle Google Drive source
    if isinstance(images, dict) and images.get("source_type") == "google_drive":
        print(json.dumps({
            "status": "google_drive_source",
            "url": images["url"],
            "instruction": "Google Drive asset source detected. To index Drive assets: 1) In Cowork: Claude reads Drive files via platform integration — provide the folder contents. 2) In Claude Code: download the folder locally first, then run with --source /local/path. The asset-source.json has been updated with the Drive URL for reference.",
            "asset_source_updated": True
        }))
        # Save the Drive URL in asset-source.json for reference
        source_config = {"type": "google_drive", "url": images["url"], "indexed_at": None}
        source_path_file = brand_dir / "asset-source.json"
        source_path_file.write_text(json.dumps(source_config, indent=2), encoding="utf-8")
        return

    if not images:
        print(json.dumps({"error": f"No images found in {source_path}"}))
        sys.exit(1)

    assets = []
    analyzed = 0
    skipped = 0

    for i, img_path in enumerate(images):
        asset_id = f"asset_{i+1:03d}"

        # Skip already-indexed in refresh mode
        if refresh and str(img_path) in existing:
            assets.append(existing[str(img_path)])
            skipped += 1
            continue

        entry = build_basic_entry(img_path, Path(source_path), asset_id)

        # Try AI analysis
        ai_result = analyze_image_gemini(img_path)
        if ai_result:
            entry["ai_description"] = ai_result.get("description", "")
            entry["tags"] = ai_result.get("tags", [])
            entry["detected_colors"] = ai_result.get("dominant_colors_hex", [])
            entry["dominant_mood"] = ai_result.get("mood", "")
            entry["lighting"] = ai_result.get("lighting", "")
            entry["setting"] = ai_result.get("setting", "")
            entry["subjects"] = ai_result.get("subjects", [])
            entry["suitable_for"] = ai_result.get("suitable_for", [])
            entry["background_removable"] = ai_result.get("background_removable", False)
            entry["is_style_reference"] = ai_result.get("style_reference_worthy", False)
            analyzed += 1

        assets.append(entry)

        # Progress every 10 images
        if (i + 1) % 10 == 0:
            print(json.dumps({"progress": f"{i+1}/{len(images)}", "analyzed": analyzed}), file=sys.stderr)

    index = {
        "brand": brand,
        "indexed_at": datetime.utcnow().isoformat() + "Z",
        "source": "local",
        "source_path": str(source_path),
        "total_assets": len(assets),
        "assets": assets
    }

    brand_dir.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")

    style_refs = [a["id"] for a in assets if a.get("is_style_reference")]

    print(json.dumps({
        "brand": brand,
        "total_images": len(images),
        "ai_analyzed": analyzed,
        "skipped_existing": skipped,
        "metadata_only": len(images) - analyzed - skipped,
        "style_reference_candidates": len(style_refs),
        "output": str(index_path)
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description="SocialForge Asset Indexer")
    parser.add_argument("--brand", required=True)
    parser.add_argument("--source", required=True, help="Path to image folder")
    parser.add_argument("--refresh", action="store_true", help="Only index new/changed images")
    args = parser.parse_args()

    index_all(args.brand, args.source, args.refresh)


if __name__ == "__main__":
    main()
