#!/usr/bin/env python3

"""BlackboardSync Controller."""

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

from requests.cookies import RequestsCookieJar
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as get_version

from .sync import BlackboardSync
from .__about__ import __id__, __title__, __uri__
from .institutions import get_names, autodetect

from .updates import check_for_updates
from .qt.manager import UIManager
from .mcp_server import MCPBridge, MCPServer


class SyncController:
    """Connects an instance of BlackboardSync with the UI module."""

    def __init__(self):
        super().__init__()
        self.model = BlackboardSync()
        self.ui = UIManager(__id__, __title__, __uri__,
                            get_names(), autodetect())

        # Tracks whether session expired and re-login is needed
        self._auth_required = False
        self.model._auth_required_callback = self._on_auth_required

        # MCP bridge dispatches HTTP-thread signals to Qt main thread
        self._mcp_bridge = MCPBridge()
        self._mcp_bridge.force_sync_requested.connect(self.force_sync)
        self._mcp_bridge.open_login_requested.connect(self._mcp_open_login)
        self._mcp_bridge.restart_sync_requested.connect(self._restart_sync)

        self._mcp_server = MCPServer(
            get_status=self._mcp_get_status,
            get_courses=self._mcp_get_courses,
            get_files=self._mcp_get_files,
            bridge=self._mcp_bridge,
            port=self.model.mcp_port,
        )
        if self.model.mcp_enabled:
            self._mcp_server.start()

        first_time = self.model.university is None
        self._pending_setup_course_selection = first_time

        if not first_time:
            self.open_login()

        self.init_signals()
        self.ui.start(first_time)

    # ── MCP helpers ────────────────────────────────────────────────────────

    def _on_auth_required(self) -> None:
        """Called from sync thread when session expires unexpectedly."""
        self._auth_required = True

    def _mcp_open_login(self) -> None:
        if self.model.university is not None:
            self.open_login()

    def _restart_sync(self) -> None:
        if self.model.is_active:
            self.model.stop_sync()
        if self.model.is_logged_in:
            self.model.start_sync()

    def _mcp_get_status(self) -> dict:
        last = self.model.last_sync_time
        nxt = self.model.next_sync
        loc = self.model.download_location

        _dl = self.model._download
        current_course = _dl.current_course if (self.model.is_syncing and _dl is not None) else None

        disk_mb: float | None = None
        files_count: int | None = None
        if loc and loc.exists():
            try:
                files = [f for f in loc.rglob("*") if f.is_file()]
                files_count = len(files)
                disk_mb = round(sum(f.stat().st_size for f in files) / (1024 * 1024), 1)
            except Exception:
                pass

        return {
            "logged_in": self.model.is_logged_in,
            "syncing": self.model.is_syncing,
            "active": self.model.is_active,
            "auth_required": self._auth_required,
            "current_course": current_course,
            "last_sync": last.isoformat() if last else None,
            "next_sync": nxt.isoformat() if nxt else None,
            "download_location": str(loc) if loc else None,
            "disk_usage_mb": disk_mb,
            "files_count": files_count,
            "university": self.model.university.name if self.model.university else None,
        }

    def _mcp_get_courses(self) -> list:
        raw_courses = self.model.list_available_courses()
        sync_status = self.model.course_sync_status
        selected_ids = set(self.model.selected_course_ids)
        sync_all = len(selected_ids) == 0
        loc = self.model.download_location

        _dl = self.model._download
        current_course = (
            _dl.current_course
            if (self.model.is_syncing and _dl is not None)
            else None
        )

        courses = []
        for course in raw_courses:
            cid = course.id
            t = sync_status.get(cid)
            year = course.created.year if course.created else None
            title = course.title or course.name or cid
            selected = sync_all or (cid in selected_ids)

            if selected:
                status = "selected"
            elif cid not in sync_status:
                status = "new"
            else:
                status = "not_selected"

            is_syncing_now = (current_course == title)

            file_count = 0
            if loc:
                year_str = str(year) if year else "No Date"
                course_path = loc / year_str / title
                try:
                    file_count = sum(
                        1 for p in course_path.rglob("*") if p.is_file()
                    )
                except (OSError, PermissionError):
                    pass

            courses.append({
                "id": cid,
                "name": title,
                "year": year,
                "selected": selected,
                "sync_status": status,
                "last_synced": t.isoformat() if t else None,
                "is_syncing_now": is_syncing_now,
                "has_local_files": file_count > 0,
                "local_file_count": file_count,
            })

        return courses

    def _mcp_get_files(self, subpath: str = "") -> list:
        from datetime import datetime
        loc = self.model.download_location
        if not loc:
            return []
        target = (loc / subpath).resolve() if subpath else loc.resolve()
        if not str(target).startswith(str(loc.resolve())):
            return []  # block path traversal
        if not target.exists() or not target.is_dir():
            return []
        entries = []
        try:
            for entry in sorted(target.iterdir(), key=lambda e: (e.is_file(), e.name.lower())):
                try:
                    stat = entry.stat()
                    entries.append({
                        "name": entry.name,
                        "type": "file" if entry.is_file() else "dir",
                        "size_kb": round(stat.st_size / 1024, 1) if entry.is_file() else None,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
                except OSError:
                    pass
        except PermissionError:
            pass
        return entries

    # ── signals ────────────────────────────────────────────────────────────

    def init_signals(self):
        self.ui.signals.open_settings.connect(self.open_settings)
        self.ui.signals.open_tray.connect(self.open_tray)
        self.ui.signals.open_downloads.connect(self.open_downloads)
        self.ui.signals.open_menu.connect(self.open_menu)
        self.ui.signals.setup.connect(self.setup)
        self.ui.signals.config.connect(self.config)
        self.ui.signals.redownload.connect(self.redownload)
        self.ui.signals.force_sync.connect(self.force_sync)
        self.ui.signals.log_in.connect(self.log_in)
        self.ui.signals.log_out.connect(self.log_out)
        self.ui.signals.quit.connect(self.quit)
        self.ui.signals.auth_drive.connect(self.auth_drive)

    def open_login(self) -> None:
        start_url = str(self.model.university.login.start_url)
        target_url = str(self.model.university.login.target_url)

        self.ui.open_login(start_url, target_url)

    def force_sync(self) -> None:
        self.model.force_sync()

    def open_settings(self) -> None:
        __version__ = None
        package = __package__.replace('_', '')

        try:
            __version__ = get_version(package)
        except PackageNotFoundError:
            pass

        courses = self.model.list_available_courses_summary()
        self.ui.open_settings(self.model.download_location,
                              self.model.username,
                              self.model.sync_interval,
                              __version__,
                              self.model.backup_enabled,
                              self.model.backup_location,
                              self.model.drive_enabled,
                              self.model.drive_credentials_path,
                              self.model.drive_email,
                              courses,
                              self.model.selected_course_ids,
                              self.model.course_sync_status,
                              self.model.mcp_enabled,
                              self.model.mcp_port)

    def open_menu(self) -> None:
        self.ui.open_menu(self.model.last_sync_time,
                          self.model.is_logged_in,
                          self.model.is_syncing)

        if self.model.has_error:
            self.ui.notify_sync_error()

    def open_tray(self, clicked) -> None:
        if clicked:
            first_time = self.model.university is None
            is_logged_in = self.model.is_logged_in

            self.ui.open_tray(first_time, is_logged_in)

    def open_downloads(self) -> None:
        self.ui.open_file(self.model.download_location)

    def setup(self, institution_index: int,
              download_location: str, min_year: int) -> None:
        self.model.setup(institution_index, download_location, min_year)
        self._pending_setup_course_selection = True
        self.open_login()

    def config(self, download_location: str, sync_frequency: int,
               backup_enabled: bool, backup_location: str | None,
               drive_enabled: bool, drive_credentials_path: str | None,
               selected_course_ids: list[str], mcp_enabled: bool = False,
               mcp_port: int = 39571) -> None:
        if self.model.download_location != download_location:
            self.model.download_location = download_location
            self.ui.ask_redownload()

        self.model.sync_interval = sync_frequency
        self.model.backup_enabled = backup_enabled
        self.model.backup_location = backup_location
        self.model.drive_enabled = drive_enabled
        self.model.drive_credentials_path = drive_credentials_path
        self.model.selected_course_ids = selected_course_ids

        mcp_changed = (mcp_enabled != self.model.mcp_enabled
                       or mcp_port != self.model.mcp_port)
        if mcp_changed:
            self._mcp_server.stop()
            self.model.mcp_enabled = mcp_enabled
            self.model.mcp_port = mcp_port
            self._mcp_server = MCPServer(
                get_status=self._mcp_get_status,
                get_courses=self._mcp_get_courses,
                get_files=self._mcp_get_files,
                bridge=self._mcp_bridge,
                port=mcp_port,
            )
            if mcp_enabled:
                self._mcp_server.start()

    def redownload(self) -> None:
        self.model.redownload()

    def log_in(self, cookies: RequestsCookieJar) -> None:
        if self.model.auth(cookies, start_sync=False):
            self._auth_required = False
            if self._pending_setup_course_selection:
                courses = self.model.list_available_courses_summary()
                selected = self.ui.ask_course_selection(
                    courses,
                    self.model.selected_course_ids,
                    self.model.course_sync_status
                )
                if selected is not None:
                    self.model.selected_course_ids = selected
                self._pending_setup_course_selection = False

            self.model.start_sync()
            self.ui.log_in()
            self.ui.notify_running()
            self.check_for_updates()
        else:
            self.ui.notify_login_error()

    def log_out(self) -> None:
        if self.model.is_active:
            self.model.stop_sync()

        self.model.log_out()

    def quit(self) -> None:
        if self.model.is_active:
            self.model.stop_sync()
        self._mcp_server.stop()

    def check_for_updates(self) -> None:
        if check_for_updates():
            self.ui.notify_update()

    def auth_drive(self, credentials_path: str | None) -> None:
        if credentials_path:
            self.model.drive_credentials_path = credentials_path
        
        if self.model.authenticate_drive():
            # Refresh settings to show connected status
            self.open_settings()
        else:
            # Maybe show error? For now just re-open settings
            self.open_settings()


if __name__ == '__main__':
    controller = SyncController()
