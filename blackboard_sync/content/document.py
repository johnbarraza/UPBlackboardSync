from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import logging

from blackboard.blackboard import BBCourseContent
from blackboard.filters import BBAttachmentFilter
from blackboard.exceptions import BBBadRequestError
from bwfilters import BWFilter

from .attachment import Attachment
from .api_path import BBContentPath
from .job import DownloadJob

logger = logging.getLogger(__name__)


class Document:
    """Represents a file with attachments in the Blackboard API"""
    def __init__(self, content: BBCourseContent, api_path: BBContentPath,
                 job: DownloadJob):
        try:
            attachments = job.session.fetch_file_attachments(**api_path)
            assert isinstance(attachments, list)
        except BBBadRequestError:
            # Some content items don't support file attachments (HTTP 400).
            # Treat them as having no attachments and continue gracefully.
            course_id = api_path.get('course_id') if isinstance(api_path, dict) else None
            content_id = api_path.get('content_id') if isinstance(api_path, dict) else None
            handler = getattr(content, 'contentHandler', None)
            title = getattr(content, 'title', None)
            logger.warning(
                "Content item does not support file attachments: title=%s, handler=%s, course_id=%s, content_id=%s",
                title, handler, course_id, content_id
            )
            attachments = []

        att_filter = BBAttachmentFilter(mime_types=BWFilter(['video/*']))
        filtered_attachments = list(att_filter.filter(attachments))

        self.attachments = []

        for i, attachment in enumerate(filtered_attachments):
            self.attachments.append(
                Attachment(attachment, api_path, job)
            )

    def write(self, path: Path, executor: ThreadPoolExecutor) -> None:
        # If only attachment, just use parent
        if len(self.attachments) > 1:
            path.mkdir(exist_ok=True, parents=True)
        else:
            path = path.parent

        for attachment in self.attachments:
            attachment.write(path, executor)

    @property
    def create_dir(self) -> bool:
        return False
