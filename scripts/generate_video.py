#!/usr/bin/env python3
"""
generate_video.py — Video production kit.
Generates video scripts, storyboards, and optionally AI video clips.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path.home() / "socialforge-workspace"

VIDEO_TYPES = {
    "hero_video": {"duration": "30-90s", "production": "Script + storyboard (needs filming)"},
    "mini_case_study": {"duration": "30-60s", "production": "Script + AI animation"},
    "short_reel": {"duration": "15-30s", "production": "AI video generation"},
    "story": {"duration": "15s", "production": "Image-to-video animation"},
    "talking_head": {"duration": "30-120s", "production": "Script only (needs filming)"},
}


def generate_script(post_data, brand_config):
    """Generate a video script from post data."""
    title = post_data.get("title", "Untitled")
    brief = post_data.get("visual", {}).get("direction_a", "")
    video_type = post_data.get("video_details", {}).get("video_type", "short_reel")
    duration = post_data.get("video_details", {}).get("duration_seconds", 30)

    script = {
        "title": title,
        "video_type": video_type,
        "target_duration_seconds": duration,
        "brand": brand_config.get("brand_name", ""),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "scenes": [
            {"timestamp": "0:00-0:03", "visual": "Brand logo reveal with motion", "audio": "Brand sound / music start", "text_overlay": ""},
            {"timestamp": "0:03-0:08", "visual": f"Hook visual: {brief[:100]}", "audio": "Narration: opening hook", "text_overlay": title[:50]},
            {"timestamp": f"0:08-0:{duration-5}", "visual": "Main content sequence", "audio": "Narration continues", "text_overlay": "Key points"},
            {"timestamp": f"0:{duration-5}-0:{duration}", "visual": "CTA + brand logo", "audio": "Closing statement", "text_overlay": "Call to action"},
        ],
        "notes": f"Based on: {brief}"
    }

    return script


def generate_storyboard(script):
    """Generate a storyboard from a script."""
    storyboard = {
        "title": script["title"],
        "total_scenes": len(script["scenes"]),
        "frames": []
    }

    for i, scene in enumerate(script["scenes"]):
        storyboard["frames"].append({
            "frame_number": i + 1,
            "timestamp": scene["timestamp"],
            "visual_description": scene["visual"],
            "camera_direction": "Static" if i == 0 else "Pan/zoom",
            "text_overlay": scene.get("text_overlay", ""),
            "transition": "Cut" if i > 0 else "Fade in"
        })

    return storyboard


def main():
    parser = argparse.ArgumentParser(description="SocialForge Video Generator")
    parser.add_argument("--brand", required=True)
    parser.add_argument("--month", required=True)
    parser.add_argument("--post-id", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    # Load post data
    calendar_path = WORKSPACE / "output" / args.brand / args.month / "calendar-data.json"
    if not calendar_path.exists():
        print(json.dumps({"error": "Calendar not found"}))
        sys.exit(1)

    calendar = json.loads(calendar_path.read_text(encoding="utf-8"))
    post = None
    for p in calendar.get("posts", []):
        if str(p.get("post_id")) == str(args.post_id):
            post = p
            break

    if not post:
        print(json.dumps({"error": f"Post {args.post_id} not found"}))
        sys.exit(1)

    # Load brand config
    config_path = WORKSPACE / "brands" / args.brand / "brand-config.json"
    brand_config = {}
    if config_path.exists():
        brand_config = json.loads(config_path.read_text(encoding="utf-8"))

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate script
    script = generate_script(post, brand_config)
    script_path = output_dir / f"post-{args.post_id}-script.json"
    script_path.write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")

    # Generate storyboard
    storyboard = generate_storyboard(script)
    storyboard_path = output_dir / f"post-{args.post_id}-storyboard.json"
    storyboard_path.write_text(json.dumps(storyboard, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "status": "success",
        "post_id": args.post_id,
        "video_type": script["video_type"],
        "duration": script["target_duration_seconds"],
        "scenes": len(script["scenes"]),
        "script": str(script_path),
        "storyboard": str(storyboard_path),
        "ai_video": "not_generated (use MCP for AI video)"
    }, indent=2))


if __name__ == "__main__":
    main()
