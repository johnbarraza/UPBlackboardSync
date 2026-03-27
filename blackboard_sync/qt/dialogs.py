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

import webbrowser
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import QObject, Qt
from PyQt6.QtWidgets import (
    QMessageBox,
    QFileDialog,
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QHBoxLayout,
    QWidget,
)

from .assets import logo


class DirDialog(QFileDialog):
    """Open the file dialog in directory mode."""
    def init(self) -> None:
        super().__init__()

    def choose(self) -> Path | None:
        self.setFileMode(QFileDialog.FileMode.Directory)
        if super().exec():
            return Path(self.directory().path())
        return None


class FileDialog(QFileDialog):
    """Open the file dialog in existing-file mode."""

    def choose(self, file_filter: str = "") -> tuple[str, str]:
        self.setFileMode(QFileDialog.FileMode.ExistingFile)
        if file_filter:
            self.setNameFilter(file_filter)

        if super().exec():
            selected = self.selectedFiles()
            if selected:
                return selected[0], self.selectedNameFilter()

        return "", self.selectedNameFilter()


class CourseSelectionDialog(QDialog):
    def __init__(self,
                 courses: list[dict[str, str]],
                 selected_course_ids: list[str],
                 course_sync_status: dict[str, datetime],
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Select courses to sync"))
        self.setWindowIcon(logo())
        self.resize(620, 460)

        self._list = QListWidget(self)
        selected = set(selected_course_ids)

        for course in courses:
            course_id = course.get('id', '')
            course_name = course.get('name', course_id)
            synced = course_sync_status.get(course_id)
            synced_label = (
                synced.astimezone().strftime('%Y-%m-%d %H:%M')
                if synced else self.tr("Never")
            )
            text = f"{course_name}  |  {self.tr('Last sync')}: {synced_label}"

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, course_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if (not selected or course_id in selected)
                else Qt.CheckState.Unchecked
            )
            self._list.addItem(item)

        info = QLabel(self.tr("Choose which courses should be synchronized."))
        info.setWordWrap(True)

        select_all_button = QPushButton(self.tr("Select all"))
        select_all_button.clicked.connect(self._select_all)

        clear_button = QPushButton(self.tr("Clear"))
        clear_button.clicked.connect(self._clear)

        action_row = QHBoxLayout()
        action_row.addWidget(select_all_button)
        action_row.addWidget(clear_button)
        action_row.addStretch(1)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self._try_accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addLayout(action_row)
        layout.addWidget(self._list)
        layout.addWidget(self._buttons)
        self.setLayout(layout)

    @property
    def selected_course_ids(self) -> list[str]:
        selected: list[str] = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is None:
                continue
            if item.checkState() == Qt.CheckState.Checked:
                course_id = item.data(Qt.ItemDataRole.UserRole)
                if course_id:
                    selected.append(str(course_id))
        return selected

    def _select_all(self) -> None:
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is None:
                continue
            item.setCheckState(Qt.CheckState.Checked)

    def _clear(self) -> None:
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is None:
                continue
            item.setCheckState(Qt.CheckState.Unchecked)

    def _try_accept(self) -> None:
        if not self.selected_course_ids:
            QMessageBox.warning(
                self,
                self.tr("No courses selected"),
                self.tr("Select at least one course to continue.")
            )
            return
        self.accept()


class Dialogs(QObject):
    def __init__(self) -> None:
        super().__init__()

    def redownload_dialog(self) -> bool:
        q = QMessageBox()
        q.setText(self.tr("Do you wish to redownload all files?"))
        q.setInformativeText(self.tr(
            "Answer no if you intend to move all past downloads manually"
            " (Recommended)."
        ))
        q.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        q.setDefaultButton(QMessageBox.StandardButton.No)
        q.setIcon(QMessageBox.Icon.Question)
        q.setWindowIcon(logo())
        return q.exec() == QMessageBox.StandardButton.Yes

    def uni_not_supported_dialog(self, url: str) -> None:
        q = QMessageBox()
        q.setText(self.tr(
            "Unfortunately, your university is not yet supported"
        ))
        q.setInformativeText(self.tr(
            "You can help us provide support for it by visiting our website, "
            "which you can access by pressing the help button."
        ))
        q.setStandardButtons(
            QMessageBox.StandardButton.Help | QMessageBox.StandardButton.Ok
        )
        q.setIcon(QMessageBox.Icon.Warning)
        q.setWindowIcon(logo())

        if q.exec() == QMessageBox.StandardButton.Help:
            webbrowser.open(url)

    def login_error_dialog(self, url: str) -> None:
        q = QMessageBox()
        q.setText(self.tr(
            "There was an issue logging you in"
        ))
        q.setInformativeText(self.tr(
            "Please try again later, and if the error persists"
            " contact our support by pressing the button below."
        ))
        q.setStandardButtons(
            QMessageBox.StandardButton.Help | QMessageBox.StandardButton.Ok
        )
        q.setIcon(QMessageBox.Icon.Warning)
        q.setWindowIcon(logo())

        if q.exec() == QMessageBox.StandardButton.Help:
            webbrowser.open(url)
