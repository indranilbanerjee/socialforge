# SocialForge admin setup (one time)

Admins create the cloud accounts once and share the credentials; team members need no cloud accounts and just run `/socialforge:setup` (see [What Team Members Do](#what-team-members-do)). These are the click-by-click steps that used to sit in the README; its [Admin Setup](../README.md#admin-setup-one-time) section is the short version.

## Pre-Requisites for Image Generation

SocialForge uses **Google Cloud Vertex AI** for image generation. Without it, image generation will fail (it will NOT silently create placeholders).

**Setup via /socialforge:setup (recommended):**
1. Your admin provides a Google Cloud service account JSON key file with Vertex AI access
2. Run `/socialforge:setup` and point it to the JSON key file
3. Credentials are stored persistently — no need to set environment variables manually

**Alternative — Direct environment variable:**
If you prefer manual configuration, set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to your service account JSON file:
```
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

**Alternative — fal.ai or Replicate:** Connect via Connectors panel after installation for third-party image generation.

Run `/socialforge:status` to verify image and video generation credentials are configured. (As of v1.5.0, credential status is reported on demand instead of via a SessionStart banner that fired on every Claude Code launch in every project.)

Admins configure the cloud accounts once. Team members then just run `/socialforge:setup` with the credentials the admin shares.

## Google Cloud (Vertex AI — Image Generation)

### Step 1: Create a Google Cloud Project
1. Open https://console.cloud.google.com/
2. If you don’t have an account, click "Get started for free" and follow registration
3. Click the project dropdown at the top of the page (next to "Google Cloud")
4. Click "NEW PROJECT"
5. Enter a project name (e.g., "socialforge-production")
6. Click "CREATE"
7. Wait for the project to be created (30 seconds), then select it from the dropdown

### Step 2: Enable Billing
1. Go to https://console.cloud.google.com/billing
2. Click "LINK A BILLING ACCOUNT"
3. If you don’t have a billing account, click "CREATE BILLING ACCOUNT"
4. Add a payment method (credit card)

### Step 3: Enable Vertex AI API
1. Go to https://console.cloud.google.com/apis/library
2. Search for "Vertex AI API"
3. Click on it, then click "ENABLE"
4. Wait for it to activate (takes a few seconds)

### Step 4: Create a Service Account
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

### Step 5: Download the JSON Key File
1. In the service accounts list, click on `socialforge-image-gen`
2. Go to the "KEYS" tab
3. Click "ADD KEY" then "Create new key"
4. Select "JSON" and click "CREATE"
5. A .json file downloads automatically — this is your credential file
6. Save it somewhere safe on your computer

### Step 6: Share with Your Team
Share the downloaded JSON file with your team via:
- Slack DM (not in a public channel)
- Email (encrypted if possible)
- Shared company drive (restricted access)

NEVER commit this file to Git. NEVER share it publicly.

**Cost:** Image generation is billed per image to the admin’s Google Cloud account. The price depends on the model and resolution and changes over time, so SocialForge stores no prices: before any paid run it quotes the planned generations from a live lookup (with the source URL and the price’s age) and waits for your `go`.

## WaveSpeed (Video Generation)

### Step 1: Create a WaveSpeed Account
1. Open https://wavespeed.ai
2. Click "Sign Up" and create an account
3. Verify your email

### Step 2: Add Credits
1. After logging in, go to your dashboard
2. Click "Top Up" or navigate to billing
3. Add credits (minimum top-up required to activate API access)
4. Pricing: WaveSpeed bills per second of video and the rate depends on the model. SocialForge quotes it from a live lookup (source URL and the price’s age shown) before every paid run and waits for your `go`.

### Step 3: Create an API Key
1. Go to https://wavespeed.ai/accesskey
2. Click "Create API Key"
3. Copy the key (it’s a long string of letters and numbers)
4. Save it somewhere safe

### Step 4: Share with Your Team
Share the API key string with your team via:
- Slack DM
- Password manager (recommended)
- Email (encrypted if possible)

NEVER commit this key to Git or paste it in public forums.

**Cost:** All video generation costs go to the admin’s WaveSpeed account. Monitor usage at https://wavespeed.ai/dashboard

## HiggsField (Optional Fallback — Video + Image)

HiggsField provides additional resilience. If both Vertex AI and WaveSpeed are down, HiggsField can generate images and videos.

### Step 1: Create a HiggsField Account
1. Open https://higgsfield.ai
2. Click "Sign Up" and create an account

### Step 2: Get API Credentials
1. Log in at https://cloud.higgsfield.ai and open the API / Developer section of your dashboard
2. Create a new API key pair — you'll get an API Key AND an API Secret
3. Save both values

### Step 3: Share with Your Team
Share both the API key AND secret with your team. Both are needed for authentication.

## What Team Members Do

Team members do NOT need any cloud accounts. The admin shares credentials, and the team member runs:

```
/socialforge:setup
```

The setup wizard first lists the Python packages that are missing and the exact pinned install command for each; it installs them only after you say `yes`. Then it asks for:
1. Path to the Google Cloud JSON file (for images) — give the file path
2. WaveSpeed API key (for video) — set `WAVESPEED_API_KEY` in your environment and say when it is set; never paste the key into the chat
3. HiggsField credentials (optional) — set `HF_API_KEY` and `HF_API_SECRET` the same way

Credentials are stored in the plugin’s persistent data directory. They survive across sessions, restarts, and plugin updates.

**Where credentials are stored per platform:**
- Windows: `%APPDATA%\Claude\plugins\data\socialforge-neels-plugins\socialforge\`
- macOS: `~/Library/Application Support/Claude/plugins/data/socialforge-neels-plugins/socialforge/`
- Linux: `~/.config/Claude/plugins/data/socialforge-neels-plugins/socialforge/`

Or if using the fallback workspace: `~/socialforge-workspace/`
