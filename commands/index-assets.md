---
description: Index or re-index a brand's visual asset library
argument-hint: "<brand-name> [--source <path>] [--refresh]"
---

# Index Assets

Scan and analyze a brand's photo library. Runs /socialforge:index-assets skill.

## Usage
```
/socialforge:index-assets acme-corp --source /path/to/photos
/socialforge:index-assets acme-corp --source /path/to/photos --refresh  (only new/changed files)
```

`--source` is required on every run, including `--refresh`.

## Output
Asset index saved to `${CLAUDE_PLUGIN_DATA}/socialforge/brands/{brand}/asset-index.json` (falls back to `~/socialforge-workspace/brands/{brand}/asset-index.json` when `${CLAUDE_PLUGIN_DATA}` is unset)
