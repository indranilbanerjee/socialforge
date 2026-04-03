#!/usr/bin/env python3
"""
render_carousel.py — Render HTML carousel templates to PNG slides via Playwright.
Handles template selection, brand variable injection, and PDF assembly.
"""

import argparse
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

TEMPLATE_DIR = PLUGIN_ROOT / "assets" / "carousel-templates"

TEMPLATE_MAP = {
    "generic": "generic-8slide.html",
    "comparison": "comparison-10slide.html",
    "case-study": "case-study-10slide.html",
    "tips": "tips-5slide.html",
    "playbook": "playbook-8slide.html",
    "recap": "recap-6slide.html",
    "data": "data-infographic-6slide.html",
    "quote": "quote-card-single.html",
}


def inject_brand_vars(html_content, brand_config):
    """Replace CSS custom properties with brand values."""
    colors = brand_config.get("colors", {})
    fonts = brand_config.get("fonts", {})

    replacements = {
        "{{brand_primary}}": colors.get("primary", "#0066CC"),
        "{{brand_secondary}}": colors.get("secondary", "#FF6600"),
        "{{brand_accent}}": colors.get("accent", "#00CC66"),
        "{{brand_bg_light}}": colors.get("background_light", "#FFFFFF"),
        "{{brand_bg_dark}}": colors.get("background_dark", "#1A1A1A"),
        "{{brand_text}}": colors.get("text_primary", "#333333"),
        "{{font_heading}}": fonts.get("heading", "Montserrat-Bold"),
        "{{font_body}}": fonts.get("body", "OpenSans-Regular"),
    }

    for placeholder, value in replacements.items():
        html_content = html_content.replace(placeholder, value)

    return html_content


def render_slides(template_type, slides_data, brand, output_dir, width=1080, height=1080):
    """Render carousel slides from HTML template."""
    # Check Playwright availability
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"error": "Playwright not installed. Run: pip install playwright && playwright install chromium"}

    # Load template
    template_file = TEMPLATE_MAP.get(template_type)
    if not template_file:
        return {"error": f"Unknown template: {template_type}", "available": list(TEMPLATE_MAP.keys())}

    template_path = TEMPLATE_DIR / template_file

    # Check brand-specific override
    brand_template = WORKSPACE / "brands" / brand / "carousel-templates" / template_file
    if brand_template.exists():
        template_path = brand_template

    if not template_path.exists():
        return {"error": f"Template not found: {template_path}", "note": "Carousel HTML templates need to be created in assets/carousel-templates/"}

    html_content = template_path.read_text(encoding="utf-8")

    # Load brand config
    config_path = WORKSPACE / "brands" / brand / "brand-config.json"
    brand_config = {}
    if config_path.exists():
        brand_config = json.loads(config_path.read_text(encoding="utf-8"))

    html_content = inject_brand_vars(html_content, brand_config)

    # Render each slide
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})

        for i, slide in enumerate(slides_data):
            # Inject slide content into template
            slide_html = html_content
            for key, value in slide.items():
                slide_html = slide_html.replace(f"{{{{slide_{key}}}}}", str(value))

            page.set_content(slide_html)

            slide_path = output_dir / f"slide-{i+1:02d}.png"
            page.screenshot(path=str(slide_path), full_page=False)
            rendered.append(str(slide_path))

        browser.close()

    # Assemble slides into PDF
    pdf_path = None
    try:
        from PIL import Image
        if rendered:
            slides_pil = [Image.open(s).convert("RGB") for s in rendered]
            pdf_file = output_dir / "carousel.pdf"
            slides_pil[0].save(str(pdf_file), save_all=True, append_images=slides_pil[1:], resolution=150)
            pdf_path = str(pdf_file)
    except Exception:
        pdf_path = None  # PDF assembly failed, PNGs still available

    return {
        "status": "success",
        "slides_rendered": len(rendered),
        "pdf": pdf_path,
        "output_dir": str(output_dir),
        "files": rendered,
        "template": template_type,
        "brand": brand
    }


def main():
    parser = argparse.ArgumentParser(description="SocialForge Carousel Renderer")
    parser.add_argument("--template", required=True, choices=list(TEMPLATE_MAP.keys()),
                        help="Carousel template type")
    parser.add_argument("--slides", required=True, help="JSON file with slide content array")
    parser.add_argument("--brand", required=True, help="Brand slug for theming")
    parser.add_argument("--output-dir", required=True, help="Output directory for slide PNGs")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--list-templates", action="store_true")
    args = parser.parse_args()

    if args.list_templates:
        print(json.dumps(TEMPLATE_MAP, indent=2))
        return

    # Load slides data
    slides_path = Path(args.slides)
    if not slides_path.exists():
        print(json.dumps({"error": f"Slides data file not found: {args.slides}"}))
        sys.exit(1)

    slides_data = json.loads(slides_path.read_text(encoding="utf-8"))

    result = render_slides(args.template, slides_data, args.brand, args.output_dir, args.width, args.height)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
