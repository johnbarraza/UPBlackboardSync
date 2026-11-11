import uuid
import mimetypes

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from blackboard.blackboard import BBAttachment

from datetime import datetime

from .base import BStream, has_extension
from .api_path import BBContentPath
from .job import DownloadJob


class Attachment(BStream):
    """File attached to a content."""

    def __init__(self, attachment: BBAttachment, api_path: BBContentPath,
                 job: DownloadJob, posted: datetime | None = None):
        self.posted = posted
        filename = attachment.fileName or str(uuid.uuid1())

        # Only guess an extension when the name has none: Blackboard sends
        # application/octet-stream for .do/.dta/etc., which would add .bin
        if has_extension(filename):
            self.filename = filename
        else:
            mime = attachment.mimeType or 'text/plain'
            possible_ext = mimetypes.guess_all_extensions(mime, strict=False)
            self.filename = filename + (
                possible_ext[0] if possible_ext else '.txt')

        self.stream = job.session.download(attachment_id=attachment.id,
                                           **api_path)

    def write(self, path: Path, executor: ThreadPoolExecutor) -> None:
        super().write_base(path / self.filename, executor, self.stream)
