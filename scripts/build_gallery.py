#!/usr/bin/env python3
"""
build_gallery.py — Build interactive HTML review gallery.
Creates a self-contained HTML file with all post previews, scores, and copy.
"""

import argparse
import base64
import html as html_lib
import json
import os
import sys
from pathlib import Path

# Persistent storage: prefer ${CLAUDE_PLUGIN_DATA} (survives sessions/updates),
# fall back to ~/socialforge-workspace (legacy/local)
_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
if _plugin_data and Path(_plugin_data).exists():
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
    WORKSPACE = Path.home() / "socialforge-workspace"


def file_to_base64(file_path, mime_type=None):
    """Convert a file to base64 data URI."""
    path = Path(file_path)
    if not path.exists():
        return ""
    data = base64.b64encode(path.read_bytes()).decode()
    if not mime_type:
        ext = path.suffix.lower().lstrip(".")
        mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                    "gif": "image/gif", "mp4": "video/mp4", "webm": "video/webm"}
        mime_type = mime_map.get(ext, "application/octet-stream")
    return f"data:{mime_type};base64,{data}"


def image_to_base64(img_path):
    """Convert image to base64 data URI."""
    return file_to_base64(img_path)


IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
VIDEO_EXTS = (".mp4", ".webm", ".mov")


# status_manager provides the canonical per-post folder naming. If it cannot
# be imported the WHOLE gallery degrades to the legacy flat layout — that is a
# run-level event and is surfaced once in the output, not silently swallowed
# per post.
try:
    from status_manager import get_post_folder_name, get_week_number
    _SM_IMPORT_ERROR = None
except ImportError as _e:  # pragma: no cover
    get_post_folder_name = get_week_number = None
    _SM_IMPORT_ERROR = str(_e)


def find_post_dir(month_dir, post):
    """Locate the per-post production folder written by status_manager.init_post_folder.

    Layout: production/week-{N}/{PostID}-{date}-{platforms}-{tier}-{ctype}/
    """
    if get_post_folder_name is None:
        return None

    week = get_week_number(post.get("date", ""))
    candidate = month_dir / "production" / f"week-{week}" / get_post_folder_name(post)
    if candidate.exists():
        return candidate

    # Folder-name fields (platforms/tier/content_type) may have changed since creation —
    # fall back to a prefix match on the post id across every week.
    pid = str(post.get("post_id", ""))
    production = month_dir / "production"
    if pid and production.exists():
        for week_dir in sorted(production.glob("week-*")):
            for d in sorted(week_dir.iterdir()):
                if d.is_dir() and d.name.startswith(f"{pid}-"):
                    return d
    return None


def first_media(dirs, exts):
    """Return the first media file with one of `exts` across `dirs`, in order."""
    for d in dirs:
        if not d or not d.exists():
            continue
        for f in sorted(d.iterdir()):
            if f.is_file() and f.suffix.lower() in exts:
                return str(f)
    return ""


def platform_label(p):
    """Platform entries are keyed by `key` in the calendar schema."""
    if isinstance(p, dict):
        return str(p.get("key") or p.get("name") or "")
    return str(p)


def build_gallery(brand, month):
    """Build the review gallery HTML."""
    month_dir = WORKSPACE / "output" / brand / month
    tracker_path = month_dir / "status-tracker.json"
    calendar_path = month_dir / "calendar-data.json"

    if not tracker_path.exists() or not calendar_path.exists():
        print(json.dumps({"error": "Status tracker or calendar not found"}))
        sys.exit(1)

    tracker = json.loads(tracker_path.read_text(encoding="utf-8"))
    calendar = json.loads(calendar_path.read_text(encoding="utf-8"))

    posts_data = []
    for post in calendar.get("posts", []):
        pid = str(post.get("post_id", ""))
        status_info = tracker.get("posts", {}).get(pid, {})

        # Per-post folder written by status_manager.init_post_folder
        post_dir = find_post_dir(month_dir, post)
        final_dir = post_dir / "final" if post_dir else None
        versions_dir = post_dir / "versions" if post_dir else None
        post_copy_dir = post_dir / "copy" if post_dir else None

        # Find generated image — approved final first, then the latest version.
        # Legacy flat production/images/ is still honoured as a fallback.
        image_path = first_media([final_dir, versions_dir], IMAGE_EXTS)
        if not image_path:
            images_dir = month_dir / "production" / "images"
            for pattern in [f"post-{pid}-variant-a*.png", f"post-{pid}-*.png"]:
                matches = list(images_dir.glob(pattern)) if images_dir.exists() else []
                if matches:
                    image_path = str(matches[0])
                    break

        # Find copy
        copy_text = ""
        copy_file = None
        if post_copy_dir and post_copy_dir.exists():
            txts = sorted(f for f in post_copy_dir.iterdir() if f.is_file() and f.suffix.lower() == ".txt")
            preferred = [f for f in txts if "linkedin" in f.name.lower()]
            if preferred or txts:
                copy_file = (preferred or txts)[0]
        if copy_file is None:
            copy_dir = month_dir / "production" / "copy"
            candidate = copy_dir / f"post-{pid}-linkedin-copy.txt"
            if candidate.exists():
                copy_file = candidate
            elif copy_dir.exists():
                for cf in copy_dir.glob(f"post-{pid}-*-copy.txt"):
                    copy_file = cf
                    break
        if copy_file is not None and copy_file.exists():
            copy_text = copy_file.read_text(encoding="utf-8")

        # Find video files
        video_path = first_media([final_dir, versions_dir], VIDEO_EXTS)
        if not video_path:
            videos_dir = month_dir / "production" / "videos"
            if videos_dir.exists():
                for vp in [f"post-{pid}-video.mp4", f"post-{pid}-video.webm"]:
                    vf = videos_dir / vp
                    if vf.exists():
                        video_path = str(vf)
                        break

        # Find video alternatives for comparison
        alt_video_path = ""
        if video_path and versions_dir and versions_dir.exists():
            for av in sorted(versions_dir.iterdir()):
                if av.is_file() and av.suffix.lower() in VIDEO_EXTS and str(av) != video_path:
                    alt_video_path = str(av)
                    break
        if not alt_video_path:
            alt_dir = month_dir / "production" / "alternatives"
            if alt_dir.exists():
                for av in alt_dir.glob(f"post-{pid}-video-v*.mp4"):
                    alt_video_path = str(av)
                    break

        posts_data.append({
            "id": pid,
            "title": post.get("title", f"Post {pid}"),
            "date": post.get("date", ""),
            "tier": post.get("tier", ""),
            "platforms": [platform_label(p) for p in post.get("platforms", [])],
            "content_type": post.get("content_type", "static"),
            "status": status_info.get("status", "QUEUED"),
            "creative_mode": status_info.get("creative_mode", ""),
            "image_b64": image_to_base64(image_path) if image_path else "",
            "video_path": video_path,
            "alt_video_path": alt_video_path,
            "copy": copy_text[:500],
            "quality_score": None
        })

    # Build HTML. Every calendar/tracker-supplied string is escaped: this
    # gallery is the artifact humans approve from, and calendar data comes
    # from client documents — a '<' in a title must not break the card, and
    # markup in any field must never execute in the reviewer's browser.
    esc = html_lib.escape
    cards_html = ""
    for p in posts_data:
        # Build visual: video takes priority over image
        if p.get("video_path"):
            vid_b64 = file_to_base64(p["video_path"])
            img_tag = f'<video src="{vid_b64}" controls style="width:100%;border-radius:4px;" preload="metadata"></video>' if vid_b64 else ""
            if p.get("alt_video_path"):
                alt_b64 = file_to_base64(p["alt_video_path"])
                if alt_b64:
                    img_tag += f'<div style="margin-top:8px;font-size:11px;color:#666;">Alternative:</div><video src="{alt_b64}" controls style="width:100%;border-radius:4px;" preload="metadata"></video>'
            if not img_tag:
                # file_to_base64 returns "" only when the file is missing or
                # unreadable — say that, never invent a different reason.
                img_tag = ('<div style="width:100%;height:200px;background:#eee;border-radius:4px;display:flex;align-items:center;justify-content:center;color:#999;">'
                           f'Video file missing or unreadable: {esc(Path(p["video_path"]).name)}</div>')
        elif p["image_b64"]:
            img_tag = f'<img src="{p["image_b64"]}" style="width:100%;border-radius:4px;" />'
        else:
            img_tag = '<div style="width:100%;height:200px;background:#eee;border-radius:4px;display:flex;align-items:center;justify-content:center;color:#999;">No image</div>'
        tier_color = {"HERO": "#e74c3c", "HUB": "#3498db", "HYGIENE": "#2ecc71"}.get(p["tier"], "#999")

        cards_html += f"""
        <div class="card" data-tier="{esc(p['tier'])}" data-status="{esc(p['status'])}">
          <div class="card-header">
            <span class="post-id">P{esc(p['id'])}</span>
            <span class="tier" style="background:{tier_color}">{esc(p['tier'])}</span>
            <span class="status">{esc(p['status'])}</span>
          </div>
          {img_tag}
          <div class="card-body">
            <strong>{esc(p['title'])}</strong>
            <div class="meta">{esc(p['date'])} | {esc(', '.join(p['platforms']))} | {esc(p['content_type'])}</div>
            <div class="copy-preview">{esc(p['copy'][:200])}...</div>
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>SocialForge Review — {esc(brand)} / {esc(month)}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f0f2f5; padding: 20px; }}
  h1 {{ margin-bottom: 20px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }}
  .card {{ background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .card-header {{ display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-bottom: 1px solid #eee; }}
  .post-id {{ font-weight: 700; font-size: 14px; }}
  .tier {{ color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
  .status {{ margin-left: auto; font-size: 11px; color: #666; }}
  .card-body {{ padding: 12px; }}
  .meta {{ font-size: 12px; color: #666; margin: 4px 0 8px; }}
  .copy-preview {{ font-size: 13px; color: #444; line-height: 1.4; }}
  .summary {{ background: white; padding: 16px; border-radius: 8px; margin-bottom: 20px; display: flex; gap: 24px; }}
  .stat {{ text-align: center; }}
  .stat-num {{ font-size: 28px; font-weight: 700; }}
  .stat-label {{ font-size: 12px; color: #666; }}
</style></head><body>
<h1>SocialForge Review — {esc(brand)} / {esc(month)}</h1>
<div class="summary">
  <div class="stat"><div class="stat-num">{len(posts_data)}</div><div class="stat-label">Total Posts</div></div>
  <div class="stat"><div class="stat-num">{sum(1 for p in posts_data if p['image_b64'])}</div><div class="stat-label">Images</div></div>
  <div class="stat"><div class="stat-num">{sum(1 for p in posts_data if p.get('video_path'))}</div><div class="stat-label">Videos</div></div>
  <div class="stat"><div class="stat-num">{sum(1 for p in posts_data if p['tier']=='HERO')}</div><div class="stat-label">HERO</div></div>
  <div class="stat"><div class="stat-num">{sum(1 for p in posts_data if p['tier']=='HUB')}</div><div class="stat-label">HUB</div></div>
  <div class="stat"><div class="stat-num">{sum(1 for p in posts_data if p['tier']=='HYGIENE')}</div><div class="stat-label">HYGIENE</div></div>
</div>
<div class="grid">{cards_html}</div>
</body></html>"""

    output_path = month_dir / "review" / "gallery.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    summary = {
        "status": "success",
        "output": str(output_path),
        "posts": len(posts_data),
        "images_embedded": sum(1 for p in posts_data if p["image_b64"]),
        "brand": brand,
        "month": month
    }
    # Name the posts that rendered with no media at all — a bare embed count
    # reads as "covered everything" when it didn't.
    no_media = [p["id"] for p in posts_data if not p["image_b64"] and not p.get("video_path")]
    if no_media:
        summary["posts_without_media"] = no_media
    if _SM_IMPORT_ERROR:
        summary["warning"] = (f"status_manager not importable ({_SM_IMPORT_ERROR}) — "
                              "per-post production folders were not searched; legacy flat layout only")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description="SocialForge Gallery Builder")
    parser.add_argument("--brand", required=True)
    parser.add_argument("--month", required=True)
    args = parser.parse_args()

    build_gallery(args.brand, args.month)


if __name__ == "__main__":
    main()
