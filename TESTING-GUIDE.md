# SocialForge Testing Guide

**Version:** 1.0.0
**Last Updated:** 2026-03-31
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
- [ ] `claude plugin marketplace add github:indranilbanerjee/socialforge` succeeds | No errors
- [ ] `claude plugin install socialforge@socialforge` succeeds | Plugin appears in installed list

### GitHub Install
- [ ] `claude plugin install github:indranilbanerjee/socialforge` succeeds | Plugin appears in installed list

### Local Install
- [ ] `claude plugins add /path/to/socialforge` succeeds | Plugin appears in installed list

### Post-Install Verification
- [ ] New session shows SocialForge welcome message | "SocialForge v1.0 loaded" with Quick Start
- [ ] `/sf:status` returns valid response | Shows "No active brand" or brand status
- [ ] All 18 commands appear in Customize panel | Count matches expected 18
- [ ] All 14 skills appear in Skills section | Count matches expected 14
- [ ] `.mcp.json` loaded (9 connectors) | No MCP initialization errors in logs

---

## 3. Command Tests

| # | Command | Test Action | Expected Result |
|---|---------|------------|-----------------|
| 1 | `/sf:brand-setup test-brand` | Run with test brand name | Interactive wizard starts, `brand-config.json` created |
| 2 | `/sf:switch-brand test-brand` | Switch to existing brand | Active brand changes, confirmed in status |
| 3 | `/sf:index-assets test-brand` | Index test asset folder | `asset-index.json` created with per-image metadata |
| 4 | `/sf:new-month test-brand 2026-04` | Start April production | Calendar prompt or data initialized |
| 5 | `/sf:sync-calendar --source test.xlsx` | Parse test calendar | `calendar-data.json` created with post entries |
| 6 | `/sf:generate-all` | Run full production | All posts processed, images generated |
| 7 | `/sf:generate-post <post-id>` | Generate single post | One post's creative produced |
| 8 | `/sf:edit-post <post-id> --copy` | Edit post copy | Copy updated in calendar data |
| 9 | `/sf:edit-image <post-id> "warmer tones"` | Edit generated image | Image regenerated with instruction |
| 10 | `/sf:swap-asset <post-id> --browse` | Browse and swap asset | Asset replaced, image regenerated |
| 11 | `/sf:preview-batch` | Generate previews | Platform mockups created for all posts |
| 12 | `/sf:review` | Open review gallery | HTML gallery renders with all posts |
| 13 | `/sf:revision <post-id> "feedback"` | Apply revision | Affected elements regenerated |
| 14 | `/sf:check-approvals` | Check approval status | Pending approvals listed by tier |
| 15 | `/sf:client-review --tier HERO` | Send for client review | Posts sent via Slack/email or export prepared |
| 16 | `/sf:finalize` | Finalize month | Delivery folder created with all assets |
| 17 | `/sf:reactive-post "trending topic"` | Create reactive post | New post created outside calendar |
| 18 | `/sf:status` | Check status | Shows brand, month, post counts, pipeline phase |
| 19 | `/sf:cost-report` | Check costs | API cost breakdown displayed |

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

Run each script from the command line to verify it executes without import errors.

| # | Script | CLI Test | Expected Result |
|---|--------|---------|-----------------|
| 1 | `adapt_copy.py` | `python3 scripts/adapt_copy.py --help` | Usage info or no import errors |
| 2 | `assemble_docx.js` | `node scripts/assemble_docx.js --help` | Usage info or no import errors |
| 3 | `build_gallery.py` | `python3 scripts/build_gallery.py --help` | Usage info displayed |
| 4 | `compliance_check.py` | `python3 scripts/compliance_check.py --help` | Usage info displayed |
| 5 | `compose_image.py` | `python3 scripts/compose_image.py --help` | Usage info displayed |
| 6 | `compose_text_overlay.py` | `python3 scripts/compose_text_overlay.py --help` | Usage info displayed |
| 7 | `cost_tracker.py` | `python3 scripts/cost_tracker.py --help` | Usage info displayed |
| 8 | `edit_image.py` | `python3 scripts/edit_image.py --help` | Usage info displayed |
| 9 | `generate_image.py` | `python3 scripts/generate_image.py --help` | Usage info displayed |
| 10 | `generate_video.py` | `python3 scripts/generate_video.py --help` | Usage info displayed |
| 11 | `index_assets.py` | `python3 scripts/index_assets.py --help` | Usage info displayed |
| 12 | `match_assets.py` | `python3 scripts/match_assets.py --help` | Usage info displayed |
| 13 | `render_carousel.py` | `python3 scripts/render_carousel.py --help` | Usage info displayed |
| 14 | `render_preview.py` | `python3 scripts/render_preview.py --help` | Usage info displayed |
| 15 | `resize_image.py` | `python3 scripts/resize_image.py --help` | Usage info displayed |
| 16 | `status_manager.py` | `python3 scripts/status_manager.py --action session-init` | Session init output, no errors |
| 17 | `verify_brand_colors.py` | `python3 scripts/verify_brand_colors.py --help` | Usage info displayed |

---

## 6. Hook Tests

### SessionStart Hook
- [ ] New session triggers status_manager.py session-init | Welcome message displayed
- [ ] Session-init completes within 30-second timeout | No timeout error
- [ ] Quick Start commands printed | 3-step quick start visible

### PreToolUse Hook (Compliance)
- [ ] Writing copy with a banned phrase triggers warning | Hook catches violation before write
- [ ] Writing copy without violations passes cleanly | "SKIP" or no interference
- [ ] Platform character limits flagged when exceeded | Warning for over-limit content
- [ ] Brand hashtag requirements enforced | Missing required hashtags flagged

### SubagentStart Hook (Brand Injection)
- [ ] Subagent receives brand-config.json context | Brand colors/fonts available to agent
- [ ] "Brand assets are sacred" principle enforced | AI does not modify brand photos
- [ ] Creative mode respected by subagent | Correct mode applied per post config
- [ ] Compliance rules loaded into subagent | Banned phrases checked in subagent scope

### Stop Hook (Quality Gate)
- [ ] Task completing with unapproved images triggers warning | List of unapproved items shown
- [ ] Task completing with over-limit copy triggers warning | Platform violations listed
- [ ] Task completing with all checks passing returns PASS | Clean completion
- [ ] Compliance violations at stop trigger issue list | User asked how to proceed

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
- [ ] Running `/sf:generate-all` with no active brand | Clear error: "Brand not found" with fix instructions
- [ ] Running `/sf:index-assets` with nonexistent brand slug | Error with suggestion to run brand-setup

### Empty Calendar
- [ ] Running `/sf:generate-all` with empty calendar-data.json | Graceful message: "No posts in calendar"
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
- [ ] Session-init hook completes in Cowork | 30-second timeout sufficient

---

## 14. Regression Checklist

Run after any code change to verify nothing broke.

- [ ] All 17 scripts pass `--help` without import errors
- [ ] Session-init hook displays welcome message
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

- [ ] `README.md` version matches actual release | Currently 1.0.0
- [ ] `plugin.json` version matches README | Consistent across files
- [ ] `CHANGELOG.md` has entry for current version | Release notes present
- [ ] `hooks.json` welcome message shows correct version | "SocialForge v1.0"
- [ ] Skill count in README matches actual skill directories | 14 skills
- [ ] Command count in README matches actual command files | 18 commands
- [ ] Agent count in README matches actual agent files | 5 agents
- [ ] Script count in README matches actual script files | 17 scripts
- [ ] Connector count in README matches `.mcp.json` entries | 9 connectors
- [ ] Carousel template count in README matches actual templates | 8 templates
- [ ] All agents have valid YAML frontmatter (name + description) | No missing frontmatter
- [ ] All skills have valid YAML frontmatter (name + description) | No missing frontmatter
- [ ] All commands have valid YAML frontmatter (description + argument-hint) | No missing frontmatter

---

*End of testing guide. Update this document as new features are added.*
