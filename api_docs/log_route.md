# Logging Routes API Documentation

Base path: `/log` (or `/tc-auth/log` when mounted under main auth router)

Authentication & Authorization:
- All routes require administrative privileges (`superadmin` role).
- Supports `Authorization: Bearer <access_token>` or HttpOnly cookie authentication (`credentials: "include"`).
- When logging is disabled via configuration (`logging=False`), all endpoints return `400 Bad Request` with `error_code: "logging_disabled"`.
- Non-admin or unauthenticated requests return `401 Unauthorized` or `403 Forbidden`.

---

## 1. Summary Table of Endpoints

| HTTP Method | Endpoint | Description | Success Status | Error Statuses |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/log` | List primary logs (`tcauth`, `server`) and all snapshots in `logs/store/` | `200 OK` | `400`, `401`, `403` |
| `POST` | `/log` | Create a point-in-time snapshot of `tcauth` or `server` in `logs/store/` | `201 Created` | `400`, `401`, `403`, `409`, `422` |
| `GET` | `/log/tcauth` | Retrieve parsed JSON records from `tcauth.log` (with pagination) | `200 OK` | `400`, `401`, `403` |
| `GET` | `/log/server` | Retrieve text lines from `server.log` (with pagination) | `200 OK` | `400`, `401`, `403` |
| `GET` | `/log/{name}` | Retrieve contents of a specific log or snapshot by name | `200 OK` | `400`, `401`, `403`, `404` |
| `GET` | `/log/tcauth/stream` | Real-time Server-Sent Events (SSE) stream for `tcauth.log` | `200 OK` (`text/event-stream`) | `400`, `401`, `403` |
| `GET` | `/log/server/stream` | Real-time Server-Sent Events (SSE) stream for `server.log` | `200 OK` (`text/event-stream`) | `400`, `401`, `403` |
| `POST` | `/log/tcauth/reset` | Truncate `tcauth.log` to 0 bytes and continue logging | `200 OK` | `400`, `401`, `403` |
| `POST` | `/log/server/reset` | Truncate `server.log` to 0 bytes and continue logging | `200 OK` | `400`, `401`, `403` |
| `DELETE` | `/log/{name}` | Delete a stored snapshot file from `logs/store/` | `204 No Content` | `400`, `401`, `403`, `404` |

---

## 2. Endpoint Details

### 2.1 `GET /log`
Retrieve summary metadata for all primary logs and saved snapshot files.

- **Headers**: `Authorization: Bearer <token>`
- **Response `200 OK`**:
```json
{
  "success": true,
  "primary_logs": [
    {
      "name": "tcauth",
      "source": "tcauth",
      "filename": "tcauth.log",
      "format": "jsonl",
      "size_bytes": 4096,
      "streamable": true,
      "resettable": true,
      "deletable": false,
      "updated_at": "2026-09-14T01:31:45+00:00"
    },
    {
      "name": "server",
      "source": "server",
      "filename": "server.log",
      "format": "text",
      "size_bytes": 8192,
      "streamable": true,
      "resettable": true,
      "deletable": false,
      "updated_at": "2026-09-14T01:31:45+00:00"
    }
  ],
  "snapshots": [
    {
      "name": "auth-debug-session",
      "source": "tcauth",
      "filename": "tcauth-auth-debug-session.log",
      "format": "jsonl",
      "size_bytes": 1024,
      "streamable": false,
      "resettable": false,
      "deletable": true,
      "created_at": "2026-09-14T01:30:00+00:00",
      "updated_at": "2026-09-14T01:30:00+00:00"
    }
  ]
}
```

---

### 2.2 `POST /log`
Create a snapshot copy of an active primary log into `logs/store/{source}-{name}.log`.

- **Headers**: `Authorization: Bearer <token>`, `Content-Type: application/json`
- **Request Body**:
```json
{
  "name": "pre-release-check",
  "source": "tcauth"
}
```
- **Validation Rules**:
  - `name`: 1–64 characters, regex `^[a-zA-Z0-9_-]+$`. Directory traversal characters (`..`, `/`, `\`, `:`) are strictly rejected.
  - `source`: `"tcauth"` or `"server"`.
- **Response `201 Created`**:
```json
{
  "success": true,
  "message": "Snapshot 'pre-release-check' created successfully",
  "snapshot": {
    "name": "pre-release-check",
    "source": "tcauth",
    "filename": "tcauth-pre-release-check.log",
    "format": "jsonl",
    "size_bytes": 4096,
    "created_at": "2026-09-14T01:32:00+00:00"
  }
}
```
- **Error Responses**:
  - `409 Conflict`: `{ "success": false, "message": "Snapshot with name 'pre-release-check' already exists in source 'tcauth'", "error_code": "snapshot_already_exists" }`
  - `422 Unprocessable Entity`: `{ "success": false, "message": "Invalid snapshot name or source", "error_code": "invalid_log_name" }`

---

### 2.3 `GET /log/tcauth`
Read structured records from `tcauth.log` (parsed JSON objects).

- **Headers**: `Authorization: Bearer <token>`
- **Query Parameters**:
  - `limit` (optional integer, 1 to 5000): Maximum records to return.
  - `offset` (optional integer, default 0): Number of records to skip from beginning.
- **Response `200 OK`**:
```json
{
  "success": true,
  "filename": "tcauth.log",
  "format": "jsonl",
  "total_records": 120,
  "count": 50,
  "offset": 0,
  "records": [
    {
      "timestamp": "2026-09-14T01:31:45.123456+00:00",
      "level": "INFO",
      "event": "LOGIN_SUCCESS",
      "message": "User logged in successfully",
      "request_id": "req-987",
      "method": "POST",
      "path": "/tc-auth/login/password",
      "status_code": 200,
      "client_ip": "127.0.0.1",
      "user_agent": "Mozilla/5.0 ...",
      "duration_ms": 42.5,
      "metadata": {
        "account_id": 1,
        "session_id": 5
      }
    }
  ]
}
```

---

### 2.4 `GET /log/server`
Read lines from `server.log` (standard text lines).

- **Headers**: `Authorization: Bearer <token>`
- **Query Parameters**:
  - `limit` (optional integer, 1 to 5000)
  - `offset` (optional integer, default 0)
- **Response `200 OK`**:
```json
{
  "success": true,
  "filename": "server.log",
  "format": "text",
  "total_records": 450,
  "count": 100,
  "offset": 0,
  "records": [
    "INFO:     Started server process [28900]",
    "INFO:     Waiting for application startup.",
    "INFO:     Application startup complete.",
    "INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)"
  ]
}
```

---

### 2.5 `GET /log/{name}`
Retrieve contents of a specific log file or snapshot by name.

- **Headers**: `Authorization: Bearer <token>`
- **Path Parameter**: `name` (e.g. `tcauth`, `server`, `auth-debug-session`)
- **Query Parameters**: `limit`, `offset`
- **Response `200 OK`**: Returns JSON records for JSONL files or string lines for text files.
- **Error Response `404 Not Found`**: `{ "success": false, "message": "Log file or snapshot 'invalid-name' was not found", "error_code": "snapshot_not_found" }`

---

### 2.6 `GET /log/tcauth/stream` & `GET /log/server/stream`
Open a persistent Server-Sent Events (SSE) connection for live log monitoring.

- **Headers**: `Authorization: Bearer <token>`, `Accept: text/event-stream`
- **Response `200 OK`**:
  - Headers: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`
- **Behavior**:
  - Immediately yields the **last 10 records** on connection.
  - Pushes newly generated log events in real time.
  - Sends `: ping\n\n` heartbeat comments every 15 seconds.
- **Sample Stream Output**:
```text
event: log
data: {"timestamp":"2026-09-14T01:31:45+00:00","level":"INFO","event":"LOGIN_SUCCESS","message":"User logged in"}

: ping

event: log
data: {"timestamp":"2026-09-14T01:32:00+00:00","level":"ERROR","event":"TOKEN_EXPIRED","message":"JWT expired"}

```

---

### 2.7 `POST /log/tcauth/reset` & `POST /log/server/reset`
Truncate the target primary log file to 0 bytes and continue logging.

- **Headers**: `Authorization: Bearer <token>`
- **Response `200 OK`**:
```json
{
  "success": true,
  "message": "Primary log 'tcauth' has been reset successfully"
}
```

---

### 2.8 `DELETE /log/{name}`
Delete a stored snapshot file from `logs/store/`.

- **Headers**: `Authorization: Bearer <token>`
- **Path Parameter**: `name` (the snapshot identifier)
- **Response `204 No Content`**
- **Error Responses**:
  - `403 Forbidden`: `{ "success": false, "message": "Cannot delete primary active log file 'tcauth'", "error_code": "cannot_delete_primary" }`
  - `404 Not Found`: `{ "success": false, "message": "Snapshot 'old-backup' not found in store", "error_code": "snapshot_not_found" }`
