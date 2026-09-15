# Logging Configuration Routes — Frontend Integration Guide

This document details the frontend integration guide for the **Dashboard Logging Configuration Routes** in `tc_auth`, updated with support for **Terminal Print Capture** (`capture_terminal`) and **Regex-Based Redaction** (`redact_patterns`):

1. **`GET /tc-auth/config/load/`** — Fetch current live configuration (including logging state).
2. **`POST /tc-auth/config/logging`** — Dynamically update logging service configuration at runtime.

---

## 1. Route Specifications

All endpoints require:
- **Authorization**: `Bearer <access_token>`
- **Role Requirement**: `superadmin`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/tc-auth/config/load/` | Loads current system configuration containing `logging` state |
| `POST` | `/tc-auth/config/logging` | Updates logging parameters dynamically (partial or full) |

---

## 2. API Contracts & Schemas

### 2.1 `GET /tc-auth/config/load/`

Retrieves the live in-memory configuration of `tc_auth` services.

- **Request Headers**:
  ```http
  Authorization: Bearer <superadmin_access_token>
  ```

- **Response (`200 OK`)**:
  ```json
  {
    "email": { ... },
    "github": { ... },
    "google": { ... },
    "discord": { ... },
    "jwt": { ... },
    "cookie": { ... },
    "logging": {
      "logging": true,
      "logs_dir": "/path/to/project/logs",
      "store_dir": "/path/to/project/logs/store",
      "static_mount_logs": false,
      "level": "INFO",
      "console_output": true,
      "capture_terminal": true,
      "redact_sensitive": true,
      "redact_patterns": [
        "(?i)authorization:\\s*bearer\\s+\\S+",
        "(?i)api[_-]?key\\s*[:=]\\s*\\S+",
        "(?i)token\\s*[:=]\\s*\\S+"
      ]
    }
  }
  ```

---

### 2.2 `POST /tc-auth/config/logging`

Dynamically updates logging service settings. Supports partial updates; omitted fields retain their existing settings.

- **Request Headers**:
  ```http
  Content-Type: application/json
  Authorization: Bearer <superadmin_access_token>
  ```

- **Request Body Fields**:

  | Field | Type | Required | Description |
  |---|---|---|---|
  | `logging` | `boolean` | Optional | Master toggle to enable (`true`) or disable (`false`) all logging. |
  | `level` | `string` | Optional | Log level threshold (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). |
  | `console_output` | `boolean` | Optional | Echo JSONL application events to terminal/stdout. |
  | `capture_terminal` | `boolean` | Optional | When `true`, all `print()` outputs produced anywhere in the process are captured into `server.log` while still printing to terminal. |
  | `redact_sensitive` | `boolean` | Optional | Mask standard tokens, passwords, cookies, and secret keys. |
  | `redact_patterns` | `string[]` | Optional | Array of regular expression patterns to redact in application logs and captured prints. Evaluated independently from `redact_sensitive`. |
  | `static_mount_logs` | `boolean` | Optional | Expose logs directory at `/logs` static route. |
  | `logs_dir` | `string` | Optional | Base directory for log storage. |

- **Example Request Payload (Full Update)**:
  ```json
  {
    "logging": true,
    "level": "INFO",
    "console_output": true,
    "capture_terminal": true,
    "redact_sensitive": true,
    "redact_patterns": [
      "(?i)authorization:\\s*bearer\\s+\\S+",
      "(?i)token\\s*[:=]\\s*\\S+"
    ],
    "static_mount_logs": false,
    "logs_dir": "logs"
  }
  ```

- **Example Request Payload (Toggle Terminal Capture Only)**:
  ```json
  {
    "capture_terminal": true
  }
  ```

- **Success Response (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Logging service configured successfully"
  }
  ```

- **Error Responses**:
  - `400 Bad Request` (`InvalidConfigError`): Invalid level name, invalid regex pattern (e.g. `[invalid`), or non-boolean values.
  - `401 Unauthorized`: Missing or invalid Bearer token.
  - `403 Forbidden`: User does not possess `superadmin` role.

---

## 3. Frontend Implementation Guide

### 3.1 TypeScript Types

```typescript
export type LogLevel = "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL";

export interface LoggingState {
  logging: boolean;
  logs_dir: string;
  store_dir: string;
  static_mount_logs: boolean;
  level: LogLevel;
  console_output: boolean;
  capture_terminal: boolean;
  redact_sensitive: boolean;
  redact_patterns: string[];
}

export interface LoggingConfigUpdatePayload {
  logging?: boolean;
  level?: LogLevel;
  console_output?: boolean;
  capture_terminal?: boolean;
  redact_sensitive?: boolean;
  redact_patterns?: string[];
  static_mount_logs?: boolean;
  logs_dir?: string;
}

export interface ConfigLoadResponse {
  logging: LoggingState | null;
  [key: string]: any;
}

export interface ApiResponse {
  success: boolean;
  message: string;
}
```

---

### 3.2 API Client Functions

```typescript
const BASE_URL = "/tc-auth";

/**
 * Loads current logging configuration from GET /config/load/
 */
export async function getLoggingConfig(token: string): Promise<LoggingState> {
  const response = await fetch(`${BASE_URL}/config/load/`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.message || `Failed to load config: HTTP ${response.status}`);
  }

  const data: ConfigLoadResponse = await response.json();
  if (!data.logging) {
    throw new Error("Logging service is not configured or unavailable");
  }

  return data.logging;
}

/**
 * Updates logging configuration via POST /config/logging
 */
export async function updateLoggingConfig(
  payload: LoggingConfigUpdatePayload,
  token: string
): Promise<ApiResponse> {
  const response = await fetch(`${BASE_URL}/config/logging`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.message || `Failed to update logging config: HTTP ${response.status}`);
  }

  return data;
}

/**
 * Quick toggle for master logging switch
 */
export async function toggleLogging(
  logging: boolean,
  token: string
): Promise<ApiResponse> {
  return updateLoggingConfig({ logging }, token);
}

/**
 * Quick toggle for terminal print capture
 */
export async function toggleTerminalCapture(
  captureTerminal: boolean,
  token: string
): Promise<ApiResponse> {
  return updateLoggingConfig({ capture_terminal: captureTerminal }, token);
}
```

---

### 3.3 Interactive React Component (`LoggingConfigPanel.tsx`)

```tsx
import React, { useState, useEffect } from "react";
import {
  getLoggingConfig,
  updateLoggingConfig,
  LoggingState,
  LoggingConfigUpdatePayload,
  LogLevel,
} from "./loggingApi";

interface Props {
  accessToken: string;
}

export const LoggingConfigPanel: React.FC<Props> = ({ accessToken }) => {
  const [config, setConfig] = useState<LoggingState | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form states
  const [logging, setLogging] = useState<boolean>(true);
  const [level, setLevel] = useState<LogLevel>("INFO");
  const [consoleOutput, setConsoleOutput] = useState<boolean>(true);
  const [captureTerminal, setCaptureTerminal] = useState<boolean>(false);
  const [redactSensitive, setRedactSensitive] = useState<boolean>(true);
  const [staticMountLogs, setStaticMountLogs] = useState<boolean>(false);
  const [logsDir, setLogsDir] = useState<string>("");
  const [patternInput, setPatternInput] = useState<string>("");
  const [redactPatterns, setRedactPatterns] = useState<string[]>([]);
  const [patternError, setPatternError] = useState<string | null>(null);

  useEffect(() => {
    loadCurrentConfig();
  }, [accessToken]);

  const loadCurrentConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getLoggingConfig(accessToken);
      setConfig(data);
      setLogging(data.logging);
      setLevel(data.level);
      setConsoleOutput(data.console_output);
      setCaptureTerminal(data.capture_terminal);
      setRedactSensitive(data.redact_sensitive);
      setStaticMountLogs(data.static_mount_logs);
      setLogsDir(data.logs_dir || "");
      setRedactPatterns(data.redact_patterns || []);
    } catch (err: any) {
      setError(err.message || "Failed to load logging config");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickToggle = async () => {
    const nextState = !logging;
    setSaving(true);
    setError(null);
    setSuccessMessage(null);
    try {
      await updateLoggingConfig({ logging: nextState }, accessToken);
      setLogging(nextState);
      setSuccessMessage(`Logging successfully ${nextState ? "enabled" : "disabled"}.`);
    } catch (err: any) {
      setError(err.message || "Failed to toggle logging");
    } finally {
      setSaving(false);
    }
  };

  const handleAddPattern = () => {
    const pattern = patternInput.trim();
    if (!pattern) return;

    // Validate regex on client side before adding
    try {
      new RegExp(pattern);
      setPatternError(null);
    } catch (e: any) {
      setPatternError(`Invalid regular expression: ${e.message}`);
      return;
    }

    if (!redactPatterns.includes(pattern)) {
      setRedactPatterns([...redactPatterns, pattern]);
      setPatternInput("");
    }
  };

  const handleRemovePattern = (patternToRemove: string) => {
    setRedactPatterns(redactPatterns.filter((p) => p !== patternToRemove));
  };

  const handleSaveForm = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccessMessage(null);

    const payload: LoggingConfigUpdatePayload = {
      logging,
      level,
      console_output: consoleOutput,
      capture_terminal: captureTerminal,
      redact_sensitive: redactSensitive,
      redact_patterns: redactPatterns,
      static_mount_logs: staticMountLogs,
      logs_dir: logsDir.trim() || undefined,
    };

    try {
      const res = await updateLoggingConfig(payload, accessToken);
      setSuccessMessage(res.message || "Logging configuration updated successfully");
      await loadCurrentConfig();
    } catch (err: any) {
      setError(err.message || "Failed to save logging configuration");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div style={{ padding: 20 }}>Loading logging configuration...</div>;
  }

  return (
    <div style={{ maxWidth: 680, margin: "0 auto", padding: 24, fontFamily: "sans-serif" }}>
      <h2>Logging Subsystem Configuration</h2>

      {error && (
        <div style={{ background: "#fee2e2", color: "#991b1b", padding: 12, borderRadius: 6, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {successMessage && (
        <div style={{ background: "#dcfce7", color: "#166534", padding: 12, borderRadius: 6, marginBottom: 16 }}>
          {successMessage}
        </div>
      )}

      {/* Master Toggle Banner */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: 16,
          background: logging ? "#f0fdf4" : "#fef2f2",
          border: `1px solid ${logging ? "#bbf7d0" : "#fecaca"}`,
          borderRadius: 8,
          marginBottom: 24,
        }}
      >
        <div>
          <strong>Master Logging: </strong>
          <span style={{ color: logging ? "#15803d" : "#b91c1c", fontWeight: "bold" }}>
            {logging ? "ENABLED" : "DISABLED"}
          </span>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "#666" }}>
            {logging ? "All logging endpoints and live streams are active." : "Logging is disabled (routes return 400)."}
          </p>
        </div>
        <button
          type="button"
          onClick={handleQuickToggle}
          disabled={saving}
          style={{
            padding: "8px 16px",
            borderRadius: 6,
            border: "none",
            background: logging ? "#dc2626" : "#16a34a",
            color: "#fff",
            cursor: "pointer",
            fontWeight: "bold",
          }}
        >
          {logging ? "Disable Logging" : "Enable Logging"}
        </button>
      </div>

      <form onSubmit={handleSaveForm}>
        {/* Log Level */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 6, fontWeight: 600 }}>Log Level Threshold:</label>
          <select
            value={level}
            onChange={(e) => setLevel(e.target.value as LogLevel)}
            style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid #ccc" }}
          >
            <option value="DEBUG">DEBUG (Most verbose)</option>
            <option value="INFO">INFO (Default)</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
            <option value="CRITICAL">CRITICAL</option>
          </select>
        </div>

        {/* Logs Directory */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 6, fontWeight: 600 }}>Logs Directory:</label>
          <input
            type="text"
            value={logsDir}
            onChange={(e) => setLogsDir(e.target.value)}
            placeholder="e.g. logs"
            style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid #ccc" }}
          />
        </div>

        {/* Terminal Print Capture Checkbox */}
        <div style={{ marginBottom: 16, padding: 12, background: "#f8fafc", borderRadius: 6, border: "1px solid #e2e8f0" }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontWeight: 600 }}>
            <input
              type="checkbox"
              checked={captureTerminal}
              onChange={(e) => setCaptureTerminal(e.target.checked)}
            />
            <span>Capture Terminal <code>print()</code> to Server Log (<code>capture_terminal</code>)</span>
          </label>
          <p style={{ margin: "4px 0 0 24px", fontSize: 13, color: "#64748b" }}>
            Captures all <code>print()</code> outputs from Uvicorn, routes, and libraries directly into <code>server.log</code> while keeping console terminal output unchanged.
          </p>
        </div>

        {/* Console Output Checkbox */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={consoleOutput}
              onChange={(e) => setConsoleOutput(e.target.checked)}
            />
            <span>Echo application JSONL events to terminal/stdout (<code>console_output</code>)</span>
          </label>
        </div>

        {/* Default Sensitive Data Redaction Checkbox */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={redactSensitive}
              onChange={(e) => setRedactSensitive(e.target.checked)}
            />
            <span>Auto-redact built-in sensitive fields (tokens, passwords, cookies)</span>
          </label>
        </div>

        {/* Static Mount Checkbox */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={staticMountLogs}
              onChange={(e) => setStaticMountLogs(e.target.checked)}
            />
            <span>Static Mount at <code>/logs</code> route</span>
          </label>
        </div>

        {/* Regex Redaction Patterns */}
        <div style={{ marginBottom: 24, padding: 16, background: "#f9fafb", borderRadius: 6, border: "1px solid #e5e7eb" }}>
          <label style={{ display: "block", marginBottom: 6, fontWeight: 600 }}>
            Custom Regex Redaction Patterns (<code>redact_patterns</code>):
          </label>
          <p style={{ margin: "0 0 8px", fontSize: 13, color: "#6b7280" }}>
            Matches in application logs and captured <code>print()</code> outputs will be replaced with <code>[REDACTED]</code>.
          </p>
          <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
            <input
              type="text"
              value={patternInput}
              onChange={(e) => {
                setPatternInput(e.target.value);
                setPatternError(null);
              }}
              placeholder="e.g. (?i)api[_-]?key\s*[:=]\s*\S+"
              style={{ flex: 1, padding: 8, borderRadius: 6, border: "1px solid #ccc" }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleAddPattern();
                }
              }}
            />
            <button
              type="button"
              onClick={handleAddPattern}
              style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid #ccc", background: "#f3f4f6", cursor: "pointer", fontWeight: 600 }}
            >
              Add Pattern
            </button>
          </div>
          {patternError && (
            <div style={{ color: "#b91c1c", fontSize: 13, marginBottom: 8 }}>{patternError}</div>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {redactPatterns.length === 0 && (
              <span style={{ fontSize: 13, color: "#9ca3af" }}>No custom regex patterns configured.</span>
            )}
            {redactPatterns.map((pattern) => (
              <div
                key={pattern}
                style={{
                  background: "#e5e7eb",
                  padding: "6px 10px",
                  borderRadius: 4,
                  fontSize: 13,
                  fontFamily: "monospace",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span>{pattern}</span>
                <button
                  type="button"
                  onClick={() => handleRemovePattern(pattern)}
                  style={{ border: "none", background: "none", cursor: "pointer", color: "#6b7280", fontWeight: "bold", fontSize: 16 }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={saving}
          style={{
            width: "100%",
            padding: 12,
            borderRadius: 6,
            border: "none",
            background: "#2563eb",
            color: "#fff",
            fontSize: 16,
            fontWeight: "bold",
            cursor: "pointer",
          }}
        >
          {saving ? "Saving Changes..." : "Save Configuration"}
        </button>
      </form>
    </div>
  );
};
```
