# index-assets — storage location and refresh behaviour

Supplementary to `SKILL.md`. Read this when the user asks where the index lives, why
`--refresh` did or did not ask for a source path, or the index is "missing" after a
host change. Everything below is read from `scripts/index_assets.py`.

## Where the index is written

`asset-index.json` is saved per brand:

1. `${CLAUDE_PLUGIN_DATA}/socialforge/brands/{brand}/asset-index.json` — when
   `CLAUDE_PLUGIN_DATA` (or the Agent Plugins name `PLUGIN_DATA`) is set and the directory
   exists. This survives sessions and plugin updates.
2. `~/socialforge-workspace/brands/{brand}/asset-index.json` — the fallback when neither
   variable is set (or the directory does not exist).

If an index "disappeared", check which of the two roots the current host resolves before
re-indexing: a different host or a missing data variable lands in the other location.

## `--source` and `--refresh`

```
/socialforge:index-assets acme-corp --source /path/to/photos
/socialforge:index-assets acme-corp --source /path/to/photos --refresh   (only new/changed files)
/socialforge:index-assets acme-corp --refresh                            (reuse the recorded source)
```

- The first index of a brand needs `--source`.
- A later run may omit `--source`: the script reuses the `source_path` recorded in the
  previous `asset-index.json`, then the `path` / `url` in the brand's `asset-source.json`.
  Only when neither exists does it stop with "`--source` is required".
- A Google Drive URL cannot be crawled by the script itself. Download the folder locally
  and pass the local path, or (in Cowork) provide the folder contents through the Drive
  integration.
