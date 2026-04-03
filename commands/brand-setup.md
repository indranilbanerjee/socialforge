---
description: Configure a new brand profile with colors, fonts, logo, visual style, platforms, and compliance rules
argument-hint: "<brand-name> [--update] [--switch]"
---

# Brand Setup

Create or update a brand profile for SocialForge production.

## Process
1. Check API credentials are configured (run /sf:setup first if not)
2. Ask for brand name, industry, colors, platforms, asset source
3. Create brand config files in the workspace
4. Optionally add logo, fonts, visual style, compliance rules, approval chain, hashtags
5. Validate brand profile completeness

## First Time
Run with a brand name to create a new profile:
```
/sf:brand-setup MyBrand
```

## Update Existing
Add --update to modify an existing brand:
```
/sf:brand-setup MyBrand --update
```

## Switch Active Brand
```
/sf:brand-setup --switch OtherBrand
```
