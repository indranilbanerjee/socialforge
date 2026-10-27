# Privacy

**No telemetry.** SocialForge sends nothing to its author or to any analytics service. There is no account, no sign-up and no tracking code in the plugin.

**Your AI host does the model calls.** SocialForge is a set of instructions and local scripts that run inside the agent you already use (Claude Code, Cowork, Codex, Cursor, Copilot CLI, Antigravity, Hermes Agent, OpenClaw or Grok). Prompts and outputs go to that host's model provider under that provider's own terms and privacy policy.

**Where your data lives.** Brand configs, asset indexes, calendars, generated creative and the approval ledger are written to your host's plugin data folder, or to `~/socialforge-workspace/` when the host provides none.

**Connections you choose.** The plugin ships with no connector switched on. When you connect a service yourself (for example an image or video generation provider, or a scheduling tool), the data you ask it to send goes to that service under its own terms. API keys you configure stay on your machine (SocialForge stores provider credentials in its data folder with owner-only file permissions).

**Web access.** Research, fact-checking and audit steps read public web pages you or the task point at, through your host's own web tools. SocialForge's own scripts fetch no web pages; they call only the generation and model-list endpoints below.

## Network endpoints and credentials

Nothing connects on install: there are no hooks and no `.mcp.json` ships. Pricing and model pages are read by your host's own web tools; `price_book.py` and `model_book.py` make no network calls. A SocialForge script opens a network connection only when you, or a skill you invoked, run it, and only to the endpoints below. Generation always waits for your approval of the brief and the quoted cost.

| What | When | Endpoint | Credential |
|---|---|---|---|
| `scripts/generate_image.py`, `scripts/edit_image.py` | when you approve an image generation or edit | Google Gemini / Vertex AI, then WaveSpeed and HiggsField as fallbacks you have keys for | `GEMINI_API_KEY` or `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION`; `WAVESPEED_API_KEY`; `HF_API_KEY` + `HF_API_SECRET`. With `GOOGLE_CLOUD_PROJECT` set and no stored service account, the Google SDK reads your gcloud application-default credentials from your machine (`scripts/credential_manager.py`) |
| `scripts/generate_video.py` | when you approve a video generation | WaveSpeed (Kling), Google Veo on Vertex AI (a Gemini API key alone cannot run Veo), HiggsField; it downloads the finished clip from the https URL the provider returns (any other scheme is refused) | `WAVESPEED_API_KEY`; `HF_API_KEY` + `HF_API_SECRET`; for Veo, `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION` or a stored Vertex profile |
| `scripts/index_assets.py` | when you index a brand's photo library, or run it with `--show-model` | Google Gemini for image analysis; before the first image (at most once every 7 days per key name) a GET of `https://generativelanguage.googleapis.com/v1beta/models` to choose the model, described below. A Google Drive source is only recorded by its URL: the script makes no Drive call, and the files are read through your host's own Drive integration | `GEMINI_API_KEY` or Google Cloud credentials |
| `scripts/refresh_models.py` | when you refresh the model registry | the model-list endpoints of api.anthropic.com, api.openai.com and generativelanguage.googleapis.com (the Gemini key in the `x-goog-api-key` header) | the matching key; a provider without one is skipped |
| `scripts/c2pa_sign.py` | when you sign an asset (C2PA) | `http://timestamp.digicert.com` (plain HTTP): an RFC 3161 timestamp request that carries a hash of the signature, not your file. With no certificate of your own, a throwaway self-signed key is created in a temporary folder for that one asset and deleted straight after it is read | none |
| `scripts/compose_image.py` | when you remove a background and the optional `rembg` package is installed | rembg fetches its model weights from the internet on first use | none |
| `scripts/install_deps.py` | **only** when you say yes in `/socialforge:setup`, run `install_deps.py --install`, or set `SOCIALFORGE_INSTALL_DEPS=1` for a single run. Otherwise nothing is installed: scripts print the exact pinned command and stop | PyPI, exact versions from `PINNED` in `scripts/install_deps.py`: Pillow, google-genai, wavespeed, imageio-ffmpeg, playwright (default groups), and on request higgsfield-client, rembg, c2pa-python, cryptography; Playwright's Chromium browser is a separate large download from Playwright's own CDN | none |
| Opt-in MCP connectors (for example a scheduler) | only after you copy an entry into `.mcp.json` yourself | the provider's endpoint in `.mcp.json.connectors-reference` | OAuth or an API key with that provider |

**Model choice from your Gemini key's own list.** Before an asset-indexing run analyses its first image, `scripts/model_router.py` asks Google which models your `GEMINI_API_KEY` can use (GET `https://generativelanguage.googleapis.com/v1beta/models`) and takes the newest generally available Flash from that list. The key goes only in the `x-goog-api-key` header and never in the URL, where proxies and server logs keep it. The call is made at most once every 7 days per key name, never on install or import, and not at all when a refresh finds nothing new to analyse; `index_assets.py --show-model` makes the same call so a cost quote names the model the run will use. The answer is kept in `model-router-cache.json` in the data folder, keyed by the environment variable's name (`GEMINI_API_KEY`), never the key and never the list itself. The list is read in pages of up to 1000 models; a list that runs past 20 pages is not used as a partial list, and the run falls back to the shipped default and says why. A run served by Vertex AI makes no list call (Vertex's catalogue is not the Gemini API's list) and uses the shipped default from `scripts/model_registry.json`. Set `MODEL_ROUTER_OFFLINE=1` to turn the call off; the run then uses the shipped default and says so, and a model you named is checked against local data only (the shipped registry and the deprecations record in `scripts/model_hints.json`). The asset index records, for the run and for each image, which model analysed it and where that answer came from.

**Deleting your data.** Remove the folders listed above. Uninstalling the plugin through your host removes the plugin's own files.

**Questions.** Open an issue at https://github.com/indranilbanerjee/socialforge/issues or use a private security advisory for anything sensitive.

The code is MIT-licensed; see [LICENSE](LICENSE) for the terms of use.
