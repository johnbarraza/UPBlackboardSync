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

from datetime import datetime
import webbrowser

from PyQt6.QtGui import QAction
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from .assets import logo, get_theme_icon, AppIcon
from .utils import time_ago
from .notification import Event, TrayMessages
from blackboard_sync.__about__ import __title__, __uri__, __version__


class SyncTrayMenu(QMenu):

    def __init__(self, logged_in: bool = False,
                 last_synced: datetime | None = None):
        super().__init__()
        self._last_synced: datetime | None = None
        self._logged_in = logged_in
        self._syncing = False
        self._auth_required = False

        self._init_ui()
        self.set_last_synced(last_synced)
        self.set_logged_in(logged_in)

    def _init_ui(self) -> None:
        sync_icon = get_theme_icon(AppIcon.SYNC)
        close_icon = get_theme_icon(AppIcon.EXIT)
        open_dir_icon = get_theme_icon(AppIcon.OPEN)

        self._status = QAction(self.tr("Status: not logged in"))
        self.addAction(self._status)
        self.addSeparator()

        self.refresh = QAction(self.tr("Sync now"))
        self.refresh.setIcon(sync_icon)
        self.addAction(self.refresh)

        self.open_dir = QAction(self.tr("Open downloads"))
        self.open_dir.setIcon(open_dir_icon)
        self.addAction(self.open_dir)

        self.preferences = QAction(self.tr("Preferences"))
        self.addAction(self.preferences)

        self.addSeparator()

        self.repository = QAction(f"{__title__} v{__version__} · GitHub")
        self.repository.setToolTip(__uri__)
        self.repository.triggered.connect(lambda: webbrowser.open(__uri__))
        self.addAction(self.repository)

        self.reset_setup = QAction(self.tr("Setup"))
        self.addAction(self.reset_setup)

        self.quit = QAction(self.tr("Quit"))
        self.quit.setIcon(close_icon)
        self.addAction(self.quit)

    def set_logged_in(self, logged_in: bool) -> None:
        self._logged_in = logged_in
        self.refresh.setVisible(logged_in)
        self.preferences.setVisible(logged_in)
        self.reset_setup.setVisible(not logged_in)
        self.open_dir.setVisible(logged_in)

        self._update_status()

    def set_last_synced(self, last_synced: datetime | None) -> None:
        self._last_synced = last_synced
        self._update_status()

    def set_currently_syncing(self, syncing: bool) -> None:
        self._syncing = syncing
        self.refresh.setEnabled(not syncing)
        self._update_status()

    def set_auth_required(self, auth_required: bool) -> None:
        self._auth_required = auth_required
        self._update_status()

    def _update_status(self) -> None:
        if self._auth_required:
            text = self.tr("Status: login required — reconnect to Blackboard")
        elif not self._logged_in:
            text = self.tr("Status: not logged in")
        elif self._syncing:
            text = self.tr("Status: synchronizing now...")
        elif self._last_synced:
            text = self.tr("Status: connected · Last synced: ") + time_ago(
                self._last_synced
            )
        else:
            text = self.tr("Status: connected · Not synchronized yet")
        self._status.setText(text)


class SyncTrayIcon(QSystemTrayIcon):
    """Control the application from the system tray."""

    class Signals(QObject):
        force_sync = pyqtSignal()
        settings = pyqtSignal()
        reset_setup = pyqtSignal()
        quit = pyqtSignal()
        open_dir = pyqtSignal()
        show_menu = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.signals = self.Signals()

        self._init_ui()

    def _init_ui(self) -> None:
        # Create the tray
        self.setIcon(logo())
        self.setVisible(True)
        self.setToolTip("")

        # Create the menu
        self._menu = SyncTrayMenu()
        self._messages = TrayMessages()

        # Signals
        self._menu.refresh.triggered.connect(self.signals.force_sync)
        self._menu.preferences.triggered.connect(self.signals.settings)
        self._menu.reset_setup.triggered.connect(self.signals.reset_setup)
        self._menu.quit.triggered.connect(self.signals.quit)
        self._menu.open_dir.triggered.connect(self.signals.open_dir)
        self._menu.aboutToShow.connect(self.signals.show_menu)

        # Add the menu to the tray
        self.setContextMenu(self._menu)

    def set_logged_in(self, value: bool) -> None:
        self._menu.set_logged_in(value)

    def set_last_synced(self, value: datetime | None) -> None:
        self._menu.set_last_synced(value)

    def set_currently_syncing(self, syncing: bool) -> None:
        self._menu.set_currently_syncing(syncing)
        self.setToolTip(self._menu._status.text())

    def set_auth_required(self, auth_required: bool) -> None:
        self._menu.set_auth_required(auth_required)
        self.setToolTip(self._menu._status.text())

    def notify(self, evt: Event) -> None:
        title, msg, icon, duration = self._messages.get_msg(evt)
        self._show_msg(title, msg, icon, duration)

    def _show_msg(self, title: str, msg: str,
                  icon: QSystemTrayIcon.MessageIcon,
                  duration: int) -> None:
        duration = int(duration) * 1000
        self.showMessage(title, msg, icon, duration)
