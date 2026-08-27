from unittest import mock
from datetime import datetime, timezone
from types import SimpleNamespace

from blackboard_sync.sync_controller import SyncController


def make_controller():
    controller = SyncController.__new__(SyncController)
    controller.model = mock.Mock()
    controller.ui = mock.Mock()
    controller._pending_setup_course_selection = False
    controller.open_login = mock.Mock()
    controller.check_for_updates = mock.Mock()
    return controller


def test_setup_marks_pending_course_selection():
    controller = make_controller()

    SyncController.setup(controller, 2, "C:/Downloads", 2025)

    controller.model.setup.assert_called_once_with(2, "C:/Downloads", 2025)
    controller.open_login.assert_called_once()
    assert controller._pending_setup_course_selection is True


def test_mcp_course_file_map_uses_year_and_course_folder(tmp_path):
    controller = make_controller()
    course = SimpleNamespace(
        id="course-1",
        title="Economia",
        name="Economia",
        created=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    controller.model.list_available_courses.return_value = [course]
    controller.model.download_location = tmp_path
    material = tmp_path / "2026" / "Economia" / "Semana 1" / "guia.pdf"
    material.parent.mkdir(parents=True)
    material.write_bytes(b"material")

    result = SyncController._mcp_get_course_files(controller, "course-1")

    assert result["local_path"] == str(tmp_path / "2026" / "Economia")
    assert result["file_count"] == 1
    assert result["files"][0]["path"] == str(
        material.relative_to(tmp_path / "2026" / "Economia")
    )


def test_mcp_course_sync_is_one_time_request():
    controller = make_controller()

    SyncController._mcp_sync_course(controller, "course-1")

    controller.model.force_sync.assert_called_once_with({"course-1"})


def test_log_in_setup_flow_shows_course_selection_and_starts_sync():
    controller = make_controller()
    controller._pending_setup_course_selection = True
    controller.model.auth.return_value = True
    controller.model.list_available_courses_summary.return_value = [
        {"id": "course-1", "name": "Course 1"}
    ]
    controller.model.selected_course_ids = []
    controller.model.course_sync_status = {}
    controller.ui.ask_course_selection.return_value = ["course-1"]

    cookies = mock.Mock()
    SyncController.log_in(controller, cookies=cookies)

    controller.model.auth.assert_called_once_with(cookies, start_sync=False)
    controller.ui.ask_course_selection.assert_called_once_with(
        [{"id": "course-1", "name": "Course 1"}], [], {}
    )
    assert controller.model.selected_course_ids == ["course-1"]
    controller.model.start_sync.assert_called_once()
    controller.ui.log_in.assert_called_once()
    controller.ui.notify_running.assert_called_once()
    controller.check_for_updates.assert_called_once()
    assert controller._pending_setup_course_selection is False


def test_log_in_without_setup_does_not_show_course_selection():
    controller = make_controller()
    controller.model.auth.return_value = True

    SyncController.log_in(controller, cookies=mock.Mock())

    controller.ui.ask_course_selection.assert_not_called()
    controller.model.start_sync.assert_called_once()


def test_log_in_failure_notifies_error():
    controller = make_controller()
    controller.model.auth.return_value = False

    SyncController.log_in(controller, cookies=mock.Mock())

    controller.ui.notify_login_error.assert_called_once()
    controller.model.start_sync.assert_not_called()
