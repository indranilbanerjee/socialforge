#!/usr/bin/env python3
"""
credential_manager.py - Manage API credentials for SocialForge.

What it keeps (1.31.0), in `credentials.json` in the plugin data folder:
  * Vertex AI: the PATH of your service-account JSON file, its project id and account email. The key file stays
    where you keep it; nothing is copied. (Before 1.31.0 setup copied it to `gcp-credentials.json`; an old copy is
    left alone, not used, and reported until you delete it.)
  * WaveSpeed and HiggsField: when the key is in the environment (WAVESPEED_API_KEY, HF_API_KEY + HF_API_SECRET),
    only the variable NAMES. The value is read from the environment each time it is needed and never written.
  * A key given through --api-key-stdin or --prompt: in the OS keychain when the optional `keyring` package is
    installed and has a working backend (`install_deps.py --groups keyring`). Without one it falls back to
    credentials.json in plain text, and the result carries a warning saying so.
Keys are never taken on the command line: --api-key / --api-secret exit 2 (shell history and the process table).
chmod 600 does nothing useful on Windows, so there a file holding a secret is also limited to your account with
`icacls <file> /inheritance:r /grant:r <you>:F`.

Usage from other scripts:
    from credential_manager import get_gemini_client, get_wavespeed_key, get_status
"""

import getpass
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # scripts/ holds _common.py
import _common  # noqa: E402

_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("PLUGIN_DATA") or ""
if _plugin_data and Path(_plugin_data).exists():
    CRED_DIR = Path(_plugin_data) / "socialforge"
else:
    CRED_DIR = Path.home() / "socialforge-workspace"

CRED_FILE = CRED_DIR / "credentials.json"
GCP_KEY_FILE = CRED_DIR / "gcp-credentials.json"   # the copy setup made before 1.31.0; no longer written or needed

KEYRING_SERVICE = "socialforge"
ENV_VARS = {"wavespeed": ("WAVESPEED_API_KEY",), "higgsfield": ("HF_API_KEY", "HF_API_SECRET")}
FIELDS = {"wavespeed": ("api_key",), "higgsfield": ("api_key", "api_secret")}
PLAINTEXT_WARNING = ("no OS keychain is available (install it with: install_deps.py --groups keyring), so the key "
                     "was written in plain text to {path}. Prefer the environment variable, which is never written.")


def _ensure_dir():
    CRED_DIR.mkdir(parents=True, exist_ok=True)
    _restrict(CRED_DIR, 0o700)


def _restrict(path, mode):
    """chmod a secret file/dir. On Windows this does nothing useful (only the read-only bit is honoured): see
    _restrict_secret_file."""
    try:
        os.chmod(path, mode)
    except (OSError, NotImplementedError):
        pass


def _windows_account() -> str:
    user = os.environ.get("USERNAME") or getpass.getuser()
    domain = os.environ.get("USERDOMAIN")
    return f"{domain}\\{user}" if domain and "\\" not in user else user


def _restrict_secret_file(path, windows=None):
    """Limit a file that holds a secret to the current account. Returns a warning string, or None when it worked.

    POSIX: chmod 600. Windows: chmod cannot do this, so the inherited ACL is removed and only the current account is
    granted access, with icacls run as an argument list (no shell)."""
    _restrict(path, 0o600)
    if windows is None:
        windows = os.name == "nt"
    if not windows:
        return None
    cmd = ["icacls", str(path), "/inheritance:r", "/grant:r", f"{_windows_account()}:F"]
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return (f"could not limit {path} to your account with icacls ({type(exc).__name__}); "
                "other accounts on this PC may be able to read it")
    if done.returncode != 0:
        return (f"icacls could not limit {path} to your account (exit {done.returncode}); "
                "other accounts on this PC may be able to read it")
    return None


def _keyring():
    """The keyring module when it is installed AND has a working backend, else None (optional dependency)."""
    try:
        import keyring
    except ImportError:
        return None
    try:
        backend = keyring.get_keyring()
        priority = getattr(backend, "priority", 0)
        if priority is None or priority <= 0:    # keyring.backends.fail / null: nothing would be stored
            return None
    except Exception:
        return None
    return keyring


def _keyring_name(provider: str, field: str) -> str:
    return f"{provider}_{field}"


def _store_secrets(provider: str, values: dict):
    """Persist secrets that did not come from the environment: OS keychain first, else the file with a warning.
    Returns (record, warnings)."""
    kr = _keyring()
    fallback = ""
    if kr is not None:
        try:
            for field, value in values.items():
                kr.set_password(KEYRING_SERVICE, _keyring_name(provider, field), value)
            return {"source": "keyring", "keyring_service": KEYRING_SERVICE,
                    "keyring_names": [_keyring_name(provider, f) for f in values]}, []
        except Exception as exc:  # a locked or broken keychain: fall back, and say so
            fallback = f"the OS keychain refused the key ({type(exc).__name__}); "
    return {"source": "file", **values}, [fallback + PLAINTEXT_WARNING.format(path=CRED_FILE)]


def _stored_secrets(provider: str) -> dict:
    """Secrets setup persisted (keychain or file) for a provider, or {} when none are stored."""
    rec = _load_creds().get(provider) or {}
    fields = FIELDS[provider]
    if rec.get("source") == "keyring":
        kr = _keyring()
        if kr is None:
            return {}
        try:
            got = {f: kr.get_password(rec.get("keyring_service", KEYRING_SERVICE), _keyring_name(provider, f))
                   for f in fields}
        except Exception:
            return {}
        return got if all(got.values()) else {}
    got = {f: rec.get(f) for f in fields}
    return got if all(got.values()) else {}


def _plaintext_warnings(creds=None) -> list:
    """Warnings for secrets an older setup (or the no-keychain fallback) left on disk in plain text."""
    creds = _load_creds() if creds is None else creds
    out = []
    for provider, fields in FIELDS.items():
        rec = creds.get(provider) or {}
        if any(rec.get(f) for f in fields):
            out.append(f"{provider}: a key is stored in plain text in {CRED_FILE}. Set "
                       f"{' and '.join(ENV_VARS[provider])} and re-run setup to replace it with the variable name.")
    if GCP_KEY_FILE.exists():
        out.append(f"vertex_ai: an older SocialForge copy of a service-account key is at {GCP_KEY_FILE}. "
                   "Re-run setup-vertex with your own key file's path, then delete this copy yourself.")
    return out


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
    """Write credentials.json and limit it to the current account. Returns a warning string or None."""
    _ensure_dir()
    CRED_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return _restrict_secret_file(CRED_FILE)


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
    """Record the PATH of a GCP service-account JSON (no copy is made) and its project_id."""
    json_path = Path(json_path).expanduser().resolve()
    if not json_path.exists():
        return {"status": "FAILED", "error": f"File not found: {json_path}"}
    try:
        sa_data = json.loads(json_path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError) as e:
        return {"status": "FAILED", "error": f"Invalid JSON file: {e}"}
    project_id = sa_data.get("project_id")
    if not project_id:
        return {"status": "FAILED", "error": "No project_id in JSON. Is this a service account key?"}
    refused = _refuse_if_corrupt()
    if refused:
        return refused
    creds = _load_creds()
    creds["vertex_ai"] = {
        "credentials_file": str(json_path),
        "source": "user_file",
        "project_id": project_id,
        "location": "us-central1",
        "service_account": sa_data.get("client_email", "unknown"),
    }
    warnings = [w for w in [_save_creds(creds)] if w]
    if GCP_KEY_FILE.exists() and os.path.normcase(str(GCP_KEY_FILE.resolve())) != os.path.normcase(str(json_path)):
        warnings.append(f"an older SocialForge copy of a service-account key is still at {GCP_KEY_FILE}. It is no "
                        "longer used; delete it yourself once you no longer need it.")
    result = {
        "status": "success",
        "project_id": project_id,
        "service_account": sa_data.get("client_email", ""),
        "key_file": str(json_path),
        "note": "the key file is used where it is (not copied): keep it there, readable only by you",
        "stored_at": str(CRED_FILE),
    }
    if warnings:
        result["warnings"] = warnings
    return result


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


def get_vertex_client():
    """Return (client, backend_name) for Vertex AI ONLY, or (None, reason).

    Veo 3.1 is a Vertex AI model: the Gemini API stopped serving the Veo 3.1 previews on 2026-10-22 and does not
    list veo-3.1-generate-001, so an AI Studio client cannot make a Veo clip and is never returned here. A stored
    service-account profile wins, then GOOGLE_CLOUD_PROJECT (application-default credentials)."""
    try:
        from google import genai
    except ImportError:
        return None, "google-genai is not installed. Run: " + _common.script_command("install_deps.py") + " (it prints the pinned install command)"
    creds, load_error = _load_creds_checked()
    va = creds.get("vertex_ai")
    if va and Path(va.get("credentials_file", "")).exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = va["credentials_file"]
        try:
            return genai.Client(vertexai=True, project=va.get("project_id"),
                                location=va.get("location", "us-central1")), "vertex-ai"
        except Exception as e:
            return None, f"Vertex AI client from the stored profile failed: {e}"
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project:
        try:
            return genai.Client(vertexai=True, project=project,
                                location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")), "vertex-env"
        except Exception as e:
            return None, f"Vertex AI client for project {project} failed: {e}"
    reason = "no Vertex AI profile and no GOOGLE_CLOUD_PROJECT"
    if load_error:
        reason += f" ({load_error})"
    return None, reason


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
        return None, "google-genai is not installed. Run: " + _common.script_command("install_deps.py") + " (it prints the pinned install command)"

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
            client = genai.Client(api_key=api_key, http_options=_common.genai_http_options())
            return client, "ai-studio-fallback"
        except Exception as e:
            tried.append(f"ai-studio (GEMINI_API_KEY): {type(e).__name__}: {str(e)[:120]}")

    if tried:
        return None, ("Credentials were found but no path produced a working client — "
                      + "; ".join(tried))
    return None, "No image generation credentials. Run /socialforge:setup or set GOOGLE_CLOUD_PROJECT."


def _setup_secrets(provider: str, values: dict, from_env: bool):
    """Record a provider's credentials. From the environment only the variable names are written; otherwise the values
    go to the OS keychain, or (no keychain) to the file with a warning."""
    refused = _refuse_if_corrupt()
    if refused:
        return refused
    creds = _load_creds()
    if from_env:
        record, warnings = {"source": "env", "env_vars": list(ENV_VARS[provider])}, []
    else:
        record, warnings = _store_secrets(provider, values)
    creds[provider] = record
    file_warning = _save_creds(creds)
    if file_warning and record.get("source") == "file":
        warnings.append(file_warning)
    result = {"status": "success", "source": record["source"], "stored_at": str(CRED_FILE)}
    if from_env:
        names = " and ".join(ENV_VARS[provider])
        result["note"] = (f"only the variable name(s) {names} were written; the value is read from the environment "
                          "each time it is needed")
    if warnings:
        result["warnings"] = warnings
        for w in warnings:
            print("WARNING: " + w, file=sys.stderr)
    return result


def setup_wavespeed(api_key, from_env=False):
    """Record the WaveSpeed key: the variable name when it came from the environment, else keychain (or file + warning)."""
    if not api_key or len(api_key) < 20:
        return {"status": "FAILED", "error": "Invalid API key"}
    return _setup_secrets("wavespeed", {"api_key": api_key}, from_env)


def _validate(provider, error):
    creds, load_error = _load_creds_checked()
    if load_error:
        return {"configured": False,
                "error": f"{load_error} — stored keys are damaged, not gone; fix the file rather than re-running setup"}
    if all(os.environ.get(v) for v in ENV_VARS[provider]):
        return {"configured": True, "source": "env_var"}
    rec = creds.get(provider) or {}
    if _stored_secrets(provider):
        if rec.get("source") == "keyring":
            return {"configured": True, "source": "keyring"}
        return {"configured": True, "source": "plugin_data_file", "warning": f"stored in plain text in {CRED_FILE}"}
    names = " and ".join(ENV_VARS[provider])
    if rec.get("source") == "env":
        return {"configured": False, "error": f"setup recorded {names}, but this process does not see it: set it where "
                                              "your host's shell can read it"}
    if rec.get("source") == "keyring":
        return {"configured": False, "error": "setup stored the key in the OS keychain, but it cannot be read here "
                                              "(keyring missing or locked, or another account). Re-run setup."}
    return {"configured": False, "error": error} if error else {"configured": False}


def validate_wavespeed():
    """Check if WaveSpeed API key is configured."""
    return _validate("wavespeed", "Not configured. Run /socialforge:setup --video")


def get_wavespeed_key():
    """Return the WaveSpeed API key: the environment first (read now, never written), then what setup stored."""
    return os.environ.get("WAVESPEED_API_KEY") or _stored_secrets("wavespeed").get("api_key")


def setup_higgsfield(api_key, api_secret, from_env=False):
    """Record the HiggsField key + secret: variable names from the environment, else keychain (or file + warning)."""
    if not api_key or not api_secret:
        return {"status": "FAILED", "error": "Both API key and secret are required"}
    return _setup_secrets("higgsfield", {"api_key": api_key, "api_secret": api_secret}, from_env)


def validate_higgsfield():
    """Check if HiggsField credentials are configured."""
    return _validate("higgsfield", None)


def get_higgsfield_auth():
    """Return (api_key, api_secret) for HiggsField: the environment first, then what setup stored."""
    if os.environ.get("HF_API_KEY") and os.environ.get("HF_API_SECRET"):
        return os.environ["HF_API_KEY"], os.environ["HF_API_SECRET"]
    stored = _stored_secrets("higgsfield")
    if stored:
        return stored["api_key"], stored["api_secret"]
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

    status = {
        "vertex_ai": va,
        "wavespeed": ws,
        "higgsfield": hf,
        "image_generation": "ready" if img_providers else "not_configured",
        "image_providers": img_providers,
        "video_generation": "ready" if vid_providers else "not_configured",
        "video_providers": vid_providers,
        "credentials_dir": str(CRED_DIR),
        "keychain": "available" if _keyring() is not None else "not available (install_deps.py --groups keyring)",
    }
    warnings = _plaintext_warnings(_load_creds_checked()[0])
    if warnings:
        status["warnings"] = warnings
    return status


class NoSecret(Exception):
    """A secret was not supplied in any way the caller asked for."""


def _has_real_console() -> bool:
    """True only when a person can type at this process. On Windows `isatty()` is True for the NUL device and the Bash tool's
    stdin is an open pipe, so GetConsoleMode is the honest test: it succeeds only for a real console."""
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.windll.kernel32
            mode = wintypes.DWORD()
            return bool(kernel32.GetConsoleMode(kernel32.GetStdHandle(-10), ctypes.byref(mode)))
        except Exception:
            return False
    return sys.stdin.isatty()


def _read_secret(env_var, label, stdin_lines=None, prompt=False):
    """Resolve a secret WITHOUT ever blocking on a stream nobody is feeding. Returns (value, source).

    Precedence: a line from stdin, ONLY when --api-key-stdin was given (`stdin_lines` is then an iterator over its lines) > a
    hidden prompt, ONLY when --prompt was given AND a real console is attached > the environment variable. Anything else is
    NoSecret, so a missing key fails at once. Before 1.29.7 this read stdin whenever it was not a console: an agent running
    setup in a shell whose stdin is an open pipe waited forever, and the NUL device (isatty() True on Windows) blocked getpass.
    There is no command-line value (1.31.0): it leaks into shell history and the process table.
    """
    if stdin_lines is not None:
        line = next(stdin_lines, "").strip()
        if line:
            return line, "stdin"
        raise NoSecret(f"no {label}: --api-key-stdin was given but stdin held no line for it")
    if prompt:
        if not _has_real_console():
            raise NoSecret(f"no {label}: --prompt needs a real console (a terminal) and this process has none: "
                           f"set {env_var}, or use --api-key-stdin")
        secret = getpass.getpass(f"{label}: ").strip()
        if secret:
            return secret, "prompt"
    from_env = os.environ.get(env_var)
    if from_env:
        return from_env, "env"
    raise NoSecret(f"no {label}: set {env_var}, or use --api-key-stdin")


COMMAND_LINE_REFUSED = ("{flag} is not accepted: a key on the command line lands in shell history and the process "
                        "table. Set {env} in the environment (only its name is stored), or pipe the value with "
                        "--api-key-stdin.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SocialForge Credential Manager")
    sub = parser.add_subparsers(dest="action")
    va_p = sub.add_parser("setup-vertex", help="Configure Vertex AI")
    va_p.add_argument("--json-path", required=True, help="Path to GCP service account JSON")
    ws_p = sub.add_parser("setup-wavespeed", help="Configure WaveSpeed (reads WAVESPEED_API_KEY; only its name is stored)")
    ws_p.add_argument("--api-key", default=None, help="refused (exit 2): set WAVESPEED_API_KEY or use --api-key-stdin")
    ws_p.add_argument("--api-key-stdin", action="store_true",
                      help="read the key from the first line of stdin (never read implicitly); kept in the OS keychain")
    ws_p.add_argument("--prompt", action="store_true",
                      help="ask for the key at a hidden prompt (needs a real terminal); kept in the OS keychain")
    hf_p = sub.add_parser("setup-higgsfield",
                          help="Configure HiggsField (reads HF_API_KEY and HF_API_SECRET; only the names are stored)")
    hf_p.add_argument("--api-key", default=None, help="refused (exit 2): set HF_API_KEY or use --api-key-stdin")
    hf_p.add_argument("--api-secret", default=None, help="refused (exit 2): set HF_API_SECRET or use --api-key-stdin")
    hf_p.add_argument("--api-key-stdin", action="store_true",
                      help="read the key from the first line of stdin and the secret from the second (never read implicitly)")
    hf_p.add_argument("--prompt", action="store_true", help="ask for the key and secret at a hidden prompt (needs a real terminal)")
    sub.add_parser("status", help="Show credential status")
    sub.add_parser("validate", help="Validate all credentials")
    args = parser.parse_args()
    if args.action == "setup-vertex":
        result = setup_vertex_ai(args.json_path)
    elif args.action in ("setup-wavespeed", "setup-higgsfield"):
        key_env = "WAVESPEED_API_KEY" if args.action == "setup-wavespeed" else "HF_API_KEY"
        for flag, value, env in (("--api-key", args.api_key, key_env),
                                 ("--api-secret", getattr(args, "api_secret", None), "HF_API_SECRET")):
            if value is not None:   # refused before anything is read; the value itself is never echoed
                print(json.dumps({"status": "FAILED", "error": COMMAND_LINE_REFUSED.format(flag=flag, env=env)}, indent=2))
                sys.exit(2)
        stdin_lines = iter(sys.stdin.readline, "") if args.api_key_stdin else None   # explicit only; one line per secret
        try:
            if args.action == "setup-wavespeed":
                key, source = _read_secret("WAVESPEED_API_KEY", "key", stdin_lines, args.prompt)
                result = setup_wavespeed(key, from_env=source == "env")
            else:
                key, key_source = _read_secret("HF_API_KEY", "HiggsField API key", stdin_lines, args.prompt)
                secret, secret_source = _read_secret("HF_API_SECRET", "HiggsField API secret", stdin_lines, args.prompt)
                result = setup_higgsfield(key, secret, from_env=key_source == secret_source == "env")
        except NoSecret as exc:
            print(json.dumps({"status": "FAILED", "error": str(exc)}, indent=2))
            sys.exit(2)
    elif args.action == "status":
        result = get_status()
    elif args.action == "validate":
        result = {"vertex_ai": validate_vertex_ai(), "wavespeed": validate_wavespeed(), "higgsfield": validate_higgsfield()}
    else:
        parser.print_help()
        return
    warning = _common.python_floor_warning()
    if warning and isinstance(result, dict):
        result["python_warning"] = warning
    print(json.dumps(result, indent=2))
    if isinstance(result, dict) and result.get("error"):   # a setup that failed must not look like one that worked
        sys.exit(1)


if __name__ == "__main__":
    main()
