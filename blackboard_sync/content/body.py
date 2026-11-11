from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from blackboard.blackboard import BBCourseContent

from .base import FStream
from .job import DownloadJob
from .templates import create_body
from .webdav import WebDavFile, ContentParser


class ContentBody(FStream):
    """Process the content body to find WebDav files."""

    def __init__(self, content: BBCourseContent, _: None,
                 job: DownloadJob) -> None:
        self.ignore = False

        if not content.body:
            self.ignore = True
            return

        title = content.title or "Untitled"
        parser = ContentParser(content.body, job.session.instance_url)

        # created = when the teacher posted it; modified also moves on
        # edits, reorders and visibility toggles
        self.posted = content.created or content.modified
        self.body = create_body(title, parser.body, parser.text)
        self.children = [WebDavFile(ln, job, self.posted)
                         for ln in parser.links]

        # Ultra items that only embed files have no text besides the file
        # names; the html wrapper adds nothing for those.
        rest = parser.text
        for ln in parser.links:
            rest = rest.replace(ln.text, '')
        self.file_only = bool(self.children) and not rest.strip()

    def write(self, path: Path, executor: ThreadPoolExecutor) -> None:
        if self.ignore:
            return

        if not self.file_only:
            self.write_base(path / f"{path.stem}.html", executor, self.body)

        for child in self.children:
            child.write(path, executor)
