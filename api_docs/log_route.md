# Logging & Monitoring Routes

Base path: Configurable (defaults to `/tc-auth/log` when mounted under main auth router with prefix `/tc-auth`, or `/log` when mounted standalone).
All endpoints and code examples below are relative to your auth `baseUrl` (e.g. `const baseUrl = "https://api.example.com/tc-auth"`).

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

## 2. Snapshot Naming Conventions

> [!IMPORTANT]
> **Snapshot Creation vs Retrieval & Deletion**:
> - **When Creating (`POST /log`)**:
>   Send only your custom identifier as `name` in the request body (e.g., `{"name": "pre-deploy-backup", "source": "tcauth"}`).
>   The physical file created on disk is `tcauth-pre-deploy-backup.log` (format: `{source}-{name}.log`).
> - **When Fetching (`GET /log/{name}`) or Deleting (`DELETE /log/{name}`)**:
>   Pass the **full snapshot name without extension** as the path parameter:
>   - Correct: `GET /log/tcauth-pre-deploy-backup`
>   - Correct: `DELETE /log/tcauth-pre-deploy-backup`
>   - Primary logs: `GET /log/tcauth` or `GET /log/server`

---

## 3. Endpoint Details & JavaScript Examples

### 3.1 GET `/log`

Retrieve summary metadata for all primary logs and saved snapshot files.

Headers:
- `Authorization: Bearer <token>` (or `credentials: "include"`)

Response (`200 OK`):

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
      "name": "tcauth-debug-session",
      "source": "tcauth",
      "filename": "tcauth-debug-session.log",
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

JavaScript Example:

```js
const res = await fetch(`${baseUrl}/log`, {
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
});
const data = await res.json();
console.log("Primary logs:", data.primary_logs);
console.log("Snapshots:", data.snapshots);
```

---

### 3.2 POST `/log`

Create a point-in-time snapshot copy of an active primary log into `logs/store/{source}-{name}.log`.

Headers:
- `Authorization: Bearer <token>`, `Content-Type: application/json`

Body:

```json
{
  "name": "pre-release-check",
  "source": "tcauth"
}
```

Validation:
- `name`: 1–64 characters, regex `^[a-zA-Z0-9_-]+$`. Directory traversal characters (`..`, `/`, `\`, `:`) are strictly rejected.
- `source`: `"tcauth"` or `"server"`.

Response (`201 Created`):

```json
{
  "success": true,
  "message": "Snapshot 'pre-release-check' created successfully",
  "snapshot": {
    "name": "tcauth-pre-release-check",
    "source": "tcauth",
    "filename": "tcauth-pre-release-check.log",
    "format": "jsonl",
    "size_bytes": 4096,
    "created_at": "2026-09-14T01:32:00+00:00"
  }
}
```

JavaScript Example:

```js
const res = await fetch(`${baseUrl}/log`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${accessToken}`,
  },
  body: JSON.stringify({
    name: "pre-release-check",
    source: "tcauth",
  }),
});
const data = await res.json();
```

---

### 3.3 GET `/log/tcauth`

Read structured records from `tcauth.log` (parsed JSON objects).

Headers:
- `Authorization: Bearer <token>`

Query Parameters:
- `page` (optional integer, default `1`, min 1): Page number (1-based).
- `limit` (optional integer, default `50`, min 1, max 5000): Maximum records per page.

Response (`200 OK`):

```json
{
  "success": true,
  "filename": "tcauth.log",
  "format": "jsonl",
  "total_records": 120,
  "page": 1,
  "limit": 50,
  "total_pages": 3,
  "count": 50,
  "has_next": true,
  "has_prev": false,
  "offset": 0,
  "records": [
    {
      "timestamp": "2026-09-14T01:31:45.123456+00:00",
      "level": "INFO",
      "event": "LOGIN_SUCCESS",
      "message": "User logged in successfully",
      "request_id": "req-987",
      "method": "POST",
      "path": "/login/password",
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

JavaScript Example:

```js
const page = 1;
const limit = 50;
const res = await fetch(`${baseUrl}/log/tcauth?page=${page}&limit=${limit}`, {
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
});
const data = await res.json();
console.log(`Loaded ${data.records.length} of ${data.total_records} logs`);
```

---

### 3.4 GET `/log/server`

Read raw runtime lines from `server.log` (standard text lines).

Headers:
- `Authorization: Bearer <token>`

Query Parameters:
- `page` (optional integer, default `1`, min 1): Page number (1-based).
- `limit` (optional integer, default `50`, min 1, max 5000): Maximum lines per page.

Response (`200 OK`):

```json
{
  "success": true,
  "filename": "server.log",
  "format": "text",
  "total_records": 450,
  "page": 1,
  "limit": 50,
  "total_pages": 9,
  "count": 50,
  "has_next": true,
  "has_prev": false,
  "offset": 0,
  "records": [
    "INFO:     Started server process [28900]",
    "INFO:     Waiting for application startup.",
    "INFO:     Application startup complete.",
    "INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)"
  ]
}
```

JavaScript Example:

```js
const res = await fetch(`${baseUrl}/log/server?page=1&limit=100`, {
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
});
const data = await res.json();
console.log("Server output lines:", data.records);
```

---

### 3.5 GET `/log/{name}`

Retrieve contents of a specific log file or snapshot by name.

Headers:
- `Authorization: Bearer <token>`

Path Parameter:
- `name`: For primary logs, `"tcauth"` or `"server"`. For stored snapshots, the **full snapshot name without extension** (e.g. `"tcauth-pre-release-check"`).

Query Parameters:
- `page` (optional integer, default `1`, min 1): Page number.
- `limit` (optional integer, default `50`, min 1, max 5000): Records/lines per page.

Response (`200 OK`):
Returns JSON records for JSONL files or string lines for text files.

JavaScript Example:

```js
const snapshotName = "tcauth-pre-release-check";
const res = await fetch(`${baseUrl}/log/${snapshotName}?page=1&limit=50`, {
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
});
const data = await res.json();
```

---

### 3.6 GET `/log/tcauth/stream` & GET `/log/server/stream`

Open a persistent Server-Sent Events (SSE) connection for live log streaming.

Headers:
- `Authorization: Bearer <token>`, `Accept: text/event-stream` (or cookie session)

Stream Behavior:
- Immediately yields the **last 10 records** upon connection.
- Pushes newly generated log events in real time.
- Sends `: ping\n\n` heartbeat comments every 15 seconds.

Sample Stream Output:

```text
event: log
data: {"timestamp":"2026-09-14T01:31:45+00:00","level":"INFO","event":"LOGIN_SUCCESS","message":"User logged in"}

: ping

event: log
data: {"timestamp":"2026-09-14T01:32:00+00:00","level":"ERROR","event":"TOKEN_EXPIRED","message":"JWT expired"}
```

JavaScript Example (Browser EventSource with Cookie Mode):

```js
// When using Cookie Mode (credentials: "include")
const eventSource = new EventSource(`${baseUrl}/log/tcauth/stream`, {
  withCredentials: true,
});

eventSource.addEventListener("log", (event) => {
  const logRecord = JSON.parse(event.data);
  console.log(`[${logRecord.level}] ${logRecord.event}: ${logRecord.message}`);
});

eventSource.onerror = (err) => {
  console.error("SSE connection error:", err);
};

// To close the stream:
// eventSource.close();
```

JavaScript Example (Fetch ReadableStream for Bearer Token Auth):

```js
// When using Bearer Token in Authorization header
async function streamLogs(onLogReceived, signal) {
  const response = await fetch(`${baseUrl}/log/tcauth/stream`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      Accept: "text/event-stream",
    },
    signal,
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop(); // keep last incomplete chunk

    for (const chunk of lines) {
      const dataLine = chunk.split("\n").find((l) => l.startsWith("data: "));
      if (dataLine) {
        const rawJson = dataLine.replace(/^data:\s*/, "").trim();
        try {
          const record = JSON.parse(rawJson);
          onLogReceived(record);
        } catch (e) {
          console.error("Error parsing log line:", e);
        }
      }
    }
  }
}
```

---

### 3.7 POST `/log/tcauth/reset` & POST `/log/server/reset`

Truncate the target primary log file to 0 bytes and continue logging.

Headers:
- `Authorization: Bearer <token>`

Response (`200 OK`):

```json
{
  "success": true,
  "message": "Primary log 'tcauth' has been reset successfully"
}
```

JavaScript Example:

```js
const res = await fetch(`${baseUrl}/log/tcauth/reset`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
});
const data = await res.json();
console.log(data.message);
```

---

### 3.8 DELETE `/log/{name}`

Delete a stored snapshot file from `logs/store/`.

Headers:
- `Authorization: Bearer <token>`

Path Parameter:
- `name`: The full snapshot name without extension (e.g. `"tcauth-pre-release-check"`).

Response (`204 No Content`):
- Successfully deleted (empty body).

Error Responses:
- `403 Forbidden`: `{ "success": false, "message": "Cannot delete primary log 'tcauth'. Only stored snapshots can be deleted.", "error_code": "log_cannot_delete_primary" }`
- `404 Not Found`: `{ "success": false, "message": "Log snapshot 'old-backup' not found", "error_code": "log_snapshot_not_found" }`

JavaScript Example:

```js
const snapshotName = "tcauth-pre-release-check";
const res = await fetch(`${baseUrl}/log/${snapshotName}`, {
  method: "DELETE",
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
});

if (res.status === 204) {
  console.log("Snapshot deleted successfully");
} else {
  const error = await res.json();
  console.error("Failed to delete snapshot:", error.message);
}
```
