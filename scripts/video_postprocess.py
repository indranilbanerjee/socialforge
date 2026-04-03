#!/usr/bin/env python3
"""
video_postprocess.py -- Video post-processing using ffmpeg (bundled via imageio-ffmpeg).

Uses imageio-ffmpeg (pip install imageio-ffmpeg) which bundles the ffmpeg binary,
so no system-level ffmpeg install is needed. The bundled binary is located
automatically via imageio_ffmpeg.get_ffmpeg_exe().

Operations:
  - Watermark overlay (logo with configurable position, margin, opacity)
  - Platform-specific resizing (letterbox/pillarbox, no stretching)
  - SRT subtitle burn-in with brand font styling
  - Background music mixing (volume-adjusted)

Brand config is read from brand-config.json for logo path, fonts, and styling.
Platform specs define target dimensions for each social media platform.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add scripts dir to path for credential_manager/install_deps import
sys.path.insert(0, str(Path(__file__).parent))

# Persistent storage: prefer ${CLAUDE_PLUGIN_DATA} (survives sessions/updates),
# fall back to ~/socialforge-workspace (legacy/local)
_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
if _plugin_data and Path(_plugin_data).exists():
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
    WORKSPACE = Path.home() / "socialforge-workspace"

# Platform video dimension specs
PLATFORM_SPECS = {
    "linkedin":        {"width": 1920, "height": 1080, "ratio": "16:9"},
    "instagram_reel":  {"width": 1080, "height": 1920, "ratio": "9:16"},
    "instagram_story": {"width": 1080, "height": 1920, "ratio": "9:16"},
    "instagram_feed":  {"width": 1080, "height": 1080, "ratio": "1:1"},
    "x_twitter":       {"width": 1600, "height": 900,  "ratio": "16:9"},
    "facebook":        {"width": 1200, "height": 630,  "ratio": "~16:9"},
    "youtube":         {"width": 1920, "height": 1080, "ratio": "16:9"},
    "youtube_short":   {"width": 1080, "height": 1920, "ratio": "9:16"},
    "tiktok":          {"width": 1080, "height": 1920, "ratio": "9:16"},
}

# ---------------------------------------------------------------------------
# ffmpeg binary
# ---------------------------------------------------------------------------

def get_ffmpeg():
    """Return the path to the ffmpeg binary bundled with imageio-ffmpeg.

    If imageio-ffmpeg is not installed, attempts auto-install via install_deps.
    Returns the absolute path string to the ffmpeg executable.
    """
    try:
        import imageio_ffmpeg
    except ImportError:
        try:
            from install_deps import ensure_package
            if ensure_package("imageio-ffmpeg"):
                import imageio_ffmpeg
            else:
                raise RuntimeError(
                    "imageio-ffmpeg install failed. Run: pip install imageio-ffmpeg"
                )
        except ImportError:
            raise RuntimeError(
                "imageio-ffmpeg not installed and install_deps unavailable. "
                "Run: pip install imageio-ffmpeg"
            )

    return imageio_ffmpeg.get_ffmpeg_exe()


# ---------------------------------------------------------------------------
# Watermark
# ---------------------------------------------------------------------------

def add_watermark(input_path, logo_path, output_path, position="bottom-right",
                  margin=20, opacity=0.7):
    """Overlay a logo watermark on the video.

    Uses ffmpeg overlay filter with colorchannelmixer for opacity control.

    Args:
        input_path: Path to the source video.
        logo_path: Path to the logo image (PNG with transparency recommended).
        output_path: Path for the watermarked output video.
        position: One of top-left, top-right, bottom-left, bottom-right, center.
        margin: Pixel margin from the edge.
        opacity: Logo opacity (0.0 to 1.0).

    Returns:
        dict with status, output path, and details.
    """
    ffmpeg = get_ffmpeg()

    if not Path(input_path).exists():
        return {"status": "FAILED", "error": f"Input video not found: {input_path}"}
    if not Path(logo_path).exists():
        return {"status": "FAILED", "error": f"Logo not found: {logo_path}"}

    positions = {
        "top-left":     f"{margin}:{margin}",
        "top-right":    f"W-w-{margin}:{margin}",
        "bottom-left":  f"{margin}:H-h-{margin}",
        "bottom-right": f"W-w-{margin}:H-h-{margin}",
        "center":       "(W-w)/2:(H-h)/2",
    }
    overlay_pos = positions.get(position, positions["bottom-right"])

    filter_complex = (
        f"[1:v]colorchannelmixer=aa={opacity}[logo];"
        f"[0:v][logo]overlay={overlay_pos}[out]"
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg, "-y",
        "-i", str(input_path),
        "-i", str(logo_path),
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-map", "0:a?",
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return {
            "status": "success",
            "output": str(output_path),
            "position": position,
            "margin": margin,
            "opacity": opacity,
        }
    except subprocess.CalledProcessError as e:
        return {"status": "FAILED", "error": f"ffmpeg watermark failed: {e.stderr[:500]}"}


# ---------------------------------------------------------------------------
# Platform resize
# ---------------------------------------------------------------------------

def resize_for_platform(input_path, output_path, platform):
    """Resize video to platform dimensions using scale + pad (no stretching).

    Uses ffmpeg scale filter to fit within target dimensions, then pad filter
    to add black letterbox/pillarbox bars as needed.

    Args:
        input_path: Path to the source video.
        output_path: Path for the resized output video.
        platform: Platform key from PLATFORM_SPECS.

    Returns:
        dict with status, output path, platform, and dimensions.
    """
    ffmpeg = get_ffmpeg()

    if not Path(input_path).exists():
        return {"status": "FAILED", "error": f"Input video not found: {input_path}"}

    if platform not in PLATFORM_SPECS:
        return {
            "status": "FAILED",
            "error": f"Unknown platform: {platform}",
            "available": list(PLATFORM_SPECS.keys()),
        }

    spec = PLATFORM_SPECS[platform]
    w, h = spec["width"], spec["height"]

    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black"
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg, "-y",
        "-i", str(input_path),
        "-vf", vf,
        "-map", "0:a?",
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return {
            "status": "success",
            "output": str(output_path),
            "platform": platform,
            "dimensions": f"{w}x{h}",
            "ratio": spec["ratio"],
        }
    except subprocess.CalledProcessError as e:
        return {"status": "FAILED", "error": f"ffmpeg resize failed: {e.stderr[:500]}"}


# ---------------------------------------------------------------------------
# Subtitle burn-in
# ---------------------------------------------------------------------------

def burn_subtitles(input_path, srt_path, output_path, font="Montserrat",
                   font_size=24, font_color="white", bg_color="black@0.5"):
    """Burn SRT subtitles into the video with brand font styling.

    Uses the ffmpeg subtitles filter with force_style for font customization.

    Args:
        input_path: Path to the source video.
        srt_path: Path to the SRT subtitle file.
        output_path: Path for the subtitled output video.
        font: Font family name (must be installed on system).
        font_size: Subtitle font size in pixels.
        font_color: Subtitle text color (ffmpeg ASS color name or hex).
        bg_color: Subtitle background color with optional opacity.

    Returns:
        dict with status, output path, and subtitle details.
    """
    ffmpeg = get_ffmpeg()

    if not Path(input_path).exists():
        return {"status": "FAILED", "error": f"Input video not found: {input_path}"}
    if not Path(srt_path).exists():
        return {"status": "FAILED", "error": f"SRT file not found: {srt_path}"}

    # Escape special characters in path for ffmpeg subtitles filter
    # On Windows, backslashes and colons need escaping
    escaped_srt = str(srt_path).replace("\\", "/").replace(":", "\\:")

    # Build force_style string for ASS subtitle styling
    force_style = (
        f"FontName={font},"
        f"FontSize={font_size},"
        "PrimaryColour=&H00FFFFFF,"
        "BackColour=&H80000000,"
        "BorderStyle=4,"
        "Outline=0,"
        "Shadow=0,"
        "MarginV=30,"
        "Alignment=2"
    )

    # Map font_color to ASS color if it is a common name
    color_map = {
        "white":  "&H00FFFFFF",
        "black":  "&H00000000",
        "yellow": "&H0000FFFF",
        "red":    "&H000000FF",
        "green":  "&H0000FF00",
        "blue":   "&H00FF0000",
    }
    if font_color.lower() in color_map:
        force_style = force_style.replace(
            "PrimaryColour=&H00FFFFFF",
            f"PrimaryColour={color_map[font_color.lower()]}"
        )

    vf = "subtitles='" + escaped_srt + "':force_style='" + force_style + "'"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg, "-y",
        "-i", str(input_path),
        "-vf", vf,
        "-map", "0:a?",
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return {
            "status": "success",
            "output": str(output_path),
            "srt": str(srt_path),
            "font": font,
            "font_size": font_size,
        }
    except subprocess.CalledProcessError as e:
        return {"status": "FAILED", "error": f"ffmpeg subtitles failed: {e.stderr[:500]}"}


# ---------------------------------------------------------------------------
# Background music
# ---------------------------------------------------------------------------

def add_background_music(input_path, audio_path, output_path, music_volume=0.2):
    """Mix background music into the video at reduced volume.

    If the input video has no existing audio track, the music is added directly.
    If the input has audio, both tracks are mixed together with the music at
    the specified volume level.

    Args:
        input_path: Path to the source video.
        audio_path: Path to the music audio file (mp3, wav, etc.).
        output_path: Path for the output video with music.
        music_volume: Volume multiplier for the music track (0.0 to 1.0).

    Returns:
        dict with status, output path, and music details.
    """
    ffmpeg = get_ffmpeg()

    if not Path(input_path).exists():
        return {"status": "FAILED", "error": f"Input video not found: {input_path}"}
    if not Path(audio_path).exists():
        return {"status": "FAILED", "error": f"Audio file not found: {audio_path}"}

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Probe whether input has an audio stream
    probe_cmd = [ffmpeg, "-i", str(input_path), "-hide_banner"]
    try:
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        has_audio = "Audio:" in probe_result.stderr
    except Exception:
        has_audio = False

    if has_audio:
        filter_complex = (
            f"[1:a]volume={music_volume}[music];"
            "[0:a][music]amix=inputs=2:duration=shortest:dropout_transition=2[aout]"
        )
        cmd = [
            ffmpeg, "-y", "-i", str(input_path), "-i", str(audio_path),
            "-filter_complex", filter_complex,
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", str(output_path),
        ]
    else:
        cmd = [
            ffmpeg, "-y", "-i", str(input_path), "-i", str(audio_path),
            "-filter_complex", f"[1:a]volume={music_volume}[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", str(output_path),
        ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return {
            "status": "success",
            "output": str(output_path),
            "music": str(audio_path),
            "music_volume": music_volume,
            "mixed_with_original": has_audio,
        }
    except subprocess.CalledProcessError as e:
        return {"status": "FAILED", "error": f"ffmpeg music mix failed: {e.stderr[:500]}"}


# ---------------------------------------------------------------------------
# Full post-processing pipeline
# ---------------------------------------------------------------------------

def postprocess_video(input_path, output_dir, brand_config, platforms,
                      srt_path=None, music_path=None, burn_subs=False,
                      add_music=False):
    """Full video post-processing pipeline.

    Steps:
      1. Add watermark (logo from brand config)
      2. Burn subtitles (if burn_subs=True and srt_path provided)
      3. Add background music (if add_music=True and music_path provided)
      4. Resize for each platform in the platforms list

    Args:
        input_path: Path to the source video.
        output_dir: Directory for all output files.
        brand_config: Brand configuration dict with logo, fonts, etc.
        platforms: List of platform keys to resize for.
        srt_path: Path to SRT subtitle file (optional).
        music_path: Path to background music file (optional).
        burn_subs: Whether to burn subtitles into the video.
        add_music: Whether to mix in background music.

    Returns:
        dict with status, list of files created, and platforms processed.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    log_dir = WORKSPACE / "shared" / "video-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"postprocess-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"

    log_entries = []
    files_created = []
    errors = []

    def log(operation, result):
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "operation": operation,
            "status": result.get("status", "unknown"),
        }
        if result.get("output"):
            entry["output"] = result["output"]
        if result.get("error"):
            entry["error"] = result["error"]
        log_entries.append(entry)

    logo_config = brand_config.get("logo", {})
    logo_relative = logo_config.get("primary", "")
    logo_position = logo_config.get("position", "bottom-right")
    logo_opacity = logo_config.get("opacity", 0.7)

    brand_dir = brand_config.get("_brand_dir", "")
    if logo_relative and brand_dir:
        logo_path = str(Path(brand_dir) / logo_relative)
    elif logo_relative:
        logo_path = logo_relative
    else:
        logo_path = None

    font = brand_config.get("fonts", {}).get("heading", "Montserrat")
    current_input = str(input_path)

    # Step 1: Add watermark
    if logo_path and Path(logo_path).exists():
        watermark_output = str(output_dir / "watermarked.mp4")
        result = add_watermark(current_input, logo_path, watermark_output,
                               position=logo_position, opacity=logo_opacity)
        log("watermark", result)
        if result["status"] == "success":
            current_input = watermark_output
            files_created.append(watermark_output)
        else:
            errors.append(f"Watermark: {result.get('error', 'unknown error')}")
    else:
        log("watermark", {"status": "skipped", "reason": "No logo found"})

    # Step 2: Burn subtitles
    if burn_subs and srt_path and Path(srt_path).exists():
        subs_output = str(output_dir / "subtitled.mp4")
        result = burn_subtitles(current_input, srt_path, subs_output, font=font)
        log("subtitles", result)
        if result["status"] == "success":
            current_input = subs_output
            files_created.append(subs_output)
        else:
            errors.append(f"Subtitles: {result.get('error', 'unknown error')}")
    elif burn_subs:
        log("subtitles", {"status": "skipped", "reason": "No SRT file provided or found"})

    # Step 3: Add background music
    if add_music and music_path and Path(music_path).exists():
        music_output = str(output_dir / "with-music.mp4")
        result = add_background_music(current_input, music_path, music_output)
        log("background_music", result)
        if result["status"] == "success":
            current_input = music_output
            files_created.append(music_output)
        else:
            errors.append(f"Music: {result.get('error', 'unknown error')}")
    elif add_music:
        log("background_music", {"status": "skipped", "reason": "No music file provided or found"})

    # Step 4: Resize for each platform
    platforms_processed = []
    for platform in platforms:
        platform_output = str(output_dir / f"{platform}.mp4")
        result = resize_for_platform(current_input, platform_output, platform)
        log(f"resize_{platform}", result)
        if result["status"] == "success":
            files_created.append(platform_output)
            platforms_processed.append({
                "platform": platform,
                "output": platform_output,
                "dimensions": result.get("dimensions"),
            })
        else:
            errors.append(f"Resize {platform}: {result.get('error', 'unknown error')}")

    log_data = {
        "input": str(input_path),
        "output_dir": str(output_dir),
        "started_at": log_entries[0]["timestamp"] if log_entries else None,
        "completed_at": datetime.utcnow().isoformat() + "Z",
        "operations": log_entries,
    }
    try:
        log_file.write_text(json.dumps(log_data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    overall_status = "success" if not errors else "partial" if platforms_processed else "FAILED"

    return {
        "status": overall_status,
        "files_created": files_created,
        "platforms_processed": platforms_processed,
        "errors": errors if errors else None,
        "log": str(log_file),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    """CLI interface for video post-processing."""
    parser = argparse.ArgumentParser(
        description="SocialForge Video Post-Processor (ffmpeg via imageio-ffmpeg)"
    )
    parser.add_argument("--input", required=True, help="Input video path")
    parser.add_argument("--output-dir", required=True, help="Output directory for processed videos")
    parser.add_argument("--brand", required=True, help="Brand slug (reads brand-config.json)")
    parser.add_argument("--platforms", default=None,
                        help="Comma-separated platform list (default: all platforms)")
    parser.add_argument("--srt", default=None, help="Path to SRT subtitle file")
    parser.add_argument("--music", default=None, help="Path to background music file")
    parser.add_argument("--burn-subs", action="store_true", help="Burn subtitles into the video")
    parser.add_argument("--add-music", action="store_true", help="Add background music")
    parser.add_argument("--logo-position", default=None,
                        help="Override logo position (top-left, top-right, bottom-left, bottom-right, center)")
    parser.add_argument("--logo-opacity", type=float, default=None,
                        help="Override logo opacity (0.0 to 1.0)")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(json.dumps({"status": "FAILED", "error": f"Input video not found: {args.input}"}))
        sys.exit(1)

    config_path = WORKSPACE / "brands" / args.brand / "brand-config.json"
    if config_path.exists():
        brand_config = json.loads(config_path.read_text(encoding="utf-8"))
        brand_config["_brand_dir"] = str(config_path.parent)
    else:
        print(json.dumps({
            "status": "FAILED",
            "error": f"Brand config not found: {config_path}",
            "hint": "Run /sf:brand-manager to set up the brand first.",
        }))
        sys.exit(1)

    if args.logo_position:
        brand_config.setdefault("logo", {})["position"] = args.logo_position
    if args.logo_opacity is not None:
        brand_config.setdefault("logo", {})["opacity"] = args.logo_opacity

    if args.platforms:
        platforms = [p.strip() for p in args.platforms.split(",")]
        invalid = [p for p in platforms if p not in PLATFORM_SPECS]
        if invalid:
            print(json.dumps({
                "status": "FAILED",
                "error": f"Unknown platforms: {invalid}",
                "available": list(PLATFORM_SPECS.keys()),
            }))
            sys.exit(1)
    else:
        platforms = list(PLATFORM_SPECS.keys())

    result = postprocess_video(
        input_path=args.input,
        output_dir=args.output_dir,
        brand_config=brand_config,
        platforms=platforms,
        srt_path=args.srt,
        music_path=args.music,
        burn_subs=args.burn_subs,
        add_music=args.add_music,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
