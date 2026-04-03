#!/usr/bin/env python3
"""
install_deps.py - Auto-install Python dependencies for SocialForge.

Called by /sf:setup and as a fallback from other scripts when imports fail.
Handles: google-genai, wavespeed, Pillow, playwright.
"""

import json
import subprocess
import sys


REQUIRED = {
    "core": ["Pillow"],
    "image": ["google-genai"],
    "video": ["wavespeed", "higgsfield-client", "imageio-ffmpeg"],
    "carousel": ["playwright"],
    "optional": ["rembg"],
}

ALL_PACKAGES = []
for group in REQUIRED.values():
    ALL_PACKAGES.extend(group)


def check_package(package_name):
    import_name = package_name.replace("-", "_").replace("google_genai", "google.genai")
    if package_name == "google-genai":
        import_name = "google.genai"
    elif package_name == "Pillow":
        import_name = "PIL"
    try:
        __import__(import_name.split(".")[0])
        return True
    except ImportError:
        return False


def install_package(package_name):
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name, "--quiet"],
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


def check_and_install(groups=None):
    if groups is None:
        groups = list(REQUIRED.keys())

    results = {}
    for group in groups:
        packages = REQUIRED.get(group, [])
        for pkg in packages:
            if check_package(pkg):
                results[pkg] = {"status": "installed", "action": "none"}
            else:
                print(f"  Installing {pkg}...")
                if install_package(pkg):
                    results[pkg] = {"status": "installed", "action": "installed"}
                    if pkg == "playwright":
                        print("  Installing Playwright browsers...")
                        if install_playwright_browsers():
                            results[pkg]["browsers"] = "installed"
                        else:
                            results[pkg]["browsers"] = "failed"
                else:
                    results[pkg] = {"status": "missing", "action": "failed",
                                    "fix": f"pip install {pkg}"}

    return results


def ensure_package(package_name):
    if not check_package(package_name):
        print(f"  Auto-installing {package_name}...")
        return install_package(package_name)
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SocialForge Dependency Installer")
    parser.add_argument("--check", action="store_true", help="Check only, do not install")
    parser.add_argument("--groups", nargs="*", default=None,
                        help="Install specific groups: core image video carousel")
    args = parser.parse_args()

    groups = args.groups or list(REQUIRED.keys())

    if args.check:
        for group in groups:
            for pkg in REQUIRED.get(group, []):
                status = "installed" if check_package(pkg) else "MISSING"
                print(f"  {pkg}: {status}")
    else:
        print("Checking and installing SocialForge dependencies...")
        results = check_and_install(groups)
        print(json.dumps(results, indent=2))

        missing = [k for k, v in results.items() if v["status"] == "missing"]
        if missing:
            print("Failed to install: " + ", ".join(missing))
            print("Try manually: pip install " + " ".join(missing))
            sys.exit(1)
        else:
            print("All dependencies ready.")


if __name__ == "__main__":
    main()
