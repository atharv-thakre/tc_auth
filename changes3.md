# `tc-auth` — Centralized Logging System Documentation (`changes3.md`)

This document provides complete instructions for the centralized logging system across three core sections:
1. **Frontend Integration & Implementation Guide** (Direct `/log` routes, live SSE streaming, snapshot UI, reset & delete workflows)
2. **SDK Documentation & Usage Guide** (Python SDK methods, configuration, automatic auth exception logging, lifecycle events, and redaction)
3. **API Documentation & Endpoint Reference** (Comprehensive REST API specifications, request/response models, query parameters, and status codes)

---

# SECTION 1: Frontend Implementation & Integration Guide

This section contains all instructions and code recipes needed by frontend developers to implement the logging dashboard, live log streams, snapshot management, and log resets.

> [!NOTE]
> All endpoints in this guide use direct API routes (`/log/*`). No `/tc-auth` prefix is required when calling the logging service endpoints.

---

### 1.1 Authentication & Authorization

All `/log` routes require administrative privileges (**`superadmin`** role).

#### Sending Credentials
1. **Bearer Token Mode**:
   ```http
   Authorization: Bearer <superadmin_access_token>
   ```
2. **Cookie Mode**:
   Include credentials in your request (`credentials: "include"` for `fetch`, or `withCredentials: true` for `EventSource` / `XMLHttpRequest`).

#### Error Statuses:
- **400 Bad Request (`logging_disabled`)**: Logging is globally disabled via configuration (`logging=False` or `LOGGING=false`).
  ```json
  {
    "success": false,
    "message": "Logging is disabled",
    "error_code": "logging_disabled"
  }
  ```
- **401 Unauthorized (`token_missing` / `token_expired`)**: User is not logged in or token is missing/expired.
  ```json
  {
    "success": false,
    "message": "Missing authorization credentials",
    "error_code": "token_missing"
  }
  ```
- **403 Forbidden (`role_mismatch`)**: User is authenticated but does not possess the `superadmin` role.
  ```json
  {
    "success": false,
    "message": "Role 'user' is not permitted. Required: superadmin",
    "error_code": "role_mismatch"
  }
  ```

---

### 1.2 Route Quick Reference Table

| HTTP Method | Endpoint | Purpose | Success Status | Error Statuses |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/log` | List primary logs (`tcauth`, `server`) and all snapshots in `logs/store/` | `200 OK` | `400`, `401`, `403` |
| `POST` | `/log` | Create a point-in-time snapshot of `tcauth` or `server` | `201 Created` | `400`, `401`, `403`, `409`, `422` |
| `GET` | `/log/tcauth` | Retrieve JSON records from `tcauth.log` (supports `limit`, `offset`) | `200 OK` | `400`, `401`, `403` |
| `GET` | `/log/server` | Retrieve text lines from `server.log` (supports `limit`, `offset`) | `200 OK` | `400`, `401`, `403` |
| `GET` | `/log/{name}` | Retrieve contents of a specific log or snapshot by name | `200 OK` | `400`, `401`, `403`, `404` |
| `GET` | `/log/tcauth/stream` | Real-time Server-Sent Events (SSE) stream for `tcauth.log` | `200 OK` (`text/event-stream`) | `400`, `401`, `403` |
| `GET` | `/log/server/stream` | Real-time Server-Sent Events (SSE) stream for `server.log` | `200 OK` (`text/event-stream`) | `400`, `401`, `403` |
| `POST` | `/log/tcauth/reset` | Truncate `tcauth.log` to 0 bytes and continue logging | `200 OK` | `400`, `401`, `403` |
| `POST` | `/log/server/reset` | Truncate `server.log` to 0 bytes and continue logging | `200 OK` | `400`, `401`, `403` |
| `DELETE` | `/log/{name}` | Delete a stored snapshot file from `logs/store/` | `204 No Content` | `400`, `401`, `403`, `404` |

---

### 1.3 Real-Time SSE Streaming Implementation

The backend streams live log events using Server-Sent Events (SSE).

#### How the Stream Works:
1. **Initial History**: Upon connecting, the server immediately sends the **last 10 records** from the log file.
2. **Live Updates**: As new application events or server outputs occur, the server sends them immediately (`event: log\ndata: <content>\n\n`).
3. **Heartbeat / Keep-Alive**: The server emits `: ping\n\n` comments every 15 seconds so load balancers, proxies, and browsers do not time out idle connections.
4. **Disconnection Cleanup**: When the client closes the connection or navigates away, the server automatically unregisters the stream listener without resource leaks.

#### TypeScript Types & SSE Client Implementation

```typescript
// types/logging.ts
export interface LogRecord {
  timestamp: string;
  level: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL";
  event: string;
  message: string;
  request_id?: string;
  method?: string;
  path?: string;
  status_code?: number;
  client_ip?: string;
  user_agent?: string;
  duration_ms?: number;
  error?: {
    type: string;
    code: string;
    message: string;
    details?: any;
  };
  exception?: {
    type: string;
    message: string;
  };
  stack_trace?: string;
  metadata?: Record<string, any>;
}

/**
 * Connects to the SSE stream using fetch + ReadableStream (supports custom headers like Authorization).
 */
export async function streamApplicationLogs(
  token: string,
  onRecord: (record: LogRecord) => void,
  onError?: (err: any) => void,
  signal?: AbortSignal
) {
  try {
    const response = await fetch("/log/tcauth/stream", {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "text/event-stream",
      },
      signal,
    });

    if (!response.ok) {
      throw new Error(`SSE stream connection failed with status ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error("ReadableStream not supported by browser");

    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() || ""; // Retain incomplete trailing chunk

      for (const eventBlock of events) {
        if (!eventBlock.trim() || eventBlock.startsWith(":")) continue; // Skip keep-alive comments

        const lines = eventBlock.split("\n");
        const dataLine = lines.find((l) => l.startsWith("data: "));
        if (dataLine) {
          const rawJson = dataLine.slice(6);
          try {
            const parsed: LogRecord = JSON.parse(rawJson);
            onRecord(parsed);
          } catch (e) {
            console.warn("Failed to parse JSONL line from stream:", rawJson);
          }
        }
      }
    }
  } catch (err: any) {
    if (err.name !== "AbortError" && onError) {
      onError(err);
    }
  }
}
```

#### React Custom Hook Example (`useLogStream`)

```typescript
import { useEffect, useState, useRef } from "react";
import { LogRecord, streamApplicationLogs } from "./logging";

export function useLogStream(token: string, isPaused: boolean = false) {
  const [logs, setLogs] = useState<LogRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const isPausedRef = useRef(isPaused);
  isPausedRef.current = isPaused;

  useEffect(() => {
    if (!token) return;
    const abortController = new AbortController();

    streamApplicationLogs(
      token,
      (newRecord) => {
        if (!isPausedRef.current) {
          setLogs((prev) => [...prev.slice(-499), newRecord]); // Keep last 500 records
        }
      },
      (err) => setError(err.message),
      abortController.signal
    );

    return () => {
      abortController.abort();
    };
  }, [token]);

  return { logs, error, clearLogs: () => setLogs([]) };
}
```

---

### 1.4 Managing Snapshots & Resets from the Frontend

#### 1. Fetching Summary of Logs & Snapshots
```typescript
async function fetchLogsSummary(token: string) {
  const res = await fetch("/log", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to load logs summary");
  return await res.json();
}
```

**Example Response Data:**
```json
{
  "success": true,
  "primary_logs": [
    {
      "name": "tcauth",
      "source": "tcauth",
      "filename": "tcauth.log",
      "format": "jsonl",
      "size_bytes": 1024,
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
      "size_bytes": 2048,
      "streamable": true,
      "resettable": true,
      "deletable": false,
      "updated_at": "2026-09-14T01:31:45+00:00"
    }
  ],
  "snapshots": [
    {
      "name": "tcauth-oauth-debug-session",
      "source": "tcauth",
      "filename": "tcauth-oauth-debug-session.log",
      "format": "jsonl",
      "size_bytes": 512,
      "streamable": false,
      "resettable": false,
      "deletable": true,
      "created_at": "2026-09-14T01:30:00+00:00"
    }
  ]
}
```

#### 2. Creating a Snapshot
When creating a snapshot, provide only your custom identifier as `name` and the target `source` (`tcauth` or `server`). The system saves it on disk as `{source}-{name}.log` (e.g. `tcauth-oauth-debug-session.log`).

```typescript
async function createSnapshot(name: string, source: "tcauth" | "server", token: string) {
  const res = await fetch("/log", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name, source }),
  });

  if (res.status === 409) {
    throw new Error(`Snapshot with name '${name}' already exists.`);
  }
  if (res.status === 422) {
    throw new Error("Invalid snapshot name. Only letters, numbers, hyphens, and underscores are allowed.");
  }
  if (!res.ok) {
    throw new Error("Failed to create snapshot.");
  }

  return await res.json(); // 201 Created -> returns snapshot with full name: `${source}-${name}`
}
```

#### 3. Resetting a Primary Log (Truncating to 0 bytes)
```typescript
async function resetPrimaryLog(source: "tcauth" | "server", token: string) {
  const res = await fetch(`/log/${source}/reset`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Failed to reset ${source} log`);
  return await res.json();
}
```

#### 4. Deleting a Stored Snapshot
For deleting a snapshot, provide the **full snapshot name without extension** (e.g. `tcauth-oauth-debug-session` or `server-oauth-debug-session` as returned by `GET /log`).

```typescript
async function deleteSnapshot(fullSnapshotName: string, token: string) {
  // fullSnapshotName = "tcauth-oauth-debug-session" (no .log extension)
  const res = await fetch(`/log/${fullSnapshotName}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (res.status === 403) {
    throw new Error("Primary logs ('tcauth', 'server') cannot be deleted.");
  }
  if (res.status === 404) {
    throw new Error("Snapshot not found.");
  }
  if (res.status !== 204) {
    throw new Error("Failed to delete snapshot.");
  }
  return true; // 204 No Content
}
```

---

# SECTION 2: SDK Documentation & Usage Guide

This section covers how to configure and use the logging subsystem in your Python backend code using the `tc-auth` SDK.

### 2.1 Accessing the Logging Service

The logging subsystem is available on your `Auth` instance as both `auth.log` and `auth.logging`:

```python
from tc_auth import Auth
from sqlalchemy import create_engine

engine = create_engine("postgresql://user:pass@localhost:5432/db")
auth = Auth(engine)

# Both aliases point to the central LogService instance:
# auth.log == auth.logging
```

---

### 2.2 Configuring the Logging Service

Call `auth.log.config(...)` during application startup:

```python
auth.log.config(
    logging=True,              # Master toggle (default: True). If False, logging is completely disabled
    logs_dir="logs",           # Base directory (default: 'logs/' in working directory)
    static_mount_logs=False,   # If True, exposes physical logs at GET /logs/*
    level="INFO",              # Minimum level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    console_output=True,       # Echo JSONL events to terminal / stdout
    redact_sensitive=True,     # Recursively redact credentials, tokens, cookies, secrets
    custom_redact_keys=None,   # Optional list of extra keys to redact (e.g. ['ssn', 'pin'])
)
```

> [!NOTE]
> When `logging=False` (or `enabled=False`):
> - All `/log/*` API endpoints immediately return `400 Bad Request` with `error_code: "logging_disabled"`.
> - SDK logging calls (`auth.log.info`, `auth.log.error`, etc.) are silent no-ops.
> - Management calls (`auth.log.list_logs()`, `auth.log.create_snapshot()`, etc.) raise `LoggingDisabledError`.

Read the active configuration at any time:
```python
config = auth.log.load()
print(config)
# {
#   "logging": True,
#   "enabled": True,
#   "logs_dir": "/path/to/project/logs",
#   "store_dir": "/path/to/project/logs/store",
#   "static_mount_logs": False,
#   "level": "INFO",
#   "console_output": True,
#   "redact_sensitive": True,
#   "custom_redact_keys": []
# }
```

---

### 2.3 Application Event Logging (JSONL)

Write structured log records to `tcauth.log`:

```python
# 1. Informational Event
auth.log.info(
    event="USER_ACTION",
    message="User updated profile details",
    request_id="req-12345",
    method="PATCH",
    path="/tc-auth/me",
    client_ip="127.0.0.1",
    metadata={"field": "name", "old_value": "Alice", "new_value": "Alice Smith"},
)

# 2. Debug Event
auth.log.debug(
    event="CACHE_LOOKUP",
    message="Session cache hit",
    metadata={"session_id": 105},
)

# 3. Warning Event
auth.log.warning(
    event="RATE_LIMIT_WARNING",
    message="User approaching hourly attempt threshold",
    client_ip="192.168.1.50",
)

# 4. Error Event with Exception Info
try:
    process_payment()
except Exception as err:
    auth.log.error(
        event="PAYMENT_FAILED",
        message="Stripe payment charge failed",
        exc_info=err,
        metadata={"order_id": "ORD-9876"},
    )

# 5. Critical Event
auth.log.critical(
    event="DB_UNAVAILABLE",
    message="Database connection pool exhausted",
    exc_info=err,
)
```

---

### 2.4 Automatic Authentication & Error Logging

You do not need to manually log standard errors or authentication lifecycles. The `tc-auth` library logs them automatically:

1. **Automatic Error Logging (`auth_exception_handler`)**:
   - Any `AuthError` subclass (e.g. `TokenMissingError`, `InvalidCredentialsError`, `RoleMismatchError`, `UserNotFoundError`, `InvalidFieldError`, etc.) is automatically captured with full HTTP context (`timestamp`, `level="ERROR"`, `event=error_code.upper()`, `method`, `path`, `status_code`, `client_ip`, `user_agent`, `error`, `exception`, and `stack_trace` for 5xx errors).
2. **Lifecycle Events**:
   - `LOGIN_SUCCESS`: User logged in via password or OAuth (includes `client_ip`, `user_agent`, `account_id`, `session_id`).
   - `LOGIN_FAILED`: Failed login attempt (wrong password or missing user).
   - `LOGOUT`: Current session terminated.
   - `LOGOUT_ALL`: All sessions revoked for account.
   - `TOKEN_REFRESHED`: New access/refresh token pair issued.

---

### 2.5 Centralized Automatic Redaction

All log entries pass through centralized recursive redaction. Sensitive keys and pattern matches are automatically converted to `[REDACTED]`:
- **Passwords**: `password`, `password_hash`, `new_password`, `old_password`, `confirm_password`
- **Tokens**: `token`, `access_token`, `refresh_token`, `id_token`, `token_secret`, `token_hash`
- **Secrets & Keys**: `secret`, `secret_key`, `client_secret`, `session_secret`, `private_key`, `api_key`, `apikey`, `csrf_token`
- **OAuth Credentials**: `authorization_code`, `state`, `oauth_state`
- **Cookies**: `cookie`, `cookies`, `set-cookie`
- **Free-text String Patterns**: JWT tokens (`eyJ...`), `Bearer <token>`, and `Basic <token>`

Safe metadata keys (`error_code`, `code`, `event`, `error`, `exception`, `status_code`, `type`, `field`) are preserved to maintain full debug utility.

---

### 2.6 Programmatic Snapshot & File Management

```python
# Create a snapshot copy into logs/store/{source}-{name}.log
auth.log.create_snapshot(name="pre-migration-backup", source="tcauth")

# List all primary logs and snapshots
summary = auth.log.list_logs()

# Read records from a primary log or snapshot
records = auth.log.get_log_content(name="tcauth", limit=100, offset=0)

# Reset a primary log (truncate to 0 bytes)
auth.log.reset_log(source="tcauth")

# Delete a snapshot file
auth.log.delete_snapshot(name="pre-migration-backup")
```

---

### 2.7 Environment Variables Configuration

In `.env`:
```env
# ==========================================================
# LOGGING CONFIGURATION
# ==========================================================
LOGGING=true
LOG_DIR=logs
LOG_STATIC_MOUNT=false
LOG_LEVEL=INFO
LOG_CONSOLE_OUTPUT=true
LOG_REDACT_SENSITIVE=true
```

In `main.py`:
```python
from config import config

auth.log.config(
    logging=config.LOGGING,
    logs_dir=config.LOG_DIR,
    static_mount_logs=config.LOG_STATIC_MOUNT,
    level=config.LOG_LEVEL,
    console_output=config.LOG_CONSOLE_OUTPUT,
    redact_sensitive=config.LOG_REDACT_SENSITIVE,
)
```

Documentation files for SDK usage:
- Markdown Guide: [`usage/logging/logging.md`](file:///d:/Code%20PlayGround/PROJECTS/AUTH_MODULE/usage/logging/logging.md)
- Executable Python Example: [`usage/logging/logging.py`](file:///d:/Code%20PlayGround/PROJECTS/AUTH_MODULE/usage/logging/logging.py)

---

# SECTION 3: API Documentation & Endpoint Reference

This section provides complete REST API endpoint specifications for the logging routes.

API Documentation Reference:
- Route API Specification: [`api_docs/log_route.md`](file:///d:/Code%20PlayGround/PROJECTS/AUTH_MODULE/api_docs/log_route.md)
- API Routes Index: [`api_docs/ROUTES_INDEX.md`](file:///d:/Code%20PlayGround/PROJECTS/AUTH_MODULE/api_docs/ROUTES_INDEX.md)

---

### 3.1 Endpoint Specifications

#### 1. `GET /log`
- **Summary**: Retrieve a summary of primary logs and stored snapshots.
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
      "name": "debug-2026",
      "source": "tcauth",
      "filename": "tcauth-debug-2026.log",
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

#### 2. `POST /log`
- **Summary**: Create a snapshot copy of a primary log file in `logs/store/`.
- **Naming Rule**: On creation, pass only the custom identifier in `name` (e.g. `"oauth-debug-session"`). The backend creates `{source}-{name}.log` (e.g. `tcauth-oauth-debug-session.log`).
- **Headers**: `Authorization: Bearer <token>`, `Content-Type: application/json`
- **Request Body**:
```json
{
  "name": "oauth-debug-session",
  "source": "tcauth"
}
```
- **Validation**:
  - `name`: String, 1–64 characters, regex `^[a-zA-Z0-9_-]+$` (no path traversal `..`, `/`, `\`, `:`).
  - `source`: Literal `"tcauth"` or `"server"`.
- **Response `201 Created`**:
```json
{
  "success": true,
  "message": "Snapshot 'oauth-debug-session' created successfully",
  "snapshot": {
    "name": "tcauth-oauth-debug-session",
    "source": "tcauth",
    "filename": "tcauth-oauth-debug-session.log",
    "format": "jsonl",
    "size_bytes": 4096,
    "created_at": "2026-09-14T01:32:00+00:00"
  }
}
```
- **Error Responses**:
  - `409 Conflict`: Snapshot with given name already exists.
  - `422 Unprocessable Entity`: Invalid source or unsafe name.

---

#### 3. `GET /log/tcauth`
- **Summary**: Retrieve parsed JSON records from `tcauth.log`.
- **Headers**: `Authorization: Bearer <token>`
- **Query Parameters**:
  - `limit`: Integer (optional, 1–5000)
  - `offset`: Integer (optional, default: 0)
- **Response `200 OK`**:
```json
{
  "success": true,
  "filename": "tcauth.log",
  "format": "jsonl",
  "total_records": 250,
  "count": 50,
  "offset": 0,
  "records": [
    {
      "timestamp": "2026-09-14T01:31:45.123456+00:00",
      "level": "ERROR",
      "event": "TOKEN_MISSING",
      "message": "Missing authorization credentials",
      "method": "POST",
      "path": "/tc-auth/logout",
      "status_code": 401,
      "client_ip": "127.0.0.1",
      "user_agent": "Mozilla/5.0 ...",
      "error": {
        "type": "TokenMissingError",
        "code": "token_missing",
        "message": "Missing authorization credentials",
        "details": null
      },
      "exception": {
        "type": "TokenMissingError",
        "message": "Missing authorization credentials"
      }
    }
  ]
}
```

---

#### 4. `GET /log/server`
- **Summary**: Retrieve lines from `server.log`.
- **Headers**: `Authorization: Bearer <token>`
- **Query Parameters**:
  - `limit`: Integer (optional, 1–5000)
  - `offset`: Integer (optional, default: 0)
- **Response `200 OK`**:
```json
{
  "success": true,
  "filename": "server.log",
  "format": "text",
  "total_records": 500,
  "count": 100,
  "offset": 0,
  "records": [
    "INFO:     Started server process [14568]",
    "INFO:     Waiting for application startup.",
    "INFO:     Application startup complete.",
    "INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)"
  ]
}
```

---

#### 5. `GET /log/{name}`
- **Summary**: Retrieve contents of a snapshot or primary log by name.
- **Headers**: `Authorization: Bearer <token>`
- **Path Parameter**: `name`
  - For primary logs: `"tcauth"` or `"server"`.
  - For stored snapshots: The **full snapshot filename without extension** (e.g. `"tcauth-oauth-debug-session"` or `"server-oauth-debug-session"`).
- **Response `200 OK`**: Returns parsed JSON array for JSONL logs or string lines for text logs.
- **Error Response**: `404 Not Found` if snapshot does not exist.

---

#### 6. `GET /log/tcauth/stream` & `GET /log/server/stream`
- **Summary**: Server-Sent Events (SSE) stream for real-time log monitoring.
- **Headers**: `Authorization: Bearer <token>`, `Accept: text/event-stream`
- **Response `200 OK`**: Content-Type `text/event-stream`, Cache-Control `no-cache`, Connection `keep-alive`.
- **SSE Stream Protocol**:
```text
event: log
data: {"timestamp":"2026-09-14T01:31:45+00:00","level":"INFO","event":"LOGIN_SUCCESS","message":"User logged in"}

: ping

```

---

#### 7. `POST /log/tcauth/reset` & `POST /log/server/reset`
- **Summary**: Truncate primary log file to 0 bytes and continue logging.
- **Headers**: `Authorization: Bearer <token>`
- **Response `200 OK`**:
```json
{
  "success": true,
  "message": "Primary log 'tcauth' has been reset successfully"
}
```

---

#### 8. `DELETE /log/{name}`
- **Summary**: Delete a stored snapshot file from `logs/store/`.
- **Headers**: `Authorization: Bearer <token>`
- **Path Parameter**: `name` (the **full snapshot name without extension**, e.g. `"tcauth-oauth-debug-session"`).
- **Response `204 No Content`**
- **Error Responses**:
  - `403 Forbidden`: If `{name}` is `"tcauth"` or `"server"` (primary logs cannot be deleted).
  - `404 Not Found`: If snapshot file is not found in `logs/store/`.
