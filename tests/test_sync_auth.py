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


def _sync_with_download(tmp_path, monkeypatch, *effects):
    sync = BlackboardSync.__new__(BlackboardSync)
    sync.sess = object()
    sync.university = object()
    sync._is_active = True
    sync._download = None
    sync._next_sync = None
    sync._sync_interval = 60
    sync._offline_since = None
    sync.last_error = None
    sync._auth_required_callback = mock.Mock()
    sync.stop_sync = mock.Mock()
    sync._config = SimpleNamespace(
        download_location=tmp_path, last_sync_time=None, min_year=None,
        selected_course_ids=[], course_sync_status={}
    )
    fake = mock.Mock()
    fake.download.side_effect = list(effects)
    fake.cancelled = False
    monkeypatch.setattr("blackboard_sync.sync.BlackboardDownload",
                        mock.Mock(return_value=fake))
    return sync


def test_download_unauthorized_requests_login(tmp_path, monkeypatch, caplog):
    from blackboard.exceptions import BBUnauthorizedError
    sync = _sync_with_download(tmp_path, monkeypatch, BBUnauthorizedError())

    BlackboardSync.download(sync)

    sync._auth_required_callback.assert_called_once()
    assert sync.last_error == "auth"
    assert "another location" in caplog.text


def test_unauthorized_after_outage_logs_inactivity(tmp_path, monkeypatch, caplog):
    from requests.exceptions import ConnectTimeout
    from blackboard.exceptions import BBUnauthorizedError
    sync = _sync_with_download(tmp_path, monkeypatch,
                               ConnectTimeout(), BBUnauthorizedError())

    BlackboardSync.download(sync)
    assert sync.last_error == "network"
    BlackboardSync.download(sync)

    assert sync.last_error == "auth"
    assert "inactivity" in caplog.text
    assert "another location" not in caplog.text
