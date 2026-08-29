"""Packaged-application self-test used by Linux release verification."""

import json
import os
import sys
from typing import Any
from urllib.request import Request, urlopen


def _request(port: int, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read())


def run_self_test() -> int:
    """Validate Qt assets and the embedded MCP transport without user data."""
    if (
        sys.platform.startswith("linux")
        and not os.environ.get("DISPLAY")
        and not os.environ.get("WAYLAND_DISPLAY")
    ):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
    from PyQt6.QtWidgets import QApplication

    from .mcp_server import MCPBridge, MCPServer
    from .qt.assets import logo
    from .qt.utils import clean_external_env

    # External apps (xdg-open) must not inherit PyInstaller's bundled libs.
    if sys.platform.startswith("linux"):
        external = clean_external_env()
        if "_internal" in external.get("LD_LIBRARY_PATH", ""):
            raise RuntimeError("clean_external_env leaked bundled LD_LIBRARY_PATH")
        if "LD_PRELOAD" in external:
            raise RuntimeError("clean_external_env leaked LD_PRELOAD")

    app = QApplication.instance() or QApplication([])
    if logo().isNull():
        raise RuntimeError("Application icon could not be loaded")

    status: dict[str, Any] = {
        "logged_in": False,
        "syncing": False,
        "self_test": True,
    }
    bridge = MCPBridge()
    server = MCPServer(
        get_status=lambda: status,
        get_courses=lambda: [],
        get_files=lambda _subpath: [],
        get_course_files=lambda course_id: {"course_id": course_id, "files": []},
        get_announcements=lambda _course_id: [],
        get_course_status=lambda course_id: {"id": course_id},
        get_roster=lambda _course_id: [],
        get_recent=lambda: [],
        bridge=bridge,
        port=0,
    )

    try:
        server.start()
        if _request(server.port, "/health") != {"ok": True}:
            raise RuntimeError("REST health endpoint failed")
        if _request(server.port, "/status") != status:
            raise RuntimeError("REST status endpoint failed")

        initialized = _request(server.port, "/mcp", {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
        })
        if initialized.get("result", {}).get("serverInfo", {}).get("name") != "blackboardsync":
            raise RuntimeError("MCP initialize failed")

        tools_response = _request(server.port, "/mcp", {
            "jsonrpc": "2.0", "id": 2, "method": "tools/list",
        })
        tool_names = {
            item["name"] for item in tools_response.get("result", {}).get("tools", [])
        }
        if "blackboard_status" not in tool_names:
            raise RuntimeError("MCP tools/list did not expose blackboard_status")

        call_response = _request(server.port, "/mcp", {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "blackboard_status", "arguments": {}},
        })
        content = call_response.get("result", {}).get("content", [])
        if not content or '"self_test": true' not in content[0].get("text", ""):
            raise RuntimeError("MCP tools/call failed")
    finally:
        server.stop()
        app.quit()

    print(json.dumps({
        "ok": True,
        "checks": ["qt", "assets", "external_env", "rest", "mcp_initialize", "mcp_tools"],
    }))
    return 0
