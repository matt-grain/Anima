# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Version management tools for Anima."""

import urllib.request
import json
from datetime import datetime
from importlib.metadata import version as get_version, PackageNotFoundError
from pathlib import Path

GITHUB_REPO = "matt-grain/Anima"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
UPDATE_CHECK_CACHE_FILE = Path.home() / ".anima" / "last_update_check.json"
UPDATE_CHECK_INTERVAL_DAYS = 1


def get_installed_version() -> str:
    """Get the currently installed version of Anima."""
    try:
        return get_version("anima-ltm")
    except PackageNotFoundError:
        # Fallback: try to read from pyproject.toml (dev mode)
        from pathlib import Path

        pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
        if pyproject.exists():
            for line in pyproject.read_text().splitlines():
                if line.startswith("version"):
                    return line.split("=")[1].strip().strip('"')
        return "unknown"


def get_latest_release() -> dict | None:
    """Fetch the latest release info from GitHub.

    Returns:
        Dict with 'tag_name', 'html_url', 'assets', etc. or None on error.
    """
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "Anima-LTM"},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception:
        return None


def parse_version(v: str) -> tuple[int, ...]:
    """Parse version string to tuple for comparison."""
    # Strip 'v' prefix if present
    v = v.lstrip("v")
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


def get_cached_update_check() -> dict | None:
    """Get cached update check result if still valid.

    Returns:
        Dict with 'latest_version', 'html_url', 'checked_at' or None if cache expired/missing.
    """
    if not UPDATE_CHECK_CACHE_FILE.exists():
        return None

    try:
        data = json.loads(UPDATE_CHECK_CACHE_FILE.read_text())
        checked_at = datetime.fromisoformat(data.get("checked_at", ""))
        days_since = (datetime.now() - checked_at).days

        if days_since < UPDATE_CHECK_INTERVAL_DAYS:
            return data
    except (json.JSONDecodeError, ValueError, KeyError):
        pass

    return None


def save_update_check_cache(latest_version: str, html_url: str) -> None:
    """Save update check result to cache."""
    UPDATE_CHECK_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "latest_version": latest_version,
        "html_url": html_url,
        "checked_at": datetime.now().isoformat(),
    }
    UPDATE_CHECK_CACHE_FILE.write_text(json.dumps(data))


def check_for_update_cached() -> dict | None:
    """Check for updates, using cache if recent.

    Returns:
        Dict with 'current', 'latest', 'update_available', 'html_url' or None on error.
    """
    current = get_installed_version()

    # Try cache first, but only if it makes sense
    cached = get_cached_update_check()
    if cached:
        latest = cached.get("latest_version", "")
        # If cached "latest" is older than current, cache is stale
        # (e.g., we just released and installed a new version)
        # Bypass cache to get the real latest
        if parse_version(latest) >= parse_version(current):
            return {
                "current": current,
                "latest": latest,
                "update_available": parse_version(latest) > parse_version(current),
                "html_url": cached.get("html_url", ""),
                "from_cache": True,
            }
        # else: fall through to fetch fresh from GitHub

    # Fetch from GitHub
    release = get_latest_release()
    if not release:
        return None

    latest = release.get("tag_name", "").lstrip("v")
    html_url = release.get("html_url", "")

    # Cache the result
    save_update_check_cache(latest, html_url)

    return {
        "current": current,
        "latest": latest,
        "update_available": parse_version(latest) > parse_version(current),
        "html_url": html_url,
        "from_cache": False,
    }


def run_version(args: list[str]) -> int:
    """Show the installed version."""
    version = get_installed_version()
    print(f"Anima v{version}")
    return 0


def run_check_update(args: list[str]) -> int:
    """Check if a newer version is available on GitHub."""
    current = get_installed_version()
    print(f"Current version: v{current}")
    print(f"Checking {GITHUB_REPO} for updates...")

    release = get_latest_release()
    if not release:
        print("  Could not fetch release info from GitHub")
        return 1

    latest = release.get("tag_name", "").lstrip("v")
    html_url = release.get("html_url", "")

    if parse_version(latest) > parse_version(current):
        print(f"\n  New version available: v{latest}")
        print(f"  Release: {html_url}")
        print("\n  Run 'anima update' to upgrade")
        return 0
    else:
        print(f"\n  You're up to date! (latest: v{latest})")
        return 0


def run_update(args: list[str]) -> int:
    """Update Anima to the latest version from GitHub releases."""
    import subprocess

    current = get_installed_version()
    print(f"Current version: v{current}")
    print(f"Fetching latest release from {GITHUB_REPO}...")

    release = get_latest_release()
    if not release:
        print("  Could not fetch release info from GitHub")
        return 1

    latest = release.get("tag_name", "").lstrip("v")

    if parse_version(latest) <= parse_version(current):
        print(f"\n  Already at latest version (v{latest})")
        return 0

    # Find the wheel asset
    assets = release.get("assets", [])
    wheel_url = None
    for asset in assets:
        name = asset.get("name", "")
        if name.endswith(".whl"):
            wheel_url = asset.get("browser_download_url")
            break

    if not wheel_url:
        print("  No wheel found in release assets")
        print(f"  Please download manually from: {release.get('html_url', '')}")
        return 1

    print(f"\n  Upgrading to v{latest}...")
    print(f"  Wheel: {wheel_url}")

    # Run uv add --dev with the wheel URL
    try:
        result = subprocess.run(
            ["uv", "add", "--dev", wheel_url, "--upgrade"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"  Error running uv add: {result.stderr}")
            return 1
        print("  Package updated successfully!")
    except FileNotFoundError:
        print("  'uv' not found. Please install with:")
        print(f"    pip install {wheel_url}")
        return 1

    # Run setup --force to refresh hooks/commands/skills
    print("\n  Refreshing hooks, commands, and skills...")
    from anima.tools.setup import run as run_setup

    run_setup(["--force"])

    print(f"\n  Anima updated to v{latest}")
    return 0
