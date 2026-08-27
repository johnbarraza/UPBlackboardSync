import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from blackboard_sync.mcp_server import MCPBridge, MCPServer


def request(server: MCPServer, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = Request(
        f"http://127.0.0.1:{server.port}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req, timeout=5) as response:
        return json.loads(response.read())


@pytest.fixture
def mcp_server():
    bridge = MCPBridge()
    server = MCPServer(
        get_status=lambda: {"logged_in": True},
        get_courses=lambda: [{"id": "course-1"}],
        get_files=lambda subpath: [{"name": subpath}],
        get_course_files=lambda course_id: {"course_id": course_id},
        get_announcements=lambda course_id: [{"course_id": course_id}],
        get_course_status=lambda course_id: {"id": course_id},
        get_roster=lambda course_id: [{"course_id": course_id}],
        get_recent=lambda: [{"name": "recent.pdf"}],
        bridge=bridge,
        port=0,
    )
    server.start()
    yield server
    server.stop()


def test_rest_health_and_status(mcp_server):
    assert request(mcp_server, "/health") == {"ok": True}
    assert request(mcp_server, "/status") == {"logged_in": True}


def test_rest_unknown_endpoint_returns_404(mcp_server):
    with pytest.raises(HTTPError) as exc_info:
        request(mcp_server, "/missing")
    assert exc_info.value.code == 404


def test_mcp_initialize_and_tools_list(mcp_server):
    initialized = request(mcp_server, "/mcp", {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
    })
    assert initialized["result"]["protocolVersion"] == "2024-11-05"
    assert initialized["result"]["serverInfo"]["name"] == "blackboardsync"

    listed = request(mcp_server, "/mcp", {
        "jsonrpc": "2.0", "id": 2, "method": "tools/list",
    })
    names = {tool["name"] for tool in listed["result"]["tools"]}
    assert "blackboard_status" in names
    assert "blackboard_sync_now" in names
    assert "blackboard_sync_course" in names
    assert "blackboard_course_files" in names
    assert "blackboard_roster" in names


def test_mcp_tools_call_status_and_files(mcp_server):
    status = request(mcp_server, "/mcp", {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "blackboard_status", "arguments": {}},
    })
    assert json.loads(status["result"]["content"][0]["text"]) == {
        "logged_in": True,
    }

    files = request(mcp_server, "/mcp", {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "blackboard_files",
            "arguments": {"subpath": "2026/course"},
        },
    })
    assert json.loads(files["result"]["content"][0]["text"]) == [
        {"name": "2026/course"},
    ]

    course_files = request(mcp_server, "/mcp", {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "blackboard_course_files",
            "arguments": {"course_id": "course-1"},
        },
    })
    assert json.loads(course_files["result"]["content"][0]["text"]) == {
        "course_id": "course-1",
    }


def test_mcp_unknown_method_returns_jsonrpc_error(mcp_server):
    response = request(mcp_server, "/mcp", {
        "jsonrpc": "2.0", "id": 5, "method": "unknown/method",
    })
    assert response["error"]["code"] == -32601
