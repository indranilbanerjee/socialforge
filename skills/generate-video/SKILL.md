---
name: generate-video
description: "Generate short-form video clips via a 5-stage human-in-the-loop pipeline: concept, keyframes, video generation, and delivery."
argument-hint: "[--post <id>] [--script-only] [--thumbnail]"
effort: high
user-invocable: true
---

# /sf:generate-video — Video Production Kit

Generate video production assets through a 5-stage human-in-the-loop pipeline. Each stage requires user approval before advancing.

## Prerequisites

- Credentials must be configured via `/sf:setup`:
  - **Vertex AI** (Gemini Imagen) — used for first-frame and last-frame keyframe generation
  - **WaveSpeed API** — used for image-to-video generation via Kling v3.0 Pro
- Brand profile must be active (`/sf:switch-brand` if needed)
- Calendar must be parsed (`/sf:parse-calendar`) with video posts identified

## The 5-Stage Pipeline

### Stage 1: Video Concept (no API call)

Claude generates **2-3 video concept ideas** based on the post brief, brand voice, and platform requirements. Each concept includes:
- Working title and hook
- Visual narrative arc (opening, middle, close)
- Suggested duration and pacing
- Tone and style direction

The user picks one concept (or requests refinements) before proceeding.

### Stage 2: First Frame Generation (Vertex AI / Gemini Imagen)

Generate **2 first-frame options** based on the chosen concept. These set the opening visual and establish the look and feel.

- Images are shown **inline** in the terminal for immediate review
- User selects one or requests a regeneration with adjusted direction

### Stage 3: Last Frame Generation (Vertex AI / Gemini Imagen)

Generate **2 last-frame options** that complete the visual narrative arc, matching the approved first frame.

- Images are shown **inline** in the terminal for immediate review
- User selects one or requests a regeneration with adjusted direction

### Stage 4: Video Generation (WaveSpeed / Kling v3.0 Pro)

Using the approved first and last frames, generate **2 video versions** via WaveSpeed's Kling v3.0 Pro image-to-video endpoint (3-15 seconds).

- A **video gallery is opened in the browser** for side-by-side comparison
- User selects the final version or requests a regeneration

### Stage 5: Save & Deliver

Save all final assets to `{post_folder}/` -- keyframes in `keyframes/`, video versions in `versions/`, final video in `final/`:
- **Video file** (.mp4) — the approved clip
- **Script** — timestamped narration/dialogue
- **Storyboard** — shot-by-shot visual breakdown with keyframe references
- **SRT subtitle file** (.srt) — for captioned playback

## Output Per Video Post

| Asset | Format | Always Generated |
|-------|--------|-----------------|
| Script | Markdown | Yes |
| Storyboard | Markdown + keyframe images | Yes |
| Thumbnail | PNG/WebP (via compose-creative) | Yes |
| First frame | PNG | Yes (Stage 2) |
| Last frame | PNG | Yes (Stage 3) |
| AI Video Clip | MP4 via WaveSpeed / Kling v3.0 Pro (image-to-video, 3-15 seconds) | If pipeline completed |
| SRT subtitles | .srt | If video generated |

## Video Types

| Type | Duration | AI Generation | Production Notes |
|------|----------|--------------|-----------------|
| hero_video | 30-90s | Partial — AI generates 3-15s hero clip; full version needs filming | Script + storyboard + AI teaser clip |
| mini_case_study | 30-60s | Yes — AI animation from keyframes | Full pipeline supported |
| short_reel | 15-30s | Yes — ideal for AI generation | Full pipeline supported |
| story | 15s | Yes — image-to-video animation | Full pipeline supported |
| talking_head | 30-120s | No — needs filming | Script + storyboard only (use `--script-only`) |

## Rules

- Every stage requires explicit user approval before advancing
- `--script-only` skips Stages 2-4 and generates script + storyboard only
- `--thumbnail` generates a video thumbnail via compose-creative (independent of the pipeline)
- AI video clips are never auto-saved; user must confirm the final selection
- Thumbnails use the same creative mode system as static images
- All assets save to `{post_folder}/` -- keyframes in `keyframes/`, video versions in `versions/`, final video in `final/`

## Timeout & Fallback

- AI video generation (Stage 4): **300-second timeout** (Kling v3.0 Pro can take several minutes for high-quality output)
- Keyframe generation (Stages 2-3): 60-second timeout per image
- If video generation fails or times out, deliver script + storyboard + keyframes as fallback
