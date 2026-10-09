#!/usr/bin/env python3
"""
install_deps.py - check SocialForge's Python dependencies, and install them only when you ask.

Nothing is installed behind your back. Run with no flags (or --check) to see what is present and
the exact pinned commands for what is missing; run with --install to let this script execute those
commands. Every package has an exact version in PINNED (the versions the scripts were tested
against), so a new package release reaches you only when this table changes on purpose.

    python scripts/install_deps.py                       # report + print the pinned commands
    python scripts/install_deps.py --groups image video  # limit the report to some groups
    python scripts/install_deps.py --install             # YOU choose to run those commands

Default groups: core (Pillow), image (google-genai), video (wavespeed, imageio-ffmpeg),
carousel (playwright, plus the Chromium browser, a large download).
Extra groups, named explicitly only: higgsfield (higgsfield-client), background-removal (rembg,
which fetches model weights on first use), c2pa (c2pa-python, cryptography).

Generation scripts that find a package missing mid-run call ensure_package(): it prints the pinned
command and returns False. Setting SOCIALFORGE_INSTALL_DEPS=1 for that run is the explicit consent
that lets it run the command instead.
"""

import json
import os
import subprocess
import sys

# Exact versions the scripts were tested against. Change a pin only together with a test run.
PINNED = {
    "Pillow": "12.3.0",
    "google-genai": "1.70.0",
    "wavespeed": "1.0.11",
    "imageio-ffmpeg": "0.6.0",
    "playwright": "1.52.0",
    "higgsfield-client": "0.1.0",
    "rembg": "2.0.77",
    "c2pa-python": "0.38.0",
    "cryptography": "46.0.6",
}

IMPORT_NAMES = {
    "Pillow": "PIL",
    "google-genai": "google.genai",
    "wavespeed": "wavespeed",
    "imageio-ffmpeg": "imageio_ffmpeg",
    "playwright": "playwright",
    "higgsfield-client": "higgsfield_client",
    "rembg": "rembg",
    "c2pa-python": "c2pa",
    "cryptography": "cryptography",
}

REQUIRED = {
    "core": ["Pillow"],
    "image": ["google-genai"],
    "video": ["wavespeed", "imageio-ffmpeg"],
    "carousel": ["playwright"],
}
EXTRA = {
    "higgsfield": ["higgsfield-client"],
    "background-removal": ["rembg"],
    "c2pa": ["c2pa-python", "cryptography"],
}
ALL_GROUPS = {**REQUIRED, **EXTRA}
DEFAULT_GROUPS = list(REQUIRED)

OPT_IN_ENV = "SOCIALFORGE_INSTALL_DEPS"


def pin(package_name):
    """`name==x.y.z` for a known package; ValueError for one without a pin."""
    if package_name not in PINNED:
        raise ValueError(f"no pinned version for {package_name!r}; add it to PINNED")
    return f"{package_name}=={PINNED[package_name]}"


def _exe():
    exe = sys.executable
    return f'"{exe}"' if " " in exe else exe


def install_command(packages):
    """The exact pinned pip command for `packages`."""
    return f"{_exe()} -m pip install {' '.join(pin(p) for p in packages)}"


def browser_command():
    return f"{_exe()} -m playwright install chromium"


def check_package(package_name):
    import_name = IMPORT_NAMES.get(package_name, package_name.replace("-", "_"))
    try:
        __import__(import_name.split(".")[0])
        return True
    except ImportError:
        return False


def install_package(package_name):
    """Run the pinned pip install. Only the --install flag and the opt-in environment variable reach this."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pin(package_name), "--quiet"],
            capture_output=True, text=True, timeout=120,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def install_playwright_browsers():
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True, text=True, timeout=300,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_and_install(groups=None, install=False):
    """Report each package in `groups`. Installs missing ones only when install=True."""
    groups = DEFAULT_GROUPS if groups is None else groups
    results = {}
    for group in groups:
        for pkg in ALL_GROUPS.get(group, []):
            if check_package(pkg):
                results[pkg] = {"status": "installed", "action": "none"}
                continue
            if not install:
                results[pkg] = {"status": "missing", "action": "none", "fix": install_command([pkg])}
                if pkg == "playwright":
                    results[pkg]["browser_fix"] = browser_command()
                continue
            print(f"  Installing {pin(pkg)}...")
            if install_package(pkg):
                results[pkg] = {"status": "installed", "action": "installed"}
                if pkg == "playwright":
                    print("  Installing Playwright browsers...")
                    results[pkg]["browsers"] = "installed" if install_playwright_browsers() else "failed"
            else:
                results[pkg] = {"status": "missing", "action": "failed", "fix": install_command([pkg])}
    return results


def ensure_package(package_name):
    """Library entry point used by scripts mid-run. Returns True when the package is importable.

    It never installs on its own: a missing package prints the exact pinned command to STDERR (the
    calling script's stdout is a JSON contract) and returns False. Only SOCIALFORGE_INSTALL_DEPS=1,
    set by the user for this run, lets it run that command."""
    if check_package(package_name):
        return True
    if os.environ.get(OPT_IN_ENV) == "1":
        print(f"  Installing {pin(package_name)} ({OPT_IN_ENV}=1 was set)...", file=sys.stderr)
        return install_package(package_name) and check_package(package_name)
    print(f"  {package_name} is not installed, and SocialForge does not install packages on its own. "
          f"Run: {install_command([package_name])}", file=sys.stderr)
    return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SocialForge dependency check / installer (installs only with --install)")
    parser.add_argument("--check", action="store_true", help="Report only (the default); never installs")
    parser.add_argument("--install", action="store_true",
                        help="Run the pinned install commands for the missing packages in --groups")
    parser.add_argument("--groups", nargs="*", default=None, choices=sorted(ALL_GROUPS),
                        help="Groups to report or install (default: " + " ".join(DEFAULT_GROUPS) + ")")
    args = parser.parse_args()
    if args.check and args.install:
        parser.error("--check and --install cannot be combined")

    groups = args.groups or DEFAULT_GROUPS
    results = check_and_install(groups, install=args.install)
    print(json.dumps(results, indent=2))

    missing = [k for k, v in results.items() if v["status"] == "missing"]
    if missing and not args.install:
        print("Not installed: " + ", ".join(missing))
        print("Nothing was installed. To install them yourself, run:")
        print("  " + install_command(missing))
        if "playwright" in missing:
            print("  " + browser_command() + "   (downloads a browser)")
        print("Or re-run this script with --install to have it run those commands.")
        sys.exit(1)
    if missing:
        print("Failed to install: " + ", ".join(missing))
        print("Try manually: " + install_command(missing))
        sys.exit(1)
    print("All requested dependencies are ready.")


if __name__ == "__main__":
    main()
