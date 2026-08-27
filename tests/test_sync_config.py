"""BlackboardSync Configuration Manager Tests"""

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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import tempfile
import logging
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from hypothesis import given, assume
from hypothesis import strategies as st

from blackboard_sync.config import SyncConfig
from blackboard_sync.sync import BlackboardSync


def test_config_default_values():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        s = SyncConfig(tmp_path)
        assert s.last_sync_time is None


def test_mcp_is_enabled_by_default_and_can_be_disabled(tmp_path):
    config = SyncConfig(tmp_path)

    assert config.mcp_enabled is True

    config.mcp_enabled = False

    assert SyncConfig(tmp_path).mcp_enabled is False


def test_config_save_creates_missing_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "missing"
        config = SyncConfig(tmp_path)

        config.university_index = 0

        assert (tmp_path / "blackboard_sync").exists()


def test_default_config_directory_uses_blackboardsync_folder(monkeypatch):
    monkeypatch.setattr(
        "blackboard_sync.config.user_config_dir",
        lambda **kwargs: "C:/Users/example/AppData/Roaming/BlackboardSync",
    )

    config = SyncConfig()

    assert config.data_directory == Path(
        "C:/Users/example/AppData/Roaming/BlackboardSync"
    )
    assert config.log_directory == config.data_directory / "logs"


def test_sync_log_handler_uses_app_log_directory(tmp_path):
    config = SyncConfig(tmp_path / "config")
    config.download_location = tmp_path / "downloads"

    sync = BlackboardSync.__new__(BlackboardSync)
    sync._config = config
    sync._log_handler = None

    BlackboardSync._add_logger_file_handler(sync)

    assert config.log_directory.exists()
    assert not (config.download_location / "log").exists()
    assert getattr(
        sync._log_handler,
        "_blackboardsync_log_path",
    ).parent == config.log_directory

    logging.getLogger("blackboard_sync").removeHandler(sync._log_handler)
    sync._log_handler.close()


def test_sync_exposes_active_log_path(tmp_path):
    config = SyncConfig(tmp_path / "config")
    sync = BlackboardSync.__new__(BlackboardSync)
    sync._config = config
    sync._log_handler = None

    BlackboardSync._add_logger_file_handler(sync)

    assert sync.log_path is not None
    assert sync.log_path.parent == config.log_directory

    logging.getLogger("blackboard_sync").removeHandler(sync._log_handler)
    sync._log_handler.close()


def test_force_sync_can_target_one_run_without_changing_config(tmp_path):
    config = SyncConfig(tmp_path / "config")
    config.selected_course_ids = ["saved-course"]
    sync = BlackboardSync.__new__(BlackboardSync)
    sync._config = config
    sync._force_sync = False
    sync._next_sync_course_ids = None

    sync.force_sync({"requested-course"})

    assert sync._force_sync is True
    assert sync._next_sync_course_ids == {"requested-course"}
    assert config.selected_course_ids == ["saved-course"]


@given(st.datetimes())
def test_config_last_sync_time(sync_time):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config = SyncConfig(tmp_path)
        config.last_sync_time = sync_time
        assert config.last_sync_time == sync_time

        new_config = SyncConfig(tmp_path)
        assert new_config.last_sync_time == sync_time

