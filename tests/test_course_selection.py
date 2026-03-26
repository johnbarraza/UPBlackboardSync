from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from blackboard_sync.config import SyncConfig
from blackboard_sync.download import BlackboardDownload


def make_sync_config(tmp_path: Path) -> SyncConfig:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return SyncConfig(config_dir)


def test_selected_course_ids_roundtrip(tmp_path):
    config = make_sync_config(tmp_path)

    config.selected_course_ids = ["course-b", "course-a", "course-a"]
    assert config.selected_course_ids == ["course-a", "course-b"]

    config.selected_course_ids = []
    assert config.selected_course_ids == []


def test_course_sync_status_roundtrip(tmp_path):
    config = make_sync_config(tmp_path)
    now = datetime.now(timezone.utc).replace(microsecond=0)

    config.course_sync_status = {"course-1": now}
    saved = config.course_sync_status

    assert "course-1" in saved
    assert saved["course-1"] == now


def test_download_filters_selected_courses_and_reports_status(tmp_path):
    course_1 = SimpleNamespace(id="course-1")
    course_2 = SimpleNamespace(id="course-2")
    sess = mock.Mock()
    sess.user_id = "user-1"
    sess.ex_fetch_courses.return_value = [course_1, course_2]

    synced_courses: list[str] = []

    def on_synced(course_id: str, _sync_time: datetime) -> None:
        synced_courses.append(course_id)

    downloader = BlackboardDownload(
        sess=sess,
        download_location=tmp_path / "downloads",
        selected_course_ids={"course-2"},
        course_synced_callback=on_synced
    )

    with mock.patch("blackboard_sync.download.Course") as course_cls:
        course_cls.return_value.write.return_value = None
        downloader.download()

    assert course_cls.call_count == 1
    assert course_cls.call_args_list[0].args[0].id == "course-2"
    assert synced_courses == ["course-2"]


def test_download_uses_course_specific_last_synced(tmp_path):
    course = SimpleNamespace(
        id="course-2",
        created=datetime(2026, 1, 1, tzinfo=timezone.utc),
        title="Course 2"
    )
    sess = mock.Mock()
    sess.user_id = "user-1"
    sess.ex_fetch_courses.return_value = [course]
    last_synced = datetime(2026, 1, 10, tzinfo=timezone.utc)
    download_dir = tmp_path / "downloads"
    existing_dir = download_dir / "2026" / "Course 2"
    existing_dir.mkdir(parents=True)
    (existing_dir / "already-synced.url").write_text("ok", encoding="utf-8")

    downloader = BlackboardDownload(
        sess=sess,
        download_location=download_dir,
        selected_course_ids={"course-2"},
        course_last_synced={"course-2": last_synced}
    )

    with (mock.patch("blackboard_sync.download.Course") as course_cls,
          mock.patch("blackboard_sync.download.DownloadJob") as job_cls):
        course_cls.return_value.write.return_value = None
        downloader.download()

    assert job_cls.call_args.kwargs["last_downloaded"] == last_synced


def test_course_marked_synced_with_empty_folder_downloads_fully(tmp_path):
    course = SimpleNamespace(
        id="course-2",
        created=datetime(2026, 1, 1, tzinfo=timezone.utc),
        title="Course 2"
    )
    sess = mock.Mock()
    sess.user_id = "user-1"
    sess.ex_fetch_courses.return_value = [course]
    last_synced = datetime(2026, 1, 10, tzinfo=timezone.utc)
    download_dir = tmp_path / "downloads"
    (download_dir / "2026" / "Course 2").mkdir(parents=True)

    downloader = BlackboardDownload(
        sess=sess,
        download_location=download_dir,
        selected_course_ids={"course-2"},
        course_last_synced={"course-2": last_synced}
    )

    with (mock.patch("blackboard_sync.download.Course") as course_cls,
          mock.patch("blackboard_sync.download.DownloadJob") as job_cls):
        course_cls.return_value.write.return_value = None
        downloader.download()

    assert job_cls.call_args.kwargs["last_downloaded"] is None


def test_selected_course_without_history_downloads_fully(tmp_path):
    course = SimpleNamespace(id="course-2")
    sess = mock.Mock()
    sess.user_id = "user-1"
    sess.ex_fetch_courses.return_value = [course]

    downloader = BlackboardDownload(
        sess=sess,
        download_location=tmp_path / "downloads",
        selected_course_ids={"course-2"},
        course_last_synced={}
    )

    with (mock.patch("blackboard_sync.download.Course") as course_cls,
          mock.patch("blackboard_sync.download.DownloadJob") as job_cls):
        course_cls.return_value.write.return_value = None
        downloader.download()

    assert job_cls.call_args.kwargs["last_downloaded"] is None


def test_download_returns_none_when_file_downloads_fail(tmp_path):
    course = SimpleNamespace(id="course-2")
    sess = mock.Mock()
    sess.user_id = "user-1"
    sess.ex_fetch_courses.return_value = [course]

    synced_courses: list[str] = []

    def on_synced(course_id: str, _sync_time: datetime) -> None:
        synced_courses.append(course_id)

    downloader = BlackboardDownload(
        sess=sess,
        download_location=tmp_path / "downloads",
        selected_course_ids={"course-2"},
        course_synced_callback=on_synced
    )
    downloader.executor.raise_exceptions = mock.Mock(return_value=1)

    with mock.patch("blackboard_sync.download.Course") as course_cls:
        course_cls.return_value.write.return_value = None
        result = downloader.download()

    assert result is None
    assert synced_courses == []
