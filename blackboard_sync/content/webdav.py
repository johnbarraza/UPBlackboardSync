"""
Parse an html to look for links
"""

# Copyright (C) 2021, Jacob Sánchez Pérez

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


import os
import re
import uuid
import mimetypes
from pathlib import Path
from requests import Response
from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse, parse_qs
from typing import List, NamedTuple
from pathvalidate import sanitize_filename
from concurrent.futures import ThreadPoolExecutor

from .base import BStream
from .job import DownloadJob


class Link(NamedTuple):
    href: str
    text: str


class ContentParser:
    def __init__(self, body: str, base_url: str,
                 *, find_links: bool = True) -> None:
        soup = BeautifulSoup(body, 'html.parser')
        self._links = []

        if find_links:
            a = self._find_replace(soup, 'a', 'href', base_url)
            img = self._find_replace(soup, 'img', 'src', base_url)
            self._links = [*a, *img]

        self._body = str(soup)
        self._text = soup.text

    def _find_replace(self, soup: BeautifulSoup,
                      tag: str, attr: str, base_url: str) -> list[Link]:
        links = []

        for el in soup.find_all(tag):
            # Add link for later download
            uri = el.get(attr)

            if uri:
                display = None

                # Priority 1: Check aria-label for filename (Blackboard Ultra uses this)
                aria_label = el.get('aria-label', '')
                if aria_label:
                    # Extract filename from patterns like "Preview File filename.pdf"
                    match = re.search(r'(?:Preview File|Download|File)\s+(.+?)(?:\s*$)', aria_label)
                    if match:
                        candidate = match.group(1).strip()
                        if candidate and not candidate.lower().startswith('xid'):
                            display = candidate

                # Priority 2: Check aria-controls for filename extraction
                if not display:
                    aria_controls = el.get('aria-controls', '')
                    if 'xid-' in aria_controls:
                        # Try to extract filename from URLs like file-preview-...xid-19839037_1
                        parsed = urlparse(uri)
                        last = unquote(os.path.basename(parsed.path))
                        if not last or last.lower().startswith('xid'):
                            # Try query params
                            qs = parse_qs(parsed.query)
                            for key in ('filename', 'file', 'name', 'FileName'):
                                if key in qs and qs[key]:
                                    display = qs[key][0]
                                    break

                # Priority 3: Use visible text if present and meaningful
                if not display:
                    text_val = (el.text or '').strip()
                    if text_val and not text_val.lower().startswith('xid'):
                        display = text_val

                # Priority 4: Parse URL and extract sensible filename
                if not display:
                    parsed = urlparse(uri)
                    last = unquote(os.path.basename(parsed.path))
                    if (not last) or ('=' in last) or last.lower().startswith('xid'):
                        qs = parse_qs(parsed.query)
                        for key in ('filename', 'file', 'name', 'FileName', 'xid'):
                            if key in qs and qs[key]:
                                last = qs[key][0]
                                break
                    display = last or parsed.netloc or f"file-{uuid.uuid4()}"

                links.append(Link(href=uri, text=display))

                # Replace href/src with a local filename when it's a same-site link
                if uri.startswith(base_url):
                    el[attr] = display
        return links

    @property
    def links(self) -> List[Link]:
        return self._links

    @property
    def body(self) -> str:
        return self._body

    @property
    def text(self) -> str:
        return self._text


def validate_webdav_response(response: Response,
                             link: str, base_url: str) -> bool:
    if response.status_code == 200:
        h = response.headers
        content_type = h.get('Content-Type', '')
        content_len = int(h.get('Content-Length', 0))

        # TODO: feature: select mime types
        len_limit = 1024 * 1024 * 20  # 20 MB

        filters = [
            link.startswith(base_url),
            'video' not in content_type,
            content_len < len_limit
        ]

        return all(filters)
    return False


class WebDavFile(BStream):
    """A Blackboard WebDav file which can be downloaded directly"""
    def __init__(self, link: Link, job: DownloadJob) -> None:
        # Download first, then try to determine a safe filename
        self.stream = job.session.download_webdav(webdav_url=link.href)

        # Try to extract filename from Content-Disposition header
        cd = self.stream.headers.get('Content-Disposition', '')
        filename = None
        if cd:
            m = re.search(r'filename\*?=(?:UTF-8''?)?\"?([^\";]+)\"?', cd)
            if m:
                filename = m.group(1)

        if not filename:
            # Use the parsed link text (from ContentParser) if it seems ok
            candidate = link.text or ''
            # If candidate looks like an encoded query param or xid, fall back
            if not candidate or ('=' in candidate) or candidate.lower().startswith('xid'):
                parsed = urlparse(link.href)
                candidate = unquote(os.path.basename(parsed.path)) or f"file-{uuid.uuid4()}"

            filename = candidate

        self.title = sanitize_filename(unquote(filename), replacement_text="_")

        content_type = self.stream.headers.get('Content-Type', 'text/plain')
        self.extension = mimetypes.guess_extension(content_type) or ''
        self.valid = validate_webdav_response(self.stream, link.href,
                                              job.session.instance_url)

    def write(self, path: Path, executor: ThreadPoolExecutor) -> None:
        if self.valid:
            path = Path(path, self.title)

            if self.extension:
                path = path.with_suffix(self.extension)

            super().write_base(path, executor, self.stream)
