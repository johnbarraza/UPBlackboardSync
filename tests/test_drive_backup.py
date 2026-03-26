from pathlib import Path
from unittest import mock

import pytest

from blackboard_sync.config import SyncConfig
from blackboard_sync.drive_service import DriveService
from blackboard_sync.sync import BlackboardSync


def make_sync_config(tmp_path: Path) -> tuple[SyncConfig, Path]:
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    download_dir = tmp_path / "downloads"
    download_dir.mkdir()

    config = SyncConfig(config_dir)
    config.download_location = download_dir
    return config, download_dir


def make_sync(config: SyncConfig, drive_service) -> BlackboardSync:
    sync = BlackboardSync.__new__(BlackboardSync)
    sync._config = config
    sync._drive_service = drive_service
    return sync


def test_find_folder_escapes_apostrophes():
    service = DriveService(Path("credentials.json"), Path("token.json"))
    files_api = mock.Mock()
    files_api.list.return_value.execute.return_value = {"files": [{"id": "folder-1"}]}
    service.service = mock.Mock(files=mock.Mock(return_value=files_api))

    folder_id = service.find_folder("John's Notes", "parent'123")

    assert folder_id == "folder-1"
    assert files_api.list.call_args.kwargs["q"] == (
        "mimeType='application/vnd.google-apps.folder' and "
        "name='John\\'s Notes' and trashed=false and 'parent\\'123' in parents"
    )


def test_upload_file_escapes_apostrophes(tmp_path):
    service = DriveService(Path("credentials.json"), Path("token.json"))
    test_file = tmp_path / "John's Notes.pdf"
    test_file.write_text("content")

    files_api = mock.Mock()
    files_api.list.return_value.execute.return_value = {"files": [{"id": "file-1"}]}
    files_api.update.return_value.execute.return_value = {}
    service.service = mock.Mock(files=mock.Mock(return_value=files_api))

    with mock.patch("blackboard_sync.drive_service.MediaFileUpload", return_value=mock.Mock()):
        assert service.upload_file(test_file, "parent'123")

    assert files_api.list.call_args.kwargs["q"] == (
        "name='John\\'s Notes.pdf' and 'parent\\'123' in parents and trashed=false"
    )
    files_api.update.assert_called_once()


def test_run_backup_reuses_existing_drive_root(tmp_path):
    config, download_dir = make_sync_config(tmp_path)
    config.drive_enabled = True
    config.drive_folder_id = "root-folder"

    drive_service = mock.Mock()
    drive_service.authenticates.return_value = True
    drive_service.folder_exists.return_value = True

    sync = make_sync(config, drive_service)
    sync._run_backup()

    drive_service.folder_exists.assert_called_once_with("root-folder")
    drive_service.ensure_folder.assert_not_called()
    drive_service.mirror_tree.assert_called_once_with(download_dir, "root-folder")
    assert config.drive_folder_id == "root-folder"


def test_run_backup_recreates_missing_drive_root(tmp_path):
    config, download_dir = make_sync_config(tmp_path)
    config.drive_enabled = True
    config.drive_folder_id = "stale-folder"

    drive_service = mock.Mock()
    drive_service.authenticates.return_value = True
    drive_service.folder_exists.return_value = False
    drive_service.ensure_folder.return_value = "new-root"

    sync = make_sync(config, drive_service)
    sync._run_backup()

    drive_service.folder_exists.assert_called_once_with("stale-folder")
    drive_service.ensure_folder.assert_called_once_with("BlackboardSync")
    drive_service.mirror_tree.assert_called_once_with(download_dir, "new-root")
    assert config.drive_folder_id == "new-root"


def test_changing_credentials_clears_token_and_cached_root(tmp_path, monkeypatch):
    config, _ = make_sync_config(tmp_path)
    old_credentials = tmp_path / "old.json"
    new_credentials = tmp_path / "new.json"
    old_credentials.write_text("{}")
    new_credentials.write_text("{}")

    config.drive_credentials_path = old_credentials
    config.drive_folder_id = "root-folder"
    token_path = config.drive_token_path
    token_path.write_text("token")

    created_services = []

    class DummyDriveService:
        def __init__(self, credentials_path: Path, token_path: Path):
            self.credentials_path = credentials_path
            self.token_path = token_path
            created_services.append(self)

    monkeypatch.setattr("blackboard_sync.sync.DriveService", DummyDriveService)

    sync = make_sync(config, object())
    sync.drive_credentials_path = str(new_credentials)

    assert config.drive_credentials_path == new_credentials
    assert config.drive_folder_id is None
    assert not token_path.exists()
    assert created_services[0].credentials_path == new_credentials
    assert created_services[0].token_path == token_path


def test_setting_same_credentials_keeps_token_and_root(tmp_path, monkeypatch):
    config, _ = make_sync_config(tmp_path)
    credentials = tmp_path / "drive.json"
    credentials.write_text("{}")

    config.drive_credentials_path = credentials
    config.drive_folder_id = "root-folder"
    token_path = config.drive_token_path
    token_path.write_text("token")

    created_services = []

    class DummyDriveService:
        def __init__(self, credentials_path: Path, token_path: Path):
            self.credentials_path = credentials_path
            self.token_path = token_path
            created_services.append(self)

    monkeypatch.setattr("blackboard_sync.sync.DriveService", DummyDriveService)

    sync = make_sync(config, object())
    sync.drive_credentials_path = str(credentials)

    assert config.drive_folder_id == "root-folder"
    assert token_path.exists()
    assert created_services[0].credentials_path == credentials
    assert created_services[0].token_path == token_path
