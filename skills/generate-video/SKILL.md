---
name: generate-video
description: "Create a short video from a concept through staged first frame, last frame, motion and render. \"turn this concept into a video\""
argument-hint: "[--post <id>] [--script-only] [--thumbnail]"
effort: high
user-invocable: true
---

# /socialforge:generate-video — Video Production Kit

Generate video production assets through a 5-stage human-in-the-loop pipeline. Each stage requires user approval before advancing.

## Context efficiency

Asset-heavy skill. **Grep before Read** the asset catalog (`${CLAUDE_PLUGIN_DATA}/socialforge/brands/<brand>/asset-index.json`) — never list the asset directory. Reference generated images / videos by path, not by loading metadata. Brand profile loads once per session.

## Prerequisites

- Credentials must be configured via `/socialforge:setup`:
  - **Vertex AI** (registry alias `latest-image-google`) — used for first-frame and last-frame keyframe generation
  - **WaveSpeed API** (registry alias `latest-video-wavespeed`) — used for image-to-video generation
- Models are never named in this skill: each alias above is resolved to a current model id when the script runs. To see what they resolve to today, run `python scripts/generate_video.py --list-models` (video) or `python scripts/resolve_model.py --aliases` (every alias).
- Brand profile must be active (`/socialforge:switch-brand` if needed)
- Calendar must be parsed (`/socialforge:parse-calendar`) with video posts identified

## The 5-Stage Pipeline

### Stage 1: Video Concept + Script (no API call)

Claude generates **2-3 video concept ideas** based on the post brief, brand voice, and platform requirements. Each concept includes:
- Working title and hook
- Visual narrative arc (opening, middle, close)
- Suggested duration and pacing
- Tone and style direction

The user picks one concept (or requests refinements). Then **fill the script
scaffold** (`generate_script` in generate_video.py) from the chosen concept and
the post's actual brief, in the brand's voice — every `[FILL]` replaced, no
placeholder survives into Stage 2. The scaffold enforces the structure; this
pass supplies the craft, under four rules the scaffold carries with it:

1. **Hook first, never the logo.** The open earns attention with the single
   most arresting thing the brief supports; the brand mark lives as the corner
   watermark and in the end card. Three seconds of logo reveal is the classic
   retention killer this pipeline used to scaffold by default.
2. **Payoff per scene.** Every scene's `payoff` field states what the viewer
   has gained by the time it ends. A beat that only sets up the next beat is
   where viewers leave — give it a payoff or fold it.
3. **The pairing rule.** The hook's text overlay and the post's caption
   (written by adapt-copy) do different jobs and never echo. Check against the
   adapted copy if it already exists for this post.
4. **Compliance before credits.** Run the filled script's narration and
   overlay text through `compliance_check.py` BEFORE Stage 2 — a banned phrase
   caught in a script costs nothing; caught in a rendered video it costs the
   whole generation chain. Claims in narration follow the same rules as claims
   in copy: sourced or absent.

The user approves the filled script before any generation spend.

### Stage 2: First Frame Generation (Vertex AI, `latest-image-google`)

Generate **2 first-frame options** based on the chosen concept. These set the opening visual and establish the look and feel.

- Images are shown **inline** in the terminal for immediate review
- User selects one or requests a regeneration with adjusted direction

### Stage 3: Last Frame Generation (Vertex AI, `latest-image-google`)

Generate **2 last-frame options** that complete the visual narrative arc, matching the approved first frame.

- Images are shown **inline** in the terminal for immediate review
- User selects one or requests a regeneration with adjusted direction

### Stage 4: Video Generation (WaveSpeed, `latest-video-wavespeed`)

Using the approved first and last frames, generate **2 video versions** through `generate_video.py --generate-video --image <first-frame> --last-image <last-frame>` (the WaveSpeed image-to-video endpoint, 3-15 seconds). The first frame goes to every provider in the chain; the last frame goes to the `kling` rung only, as the clip's end image. After each run, read `video.last_frame_used` before presenting a clip as landing on the approved last frame — see "Keyframe and reference inputs" below.

- A **video gallery is opened in the browser** for side-by-side comparison
- User selects the final version or requests a regeneration

### Stage 5: Post-Process, Save & Deliver

After the user picks the final video, post-processing runs before saving:
- **Logo watermark** is automatically added to the video via video_postprocess.py
- **Subtitles:** User is asked whether to burn subtitles into the video (optional). SRT was already generated from the script and is saved separately regardless.
- **Background music:** If the video has no audio (sound=False in the clip request), user is asked whether to add background music (optional).
- **Platform resize:** Video is automatically resized for each target platform (letterbox/pillarbox with black padding, no stretching)

Save all final assets to `{post_folder}/` -- keyframes in `keyframes/`, video versions in `versions/`, platform-resized final videos in `final/`:
- **Video files** (.mp4) — post-processed and resized per platform
- **Script** — timestamped narration/dialogue
- **Storyboard** — shot-by-shot visual breakdown with keyframe references
- **SRT subtitle file** (.srt) — for captioned playback

## Keyframe and reference inputs — what `generate_video.py` implements

Read from `scripts/generate_video.py`. Never describe the video as doing more than this.

| Input | Flag | What is true today |
|---|---|---|
| First frame (image-to-video) | `--image <path>` | Passed to every provider in the chain. The `kling` rung **requires** it — without one, and once its credential check has passed, that rung records `bad-input` and the chain moves on to a text-to-video rung. The `veo` and `higgsfield` rungs treat it as optional and run text-to-video when it is absent. Use a PNG or JPEG: file type is set from the extension (Veo) or always sent as PNG (the `higgsfield` rung). |
| Last frame | `--last-image <path>` (requires `--generate-video`) | Sent to the `kling` rung as the clip's end image (the WaveSpeed image-to-video API's `end_image`, documented there as the end frame for guided transitions), so the clip is guided toward it. **Only that rung takes one:** the `veo` and `higgsfield` rungs have no end-frame input. A clip made by either of them (because `--provider` named one of them, or because `kling` had no key or failed and the chain fell through) carries `last_frame_used: false` and a `last_frame_note`; it was **not** steered to the approved last frame. A `--last-image` path that does not exist is an input error (exit 1), never dropped quietly. Use a PNG or JPEG. |
| Reference images for video | none | Not implemented. |

Practical consequence: Stage 3's approved last frame is a real model input on the `kling` rung only. Under `--provider auto`, a supplied `--last-image` makes the chain try `kling` first (without one, auto sends clips of 8 seconds or less to `veo` whenever Google credentials exist, and `veo` cannot take an end frame). Passing `--provider kling` says the same thing explicitly; an explicit `--provider veo` or `higgsfield` still wins and leaves the frame unused. Then read `video.last_frame_used` in the result. `true` means the end image was sent. `false` means it was not, and `last_frame_note` says which rung made the clip: tell the user, put the intended ending into the motion prompt in words, and do not describe the clip as landing on the approved frame. Even when it was sent, the model is *guided toward* the frame rather than guaranteed to reach it — look at the clip's final seconds before the user approves it.

## Output Per Video Post

| Asset | Format | Always Generated |
|-------|--------|-----------------|
| Script | Markdown | Yes |
| Storyboard | Markdown + keyframe images | Yes |
| Thumbnail | PNG/WebP (via compose-creative) | Yes |
| First frame | PNG | Yes (Stage 2) |
| Last frame | PNG | Yes (Stage 3) |
| AI Video Clip | MP4 via WaveSpeed (`latest-video-wavespeed`, image-to-video, 3-15 seconds) | If pipeline completed |
| SRT subtitles | .srt | If video generated |

## Video Types

| Type | Duration | AI Generation | Production Notes |
|------|----------|--------------|-----------------|
| hero_video | 30-90s | Partial — AI generates 3-15s hero clip; full version needs filming | Script + storyboard + AI teaser clip |
| mini_case_study | 30-60s | Yes — AI animation from keyframes | Full pipeline supported |
| short_reel | 15-30s recommended (Instagram Reels and YouTube Shorts accept up to 3 min) | Yes — ideal for AI generation | Full pipeline supported |
| story | up to 60s per frame (Instagram Stories) | Yes — image-to-video animation | Full pipeline supported |
| talking_head | 30-120s | No — needs filming | Script + storyboard only (use `--script-only`) |

## Rules

- Every stage requires explicit user approval before advancing
- `--script-only` skips Stages 2-4 and generates script + storyboard only
- `--thumbnail` generates a video thumbnail via compose-creative (independent of the pipeline)
- AI video clips are never auto-saved; user must confirm the final selection
- Thumbnails use the same creative mode system as static images
- All assets save to `{post_folder}/` -- keyframes in `keyframes/`, video versions in `versions/`, final video in `final/`

## Timeout & Fallback

- AI video generation (Stage 4): **300-second timeout** (the video model can take several minutes for high-quality output)
- Keyframe generation (Stages 2-3): 60-second timeout per image
- If video generation fails or times out, deliver script + storyboard + keyframes as fallback
