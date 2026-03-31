---
name: generate-video
description: Generate short-form video scripts, storyboards, and AI video clips for video content posts.
argument-hint: "[--post <id>] [--script-only] [--thumbnail]"
effort: high
user-invocable: true
---

# /sf:generate-video — Video Production Kit

Generate video production assets: scripts, storyboards, thumbnails, and optionally AI video clips.

## Output Per Video Post
1. **Script** — Timestamped narration/dialogue script
2. **Storyboard** — Shot-by-shot visual descriptions
3. **Thumbnail** — AI-generated video thumbnail (using compose-creative)
4. **AI Video Clip** (optional) — Short clip via Gemini Veo or fal.ai (if connected)

## Video Types
| Type | Duration | Production |
|------|----------|-----------|
| hero_video | 30-90s | Script + storyboard (needs filming) |
| mini_case_study | 30-60s | Script + AI animation |
| short_reel | 15-30s | AI video generation |
| story | 15s | Image-to-video animation |
| talking_head | 30-120s | Script only (needs filming) |

## Rules
- Video generation is optional — always generates script + storyboard
- AI video clips require user approval before saving
- Thumbnails use the same creative mode system as static images
- Save all to `production/video/post-{id}-*`

## Timeout & Fallback
- AI video generation: 120-second timeout (video gen is slow). If fails, provide script + storyboard only.
