---
description: Index or re-index a brand's visual asset library
argument-hint: "<brand-name> [--source <path>] [--refresh]"
---

# Index Assets

Scan and analyze a brand's photo library. Runs /sf:index-assets skill.

## Usage
```
/sf:index-assets acme-corp --source /path/to/photos
/sf:index-assets acme-corp --refresh  (only new/changed files)
```

## Output
Asset index saved to ~/socialforge-workspace/brands/{brand}/asset-index.json
