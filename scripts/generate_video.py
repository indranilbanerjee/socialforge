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


def route_video_provider(duration_seconds, video_type):
    """Route to the appropriate video generation provider based on duration."""
    if duration_seconds <= 10:
        return {"provider": "veo_fast", "model": "veo-3.1-generate-preview", "mode": "fast"}
    elif duration_seconds <= 30:
        return {"provider": "veo_standard", "model": "veo-3.1-generate-preview", "mode": "standard"}
    elif duration_seconds <= 180:
        return {"provider": "kling", "model": "kling-v2", "mode": "long_form"}
    else:
        return {"provider": "manual", "model": None, "mode": "needs_filming",
                "note": "Videos over 3 minutes require live filming"}


def generate_video_veo(prompt, output_path, duration=10, image_path=None):
    """Generate video using Gemini Veo 3.1 API."""
    try:
        import google.generativeai as genai
        import os
        import base64
        import time
    except ImportError:
        return {"error": "google-generativeai not installed"}

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY not set", "fallback": "script_and_storyboard_only"}

    genai.configure(api_key=api_key)

    try:
        # Veo 3.1 video generation
        model = genai.GenerativeModel("veo-3.1-generate-preview")

        contents = []
        if image_path and Path(image_path).exists():
            # Image-to-video
            img_data = Path(image_path).read_bytes()
            mime = "image/jpeg" if Path(image_path).suffix.lower() in [".jpg", ".jpeg"] else "image/png"
            contents.append({"mime_type": mime, "data": base64.b64encode(img_data).decode()})

        contents.append(f"Generate a {duration}-second video: {prompt}")

        response = model.generate_content(
            contents,
            generation_config={"response_modalities": ["VIDEO"]}
        )

        # Extract video from response
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data.mime_type.startswith("video/"):
                video_bytes = base64.b64decode(part.inline_data.data)
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                Path(output_path).write_bytes(video_bytes)
                return {
                    "status": "success",
                    "provider": "veo_3.1",
                    "output": str(output_path),
                    "duration_requested": duration
                }

        return {"error": "No video in Veo response", "fallback": "script_and_storyboard_only"}

    except Exception as e:
        return {"error": f"Veo generation failed: {str(e)}", "fallback": "script_and_storyboard_only"}


def generate_srt(script, output_path):
    """Generate SRT subtitle file from video script."""
    srt_lines = []
    for i, scene in enumerate(script.get("scenes", [])):
        timestamp = scene.get("timestamp", "0:00-0:05")
        parts = timestamp.split("-")
        start = parts[0].strip() if parts else "00:00:00"
        end = parts[1].strip() if len(parts) > 1 else "00:00:05"

        # Convert M:SS to HH:MM:SS,mmm
        def to_srt_time(t):
            parts = t.split(":")
            if len(parts) == 2:
                return f"00:{parts[0].zfill(2)}:{parts[1].zfill(2)},000"
            return f"{t},000"

        text = scene.get("text_overlay", "") or scene.get("visual", "")[:80]
        if text:
            srt_lines.append(f"{i + 1}")
            srt_lines.append(f"{to_srt_time(start)} --> {to_srt_time(end)}")
            srt_lines.append(text)
            srt_lines.append("")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text("\n".join(srt_lines), encoding="utf-8")
    return {"status": "success", "output": str(output_path), "subtitle_count": len(script.get("scenes", []))}


def main():
    parser = argparse.ArgumentParser(description="SocialForge Video Generator")
    parser.add_argument("--brand", required=True)
    parser.add_argument("--month", required=True)
    parser.add_argument("--post-id", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--generate-video", action="store_true", help="Actually generate AI video (requires API key)")
    parser.add_argument("--image", default=None, help="Input image for image-to-video")
    parser.add_argument("--srt", action="store_true", help="Generate SRT subtitle file")
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

    # Generate script (always)
    script = generate_script(post, brand_config)
    script_path = output_dir / f"post-{args.post_id}-script.json"
    script_path.write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")

    # Generate storyboard (always)
    storyboard = generate_storyboard(script)
    storyboard_path = output_dir / f"post-{args.post_id}-storyboard.json"
    storyboard_path.write_text(json.dumps(storyboard, indent=2, ensure_ascii=False), encoding="utf-8")

    # Route video provider
    duration = post.get("video_details", {}).get("duration_seconds", 30)
    video_type = post.get("video_details", {}).get("video_type", "short_reel")
    routing = route_video_provider(duration, video_type)

    # Generate SRT if requested
    srt_result = None
    if args.srt:
        srt_path = output_dir / f"post-{args.post_id}-subtitles.srt"
        srt_result = generate_srt(script, str(srt_path))

    # Generate actual video if requested
    video_result = None
    if args.generate_video and routing["provider"] != "manual":
        video_path = output_dir / f"post-{args.post_id}-video.mp4"
        prompt = post.get("visual", {}).get("direction_a", post.get("title", ""))
        video_result = generate_video_veo(prompt, str(video_path), duration, args.image)

    print(json.dumps({
        "status": "success",
        "post_id": args.post_id,
        "video_type": video_type,
        "duration": duration,
        "routing": routing,
        "scenes": len(script["scenes"]),
        "script": str(script_path),
        "storyboard": str(storyboard_path),
        "srt": srt_result,
        "video": video_result or {"status": "not_requested", "note": "Use --generate-video to create AI video"}
    }, indent=2))


if __name__ == "__main__":
    main()
