# Troubleshooting Guide

Common SocialForge errors with causes and fixes.

---

## "Brand not found"

**When:** Any command that requires brand context (most commands).

**Cause:** No `brand-config.json` exists at `~/socialforge-workspace/brands/<brand-slug>/`, or the slug doesn't match.

**Fix:**
1. Run `/sf:brand-setup` to create a new brand profile.
2. If the brand exists, check the slug: `ls ~/socialforge-workspace/brands/` and verify the directory name matches exactly.
3. Ensure `brand-config.json` contains valid JSON with `brand_name` and `brand_slug` fields.

---

## "No assets indexed"

**When:** Visual production phase, or any command referencing the asset index.

**Cause:** `asset-index.json` doesn't exist or contains zero assets.

**Fix:**
1. Run `/sf:index-assets` to scan and index the brand's asset directory.
2. Verify assets exist in the brand's `assets/` folder — the indexer needs actual image files.
3. Check that image files are in supported formats: `.jpg`, `.jpeg`, `.png`, `.webp`.
4. If assets are in a non-standard location, specify the path when running the indexer.

---

## "Image generation failed"

**When:** Phase 4 (Visual Production) using STYLE_REFERENCED or AI_ORIGINAL modes.

**Cause:** API key missing, rate limit hit, or provider outage.

**Fix:**
1. Check `.env` for the relevant API key (`GEMINI_API_KEY`, `FAL_KEY`, `REPLICATE_API_TOKEN`).
2. Check provider status pages for outages.
3. If rate-limited, wait and retry. The pipeline supports resuming from the failed post.
4. Try switching providers: update the post's visual config or set a fallback provider in settings.
5. As a workaround, switch the post to `ASSET_ONLY` or `ANCHOR_COMPOSE` mode using an existing asset.

---

## "Playwright not installed"

**When:** Carousel rendering or gallery build.

**Cause:** Playwright or its Chromium browser binary is not installed.

**Fix:**
1. Install Playwright: `pip install playwright`
2. Install browser binaries: `playwright install chromium`
3. If in a restricted environment (Cowork VM), check that Chromium dependencies are available. Run `playwright install-deps` for system-level dependencies.
4. Verify installation: `python -c "from playwright.sync_api import sync_playwright; print('OK')"`

---

## "API key missing"

**When:** Any operation requiring an external service (image generation, MCP connectors).

**Cause:** The required API key is not set in `.env`.

**Fix:**
1. Identify which key is needed from the error message.
2. Add it to `.env` in the project root:
   ```
   FAL_KEY=your-key-here
   REPLICATE_API_TOKEN=your-token-here
   GEMINI_API_KEY=your-key-here
   ```
3. Restart the session after updating `.env`.
4. For MCP connectors (Slack, Notion, etc.), follow `/sf:connect <name>` for OAuth setup — these don't use `.env` keys.

---

## "Compliance blocked"

**When:** Phase 6 (Compliance Check) or during review.

**Cause:** Post content triggered a `"block"` severity rule in `compliance-rules.json`.

**Fix:**
1. Read the error details — it will identify the banned phrase or rule that triggered.
2. Check `compliance-rules.json` for the specific rule and its `suggestion` field.
3. Revise the copy using the suggested replacement.
4. If the rule is a false positive, update `compliance-rules.json` to adjust the `match_type` or change severity to `"warn"`.
5. Re-run compliance check after editing.

---

## "Gallery build failed"

**When:** Phase 7 (Gallery Build) — assembling the visual review gallery.

**Cause:** Missing image files, Playwright failure, or file path issues.

**Fix:**
1. Check that all posts in `status-tracker.json` marked `approved` have image files at their expected paths.
2. Verify Playwright is installed (see "Playwright not installed" above).
3. Check disk space — gallery builds generate multiple image variants.
4. Look for path issues: Windows backslashes vs. forward slashes in file references.
5. Re-run the gallery build. It will skip already-rendered posts and only process missing ones.

---

## "DOCX assembly failed"

**When:** Phase 8 (Export) when generating the content calendar DOCX.

**Cause:** Missing Python dependency (`python-docx`), or template file not found.

**Fix:**
1. Install the dependency: `pip install python-docx`
2. Verify the DOCX template exists in the expected location.
3. Check that all posts referenced in the export have complete data (copy, visual paths, metadata).
4. If a specific post causes failure, check its entry in `status-tracker.json` for missing fields.
5. Try exporting without the problematic post by setting its status to `"blocked"`.

---

## General Debugging Steps

1. **Check status tracker** — `status-tracker.json` shows exactly where the pipeline stopped.
2. **Check brand config** — Most errors trace back to missing or malformed `brand-config.json`.
3. **Check file paths** — Use forward slashes. Verify files exist at referenced paths.
4. **Check dependencies** — `pip install playwright python-docx gspread pillow` covers most needs.
5. **Resume, don't restart** — The pipeline is designed to resume from the last successful phase. You rarely need to start over.

---

## "Background removal failed" / rembg not available

**When:** compose_image.py remove-bg fails in Cowork or restricted environments
**Cause:** rembg requires C-extension libraries that may not compile in all environments
**Fix:**
1. **Automatic fallback:** Script falls back to basic white-background removal (threshold-based). Works for product-on-white images.
2. **Manual:** Upload pre-masked images (PNG with alpha channel) — skip background removal entirely
3. **Claude Code:** `pip install rembg` works in full Claude Code environments
