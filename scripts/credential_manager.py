#!/usr/bin/env python3
"""
credential_manager.py - Manage API credentials for SocialForge.

Stores credentials in plugin persistent data directory.
Supports: Google Cloud Vertex AI (service account JSON) + WaveSpeed API key.

Usage from other scripts:
    from credential_manager import get_gemini_client, get_wavespeed_key, get_status
"""

import getpass
import json
import os
import shutil
import sys
from pathlib import Path

_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("PLUGIN_DATA") or ""
if _plugin_data and Path(_plugin_data).exists():
    CRED_DIR = Path(_plugin_data) / "socialforge"
else:
    CRED_DIR = Path.home() / "socialforge-workspace"

CRED_FILE = CRED_DIR / "credentials.json"
GCP_KEY_FILE = CRED_DIR / "gcp-credentials.json"


def _ensure_dir():
    CRED_DIR.mkdir(parents=True, exist_ok=True)
    _restrict(CRED_DIR, 0o700)


def _restrict(path, mode):
    """Tighten permissions on a secret file/dir. No-op where chmod isn't meaningful."""
    try:
        os.chmod(path, mode)
    except (OSError, NotImplementedError):
        pass


def _load_creds_checked():
    """Load credentials, distinguishing 'no file' from 'unreadable file'.

    Returns (data, load_error). A corrupt credentials.json must never read as
    'nothing configured': that misdiagnosis told users to re-run setup, and
    the re-run then overwrote the file — silently destroying every other
    provider's stored keys.
    """
    if CRED_FILE.exists():
        try:
            return json.loads(CRED_FILE.read_text(encoding="utf-8")), None
        except (json.JSONDecodeError, OSError) as e:
            return {}, f"credentials.json is unreadable ({type(e).__name__}: {e}) at {CRED_FILE}"
    return {}, None


def _load_creds():
    return _load_creds_checked()[0]


def _save_creds(data):
    _ensure_dir()
    CRED_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    _restrict(CRED_FILE, 0o600)


def _refuse_if_corrupt():
    """Setup guard: if the credentials file exists but is unreadable, refuse to
    write over it — the stored keys are damaged, not gone. Returns the FAILED
    payload to hand back, or None when writing is safe."""
    _, load_error = _load_creds_checked()
    if load_error:
        return {
            "status": "FAILED",
            "error": (f"{load_error} — refusing to overwrite it: other providers' keys "
                      "may still be recoverable from the damaged file. Fix the JSON "
                      "or delete the file deliberately, then re-run setup."),
        }
    return None


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
    refused = _refuse_if_corrupt()
    if refused:
        return refused
    _ensure_dir()
    shutil.copy2(str(json_path), str(GCP_KEY_FILE))
    _restrict(GCP_KEY_FILE, 0o600)
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
    creds, load_error = _load_creds_checked()
    if load_error:
        return {"configured": False, "error": f"{load_error} — stored keys are damaged, not gone; fix the file rather than re-running setup"}
    va = creds.get("vertex_ai")
    if not va:
        return {"configured": False, "error": "Not configured. Run /socialforge:setup"}
    if not Path(va.get("credentials_file", "")).exists():
        return {"configured": False, "error": "Credentials file missing. Run /socialforge:setup again"}
    return {
        "configured": True,
        "project_id": va.get("project_id", "unknown"),
        "location": va.get("location", "us-central1"),
        "service_account": va.get("service_account", ""),
    }


def get_gemini_client():
    """Return a configured google-genai Client for Vertex AI image generation.
    Returns: (client, backend_name) or (None, error_message).

    Every rung that fails is remembered: "configured but broken" must never
    read as "not configured". The terminal message names each path tried and
    why it failed — this was the 'I ran /socialforge:setup and it still says
    no credentials' bug.
    """
    try:
        from google import genai
    except ImportError:
        return None, "google-genai not installed. Run: pip install google-genai"

    tried = []

    # Priority 1: Plugin data credentials (Vertex AI)
    creds, load_error = _load_creds_checked()
    if load_error:
        tried.append(f"stored-credentials: {load_error}")
    va = creds.get("vertex_ai")
    if va and Path(va.get("credentials_file", "")).exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = va["credentials_file"]
        try:
            client = genai.Client(vertexai=True, project=va.get("project_id"),
                                  location=va.get("location", "us-central1"))
            return client, "vertex-ai"
        except Exception as e:
            tried.append(f"vertex-ai (stored service account): {type(e).__name__}: {str(e)[:120]}")
    elif va:
        tried.append(f"vertex-ai (stored): credentials_file missing at {va.get('credentials_file')}")

    # Priority 2: Env var GOOGLE_CLOUD_PROJECT + ADC
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project:
        try:
            client = genai.Client(vertexai=True, project=project,
                                  location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"))
            return client, "vertex-ai-env"
        except Exception as e:
            tried.append(f"vertex-ai-env (GOOGLE_CLOUD_PROJECT): {type(e).__name__}: {str(e)[:120]}")

    # Priority 3: AI Studio API key (fallback)
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            return client, "ai-studio-fallback"
        except Exception as e:
            tried.append(f"ai-studio (GEMINI_API_KEY): {type(e).__name__}: {str(e)[:120]}")

    if tried:
        return None, ("Credentials were found but no path produced a working client — "
                      + "; ".join(tried))
    return None, "No image generation credentials. Run /socialforge:setup or set GOOGLE_CLOUD_PROJECT."


def setup_wavespeed(api_key):
    """Save WaveSpeed API key to plugin data."""
    if not api_key or len(api_key) < 20:
        return {"status": "FAILED", "error": "Invalid API key"}
    refused = _refuse_if_corrupt()
    if refused:
        return refused
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
        return {"configured": False, "error": "Not configured. Run /socialforge:setup --video"}
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
    refused = _refuse_if_corrupt()
    if refused:
        return refused
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


def _read_secret(value, env_var, label):
    """Resolve a secret without requiring it on the command line.

    Precedence: explicit flag > environment variable > stdin. Passing a secret as a
    CLI argument leaks it into shell history and the process table, so the flag is
    optional and the env-var / stdin forms are preferred.
    """
    if value:
        return value
    from_env = os.environ.get(env_var)
    if from_env:
        return from_env
    if not sys.stdin.isatty():
        # Non-interactive (agent/CI harness): never fall through to getpass —
        # it would block on a closed stdin. An empty pipe means no secret,
        # and the setup function will report the invalid/missing key.
        return sys.stdin.readline().strip() or None
    return getpass.getpass(f"{label}: ").strip()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SocialForge Credential Manager")
    sub = parser.add_subparsers(dest="action")
    va_p = sub.add_parser("setup-vertex", help="Configure Vertex AI")
    va_p.add_argument("--json-path", required=True, help="Path to GCP service account JSON")
    ws_p = sub.add_parser("setup-wavespeed", help="Configure WaveSpeed")
    ws_p.add_argument("--api-key", default=None,
                      help="WaveSpeed API key (omit to read from WAVESPEED_API_KEY or stdin — avoids shell-history leaks)")
    hf_p = sub.add_parser("setup-higgsfield", help="Configure HiggsField")
    hf_p.add_argument("--api-key", default=None,
                      help="HiggsField API key (omit to read from HF_API_KEY or stdin)")
    hf_p.add_argument("--api-secret", default=None,
                      help="HiggsField API secret (omit to read from HF_API_SECRET or stdin)")
    sub.add_parser("status", help="Show credential status")
    sub.add_parser("validate", help="Validate all credentials")
    args = parser.parse_args()
    if args.action == "setup-vertex":
        result = setup_vertex_ai(args.json_path)
    elif args.action == "setup-wavespeed":
        result = setup_wavespeed(_read_secret(args.api_key, "WAVESPEED_API_KEY", "WaveSpeed API key"))
    elif args.action == "setup-higgsfield":
        result = setup_higgsfield(
            _read_secret(args.api_key, "HF_API_KEY", "HiggsField API key"),
            _read_secret(args.api_secret, "HF_API_SECRET", "HiggsField API secret"),
        )
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
