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
_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("PLUGIN_DATA") or ""
if _plugin_data and Path(_plugin_data).exists():
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
    WORKSPACE = Path.home() / "socialforge-workspace"
# Optional per-platform mockup overrides: assets/preview-templates/<platform>.html
# with {{name}} / {{handle}} / {{platform}} / {{image_uri}} / {{copy}} placeholders.
TEMPLATE_DIR = PLUGIN_ROOT / "assets" / "preview-templates"


def render_preview(image_path, copy_text, platform, brand, output_path,
                   allow_missing_image=False):
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

    # A missing image used to sail straight through: the path became a file://
    # URI, the browser rendered a broken image as blank white, and this function
    # returned {"status": "success"} for a preview containing nothing. A reviewer
    # approving that gallery would be approving an empty rectangle. Refuse
    # instead — this is the exact failure mode the plugin claims is impossible.
    resolved = Path(image_path).resolve()
    missing = not resolved.is_file()
    if missing and not allow_missing_image:
        return {
            "status": "FAILED",
            "error": f"image not found: {resolved}",
            "stage": "input",
            "reason": "missing-image",
            "detail": ("render_preview was given a path that does not exist. Rendering it "
                       "would produce a blank preview that looks like a successful render."),
            "next_steps": [
                "Generate or match the image first (/socialforge:compose-creative or /socialforge:match-assets).",
                "To preview copy layout without artwork, pass --allow-missing-image "
                "— the preview is then explicitly marked as having no artwork.",
            ],
            "platform": platform, "brand": brand, "action_required": True,
        }
    image_uri = "" if missing else html_lib.escape(resolved.as_uri())

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

    if missing:
        # Explicitly opted into rendering without artwork. This is never
        # "success" — a reviewer must be able to tell a finished preview from a
        # copy-layout mockup by reading one field.
        return {"status": "placeholder", "output": str(output_path),
                "platform": platform, "brand": brand,
                "warning": ("Copy-layout preview only — no artwork was rendered. "
                            "Do not treat this as an approved creative."),
                "action_required": True}
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
    parser.add_argument("--allow-missing-image", action="store_true",
                        help="Render a copy-layout preview with no artwork. The result is "
                             "marked status=placeholder, never success.")
    args = parser.parse_args()

    result = render_preview(args.image, args.copy, args.platform, args.brand, args.output,
                            allow_missing_image=args.allow_missing_image)
    print(json.dumps(result, indent=2))
    # Exit codes are a contract: a caller in an && chain must not read a failed
    # render as a successful one. 0 clean, 1 refused.
    sys.exit(0 if result.get("status") in ("success", "placeholder") else 1)


if __name__ == "__main__":
    main()
