#!/usr/bin/env python3

"""
BlackboardDownload,
mass download all user content from Blackboard
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

import logging
from pathlib import Path
from datetime import datetime, timezone
from collections.abc import Callable

from blackboard.api_extended import BlackboardExtended
from blackboard.filters import BBMembershipFilter, BWFilter

from .executor import SyncExecutor
from .content.job import DownloadJob
from .content.course import Course


logger = logging.getLogger(__name__)


class BlackboardDownload:
    """Blackboard download job."""

    _last_downloaded = datetime.fromtimestamp(0, tz=timezone.utc)

    def __init__(self, sess: BlackboardExtended,
                 download_location: Path,
                 last_downloaded: datetime | None = None,
                 min_year: int | None = None,
                 selected_course_ids: set[str] | None = None,
                 course_last_synced: dict[str, datetime] | None = None,
                 course_synced_callback: Callable[[str, datetime], None] | None = None):
        """BlackboardDownload constructor

        Download all files in blackboard recursively to download_location,
        only if they have been altered since specified datetime

        Keyword arguments:

        :param BlackboardExtended sess: UCLan BB user session
        :param (str / Path) download_location: Where files will be stored
        :param str last_downloaded: Files modified before are ignored
        :param min_year: Courses created before are ignored
        """

        self._sess = sess
        self._user_id = sess.user_id
        self._download_location = download_location
        self._min_year = min_year
        self._selected_course_ids = selected_course_ids or set()
        self._course_last_synced = course_last_synced or {}
        self._course_synced_callback = course_synced_callback
        self.executor = SyncExecutor()
        self.cancelled = False
        self.current_course: str | None = None

        if last_downloaded is not None:
            self._last_downloaded = last_downloaded

    def download(self) -> datetime | None:
        """Retrieve the user's courses, and start download of all contents

        :return: Datetime when method was called.
        """
        if self.cancelled:
            return None

        logger.info("Starting Blackboard content download")

        start_time = datetime.now(timezone.utc)

        if not self.download_location.exists():
            self.download_location.mkdir(parents=True)
            logger.info("Created download folder")

        logger.info("Fetching user memberships and courses")

        course_filter = BBMembershipFilter(min_year=self._min_year,
                                           data_sources=BWFilter())
        courses = self._sess.ex_fetch_courses(user_id=self.user_id,
                                              result_filter=course_filter)
        if self._selected_course_ids:
            courses = [course for course in courses if course.id in self._selected_course_ids]

        synced_course_ids: list[str] = []

        for course in courses:
            if self.cancelled:
                break

            self.current_course = course.title or course.name or course.id
            logger.info(f"Fetching user course <{course.id}>")

            # When using course selection, a never-synced course should download
            # fully at least once (last_downloaded=None -> UNIX_EPOCH).
            if course.id in self._course_last_synced:
                last_downloaded = self._course_last_synced[course.id]
                if not self._course_has_local_files(course):
                    logger.info(
                        "Course %s is marked as synced but has no local files. "
                        "Forcing full download.",
                        course.id
                    )
                    last_downloaded = None
            elif self._selected_course_ids:
                last_downloaded = None
            else:
                last_downloaded = self._last_downloaded

            job = DownloadJob(session=self._sess,
                              last_downloaded=last_downloaded)
            Course(course, job).write(self.download_location, self.executor)
            synced_course_ids.append(course.id)

        logger.info("Shutting down download workers")

        self.executor.shutdown(wait=True, cancel_futures=self.cancelled)
        failed_files = self.executor.raise_exceptions()

        if failed_files > 0:
            logger.warning(
                "Download finished with errors. Last sync timestamp will not "
                "advance so failed files are retried."
            )
            return None

        if self._course_synced_callback is not None:
            for course_id in synced_course_ids:
                self._course_synced_callback(course_id, start_time)

        return start_time if not self.cancelled else None

    def _course_has_local_files(self, course) -> bool:
        year = str(course.created.year) if course.created is not None else "No Date"
        title = course.title or "Untitled Course"
        course_path = self.download_location / year / title

        if not course_path.exists():
            return False

        return any(path.is_file() for path in course_path.rglob("*"))

    def cancel(self) -> None:
        """Cancel the download job."""
        self.cancelled = True

    @property
    def download_location(self) -> Path:
        """The location where files will be downloaded to."""
        return self._download_location

    @property
    def user_id(self) -> str:
        """User ID used for API calls."""
        return self._user_id
