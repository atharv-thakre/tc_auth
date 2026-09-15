# Logging Configuration Routes — Frontend Implementation Guide

This document details the frontend implementation for the 2 dashboard logging routes in `tc_auth`:
1. **`GET /tc-auth/config/load/`** — Fetch current live configuration (including logging settings).
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
      "redact_sensitive": true,
      "custom_redact_keys": ["tenant_token", "api_secret"]
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
  | `redact_sensitive` | `boolean` | Optional | Mask passwords, tokens, cookies, and secret keys. |
  | `static_mount_logs` | `boolean` | Optional | Expose logs directory at `/logs` static route. |
  | `logs_dir` | `string` | Optional | Base directory for log storage. |
  | `custom_redact_keys` | `string[]` | Optional | Additional JSON keys to redact in application logs. |

- **Example Request Payload (Full Update)**:
  ```json
  {
    "logging": true,
    "level": "DEBUG",
    "console_output": true,
    "redact_sensitive": true,
    "static_mount_logs": false,
    "logs_dir": "logs",
    "custom_redact_keys": ["tenant_key", "secret_payload"]
  }
  ```

- **Example Request Payload (Toggle Only)**:
  ```json
  {
    "logging": false
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
  - `400 Bad Request` (`InvalidConfigError`): Invalid level name or non-boolean values.
  - `401 Unauthorized`: Missing or invalid Bearer token.
  - `403 Forbidden`: User does not possess `superadmin` role.

---

## 3. Frontend Implementation

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
  redact_sensitive: boolean;
  custom_redact_keys: string[];
}

export interface LoggingConfigUpdatePayload {
  logging?: boolean;
  level?: LogLevel;
  console_output?: boolean;
  redact_sensitive?: boolean;
  static_mount_logs?: boolean;
  logs_dir?: string;
  custom_redact_keys?: string[];
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
 * Fast master toggle for logging
 */
export async function toggleLogging(
  logging: boolean,
  token: string
): Promise<ApiResponse> {
  return updateLoggingConfig({ logging }, token);
}
```

---

### 3.3 Ready-to-Use React Form Component (`LoggingConfigPanel.tsx`)

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

  // Form state
  const [logging, setLogging] = useState<boolean>(true);
  const [level, setLevel] = useState<LogLevel>("INFO");
  const [consoleOutput, setConsoleOutput] = useState<boolean>(true);
  const [redactSensitive, setRedactSensitive] = useState<boolean>(true);
  const [staticMountLogs, setStaticMountLogs] = useState<boolean>(false);
  const [logsDir, setLogsDir] = useState<string>("");
  const [customKeyInput, setCustomKeyInput] = useState<string>("");
  const [customRedactKeys, setCustomRedactKeys] = useState<string[]>([]);

  // Load config on mount
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
      setRedactSensitive(data.redact_sensitive);
      setStaticMountLogs(data.static_mount_logs);
      setLogsDir(data.logs_dir || "");
      setCustomRedactKeys(data.custom_redact_keys || []);
    } catch (err: any) {
      setError(err.message || "Failed to load logging config");
    } finally {
      setLoading(false);
    }
  };

  // Quick toggle logging master switch
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

  // Submit full form changes
  const handleSaveForm = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccessMessage(null);

    const payload: LoggingConfigUpdatePayload = {
      logging,
      level,
      console_output: consoleOutput,
      redact_sensitive: redactSensitive,
      static_mount_logs: staticMountLogs,
      logs_dir: logsDir.trim() || undefined,
      custom_redact_keys: customRedactKeys,
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

  const handleAddRedactKey = () => {
    const cleanKey = customKeyInput.trim().toLowerCase();
    if (cleanKey && !customRedactKeys.includes(cleanKey)) {
      setCustomRedactKeys([...customRedactKeys, cleanKey]);
      setCustomKeyInput("");
    }
  };

  const handleRemoveRedactKey = (keyToRemove: string) => {
    setCustomRedactKeys(customRedactKeys.filter((k) => k !== keyToRemove));
  };

  if (loading) {
    return <div style={{ padding: 20 }}>Loading logging configuration...</div>;
  }

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: 24, fontFamily: "sans-serif" }}>
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

      {/* Master Toggle Bar */}
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
          <strong>Logging Status: </strong>
          <span style={{ color: logging ? "#15803d" : "#b91c1c", fontWeight: "bold" }}>
            {logging ? "ENABLED" : "DISABLED"}
          </span>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "#666" }}>
            {logging ? "All routes & event streams are active." : "Log routes will return 400 Bad Request."}
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

      {/* Form Settings */}
      <form onSubmit={handleSaveForm}>
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 6, fontWeight: 600 }}>Log Level:</label>
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

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={consoleOutput}
              onChange={(e) => setConsoleOutput(e.target.checked)}
            />
            <span>Echo logs to Console / Stdout</span>
          </label>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={redactSensitive}
              onChange={(e) => setRedactSensitive(e.target.checked)}
            />
            <span>Auto-redact sensitive keys (passwords, tokens, cookies)</span>
          </label>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={staticMountLogs}
              onChange={(e) => setStaticMountLogs(e.target.checked)}
            />
            <span>Static Mount at <code>/logs</code></span>
          </label>
        </div>

        {/* Custom Redact Keys */}
        <div style={{ marginBottom: 24 }}>
          <label style={{ display: "block", marginBottom: 6, fontWeight: 600 }}>Custom Redact Keys:</label>
          <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
            <input
              type="text"
              value={customKeyInput}
              onChange={(e) => setCustomKeyInput(e.target.value)}
              placeholder="e.g. tenant_secret"
              style={{ flex: 1, padding: 8, borderRadius: 6, border: "1px solid #ccc" }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleAddRedactKey();
                }
              }}
            />
            <button
              type="button"
              onClick={handleAddRedactKey}
              style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid #ccc", background: "#f3f4f6", cursor: "pointer" }}
            >
              Add Key
            </button>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {customRedactKeys.map((key) => (
              <span
                key={key}
                style={{
                  background: "#e5e7eb",
                  padding: "4px 8px",
                  borderRadius: 4,
                  fontSize: 13,
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                {key}
                <button
                  type="button"
                  onClick={() => handleRemoveRedactKey(key)}
                  style={{ border: "none", background: "none", cursor: "pointer", color: "#666", fontWeight: "bold" }}
                >
                  ×
                </button>
              </span>
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
