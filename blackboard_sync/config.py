"""
BlackboardSync configuration manager
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
import json
import configparser
from typing import Any
from pathlib import Path
from functools import wraps
from datetime import datetime
from collections.abc import Callable

from appdirs import user_config_dir

logger = logging.getLogger(__name__)


class Config(configparser.ConfigParser):
    """Base configuration manager class, which wraps a ConfigParser."""

    def __init__(self, config_file: Path, *args, **kwargs):
        converters: dict[str, Callable[[str], Any]] = {
            'path': Path, 'date': datetime.fromisoformat
        }

        super().__init__(converters=converters, interpolation=None,
                         *args, **kwargs)

        self._config_file = config_file
        self.read(self._config_file)

        # Set up logging
        logger.setLevel(logging.WARN)
        logger.addHandler(logging.StreamHandler())

    def save(self) -> None:
        """Save the current configuration to disk."""
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
        with self._config_file.open('w') as config_file:
            self.write(config_file)

    @staticmethod
    def persist(func) -> Callable[[Any, Any], None]:
        """A decorator to save any changes to the field to disk."""
        @wraps(func)
        def save_wrapper(self, *args: Any, **kwargs: Any) -> None:
            func(self, *args, **kwargs)
            self.save()
            logger.info("Updated configuration file")
        return save_wrapper


class SyncConfig(Config):
    """Configuration manager for BlackboardSync."""
    _config_filename = "blackboard_sync"
    _app_dir_name = "BlackboardSync"

    def __init__(self, custom_dir=None):
        default_dir = Path(user_config_dir(
            appname=self._app_dir_name,
            appauthor=False,
            roaming=True,
        ))

        config_dir = custom_dir or default_dir
        super().__init__(config_dir / self._config_filename,
                         empty_lines_in_values=False)

        if 'Sync' not in self:
            self['Sync'] = {}

        self._sync = self['Sync']

    @property
    def last_sync_time(self) -> datetime | None:
        return self._sync.getdate('last_sync_time')

    @last_sync_time.setter
    @Config.persist
    def last_sync_time(self, last: datetime | None) -> None:
        if last is None:
            self.remove_option('Sync', 'last_sync_time')
        else:
            self._sync['last_sync_time'] = last.isoformat()

    @property
    def download_location(self) -> Path | None:
        # Default download location
        default = Path(Path.home(), 'Downloads', 'BlackboardSync')
        return self._sync.getpath('download_location') or default

    @download_location.setter
    @Config.persist
    def download_location(self, sync_dir: Path) -> None:
        self._sync['download_location'] = str(sync_dir)

    @property
    def university_index(self) -> int | None:
        return self._sync.getint('university')

    @university_index.setter
    @Config.persist
    def university_index(self, university: int) -> None:
        self._sync['university'] = str(university)

    @property
    def min_year(self) -> int | None:
        return self._sync.getint('min_year')

    @min_year.setter
    @Config.persist
    def min_year(self, year: int | None) -> None:
        self._sync['min_year'] = str(year or 0)

    @property
    def backup_location(self) -> Path | None:
        """Location to backup downloaded files."""
        return self._sync.getpath('backup_location')

    @backup_location.setter
    @Config.persist
    def backup_location(self, backup_dir: Path | None) -> None:
        if backup_dir is None:
            self.remove_option('Sync', 'backup_location')
        else:
            self._sync['backup_location'] = str(backup_dir)

    @property
    def backup_enabled(self) -> bool:
        """Whether backup is enabled."""
        return self._sync.getboolean('backup_enabled', fallback=False)

    @backup_enabled.setter
    @Config.persist
    def backup_enabled(self, enabled: bool) -> None:
        self._sync['backup_enabled'] = str(enabled)

    @property
    def drive_enabled(self) -> bool:
        return self._sync.getboolean('drive_enabled', fallback=False)

    @drive_enabled.setter
    @Config.persist
    def drive_enabled(self, enabled: bool) -> None:
        self._sync['drive_enabled'] = str(enabled)

    @property
    def drive_folder_id(self) -> str | None:
        return self._sync.get('drive_folder_id')

    @drive_folder_id.setter
    @Config.persist
    def drive_folder_id(self, folder_id: str | None) -> None:
        if folder_id:
            self._sync['drive_folder_id'] = folder_id
        else:
            self.remove_option('Sync', 'drive_folder_id')

    @property
    def drive_credentials_path(self) -> Path | None:
        return self._sync.getpath('drive_credentials_path')

    @drive_credentials_path.setter
    @Config.persist
    def drive_credentials_path(self, path: Path | None) -> None:
        if path:
            self._sync['drive_credentials_path'] = str(path)
        else:
            self.remove_option('Sync', 'drive_credentials_path')
    
    @property
    def drive_token_path(self) -> Path:
        """Path where file token.json is stored (next to config file)."""
        return self._config_file.parent / 'token.json'

    @property
    def data_directory(self) -> Path:
        """Directory where app-owned config, token, and logs are stored."""
        return self._config_file.parent

    @property
    def log_directory(self) -> Path:
        """Directory where diagnostic logs are stored."""
        return self.data_directory / 'logs'

    @property
    def selected_course_ids(self) -> list[str]:
        """Selected course ids for sync. Empty means sync all courses."""
        raw = self._sync.get('selected_course_ids')
        if not raw:
            return []

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []

        if not isinstance(parsed, list):
            return []

        return [str(course_id) for course_id in parsed if course_id]

    @selected_course_ids.setter
    @Config.persist
    def selected_course_ids(self, course_ids: list[str]) -> None:
        clean = sorted({str(course_id) for course_id in course_ids if course_id})
        if clean:
            self._sync['selected_course_ids'] = json.dumps(clean)
        else:
            self.remove_option('Sync', 'selected_course_ids')

    @property
    def mcp_enabled(self) -> bool:
        return self._sync.getboolean('mcp_enabled', fallback=True)

    @mcp_enabled.setter
    @Config.persist
    def mcp_enabled(self, enabled: bool) -> None:
        self._sync['mcp_enabled'] = str(enabled)

    @property
    def course_sync_status(self) -> dict[str, datetime]:
        """Course id -> last successful sync timestamp."""
        raw = self._sync.get('course_sync_status')
        if not raw:
            return {}

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}

        if not isinstance(parsed, dict):
            return {}

        status: dict[str, datetime] = {}
        for course_id, sync_value in parsed.items():
            if not course_id or not isinstance(sync_value, str):
                continue
            try:
                status[str(course_id)] = datetime.fromisoformat(sync_value)
            except ValueError:
                continue

        return status

    @course_sync_status.setter
    @Config.persist
    def course_sync_status(self, status: dict[str, datetime]) -> None:
        if not status:
            self.remove_option('Sync', 'course_sync_status')
            return

        encoded = {
            str(course_id): timestamp.isoformat()
            for course_id, timestamp in status.items()
            if course_id and isinstance(timestamp, datetime)
        }

        if encoded:
            self._sync['course_sync_status'] = json.dumps(encoded)
        else:
            self.remove_option('Sync', 'course_sync_status')
