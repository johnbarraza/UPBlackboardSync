"""
Checks for updates in GitHub.
"""

# Copyright (C) 2023, Jacob Sánchez Pérez

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

import hashlib
import logging
import sys
import tempfile
from pathlib import Path

import requests
from packaging import version

from .__about__ import __uri__, __version__

logger = logging.getLogger(__name__)

REPO = __uri__.removeprefix("https://github.com/")
LATEST_API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"{__uri__}/releases/latest"
SETUP_NAME = "BlackboardSync-Setup.exe"


def _is_newer(tag: str) -> bool:
    tag = tag[1:] if tag.startswith('v') else tag
    try:
        return version.parse(tag) > version.parse(__version__)
    except version.InvalidVersion:
        return False


def check_for_updates() -> bool:
    """Checks if there is a newer release than the current on Github."""
    try:
        response = requests.get(LATEST_API, timeout=20)
        response.raise_for_status()
        tag = response.json()['tag_name']
    except (requests.RequestException, KeyError, ValueError):
        return False
    return _is_newer(tag)


def is_installed() -> bool:
    """True for the NSIS-installed Windows app; False for the portable exe."""
    return (sys.platform == "win32"
            and bool(getattr(sys, "frozen", False))
            and (Path(sys.executable).parent / "Uninstall.exe").exists())


def download_installer() -> Path | None:
    """Download the latest Setup.exe and verify it, or return None.

    Only accepts a newer release's asset hosted under this repo's GitHub
    releases, and only if its bytes match the SHA-256 digest GitHub
    computed on upload. Anything else falls back to the browser.
    """
    try:
        response = requests.get(LATEST_API, timeout=20)
        response.raise_for_status()
        release = response.json()
        asset = next(a for a in release["assets"] if a["name"] == SETUP_NAME)
        url = asset["browser_download_url"]
        algo, _, expected = asset["digest"].partition(":")
        newer = _is_newer(release["tag_name"])
    except (requests.RequestException, KeyError, ValueError, TypeError,
            AttributeError, StopIteration):
        logger.warning("Update: could not read latest release")
        return None

    prefix = f"https://github.com/{REPO}/releases/download/"
    if not newer or algo != "sha256" or not url.startswith(prefix):
        logger.warning("Update: release rejected (newer=%s, digest=%s, url=%s)",
                       newer, algo, url)
        return None

    # fresh private dir; never the exe name the installer taskkills
    path = Path(tempfile.mkdtemp(prefix="bbsync-update-")) / SETUP_NAME
    digest = hashlib.sha256()
    try:
        with requests.get(url, stream=True, timeout=(20, 120)) as resp:
            resp.raise_for_status()
            with path.open("wb") as f:
                for chunk in resp.iter_content(1 << 20):
                    digest.update(chunk)
                    f.write(chunk)
    except (requests.RequestException, OSError):
        logger.warning("Update: download failed")
        path.unlink(missing_ok=True)
        return None

    if digest.hexdigest() != expected.lower():
        logger.warning("Update: SHA-256 mismatch, installer discarded")
        path.unlink(missing_ok=True)
        return None

    logger.info("Update: installer downloaded and verified (%s)", path)
    return path
