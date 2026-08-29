# BlackboardSync MCP Server

An embedded HTTP server that starts automatically with BlackboardSync, exposing status and control endpoints so Hermes, OpenClaw, or any MCP-compatible agent running inside Docker can monitor and control the app.

## Connection

BlackboardSync listens on `0.0.0.0:39571` (all interfaces).

| Client location | URL |
|---|---|
| Docker container | `http://host.docker.internal:39571` |
| Same machine | `http://localhost:39571` |

Override port: set `BBSYNC_MCP_PORT` environment variable before launching the app.
The MCP server is enabled by default on fresh installations and can be disabled or
moved to another port from **Preferences > MCP server**.

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
  "version": "1.3.7",
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
    "last_synced": "2026-08-09T14:30:00+00:00",
    "is_syncing_now": true,
    "has_local_files": true,
    "local_file_count": 47
  },
  {
    "id": "_99999_1",
    "name": "Física II",
    "year": 2026,
    "selected": true,
    "sync_status": "selected",
    "last_synced": null,
    "is_syncing_now": false,
    "has_local_files": false,
    "local_file_count": 0
  }
]
```

`sync_status` values:

| Value | Meaning |
|---|---|
| `selected` | User chose to sync this course — downloading |
| `not_selected` | User deselected it — skipped |
| `new` | Newly enrolled, never seen — **not downloading yet** |

Per-course sync state fields:

| Field | Meaning |
|---|---|
| `is_syncing_now` | This course is being downloaded at this moment |
| `has_local_files` | At least one file exists on disk for this course |
| `local_file_count` | Number of files on disk (0 = never synced or empty) |

**Reading sync state per course:**
- `selected + last_synced: null + has_local_files: false` → **needs full sync** (never downloaded)
- `selected + last_synced: <date> + has_local_files: true` → **up to date**
- `is_syncing_now: true` → **downloading right now**
- `selected + has_local_files: false + last_synced: <date>` → **local files missing**, will re-download next sync

> Note: `local_file_count` scans the course folder on every call. Avoid calling faster than every 30 s when many courses are selected.

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

### `blackboard_sync_course`
Synchronize only one course for this run. This does not change the courses selected
in Settings, so it is useful before a class when only that course needs updating.

**Arguments:**
- `course_id` *(required)* — obtain it from `blackboard_courses`.

If another download is already running, the course-specific run remains queued and
starts on the next sync pass.

```json
{ "course_id": "_12345_1" }
```

---

### `blackboard_course_files`
Map every locally downloaded material for one course without knowing its year or
folder name. Returns `file_count`, `total_size_mb`, `local_path`, and a recursive
`files` list containing relative path, size, and modification time.

**Arguments:**
- `course_id` *(required)* — obtain it from `blackboard_courses`.

For a course stored at `<download_location>/2026/Calculo Diferencial`, a typical
response is:

```json
{
  "course_id": "_12345_1",
  "course": "Calculo Diferencial",
  "local_path": "/home/user/Blackboard/2026/Calculo Diferencial",
  "file_count": 2,
  "total_size_mb": 1.4,
  "files": [
    {
      "path": "Semana 1/guia.pdf",
      "size_kb": 1433.6,
      "modified": "2026-08-27T08:30:00"
    },
    {
      "path": "Announcements/Bienvenida.md",
      "size_kb": 2.1,
      "modified": "2026-08-27T08:31:00"
    }
  ]
}
```

The year and course directory are resolved from Blackboard metadata; the caller
does not need to know or construct the `2026/<course>` path.

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

### `blackboard_announcements`
Fetch course announcements live from Blackboard. Each announcement is also written to disk as a `.md` file during sync (see below).

**Arguments:**
- `course_id` *(optional)* — Blackboard course ID (e.g. `"_12345_1"`). Omit to fetch from all enrolled courses.

```json
[
  {
    "id": "_999_1",
    "title": "Bienvenidos",
    "body": "<p>...</p>",
    "created": "2026-08-07T14:00:00.000Z",
    "modified": "2026-08-07T14:00:00.000Z",
    "course_id": "_77249_1"
  }
]
```

> Makes one Blackboard API call per course. Use sparingly.

**On-disk format:** during every sync, announcements are written to:
```
<download_location>/<year>/<course>/Announcements/YYYY-MM-DD - Title.md
```
Each file contains the title, timestamp, and HTML-stripped body. Existing files are never overwritten.

---

### `blackboard_course_status`
Detailed status for a single course. Faster than `blackboard_courses` when you only need one.

**Arguments:**
- `course_id` *(required)*

```json
{
  "id": "_77249_1",
  "name": "Economia Conductual",
  "year": 2026,
  "selected_for_sync": true,
  "last_synced": "2026-08-10T07:15:00+00:00",
  "local_file_count": 12,
  "local_announcement_count": 1,
  "local_path": "C:/Users/john/Blackboard/2026/Economia Conductual-A-PRE-...",
  "live_announcement_count": 1
}
```

| Field | Meaning |
|---|---|
| `local_announcement_count` | `.md` files in the `Announcements/` subfolder on disk |
| `live_announcement_count` | Announcements fetched live from Blackboard API right now |

---

### `blackboard_roster`
Get enrolled members for a course (name, username, role). Full list for instructors; may be limited for students depending on institution settings.

**Arguments:**
- `course_id` *(required)* — Blackboard course ID (e.g. `"_12345_1"`)

```json
[
  { "userId": "_1001_1", "name": "García López, Ana", "userName": "ana.garcia", "role": "Student" },
  { "userId": "_1002_1", "name": "Ramírez, Luis",    "userName": "luis.ramirez", "role": "Instructor" }
]
```

> Also written to disk as `<download_location>/<year>/<course>/Roster/roster.md` during each sync.

---

### `blackboard_recent`
Files downloaded in the last 4 hours across all syncs. No API call — reads the local `.recent_activity.json` written after each sync.

```json
[
  {
    "path": "2026\\Cálculo Diferencial\\Semana3\\parcial1.pdf",
    "name": "parcial1.pdf",
    "course": "Cálculo Diferencial",
    "size_kb": 234.5,
    "synced_at": "2026-08-12T15:29:00+00:00"
  }
]
```

> Use this instead of `blackboard_files` to quickly answer "what just synced?" without scanning the whole directory tree. Also written as a human-readable `recent.md` in the download folder root.

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

On demand  →  blackboard_courses, blackboard_course_status,
              blackboard_course_files, blackboard_sync_course,
              blackboard_files, blackboard_sync_now
```

## Security note

The server has no authentication. If you are on an untrusted network, consider
firewalling port 39571 to localhost only, or setting `BBSYNC_MCP_PORT` to a
non-default port.
