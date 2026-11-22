from unittest import mock

import requests

from blackboard_sync import updates


def test_check_for_updates_uses_fork_release_url():
    response = mock.Mock()
    response.json.return_value = {"tag_name": "v9.9.9"}

    with (
        mock.patch("blackboard_sync.updates.__version__", "1.0.0"),
        mock.patch("blackboard_sync.updates.requests.get", return_value=response) as get,
    ):
        assert updates.check_for_updates()

    get.assert_called_once_with(
        "https://api.github.com/repos/johnbarraza/UPBlackboardSync/releases/latest",
        timeout=20,
    )
    response.raise_for_status.assert_called_once()


def test_check_for_updates_returns_false_on_network_error():
    with (
        mock.patch("blackboard_sync.updates.__version__", "1.0.0"),
        mock.patch(
            "blackboard_sync.updates.requests.get",
            side_effect=requests.Timeout,
        ),
    ):
        assert not updates.check_for_updates()


def test_check_for_updates_returns_false_on_invalid_release_payload():
    response = mock.Mock()
    response.json.return_value = {}

    with (
        mock.patch("blackboard_sync.updates.__version__", "1.0.0"),
        mock.patch("blackboard_sync.updates.requests.get", return_value=response),
    ):
        assert not updates.check_for_updates()


def _release(digest, url=None, tag="v9.9.9"):
    url = url or ("https://github.com/johnbarraza/UPBlackboardSync/"
                  "releases/download/v9.9.9/BlackboardSync-Setup.exe")
    meta = mock.Mock()
    meta.json.return_value = {"tag_name": tag, "assets": [
        {"name": "BlackboardSync-Setup.exe", "browser_download_url": url,
         "digest": digest}]}
    blob = mock.MagicMock()
    blob.__enter__.return_value.iter_content.return_value = [b"setup-", b"bytes"]
    return [meta, blob]


def _download(responses):
    with (
        mock.patch("blackboard_sync.updates.__version__", "1.0.0"),
        mock.patch("blackboard_sync.updates.requests.get", side_effect=responses),
    ):
        return updates.download_installer()


def test_download_installer_verifies_sha256():
    import hashlib
    good = "sha256:" + hashlib.sha256(b"setup-bytes").hexdigest()

    path = _download(_release(good))

    assert path is not None and path.read_bytes() == b"setup-bytes"
    assert path.name == "BlackboardSync-Setup.exe"


def test_download_installer_rejects_bad_digest_url_or_old_release():
    assert _download(_release("sha256:" + "0" * 64)) is None
    good = "sha256:" + __import__("hashlib").sha256(b"setup-bytes").hexdigest()
    assert _download(_release(good, url="https://evil.example/Setup.exe")) is None
    assert _download(_release(good, tag="v0.1.0")) is None
    assert _download(_release(None)) is None  # no digest published


def test_portable_is_not_installed():
    assert not updates.is_installed()  # tests never run frozen
