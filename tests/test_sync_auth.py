from types import SimpleNamespace
from unittest import mock

from blackboard_sync.sync import BlackboardSync


def test_auth_sets_api_timeout_and_retries(monkeypatch):
    sync = BlackboardSync.__new__(BlackboardSync)
    sync.university = SimpleNamespace(api_url="https://example.edu")
    sync._is_logged_in = False
    sync.start_sync = mock.Mock()

    fake_session = mock.Mock()
    fake_session.fetch_users.return_value = {"id": "me"}

    session_factory = mock.Mock(return_value=fake_session)
    monkeypatch.setattr("blackboard_sync.sync.BlackboardExtended",
                        session_factory)

    assert BlackboardSync.auth(sync, cookies=mock.Mock()) is True
    assert getattr(fake_session, "__api_timeout") == (30, 300)
    assert getattr(fake_session, "__api_max_retries") == 3


def test_download_schedules_next_retry_when_partial_failure(tmp_path, monkeypatch):
    sync = BlackboardSync.__new__(BlackboardSync)
    sync.sess = object()
    sync.university = object()
    sync._is_active = True
    sync._download = None
    sync._next_sync = None
    sync._sync_interval = 60
    sync._config = SimpleNamespace(
        download_location=tmp_path,
        last_sync_time=None,
        min_year=None,
        selected_course_ids=[],
        course_sync_status={}
    )

    fake_download = mock.Mock()
    fake_download.download.return_value = None
    fake_download.cancelled = False

    monkeypatch.setattr("blackboard_sync.sync.BlackboardDownload",
                        mock.Mock(return_value=fake_download))

    assert BlackboardSync.download(sync) is None
    assert sync.next_sync is not None


def test_auth_does_not_start_sync_when_disabled(monkeypatch):
    sync = BlackboardSync.__new__(BlackboardSync)
    sync.university = SimpleNamespace(api_url="https://example.edu")
    sync._is_logged_in = False
    sync.start_sync = mock.Mock()

    fake_session = mock.Mock()
    fake_session.fetch_users.return_value = {"id": "me"}

    session_factory = mock.Mock(return_value=fake_session)
    monkeypatch.setattr("blackboard_sync.sync.BlackboardExtended",
                        session_factory)

    assert BlackboardSync.auth(sync, cookies=mock.Mock(), start_sync=False) is True
    sync.start_sync.assert_not_called()
