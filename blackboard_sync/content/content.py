import logging
from pathlib import Path
from json import JSONDecodeError
from pydantic import ValidationError
from requests import RequestException
from concurrent.futures import ThreadPoolExecutor

from blackboard.blackboard import (
    BBCourseContent,
    BBResourceType,
    BBContentHandler
)
from blackboard.exceptions import BBBadRequestError, BBForbiddenError

from . import folder, document, externallink, body, unhandled

from .api_path import BBContentPath
from .job import DownloadJob
from .webdav import ContentParser
from pathvalidate import sanitize_filename

logger = logging.getLogger(__name__)


class Content:
    """Content factory for all types."""

    def __init__(self, content: BBCourseContent, api_path: BBContentPath,
                 job: DownloadJob) -> None:

        logger.info(f"{content.title}[{content.contentHandler}]")

        self.body = None
        self.handler = None

        self.ignore = not Content.should_download(content, job)

        if self.ignore:
            return

        Handler = Content.get_handler(content.contentHandler)
        # Prefer the provided title, but Blackboard sometimes uses the
        # placeholder 'ultraDocumentBody' for items that only have HTML
        # content. In that case, try to extract a meaningful title from the
        # HTML body (first heading or first line of text).
        raw_title = getattr(content, 'title', None) or ''

        if raw_title and raw_title != 'ultraDocumentBody':
            chosen = raw_title
        else:
            chosen = None
            try:
                if getattr(content, 'body', None):
                    parser = ContentParser(content.body, job.session.instance_url)
                    text = (parser.text or '').strip()
                    if text:
                        # use first non-empty line as title
                        first_line = next((ln for ln in text.splitlines() if ln.strip()), None)
                        chosen = first_line
                    # fallback to first link text
                    if not chosen and parser.links:
                        chosen = parser.links[0].text
            except Exception:
                chosen = None

            if not chosen:
                chosen = raw_title or 'Untitled'

        # Make a filesystem-safe title
        self.title = sanitize_filename(str(chosen).replace('.', '_'))

        try:
            self.handler = Handler(content, api_path, job)
        except (ValidationError, JSONDecodeError,
                BBBadRequestError, BBForbiddenError):
            logger.exception(f"Error fetching {content.title}")

        try:
            if content.body:
                self.body = body.ContentBody(content, None, job)
        except (ValidationError, JSONDecodeError,
                BBBadRequestError, BBForbiddenError, RequestException):
            logger.warning(f"Error fetching body of {content.title}")

    def write(self, path: Path, executor: ThreadPoolExecutor) -> None:
        if self.ignore:
            return

        # Build nested path with content title
        path = path / self.title

        if self.handler is not None:
            if self.handler.create_dir:
                path.mkdir(exist_ok=True, parents=True)

            self.handler.write(path, executor)

        if self.body is not None:
            path.mkdir(exist_ok=True, parents=True)
            self.body.write(path, executor)

    @staticmethod
    def should_download(content: BBCourseContent, job: DownloadJob) -> bool:
        or_guards = [
            job.has_changed(content.modified),
            content.hasChildren,
        ]

        return any(or_guards) and bool(content.availability)

    @staticmethod
    def get_handler(content_handler: BBContentHandler | None):
        match content_handler:
            case BBResourceType.Folder | BBResourceType.Lesson:
                return folder.Folder
            case BBResourceType.File | BBResourceType.Document:
                return document.Document
            case BBResourceType.Assignment:
                return document.Document
            case BBResourceType.ExternalLink:
                return externallink.ExternalLink
            case _:
                return unhandled.Unhandled
