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

import requests
from packaging import version

from .__about__ import __uri__, __version__


def check_for_updates() -> bool:
    """Checks if there is a newer release than the current on Github."""

    repo = __uri__.removeprefix("https://github.com/")
    url = f"https://api.github.com/repos/{repo}/releases/latest"

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        tag = response.json()['tag_name']
    except (requests.RequestException, KeyError, ValueError):
        return False

    tag = tag[1:] if tag.startswith('v') else tag
    try:
        return version.parse(tag) > version.parse(__version__)
    except version.InvalidVersion:
        return False
    return False
