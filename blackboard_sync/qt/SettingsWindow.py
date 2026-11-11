# Copyright (C) 2024, Jacob Sánchez Pérez

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

from enum import IntEnum
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import pyqtSlot, pyqtSignal, QObject
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtWidgets import (QComboBox, QPushButton, QDialogButtonBox,
                             QCheckBox, QSpinBox, QLineEdit, QBoxLayout)

from .assets import load_ui
from .dialogs import DirDialog, FileDialog, CourseSelectionDialog
from blackboard_sync.__about__ import __title__, __uri__
from blackboard_sync import credentials


class SettingsWindow(QWidget):
    """Tweaks main application preferences."""

    class SyncPeriod(IntEnum):
        HALF_HOUR = 60 * 30
        ONE_HOUR = 60 * 60
        SIX_HOURS = 60 * 60 * 6

    class Signals(QObject):
        log_out = pyqtSignal()
        setup_wiz = pyqtSignal()
        save = pyqtSignal()
        auth_drive = pyqtSignal()
        open_diagnostics = pyqtSignal()
        reconnect = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        # Typing information
        self.frequency_combo: QComboBox
        self.current_session_label: QLabel
        self.download_location_hint: QLabel
        self.version_label: QLabel
        self.select_download_location: QPushButton
        self.log_out_button: QPushButton
        self.setup_button: QPushButton
        self.nerd_stats_button: QPushButton
        self.reconnect_button: QPushButton
        self.button_box: QDialogButtonBox

        # Backup widgets
        self.select_backup_location: QPushButton
        self.enable_backup: QCheckBox
        self.backup_location_hint: QLabel

        # Drive widgets
        self.drive_label: QLabel
        self.enable_drive: QCheckBox
        self.select_credentials: QPushButton
        self.drive_auth_button: QPushButton
        self.drive_status_label: QLabel

        # Course selection
        self.select_courses_button: QPushButton
        self.selected_courses_hint: QLabel

        # MCP widgets
        self.enable_mcp: QCheckBox
        self.mcp_port_input: QSpinBox
        self.mcp_port_label: QLabel
        self.mcp_hint: QLabel
        self.mcp_label: QLabel

        self.signals = self.Signals()
        self._data_source = ""
        # Google Drive integration is not shipping yet; presented as
        # "coming soon" and kept fully disabled so no OAuth flow can run.
        self._drive_coming_soon = True
        self._credentials_path: Path | None = None
        self._available_courses: list[dict[str, str]] = []
        self._selected_course_ids: list[str] = []
        self._course_sync_status: dict[str, datetime] = {}

        self._init_ui()

    def _init_ui(self) -> None:
        load_ui(self)

        # Slots
        self.select_download_location.clicked.connect(self._choose_location)
        self.select_backup_location.clicked.connect(
            self._choose_backup_location
        )
        self.enable_backup.toggled.connect(self._toggle_backup)
        self.enable_mcp.toggled.connect(self._toggle_mcp)
        self.select_credentials.clicked.connect(self._choose_credentials)
        self.drive_auth_button.clicked.connect(self.signals.auth_drive)
        self.enable_drive.toggled.connect(self._toggle_drive)
        self.select_courses_button.clicked.connect(self._choose_courses)

        # Signals
        self.log_out_button.clicked.connect(self.signals.log_out)
        self.setup_button.clicked.connect(self.signals.setup_wiz)
        self.nerd_stats_button.clicked.connect(self.signals.open_diagnostics)
        self.reconnect_button.clicked.connect(self.signals.reconnect)
        self.button_box.accepted.connect(self.signals.save)

        if self._drive_coming_soon:
            self._apply_drive_coming_soon()

        self._init_saved_login()

    def _init_saved_login(self) -> None:
        """Opt-in 'remember my login' section, added under MCP."""
        self.save_login = QCheckBox(self.tr(
            "Save username and password to log in again automatically"))
        self.login_user = QLineEdit()
        self.login_user.setPlaceholderText(self.tr("Username"))
        self.login_password = QLineEdit()
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        hint = QLabel(self.tr(
            "Stored encrypted in the system credential manager, never in "
            "the config file. Untick to delete it."))
        hint.setWordWrap(True)
        hint.setFont(self.mcp_hint.font())
        title = QLabel(self.tr("Automatic login"))
        title.setFont(self.mcp_label.font())

        # the (nested) layout that holds the MCP section
        layout = next(lay for lay in self.findChildren(QBoxLayout)
                      if lay.indexOf(self.mcp_hint) >= 0)
        at = layout.indexOf(self.mcp_hint) + 1
        layout.insertSpacing(at, 16)
        at += 1
        for i, w in enumerate((title, self.save_login, self.login_user,
                               self.login_password, hint)):
            layout.insertWidget(at + i, w)

        self.save_login.toggled.connect(self.login_user.setEnabled)
        self.save_login.toggled.connect(self.login_password.setEnabled)
        self.button_box.accepted.connect(self._store_login)
        self.load_saved_login()

    def load_saved_login(self) -> None:
        saved = credentials.load()
        self.save_login.setChecked(saved is not None)
        self.login_user.setEnabled(saved is not None)
        self.login_password.setEnabled(saved is not None)
        self.login_user.setText(saved[0] if saved else "")
        # never put the stored password back on screen
        self.login_password.clear()
        self.login_password.setPlaceholderText(
            self.tr("Saved — type to change") if saved
            else self.tr("Password"))

    @pyqtSlot()
    def _store_login(self) -> None:
        if not self.save_login.isChecked():
            credentials.clear()
            return
        user = self.login_user.text().strip()
        password = self.login_password.text()
        if not password:  # keep the saved one unless a new one was typed
            saved = credentials.load()
            password = saved[1] if saved else ""
        if user and password:
            credentials.save(user, password)
        self.load_saved_login()

    def _apply_drive_coming_soon(self) -> None:
        """Disable the Google Drive section and mark it as coming soon."""
        self.drive_label.setText(
            self.tr("Google Drive Integration (coming soon)")
        )
        self.enable_drive.setChecked(False)
        self.enable_drive.setEnabled(False)
        self.select_credentials.setEnabled(False)
        self.drive_auth_button.setEnabled(False)
        self.drive_status_label.setText(self.tr("Coming soon"))

        tip = self.tr("Google Drive sync is coming soon.")
        for widget in (self.enable_drive, self.select_credentials,
                       self.drive_auth_button, self.drive_status_label):
            widget.setToolTip(tip)

    @pyqtSlot()
    def _choose_location(self) -> None:
        location = DirDialog().choose()

        if location is not None:
            self.download_location = location

    @pyqtSlot()
    def _choose_backup_location(self) -> None:
        location = DirDialog().choose()
        if location is not None:
            self.backup_location = location

    @pyqtSlot(bool)
    def _toggle_backup(self, checked: bool) -> None:
        self.select_backup_location.setEnabled(checked)
        self.backup_location_hint.setEnabled(checked)

    @pyqtSlot(bool)
    def _toggle_mcp(self, checked: bool) -> None:
        self.mcp_port_label.setEnabled(checked)
        self.mcp_port_input.setEnabled(checked)
        self.mcp_hint.setEnabled(checked)

    @pyqtSlot(bool)
    def _toggle_drive(self, checked: bool) -> None:
        self.select_credentials.setEnabled(checked)
        self.drive_auth_button.setEnabled(checked)

    @pyqtSlot()
    def _choose_credentials(self) -> None:
        file, _ = FileDialog().choose("JSON Files (*.json)")
        if file:
            self.drive_credentials_path = Path(file)

    @pyqtSlot()
    def _choose_courses(self) -> None:
        dialog = CourseSelectionDialog(
            self._available_courses,
            self._selected_course_ids,
            self._course_sync_status,
            self
        )
        if dialog.exec():
            self._selected_course_ids = dialog.result_ids
            self._update_course_selection_hint()

    @property
    def mcp_enabled(self) -> bool:
        return self.enable_mcp.isChecked()

    @mcp_enabled.setter
    def mcp_enabled(self, enabled: bool) -> None:
        self.enable_mcp.setChecked(enabled)
        self._toggle_mcp(enabled)

    @property
    def mcp_port(self) -> int:
        return self.mcp_port_input.value()

    @mcp_port.setter
    def mcp_port(self, port: int) -> None:
        self.mcp_port_input.setValue(port)

    @property
    def drive_enabled(self) -> bool:
        if self._drive_coming_soon:
            return False
        return self.enable_drive.isChecked()

    @drive_enabled.setter
    def drive_enabled(self, enabled: bool) -> None:
        if self._drive_coming_soon:
            return
        self.enable_drive.setChecked(enabled)
        self._toggle_drive(enabled)

    @property
    def drive_credentials_path(self) -> Path | None:
        return self._credentials_path

    @drive_credentials_path.setter
    def drive_credentials_path(self, path: Path | None) -> None:
        self._credentials_path = path

    def set_drive_status(self, email: str | None) -> None:
        if self._drive_coming_soon:
            self.drive_status_label.setText(self.tr("Coming soon"))
            return
        if email:
            self.drive_status_label.setText(f"Connected as {email}")
        else:
            self.drive_status_label.setText("Not connected")

    @property
    def backup_location(self) -> Path | None:
        if not self.backup_location_hint.text():
            return None
        return Path(self.backup_location_hint.text())

    @backup_location.setter
    def backup_location(self, location: Path | None) -> None:
        if location:
            self.backup_location_hint.setText(str(location.resolve()))
        else:
            self.backup_location_hint.setText("")

    @property
    def backup_enabled(self) -> bool:
        return self.enable_backup.isChecked()

    @backup_enabled.setter
    def backup_enabled(self, enabled: bool) -> None:
        self.enable_backup.setChecked(enabled)
        self._toggle_backup(enabled)

    @property
    def download_location(self) -> Path:
        """Current download location."""
        return self._download_location

    @download_location.setter
    def download_location(self, location: Path) -> None:
        self._download_location = location.resolve()
        self.download_location_hint.setText(str(self._download_location))

    @property
    def sync_frequency(self) -> int:
        """Seconds to wait between each sync job."""
        options = list(self.SyncPeriod)
        return int(options[self.frequency_combo.currentIndex()])

    @sync_frequency.setter
    def sync_frequency(self, s: int) -> None:
        options = list(self.SyncPeriod)
        current = options.index(self.SyncPeriod(s))
        self.frequency_combo.setCurrentIndex(current)

    @property
    def username(self) -> str:
        """Username of current session."""
        return self.current_session_label.text()

    @username.setter
    def username(self, username: str) -> None:
        if username:
            self.current_session_label.setText(
                self.tr("Logged in as ") + username)
        else:
            self.current_session_label.setText(
                self.tr("Not currently logged in"))

    def set_connection_status(self, logged_in: bool) -> None:
        self.reconnect_button.setVisible(not logged_in)

    @property
    def version(self) -> str | None:
        return self.version_label.text()

    @version.setter
    def version(self, value: str | None) -> None:
        if value is None:
            value = self.tr("No version detected")
        self.version_label.setOpenExternalLinks(True)
        repository_link = (
            f'<a href="{__uri__}">Repositorio GitHub</a>'
        )
        self.version_label.setText(
            f'{__title__} v{value} · {repository_link}'
        )
        self.version_label.setToolTip(__uri__)

    @property
    def data_source(self) -> str:
        return self._data_source

    @data_source.setter
    def data_source(self, value: str) -> None:
        self._data_source = value

    @property
    def selected_course_ids(self) -> list[str]:
        return self._selected_course_ids

    @selected_course_ids.setter
    def selected_course_ids(self, value: list[str]) -> None:
        self._selected_course_ids = [
            course_id for course_id in value if course_id
        ]
        self._update_course_selection_hint()

    def set_courses(self,
                    courses: list[dict[str, str]],
                    selected_course_ids: list[str],
                    course_sync_status: dict[str, datetime]) -> None:
        self._available_courses = courses
        self._course_sync_status = course_sync_status
        self._selected_course_ids = [
            course_id for course_id in selected_course_ids if course_id
        ]
        self.select_courses_button.setEnabled(bool(self._available_courses))
        self._update_course_selection_hint()

    def _update_course_selection_hint(self) -> None:
        total = len(self._available_courses)
        available_ids = {
            course.get('id') for course in self._available_courses
        }
        selected = (
            len(available_ids.intersection(self._selected_course_ids))
            if self._selected_course_ids else total
        )
        if total <= 0:
            self.selected_courses_hint.setText(
                self.tr("No courses loaded yet")
            )
            return

        if selected >= total:
            self.selected_courses_hint.setText(
                self.tr("All courses (%1)").replace("%1", str(total)))
        else:
            self.selected_courses_hint.setText(
                self.tr("Selected courses: %1/%2")
                .replace("%1", str(selected)).replace("%2", str(total)))
