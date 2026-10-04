# render-carousels — prerequisites and output files

Supplementary to `SKILL.md`. Read this when a render fails before the first slide, or the
user asks what files a render leaves behind. Everything below is read from
`scripts/render_carousel.py` and `scripts/install_deps.py`.

## Prerequisites

- A calendar parsed with the carousel posts identified (`calendar-data.json`, see
  `/socialforge:parse-calendar`).
- Playwright and its Chromium build installed. `/socialforge:setup` runs
  `scripts/install_deps.py`, whose `carousel` group installs `playwright` and then
  `python -m playwright install chromium`. If the import still fails, `render_carousel.py`
  returns the manual fix: `pip install playwright && playwright install chromium`.
- Brand colors and fonts set in `brand-config.json`. Missing keys fall back to the
  renderer's built-in default palette and fonts rather than failing, so a half-configured
  brand renders in the wrong colors instead of erroring — confirm the first slide before
  approving the rest.
- A brand may override any template by placing a file with the same name under
  `brands/{brand}/carousel-templates/`; the override wins over the shipped template.

## What a render writes

In the directory passed as `--output-dir` (required; the post's folder in the normal pipeline):

| File | Notes |
|------|-------|
| `slide-01.png`, `slide-02.png`, ... | One PNG per slide at the viewport size (default 1080x1080). |
| `carousel.pdf` | All slides in order, for platforms that take a document upload. Built with Pillow. |

If PDF assembly fails, the PNGs are kept and the result reports `"pdf": null` — treat that
as "slides fine, PDF missing", not as a failed render.
