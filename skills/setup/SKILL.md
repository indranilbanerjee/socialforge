---
name: setup
description: "One-time setup for image and video generation APIs. Run this before any creative production."
argument-hint: "[--image | --video | --fallback | --status | --reset]"
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

### Step 2.5: HiggsField (Optional Fallback)

```
HiggsField Setup (Optional — adds fallback resilience)

Do you have a HiggsField API key and secret?
  → Paste the API key, then the API secret

Or type "skip" (HiggsField is optional — Vertex AI and WaveSpeed are sufficient).
```

When user provides both:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/credential_manager.py" setup-higgsfield --api-key "<key>" --api-secret "<secret>"
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

  HiggsField: [configured / skipped]
    Provider: HiggsField (Soul v2 + Kling v2.1, fallback)

  Credentials stored persistently. No further setup needed.

  Next: /sf:brand-setup [brand-name] to configure your first brand.
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
5. New accounts get $300 free credits for 90 days

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

**Cost:** Image generation costs approximately $0.01-0.04 per image depending on resolution and model. All costs go to the admin's billing account.

### WaveSpeed (Kling v3.0 — Video Generation)

#### Step 1: Create a WaveSpeed Account
1. Open https://wavespeed.ai
2. Click "Sign Up" and create an account
3. Verify your email

#### Step 2: Add Credits
1. After logging in, go to your dashboard
2. Click "Top Up" or navigate to billing
3. Add credits (minimum top-up required to activate API access)
4. Pricing: approximately $0.08-0.11 per second of video
   - A 5-second video costs roughly $0.40-0.56
   - A 10-second video costs roughly $0.84-1.12

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
3. New accounts get 150 free credits

#### Step 2: Get API Credentials
1. Go to https://cloud.higgsfield.ai/api-keys
2. Create a new API key pair — you'll get an API Key AND an API Secret
3. Save both values

#### Step 3: Share with Your Team
Share both the API key AND secret with your team. Both are needed for authentication.

## Security Notes

- Credentials are stored in the plugin persistent data directory
- The GCP JSON file is copied (not linked) to ensure it survives if the original is deleted
- WaveSpeed API key is stored in credentials.json within plugin data
- No credentials are committed to git or shared outside the local machine
- To revoke access: rotate the service account key in GCP Console or regenerate the WaveSpeed API key
