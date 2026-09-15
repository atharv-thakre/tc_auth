# Dashboard API Routes — Recent Changes & Integration Guide

This document covers all recent updates, enhancements, and route additions to the **Dashboard / System Configuration API Routes** (`/tc-auth/config/*`).

---

## 1. Summary of Recent Dashboard Route Updates

1. **Logging Runtime Configuration (`POST /tc-auth/config/logging`)**:
   - Added endpoint for superadmins to dynamically configure the centralized logging subsystem at runtime.
   - Enforces a single master toggle: `logging` (boolean, defaults to `True`).
   - Supports non-destructive partial updates: omitting keys retains their active in-memory values.
   - Pydantic schema validation (`LoggingConfig`) with `extra="forbid"`.

2. **Full System Configuration Inspection (`GET /tc-auth/config/load/`)**:
   - Updated response payload to include full runtime configurations for `"logging"` and `"cookie"` alongside `"email"`, `"github"`, `"google"`, `"discord"`, and `"jwt"`.
   - Returns a single, uniform `"logging": true/false` status key (duplicate `"enabled"` key removed).

3. **Cookie Mode Runtime Configuration (`POST /tc-auth/config/cookie`)**:
   - Added endpoint for superadmins to toggle cookie mode (`cookie_mode: true/false`) and customize cookie parameters (`path`, `domain`, `secure`, `httponly`, `samesite`, `max_age`).

---

## 2. Route Specifications

All endpoints below are prefixed with `/tc-auth/config`.

| Endpoint | Method | Role Required | Description |
|---|---|---|---|
| `/tc-auth/config/pulse` | `GET` | **Public** | System health and readiness probe |
| `/tc-auth/config/load/` | `GET` | `superadmin` | Inspect active runtime configs (`email`, `oauth`, `jwt`, `cookie`, `logging`) |
| `/tc-auth/config/counts` | `GET` | `superadmin` | Database record counts (`accounts`, `oauth`, `sessions`, `otp`) |
| `/tc-auth/config/logging` | `POST` | `superadmin` | Dynamically update logging service settings |
| `/tc-auth/config/cookie` | `POST` | `superadmin` | Dynamically update cookie authentication settings |
| `/tc-auth/config/jwt` | `POST` | `superadmin` | Dynamically update JWT secret, algorithm, and token expiration |
| `/tc-auth/config/email` | `POST` | `superadmin` | Dynamically update SMTP credentials and sender config |
| `/tc-auth/config/google` | `POST` | `superadmin` | Dynamically update Google OAuth client credentials |
| `/tc-auth/config/github` | `POST` | `superadmin` | Dynamically update GitHub OAuth client credentials |
| `/tc-auth/config/discord` | `POST` | `superadmin` | Dynamically update Discord OAuth client credentials |

---

## 3. Detailed Request & Response Contracts

### 3.1 `GET /tc-auth/config/load/`

Retrieves the live in-memory configuration of all subsystem modules.

- **Headers**: `Authorization: Bearer <superadmin_access_token>`
- **Response (`200 OK`)**:

```json
{
  "email": {
    "host": "smtp.gmail.com",
    "port": 587,
    "username": "mailer@example.com",
    "password": "***",
    "sender": "mailer@example.com",
    "sender_name": "CodeSena Auth",
    "use_tls": true
  },
  "github": {
    "client_id": "gh_client_123",
    "client_secret": "***",
    "redirect_uri": "https://app.example.com/tc-auth/github/callback"
  },
  "google": {
    "client_id": "google_client_123",
    "client_secret": "***",
    "redirect_uri": "https://app.example.com/tc-auth/google/callback"
  },
  "discord": {
    "client_id": "discord_client_123",
    "client_secret": "***",
    "redirect_uri": "https://app.example.com/tc-auth/discord/callback"
  },
  "jwt": {
    "secret_key": "***",
    "algorithm": "HS256",
    "session_duration_days": 7,
    "dual_token_mode": false,
    "access_token_expire_minutes": 15,
    "refresh_token_expire_days": 7
  },
  "cookie": {
    "cookie_mode": false,
    "access_cookie_name": "access_token",
    "refresh_cookie_name": "refresh_token",
    "path": "/",
    "domain": null,
    "secure": false,
    "httponly": true,
    "samesite": "lax",
    "max_age": null
  },
  "logging": {
    "logging": true,
    "logs_dir": "/path/to/project/logs",
    "store_dir": "/path/to/project/logs/store",
    "static_mount_logs": false,
    "level": "INFO",
    "console_output": true,
    "redact_sensitive": true,
    "custom_redact_keys": []
  }
}
```

---

### 3.2 `POST /tc-auth/config/logging`

Updates logging service properties. Supports partial payloads; any omitted field retains its current setting.

- **Headers**:
  - `Content-Type: application/json`
  - `Authorization: Bearer <superadmin_access_token>`

- **Request Body Fields**:

| Field | Type | Default | Description |
|---|---|---|---|
| `logging` | `boolean` (optional) | `None` | Master toggle to enable (`true`) or disable (`false`) all logging. |
| `level` | `string` (optional) | `None` | Log level threshold (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). |
| `console_output` | `boolean` (optional) | `None` | Whether to echo JSONL application events to stdout. |
| `redact_sensitive` | `boolean` (optional) | `None` | Recursively mask sensitive fields (passwords, tokens, cookies, secrets). |
| `static_mount_logs` | `boolean` (optional) | `None` | Expose logs directory at `/logs` static route. |
| `logs_dir` | `string` (optional) | `None` | Custom base directory for log storage. |
| `custom_redact_keys` | `list[str]` (optional) | `None` | Additional dictionary keys to automatically redact in application logs. |

- **Example Request Body (Full)**:
```json
{
  "logging": true,
  "level": "DEBUG",
  "console_output": true,
  "redact_sensitive": true,
  "static_mount_logs": false,
  "logs_dir": "/app/logs",
  "custom_redact_keys": ["tenant_token", "x_api_secret"]
}
```

- **Example Request Body (Partial / Toggle Only)**:
```json
{
  "logging": false
}
```

- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Logging service configured successfully"
}
```

- **Error Responses**:
  - `400 Bad Request` (`InvalidConfigError`): If an invalid level, non-boolean flag, or invalid directory is passed.
  - `401 Unauthorized`: Missing or invalid JWT access token.
  - `403 Forbidden`: Authenticated user does not possess `superadmin` role.

---

### 3.3 `POST /tc-auth/config/cookie`

Updates cookie authentication settings.

- **Headers**:
  - `Content-Type: application/json`
  - `Authorization: Bearer <superadmin_access_token>`

- **Request Body**:
```json
{
  "cookie_mode": true,
  "access_cookie_name": "access_token",
  "refresh_cookie_name": "refresh_token",
  "path": "/",
  "domain": "example.com",
  "secure": true,
  "httponly": true,
  "samesite": "lax",
  "max_age": 604800
}
```

- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Cookie settings updated successfully"
}
```

---

## 4. Frontend Integration Examples

### 4.1 TypeScript Interfaces

```typescript
export interface LoggingConfigPayload {
  logging?: boolean;
  level?: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL";
  console_output?: boolean;
  redact_sensitive?: boolean;
  static_mount_logs?: boolean;
  logs_dir?: string;
  custom_redact_keys?: string[];
}

export interface DashboardConfigResponse {
  email: Record<string, any> | null;
  github: Record<string, any> | null;
  google: Record<string, any> | null;
  discord: Record<string, any> | null;
  jwt: Record<string, any> | null;
  cookie: {
    cookie_mode: boolean;
    access_cookie_name: string;
    refresh_cookie_name: string;
    path: string;
    domain: string | null;
    secure: boolean;
    httponly: boolean;
    samesite: string;
    max_age: number | null;
  } | null;
  logging: {
    logging: boolean;
    logs_dir: string;
    store_dir: string;
    static_mount_logs: boolean;
    level: string;
    console_output: boolean;
    redact_sensitive: boolean;
    custom_redact_keys: string[];
  } | null;
}
```

---

### 4.2 Fetch Helper Functions

```typescript
const BASE_URL = "https://api.example.com/tc-auth";

/**
 * Load all subsystem configurations
 */
export async function fetchSystemConfig(token: string): Promise<DashboardConfigResponse> {
  const res = await fetch(`${BASE_URL}/config/load/`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    throw new Error(`Failed to load config: ${res.statusText}`);
  }

  return res.json();
}

/**
 * Dynamically update logging configuration
 */
export async function updateLoggingConfig(
  config: LoggingConfigPayload,
  token: string
): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${BASE_URL}/config/logging`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(config),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || "Failed to update logging config");
  }

  return data;
}

/**
 * Quick toggle for master logging switch
 */
export async function toggleLogging(
  logging: boolean,
  token: string
): Promise<{ success: boolean; message: string }> {
  return updateLoggingConfig({ logging }, token);
}
```
