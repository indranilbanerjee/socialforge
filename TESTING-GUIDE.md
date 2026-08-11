# SocialForge Testing Guide

**Version:** 1.13.1
**Last Updated:** July 2026
**Format:** Checklist — work through each section top to bottom.

---

## 1. Test Environment Setup

- [ ] Python 3.10+ available | `python3 --version` returns 3.10+
- [ ] Node.js 18+ available | `node --version` returns 18+
- [ ] Playwright installed | `python -c "from playwright.sync_api import sync_playwright; print('OK')"` prints OK
- [ ] Chromium binary installed | `playwright install chromium` completes without error
- [ ] python-docx installed | `python -c "import docx; print('OK')"` prints OK
- [ ] Pillow installed | `python -c "from PIL import Image; print('OK')"` prints OK
- [ ] At least one AI image API key set in `.env` | `FAL_KEY`, `REPLICATE_API_TOKEN`, or `GEMINI_API_KEY`
- [ ] Test brand asset folder prepared | Minimum 10 images (JPG/PNG/WEBP, 800x800+)
- [ ] Test calendar prepared | DOCX or XLSX with 5-10 posts across HERO/HUB/HYGIENE tiers

---

## 2. Installation Tests

### Marketplace Install
- [ ] `claude plugin marketplace add indranilbanerjee/neels-plugins` succeeds | No errors
- [ ] `claude plugin install socialforge@neels-plugins` succeeds | Plugin appears in installed list

### GitHub Install
- [ ] `claude plugin install github:indranilbanerjee/socialforge` succeeds | Plugin appears in installed list

### Local Install
- [ ] `claude plugins add /path/to/socialforge` succeeds | Plugin appears in installed list

### Post-Install Verification
- [ ] No welcome banner appears on session start | Correct — the 4 global hooks were removed in v1.5.0
- [ ] `/socialforge:status` reports credential state on demand | Shows "No active brand" or brand status, plus Vertex AI / WaveSpeed credential state
- [ ] Commands appear in Customize panel | Count matches expected 25
- [ ] Skills appear in Skills section | Count matches expected 16
- [ ] `.mcp.json` has zero active servers by design | `{"mcpServers":{}}`; no MCP initialization errors in logs. The 10-connector catalog lives in `.mcp.json.connectors-reference` and is opt-in.

---

## 3. Command Tests

All 25 shipped commands:

| # | Command | Test Action | Expected Result |
|---|---------|------------|-----------------|
| 1 | `/socialforge:setup` | Run credential setup | Wizard prompts for Vertex AI JSON path + WaveSpeed key |
| 2 | `/socialforge:brand-setup test-brand` | Run with test brand name | Interactive wizard starts, `brand-config.json` created |
| 3 | `/socialforge:switch-brand test-brand` | Switch to existing brand | Active brand changes, confirmed in status |
| 4 | `/socialforge:index-assets test-brand` | Index test asset folder | `asset-index.json` created with per-image metadata |
| 5 | `/socialforge:new-month test-brand 2026-04` | Start April production | Calendar prompt or data initialized |
| 6 | `/socialforge:parse-calendar test.xlsx` | Parse test calendar | `calendar-data.json` created with post entries |
| 7 | `/socialforge:sync-calendar` | Re-read the calendar source | Existing approved posts preserved, new posts added |
| 8 | `/socialforge:match-assets --brand test-brand` | Match assets to posts | Each post gets an asset + creative mode |
| 9 | `/socialforge:generate-all` | Run full production | All posts processed, images generated |
| 10 | `/socialforge:generate-post <post-id>` | Generate single post | One post's creative produced |
| 11 | `/socialforge:adapt-copy --all` | Adapt copy per platform | Platform variants respect character limits |
| 12 | `/socialforge:render-carousels --post <post-id>` | Render carousel slides | Slide PNGs + carousel.pdf produced |
| 13 | `/socialforge:edit-post <post-id> --copy` | Edit post copy | Copy updated in calendar data |
| 14 | `/socialforge:edit-image <post-id> "warmer tones"` | Edit generated image | Image regenerated with instruction |
| 15 | `/socialforge:swap-asset <post-id> --browse` | Browse and swap asset | Asset replaced, image regenerated |
| 16 | `/socialforge:preview-batch` | Generate previews | Platform mockups created for all posts |
| 17 | `/socialforge:review` | Open review gallery | HTML gallery renders with all posts |
| 18 | `/socialforge:revision <post-id> "feedback"` | Apply revision | Affected elements regenerated |
| 19 | `/socialforge:check-approvals` | Check approval status | Pending approvals listed by tier |
| 20 | `/socialforge:client-review --tier HERO` | Send for client review | Posts sent via Slack/email or export prepared |
| 21 | `/socialforge:assemble-document` | Create delivery DOCX | Valid .docx with all posts, images, and schedule |
| 22 | `/socialforge:finalize` | Finalize month | Delivery folder created with all assets |
| 23 | `/socialforge:reactive-post "trending topic"` | Create reactive post | New post created outside calendar |
| 24 | `/socialforge:status` | Check status | Shows brand, month, post counts, pipeline phase |
| 25 | `/socialforge:cost-report` | Check costs | API cost breakdown displayed |

---

## 4. Skill Tests

| # | Skill | Test Scenario | Expected Result |
|---|-------|--------------|-----------------|
| 1 | `brand-manager` | Create brand, update colors, switch brands | brand-config.json reflects changes |
| 2 | `parse-calendar` | Parse DOCX with 10 posts | calendar-data.json has 10 post objects with correct fields |
| 3 | `parse-calendar` | Parse XLSX with mixed tiers | Tiers correctly assigned (HERO/HUB/HYGIENE) |
| 4 | `index-assets` | Index folder with 20 images | asset-index.json has 20 entries with descriptions and tags |
| 5 | `match-assets` | Match assets to 10 posts | Each post assigned an asset and creative mode |
| 6 | `compose-creative` | ANCHOR_COMPOSE with product photo | Brand photo untouched at center, AI background around it |
| 7 | `compose-creative` | STYLE_REFERENCED with no asset | New image generated matching brand style palette |
| 8 | `compose-creative` | PURE_CREATIVE for abstract post | Image generated from text prompt + brand colors |
| 9 | `adapt-copy` | Adapt 500-word copy for X/Twitter | Output respects 280 char limit, hashtags adjusted |
| 10 | `render-carousels` | Render tips-5slide template | 5-slide carousel PNG/PDF produced with brand styling |
| 11 | `create-previews` | Preview for LinkedIn + Instagram | Mockups show correct dimensions per platform |
| 12 | `manage-reviews` | Approve HERO post → check escalation | Approval recorded, moves to client review stage |
| 13 | `build-review-gallery` | Build gallery for 10 posts | HTML file renders with all 10 posts, images load |
| 14 | `finalize-month` | Finalize with all approved | Delivery folder with images/, carousels/, copy/, calendar.docx |
| 15 | `assemble-document` | Generate DOCX | Valid .docx opens in Word/LibreOffice with all posts |
| 16 | `full-pipeline` | End-to-end for 5-post calendar | All phases complete, gallery and delivery produced |
| 17 | `generate-video` | Generate video script for a post | Script, storyboard, and optional AI clip produced |

---

## 5. Script Tests

Run each script from the command line to verify it executes without import errors. The repo ships **22 Python scripts plus `assemble_docx.js`**.

| # | Script | CLI Test | Expected Result |
|---|--------|---------|-----------------|
| 1 | `adapt_copy.py` | `python3 scripts/adapt_copy.py --help` | Usage info or no import errors |
| 2 | `assemble_docx.js` | `node scripts/assemble_docx.js --help` | Usage info or no import errors |
| 3 | `build_gallery.py` | `python3 scripts/build_gallery.py --help` | Usage info displayed |
| 4 | `c2pa_sign.py` | `python3 scripts/c2pa_sign.py --help` | Usage info displayed |
| 5 | `compliance_check.py` | `python3 scripts/compliance_check.py --help` | Usage info displayed |
| 6 | `compose_image.py` | `python3 scripts/compose_image.py --help` | Usage info displayed |
| 7 | `compose_text_overlay.py` | `python3 scripts/compose_text_overlay.py --help` | Usage info displayed |
| 8 | `cost_tracker.py` | `python3 scripts/cost_tracker.py --help` | Usage info displayed |
| 9 | `credential_manager.py` | `python3 scripts/credential_manager.py --help` | Usage info displayed |
| 10 | `edit_image.py` | `python3 scripts/edit_image.py --help` | Usage info displayed |
| 11 | `generate_image.py` | `python3 scripts/generate_image.py --help` | Usage info displayed |
| 12 | `generate_video.py` | `python3 scripts/generate_video.py --help` | Usage info displayed |
| 13 | `index_assets.py` | `python3 scripts/index_assets.py --help` | Usage info displayed |
| 14 | `install_deps.py` | `python3 scripts/install_deps.py --help` | Usage info displayed |
| 15 | `match_assets.py` | `python3 scripts/match_assets.py --help` | Usage info displayed |
| 16 | `refresh_models.py` | `python3 scripts/refresh_models.py --help` | Usage info displayed |
| 17 | `render_carousel.py` | `python3 scripts/render_carousel.py --help` | Usage info displayed |
| 18 | `render_preview.py` | `python3 scripts/render_preview.py --help` | Usage info displayed |
| 19 | `resize_image.py` | `python3 scripts/resize_image.py --help` | Usage info displayed |
| 20 | `resolve_model.py` | `python3 scripts/resolve_model.py --aliases` | Alias table printed from the registry |
| 21 | `status_manager.py` | `python3 scripts/status_manager.py --help` | Usage info displayed |
| 22 | `verify_brand_colors.py` | `python3 scripts/verify_brand_colors.py --help` | Usage info displayed |
| 23 | `video_postprocess.py` | `python3 scripts/video_postprocess.py --help` | Usage info displayed |

---

## 6. Opt-in hook reference — not shipped active

**There are no hook tests.** SocialForge ships **zero global hooks** — `hooks/hooks.json` is empty by design. The four hooks that existed before v1.5.0 (SessionStart credential banner, PreToolUse compliance check, SubagentStart brand-context injection, Stop image-approval verification) were removed because they fired on every Claude Code operation in every project.

The old configuration is archived at `hooks/hooks-reference.example.json` as an opt-in example only — nothing loads it. The only thing to verify here:

- [ ] `hooks/hooks.json` contains no active hook entries | Empty by design
- [ ] No SocialForge hook fires in an unrelated project | Zero global side effects

---

## 7. Creative Pipeline Tests (End-to-End)

### Test Data
- Brand: `test-brand` with 10 product images, 3 style reference images
- Calendar: 10 posts (2 HERO, 4 HUB, 4 HYGIENE) across LinkedIn, Instagram, X

### Pipeline Phases
- [ ] Phase 1: Calendar parse | 10 posts in calendar-data.json with correct dates/platforms
- [ ] Phase 2: Asset match | All 10 posts assigned assets and creative modes
- [ ] Phase 3: Visual production (ANCHOR_COMPOSE) | Brand photo centered, AI background generated
- [ ] Phase 3: Visual production (ENHANCE_EXTEND) | Image extended without modifying core
- [ ] Phase 3: Visual production (STYLE_REFERENCED) | New image matches brand palette
- [ ] Phase 3: Visual production (PURE_CREATIVE) | Image generated from prompt + brand colors
- [ ] Phase 4: Copy generation | Master copy written for all 10 posts
- [ ] Phase 5: Copy adaptation | Platform variants respect character limits
- [ ] Phase 6: Compliance check | No false positives on clean copy; banned phrases caught
- [ ] Phase 7: Preview generation | Mockups created for each platform target
- [ ] Phase 8: Gallery build | HTML gallery renders all 10 posts with images and copy
- [ ] Pipeline resume | Kill mid-run, restart — picks up from last completed phase

---

## 8. State Machine Tests

### Valid Transitions
- [ ] `draft` -> `asset-matched` | After match-assets runs
- [ ] `asset-matched` -> `visual-ready` | After compose-creative completes
- [ ] `visual-ready` -> `copy-ready` | After adapt-copy completes
- [ ] `copy-ready` -> `compliance-passed` | After compliance check passes
- [ ] `compliance-passed` -> `in-review` | After entering review queue
- [ ] `in-review` -> `approved` | After all required approvals received
- [ ] `in-review` -> `revision-requested` | After reviewer requests changes
- [ ] `revision-requested` -> `visual-ready` or `copy-ready` | After revision applied
- [ ] `approved` -> `finalized` | After finalize completes

### Invalid Transitions
- [ ] `draft` -> `approved` | Rejected — cannot skip production phases
- [ ] `finalized` -> `draft` | Rejected — cannot revert finalized content
- [ ] `in-review` -> `finalized` | Rejected — must be approved first
- [ ] `compliance-passed` -> `approved` | Rejected — must go through review

---

## 9. Approval Workflow Tests

### HERO Path (highest scrutiny)
- [ ] HERO post enters review with 3 required reviewers | social-lead, brand-manager, creative-director
- [ ] Partial approval (1 of 3) does not advance post | Remains in-review
- [ ] Full internal approval triggers client review | Client notification sent or staged
- [ ] Client approval triggers CEO approval | CEO review step activated
- [ ] CEO approval marks post as fully approved | Status: approved
- [ ] Escalation triggers after max_review_hours exceeded | Reminder sent or escalation logged

### HUB Path (standard)
- [ ] HUB post requires social-lead + brand-manager | 2 reviewers minimum
- [ ] Client approval required, CEO approval not | Correct approval chain
- [ ] Approved HUB post can be finalized | Moves to finalized without CEO step

### HYGIENE Path (lightweight)
- [ ] HYGIENE post requires social-lead only | 1 reviewer minimum
- [ ] No client or CEO approval required | Moves directly to approved after internal review
- [ ] Approved HYGIENE post finalizes cleanly | Delivery output includes post

---

## 10. MCP Connector Tests

Test each connector loads and responds. These require active OAuth/authentication.

| # | Connector | Test | Expected Result |
|---|-----------|------|-----------------|
| 1 | Notion | Read a Notion page | Page content returned |
| 2 | Canva | List Canva designs | Design list returned or auth prompt |
| 3 | Slack | Send test message to channel | Message delivered |
| 4 | Gmail | Read inbox | Recent emails listed or auth prompt |
| 5 | Google Calendar | List events | Calendar events returned |
| 6 | Figma | Read a Figma file | File data returned |
| 7 | fal.ai | Generate test image | Image URL returned |
| 8 | Replicate | Run test model | Prediction result returned |
| 9 | Asana | List tasks | Task list returned |

- [ ] Plugin loads without errors when connectors are not authenticated | Graceful "not connected" handling
- [ ] Plugin loads without errors when no connectors are configured | Full offline functionality

---

## 11. Carousel Template Tests

Test each of the 8 templates renders correctly.

- [ ] `tips-5slide.html` renders 5 slides | All slides visible, brand colors applied
- [ ] `recap-6slide.html` renders 6 slides | Correct slide count, content injected
- [ ] `data-infographic-6slide.html` renders 6 slides | Data values display correctly
- [ ] `generic-8slide.html` renders 8 slides | Generic content populates all slides
- [ ] `playbook-8slide.html` renders 8 slides | Step numbering correct
- [ ] `comparison-10slide.html` renders 10 slides | Side-by-side layout preserved
- [ ] `case-study-10slide.html` renders 10 slides | Client name, metrics, quotes injected
- [ ] `quote-card-single.html` renders 1 slide | Quote text, attribution, and brand styling correct
- [ ] All templates apply brand colors from brand-config.json | Hex colors match config
- [ ] All templates apply brand fonts from brand-config.json | Font family matches config
- [ ] Logo overlay placed correctly on all templates | Logo visible and correctly positioned
- [ ] Output dimensions match platform specs (1080x1080 for LinkedIn/Instagram carousels) | Pixel dimensions verified

---

## 12. Edge Cases

### Missing Brand
- [ ] Running `/socialforge:generate-all` with no active brand | Clear error: "Brand not found" with fix instructions
- [ ] Running `/socialforge:index-assets` with nonexistent brand slug | Error with suggestion to run brand-setup

### Empty Calendar
- [ ] Running `/socialforge:generate-all` with empty calendar-data.json | Graceful message: "No posts in calendar"
- [ ] Parsing a blank DOCX | Error: "No posts found in calendar source"

### No Assets
- [ ] Running pipeline with zero indexed assets | Posts default to PURE_CREATIVE mode
- [ ] Running ANCHOR_COMPOSE with no matching asset | Fallback to STYLE_REFERENCED or PURE_CREATIVE

### API Failures
- [ ] Image generation API returns 429 (rate limit) | Retry with backoff, resume supported
- [ ] Image generation API returns 500 (server error) | Error logged, post marked as failed, pipeline continues
- [ ] All API keys missing | Clear error listing which keys are needed

### File System
- [ ] Path with spaces in brand name | Handled correctly (slug is kebab-case)
- [ ] Very long file names (>200 chars) | Truncated or handled without OS error
- [ ] Output directory does not exist | Created automatically

### Large Calendars
- [ ] Calendar with 60+ posts | Pipeline handles without timeout (may need batching)
- [ ] Calendar with posts spanning multiple months | Only target month posts processed

---

## 13. Cowork Compatibility Tests

- [ ] Plugin installs in Cowork VM | No SSH errors (HTTPS source used)
- [ ] Python 3.10 available in Cowork | `python3 --version` confirms 3.10+
- [ ] `pip install` works for dependencies | playwright, python-docx, Pillow, gspread install
- [ ] Playwright Chromium runs in Cowork | Carousel rendering works (may need `--no-sandbox`)
- [ ] `.mcp.json` HTTP connectors load in Cowork | No npx/node dependency issues
- [ ] File paths use forward slashes | No Windows backslash errors in Cowork (Linux VM)
- [ ] Scripts execute without C-extension failures | rembg fallback works if compilation fails

---

## 14. Regression Checklist

Run after any code change to verify nothing broke.

- [ ] All 22 Python scripts (+ `assemble_docx.js`) pass `--help` without import errors
- [ ] `python tests/run_all.py` passes | 55 tests
- [ ] Brand setup creates valid brand-config.json
- [ ] Asset indexing produces valid asset-index.json
- [ ] Calendar parsing handles DOCX input
- [ ] Calendar parsing handles XLSX input
- [ ] All 4 creative modes produce output
- [ ] Copy adaptation respects platform character limits
- [ ] Compliance check catches banned phrases
- [ ] Carousel templates render via Playwright
- [ ] Review gallery builds successfully
- [ ] Approval chain follows tier rules
- [ ] Finalize produces delivery folder with expected structure
- [ ] Pipeline resume works after interruption
- [ ] Reactive post creation works outside calendar
- [ ] Cost report shows accurate API usage
- [ ] No regression in existing brand configs (backward compatibility)

---

## 15. Version Consistency Check

- [ ] `README.md` version matches actual release | Currently 1.13.1
- [ ] `plugin.json` version matches README | Consistent across all 7 platform manifests
- [ ] `CHANGELOG.md` has entry for current version | Release notes present
- [ ] Skill count in README matches actual skill directories | 18 skills
- [ ] Command count in README matches actual command files | 25 commands
- [ ] Agent count in README matches actual agent files | 5 agents
- [ ] Script count in README matches actual script files | 22 Python scripts (+ `assemble_docx.js`)
- [ ] Connector count in README matches `.mcp.json.connectors-reference` | 10 opt-in connectors; `.mcp.json` itself is `{"mcpServers":{}}`
- [ ] Carousel template count in README matches actual templates | 8 templates
- [ ] All agents have valid YAML frontmatter (name + description) | No missing frontmatter
- [ ] All skills have valid YAML frontmatter (name + description) | No missing frontmatter
- [ ] All commands have valid YAML frontmatter (description + argument-hint) | No missing frontmatter

---

*End of testing guide. Update this document as new features are added.*
