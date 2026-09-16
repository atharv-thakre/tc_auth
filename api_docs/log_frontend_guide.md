# Logging System — Frontend Integration & Implementation Guide

This guide provides frontend engineers with a complete, production-ready implementation reference for integrating the `tc-auth` Centralized Logging Subsystem into client applications (React, Next.js, Vue, Svelte, or Vanilla JavaScript/TypeScript).

---

## 1. Architectural Overview & Protocols

The `tc-auth` logging system exposes an administrative subsystem under `/log/*` (or `/tc-auth/log/*` if mounted with prefix).

```text
Backend Log Store
├── logs/tcauth.log            <--- Streamable JSONL structured application & auth events
├── logs/server.log            <--- Streamable raw text lines from Uvicorn / server runtime
└── logs/store/
    ├── tcauth-{name}.log      <--- Point-in-time snapshot of application logs
    └── server-{name}.log      <--- Point-in-time snapshot of server logs
```

### 1.1 Authentication & Authorization
All logging routes require administrative access (**`superadmin`** role).
1. **Bearer Token Authentication**:
   Include standard authorization header:
   ```http
   Authorization: Bearer <superadmin_access_token>
   ```
2. **HttpOnly Cookie Authentication**:
   Ensure requests include credentials:
   - `fetch(url, { credentials: "include" })`
   - `axios.get(url, { withCredentials: true })`
   - `new EventSource(url, { withCredentials: true })`

### 1.2 Disabled Logging Mode (`LOGGING=false`)
If logging is disabled on the backend via configuration (`logging=False` or `LOGGING=false` in `.env`), **all** `/log/*` endpoints immediately return `400 Bad Request`:
```json
{
  "success": false,
  "message": "Logging is disabled",
  "error_code": "logging_disabled"
}
```

---

## 2. API Routes Matrix & Quick Reference

| HTTP Method | Endpoint | Description | Success Status | Error Statuses |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/log` | List primary logs (`tcauth`, `server`) and all snapshots in `logs/store/` | `200 OK` | `400`, `401`, `403` |
| `POST` | `/log` | Create a snapshot copy of `tcauth` or `server` in `logs/store/` | `201 Created` | `400`, `401`, `403`, `409`, `422` |
| `GET` | `/log/tcauth` | Retrieve paginated JSON records from `tcauth.log` | `200 OK` | `400`, `401`, `403` |
| `GET` | `/log/server` | Retrieve paginated text lines from `server.log` | `200 OK` | `400`, `401`, `403` |
| `GET` | `/log/{name}` | Retrieve records or text lines of a primary log or snapshot by name | `200 OK` | `400`, `401`, `403`, `404` |
| `GET` | `/log/tcauth/stream` | Real-time Server-Sent Events (SSE) stream for `tcauth.log` | `200 OK` (`text/event-stream`) | `400`, `401`, `403` |
| `GET` | `/log/server/stream` | Real-time Server-Sent Events (SSE) stream for `server.log` | `200 OK` (`text/event-stream`) | `400`, `401`, `403` |
| `POST` | `/log/tcauth/reset` | Truncate `tcauth.log` to 0 bytes and continue logging | `200 OK` | `400`, `401`, `403` |
| `POST` | `/log/server/reset` | Truncate `server.log` to 0 bytes and continue logging | `200 OK` | `400`, `401`, `403` |
| `DELETE` | `/log/{name}` | Delete a stored snapshot file from `logs/store/` | `204 No Content` | `400`, `401`, `403`, `404` |

---

## 3. Snapshot Naming Conventions

> [!IMPORTANT]
> **Snapshot Creation vs Retrieval & Deletion Naming**:
> - **When Creating (`POST /log`)**:
>   Send only your custom identifier as `name` in the request body (e.g., `{"name": "pre-deploy-backup", "source": "tcauth"}`).
>   The physical file created on disk is `tcauth-pre-deploy-backup.log` (format: `{source}-{name}.log`).
> - **When Fetching (`GET /log/{name}`) or Deleting (`DELETE /log/{name}`)**:
>   Pass the **full snapshot name without extension** as the path parameter:
>   - Correct: `GET /log/tcauth-pre-deploy-backup`
>   - Correct: `DELETE /log/tcauth-pre-deploy-backup`
>   - Primary logs: `GET /log/tcauth` or `GET /log/server`

---

## 4. TypeScript Type Definitions

Save these types in your project (e.g. `src/types/logging.ts`):

```typescript
export type LogLevel = "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL";
export type LogSource = "tcauth" | "server";

export interface LogRecordError {
  type: string;
  code: string;
  message: string;
  details?: Record<string, any> | null;
}

export interface LogRecordException {
  type: string;
  message: string;
}

export interface TcAuthLogRecord {
  timestamp: string;
  level: LogLevel;
  event: string;
  message: string;
  request_id?: string;
  method?: string;
  path?: string;
  status_code?: number;
  client_ip?: string;
  user_agent?: string;
  duration_ms?: number;
  provider?: string;
  operation?: string;
  environment?: string;
  error?: LogRecordError;
  exception?: LogRecordException;
  stack_trace?: string;
  metadata?: Record<string, any>;
  [key: string]: any;
}

export interface PrimaryLogSummary {
  name: "tcauth" | "server";
  source: "tcauth" | "server";
  filename: string;
  format: "jsonl" | "text";
  size_bytes: number;
  streamable: boolean;
  resettable: boolean;
  deletable: boolean;
  updated_at: string | null;
}

export interface SnapshotSummary {
  name: string;             // e.g. "tcauth-pre-deploy-backup"
  source: string;           // "tcauth" | "server" | "unknown"
  filename: string;         // e.g. "tcauth-pre-deploy-backup.log"
  format: "jsonl" | "text";
  size_bytes: number;
  streamable: boolean;
  resettable: boolean;
  deletable: boolean;
  created_at: string;
  updated_at: string;
}

export interface LogsOverviewResponse {
  success: boolean;
  primary_logs: PrimaryLogSummary[];
  snapshots: SnapshotSummary[];
}

export interface CreateSnapshotRequest {
  name: string;             // 1-64 chars: ^[a-zA-Z0-9_-]+$
  source: "tcauth" | "server";
}

export interface CreateSnapshotResponse {
  success: boolean;
  message: string;
  snapshot: {
    name: string;           // Full name without .log (e.g. "tcauth-pre-deploy-backup")
    source: "tcauth" | "server";
    filename: string;       // Physical file (e.g. "tcauth-pre-deploy-backup.log")
    format: "jsonl" | "text";
    size_bytes: number;
    created_at: string;
  };
}

export interface GetLogContentResponse<T = TcAuthLogRecord | string> {
  success: boolean;
  filename: string;
  format: "jsonl" | "text";
  total_records: number;
  page: number;
  limit: number;
  total_pages: number;
  count: number;
  has_next: boolean;
  has_prev: boolean;
  offset: number;
  records: T[];
}

export interface GenericActionResponse {
  success: boolean;
  message: string;
}

export interface LoggingApiErrorResponse {
  success: false;
  message: string;
  error_code: string;
  details?: any;
}
```

---

## 5. Endpoints: Detailed Requests & Responses

### 5.1 `GET /log` — Retrieve System Logs Overview
Fetches metadata, file sizes, timestamps, and permissions for primary logs and saved snapshots.

- **Request**:
  ```http
  GET /log HTTP/1.1
  Host: api.example.com
  Authorization: Bearer <token>
  Accept: application/json
  ```
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
        "updated_at": "2026-09-15T10:00:00+00:00"
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
        "updated_at": "2026-09-15T10:00:00+00:00"
      }
    ],
    "snapshots": [
      {
        "name": "tcauth-pre-release-check",
        "source": "tcauth",
        "filename": "tcauth-pre-release-check.log",
        "format": "jsonl",
        "size_bytes": 1024,
        "streamable": false,
        "resettable": false,
        "deletable": true,
        "created_at": "2026-09-15T09:30:00+00:00",
        "updated_at": "2026-09-15T09:30:00+00:00"
      }
    ]
  }
  ```

---

### 5.2 `POST /log` — Create a Point-in-Time Snapshot
Copies the current content of `tcauth.log` or `server.log` into `logs/store/{source}-{name}.log`.

- **Request**:
  ```http
  POST /log HTTP/1.1
  Host: api.example.com
  Authorization: Bearer <token>
  Content-Type: application/json

  {
    "name": "oauth-debug-session",
    "source": "tcauth"
  }
  ```
- **Validation**:
  - `name`: 1–64 characters, letters, numbers, dashes, and underscores only (`^[a-zA-Z0-9_-]+$`).
  - `source`: `"tcauth"` or `"server"`.
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
      "created_at": "2026-09-15T10:15:00+00:00"
    }
  }
  ```
- **Errors**:
  - `409 Conflict`: `{"success": false, "message": "Log snapshot 'oauth-debug-session' already exists", "error_code": "log_snapshot_already_exists"}`
  - `422 Unprocessable Entity`: `{"success": false, "message": "Invalid log snapshot name...", "error_code": "invalid_log_name"}`

---

### 5.3 `GET /log/tcauth` — Read Application JSONL Records
Reads parsed JSON log events with page and limit pagination.

- **Query Parameters**:
  - `page` (*integer, optional*): Page number (1-based, default: 1).
  - `limit` (*integer, optional*): Maximum records per page (1–5000, default: 50).
- **Request**:
  ```http
  GET /log/tcauth?page=1&limit=50 HTTP/1.1
  Authorization: Bearer <token>
  ```
- **Response `200 OK`**:
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
        "timestamp": "2026-09-15T10:14:22.123456+00:00",
        "level": "INFO",
        "event": "LOGIN_SUCCESS",
        "message": "User authenticated via password",
        "request_id": "req-9876",
        "method": "POST",
        "path": "/tc-auth/login/password",
        "status_code": 200,
        "client_ip": "127.0.0.1",
        "user_agent": "Mozilla/5.0 ...",
        "metadata": {
          "account_id": 42
        }
      }
    ]
  }
  ```

---

### 5.4 `GET /log/server` — Read Uvicorn Server Logs
Reads text lines from `server.log`.

- **Query Parameters**:
  - `page` (*integer, optional*): Page number (1-based, default: 1).
  - `limit` (*integer, optional*): Maximum lines per page (1–5000, default: 50).
- **Response `200 OK`**:
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
      "INFO:     Started server process [19404]",
      "INFO:     Waiting for application startup.",
      "INFO:     Application startup complete.",
      "INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)"
    ]
  }
  ```

---

### 5.5 `GET /log/{name}` — Read Specific Snapshot or Log
Retrieves the content of any stored snapshot using its full identifier.

- **Path Parameter**: `name` (e.g. `tcauth-oauth-debug-session`, `server-pre-deploy`, `tcauth`, `server`).
- **Response `200 OK`**: Returns JSON array for JSONL logs or string array for text logs.
- **Error `404 Not Found`**:
  ```json
  {
    "success": false,
    "message": "Log snapshot 'invalid-name' not found",
    "error_code": "log_snapshot_not_found"
  }
  ```

---

### 5.6 `POST /log/tcauth/reset` & `POST /log/server/reset` — Reset Primary Log
Truncates the primary log file to 0 bytes and keeps logger handles open.

- **Request**:
  ```http
  POST /log/tcauth/reset HTTP/1.1
  Authorization: Bearer <token>
  ```
- **Response `200 OK`**:
  ```json
  {
    "success": true,
    "message": "Primary log 'tcauth' has been reset successfully"
  }
  ```

---

### 5.7 `DELETE /log/{name}` — Delete Stored Snapshot
Permanently deletes a snapshot file from `logs/store/`.

- **Path Parameter**: `name` (the full snapshot name, e.g. `tcauth-oauth-debug-session`).
- **Response `204 No Content`**
- **Error `403 Forbidden`** (if attempting to delete primary logs):
  ```json
  {
    "success": false,
    "message": "Cannot delete primary log 'tcauth'. Only stored snapshots can be deleted.",
    "error_code": "log_cannot_delete_primary"
  }
  ```

---

## 6. Real-Time SSE Streaming Implementation

The backend streams live log lines over Server-Sent Events (SSE).

### 6.1 SSE Protocol Details:
- **Initial Burst**: Returns the **last 10 records** on connection so clients immediately see recent history.
- **Live Events**: Emits `event: log\ndata: <JSON or text>\n\n` as new records occur.
- **Heartbeat Pings**: Sends `: ping\n\n` every 15 seconds to prevent browser and reverse-proxy timeouts.
- **Connection Closure**: When the client aborts, the backend cleanly drops the subscriber queue without memory leaks.

### 6.2 SSE Streaming Client (`fetch` + `ReadableStream`)
Standard `EventSource` in browsers does not allow sending custom headers like `Authorization: Bearer <token>`. The following helper uses `fetch` with `ReadableStream` for universal support:

```typescript
// src/services/loggingStream.ts
import { TcAuthLogRecord } from "../types/logging";

export interface StreamOptions {
  source?: "tcauth" | "server";
  token?: string;
  onRecord: (record: TcAuthLogRecord | string) => void;
  onError?: (err: Error) => void;
  signal?: AbortSignal;
}

export async function connectLogStream({
  source = "tcauth",
  token,
  onRecord,
  onError,
  signal,
}: StreamOptions): Promise<void> {
  const url = `/log/${source}/stream`;
  const headers: Record<string, string> = {
    Accept: "text/event-stream",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      method: "GET",
      headers,
      credentials: "include", // Supports cookie auth
      signal,
    });

    if (!response.ok) {
      const errorJson = await response.json().catch(() => null);
      const message = errorJson?.message || `SSE failed with HTTP ${response.status}`;
      throw new Error(message);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("ReadableStream not supported by client environment");
    }

    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() || ""; // Retain incomplete trailing fragment

      for (const chunk of chunks) {
        const trimmed = chunk.trim();
        if (!trimmed || trimmed.startsWith(":")) {
          // Heartbeat comment ': ping', ignore
          continue;
        }

        const lines = chunk.split("\n");
        const dataLine = lines.find((l) => l.startsWith("data: "));
        if (!dataLine) continue;

        const rawData = dataLine.slice(6);
        if (source === "tcauth") {
          try {
            const parsed: TcAuthLogRecord = JSON.parse(rawData);
            onRecord(parsed);
          } catch {
            onRecord(rawData);
          }
        } else {
          onRecord(rawData);
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

---

## 7. React Custom Hook: `useLogStream`

```typescript
// src/hooks/useLogStream.ts
import { useEffect, useState, useRef, useCallback } from "react";
import { TcAuthLogRecord } from "../types/logging";
import { connectLogStream } from "../services/loggingStream";

interface UseLogStreamOptions {
  source?: "tcauth" | "server";
  token?: string;
  maxBuffer?: number;
}

export function useLogStream({
  source = "tcauth",
  token,
  maxBuffer = 500,
}: UseLogStreamOptions = {}) {
  const [logs, setLogs] = useState<(TcAuthLogRecord | string)[]>([]);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const isPausedRef = useRef(isPaused);
  isPausedRef.current = isPaused;

  const clearLogs = useCallback(() => setLogs([]), []);

  useEffect(() => {
    const controller = new AbortController();
    setIsConnected(true);
    setError(null);

    connectLogStream({
      source,
      token,
      onRecord: (record) => {
        if (!isPausedRef.current) {
          setLogs((prev) => {
            const next = [...prev, record];
            return next.length > maxBuffer ? next.slice(-maxBuffer) : next;
          });
        }
      },
      onError: (err) => {
        setError(err.message);
        setIsConnected(false);
      },
      signal: controller.signal,
    });

    return () => {
      controller.abort();
      setIsConnected(false);
    };
  }, [source, token, maxBuffer]);

  return {
    logs,
    isConnected,
    isPaused,
    setIsPaused,
    error,
    clearLogs,
  };
}
```

---

## 8. Complete React Logging Dashboard Component

A production-ready logging dashboard interface with live streaming, level filtering, snapshot creation, and log reset:

```tsx
// src/components/LoggingDashboard.tsx
import React, { useState, useEffect } from "react";
import { useLogStream } from "../hooks/useLogStream";
import {
  LogsOverviewResponse,
  LogLevel,
  TcAuthLogRecord,
} from "../types/logging";

interface Props {
  token: string;
}

export const LoggingDashboard: React.FC<Props> = ({ token }) => {
  const [source, setSource] = useState<"tcauth" | "server">("tcauth");
  const [levelFilter, setLevelFilter] = useState<LogLevel | "ALL">("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [overview, setOverview] = useState<LogsOverviewResponse | null>(null);
  const [snapshotInput, setSnapshotInput] = useState<string>("");
  const [isCreatingSnapshot, setIsCreatingSnapshot] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const { logs, isConnected, isPaused, setIsPaused, error, clearLogs } =
    useLogStream({ source, token });

  // Load summary overview
  const loadOverview = async () => {
    try {
      const res = await fetch("/log", {
        headers: { Authorization: `Bearer ${token}` },
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setOverview(data);
      }
    } catch (e) {
      console.error("Failed to load logs overview", e);
    }
  };

  useEffect(() => {
    loadOverview();
  }, [token]);

  // Create Snapshot Handler
  const handleCreateSnapshot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!snapshotInput.trim()) return;

    setIsCreatingSnapshot(true);
    setActionMessage(null);
    try {
      const res = await fetch("/log", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({ name: snapshotInput.trim(), source }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "Failed to create snapshot");

      setSnapshotInput("");
      setActionMessage(`Snapshot created: ${data.snapshot.name}`);
      loadOverview();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setIsCreatingSnapshot(false);
    }
  };

  // Reset Primary Log Handler
  const handleResetLog = async () => {
    if (!window.confirm(`Are you sure you want to reset ${source}.log?`)) return;

    try {
      const res = await fetch(`/log/${source}/reset`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        credentials: "include",
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message);

      clearLogs();
      setActionMessage(`${source}.log was reset successfully.`);
      loadOverview();
    } catch (err: any) {
      alert(err.message);
    }
  };

  // Delete Snapshot Handler
  const handleDeleteSnapshot = async (snapshotName: string) => {
    if (!window.confirm(`Delete snapshot '${snapshotName}'?`)) return;

    try {
      const res = await fetch(`/log/${snapshotName}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
        credentials: "include",
      });
      if (!res.ok && res.status !== 204) {
        const data = await res.json();
        throw new Error(data.message);
      }
      loadOverview();
    } catch (err: any) {
      alert(err.message);
    }
  };

  // Filtered log list
  const filteredLogs = logs.filter((log) => {
    if (typeof log === "string") {
      return log.toLowerCase().includes(searchQuery.toLowerCase());
    }
    const record = log as TcAuthLogRecord;
    const matchesLevel =
      levelFilter === "ALL" || record.level === levelFilter;
    const matchesSearch =
      !searchQuery ||
      record.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
      record.event.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (record.path && record.path.toLowerCase().includes(searchQuery.toLowerCase()));

    return matchesLevel && matchesSearch;
  });

  return (
    <div style={{ padding: "24px", fontFamily: "monospace", backgroundColor: "#121212", color: "#e0e0e0" }}>
      <h2>Centralized Log Monitor</h2>

      {/* Top Controls Bar */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "16px", flexWrap: "wrap" }}>
        <button
          onClick={() => setSource("tcauth")}
          style={{ fontWeight: source === "tcauth" ? "bold" : "normal" }}
        >
          tcauth.log (JSONL)
        </button>
        <button
          onClick={() => setSource("server")}
          style={{ fontWeight: source === "server" ? "bold" : "normal" }}
        >
          server.log (Text)
        </button>

        <button onClick={() => setIsPaused(!isPaused)}>
          {isPaused ? "Resume Stream" : "Pause Stream"}
        </button>
        <button onClick={clearLogs}>Clear Window</button>
        <button onClick={handleResetLog} style={{ backgroundColor: "#8b0000", color: "#fff" }}>
          Reset Log File
        </button>
      </div>

      {/* Filters Bar */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "16px" }}>
        {source === "tcauth" && (
          <select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value as any)}
          >
            <option value="ALL">ALL LEVELS</option>
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
            <option value="CRITICAL">CRITICAL</option>
          </select>
        )}

        <input
          type="text"
          placeholder="Filter messages, paths, events..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{ flex: 1, padding: "4px 8px" }}
        />
      </div>

      {error && <div style={{ color: "#ff6b6b", marginBottom: "12px" }}>Error: {error}</div>}
      {actionMessage && <div style={{ color: "#51cf66", marginBottom: "12px" }}>{actionMessage}</div>}

      {/* Live Log Stream Terminal */}
      <div
        style={{
          height: "400px",
          overflowY: "auto",
          backgroundColor: "#1e1e1e",
          padding: "12px",
          borderRadius: "6px",
          border: "1px solid #333",
        }}
      >
        {filteredLogs.length === 0 ? (
          <div style={{ color: "#777" }}>No log records found matching criteria...</div>
        ) : (
          filteredLogs.map((log, index) => (
            <div key={index} style={{ marginBottom: "6px", lineHeight: "1.4" }}>
              {typeof log === "string" ? (
                <span>{log}</span>
              ) : (
                <span>
                  <span style={{ color: "#888" }}>[{log.timestamp}]</span>{" "}
                  <strong
                    style={{
                      color:
                        log.level === "ERROR" || log.level === "CRITICAL"
                          ? "#ff6b6b"
                          : log.level === "WARNING"
                          ? "#fcc419"
                          : "#51cf66",
                    }}
                  >
                    [{log.level}]
                  </strong>{" "}
                  <span style={{ color: "#339af0" }}>[{log.event}]</span>: {log.message}
                  {log.path && <span style={{ color: "#868e96" }}> ({log.method} {log.path})</span>}
                </span>
              )}
            </div>
          ))
        )}
      </div>

      {/* Snapshot Manager */}
      <h3 style={{ marginTop: "24px" }}>Snapshot Management</h3>
      <form onSubmit={handleCreateSnapshot} style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
        <input
          type="text"
          placeholder="New snapshot identifier (e.g. debug-run-1)"
          value={snapshotInput}
          onChange={(e) => setSnapshotInput(e.target.value)}
          required
        />
        <button type="submit" disabled={isCreatingSnapshot}>
          {isCreatingSnapshot ? "Creating..." : "Save Snapshot"}
        </button>
      </form>

      {/* Stored Snapshots Table */}
      {overview?.snapshots && overview.snapshots.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #444" }}>
              <th style={{ padding: "8px" }}>Snapshot Name</th>
              <th style={{ padding: "8px" }}>Source</th>
              <th style={{ padding: "8px" }}>Size</th>
              <th style={{ padding: "8px" }}>Created At</th>
              <th style={{ padding: "8px" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {overview.snapshots.map((snap) => (
              <tr key={snap.name} style={{ borderBottom: "1px solid #222" }}>
                <td style={{ padding: "8px" }}>{snap.name}</td>
                <td style={{ padding: "8px" }}>{snap.source}</td>
                <td style={{ padding: "8px" }}>{(snap.size_bytes / 1024).toFixed(1)} KB</td>
                <td style={{ padding: "8px" }}>{snap.created_at}</td>
                <td style={{ padding: "8px" }}>
                  <button onClick={() => handleDeleteSnapshot(snap.name)} style={{ color: "#ff6b6b" }}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
```
