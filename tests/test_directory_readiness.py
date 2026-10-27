"""The Claude plugin directory's own checks, run on SocialForge's tree before the owner submits.

The directory validates a plugin when you press Validate in the developer portal and scans it again
on every new commit it picks up. `claude plugin validate --strict --profile directory` runs only a
subset of those checks, so this module covers the file-level rules from Anthropic's "Plugin
pre-submission checklist" (read 2026-10-27) that a local command cannot:

  * repository layout: no system files (`.DS_Store`, `Thumbs.db`, `desktop.ini`, `__MACOSX`), file
    names valid on Windows and macOS, no symbolic links or submodules, no `.gitattributes` that
    rewrites contents (`filter`, `export-ignore`, `export-subst`);
  * file limits that HOLD a version for a reviewer: at most 512 files; every file that is not an
    image or a font under 256 KiB; only text, complete PNG/JPEG/GIF/WebP images and fonts (an .ico,
    .pdf, .zip, executable or a base64 blob is held); every file under 5 MiB;
  * manifest and listing: name pattern, ASCII displayName, description, author, version, an `icon`
    that is a complete image inside the plugin, https `documentationUrl`, `supportUrl`,
    `privacyPolicyUrl`, `termsOfServiceUrl`; a README of at least 40 words outside code blocks and a
    LICENSE;
  * what the plugin runs: no package launcher (`npx`, `bunx`, `uvx`, `pipx run`, `uv run`,
    `pnpm dlx`, `yarn dlx`) in a manifest, hook or MCP file, no package-manager config
    (`.npmrc`, `bunfig.toml`, `uv.toml`) and no lockfile beside `package.json`;
  * no real credential and no path from the author's own machine in any file (a path like
    C:/Users/<name> was found in two base64 helper scripts that shipped from 1.5.0 to 1.29.8).

`tree_problems()` is one pure function over a folder and a list of paths, so each rule is also
exercised on a planted tree: a rule that cannot fail has not been tested. The real-tree test runs in
a git checkout only (an installed copy carries `__pycache__` and is not what the directory reads).
"""
from __future__ import annotations

import json
import re
import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

MAX_FILES = 512
MAX_TEXT_BYTES = 256 * 1024
MAX_ANY_BYTES = 5 * 1024 * 1024
IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
FONTS = {".ttf", ".otf", ".woff", ".woff2"}
SYSTEM_FILES = {".ds_store", "thumbs.db", "desktop.ini"}
DEVICE_NAME = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$", re.I)
BAD_NAME_CHARS = set(':<>"|?*\\')
LAUNCHER = re.compile(r"\b(npx|bunx|pnpm dlx|yarn dlx|uvx|pipx run|uv run)\b")
PM_CONFIG = {".npmrc", "bunfig.toml", "uv.toml"}
LOCKFILES = {"package-lock.json", "npm-shrinkwrap.json", "bun.lock", "bun.lockb"}
LISTING_URLS = ("documentationUrl", "supportUrl", "privacyPolicyUrl", "termsOfServiceUrl")
NAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
SECRETS = {
    "an OpenAI-style key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "a Google API key": re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    "a GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    "a Slack token": re.compile(r"xox[abp]-[A-Za-z0-9-]{10,}"),
    "an AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "a private key block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "a JWT": re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\."),
}
# C:/Users/<name> or C:\Users\<name>, except the placeholders docs use for "your own folder".
MACHINE_PATH = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+([A-Za-z0-9._-]+)")
PLACEHOLDER_USERS = {"you", "name", "user", "username", "yourname", "your-name", "me", "example", "public", "default"}
BASE64_BLOB = re.compile(r"^[A-Za-z0-9+/=\s]{200,}$")
STALE_COUNT = re.compile(r"\b\d+\s+tracked files\b", re.I)
UNPINNED_PIP = re.compile(r"\bpip install\s+(?!-)(?!\S+==)[A-Za-z]")
# History is allowed to quote old wording; the engineering spec is marked as a historical record.
PIP_EXEMPT = {"CHANGELOG.md", "SOCIALFORGE-COMPLETE-ENGINEERING-SPEC.md"}


def _complete_image(ext: str, data: bytes) -> bool:
    """A whole image, not a truncated download: signature plus its terminator."""
    if ext == ".png":
        return data[:8] == b"\x89PNG\r\n\x1a\n" and data[-12:] == b"\x00\x00\x00\x00IEND\xaeB`\x82"
    if ext in (".jpg", ".jpeg"):
        return data[:2] == b"\xff\xd8" and data[-2:] == b"\xff\xd9"
    if ext == ".gif":
        return data[:4] == b"GIF8" and data[-1:] == b";"
    if ext == ".webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP" and struct.unpack("<I", data[4:8])[0] + 8 == len(data)
    return False


def _front_matter_description(text: str):
    """The description value of a SKILL/command/agent file, or the sentinel strings 'NONE' / 'BAD'."""
    match = re.match(r"---\r?\n(.*?)\r?\n---", text, re.S)
    if not match:
        return "NONE"
    try:
        import yaml
        data = yaml.safe_load(match.group(1))
    except ImportError:  # no PyYAML: a plain `description:` line is enough for the layout rule
        line = re.search(r"^description:\s*(.+)$", match.group(1), re.M)
        return line.group(1) if line else "NONE"
    except Exception:
        return "BAD"
    if not isinstance(data, dict) or "description" not in data:
        return "NONE"
    return data["description"] if isinstance(data["description"], str) else "BAD"


def _looks_like_base64(text: str) -> bool:
    """One long run of base64 characters (wrapped at 64 or 76 columns at most), not prose or a word list."""
    if len(text) < 200 or not BASE64_BLOB.match(text):
        return False
    return sum(c.isspace() for c in text) / len(text) < 0.03


def tree_problems(root: Path, files: list[str]) -> list[str]:
    """Every way `files` (paths relative to `root`) would block, hold or embarrass a directory submission."""
    problems: list[str] = []
    names = set(files)
    if len(files) > MAX_FILES:
        problems.append(f"{len(files)} files: more than {MAX_FILES} holds the version for a reviewer")

    lowered: dict[str, str] = {}
    for rel in files:
        parts = rel.split("/")
        base = parts[-1]
        ext = Path(base).suffix.lower()
        if base.lower() in SYSTEM_FILES or "__MACOSX" in parts:
            problems.append(f"{rel}: a macOS or Windows system file blocks validation")
        for part in parts:
            if any(c in BAD_NAME_CHARS for c in part) or part.endswith((".", " ")) or DEVICE_NAME.match(part):
                problems.append(f"{rel}: '{part}' is not a valid name on both Windows and macOS")
        if rel.lower() in lowered and lowered[rel.lower()] != rel:
            problems.append(f"{rel} and {lowered[rel.lower()]} differ only by capitalization")
        lowered[rel.lower()] = rel
        if base in PM_CONFIG:
            problems.append(f"{rel}: a package-manager config sets a package source")
        if base in LOCKFILES and "package.json" in names:
            problems.append(f"{rel}: a lockfile beside package.json holds the version (the lockfile install is a reviewer choice)")

        try:
            data = (root / rel).read_bytes()
        except FileNotFoundError:  # a planted name list on a case-insensitive disk resolves one file for two names
            data = b""
        if len(data) > MAX_ANY_BYTES:
            problems.append(f"{rel}: {len(data)} bytes is over the 5 MiB file limit")
        if ext in IMAGES:
            if not _complete_image(ext, data):
                problems.append(f"{rel}: not a complete {ext[1:].upper()} image (truncated or the wrong format)")
            continue
        if ext in FONTS:
            continue
        if len(data) > MAX_TEXT_BYTES:
            problems.append(f"{rel}: {len(data)} bytes is over the 256 KiB limit for a file that is not an image or font")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            problems.append(f"{rel}: a binary file (only text, PNG/JPEG/GIF/WebP and fonts are accepted)")
            continue
        if "\x00" in text:
            problems.append(f"{rel}: a binary file (only text, PNG/JPEG/GIF/WebP and fonts are accepted)")
            continue
        if ext == ".b64" or _looks_like_base64(text):
            problems.append(f"{rel}: a base64 blob is code the scanner cannot read")
        for label, pattern in SECRETS.items():
            if pattern.search(text):
                problems.append(f"{rel}: contains what looks like {label}")
        for found in MACHINE_PATH.finditer(text):
            if found.group(1).lower() not in PLACEHOLDER_USERS:
                problems.append(f"{rel}: names a path on the author's own machine ({found.group(0)})")
        if rel not in PIP_EXEMPT and not rel.startswith("tests/") and UNPINNED_PIP.search(text):
            problems.append(f"{rel}: an unpinned `pip install` (print the pinned command from install_deps.py instead)")
        if rel in (".claude-plugin/plugin.json", "package.json", "hooks/hooks.json") or rel.startswith(".mcp.json"):
            hit = LAUNCHER.search(text)
            if hit:
                problems.append(f"{rel}: runs a package launcher ({hit.group(0)})")
        if re.match(r"(skills/[^/]+/SKILL|commands/[^/]+|agents/[^/]+)\.md$", rel):
            description = _front_matter_description(text)
            if description == "BAD":
                problems.append(f"{rel}: the front matter does not parse or its description is not a single text value")
            elif description == "NONE":
                problems.append(f"{rel}: no front matter description")

    if ".gitattributes" in names:
        attrs = (root / ".gitattributes").read_text(encoding="utf-8", errors="replace")
        if re.search(r"export-ignore|export-subst|\bfilter=", attrs):
            problems.append(".gitattributes: export-ignore, export-subst or filter stops validation")
    if ".gitmodules" in names:
        problems.append(".gitmodules: Git submodules are not accepted")

    readme = next((n for n in ("README.md", "readme.md", "README") if n in names), None)
    if readme is None:
        problems.append("README missing")
    else:
        prose = re.sub(r"```.*?```", "", (root / readme).read_text(encoding="utf-8"), flags=re.S)
        if len(prose.split()) < 40:
            problems.append(f"{readme}: fewer than 40 words outside code blocks")
    if "LICENSE" not in names and "LICENSE.md" not in names:
        problems.append("LICENSE missing")

    problems.extend(_manifest_problems(root, names))
    bundle = "docs/distribution/submission-bundle.md"
    if bundle in names:
        found = STALE_COUNT.search((root / bundle).read_text(encoding="utf-8"))
        if found:
            problems.append(f"{bundle}: states '{found.group(0)}', a count that goes stale on the next file")
    return problems


def _manifest_problems(root: Path, names: set[str]) -> list[str]:
    path = ".claude-plugin/plugin.json"
    if path not in names:
        return [f"{path} missing"]
    try:
        manifest = json.loads((root / path).read_text(encoding="utf-8-sig"))
    except ValueError as exc:
        return [f"{path}: not valid JSON ({exc})"]
    problems = []
    name = manifest.get("name", "")
    if not NAME_PATTERN.match(name):
        problems.append(f"{path}: name {name!r} must be lowercase letters, digits and hyphens, up to 64 characters")
    for field in ("displayName",):
        value = manifest.get(field, "")
        if not value or not value.isascii():
            problems.append(f"{path}: {field} must be present and in one writing system (ASCII here)")
    author = manifest.get("author")
    if not (isinstance(author, dict) and str(author.get("name", "")).isascii() and author.get("name")):
        problems.append(f"{path}: author.name missing or not ASCII")
    for field in ("description", "version"):
        if not manifest.get(field):
            problems.append(f"{path}: {field} missing")
    if not manifest.get("license") and "LICENSE" not in names:
        problems.append(f"{path}: no license field and no LICENSE file")
    if manifest.get("hooks") in ("./hooks/hooks.json", "hooks/hooks.json"):
        problems.append(f"{path}: hooks/hooks.json is loaded automatically; leave it out of the hooks field")
    for field in LISTING_URLS:
        if not str(manifest.get(field, "")).startswith("https://"):
            problems.append(f"{path}: {field} must be an https URL")
    icon = manifest.get("icon")
    if not isinstance(icon, str) or not icon.startswith("./") or ".." in icon.split("/"):
        problems.append(f"{path}: icon must be a ./ path inside the plugin")
    else:
        target = icon[2:]
        ext = Path(target).suffix.lower()
        if target not in names:
            problems.append(f"{path}: icon {icon} is not in the plugin")
        elif ext not in IMAGES or not _complete_image(ext, (root / target).read_bytes()):
            problems.append(f"{path}: icon {icon} is not a complete PNG, JPEG, GIF or WebP image")
    return problems


def git_files() -> list[str] | None:
    """Tracked files plus their modes, or None when this is not a checkout."""
    if not (REPO / ".git").exists():
        return None
    out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8").split("\0") if p]


def _png(width: int = 8) -> bytes:
    """A complete, valid PNG (one transparent pixel row), built here so no fixture file ships."""
    import zlib

    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, 1, 8, 6, 0, 0, 0)
    pixels = zlib.compress(b"\x00" + b"\x00\x00\x00\x00" * width)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", pixels) + chunk(b"IEND", b"")


GOOD_MANIFEST = {
    "name": "demo-plugin", "displayName": "Demo Plugin", "version": "1.0.0", "description": "A demo.",
    "author": {"name": "Jane Doe"}, "license": "MIT", "icon": "./assets/icon.png",
    "documentationUrl": "https://example.com/docs", "supportUrl": "https://example.com/support",
    "privacyPolicyUrl": "https://example.com/privacy", "termsOfServiceUrl": "https://example.com/terms",
}
GOOD_README = "Demo plugin. " + "It plans a month of posts and checks each one before it ships. " * 6


class PlantedTree(unittest.TestCase):
    """Each rule fails on a tree built to break it, and the unbroken tree passes."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dirready-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.put(".claude-plugin/plugin.json", json.dumps(GOOD_MANIFEST))
        self.put("assets/icon.png", _png())
        self.put("README.md", GOOD_README)
        self.put("LICENSE", "MIT License")
        self.put("skills/demo/SKILL.md", "---\nname: demo\ndescription: Does a demo.\n---\nBody.\n")

    def put(self, rel: str, content) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))

    def problems(self) -> list[str]:
        files = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file())
        return tree_problems(self.root, files)

    def assertFlags(self, fragment: str) -> None:
        found = self.problems()
        self.assertTrue(any(fragment in p for p in found), f"expected a problem containing {fragment!r}, got {found}")

    def test_the_unbroken_tree_passes(self):
        self.assertEqual(self.problems(), [])

    def test_system_files_block(self):
        self.put("docs/.DS_Store", "x")
        self.assertFlags("system file")

    def test_windows_and_mac_invalid_names(self):
        self.put("docs/con.md", "x")
        self.assertFlags("not a valid name")

    def test_case_collisions(self):
        # Two names for one folder entry cannot both exist on this disk, so plant the name list itself.
        self.put("docs/Guide.md", "a")
        found = tree_problems(self.root, ["README.md", "LICENSE", "docs/Guide.md", "docs/guide.md"])
        self.assertTrue(any("differ only by capitalization" in p for p in found), found)

    def test_more_than_512_files_is_held(self):
        for n in range(520):
            self.put(f"refs/r{n}.md", "x")
        self.assertFlags("more than 512")

    def test_a_large_text_file_is_held(self):
        self.put("docs/big.md", "a " * 140_000)
        self.assertFlags("256 KiB")

    def test_a_binary_file_is_held(self):
        self.put("assets/favicon.ico", b"\x00\x00\x01\x00\x01\x00\x10\x10\xff\xfe")
        self.assertFlags("binary file")

    def test_a_truncated_image_is_held(self):
        self.put("docs/shot.png", _png()[:-20])
        self.assertFlags("not a complete PNG")

    def test_a_base64_blob_is_held(self):
        self.put(".tmp/script.b64", "QWxsIHlvdXIgYmFzZQ" * 40)
        self.assertFlags("base64 blob")

    def test_a_base64_blob_under_an_innocent_name_is_held(self):
        self.put("scripts/helper.txt", "aW1wb3J0IG9z" * 40)
        self.assertFlags("base64 blob")

    def test_a_credential_is_blocked(self):
        self.put("docs/setup.md", "key = " + "sk-" + "a1B2c3D4e5" * 4)
        self.assertFlags("OpenAI-style key")

    def test_a_private_key_is_blocked(self):
        self.put("docs/key.md", "-----BEGIN " + "RSA PRIVATE KEY-----")
        self.assertFlags("private key")

    def test_the_authors_own_machine_path_is_flagged(self):
        self.put("scripts/old.py", "path = 'C:/Users/" + "jdoe/Downloads/plugin/README.md'")
        self.assertFlags("author's own machine")

    def test_a_placeholder_user_path_is_fine(self):
        self.put("docs/win.md", "Open C:\\Users\\" + "you\\Downloads and look.")
        self.assertEqual(self.problems(), [])

    def test_an_unpinned_pip_install_is_flagged(self):
        self.put("docs/setup.md", "Run `pip " + "install playwright` first.")
        self.assertFlags("unpinned `pip install`")

    def test_a_pinned_pip_install_is_fine(self):
        self.put("docs/setup.md", "Run `pip " + "install playwright==1.52.0` first.")
        self.assertEqual(self.problems(), [])

    def test_a_launcher_in_a_manifest_or_mcp_file_is_flagged(self):
        self.put(".mcp.json.example", '{"mcpServers": {"x": {"command": "' + "np" + 'x", "args": ["-y", "some-pkg"]}}}')
        self.assertFlags("package launcher")

    def test_a_package_manager_config_is_flagged(self):
        self.put(".npmrc", "registry=https://example.com/")
        self.assertFlags("package source")

    def test_a_lockfile_beside_package_json_is_flagged(self):
        self.put("package.json", "{}")
        self.put("package-lock.json", "{}")
        self.assertFlags("lockfile")

    def test_gitattributes_that_rewrite_contents(self):
        self.put(".gitattributes", "*.md export-ignore\n")
        self.assertFlags(".gitattributes")

    def test_a_short_readme_blocks(self):
        self.put("README.md", "Too short.\n```\n" + "code " * 100 + "\n```\n")
        self.assertFlags("fewer than 40 words")

    def test_a_missing_license_blocks(self):
        (self.root / "LICENSE").unlink()
        manifest = dict(GOOD_MANIFEST)
        del manifest["license"]
        self.put(".claude-plugin/plugin.json", json.dumps(manifest))
        self.assertFlags("LICENSE")

    def test_manifest_rules(self):
        cases = {
            "name": ("Demo Plugin", "must be lowercase"),
            "displayName": ("D\u0435mo", "one writing system"),   # Cyrillic e
            "documentationUrl": ("http://example.com", "https URL"),
            "privacyPolicyUrl": ("", "https URL"),
            "icon": ("../outside.png", "inside the plugin"),
        }
        for field, (bad, fragment) in cases.items():
            with self.subTest(field=field):
                manifest = dict(GOOD_MANIFEST)
                manifest[field] = bad
                self.put(".claude-plugin/plugin.json", json.dumps(manifest))
                self.assertFlags(fragment)

    def test_a_missing_or_wrong_icon(self):
        (self.root / "assets" / "icon.png").unlink()
        self.assertFlags("is not in the plugin")
        self.put("assets/icon.png", b"GIF89a not really a png")
        self.assertFlags("not a complete PNG")

    def test_front_matter_description_must_be_text(self):
        self.put("skills/demo/SKILL.md", "---\nname: demo\ndescription:\n  - one\n  - two\n---\nBody.\n")
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML not installed: the list-valued description is only detectable with it")
        self.assertFlags("single text value")

    def test_the_bundle_does_not_pin_a_file_count(self):
        self.put("docs/distribution/submission-bundle.md", "Ready (182 tracked files).")
        self.assertFlags("count that goes stale")


class RealTree(unittest.TestCase):
    def test_socialforge_passes_the_directory_file_checks(self):
        files = git_files()
        if files is None:
            self.skipTest("not a git checkout: an installed copy carries __pycache__ and is not what the directory reads")
        found = tree_problems(REPO, files)
        self.assertEqual(found, [], "\n" + "\n".join(found))

    def test_the_index_has_no_symlinks_or_submodules(self):
        if git_files() is None:
            self.skipTest("not a git checkout")
        out = subprocess.run(["git", "ls-files", "-s"], cwd=REPO, capture_output=True, text=True, encoding="utf-8", check=True).stdout
        odd = [line for line in out.splitlines() if line.startswith(("120000", "160000"))]
        self.assertEqual(odd, [])


if __name__ == "__main__":
    unittest.main()
