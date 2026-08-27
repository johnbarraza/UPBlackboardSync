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
