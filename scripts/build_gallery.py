#!/usr/bin/env python3
"""
build_gallery.py — Build interactive HTML review gallery.
Creates a self-contained HTML file with all post previews, scores, and copy.
"""

import argparse
import base64
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


def image_to_base64(img_path):
    """Convert image to base64 data URI."""
    path = Path(img_path)
    if not path.exists():
        return ""
    data = base64.b64encode(path.read_bytes()).decode()
    ext = path.suffix.lower().lstrip(".")
    mime = f"image/{'jpeg' if ext in ['jpg', 'jpeg'] else ext}"
    return f"data:{mime};base64,{data}"


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

        # Find generated image
        images_dir = month_dir / "production" / "images"
        image_path = ""
        for pattern in [f"post-{pid}-variant-a*.png", f"post-{pid}-*.png"]:
            matches = list(images_dir.glob(pattern)) if images_dir.exists() else []
            if matches:
                image_path = str(matches[0])
                break

        # Find copy
        copy_dir = month_dir / "production" / "copy"
        copy_text = ""
        copy_file = copy_dir / f"post-{pid}-linkedin-copy.txt"
        if not copy_file.exists():
            for cf in (copy_dir.glob(f"post-{pid}-*-copy.txt") if copy_dir.exists() else []):
                copy_file = cf
                break
        if copy_file.exists():
            copy_text = copy_file.read_text(encoding="utf-8")

        posts_data.append({
            "id": pid,
            "title": post.get("title", f"Post {pid}"),
            "date": post.get("date", ""),
            "tier": post.get("tier", ""),
            "platforms": [p.get("name", "") for p in post.get("platforms", [])],
            "content_type": post.get("content_type", "static"),
            "status": status_info.get("status", "QUEUED"),
            "creative_mode": status_info.get("creative_mode", ""),
            "image_b64": image_to_base64(image_path) if image_path else "",
            "copy": copy_text[:500],
            "quality_score": None
        })

    # Build HTML
    cards_html = ""
    for p in posts_data:
        img_tag = f'<img src="{p["image_b64"]}" style="width:100%;border-radius:4px;" />' if p["image_b64"] else '<div style="width:100%;height:200px;background:#eee;border-radius:4px;display:flex;align-items:center;justify-content:center;color:#999;">No image</div>'
        tier_color = {"HERO": "#e74c3c", "HUB": "#3498db", "HYGIENE": "#2ecc71"}.get(p["tier"], "#999")

        cards_html += f"""
        <div class="card" data-tier="{p['tier']}" data-status="{p['status']}">
          <div class="card-header">
            <span class="post-id">P{p['id']}</span>
            <span class="tier" style="background:{tier_color}">{p['tier']}</span>
            <span class="status">{p['status']}</span>
          </div>
          {img_tag}
          <div class="card-body">
            <strong>{p['title']}</strong>
            <div class="meta">{p['date']} | {', '.join(p['platforms'])} | {p['content_type']}</div>
            <div class="copy-preview">{p['copy'][:200]}...</div>
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>SocialForge Review — {brand} / {month}</title>
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
<h1>SocialForge Review — {brand} / {month}</h1>
<div class="summary">
  <div class="stat"><div class="stat-num">{len(posts_data)}</div><div class="stat-label">Total Posts</div></div>
  <div class="stat"><div class="stat-num">{sum(1 for p in posts_data if p['image_b64'])}</div><div class="stat-label">Images Ready</div></div>
  <div class="stat"><div class="stat-num">{sum(1 for p in posts_data if p['tier']=='HERO')}</div><div class="stat-label">HERO</div></div>
  <div class="stat"><div class="stat-num">{sum(1 for p in posts_data if p['tier']=='HUB')}</div><div class="stat-label">HUB</div></div>
  <div class="stat"><div class="stat-num">{sum(1 for p in posts_data if p['tier']=='HYGIENE')}</div><div class="stat-label">HYGIENE</div></div>
</div>
<div class="grid">{cards_html}</div>
</body></html>"""

    output_path = month_dir / "review" / "gallery.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    print(json.dumps({
        "status": "success",
        "output": str(output_path),
        "posts": len(posts_data),
        "images_embedded": sum(1 for p in posts_data if p["image_b64"]),
        "brand": brand,
        "month": month
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description="SocialForge Gallery Builder")
    parser.add_argument("--brand", required=True)
    parser.add_argument("--month", required=True)
    args = parser.parse_args()

    build_gallery(args.brand, args.month)


if __name__ == "__main__":
    main()
