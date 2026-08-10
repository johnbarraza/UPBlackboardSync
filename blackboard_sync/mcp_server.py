"""
Embedded MCP/REST HTTP server for BlackboardSync remote control.

Hermes / OpenClaw (Docker) connect via:
  http://host.docker.internal:39571/mcp   ← MCP streamable-HTTP transport
  http://host.docker.internal:39571/status  ← plain REST

Port override: BBSYNC_MCP_PORT env var.
"""

import os
import json
import logging
import threading
from typing import Any, Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

DEFAULT_PORT = 39571

_TOOLS: list[dict] = [
    {
        "name": "blackboard_status",
        "description": (
            "Get full BlackboardSync status: logged_in, syncing, current_course "
            "(file being downloaded), last_sync, next_sync, auth_required, "
            "download_location, disk_usage_mb, files_count, university."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "blackboard_sync_now",
        "description": "Force an immediate download of new Blackboard content (requires user to be logged in).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "blackboard_open_login",
        "description": (
            "Show the Blackboard login window on the PC. "
            "Use when auth_required is true or user is not logged in."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "blackboard_courses",
        "description": "List enrolled courses with their individual last-sync timestamps.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "blackboard_files",
        "description": (
            "Browse the local download folder. "
            "Pass subpath (relative to download_location) to drill into a subdirectory. "
            "Returns a list of entries with name, type (file/dir), and size_kb."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "subpath": {
                    "type": "string",
                    "description": "Relative path inside the download folder (e.g. '2024/Calculus'). Empty string for root.",
                }
            },
        },
    },
    {
        "name": "blackboard_restart",
        "description": "Restart the sync engine (use if sync appears stuck or stopped).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "blackboard_auth_required",
        "description": (
            "Check if re-login is required (session expired, e.g. because the user "
            "logged into Blackboard from another device such as a phone or tablet)."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "blackboard_announcements",
        "description": (
            "Fetch course announcements from Blackboard. "
            "Pass course_id to get announcements for a specific course, "
            "or omit to get recent announcements from all enrolled courses."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "course_id": {
                    "type": "string",
                    "description": "Blackboard course ID (e.g. '_12345_1'). Omit to fetch from all courses.",
                }
            },
        },
    },
    {
        "name": "blackboard_course_status",
        "description": (
            "Get detailed status for a specific course by its ID: "
            "name, year, selected for sync, last_synced, local file count, "
            "local path, and count of announcements available."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "course_id": {
                    "type": "string",
                    "description": "Blackboard course ID (e.g. '_12345_1').",
                }
            },
            "required": ["course_id"],
        },
    },
]


# ---------------------------------------------------------------------------
# Qt bridge — signals are delivered on the main Qt thread via QueuedConnection
# ---------------------------------------------------------------------------

class MCPBridge(QObject):
    """Emitted from the HTTP thread; slots run on the Qt main thread."""
    open_login_requested = pyqtSignal()
    force_sync_requested = pyqtSignal()
    restart_sync_requested = pyqtSignal()


# ---------------------------------------------------------------------------
# HTTP request handler
# ---------------------------------------------------------------------------

class _Handler(BaseHTTPRequestHandler):
    # Injected as class attributes by MCPServer
    get_status: Callable[[], dict]
    get_courses: Callable[[], list]
    get_files: Callable[[str], list]
    get_announcements: Callable[[str | None], list]
    get_course_status: Callable[[str], dict]
    bridge: MCPBridge

    def log_message(self, fmt: str, *args: Any) -> None:
        pass  # silence built-in access log

    # ── helpers ─────────────────────────────────────────────────────────────

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    # ── REST GET ─────────────────────────────────────────────────────────────

    def do_GET(self) -> None:
        if self.path == "/status":
            self._send_json(self.get_status())
        elif self.path == "/courses":
            self._send_json({"courses": self.get_courses()})
        elif self.path.startswith("/files"):
            subpath = self.path[len("/files"):].lstrip("/")
            self._send_json({"entries": self.get_files(subpath)})
        elif self.path == "/health":
            self._send_json({"ok": True})
        else:
            self._send_json({"error": "not found"}, 404)

    # ── REST POST ────────────────────────────────────────────────────────────

    def do_POST(self) -> None:
        if self.path == "/mcp":
            self._handle_mcp()
        elif self.path == "/sync":
            self.bridge.force_sync_requested.emit()
            self._send_json({"ok": True, "message": "sync triggered"})
        elif self.path == "/login":
            self.bridge.open_login_requested.emit()
            self._send_json({"ok": True, "message": "login window requested"})
        elif self.path == "/restart":
            self.bridge.restart_sync_requested.emit()
            self._send_json({"ok": True, "message": "restart triggered"})
        else:
            self._send_json({"error": "not found"}, 404)

    # ── MCP streamable-HTTP transport (spec 2024-11-05) ─────────────────────

    def _handle_mcp(self) -> None:
        try:
            req = self._read_json()
        except Exception:
            self._send_json({
                "jsonrpc": "2.0", "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            })
            return

        req_id = req.get("id")
        method = req.get("method", "")

        if method == "initialize":
            result: Any = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "blackboardsync", "version": "1.0"},
            }
        elif method in ("notifications/initialized", "ping"):
            self._send_json({"jsonrpc": "2.0", "id": req_id, "result": {}})
            return
        elif method == "tools/list":
            result = {"tools": _TOOLS}
        elif method == "tools/call":
            params = req.get("params", {})
            result = self._call_tool(
                params.get("name", ""),
                params.get("arguments", {}),
            )
        else:
            self._send_json({
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            })
            return

        self._send_json({"jsonrpc": "2.0", "id": req_id, "result": result})

    def _call_tool(self, name: str, args: dict) -> dict:
        def text(msg: str) -> dict:
            return {"content": [{"type": "text", "text": msg}]}

        if name == "blackboard_status":
            return text(json.dumps(self.get_status(), default=str, indent=2))
        elif name == "blackboard_sync_now":
            self.bridge.force_sync_requested.emit()
            return text("Sync triggered.")
        elif name == "blackboard_open_login":
            self.bridge.open_login_requested.emit()
            return text("Login window shown on PC.")
        elif name == "blackboard_courses":
            return text(json.dumps(self.get_courses(), default=str, indent=2))
        elif name == "blackboard_files":
            subpath = args.get("subpath", "")
            entries = self.get_files(subpath)
            return text(json.dumps(entries, default=str, indent=2))
        elif name == "blackboard_restart":
            self.bridge.restart_sync_requested.emit()
            return text("Sync engine restarted.")
        elif name == "blackboard_auth_required":
            status = self.get_status()
            if status.get("auth_required") or not status.get("logged_in"):
                return text(
                    "⚠️ Login required — session expired or not logged in.\n"
                    "Call blackboard_open_login to show the login window on the PC."
                )
            return text("✅ Logged in — no action needed.")
        elif name == "blackboard_announcements":
            course_id = args.get("course_id") or None
            announcements = self.get_announcements(course_id)
            return text(json.dumps(announcements, default=str, indent=2))
        elif name == "blackboard_course_status":
            course_id = args.get("course_id", "")
            status = self.get_course_status(course_id)
            return text(json.dumps(status, default=str, indent=2))
        else:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
            }


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class MCPServer:
    """Runs _Handler in a daemon ThreadingHTTPServer on 0.0.0.0:PORT."""

    def __init__(
        self,
        get_status: Callable[[], dict],
        get_courses: Callable[[], list],
        get_files: Callable[[str], list],
        get_announcements: Callable[[str | None], list],
        get_course_status: Callable[[str], dict],
        bridge: MCPBridge,
        port: int | None = None,
    ) -> None:
        self._port = port or int(os.environ.get("BBSYNC_MCP_PORT", DEFAULT_PORT))
        self._handler_cls = type(
            "Handler",
            (_Handler,),
            {
                "get_status": staticmethod(get_status),
                "get_courses": staticmethod(get_courses),
                "get_files": staticmethod(get_files),
                "get_announcements": staticmethod(get_announcements),
                "get_course_status": staticmethod(get_course_status),
                "bridge": bridge,
            },
        )
        self._server: ThreadingHTTPServer | None = None

    def start(self) -> None:
        try:
            self._server = ThreadingHTTPServer(("0.0.0.0", self._port), self._handler_cls)
            t = threading.Thread(target=self._server.serve_forever, daemon=True)
            t.start()
            logger.info("MCP server listening on 0.0.0.0:%d", self._port)
        except OSError:
            logger.exception("MCP server failed to start (port %d in use?)", self._port)

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server = None
