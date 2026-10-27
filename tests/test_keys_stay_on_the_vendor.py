"""1.30.2: an API key never follows a redirect off the vendor it was sent to.

urllib's redirect handler builds the follow-up request from the first one's ordinary headers (everything except Content-Length and
Content-Type), so a key set with `Request(url, headers=...)` or `req.add_header(...)` is sent, as it stands, to whatever host a 30x
answer names. `add_unredirected_header` keeps a header on the first request only. Three kinds of test keep it that way:

  * a stub-redirect run: the script's own code asks a vendor host for a model list, the stub answers 302 to another host, and that
    host is shown every header it receives. No network, no real key. The harness is checked first with a request that sets the key
    the old way, because a test of a leak that cannot see a leak proves nothing. This covers refresh_models.py and the model
    router's three list calls (scripts/model_router.py is copied from Digital Marketing Pro and keeps its fix there).
  * a static guard over every shipped Python file: a urllib Request that carries a credential header, or an `add_header` call that
    names one (or whose header name cannot be read from the source), is a failure. Planted cases show the guard fires.
  * the two Higgsfield calls (generate_video.py, generate_image.py) and the WaveSpeed SDK use `requests`, not urllib. `requests`
    drops `Authorization` when a redirect names another host, so a key sent that way is safe; a test shows it with the installed
    version, and shows that it would NOT drop a custom key header, which is why those calls must keep to `Authorization`.
  * the google-genai client. Its own httpx client follows redirects (`SyncHttpxClient` sets follow_redirects=True) and httpx drops
    only `Authorization`, while an API key travels as `x-goog-api-key`. Every client built with an API key therefore takes
    `_common.genai_http_options()` (no redirects); tests show the SDK default leaks, the option does not, and a Vertex AI client
    (an OAuth `Authorization` header) leaks nothing either way.
"""
from __future__ import annotations

import ast
import email.message
import io
import json
import os
import re
import sys
import tempfile
import unittest
import urllib.parse
import urllib.request
import urllib.response
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import model_router  # noqa: E402
import refresh_models  # noqa: E402

SKIP_PARTS = {".git", "__pycache__", "node_modules", "tests", "results", "dist"}
ELSEWHERE = "elsewhere.example"

# ---------------------------------------------------------------------------------------------------------------------------
# The static guard
# ---------------------------------------------------------------------------------------------------------------------------

# Authorization, Proxy-Authorization and Cookie, anything ending in -key / -token / -secret (x-api-key, x-goog-api-key, api-key,
# xi-api-key, api-subscription-key ...), or a bare key / token / secret.
CREDENTIAL_NAME = re.compile(r"(?i)^(authorization|proxy-authorization|cookie)$|[-_](key|token|secret)$|^(api)?(key|token|secret)$")
CREDENTIAL_SCHEME = re.compile(r"(?i)^\s*(bearer|basic|key|token)\s")


def leading_text(node) -> str:
    """The literal text a string expression starts with ('Bearer ' for 'Bearer ' + key and for f'Bearer {key}'), else ''."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr) and node.values:
        return leading_text(node.values[0])
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        return leading_text(node.left)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        return leading_text(node.func.value)
    return ""


def is_credential(name_node, value_node) -> bool:
    if isinstance(name_node, ast.Constant) and isinstance(name_node.value, str) and CREDENTIAL_NAME.search(name_node.value):
        return True
    return bool(CREDENTIAL_SCHEME.match(leading_text(value_node)))


def callee(node: ast.Call) -> str:
    f = node.func
    return f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""


def credential_leaks(source: str, where: str = "<source>") -> list[str]:
    """One line per place a credential header would be copied to a redirect target."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        name = callee(node)
        if name == "add_header":
            head = node.args[0] if node.args else None
            tail = node.args[1] if len(node.args) > 1 else None
            if head is None or not (isinstance(head, ast.Constant) and isinstance(head.value, str)):
                found.append(f"{where}:{node.lineno}: add_header with a header name that cannot be read from the source")
            elif is_credential(head, tail):
                found.append(f"{where}:{node.lineno}: add_header sets {head.value!r}; use add_unredirected_header")
        elif name == "Request":
            headers = next((k.value for k in node.keywords if k.arg == "headers"), node.args[2] if len(node.args) > 2 else None)
            if headers is None or (isinstance(headers, ast.Constant) and headers.value is None):
                continue
            if not isinstance(headers, ast.Dict):
                found.append(f"{where}:{node.lineno}: Request(headers=...) is built elsewhere; add each header with add_unredirected_header")
                continue
            for key, value in zip(headers.keys, headers.values):
                if key is None or not isinstance(key, ast.Constant):
                    found.append(f"{where}:{node.lineno}: Request(headers=...) has a header name that cannot be read from the source")
                elif is_credential(key, value):
                    found.append(f"{where}:{node.lineno}: Request(headers=...) carries {key.value!r}; use add_unredirected_header")
    return found


def shipped_python() -> list[Path]:
    return sorted(p for p in REPO.rglob("*.py") if p.is_file() and not (set(p.relative_to(REPO).parts) & SKIP_PARTS))


class TestStaticGuard(unittest.TestCase):

    def test_no_shipped_script_copies_a_credential_header_to_a_redirect(self):
        found = []
        for path in shipped_python():
            found += credential_leaks(path.read_text(encoding="utf-8-sig"), str(path.relative_to(REPO)))
        self.assertEqual(found, [], "\n  " + "\n  ".join(found))

    def test_the_scan_reads_the_scripts_that_send_keys(self):
        names = {p.name for p in shipped_python()}
        for script in ("refresh_models.py", "model_router.py", "generate_video.py", "generate_image.py"):
            self.assertIn(script, names)

    def test_plants(self):
        planted = {
            "add_header, the usual way": 'req = urllib.request.Request(u)\nreq.add_header("Authorization", "Bearer " + key)\n',
            "add_header, the x-api-key header": 'req.add_header("x-api-key", key)\n',
            "add_header, the Gemini header": 'req.add_header("X-Goog-Api-Key", key)\n',
            "add_header, a header name in a variable": "for k, v in headers.items():\n    req.add_header(k, v)\n",
            "add_header, a Bearer value under any name": 'req.add_header("X-Auth", f"Bearer {key}")\n',
            "add_header, a Key value under any name": 'req.add_header("X-Auth", f"Key {key}:{secret}")\n',
            "Request headers literal": 'urllib.request.Request(u, headers={"xi-api-key": key})\n',
            "Request headers literal, Sarvam": 'urllib.request.Request(u, data=b, headers={"api-subscription-key": key})\n',
            "Request headers literal, Bearer value": 'Request(u, headers={"X-Auth": "Bearer " + key})\n',
            "Request headers positional": 'Request(u, None, {"Authorization": token})\n',
            "Request headers from a variable": "urllib.request.Request(u, headers=hdr)\n",
            "Request headers unpacked": "urllib.request.Request(u, headers={**base, 'a': 'b'})\n",
        }
        for label, source in planted.items():
            self.assertTrue(credential_leaks(source), label)

    def test_what_is_allowed_stays_allowed(self):
        fine = (
            'req = urllib.request.Request(u)\nreq.add_unredirected_header("Authorization", "Bearer " + key)\n',
            'req.add_unredirected_header("x-api-key", key)\n',
            'for k, v in headers.items():\n    req.add_unredirected_header(k, v)\n',
            'urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "text/html"})\n',
            'urllib.request.Request(u, data=b, headers={"Content-Type": ct})\n',
            'urllib.request.Request(u, headers={})\n',
            'urllib.request.Request(u, method="GET")\nreq.add_header("Accept", "application/json")\n',
        )
        for source in fine:
            self.assertEqual(credential_leaks(source), [], source)


# ---------------------------------------------------------------------------------------------------------------------------
# The stub redirect (urllib)
# ---------------------------------------------------------------------------------------------------------------------------

A_KEY = "ant-test-0000-not-a-real-anthropic-key"
O_KEY = "oai-test-0000-not-a-real-openai-key"
G_KEY = "g-test-0000-not-a-real-google-key"
ENV = {"ANTHROPIC_API_KEY": A_KEY, "OPENAI_API_KEY": O_KEY, "GEMINI_API_KEY": G_KEY}
LIST = json.dumps({"data": [], "has_more": False, "models": []}).encode()


def answer(url: str, code: int, msg: str, headers: dict, payload: bytes) -> urllib.response.addinfourl:
    head = email.message.Message()
    for name, value in headers.items():
        head[name] = value
    response = urllib.response.addinfourl(io.BytesIO(payload), head, url, code)
    response.msg = msg
    return response


class RedirectingHost(urllib.request.BaseHandler):
    """Stands in for the network: every host except ELSEWHERE answers 302 to ELSEWHERE, and ELSEWHERE answers an empty list.
    It records the headers each host was shown, which is all a redirect target could ever read."""

    handler_order = 100          # ahead of the real HTTPSHandler

    def __init__(self):
        self.shown = []          # (host, [(header, value), ...]) in the order the requests arrived

    def https_open(self, req):
        host = urllib.parse.urlsplit(req.full_url).netloc
        self.shown.append((host, list(req.header_items())))
        if host != ELSEWHERE:
            return answer(req.full_url, 302, "Found", {"Location": f"https://{ELSEWHERE}/leak"}, b"")
        return answer(req.full_url, 200, "OK", {"Content-Type": "application/json"}, LIST)

    def vendor_headers(self) -> dict:
        return {k.lower(): v for host, items in self.shown if host != ELSEWHERE for k, v in items}

    def seen_by_elsewhere(self) -> str:
        return " ".join(f"{k}: {v}" for host, items in self.shown if host == ELSEWHERE for k, v in items)

    def reached_elsewhere(self) -> bool:
        return any(host == ELSEWHERE for host, _ in self.shown)


def through(handler: RedirectingHost, fn, env: dict | None = None):
    """Run fn with urllib's own opener chain (redirect handler included) and the stub as the network."""
    opener = urllib.request.build_opener(handler)
    with mock.patch.dict(os.environ, ENV if env is None else env), mock.patch.object(urllib.request, "_opener", opener):
        return fn()


class KeyStaysWithTheVendor:
    """Mixin: check(fn, key, header_name) runs fn through the stub and asserts the key reached the vendor and no one else."""

    def check(self, fn, key, header_name):
        handler = RedirectingHost()
        through(handler, fn)
        sent = handler.vendor_headers()
        self.assertIn(header_name.lower(), sent, "the vendor must still receive the key")
        self.assertIn(key, sent[header_name.lower()])
        self.assertTrue(handler.reached_elsewhere(), "the stub did not follow its own redirect")
        leaked = handler.seen_by_elsewhere()
        self.assertNotIn(key, leaked)
        self.assertNotIn(header_name.lower(), leaked.lower())
        return handler


class TestTheStubSeesALeak(unittest.TestCase):

    def test_the_stub_sees_a_key_set_the_old_way(self):
        """Plant: the old code, `Request(..., headers=)`, leaks. If this passes the stub can see a leak; if it fails the tests below prove nothing."""
        def old_way():
            req = urllib.request.Request("https://api.vendor.example/v1/models", headers={"x-api-key": A_KEY})
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.read()
        handler = RedirectingHost()
        through(handler, old_way)
        self.assertTrue(handler.reached_elsewhere(), "the stub did not follow its own redirect")
        self.assertIn(A_KEY, handler.seen_by_elsewhere())

    def test_the_stub_sees_a_key_set_with_add_header(self):
        def old_way():
            req = urllib.request.Request("https://api.vendor.example/v1/models", method="GET")
            req.add_header("Authorization", f"Bearer {O_KEY}")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.read()
        handler = RedirectingHost()
        through(handler, old_way)
        self.assertIn(O_KEY, handler.seen_by_elsewhere())


class TestRefreshModels(KeyStaysWithTheVendor, unittest.TestCase):

    def test_anthropic_key_stays_with_anthropic(self):
        self.check(refresh_models.list_anthropic, A_KEY, "x-api-key")

    def test_openai_key_stays_with_openai(self):
        self.check(refresh_models.list_openai, O_KEY, "Authorization")

    def test_gemini_key_stays_with_google(self):
        self.check(refresh_models.list_gemini, G_KEY, "x-goog-api-key")

    def test_no_header_the_vendor_was_sent_reaches_the_redirect_target(self):
        handler = RedirectingHost()
        through(handler, refresh_models.list_anthropic)
        self.assertNotIn("anthropic-version", handler.seen_by_elsewhere().lower())


class TestTheModelRouter(KeyStaysWithTheVendor, unittest.TestCase):
    """scripts/model_router.py is Digital Marketing Pro's, copied byte for byte; its three list calls must keep the key off a redirect."""

    def test_anthropic_key_stays_with_anthropic(self):
        self.check(lambda: model_router.fetch_anthropic(A_KEY, "2023-06-01"), A_KEY, "x-api-key")

    def test_openai_key_stays_with_openai(self):
        self.check(lambda: model_router.fetch_openai(O_KEY), O_KEY, "Authorization")

    def test_gemini_key_stays_with_google(self):
        self.check(lambda: model_router.fetch_google(G_KEY), G_KEY, "x-goog-api-key")


# ---------------------------------------------------------------------------------------------------------------------------
# The two Higgsfield calls (requests)
# ---------------------------------------------------------------------------------------------------------------------------

try:
    import requests
    import requests.adapters
except ImportError:           # a bare interpreter: the Higgsfield rungs then record "dependency-missing" and send nothing
    requests = None

HF_KEY, HF_SECRET = "hf-key-test-0000", "hf-secret-test-0000"
# One body both vendors can read: Higgsfield reads request_id and status, WaveSpeed reads data.id and data.status.
HF_BODY = json.dumps({"request_id": "req-1", "status": "failed", "data": {"id": "req-1", "status": "completed", "outputs": []}}).encode()


class FakeNetwork:
    """Replaces requests' adapter: the vendor host answers 302 to ELSEWHERE, ELSEWHERE answers a failed job."""

    def __init__(self):
        self.shown = []          # (host, {header: value})

    def send(self, adapter, request, **kwargs):
        host = urllib.parse.urlsplit(request.url).netloc
        self.shown.append((host, dict(request.headers)))
        resp = requests.Response()
        resp.request, resp.url, resp.raw = request, request.url, io.BytesIO(b"")
        if host != ELSEWHERE:
            resp.status_code = 302
            resp.headers["Location"] = f"https://{ELSEWHERE}/leak"
        else:
            resp.status_code = 200
            resp.headers["Content-Type"] = "application/json"
            resp._content = HF_BODY
        return resp

    def elsewhere(self) -> str:
        return " ".join(f"{k}: {v}" for host, headers in self.shown if host == ELSEWHERE for k, v in headers.items())

    def vendor(self) -> dict:
        return {k.lower(): v for host, headers in self.shown if host != ELSEWHERE for k, v in headers.items()}


@unittest.skipIf(requests is None, "requests is not installed")
class TestHiggsfieldKeepsItsKeyOffARedirect(unittest.TestCase):

    def run_with_stub(self, fn):
        net = FakeNetwork()
        with mock.patch.object(requests.adapters.HTTPAdapter, "send", lambda adapter, request, **kw: net.send(adapter, request, **kw)), \
                mock.patch("time.sleep", lambda s: None):
            fn()
        return net

    def test_the_stub_sees_a_custom_key_header_follow_a_redirect(self):
        """Plant: requests drops Authorization on a new host, not x-api-key. The Higgsfield calls therefore must keep to Authorization."""
        net = self.run_with_stub(lambda: requests.post("https://platform.vendor.example/x", headers={"x-api-key": HF_KEY}, json={}, timeout=5))
        self.assertIn(HF_KEY, net.elsewhere())

    def check(self, call):
        net = self.run_with_stub(call)
        self.assertIn(f"Key {HF_KEY}:{HF_SECRET}", net.vendor().get("authorization", ""), "the vendor must still receive the key")
        self.assertTrue(any(host == ELSEWHERE for host, _ in net.shown), "the stub did not follow its own redirect")
        self.assertNotIn(HF_KEY, net.elsewhere())
        self.assertNotIn("authorization", net.elsewhere().lower())

    def test_video_generation_and_polling(self):
        import generate_video
        with mock.patch("credential_manager.get_higgsfield_auth", return_value=(HF_KEY, HF_SECRET)), \
                mock.patch.object(generate_video, "_resolve_execution_model", lambda *a, **k: "vendor/model"):
            self.check(lambda: generate_video.generate_video_higgsfield("a prompt", os.path.join(tempfile.gettempdir(), "sf-keys.mp4"), attempts=[]))

    def test_image_generation_and_polling(self):
        import generate_image
        with mock.patch("credential_manager.get_higgsfield_auth", return_value=(HF_KEY, HF_SECRET)), \
                mock.patch.object(generate_image, "_resolve_execution_model", lambda *a, **k: "vendor/model"):
            self.check(lambda: generate_image.generate_image_higgsfield("a prompt", os.path.join(tempfile.gettempdir(), "sf-keys.png"), attempts=[]))

    def test_the_two_calls_send_the_key_only_as_authorization(self):
        """requests keeps any other credential header across a redirect, so a call that added one would leak it."""
        for name in ("generate_video.py", "generate_image.py"):
            source = (SCRIPTS_DIR / name).read_text(encoding="utf-8-sig")
            for header in re.findall(r"headers = \{([^}]*)\}", source):
                names = re.findall(r"""["']([A-Za-z][\w-]*)["']\s*:""", header)
                self.assertTrue([n for n in names if CREDENTIAL_NAME.search(n)] in ([], ["Authorization"]), (name, names))


@unittest.skipIf(requests is None, "requests is not installed")
class TestWaveSpeedSdkKeepsItsKeyOffARedirect(unittest.TestCase):
    """The WaveSpeed SDK (pinned in install_deps.py) posts and polls with `requests` and sends only `Authorization: Bearer`."""

    def test_submit_and_poll(self):
        try:
            import wavespeed
        except ImportError:
            self.skipTest("wavespeed is not installed")
        net = FakeNetwork()
        client = wavespeed.Client(api_key=HF_KEY)
        with mock.patch.object(requests.adapters.HTTPAdapter, "send", lambda adapter, request, **kw: net.send(adapter, request, **kw)):
            client._submit("vendor/model", {"prompt": "p"})
            client._get_result("req-1")
        self.assertIn(f"Bearer {HF_KEY}", net.vendor().get("authorization", ""), "the vendor must still receive the key")
        self.assertTrue(any(host == ELSEWHERE for host, _ in net.shown), "the stub did not follow its own redirect")
        self.assertNotIn(HF_KEY, net.elsewhere())
        self.assertNotIn("authorization", net.elsewhere().lower())


# ---------------------------------------------------------------------------------------------------------------------------
# The google-genai client
# ---------------------------------------------------------------------------------------------------------------------------

try:
    import httpx
    from google import genai
    from google.genai import types as genai_types
except ImportError:           # a bare interpreter: the image and vision rungs then report "dependency-missing" and send nothing
    httpx = genai = genai_types = None

GENAI_KEY = "genai-test-0000-not-a-real-key"
GENAI_TOKEN = "ya29.test-0000-not-a-real-token"


def genai_network():
    """An httpx transport that answers the vendor with 302 to ELSEWHERE and ELSEWHERE with a model, recording what each host sees."""
    seen = []

    def handler(request):
        seen.append((request.url.host, {k.lower(): v for k, v in request.headers.items()}))
        if request.url.host != ELSEWHERE:
            return httpx.Response(302, headers={"Location": f"https://{ELSEWHERE}/leak"})
        return httpx.Response(200, json={"name": "models/gemini-test", "displayName": "t"})

    return seen, httpx.MockTransport(handler)


def left_the_vendor(seen) -> str:
    return " ".join(f"{k}: {v}" for host, headers in seen if host == ELSEWHERE for k, v in headers.items())


def get_model(client):
    try:
        client.models.get(model="gemini-test")
    except Exception:             # a refused redirect surfaces as an API error; what matters is who was asked
        pass


@unittest.skipIf(genai is None, "google-genai is not installed")
class TestGenaiClientKeepsItsKeyOffARedirect(unittest.TestCase):

    def test_the_sdk_default_follows_a_redirect_and_takes_the_key_along(self):
        """Plant: a client built the plain way leaks. If this passes, the stub can see a leak; if it fails, the tests below prove nothing."""
        seen, transport = genai_network()
        client = genai.Client(api_key=GENAI_KEY, http_options=genai_types.HttpOptions(client_args={"transport": transport}))
        get_model(client)
        self.assertIn(GENAI_KEY, left_the_vendor(seen))

    def test_the_option_keeps_the_key_on_the_vendor(self):
        import _common
        seen, transport = genai_network()
        options = _common.genai_http_options()
        options.client_args = {**options.client_args, "transport": transport}
        get_model(genai.Client(api_key=GENAI_KEY, http_options=options))
        vendor = [headers for host, headers in seen if host != ELSEWHERE]
        self.assertEqual(len(vendor), 1, "the vendor must be asked exactly once")
        self.assertEqual(vendor[0].get("x-goog-api-key"), GENAI_KEY)
        self.assertFalse([host for host, _ in seen if host == ELSEWHERE], "the client followed the redirect")

    def test_the_option_turns_off_redirects_on_the_sdk_client(self):
        import _common
        client = genai.Client(api_key=GENAI_KEY, http_options=_common.genai_http_options())
        self.assertFalse(client._api_client._httpx_client.follow_redirects)

    def test_a_vertex_client_sends_only_an_oauth_header_that_httpx_drops(self):
        """Vertex AI uses `Authorization: Bearer <token>`; httpx drops that header on a hop to another origin, so it needs no option."""
        from google.oauth2.credentials import Credentials
        seen, transport = genai_network()
        client = genai.Client(vertexai=True, project="p", location="us-central1", credentials=Credentials(token=GENAI_TOKEN),
                              http_options=genai_types.HttpOptions(client_args={"transport": transport}))
        get_model(client)
        vendor = [headers for host, headers in seen if host != ELSEWHERE]
        self.assertTrue(vendor and GENAI_TOKEN in vendor[0].get("authorization", ""), "the vendor must still receive the token")
        self.assertTrue(any(host == ELSEWHERE for host, _ in seen), "the stub did not follow its own redirect")
        self.assertNotIn(GENAI_TOKEN, left_the_vendor(seen))
        self.assertNotIn("authorization", left_the_vendor(seen))


def api_key_clients_without_the_option(source: str, where: str = "<source>") -> list[str]:
    """genai.Client(api_key=...) calls that do not pass http_options=."""
    out = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and callee(node) == "Client":
            names = {k.arg for k in node.keywords}
            if "api_key" in names and "http_options" not in names:
                out.append(f"{where}:{node.lineno}: Client(api_key=...) without http_options=_common.genai_http_options()")
    return out


class TestEveryApiKeyClientHasTheOption(unittest.TestCase):

    def test_no_shipped_script_builds_an_api_key_client_that_follows_redirects(self):
        found = []
        for path in shipped_python():
            found += api_key_clients_without_the_option(path.read_text(encoding="utf-8-sig"), str(path.relative_to(REPO)))
        self.assertEqual(found, [], "\n  " + "\n  ".join(found))

    def test_the_four_scripts_that_build_one_take_the_option(self):
        for name in ("credential_manager.py", "edit_image.py", "generate_image.py", "index_assets.py"):
            source = (SCRIPTS_DIR / name).read_text(encoding="utf-8-sig")
            self.assertTrue("genai_http_options()" in source, f"{name} does not take _common.genai_http_options()")

    def test_plants(self):
        self.assertTrue(api_key_clients_without_the_option("client = genai.Client(api_key=key)\n"))
        self.assertTrue(api_key_clients_without_the_option("return genai.Client(api_key=os.environ['K'], vertexai=False), 'x'\n"))
        self.assertEqual(api_key_clients_without_the_option("genai.Client(api_key=key, http_options=_common.genai_http_options())\n"), [])
        self.assertEqual(api_key_clients_without_the_option("genai.Client(vertexai=True, project=p, location=l)\n"), [])


if __name__ == "__main__":
    unittest.main()
