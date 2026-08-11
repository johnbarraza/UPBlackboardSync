import logging
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from blackboard.blackboard import BBCourse

from .api_path import BBContentPath
from .announcement import Announcement
from .roster import Roster
from .job import DownloadJob
from .content import Content

logger = logging.getLogger(__name__)


class Course:
    def __init__(self, course: BBCourse, job: DownloadJob):
        logger.info(f"<{course.code}> - <{course.title}>")

        self.ignore = not course.availability

        if self.ignore:
            return

        self.year = self.get_year(course.created)
        self.title = course.title or 'Untitled Course'

        contents = job.session.fetch_contents(course_id=course.id)
        self.children = []

        for content in contents:
            api_path = BBContentPath(course_id=course.id,
                                     content_id=content.id)
            self.children.append(Content(content, api_path, job))

        self.announcements = self._fetch_announcements(course.id, job)
        self.roster = Roster.fetch(job.session, course.id)

    @staticmethod
    def _fetch_announcements(course_id: str, job: DownloadJob) -> list[Announcement]:
        try:
            result = job.session.fetch_course_announcements(course_id=course_id)
            if isinstance(result, dict):
                items = result.get("results", [])
            elif isinstance(result, list):
                items = result
            else:
                return []
            return [Announcement(item) for item in items]
        except Exception:
            logger.debug("Could not fetch announcements for %s", course_id)
            return []

    def write(self, path: Path, executor: ThreadPoolExecutor) -> None:
        if self.ignore:
            return

        path = path / self.year / self.title

        for child in self.children:
            child.write(path, executor)

        if self.announcements:
            ann_folder = path / "Announcements"
            for ann in self.announcements:
                ann.write(ann_folder)

        self.roster.write(path / "Roster")

    @staticmethod
    def get_year(created: datetime | None) -> str:
        return str(created.year) if created is not None else 'No Date'
