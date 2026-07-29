#!/usr/bin/env python3
"""
render_preview.py — Render platform mockup previews via Playwright.
Shows how posts will look when published on each social platform.
"""

import argparse
import html as html_lib
import json
import os
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
if _plugin_data and Path(_plugin_data).exists():
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
    WORKSPACE = Path.home() / "socialforge-workspace"
# Optional per-platform mockup overrides: assets/preview-templates/<platform>.html
# with {{name}} / {{handle}} / {{platform}} / {{image_uri}} / {{copy}} placeholders.
TEMPLATE_DIR = PLUGIN_ROOT / "assets" / "preview-templates"


def render_preview(image_path, copy_text, platform, brand, output_path):
    """Render a platform preview mockup."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"error": "Playwright not installed. Run: pip install playwright && playwright install chromium"}

    # Load brand config for profile info
    config_path = WORKSPACE / "brands" / brand / "brand-config.json"
    profile = {"name": brand, "handle": f"@{brand}", "avatar": "", "headline": ""}
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        profiles = config.get("social_profiles", {})
        if platform in profiles:
            profile = profiles[platform]

    # Every interpolated value is escaped — post copy and brand values are untrusted
    # text and must not be able to inject markup into the preview reviewers approve.
    name = html_lib.escape(str(profile.get("name", brand)))
    handle = html_lib.escape(str(profile.get("handle", "@" + brand)))
    platform_label = html_lib.escape(platform.upper())
    copy_html = html_lib.escape(copy_text[:500])
    image_uri = html_lib.escape(Path(image_path).resolve().as_uri())

    # Per-platform template if one exists, otherwise the inline mockup below
    template_path = TEMPLATE_DIR / f"{platform}.html"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
        for placeholder, value in (("{{name}}", name), ("{{handle}}", handle),
                                   ("{{platform}}", platform_label),
                                   ("{{image_uri}}", image_uri), ("{{copy}}", copy_html)):
            template = template.replace(placeholder, value)
        html = template
    else:
        html = build_default_html(name, handle, platform_label, image_uri, copy_html)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 600, "height": 800})
        page.set_content(html)
        page.wait_for_timeout(500)
        page.screenshot(path=str(output_path), full_page=True)
        browser.close()

    return {"status": "success", "output": str(output_path), "platform": platform, "brand": brand}


def build_default_html(name, handle, platform_label, image_uri, copy_html):
    """Inline mockup used when no per-platform template is present."""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ margin: 0; background: #f5f5f5; font-family: -apple-system, sans-serif; }}
  .card {{ background: white; max-width: 500px; margin: 20px auto; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .header {{ display: flex; align-items: center; padding: 12px 16px; gap: 10px; }}
  .avatar {{ width: 40px; height: 40px; border-radius: 50%; background: #ddd; }}
  .name {{ font-weight: 600; font-size: 14px; }}
  .handle {{ color: #666; font-size: 12px; }}
  .image {{ width: 100%; }}
  .copy {{ padding: 12px 16px; font-size: 14px; line-height: 1.5; color: #333; }}
  .platform-badge {{ position: absolute; top: 10px; right: 10px; background: #333; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; }}
  .wrapper {{ position: relative; }}
</style></head><body>
<div class="card">
  <div class="header">
    <div class="avatar"></div>
    <div><div class="name">{name}</div><div class="handle">{handle}</div></div>
  </div>
  <div class="wrapper">
    <img class="image" src="{image_uri}" />
    <div class="platform-badge">{platform_label}</div>
  </div>
  <div class="copy">{copy_html}</div>
</div></body></html>"""


def main():
    parser = argparse.ArgumentParser(description="SocialForge Preview Renderer")
    parser.add_argument("--image", required=True, help="Post image path")
    parser.add_argument("--copy", required=True, help="Post copy text")
    parser.add_argument("--platform", required=True)
    parser.add_argument("--brand", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = render_preview(args.image, args.copy, args.platform, args.brand, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
