# BlackboardSync MCP Server

An embedded HTTP server that starts automatically with BlackboardSync, exposing status and control endpoints so Hermes, OpenClaw, or any MCP-compatible agent running inside Docker can monitor and control the app.

## Connection

BlackboardSync listens on `0.0.0.0:39571` (all interfaces).

| Client location | URL |
|---|---|
| Docker container | `http://host.docker.internal:39571` |
| Same machine | `http://localhost:39571` |

Override port: set `BBSYNC_MCP_PORT` environment variable before launching the app.

## Connecting Hermes / OpenClaw (MCP protocol)

Add to your agent's MCP server config:

```json
{
  "mcpServers": {
    "blackboardsync": {
      "url": "http://host.docker.internal:39571/mcp",
      "type": "http"
    }
  }
}
```

The server implements the **MCP streamable-HTTP transport** (spec `2024-11-05`). It handles `initialize`, `tools/list`, and `tools/call` over plain `POST /mcp`.

---

## MCP Tools

### `blackboard_status`
Full snapshot of the app state. Good for polling every 30–60 s.

```json
{
  "logged_in": true,
  "syncing": true,
  "active": true,
  "auth_required": false,
  "current_course": "Cálculo Diferencial 2026",
  "last_sync": "2026-08-09T14:30:00+00:00",
  "next_sync": "2026-08-09T15:00:00+00:00",
  "download_location": "C:/Users/john/Blackboard",
  "disk_usage_mb": 342.7,
  "files_count": 1847,
  "university": "Universidad Panamericana"
}
```

> `disk_usage_mb` / `files_count` scan the download folder on every call. Fine for
> occasional polling; avoid calling faster than every 10 s on very large directories.

---

### `blackboard_courses`
All enrolled courses with sync status and year. Makes a Blackboard API call — use
sparingly (once at startup, then on demand).

```json
[
  {
    "id": "_12345_1",
    "name": "Cálculo Diferencial",
    "year": 2026,
    "selected": true,
    "sync_status": "selected",
    "last_synced": "2026-08-09T14:30:00+00:00"
  },
  {
    "id": "_99999_1",
    "name": "Física II",
    "year": 2026,
    "selected": false,
    "sync_status": "new",
    "last_synced": null
  }
]
```

`sync_status` values:

| Value | Meaning |
|---|---|
| `selected` | User chose to sync this course — downloading |
| `not_selected` | User deselected it — skipped |
| `new` | Newly enrolled, never seen — **not downloading yet** |

> **Tip:** Hermes can detect `sync_status: "new"` courses and notify you so you can
> open Settings → select the course → it starts syncing.

---

### `blackboard_files`
Browse the local download folder. Directories sort before files.

```json
// arguments: { "subpath": "2026/Cálculo Diferencial" }
[
  { "name": "Apuntes", "type": "dir",  "size_kb": null,  "modified": "2026-08-08T10:00:00" },
  { "name": "Parcial1.pdf", "type": "file", "size_kb": 234.5, "modified": "2026-08-07T18:22:00" }
]
```

- `subpath` is relative to `download_location`. Empty string = root.
- Path traversal attempts (`../..`) are silently blocked.

---

### `blackboard_sync_now`
Force an immediate sync. Requires user to be logged in.

---

### `blackboard_open_login`
Show the Blackboard login window on the PC. Use when `auth_required` is `true`.

This is the key tool for the session-expiry flow: when the user logs into Blackboard
from their phone or tablet, the PC session cookie is invalidated. The next sync sets
`auth_required: true`. Hermes detects this, notifies the user (via WhatsApp, Telegram,
or any channel), and when the user is ready can call `blackboard_open_login` to bring
the login window to the foreground — the user just completes the login and sync resumes.

---

### `blackboard_auth_required`
Shortcut that returns a human-readable message about whether login is needed.

---

### `blackboard_restart`
Stop and restart the sync engine. Use if `syncing: true` has been stuck for an
unusually long time without progress.

---

## REST API (no MCP client needed)

All endpoints also work as plain HTTP for quick debugging or scripts:

| Method | Path | Description |
|---|---|---|
| GET | `/status` | Same JSON as `blackboard_status` tool |
| GET | `/courses` | `{ "courses": [...] }` |
| GET | `/files?subpath=2026/Cálculo` | `{ "entries": [...] }` (use path separator matching OS) |
| GET | `/health` | `{ "ok": true }` |
| POST | `/sync` | Force sync |
| POST | `/login` | Open login window |
| POST | `/restart` | Restart engine |

Quick test from PowerShell:
```powershell
Invoke-RestMethod http://localhost:39571/status
```

Quick test from Docker bash:
```bash
curl http://host.docker.internal:39571/status
```

---

## Recommended Hermes polling strategy

```
Every 60 s  →  blackboard_status
  if auth_required or not logged_in  →  alert user, offer blackboard_open_login
  if new courses found (check periodically)  →  alert user

On demand  →  blackboard_courses, blackboard_files, blackboard_sync_now
```

## Security note

The server has no authentication. If you are on an untrusted network, consider
firewalling port 39571 to localhost only, or setting `BBSYNC_MCP_PORT` to a
non-default port.
