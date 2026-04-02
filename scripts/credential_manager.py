#!/usr/bin/env python3
"""
credential_manager.py - Manage API credentials for SocialForge.

Stores credentials in plugin persistent data directory.
Supports: Google Cloud Vertex AI (service account JSON) + WaveSpeed API key.

Usage from other scripts:
    from credential_manager import get_gemini_client, get_wavespeed_key, get_status
"""

import json
import os
import shutil
from pathlib import Path

_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
if _plugin_data and Path(_plugin_data).exists():
    CRED_DIR = Path(_plugin_data) / "socialforge"
else:
    CRED_DIR = Path.home() / "socialforge-workspace"

CRED_FILE = CRED_DIR / "credentials.json"
GCP_KEY_FILE = CRED_DIR / "gcp-credentials.json"


def _ensure_dir():
    CRED_DIR.mkdir(parents=True, exist_ok=True)


def _load_creds():
    if CRED_FILE.exists():
        try:
            return json.loads(CRED_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_creds(data):
    _ensure_dir()
    CRED_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def setup_vertex_ai(json_path):
    """Copy GCP service account JSON to plugin data, extract project_id."""
    json_path = Path(json_path).expanduser().resolve()
    if not json_path.exists():
        return {"status": "FAILED", "error": f"File not found: {json_path}"}
    try:
        sa_data = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {"status": "FAILED", "error": f"Invalid JSON file: {e}"}
    project_id = sa_data.get("project_id")
    if not project_id:
        return {"status": "FAILED", "error": "No project_id in JSON. Is this a service account key?"}
    _ensure_dir()
    shutil.copy2(str(json_path), str(GCP_KEY_FILE))
    creds = _load_creds()
    creds["vertex_ai"] = {
        "credentials_file": str(GCP_KEY_FILE),
        "project_id": project_id,
        "location": "us-central1",
        "service_account": sa_data.get("client_email", "unknown"),
    }
    _save_creds(creds)
    return {
        "status": "success",
        "project_id": project_id,
        "service_account": sa_data.get("client_email", ""),
        "stored_at": str(GCP_KEY_FILE),
    }


def validate_vertex_ai():
    """Check if Vertex AI credentials are configured."""
    creds = _load_creds()
    va = creds.get("vertex_ai")
    if not va:
        return {"configured": False, "error": "Not configured. Run /sf:setup"}
    if not Path(va["credentials_file"]).exists():
        return {"configured": False, "error": "Credentials file missing. Run /sf:setup again"}
    return {
        "configured": True,
        "project_id": va["project_id"],
        "location": va.get("location", "us-central1"),
        "service_account": va.get("service_account", ""),
    }


def get_gemini_client():
    """Return a configured google-genai Client for Vertex AI image generation.
    Returns: (client, backend_name) or (None, error_message)
    """
    try:
        from google import genai
    except ImportError:
        return None, "google-genai not installed. Run: pip install google-genai"

    # Priority 1: Plugin data credentials (Vertex AI)
    creds = _load_creds()
    va = creds.get("vertex_ai")
    if va and Path(va.get("credentials_file", "")).exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = va["credentials_file"]
        try:
            client = genai.Client(vertexai=True, project=va["project_id"],
                                  location=va.get("location", "us-central1"))
            return client, "vertex-ai"
        except Exception:
            pass

    # Priority 2: Env var GOOGLE_CLOUD_PROJECT + ADC
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project:
        try:
            client = genai.Client(vertexai=True, project=project,
                                  location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"))
            return client, "vertex-ai-env"
        except Exception:
            pass

    # Priority 3: AI Studio API key (fallback)
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            return client, "ai-studio-fallback"
        except Exception as e:
            return None, f"AI Studio init failed: {e}"

    return None, "No image generation credentials. Run /sf:setup or set GOOGLE_CLOUD_PROJECT."


def setup_wavespeed(api_key):
    """Save WaveSpeed API key to plugin data."""
    if not api_key or len(api_key) < 20:
        return {"status": "FAILED", "error": "Invalid API key"}
    creds = _load_creds()
    creds["wavespeed"] = {"api_key": api_key}
    _save_creds(creds)
    return {"status": "success", "stored_at": str(CRED_FILE)}


def validate_wavespeed():
    """Check if WaveSpeed API key is configured."""
    creds = _load_creds()
    ws = creds.get("wavespeed")
    if not ws or not ws.get("api_key"):
        if os.environ.get("WAVESPEED_API_KEY"):
            return {"configured": True, "source": "env_var"}
        return {"configured": False, "error": "Not configured. Run /sf:setup --video"}
    return {"configured": True, "source": "plugin_data"}


def get_wavespeed_key():
    """Return WaveSpeed API key. Plugin data first, env var fallback."""
    creds = _load_creds()
    ws = creds.get("wavespeed")
    if ws and ws.get("api_key"):
        return ws["api_key"]
    return os.environ.get("WAVESPEED_API_KEY")


def setup_higgsfield(api_key, api_secret):
    """Save HiggsField API key + secret to plugin data."""
    if not api_key or not api_secret:
        return {"status": "FAILED", "error": "Both API key and secret are required"}
    creds = _load_creds()
    creds["higgsfield"] = {"api_key": api_key, "api_secret": api_secret}
    _save_creds(creds)
    return {"status": "success", "stored_at": str(CRED_FILE)}


def validate_higgsfield():
    """Check if HiggsField credentials are configured."""
    creds = _load_creds()
    hf = creds.get("higgsfield")
    if not hf or not hf.get("api_key"):
        if os.environ.get("HF_API_KEY") and os.environ.get("HF_API_SECRET"):
            return {"configured": True, "source": "env_var"}
        return {"configured": False}
    return {"configured": True, "source": "plugin_data"}


def get_higgsfield_auth():
    """Return (api_key, api_secret) for HiggsField. Plugin data first, env fallback."""
    creds = _load_creds()
    hf = creds.get("higgsfield")
    if hf and hf.get("api_key") and hf.get("api_secret"):
        return hf["api_key"], hf["api_secret"]
    return os.environ.get("HF_API_KEY"), os.environ.get("HF_API_SECRET")


def get_status():
    """Return status of all configured services."""
    va = validate_vertex_ai()
    ws = validate_wavespeed()
    hf = validate_higgsfield()

    # Image: ready if any provider is configured
    img_providers = []
    if va.get("configured"):
        img_providers.append("vertex-ai")
    if ws.get("configured"):
        img_providers.append("wavespeed")
    if hf.get("configured"):
        img_providers.append("higgsfield")

    # Video: ready if any provider is configured
    vid_providers = []
    if ws.get("configured"):
        vid_providers.append("wavespeed")
    if hf.get("configured"):
        vid_providers.append("higgsfield")

    return {
        "vertex_ai": va,
        "wavespeed": ws,
        "higgsfield": hf,
        "image_generation": "ready" if img_providers else "not_configured",
        "image_providers": img_providers,
        "video_generation": "ready" if vid_providers else "not_configured",
        "video_providers": vid_providers,
        "credentials_dir": str(CRED_DIR),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SocialForge Credential Manager")
    sub = parser.add_subparsers(dest="action")
    va_p = sub.add_parser("setup-vertex", help="Configure Vertex AI")
    va_p.add_argument("--json-path", required=True, help="Path to GCP service account JSON")
    ws_p = sub.add_parser("setup-wavespeed", help="Configure WaveSpeed")
    ws_p.add_argument("--api-key", required=True, help="WaveSpeed API key")
    hf_p = sub.add_parser("setup-higgsfield", help="Configure HiggsField")
    hf_p.add_argument("--api-key", required=True, help="HiggsField API key")
    hf_p.add_argument("--api-secret", required=True, help="HiggsField API secret")
    sub.add_parser("status", help="Show credential status")
    sub.add_parser("validate", help="Validate all credentials")
    args = parser.parse_args()
    if args.action == "setup-vertex":
        result = setup_vertex_ai(args.json_path)
    elif args.action == "setup-wavespeed":
        result = setup_wavespeed(args.api_key)
    elif args.action == "setup-higgsfield":
        result = setup_higgsfield(args.api_key, args.api_secret)
    elif args.action == "status":
        result = get_status()
    elif args.action == "validate":
        result = {"vertex_ai": validate_vertex_ai(), "wavespeed": validate_wavespeed(), "higgsfield": validate_higgsfield()}
    else:
        parser.print_help()
        return
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
