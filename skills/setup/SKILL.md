---
name: setup
description: "One-time setup of image and video generation credentials, verified before use. \"set up my API keys\""
argument-hint: "[--image | --video | --fallback | --status | --reset]"
effort: low
user-invocable: true
---

# /socialforge:setup — API Credential Configuration

> **Script location.** If your host does not set `${CLAUDE_PLUGIN_ROOT}`, the scripts are in this plugin's `scripts/` folder, next to `skills/`.

One-time setup that stores credentials persistently. Run once, works forever across all sessions.

## Context efficiency

Asset-heavy skill. **Grep before Read** the asset catalog (`${CLAUDE_PLUGIN_DATA}/socialforge/brands/<brand>/asset-index.json`) — never list the asset directory. Reference generated images / videos by path, not by loading metadata. Brand profile loads once per session.

## What This Does

Configures two services that SocialForge needs for creative production:

1. **Google Cloud Vertex AI** (required for images) — the image models, resolved at run time from the registry aliases `latest-image-balanced-google` and `latest-image-google`
2. **WaveSpeed** (required for video) — image-to-video, resolved from the registry alias `latest-video-wavespeed`

## Prerequisites

Your admin provides you with:
- A **Google Cloud service account JSON file** (for image generation)
- A **WaveSpeed API key** (for video generation)

If you are the admin, see the Admin Setup section below.

## How to Run

```
/socialforge:setup
```

## Interactive Flow

### Step 0: Check Dependencies (nothing installs without your yes)

Run this first. It only REPORTS which packages are present and prints the exact pinned install command for each one that is missing; it installs nothing:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/install_deps.py"
```

Packages it checks by default (every version is pinned in `scripts/install_deps.py`): Pillow (compositing), google-genai (Vertex AI), wavespeed and imageio-ffmpeg (video), playwright (carousels; its Chromium browser is a large download).

Show the user the list, then ask:

```
These packages are missing: <list>. Install them now with the pinned versions? (yes / no)
  Playwright's browser (for carousels) is a large download; say so if playwright is on the list.
```

Only on an explicit `yes`, run:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/install_deps.py" --install
```
Any other answer: print the pinned commands from the report for the user to run themselves, and continue.

Extra packages are never part of that default and are installed only when the user asks for them by name: HiggsField's client (`--groups higgsfield`), background removal, which fetches model weights on first use (`--groups background-removal`), and C2PA signing (`--groups c2pa`).

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
  Models: resolved at run time from the registry (aliases latest-image-balanced-google, latest-image-google)
```

### Step 2: Video Generation (WaveSpeed)

```
Video Generation Setup (WaveSpeed)

Do you have a WaveSpeed API key?
  Do NOT paste it here: anything typed into this chat is stored in the conversation transcript.
  Set it as the environment variable WAVESPEED_API_KEY (in your shell or your host's environment
  settings) and tell me when it is set.

Or type "skip" to configure later (video generation will not work).
```

When the user says it is set, run this WITHOUT `--api-key` (the script reads `WAVESPEED_API_KEY`, or one line from stdin; a key on the command line lands in shell history and the process table):
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/credential_manager.py" setup-wavespeed
```

Show the result. If success:
```
Video generation configured.
  Provider: WaveSpeed (alias latest-video-wavespeed)
  Models: image-to-video, text-to-video (3-15 seconds)
```

### Step 2.5: HiggsField (Optional Fallback)

```
HiggsField Setup (Optional — adds fallback resilience)

Do you have a HiggsField API key and secret?
  Do NOT paste them here. Set the environment variables HF_API_KEY and HF_API_SECRET and tell me
  when they are set.

Or type "skip" (HiggsField is optional — Vertex AI and WaveSpeed are sufficient).
```

When the user says both are set, run this WITHOUT `--api-key` or `--api-secret` (the script reads `HF_API_KEY` and `HF_API_SECRET`, or stdin):
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/credential_manager.py" setup-higgsfield
```

### Step 3: Summary

```
SocialForge API Setup Complete

  Image Generation: [configured / not configured]
    Provider: Google Cloud Vertex AI
    Project: <project_id>
    Models: registry aliases latest-image-balanced-google, latest-image-google

  Video Generation: [configured / not configured]
    Provider: WaveSpeed (alias latest-video-wavespeed)
    Modes: image-to-video, text-to-video

  HiggsField: [configured / skipped]
    Provider: HiggsField (fallback)

  Credentials stored persistently. No further setup needed.

  Next: /socialforge:brand-setup [brand-name] to configure your first brand.
```

## Arguments

| Argument | Effect |
|----------|--------|
| (none) | Run full interactive setup |
| `--image` | Configure image generation only (Vertex AI) |
| `--video` | Configure video generation only (WaveSpeed) |
| `--fallback` | Configure HiggsField fallback only |
| `--status` | Show current configuration status |
| `--reset` | Remove all stored credentials and start fresh |

## Admin Setup Guide

If you are setting up the cloud accounts for your team, follow these detailed guides.

### Google Cloud (Vertex AI — Image Generation)

#### Step 1: Create a Google Cloud Project
1. Open https://console.cloud.google.com/
2. If you don't have an account, click "Get started for free" and follow registration
3. Click the project dropdown at the top of the page (next to "Google Cloud")
4. Click "NEW PROJECT"
5. Enter a project name (e.g., "socialforge-production")
6. Click "CREATE"
7. Wait for the project to be created (30 seconds), then select it from the dropdown

#### Step 2: Enable Billing
1. Go to https://console.cloud.google.com/billing
2. Click "LINK A BILLING ACCOUNT"
3. If you don't have a billing account, click "CREATE BILLING ACCOUNT"
4. Add a payment method (credit card)
5. New accounts may come with promotional credits — the console states the current offer and its expiry. This skill does not quote it, because a number stated from memory is wrong the moment the vendor changes it.

#### Step 3: Enable Vertex AI API
1. Go to https://console.cloud.google.com/apis/library
2. Search for "Vertex AI API"
3. Click on it, then click "ENABLE"
4. Wait for it to activate (takes a few seconds)

#### Step 4: Create a Service Account
1. Go to https://console.cloud.google.com/iam-admin/serviceaccounts
2. Click "+ CREATE SERVICE ACCOUNT"
3. Service account name: `socialforge-image-gen`
4. Description: `SocialForge AI image generation`
5. Click "CREATE AND CONTINUE"
6. In "Grant this service account access to project":
   - Click the "Select a role" dropdown
   - Type "Vertex AI User" in the search box
   - Select "Vertex AI User"
7. Click "CONTINUE", then "DONE"

#### Step 5: Download the JSON Key File
1. In the service accounts list, click on `socialforge-image-gen`
2. Go to the "KEYS" tab
3. Click "ADD KEY" then "Create new key"
4. Select "JSON" and click "CREATE"
5. A .json file downloads automatically — this is your credential file
6. Save it somewhere safe on your computer

#### Step 6: Share with Your Team
Share the downloaded JSON file with your team via:
- Slack DM (not in a public channel)
- Email (encrypted if possible)
- Shared company drive (restricted access)

NEVER commit this file to Git. NEVER share it publicly.

**Cost:** this skill does not state a price. Per-image cost depends on model and resolution and changes without notice, so quoting one here would be a number nobody looked up. Run `python ${CLAUDE_PLUGIN_ROOT}/scripts/price_book.py --action lookup --model <model> --provider <provider>`; it returns a recorded price or refuses with the vendor's own pricing URL. All costs go to the admin's billing account.

### WaveSpeed (Video Generation)

#### Step 1: Create a WaveSpeed Account
1. Open https://wavespeed.ai
2. Click "Sign Up" and create an account
3. Verify your email

#### Step 2: Add Credits
1. After logging in, go to your dashboard
2. Click "Top Up" or navigate to billing
3. Add credits (minimum top-up required to activate API access)
4. Pricing: read the current per-second rate from the vendor's billing page. This skill deliberately does not quote it — see `price_book.py`, which refuses to quote a price it has not looked up rather than repeating a stale one.

#### Step 3: Create an API Key
1. Go to https://wavespeed.ai/accesskey
2. Click "Create API Key"
3. Copy the key (it's a long string of letters and numbers)
4. Save it somewhere safe

#### Step 4: Share with Your Team
Share the API key string with your team via:
- Slack DM
- Password manager (recommended)
- Email (encrypted if possible)

NEVER commit this key to Git or paste it in public forums.

**Cost:** All video generation costs go to the admin's WaveSpeed account. Monitor usage at https://wavespeed.ai/dashboard

### HiggsField (Optional Fallback — Video + Image)

HiggsField provides additional resilience. If both Vertex AI and WaveSpeed are down, HiggsField can generate images and videos.

#### Step 1: Create a HiggsField Account
1. Open https://higgsfield.ai
2. Click "Sign Up" and create an account
3. Any promotional credit for new accounts is shown at signup; this skill does not quote an amount.

#### Step 2: Get API Credentials
1. Log in at https://cloud.higgsfield.ai and open the API / Developer section of your dashboard
2. Create a new API key pair — you'll get an API Key AND an API Secret
3. Save both values

#### Step 3: Share with Your Team
Share both the API key AND secret with your team. Both are needed for authentication.

## Security Notes

- Credentials are stored in the plugin persistent data directory
- The GCP JSON file is copied (not linked) to ensure it survives if the original is deleted
- WaveSpeed API key is stored in credentials.json within plugin data
- Keys are never taken through the chat or the command line: only from environment variables or stdin
- No credentials are committed to git or shared outside the local machine
- To revoke access: rotate the service account key in GCP Console or regenerate the WaveSpeed API key
