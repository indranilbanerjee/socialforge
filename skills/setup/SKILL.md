---
name: setup
description: "One-time setup for image and video generation APIs. Run this before any creative production."
argument-hint: "[--image | --video | --status | --reset]"
effort: low
user-invocable: true
---

# /sf:setup — API Credential Configuration

One-time setup that stores credentials persistently. Run once, works forever across all sessions.

## What This Does

Configures two services that SocialForge needs for creative production:

1. **Google Cloud Vertex AI** (required for images) — Gemini Nano Banana 2 + Pro
2. **WaveSpeed** (required for video) — Kling v3.0 Pro for image-to-video

## Prerequisites

Your admin provides you with:
- A **Google Cloud service account JSON file** (for image generation)
- A **WaveSpeed API key** (for video generation)

If you are the admin, see the Admin Setup section below.

## How to Run

```
/sf:setup
```

## Interactive Flow

### Step 0: Install Dependencies (Automatic)

Run this first — installs all required Python packages:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/install_deps.py"
```

This auto-installs: google-genai (Vertex AI), wavespeed (Kling video), Pillow (compositing), playwright (carousels).

If any package fails, show the manual install command and continue.

### Step 1: Image Generation (Vertex AI)

Check if already configured:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/credential_manager.py" status
```

If not configured, ask:

```
Image Generation Setup (Google Cloud Vertex AI)

Do you have a Google Cloud service account JSON file?
  Provide the full file path (e.g., C:\Users\you\Downloads\socialforge-credentials.json)

Or type "skip" to configure later (image generation will not work).
```

When user provides the path:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/credential_manager.py" setup-vertex --json-path "<user-provided-path>"
```

Show the result. If success:
```
Image generation configured.
  Project: <project_id>
  Service Account: <email>
  Models available: gemini-2.5-flash-image (Nano Banana 2), gemini-3-pro-image-preview (Nano Banana Pro)
```

### Step 2: Video Generation (WaveSpeed)

```
Video Generation Setup (WaveSpeed / Kling v3.0)

Do you have a WaveSpeed API key?
  Paste the key here

Or type "skip" to configure later (video generation will not work).
```

When user provides the key:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/credential_manager.py" setup-wavespeed --api-key "<user-provided-key>"
```

Show the result. If success:
```
Video generation configured.
  Provider: WaveSpeed (Kling v3.0 Pro)
  Models: image-to-video, text-to-video (3-15 seconds)
```

### Step 3: Summary

```
SocialForge API Setup Complete

  Image Generation: [configured / not configured]
    Provider: Google Cloud Vertex AI
    Project: <project_id>
    Models: Nano Banana 2, Nano Banana Pro

  Video Generation: [configured / not configured]
    Provider: WaveSpeed (Kling v3.0 Pro)
    Modes: image-to-video, text-to-video

  Credentials stored persistently. No further setup needed.

  Next: /sf:brand-setup [brand-name] to configure your first brand.
```

## Arguments

| Argument | Effect |
|----------|--------|
| (none) | Run full interactive setup |
| `--image` | Configure image generation only (Vertex AI) |
| `--video` | Configure video generation only (WaveSpeed) |
| `--status` | Show current configuration status |
| `--reset` | Remove all stored credentials and start fresh |

## Admin Setup Guide

If you are setting up the Google Cloud project for your team:

### Google Cloud (Vertex AI) — One-Time Admin Setup

1. Go to https://console.cloud.google.com
2. Select or create a project
3. Enable billing on the project
4. Go to APIs and Services > Library
5. Search and enable: Vertex AI API
6. Go to IAM and Admin > Service Accounts
7. Click CREATE SERVICE ACCOUNT
8. Name: socialforge-image-gen
9. Role: Vertex AI User
10. Go to KEYS tab > ADD KEY > Create new key > JSON
11. Download the JSON file
12. Share this JSON file with your team members

Team members run /sf:setup and provide the path to this JSON file. All billing goes to your GCP project.

### WaveSpeed — One-Time Admin Setup

1. Go to https://wavespeed.ai
2. Create an account
3. Top up credits (minimum required to activate API)
4. Go to https://wavespeed.ai/accesskey
5. Create an API key
6. Share the key with your team members

Team members run /sf:setup and paste the key. All billing goes to your WaveSpeed account.

## Security Notes

- Credentials are stored in the plugin persistent data directory
- The GCP JSON file is copied (not linked) to ensure it survives if the original is deleted
- WaveSpeed API key is stored in credentials.json within plugin data
- No credentials are committed to git or shared outside the local machine
- To revoke access: rotate the service account key in GCP Console or regenerate the WaveSpeed API key
