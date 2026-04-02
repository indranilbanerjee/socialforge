#!/usr/bin/env python3
"""
generate_video.py — Video production with AI generation.

Pipeline: Gemini generates image → Kling (via WaveSpeed) or Veo (via Vertex AI) animates to video.

Video providers:
  - Kling v2.0 via WaveSpeed: image-to-video (5-10s clips). Best price/quality for short-form.
  - Veo 2.0 via Vertex AI: text-to-video and image-to-video (up to 8s). Google-native.

Setup (WaveSpeed — for Kling):
    export WAVESPEED_API_KEY=your-fal-key (get at https://WaveSpeed/dashboard/keys)
    pip install wavespeed

Setup (Vertex AI — for Veo):
    export GOOGLE_CLOUD_PROJECT=your-project-id
    gcloud auth application-default login
    pip install google-genai
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
if _plugin_data and Path(_plugin_data).exists():
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
    WORKSPACE = Path.home() / "socialforge-workspace"

VIDEO_TYPES = {
    "hero_video": {"duration": "30-90s", "production": "Script + storyboard (needs filming)"},
    "mini_case_study": {"duration": "30-60s", "production": "Script + AI animation"},
    "short_reel": {"duration": "15-30s", "production": "AI video generation"},
    "story": {"duration": "15s", "production": "Image-to-video animation"},
    "talking_head": {"duration": "30-120s", "production": "Script only (needs filming)"},
}


# ---------------------------------------------------------------------------
# Video Generation — Kling via WaveSpeed
# ---------------------------------------------------------------------------

def generate_video_kling(prompt, output_path, first_frame_path, last_frame_path=None,
                         duration=5, model="kwaivgi/kling-v3.0-pro/image-to-video", sound=False):
    """Generate video using Kling v3.0 via WaveSpeed API.
    Takes first frame (required) and optionally last frame as keyframes.
    Kling animates between them guided by the motion prompt."""
    try:
        import wavespeed
    except ImportError:
        return {"status": "FAILED", "error": "wavespeed not installed. Run: pip install wavespeed"}

    ws_key = os.environ.get("WAVESPEED_API_KEY")
    if not ws_key:
        return {
            "status": "FAILED",
            "error": "WAVESPEED_API_KEY not set. Get at https://wavespeed.ai/accesskey",
            "action_required": True,
        }
    os.environ["WAVESPEED_API_KEY"] = ws_key

    if not Path(first_frame_path).exists():
        return {"status": "FAILED", "error": f"First frame not found: {first_frame_path}"}

    try:
        print(f"  Uploading first frame...")
        image_url = wavespeed.upload(first_frame_path)
        payload = {
            "image": image_url,
            "prompt": prompt,
            "duration": min(max(duration, 3), 15),
            "cfg_scale": 0.5,
            "sound": sound,
            "shot_type": "customize",
        }

        if last_frame_path and Path(last_frame_path).exists():
            print(f"  Uploading last frame...")
            payload["end_image"] = wavespeed.upload(last_frame_path)

        print(f"  Generating video via {model}...")
        output = wavespeed.run(model, payload, timeout=300.0, poll_interval=3.0)

        video_url = output.get("outputs", [None])[0]
        if not video_url and isinstance(output.get("video"), dict):
            video_url = output["video"].get("url")
        if video_url:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(video_url, output_path)
            return {
                "status": "success",
                "provider": "wavespeed-kling-v3",
                "model": model,
                "output": str(output_path),
                "video_url": video_url,
                "duration": duration,
                "sound": sound,
            }
        else:
            return {"status": "FAILED", "error": "No video URL in WaveSpeed response", "raw": str(output)[:500]}

    except Exception as e:
        return {"status": "FAILED", "error": f"Kling generation failed: {str(e)}"}


# ---------------------------------------------------------------------------
# Video Generation — Veo via Vertex AI
# ---------------------------------------------------------------------------

def generate_video_veo(prompt, output_path, image_path=None, duration=5, aspect_ratio="16:9"):
    """Generate video using Google Veo 2.0 via Vertex AI."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return {"status": "FAILED", "error": "google-genai not installed. Run: pip install google-genai"}

    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    if not project:
        # Try AI Studio fallback
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            client = genai.Client(api_key=api_key)
            backend = "aistudio"
        else:
            return {
                "status": "FAILED",
                "error": "GOOGLE_CLOUD_PROJECT not set for Vertex AI Veo. "
                         "Run: export GOOGLE_CLOUD_PROJECT=your-project-id",
                "action_required": True,
            }
    else:
        try:
            client = genai.Client(vertexai=True, project=project, location=location)
            backend = "vertex"
        except Exception as e:
            return {"status": "FAILED", "error": f"Vertex AI init failed: {e}"}

    try:
        # Build generation config
        gen_config = types.GenerateVideosConfig(
            prompt=prompt,
            number_of_videos=1,
            duration_seconds=min(duration, 8),  # Veo max 8s
            aspect_ratio=aspect_ratio,
        )

        # Image-to-video or text-to-video
        if image_path and Path(image_path).exists():
            img_bytes = Path(image_path).read_bytes()
            mime = "image/jpeg" if Path(image_path).suffix.lower() in (".jpg", ".jpeg") else "image/png"
            image = types.Image(image_bytes=img_bytes, mime_type=mime)
            operation = client.models.generate_videos(
                model="veo-2.0-generate-001",
                image=image,
                config=gen_config,
            )
        else:
            operation = client.models.generate_videos(
                model="veo-2.0-generate-001",
                config=gen_config,
            )

        # Poll for completion (max 5 minutes)
        timeout = 300
        start = time.time()
        while not operation.done and (time.time() - start) < timeout:
            time.sleep(15)
            operation = client.operations.get(operation)

        if not operation.done:
            return {"status": "FAILED", "error": "Veo generation timed out after 5 minutes"}

        if operation.result and operation.result.generated_videos:
            video = operation.result.generated_videos[0]
            video_bytes = client.files.download(file=video.video)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(video_bytes)
            return {
                "status": "success",
                "provider": f"veo-2.0-{backend}",
                "output": str(output_path),
                "duration": min(duration, 8),
                "mode": "image-to-video" if image_path else "text-to-video",
            }
        else:
            return {"status": "FAILED", "error": "Veo returned no video (may have been filtered)"}

    except Exception as e:
        return {"status": "FAILED", "error": f"Veo generation failed: {str(e)}"}


# ---------------------------------------------------------------------------
# Script and Storyboard generation
# ---------------------------------------------------------------------------

def generate_script(post_data, brand_config):
    """Generate a video script from post data."""
    title = post_data.get("title", "Untitled")
    brief = post_data.get("visual", {}).get("direction_a", "")
    video_type = post_data.get("video_details", {}).get("video_type", "short_reel")
    duration = post_data.get("video_details", {}).get("duration_seconds", 30)

    return {
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
        "notes": f"Based on: {brief}",
    }


def generate_storyboard(script):
    """Generate a storyboard from a script."""
    return {
        "title": script["title"],
        "total_scenes": len(script["scenes"]),
        "frames": [
            {
                "frame_number": i + 1,
                "timestamp": scene["timestamp"],
                "visual_description": scene["visual"],
                "camera_direction": "Static" if i == 0 else "Pan/zoom",
                "text_overlay": scene.get("text_overlay", ""),
                "transition": "Cut" if i > 0 else "Fade in",
            }
            for i, scene in enumerate(script["scenes"])
        ],
    }


def generate_srt(script, output_path):
    """Generate SRT subtitle file from video script."""
    srt_lines = []
    for i, scene in enumerate(script.get("scenes", [])):
        timestamp = scene.get("timestamp", "0:00-0:05")
        parts = timestamp.split("-")
        start = parts[0].strip() if parts else "00:00:00"
        end = parts[1].strip() if len(parts) > 1 else "00:00:05"

        def to_srt_time(t):
            p = t.split(":")
            if len(p) == 2:
                return f"00:{p[0].zfill(2)}:{p[1].zfill(2)},000"
            return f"{t},000"

        text = scene.get("text_overlay", "") or scene.get("visual", "")[:80]
        if text:
            srt_lines.extend([f"{i + 1}", f"{to_srt_time(start)} --> {to_srt_time(end)}", text, ""])

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text("\n".join(srt_lines), encoding="utf-8")
    return {"status": "success", "output": str(output_path), "subtitle_count": len(script.get("scenes", []))}


def route_video_provider(duration_seconds, video_type):
    """Route to the appropriate video provider."""
    fal_key = os.environ.get("WAVESPEED_API_KEY")
    gcp_project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    if duration_seconds <= 8 and (gcp_project or gemini_key):
        return {"provider": "veo", "model": "veo-2.0-generate-001", "max_duration": 8}
    elif duration_seconds <= 10 and fal_key:
        return {"provider": "kling", "model": "kling-v2", "max_duration": 10}
    elif fal_key:
        return {"provider": "kling", "model": "kling-v2", "max_duration": 10}
    elif gcp_project or gemini_key:
        return {"provider": "veo", "model": "veo-2.0-generate-001", "max_duration": 8}
    else:
        return {
            "provider": "none",
            "error": "No video API configured. Set WAVESPEED_API_KEY for Kling or GOOGLE_CLOUD_PROJECT for Veo.",
            "fallback": "script_and_storyboard_only",
        }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="SocialForge Video Generator (Kling + Veo)")
    parser.add_argument("--brand", required=True)
    parser.add_argument("--month", required=True)
    parser.add_argument("--post-id", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--generate-video", action="store_true", help="Generate AI video")
    parser.add_argument("--image", default=None, help="Input image for image-to-video")
    parser.add_argument("--provider", default="auto", choices=["auto", "kling", "veo"],
                        help="Video provider (auto routes by duration and available keys)")
    parser.add_argument("--duration", type=int, default=None, help="Override video duration (seconds)")
    parser.add_argument("--aspect-ratio", default="16:9", help="Video aspect ratio")
    parser.add_argument("--srt", action="store_true", help="Generate SRT subtitle file")
    args = parser.parse_args()

    # Load post data
    calendar_path = WORKSPACE / "output" / args.brand / args.month / "calendar-data.json"
    if not calendar_path.exists():
        print(json.dumps({"error": "Calendar not found", "path": str(calendar_path)}))
        sys.exit(1)

    calendar = json.loads(calendar_path.read_text(encoding="utf-8"))
    post = next((p for p in calendar.get("posts", []) if str(p.get("post_id")) == str(args.post_id)), None)
    if not post:
        print(json.dumps({"error": f"Post {args.post_id} not found"}))
        sys.exit(1)

    # Load brand config
    config_path = WORKSPACE / "brands" / args.brand / "brand-config.json"
    brand_config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}

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

    # Duration and routing
    duration = args.duration or post.get("video_details", {}).get("duration_seconds", 10)
    video_type = post.get("video_details", {}).get("video_type", "short_reel")
    routing = route_video_provider(duration, video_type)

    # SRT
    srt_result = None
    if args.srt:
        srt_path = output_dir / f"post-{args.post_id}-subtitles.srt"
        srt_result = generate_srt(script, str(srt_path))

    # Generate video
    video_result = None
    if args.generate_video and routing["provider"] != "none":
        video_path = output_dir / f"post-{args.post_id}-video.mp4"
        prompt = post.get("visual", {}).get("direction_a", post.get("title", ""))
        provider = args.provider if args.provider != "auto" else routing["provider"]

        if provider == "kling":
            video_result = generate_video_kling(prompt, str(video_path), args.image, duration, args.aspect_ratio)
        elif provider == "veo":
            video_result = generate_video_veo(prompt, str(video_path), args.image, duration, args.aspect_ratio)
    elif args.generate_video and routing["provider"] == "none":
        video_result = {"status": "FAILED", "error": routing["error"], "action_required": True}

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
        "video": video_result or {"status": "not_requested", "note": "Use --generate-video to create AI video"},
    }, indent=2))


if __name__ == "__main__":
    main()
