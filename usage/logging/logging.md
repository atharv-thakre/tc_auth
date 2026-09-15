# `tc-auth` Logging System Guide

The `tc-auth` logging system provides structured **JSONL** application/auth event logging (`tcauth.log`) and standard formatted **Uvicorn** server log capture (`server.log`), complete with real-time SSE streaming, snapshot management, automatic sensitive data redaction, and protected FastAPI endpoints.

---

## 1. Directory Structure

```text
logs/
├── tcauth.log                 # Primary application log (JSONL)
├── server.log                 # Primary server output log (Text)
└── store/                     # Snapshots directory
    ├── tcauth-{name}.log
    └── server-{name}.log
```

---

## 2. Configuration & Methods

Configure via `auth.log.config(...)` or `auth.logging.config(...)`:

```python
auth.log.config(
    logging=True,              # Master toggle (default: True). Set False to disable logging
    logs_dir="logs",           # Base directory (default: 'logs/' in working directory)
    static_mount_logs=False,   # If True, exposes logs/ at GET /logs/*
    level="INFO",              # DEBUG, INFO, WARNING, ERROR, CRITICAL
    console_output=True,       # Echo JSONL events to stdout
    redact_sensitive=True,     # Recursively redact tokens, passwords, cookies, secrets
)
```

> [!NOTE]
> **Disabled Mode (`logging=False` / `enabled=False`)**:
> - SDK logging calls (`auth.log.info`, `auth.log.error`, etc.) become silent no-ops.
> - SDK management calls (`auth.log.list_logs()`, `auth.log.create_snapshot()`, etc.) raise `LoggingDisabledError`.
> - All `/log/*` API endpoints return HTTP `400 Bad Request` with `{"success": false, "message": "Logging is disabled", "error_code": "logging_disabled"}`.

---

## 3. Application Logging (JSONL)

Every line in `tcauth.log` is an independently valid JSON object:

```python
auth.log.info(
    event="LOGIN_SUCCESS",
    message="User logged in",
    request_id="req-12345",
    method="POST",
    path="/tc-auth/login/password",
    client_ip="127.0.0.1",
    metadata={"account_id": 42},
)
```

Generated JSONL line:
```json
{"timestamp": "2026-09-14T01:00:00.000Z", "level": "INFO", "event": "LOGIN_SUCCESS", "message": "User logged in", "request_id": "req-12345", "method": "POST", "path": "/tc-auth/login/password", "client_ip": "127.0.0.1", "metadata": {"account_id": 42}}
```

---

## 4. Centralized Redaction

Sensitive fields are never written to disk in plain text. Any dictionary keys or values matching sensitive patterns (passwords, JWTs, Bearer tokens, cookies, secrets, hashes) are replaced with `[REDACTED]`:

```python
auth.log.info(
    event="AUTH_ATTEMPT",
    message="Processing login",
    metadata={"password": "mypassword", "access_token": "eyJ..."},
)
```

Logged output:
```json
{"timestamp": "...", "level": "INFO", "event": "AUTH_ATTEMPT", "message": "Processing login", "metadata": {"password": "[REDACTED]", "access_token": "[REDACTED]"}}
```

---

## 5. API Endpoints

All management endpoints require administrative privilege (`superadmin` role).
If logging is disabled via `logging=False`, all endpoints return `400 Bad Request` with `{"success": false, "message": "Logging is disabled", "error_code": "logging_disabled"}`.

Prefix: `/tc-auth/log` (or `/log` depending on `include_routes` prefix).

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `GET` | `/log` | List primary logs & stored snapshots | `200 OK` (`400` if disabled) |
| `POST` | `/log` | Create a snapshot (`{ "name": "...", "source": "tcauth" }`) | `201 Created` (`400` if disabled) |
| `GET` | `/log/tcauth` | Get `tcauth.log` records (supports `limit`, `offset`) | `200 OK` (`400` if disabled) |
| `GET` | `/log/server` | Get `server.log` lines (supports `limit`, `offset`) | `200 OK` (`400` if disabled) |
| `GET` | `/log/{name}` | Get specific snapshot or primary log content | `200 OK` (`400` if disabled) |
| `GET` | `/log/tcauth/stream` | Server-Sent Events (SSE) stream for `tcauth.log` | `200 OK` (`400` if disabled) |
| `GET` | `/log/server/stream` | Server-Sent Events (SSE) stream for `server.log` | `200 OK` (`400` if disabled) |
| `POST` | `/log/tcauth/reset` | Truncate `tcauth.log` to 0 bytes and continue logging | `200 OK` (`400` if disabled) |
| `POST` | `/log/server/reset` | Truncate `server.log` to 0 bytes and continue logging | `200 OK` (`400` if disabled) |
| `DELETE` | `/log/{name}` | Delete snapshot from `logs/store/` | `204 No Content` (`400` if disabled) |

---

## 6. Server-Sent Events (SSE)

Clients can connect to `/tc-auth/log/tcauth/stream` or `/tc-auth/log/server/stream`:

1. Sends the last 10 records immediately on connection.
2. Streams newly logged records in real-time (`event: log\ndata: {...}\n\n`).
3. Sends periodic keep-alive `: ping\n\n` comments.
