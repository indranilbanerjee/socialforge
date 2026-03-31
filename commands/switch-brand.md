---
description: Switch the active brand context
argument-hint: "<brand-name>"
---

# Switch Brand

Switch SocialForge to work on a different brand. Loads the brand's config, platform settings, compliance rules, and asset index.

## Usage
```
/sf:switch-brand acme-corp
```

## What Happens
1. Saves current brand state
2. Loads target brand config files
3. Sets active brand in session context
4. Shows brand summary: platforms, assets indexed, current month status
