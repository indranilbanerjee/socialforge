---
description: Configure API credentials for image and video generation (one-time setup)
argument-hint: "[--image | --video | --status]"
---

# Setup

One-time configuration for SocialForge API credentials.

## Process
1. Check current credential status
2. If image generation not configured: prompt for Google Cloud service account JSON path
3. If video generation not configured: prompt for WaveSpeed API key
4. Validate and store credentials persistently
5. Show summary of configured services

## What You Need

Get from your admin:
- **Google Cloud JSON file** (for image generation via Vertex AI)
- **WaveSpeed API key** (for video generation via Kling v3.0)

## Quick Check
`/sf:setup --status` shows what is currently configured without changing anything.
