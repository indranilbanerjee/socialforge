#!/usr/bin/env python3
"""
index_assets.py — Index brand visual assets using AI vision analysis.
Scans image libraries, analyzes each with Gemini Vision, builds asset-index.json.

Model selection (decided once per run, recorded in asset-index.json as `vision_model`):
  1. the brand's pin: `model_pins["index-assets.vision.google"]` in brand-config.json
  2. --model
  3. scripts/model_router.py, which lists the models this Gemini API key can use
     (GET .../v1beta/models, the key in the x-goog-api-key header, at most once a
     week per key name) and takes the newest active, generally available Flash in
     the family scripts/model_hints.json names
  4. the registry alias `latest-vision-google`, tagged "offline", when that list
     cannot be read, MODEL_ROUTER_OFFLINE=1 is set, or Vertex AI serves the run
     (its catalogue is not the Gemini API's list)
A pin or --model is a name asked for: kept with a warning if it is deprecated,
refused (exit 2, nothing sent) if it is retired. Nothing is swapped silently.
--show-model prints the decision and stops, so a cost quote is for the model the
run will use.
"""

import argparse
import base64
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add scripts dir to path for credential_manager + curator imports
sys.path.insert(0, str(Path(__file__).parent))

import model_router  # noqa: E402

try:
    from resolve_model import resolve as _resolve_model, get_registry as _get_registry
except ImportError:  # pragma: no cover
    # No literal id here: a literal would always answer, and one day the answer is
    # a retired model. Without the curator the offline rung has no default and the
    # router refuses, naming why.
    _resolve_model = None
    _get_registry = None

# Persistent storage: prefer ${CLAUDE_PLUGIN_DATA} (survives sessions/updates),
# fall back to ~/socialforge-workspace (legacy/local)
_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("PLUGIN_DATA") or ""
if _plugin_data and Path(_plugin_data).exists():
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
    WORKSPACE = Path.home() / "socialforge-workspace"
SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".webp"}

VISION_PROMPT = """Analyze this brand asset image for a social media automation system.

Provide a JSON response with these fields:
{
  "description": "2-3 sentence description of what's in the image",
  "subjects": ["main subjects: person, product, office, event, nature, abstract, etc."],
  "tags": ["15-20 descriptive tags"],
  "dominant_colors_hex": ["top 5 hex color codes"],
  "mood": "1-3 word mood description",
  "lighting": "natural/studio/ambient/dramatic/mixed",
  "setting": "indoor/outdoor/studio/mixed + specific setting",
  "suitable_for": ["3-5 descriptions of what social posts this suits"],
  "background_type": "transparent/solid_white/solid_color/simple/complex",
  "background_removable": true/false,
  "quality_assessment": "high/medium/low",
  "style_reference_worthy": true/false
}"""


sys.path.insert(0, str(Path(__file__).resolve().parent))  # scripts/ holds _common.py
import _common  # noqa: E402

VISION_JOB = "index-assets.vision.google"
VISION_CREDENTIAL = "GEMINI_API_KEY"          # the NAME of the environment variable; the router never stores the key
HINTS_FILE = Path(__file__).resolve().parent / "model_hints.json"
ROUTER_CACHE_NAME = "model-router-cache.json"  # in the workspace folder, next to the other per-user state
GEMINI_API_BACKEND = "ai-studio-fallback"      # credential_manager's name for "a GEMINI_API_KEY serves this run"
MIME_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def _iso(moment):
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _plain(model_id):
    """The Gemini API writes ids as `models/<id>`; the index records the id alone."""
    return model_id[len("models/"):] if isinstance(model_id, str) and model_id.startswith("models/") else model_id


def read_brand_config(brand):
    """(config, warning). A missing file is no config; an unreadable one is named, never ignored silently."""
    path = WORKSPACE / "brands" / brand / "brand-config.json"
    if not path.exists():
        return {}, None
    try:
        config = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(config, dict):
            return config, None
        problem = "it is not a JSON object"
    except (OSError, ValueError) as exc:
        problem = f"{type(exc).__name__}: {str(exc)[:100]}"
    return {}, f"{path.name} could not be read ({problem}), so no model pin was applied"


def brand_pin(config):
    """The model id this brand pins for the job, or None. A pin that is not a model id is refused, because
    ignoring it would swap the model the brand chose without saying so."""
    pins = (config or {}).get("model_pins")
    if pins is None:
        return None
    if not isinstance(pins, dict):
        raise model_router.RouterError(
            f'brand-config.json: model_pins must be an object that maps a job name to a model id, for example '
            f'{{"{VISION_JOB}": "<model id>"}}')
    if VISION_JOB not in pins:
        return None
    pin = pins[VISION_JOB]
    if not isinstance(pin, str) or not pin.strip():
        raise model_router.RouterError(
            f'brand-config.json: model_pins["{VISION_JOB}"] must be a model id (a non-empty string)')
    return _plain(pin.strip())


def _default_model(alias):
    if _resolve_model is None:
        return None
    try:
        return _resolve_model(alias)
    except (KeyError, ValueError):
        return None


def _registry():
    if _get_registry is None:
        return None
    try:
        return _get_registry()
    except (OSError, ValueError, KeyError):
        return None


def choose_vision_model(brand_config, cli_model, *, backend, api_key="", fetch=None, now=None, cache_path=None, env=None):
    """The vision model for this run, with where the answer came from. Raises model_router.RouterError when no image
    should be sent (a rejected key, no usable model, a retired model asked for, a malformed pin).

    Order: the brand's pin, then --model, then the router's pick from the key's own model list, then (list unreadable,
    offline, or a Vertex AI run) the registry alias, tagged "offline". Vertex serves its own catalogue, which the Gemini
    API list does not describe, so a Vertex run never makes the list call."""
    hints = json.loads(HINTS_FILE.read_text(encoding="utf-8-sig"))
    pin, flag = brand_pin(brand_config), _plain(cli_model) if cli_model else None
    notes = []
    if pin and flag and pin != flag:
        notes.append(f"the brand's model pin {pin} is used; --model {flag} was ignored "
                     f"(remove model_pins from brand-config.json to use the flag)")
    requested, selected_by = (pin, "brand-pin") if pin else (flag, "--model") if flag else (None, "router")
    environ = dict(os.environ if env is None else env)
    gemini_api = backend == GEMINI_API_BACKEND
    if not gemini_api:
        environ[model_router.OFFLINE_ENV] = "1"
    when = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    routing = model_router.route(
        VISION_JOB, hints, provider="google", credential_name=VISION_CREDENTIAL, api_key=api_key,
        default_model=_default_model(hints["jobs"][VISION_JOB]["default_alias"]), requested=requested, fetch=fetch,
        cache_path=cache_path, now=when, env=environ, registry=_registry())
    reason = routing["reason"]
    if not gemini_api:
        reason = (f"the run is served by {backend}, not the Gemini API (Vertex AI's model catalogue differs from the "
                  f"Gemini API's list), so the list was not read")
    if requested is None and routing["basis"] == "offline":
        selected_by = "registry-alias"
    return {"job": VISION_JOB, "model": routing["model"], "model_requested": routing["model_requested"],
            "selected_by": selected_by, "basis": routing["basis"], "source": routing["source"],
            "discovered_at": routing["discovered_at"], "decided_at": _iso(when), "replacement": routing["replacement"],
            "reason": reason, "router": routing["router"], "warnings": notes + list(routing["warnings"])}


def unavailable(reason, now=None):
    """The record for a run that cannot analyse anything: no client, so no model was asked for."""
    return {"job": VISION_JOB, "model": None, "model_requested": None, "selected_by": None, "basis": "unavailable",
            "source": None, "discovered_at": None, "decided_at": _iso(now or datetime.now(timezone.utc)),
            "replacement": None, "reason": reason, "router": model_router.ROUTER, "warnings": []}


def decide(brand, cli_model, backend, *, fetch=None, now=None):
    """Read the brand's pin and choose the model for a run served by `backend`."""
    config, warning = read_brand_config(brand)
    decision = choose_vision_model(config, cli_model, backend=backend, api_key=os.environ.get(VISION_CREDENTIAL, ""),
                                   fetch=fetch, now=now, cache_path=WORKSPACE / ROUTER_CACHE_NAME)
    if warning:
        decision["warnings"].insert(0, warning)
    return decision


def report(decision):
    for warning in decision["warnings"]:
        print(f"WARNING (google): {warning}", file=sys.stderr)
    if decision["basis"] == "offline" and decision["selected_by"] == "registry-alias":
        print(f"NOTE (google): {decision['reason']}; using the shipped default {decision['model']}", file=sys.stderr)


def refuse(exc):
    """The router refused: nothing was sent and nothing is written."""
    print(json.dumps({"error": exc.reason, "stage": "model routing", "action_required": True}))
    sys.exit(exc.exit_code)


def open_client():
    """(client, backend, failure): the Gemini client for this run, built once. `failure` names what stopped it, in the
    words the per-image failure reasons use."""
    try:
        from credential_manager import get_gemini_client
        client, backend = get_gemini_client()
        if not client:
            # backend carries the credential manager's error message here
            return None, None, f"no-credentials: {backend}"
        return client, backend, None
    except ImportError:
        # Fallback if credential_manager not available
        try:
            from google import genai
        except ImportError:
            return None, None, "dependency-missing: google-genai not importable"
        api_key = os.environ.get(VISION_CREDENTIAL)
        if not api_key:
            return None, None, f"no-credentials: {VISION_CREDENTIAL} not set"
        return genai.Client(api_key=api_key), GEMINI_API_BACKEND, None


def scan_images(source_path):
    """Find all image files in the source directory.
    Supports local paths and Google Drive paths.
    Google Drive: In Cowork, Drive is available via platform integration.
    In Claude Code, files must be downloaded or Drive path must be mounted.
    """
    source = Path(source_path)

    # Handle Google Drive URLs (strip to local path if available)
    source_str = str(source_path)
    if source_str.startswith("https://drive.google.com") or source_str.startswith("gdrive://"):
        # In Cowork: Claude can read Drive files via platform integration
        # In Claude Code: user must download or mount Drive
        # Return empty with helpful message — actual files accessed by Claude reading Drive
        return {"source_type": "google_drive", "url": source_str, "files": [],
                "note": "Google Drive source detected. Claude will read files via platform integration. Index will be built from files Claude can access."}

    if not source.exists():
        return []

    images = []
    for f in sorted(source.rglob("*")):
        if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS:
            images.append(f)
    return images


def analyze_image_gemini(image_path, model=None, client=None):
    """Analyze a single image with Gemini Vision.

    `client` is the one index_all built for the run (one client, one model decision); without it a client is built here.
    Returns (result_dict, None) on success or (None, reason) on failure —
    the reason string names what stopped the analysis so the index summary
    can report WHY images fell back to metadata-only instead of a bare count.
    """
    if client is None:
        client, _backend, failure = open_client()
        if client is None:
            return None, failure

    if not model:
        return None, ("unresolved-model: no vision model was chosen "
                      "(the model router and the registry alias both came back empty)")

    from google.genai import types

    img_data = image_path.read_bytes()
    mime = MIME_TYPES.get(image_path.suffix.lower(), "image/png")

    try:
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(data=img_data, mime_type=mime),
                VISION_PROMPT,
            ],
        )
        # Parse JSON from response
        resp_text = response.text.strip()
        if resp_text.startswith("```"):
            resp_text = resp_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(resp_text), None
    except Exception as e:
        return None, f"request-error: {type(e).__name__}: {str(e)[:150]}"


def build_basic_entry(image_path, source_root, asset_id):
    """Build a basic index entry from file metadata only."""
    try:
        from PIL import Image
        img = Image.open(image_path)
        w, h = img.size
    except Exception:
        w, h = 0, 0

    try:
        rel_path = str(image_path.relative_to(source_root))
        folder = str(image_path.parent.relative_to(source_root))
    except ValueError:  # reached via a symlink outside the source tree
        rel_path = image_path.name
        folder = ""
    entry = {
        "id": asset_id,
        "filename": image_path.name,
        "path": str(image_path),
        "relative_path": rel_path,
        "folder": folder,
        "dimensions": {"width": w, "height": h},
        "file_size_mb": round(image_path.stat().st_size / (1024 * 1024), 2),
        "format": image_path.suffix.lstrip(".").lower(),
        "ai_description": "",
        "tags": [],
        "detected_colors": [],
        "dominant_mood": "",
        "lighting": "",
        "setting": "",
        "subjects": [],
        "suitable_for": [],
        "has_background": True,
        "background_removable": False,
        "is_style_reference": False,
        "usage_history": [],
        "platforms_compatible": {}
    }
    if (w, h) == (0, 0):
        # 0x0 feeds match_assets crop-feasibility scoring — flag it so a
        # PIL failure is visible instead of masquerading as a real dimension.
        entry["dimensions_unreadable"] = True
    return entry


def stored_source(brand):
    """Recover the source path recorded by a previous index (`--refresh` without --source)."""
    brand_dir = WORKSPACE / "brands" / brand
    index_path = brand_dir / "asset-index.json"
    if index_path.exists():
        try:
            prior = json.loads(index_path.read_text(encoding="utf-8"))
            if prior.get("source_path"):
                return prior["source_path"]
        except (json.JSONDecodeError, OSError):
            pass
    source_file = brand_dir / "asset-source.json"
    if source_file.exists():
        try:
            config = json.loads(source_file.read_text(encoding="utf-8-sig"))
            return config.get("path") or config.get("url") or None
        except (json.JSONDecodeError, OSError):
            pass
    return None


def index_all(brand, source_path, refresh=False, model=None, *, fetch=None, now=None):
    """Index all images for a brand. `fetch` and `now` are the router's seams for tests: the list call and the clock."""
    brand_dir = WORKSPACE / "brands" / brand
    index_path = brand_dir / "asset-index.json"

    # Load existing index for refresh mode
    existing = {}
    prior_vision = None
    if refresh and index_path.exists():
        old_index = json.loads(index_path.read_text(encoding="utf-8"))
        prior_vision = old_index.get("vision_model")
        for asset in old_index.get("assets", []):
            existing[asset.get("path", "")] = asset

    images = scan_images(source_path)

    # Handle Google Drive source
    if isinstance(images, dict) and images.get("source_type") == "google_drive":
        print(json.dumps({
            "status": "google_drive_source",
            "url": images["url"],
            "instruction": "Google Drive asset source detected. To index Drive assets: 1) In Cowork: Claude reads Drive files via platform integration — provide the folder contents. 2) In Claude Code: download the folder locally first, then run with --source /local/path. The asset-source.json has been updated with the Drive URL for reference.",
            "asset_source_updated": True
        }))
        # Save the Drive URL in asset-source.json for reference
        source_config = {"type": "google_drive", "url": images["url"], "indexed_at": None}
        source_path_file = brand_dir / "asset-source.json"
        source_path_file.write_text(json.dumps(source_config, indent=2), encoding="utf-8")
        return

    if not images:
        print(json.dumps({"error": f"No images found in {source_path}"}))
        sys.exit(1)

    # The vision model is decided ONCE, and only when an image needs analysing: a refresh that finds nothing new asks for no
    # model and makes no list call. A refusal (retired pin, rejected key, no usable model) ends the run before anything is sent
    # or written.
    client, client_failure, vision = None, None, prior_vision
    if any(not (refresh and str(p) in existing) for p in images):
        client, backend, client_failure = open_client()
        if client is None:
            vision = unavailable(client_failure, now)
        else:
            try:
                vision = decide(brand, model, backend, fetch=fetch, now=now)
            except model_router.RouterError as exc:
                refuse(exc)
            report(vision)

    assets = []
    analyzed = 0
    skipped = 0
    ai_failures = []

    # New ids are minted ABOVE the highest id a preserved entry already holds.
    # Positional ids (`asset_{i+1}`) collided on --refresh: one new file that
    # sorts first re-minted asset_001 while the preserved entry kept it too,
    # and every downstream lookup by id then resolved to the wrong image.
    import re as _re
    next_num = 1
    if existing:
        nums = []
        for a in existing.values():
            m = _re.match(r"asset_(\d+)$", str(a.get("id", "")))
            if m:
                nums.append(int(m.group(1)))
        next_num = max(nums, default=0) + 1

    for i, img_path in enumerate(images):
        # Skip already-indexed in refresh mode (they keep their original id)
        if refresh and str(img_path) in existing:
            assets.append(existing[str(img_path)])
            skipped += 1
            continue

        asset_id = f"asset_{next_num:03d}"
        next_num += 1

        entry = build_basic_entry(img_path, Path(source_path), asset_id)

        # Try AI analysis
        if client is None:
            ai_result, ai_fail_reason = None, client_failure
        else:
            ai_result, ai_fail_reason = analyze_image_gemini(img_path, model=vision["model"], client=client)
        if ai_fail_reason:
            ai_failures.append({"id": asset_id, "file": img_path.name, "reason": ai_fail_reason})
        if ai_result:
            # Each analysed asset names the model that analysed it: a refresh can mix models in one index.
            entry["analysis_model"] = vision["model"]
            entry["analyzed_at"] = datetime.now(timezone.utc).isoformat()
            entry["ai_description"] = ai_result.get("description", "")
            entry["tags"] = ai_result.get("tags", [])
            entry["detected_colors"] = ai_result.get("dominant_colors_hex", [])
            entry["dominant_mood"] = ai_result.get("mood", "")
            entry["lighting"] = ai_result.get("lighting", "")
            entry["setting"] = ai_result.get("setting", "")
            entry["subjects"] = ai_result.get("subjects", [])
            entry["suitable_for"] = ai_result.get("suitable_for", [])
            entry["background_removable"] = ai_result.get("background_removable", False)
            entry["is_style_reference"] = ai_result.get("style_reference_worthy", False)
            analyzed += 1

        assets.append(entry)

        # Progress every 10 images
        if (i + 1) % 10 == 0:
            print(json.dumps({"progress": f"{i+1}/{len(images)}", "analyzed": analyzed}), file=sys.stderr)

    index = {
        "brand": brand,
        "indexed_at": datetime.now(timezone.utc).isoformat(),
        "source": "local",
        "source_path": str(source_path),
        "total_assets": len(assets),
    }
    if vision:
        index["vision_model"] = vision  # the latest decision; each asset's own analysis_model is the truth for that asset
    index["assets"] = assets

    brand_dir.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")

    style_refs = [a["id"] for a in assets if a.get("is_style_reference")]

    # Aggregate failure reasons so the summary says WHY analysis fell back,
    # not just how many times.
    failure_counts = {}
    for f in ai_failures:
        key = f["reason"].split(":", 1)[0]
        failure_counts[key] = failure_counts.get(key, 0) + 1

    summary = {
        "brand": brand,
        "total_images": len(images),
        "ai_analyzed": analyzed,
        "skipped_existing": skipped,
        "metadata_only": len(images) - analyzed - skipped,
        "style_reference_candidates": len(style_refs),
        "output": str(index_path)
    }
    if vision:
        summary["vision_model"] = vision
    if ai_failures:
        summary["ai_failure_reasons"] = failure_counts
        summary["first_failure_detail"] = ai_failures[0]["reason"]
    attempted = len(images) - skipped
    total_ai_failure = attempted > 0 and analyzed == 0
    if total_ai_failure:
        summary["ai_analysis"] = ("FAILED — 0 of "
                                  f"{attempted} images were AI-analyzed; the index is metadata-only "
                                  "(empty tags degrade every downstream asset match)")
        summary["action_required"] = True
    print(json.dumps(summary, indent=2))
    if total_ai_failure:
        sys.exit(3)  # index written, but the AI-analysis contract was not met


def show_model(brand, cli_model, fetch=None, now=None):
    """Print the model this run would use and stop: no image is read or sent and no index is written. A cost quote is for
    this model, not for the registry alias, which the router may have moved past."""
    client, backend, failure = open_client()
    if client is None:
        print(json.dumps({**unavailable(failure, now), "action_required": True}, indent=2))
        return 4
    try:
        decision = decide(brand, cli_model, backend, fetch=fetch, now=now)
    except model_router.RouterError as exc:
        refuse(exc)
    report(decision)
    print(json.dumps(decision, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(description="SocialForge Asset Indexer")
    parser.add_argument("--brand", type=_common.path_component, required=True)
    parser.add_argument("--source", default=None,
                        help="Path to image folder (omit to reuse the source recorded by the previous index)")
    parser.add_argument("--refresh", action="store_true", help="Only index new/changed images")
    parser.add_argument("--model", default=None,
                        help="Vision model id. Without it the model comes from your Gemini API key's own model list "
                             "(scripts/model_router.py). A brand pin (model_pins in brand-config.json) overrides this flag. "
                             "A deprecated id is kept with a warning; a retired one is refused (exit 2) and the "
                             "replacement is named.")
    parser.add_argument("--show-model", action="store_true",
                        help="Print which vision model this run would use and stop (no image is read or sent, no index "
                             "is written). Run it before quoting the cost.")
    args = parser.parse_args()

    if args.show_model:
        sys.exit(show_model(args.brand, args.model))

    source = args.source or stored_source(args.brand)
    if not source:
        parser.error("--source is required (no previous index recorded a source path for this brand)")

    index_all(args.brand, source, args.refresh, model=args.model)


if __name__ == "__main__":
    main()
