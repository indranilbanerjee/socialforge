#!/usr/bin/env python3
"""
generate_video.py — Video production with AI generation.

Pipeline: Gemini generates image -> Kling (WaveSpeed) or Veo (Vertex AI) animates to video.

Video providers:
  - Kling v3.0 Pro via WaveSpeed: image-to-video (5-15s clips). Best price/quality for short-form.
  - Veo 3.1 via Vertex AI: text-to-video and image-to-video (up to 8s). Google-native.
  - HiggsField (Kling v2.1 Pro) as a third fallback.

Model selection: model ids are resolved through the curator
(scripts/model_registry.json) so a registry refresh propagates automatically.
Override per-call with --video-model.

Setup (WaveSpeed — for Kling):
    export WAVESPEED_API_KEY=your-key (get at https://wavespeed.ai/accesskey)
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
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Add scripts dir to path for credential_manager + curator imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from resolve_model import resolve as _resolve_model, check as _check_model
    DEFAULT_KLING_MODEL = _resolve_model("latest-video-wavespeed")
    DEFAULT_VEO_MODEL = _resolve_model("latest-video-google")
except (ImportError, KeyError, ValueError):  # pragma: no cover
    _resolve_model = None
    _check_model = None
    # No hardcoded ids here. A model string written into source is a claim about
    # the day it was written, and this plugin runs long after that day — one
    # fallback sat pinned to a superseded generation for about six months and
    # nothing could say so. When the registry is unavailable the model must be
    # discovered; see model_book.resolve_for_execution.
    DEFAULT_KLING_MODEL = None
    DEFAULT_VEO_MODEL = None


def _resolve_execution_model(kind, provider, registry_alias=None):
    """Model id for a capability, discovered live where possible.

    Returns None rather than a guess when nothing resolves, so the caller falls
    through to the next provider instead of calling a model that may be retired.
    """
    try:
        from model_book import resolve_for_execution
    except ImportError:
        return None
    result = resolve_for_execution(kind, provider, registry_alias)
    if result.get("warning"):
        print(f"NOTE: {result['warning']}", file=sys.stderr)
    elif result.get("action_required"):
        print(f"NOTE: {result['action_required']}", file=sys.stderr)
    return result.get("model_id")


def _negotiate_video_model(user_value, alias):
    """Resolve user-supplied --video-model or fall back to alias."""
    if _check_model is None or _resolve_model is None:
        # Curator unavailable: honour an explicit user id, but never hand the
        # ALIAS STRING to an SDK as if it were a model id — that produced an
        # opaque provider error instead of a clear "unresolved model" record.
        return user_value or None
    if user_value:
        status, replacement = _check_model(user_value)
        if status in ("deprecated", "retired") and replacement:
            print(f"WARNING: video model {user_value!r} is {status}; using {replacement!r}", file=sys.stderr)
            return replacement
        if status == "unknown":
            print(f"WARNING: video model {user_value!r} not in curated registry", file=sys.stderr)
        return user_value
    try:
        return _resolve_model(alias)
    except (KeyError, ValueError):
        return None

_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("PLUGIN_DATA") or ""
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
                         duration=5, model=None, sound=False, attempts=None):
    """Generate video using Kling via WaveSpeed API.
    Model id defaults to the curator's `latest-video-wavespeed` alias.
    Takes first frame (required) and optionally last frame as keyframes.
    Kling animates between them guided by the motion prompt.

    One rung of the provider chain (see generate_video_chain): returns the
    success dict, or None with the reason recorded into `attempts`. A rung
    that cannot run never aborts the chain and never fails silently.
    """
    from provider_failures import record
    model = model or DEFAULT_KLING_MODEL
    if not model:
        record(attempts, "wavespeed-kling", "model-resolution", "unresolved-model",
               "no current model id for the wavespeed video alias")
        return None
    # Credentials before dependencies: never auto-install an SDK the caller
    # has no key for (and a keyless rung stays fully offline).
    try:
        from credential_manager import get_wavespeed_key
        ws_key = get_wavespeed_key()
    except ImportError:
        ws_key = os.environ.get("WAVESPEED_API_KEY")
    if not ws_key:
        record(attempts, "wavespeed-kling", "credentials", "no-credentials",
               "WAVESPEED_API_KEY not set and no key in the credential profile")
        return None

    try:
        import wavespeed  # noqa: F401
    except ImportError:
        try:
            from install_deps import ensure_package
            if ensure_package("wavespeed"):
                import wavespeed  # noqa: F401
            else:
                record(attempts, "wavespeed-kling", "dependencies", "dependency-missing",
                       "wavespeed install failed. Run: pip install wavespeed")
                return None
        except Exception as exc:
            record(attempts, "wavespeed-kling", "dependencies", "dependency-missing",
                   f"wavespeed not installed ({exc}). Run: pip install wavespeed")
            return None
    os.environ["WAVESPEED_API_KEY"] = ws_key
    from wavespeed import Client as WsClient
    _ws_client = WsClient(api_key=ws_key)

    if not first_frame_path or not Path(first_frame_path).exists():
        record(attempts, "wavespeed-kling", "request", "bad-input",
               f"first-frame image required for image-to-video but not found: {first_frame_path}")
        return None

    try:
        print("  Uploading first frame...", file=sys.stderr)
        image_url = _ws_client.upload(first_frame_path)
        payload = {
            "image": image_url,
            "prompt": prompt,
            "duration": min(max(duration, 3), 15),
            "cfg_scale": 0.5,
            "sound": sound,
            "shot_type": "customize",
        }

        if last_frame_path and Path(last_frame_path).exists():
            print("  Uploading last frame...", file=sys.stderr)
            payload["end_image"] = _ws_client.upload(last_frame_path)

        print(f"  Generating video via {model}...", file=sys.stderr)
        output = _ws_client.run(model, payload, timeout=300.0, poll_interval=3.0)

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
        record(attempts, "wavespeed-kling", "response", "bad-response",
               f"no video URL in WaveSpeed response: {str(output)[:150]}")
    except Exception as e:
        record(attempts, "wavespeed-kling", "request", "request-error", str(e))
    return None


def generate_video_higgsfield(prompt, output_path, image_path=None, duration=5, sound=False,
                              attempts=None):
    """Fallback: Generate video via HiggsField (Kling or DoP).

    One rung of the provider chain: success dict, or None with the reason
    recorded into `attempts`. A content-policy rejection, a missing key, and
    an HTTP error are three different problems with three different fixes —
    they are never collapsed into one silent None anymore.
    """
    from provider_failures import record
    try:
        from credential_manager import get_higgsfield_auth
        api_key, api_secret = get_higgsfield_auth()
    except ImportError:
        api_key = os.environ.get("HF_API_KEY")
        api_secret = os.environ.get("HF_API_SECRET")
    if not api_key or not api_secret:
        record(attempts, "higgsfield", "credentials", "no-credentials",
               "HF_API_KEY/HF_API_SECRET not set and no auth in the credential profile")
        return None
    try:
        import requests as req
    except ImportError as e:
        record(attempts, "higgsfield", "dependencies", "dependency-missing",
               f"requests not importable: {e}")
        return None
    try:
        import time as _time
        headers = {"Authorization": f"Key {api_key}:{api_secret}", "Content-Type": "application/json"}
        payload = {"prompt": prompt, "duration": min(max(duration, 3), 15)}
        # This line is why the fallback sat two generations behind for months:
        # the version was written into the path and nothing ever re-checked it.
        # Ask for the kind; whichever model currently satisfies it gets used.
        kind = "video.image-to-video" if image_path else "video.text-to-video"
        model_path = _resolve_execution_model(kind, "higgsfield",
                                              "latest-video-higgsfield")
        if not model_path:
            record(attempts, "higgsfield", "model-resolution", "unresolved-model",
                   f"no current model path for kind {kind} on higgsfield")
            return None
        if image_path and Path(image_path).exists():
            import base64 as b64
            img_data = b64.b64encode(Path(image_path).read_bytes()).decode()
            payload["image_url"] = f"data:image/png;base64,{img_data}"
        resp = req.post(f"https://platform.higgsfield.ai/{model_path}", headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            record(attempts, "higgsfield", "request", "request-error",
                   f"HTTP {resp.status_code} from generation endpoint")
            return None
        request_id = resp.json().get("request_id")
        for _ in range(100):
            _time.sleep(3)
            st = req.get(f"https://platform.higgsfield.ai/requests/{request_id}/status", headers=headers, timeout=15).json()
            if st.get("status") == "completed":
                vid_url = st.get("video", {}).get("url") or (st.get("outputs", [None]) or [None])[0]
                if vid_url:
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    urllib.request.urlretrieve(vid_url, output_path)
                    return {"status": "success", "provider": "higgsfield-kling", "output": str(output_path)}
                record(attempts, "higgsfield", "response", "bad-response",
                       "job completed but no video URL in status payload")
                return None
            elif st.get("status") == "nsfw":
                record(attempts, "higgsfield", "content-policy", "content-rejected",
                       "provider flagged the prompt/content (nsfw)")
                return None
            elif st.get("status") == "failed":
                record(attempts, "higgsfield", "response", "bad-response",
                       "provider reported the generation job failed")
                return None
        record(attempts, "higgsfield", "request", "timeout",
               "job did not complete within 300s of polling")
    except Exception as e:
        record(attempts, "higgsfield", "request", "request-error", str(e))
    return None


# ---------------------------------------------------------------------------
# Video Generation — Veo via Vertex AI
# ---------------------------------------------------------------------------

def generate_video_veo(prompt, output_path, image_path=None, duration=5, aspect_ratio="16:9",
                       model=None, attempts=None):
    """Generate video using Google Veo via Vertex AI.
    Model id defaults to the curator's `latest-video-google` alias.

    One rung of the provider chain: success dict, or None with the reason
    recorded into `attempts`."""
    from provider_failures import record
    model = model or DEFAULT_VEO_MODEL
    if not model:
        record(attempts, "veo", "model-resolution", "unresolved-model",
               "no current model id for the google video alias")
        return None
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        try:
            from install_deps import ensure_package
            if ensure_package("google-genai"):
                from google import genai
                from google.genai import types
            else:
                record(attempts, "veo", "dependencies", "dependency-missing",
                       "google-genai install failed. Run: pip install google-genai")
                return None
        except Exception as exc:
            record(attempts, "veo", "dependencies", "dependency-missing",
                   f"google-genai not installed ({exc}). Run: pip install google-genai")
            return None

    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    if not project:
        # Try AI Studio fallback
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            try:
                client = genai.Client(api_key=api_key)
                backend = "aistudio"
            except Exception as e:
                record(attempts, "veo", "request", "request-error",
                       f"AI Studio init failed: {e}")
                return None
        else:
            record(attempts, "veo", "credentials", "no-credentials",
                   "GOOGLE_CLOUD_PROJECT not set and no GEMINI_API_KEY for the AI Studio fallback")
            return None
    else:
        try:
            client = genai.Client(vertexai=True, project=project, location=location)
            backend = "vertex"
        except Exception as e:
            record(attempts, "veo", "request", "request-error", f"Vertex AI init failed: {e}")
            return None

    try:
        # Build generation config. NOTE: `prompt` is a direct argument of
        # generate_videos, NOT a config field — the SDK rejects it there with
        # a validation error (caught live by the chain's attempt records).
        gen_config = types.GenerateVideosConfig(
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
                model=model,
                prompt=prompt,
                image=image,
                config=gen_config,
            )
        else:
            operation = client.models.generate_videos(
                model=model,
                prompt=prompt,
                config=gen_config,
            )

        # Poll for completion (max 5 minutes)
        timeout = 300
        start = time.time()
        while not operation.done and (time.time() - start) < timeout:
            time.sleep(15)
            operation = client.operations.get(operation)

        if not operation.done:
            record(attempts, "veo", "request", "timeout",
                   "Veo generation timed out after 5 minutes")
            return None

        if operation.result and operation.result.generated_videos:
            video = operation.result.generated_videos[0]
            video_bytes = client.files.download(file=video.video)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(video_bytes)
            return {
                "status": "success",
                "provider": f"veo-{backend}",
                "model": model,
                "output": str(output_path),
                "duration": min(duration, 8),
                "mode": "image-to-video" if image_path else "text-to-video",
            }
        record(attempts, "veo", "response", "bad-response",
               "Veo returned no video (possibly safety-filtered)")
        return None

    except Exception as e:
        record(attempts, "veo", "request", "request-error", f"Veo generation failed: {str(e)[:200]}")
        return None


def generate_video_chain(prompt, output_path, image_path, duration, aspect_ratio="16:9",
                         kling_model=None, veo_model=None, sound=False, preferred=None):
    """Try every configured video provider in order, recording every failed
    attempt. The preferred provider (from routing or --provider) goes first;
    the others remain as fallbacks.

    Before this chain existed, the fallbacks lived inside one provider's
    exception handler: a Veo-routed failure never fell back at all, a missing
    WaveSpeed key aborted the whole run, and the terminal error was one
    80-character string. Now the terminal FAILED payload lists who was tried,
    at which stage each stopped, and what to do about it.
    """
    from provider_failures import failure_payload
    attempts = []
    order = ["kling", "veo", "higgsfield"]
    if preferred in order:
        order.remove(preferred)
        order.insert(0, preferred)
    for prov in order:
        if prov == "kling":
            result = generate_video_kling(prompt, output_path, image_path, None,
                                          duration, model=kling_model, sound=sound,
                                          attempts=attempts)
        elif prov == "veo":
            result = generate_video_veo(prompt, output_path, image_path, duration,
                                        aspect_ratio, model=veo_model, attempts=attempts)
        else:
            result = generate_video_higgsfield(prompt, output_path, image_path,
                                               duration, sound, attempts=attempts)
        if result and result.get("status") == "success":
            if attempts:
                result["fallback_from"] = ", ".join(dict.fromkeys(a["provider"] for a in attempts))
                result["earlier_attempts"] = attempts
            return result
    return failure_payload(attempts, context="video generation")


# ---------------------------------------------------------------------------
# Script and Storyboard generation
# ---------------------------------------------------------------------------

def _mmss(total_seconds):
    """Format seconds as M:SS — rolls over past 59s so SRT conversion stays valid."""
    total_seconds = max(0, int(total_seconds))
    return f"{total_seconds // 60}:{total_seconds % 60:02d}"


def generate_script(post_data, brand_config):
    """Scaffold a video script from post data — structure the agent then fills.

    Two rules are load-bearing and tested:

    1. **The hook opens the video. Never the logo.** The old scaffold spent
       seconds 0-3 on "brand logo reveal" — on a social feed those are the only
       seconds most viewers give, and a logo is the one thing guaranteed not to
       earn the next three. The brand mark lives as a corner watermark
       throughout (video_postprocess adds it) and in the end card.
    2. **Every scene carries a payoff** — what the viewer has gained by the time
       the scene ends. A scene whose payoff is "sets up the next scene" is where
       viewers leave; the field forces the question scene by scene.

    This function stays deterministic scaffolding: the agent running
    /socialforge:generate-video replaces every [FILL] with content from the
    post's actual brief in the brand's voice, and the skill's rules govern that
    pass (pairing with the caption, compliance before credits are spent).
    """
    title = post_data.get("title", "Untitled")
    brief = post_data.get("visual", {}).get("direction_a", "")
    video_type = post_data.get("video_details", {}).get("video_type", "short_reel")
    duration = post_data.get("video_details", {}).get("duration_seconds", 30)

    hook_end = min(3, max(1, duration // 10))
    cta_start = max(hook_end + 2, duration - max(3, duration // 6))
    # Split the middle into 1-3 beats depending on how much room exists.
    middle = cta_start - hook_end
    beat_count = 1 if middle <= 8 else 2 if middle <= 18 else 3
    beat_len = middle / beat_count

    scenes = [{
        "timestamp": f"{_mmss(0)}-{_mmss(hook_end)}",
        "role": "hook",
        "visual": f"[FILL: the single most arresting image this brief supports — {brief[:80]}]",
        "audio": "[FILL: the hook line — lead with the most interesting thing, not a greeting]",
        "text_overlay": "[FILL: 1-5 words of tension — must NOT repeat the caption's first line]",
        "payoff": "Viewer knows exactly why the next seconds are worth staying for",
    }]
    for i in range(beat_count):
        start = hook_end + round(i * beat_len)
        end = hook_end + round((i + 1) * beat_len) if i < beat_count - 1 else cta_start
        scenes.append({
            "timestamp": f"{_mmss(start)}-{_mmss(end)}",
            "role": f"beat-{i + 1}",
            "visual": f"[FILL: what is shown for beat {i + 1}]",
            "audio": f"[FILL: the point beat {i + 1} delivers — a point, not a promise of one]",
            "text_overlay": "[FILL or empty]",
            "payoff": f"[FILL: what the viewer has gained by {_mmss(end)} — no beat ends on setup]",
        })
    scenes.append({
        "timestamp": f"{_mmss(cta_start)}-{_mmss(duration)}",
        "role": "cta-endcard",
        "visual": "[FILL: CTA visual] + brand end card (logo lives HERE, not in the open)",
        "audio": "[FILL: one specific ask — match the platform's CTA mechanism from adapt-copy]",
        "text_overlay": "[FILL: the CTA, 2-6 words]",
        "payoff": "Viewer knows the single next action",
    })

    return {
        "title": title,
        "video_type": video_type,
        "target_duration_seconds": duration,
        "brand": brand_config.get("brand_name", ""),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenes": scenes,
        "script_rules": [
            "hook-first: the open earns attention; the logo never opens (corner watermark + end card only)",
            "payoff-per-scene: no scene ends on setup",
            "pairing: overlay text and the post caption do different jobs and never echo",
            "compliance: the filled script passes compliance_check before any generation credits are spent",
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


def _provider_availability():
    """Which video providers have credentials — checking the STORED profile
    first, then env vars. Routing used to read env vars only, so a user who
    ran /socialforge:setup (keys in credentials.json, no env vars) was told
    'No video API configured' while being fully configured."""
    ws_key = hf_key = hf_secret = None
    google_stored = False
    try:
        from credential_manager import get_wavespeed_key, get_higgsfield_auth, validate_vertex_ai
        ws_key = get_wavespeed_key()
        hf_key, hf_secret = get_higgsfield_auth()
        google_stored = bool(validate_vertex_ai().get("configured"))
    except ImportError:
        ws_key = os.environ.get("WAVESPEED_API_KEY")
        hf_key = os.environ.get("HF_API_KEY")
        hf_secret = os.environ.get("HF_API_SECRET")
    return {
        "wavespeed": bool(ws_key),
        "google": bool(google_stored or os.environ.get("GOOGLE_CLOUD_PROJECT")
                       or os.environ.get("GEMINI_API_KEY")),
        "higgsfield": bool(hf_key and hf_secret),
    }


def route_video_provider(duration_seconds, video_type):
    """Route to the appropriate video provider."""
    # Some video types are live-action by definition — no AI provider can produce them
    production = VIDEO_TYPES.get(video_type, {}).get("production", "")
    if "needs filming" in production:
        return {
            "provider": "none",
            "error": f"Video type '{video_type}' requires filming ({production}).",
            "fallback": "script_and_storyboard_only",
        }

    avail = _provider_availability()
    if duration_seconds <= 8 and avail["google"]:
        return {"provider": "veo", "model": DEFAULT_VEO_MODEL, "max_duration": 8,
                "credentials_found": avail}
    elif avail["wavespeed"]:
        return {"provider": "kling", "model": DEFAULT_KLING_MODEL, "max_duration": 15,
                "credentials_found": avail}
    elif avail["google"]:
        return {"provider": "veo", "model": DEFAULT_VEO_MODEL, "max_duration": 8,
                "credentials_found": avail}
    elif avail["higgsfield"]:
        return {"provider": "higgsfield", "max_duration": 15, "credentials_found": avail}
    else:
        return {
            "provider": "none",
            "error": ("No video provider credentials found — checked the stored credential "
                      "profile and env vars for WaveSpeed, Google (Vertex/AI Studio), and HiggsField. "
                      "Run /socialforge:setup --video or set WAVESPEED_API_KEY / GOOGLE_CLOUD_PROJECT."),
            "credentials_found": avail,
            "fallback": "script_and_storyboard_only",
        }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="SocialForge Video Generator (Kling + Veo)")
    parser.add_argument("--brand", required=False, default="")
    parser.add_argument("--month", required=False, default="")
    parser.add_argument("--post-id", required=False, default="")
    parser.add_argument("--output-dir", required=False, default="")
    parser.add_argument("--generate-video", action="store_true", help="Generate AI video")
    parser.add_argument("--image", default=None, help="Input image for image-to-video")
    parser.add_argument("--provider", default="auto", choices=["auto", "kling", "veo", "higgsfield"],
                        help="Preferred video provider (auto routes by duration and available "
                             "credentials; the others stay as fallbacks in the chain)")
    parser.add_argument("--duration", type=int, default=None, help="Override video duration (seconds)")
    parser.add_argument("--aspect-ratio", default="16:9", help="Video aspect ratio")
    parser.add_argument("--srt", action="store_true", help="Generate SRT subtitle file")
    parser.add_argument("--postprocess", action="store_true",
                        help="Run video post-processing (watermark, resize, subtitles, music)")
    parser.add_argument("--video-input", default=None, help="Existing video to post-process")
    parser.add_argument("--burn-subs", action="store_true", help="Burn SRT subtitles into video")
    parser.add_argument("--music", default=None, help="Background music file to mix in")
    parser.add_argument("--platforms", default=None,
                        help="Comma-separated platforms for resizing (e.g., instagram_reel,linkedin,tiktok)")
    parser.add_argument("--video-model", default=None,
                        help=f"Override video model id. Defaults via curator: kling=`{DEFAULT_KLING_MODEL}` / veo=`{DEFAULT_VEO_MODEL}`. "
                             f"Deprecated ids auto-fall-forward.")
    parser.add_argument("--list-models", action="store_true",
                        help="Print the curated video models and exit")
    args = parser.parse_args()

    if args.list_models:
        if _resolve_model is None:
            print("Model curator not available", file=sys.stderr)
            sys.exit(2)
        from resolve_model import list_models as _ll, get_registry as _gr
        reg = _gr()
        print(f"Video models (registry last_updated: {reg.get('last_updated')})")
        for m in _ll(modality="video-gen", status="current"):
            print(f"  {m['id']:55s}  {m.get('vendor', '?'):10s}  {m.get('display_name', '')}")
        return

    if not (args.brand and args.month and args.post_id and args.output_dir):
        parser.error("--brand, --month, --post-id, and --output-dir are required (unless --list-models is set)")

    # Resolve --video-model via curator (kling uses wavespeed alias; veo uses google alias)
    chosen_kling = _negotiate_video_model(args.video_model, "latest-video-wavespeed") if args.provider in {"auto", "kling"} else None
    chosen_veo = _negotiate_video_model(args.video_model, "latest-video-google") if args.provider in {"auto", "veo"} else None

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

    # Generate video — through the full provider chain. The preferred provider
    # (explicit --provider, else routing's pick) goes first; every other
    # configured provider remains a fallback, and every failed rung is
    # recorded in the result's attempts list.
    video_result = None
    if args.generate_video and routing["provider"] != "none":
        video_path = output_dir / f"post-{args.post_id}-video.mp4"
        prompt = post.get("visual", {}).get("direction_a", post.get("title", ""))
        preferred = args.provider if args.provider != "auto" else routing["provider"]
        video_result = generate_video_chain(prompt, str(video_path), args.image, duration,
                                            args.aspect_ratio, kling_model=chosen_kling,
                                            veo_model=chosen_veo, preferred=preferred)
    elif args.generate_video and routing["provider"] == "none":
        video_result = {"status": "FAILED", "error": routing["error"],
                        "credentials_found": routing.get("credentials_found"),
                        "action_required": True}

    # Post-process video if requested
    postprocess_result = None
    if args.postprocess and video_result and video_result.get("status") == "success":
        try:
            from video_postprocess import postprocess_video
            video_file = video_result.get("output", str(output_dir / f"post-{args.post_id}-video.mp4"))
            platforms_list = args.platforms.split(",") if args.platforms else [p.get("name", p) if isinstance(p, dict) else str(p) for p in post.get("platforms", [])]
            srt_file = str(output_dir / f"post-{args.post_id}-subtitles.srt") if args.burn_subs else None
            postprocess_result = postprocess_video(
                input_path=video_file,
                output_dir=str(output_dir / "platform-versions"),
                brand_config=brand_config,
                platforms=platforms_list,
                srt_path=srt_file,
                music_path=args.music,
                burn_subs=args.burn_subs,
                add_music=bool(args.music),
            )
        except Exception as e:
            postprocess_result = {"status": "FAILED", "error": str(e)}

    # Also handle standalone post-processing of existing video
    if args.postprocess and args.video_input and not args.generate_video:
        try:
            from video_postprocess import postprocess_video
            platforms_list = args.platforms.split(",") if args.platforms else ["linkedin", "instagram_reel"]
            srt_file = str(output_dir / f"post-{args.post_id}-subtitles.srt") if args.burn_subs else None
            postprocess_result = postprocess_video(
                input_path=args.video_input,
                output_dir=str(output_dir / "platform-versions"),
                brand_config=brand_config,
                platforms=platforms_list,
                srt_path=srt_file,
                music_path=args.music,
                burn_subs=args.burn_subs,
                add_music=bool(args.music),
            )
        except Exception as e:
            postprocess_result = {"status": "FAILED", "error": str(e)}

    # Top-level status reflects the worst nested result. It used to say
    # "success" unconditionally, so a caller grepping the top level sailed
    # past a fully-failed video generation.
    overall = "success"
    if video_result and video_result.get("status") == "FAILED":
        overall = "FAILED"
    elif postprocess_result and postprocess_result.get("status") == "FAILED":
        overall = "partial"

    print(json.dumps({
        "status": overall,
        "post_id": args.post_id,
        "video_type": video_type,
        "duration": duration,
        "routing": routing,
        "scenes": len(script["scenes"]),
        "script": str(script_path),
        "storyboard": str(storyboard_path),
        "srt": srt_result,
        "video": video_result or {"status": "not_requested", "note": "Use --generate-video to create AI video"},
        "postprocess": postprocess_result,
    }, indent=2))
    if overall == "FAILED":
        sys.exit(4)  # script/storyboard artifacts exist, but the requested video does not


if __name__ == "__main__":
    main()
