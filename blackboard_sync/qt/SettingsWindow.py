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
from PyQt6.QtWidgets import QComboBox, QPushButton, QDialogButtonBox, QCheckBox

from .assets import load_ui
from .dialogs import DirDialog, FileDialog, CourseSelectionDialog


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
        self.button_box: QDialogButtonBox

        # Backup widgets
        self.select_backup_location: QPushButton
        self.enable_backup: QCheckBox
        self.backup_location_hint: QLabel

        # Drive widgets
        self.enable_drive: QCheckBox
        self.select_credentials: QPushButton
        self.drive_auth_button: QPushButton
        self.drive_status_label: QLabel

        # Course selection
        self.select_courses_button: QPushButton
        self.selected_courses_hint: QLabel

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
        self.select_credentials.clicked.connect(self._choose_credentials)
        self.drive_auth_button.clicked.connect(self.signals.auth_drive)
        self.enable_drive.toggled.connect(self._toggle_drive)
        self.select_courses_button.clicked.connect(self._choose_courses)

        # Signals
        self.log_out_button.clicked.connect(self.signals.log_out)
        self.setup_button.clicked.connect(self.signals.setup_wiz)
        self.button_box.accepted.connect(self.signals.save)

        if self._drive_coming_soon:
            self._apply_drive_coming_soon()

    def _apply_drive_coming_soon(self) -> None:
        """Lock the Google Drive section as a disabled 'coming soon' feature."""
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
            self._selected_course_ids = dialog.selected_course_ids
            self._update_course_selection_hint()

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

    @property
    def version(self) -> str | None:
        return self.version_label.text()

    @version.setter
    def version(self, value: str | None) -> None:
        if value is None:
            value = self.tr("No version detected")
        self.version_label.setText(value)

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
            self.selected_courses_hint.setText(f"All courses ({total})")
        else:
            self.selected_courses_hint.setText(
                f"Selected courses: {selected}/{total}"
            )
