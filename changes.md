# Dashboard Logging Config — Frontend Integration Guide

This guide details the API integration for the 2 Dashboard Configuration routes updated for the logging subsystem.

---

## 1. Authentication
- **Role Required**: `superadmin`
- **Headers**: `Authorization: Bearer <access_token>` or cookie session (`credentials: "include"`)

---

## 2. Route 1: Load Configuration

### `GET /tc-auth/config/load`
Retrieves live configuration across all services, including the updated `logging` object.

#### Response (`200 OK`)
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
    "logs_dir": "D:\\path\\to\\logs",
    "store_dir": "D:\\path\\to\\logs\\store",
    "level": "INFO",
    "console_output": true,
    "capture_terminal": false,
    "redact_sensitive": true,
    "redact_patterns": [],
    "max_log_lines": 10000,
    "trim_log_lines": 1000
  }
}
```

---

## 3. Route 2: Update Logging Configuration

### `POST /tc-auth/config/logging`
Updates logging settings at runtime. Supports partial updates (only include fields you want to change).

#### Request Headers
```http
Content-Type: application/json
Authorization: Bearer <access_token>
```

#### Request Body Fields
| Field | Type | Description |
|---|---|---|
| `logging` | `boolean` | Master switch for persistent logs (`tcauth.log`, `server.log`). |
| `logs_dir` | `string` | Directory where persistent logs live. |
| `level` | `string` | Severity threshold: `"DEBUG"` \| `"INFO"` \| `"WARNING"` \| `"ERROR"` \| `"CRITICAL"`. |
| `console_output` | `boolean` | Display logs in console (operates independently of `logging`). |
| `capture_terminal` | `boolean` | Capture `stdout`/`stderr` print output into `server.log`. |
| `redact_sensitive` | `boolean` | Auto-mask sensitive data (passwords, tokens, cookies, secrets). |
| `redact_patterns` | `string[]` | Array of custom regex patterns to mask as `[REDACTED]`. |
| `max_log_lines` | `integer (>= 10)` | Maximum retained lines for `server.log` and `tcauth.log`. |
| `trim_log_lines` | `integer (>= 1)` | Number of oldest lines deleted when line limit is reached. |

#### Example Request Payload
```json
{
  "logging": true,
  "level": "INFO",
  "console_output": true,
  "capture_terminal": false,
  "redact_sensitive": true,
  "redact_patterns": [
    "(?i)authorization:\\s*bearer\\s+\\S+",
    "(?i)api[_-]?key\\s*[:=]\\s*\\S+"
  ],
  "max_log_lines": 10000,
  "trim_log_lines": 1000
}
```

#### Success Response (`200 OK`)
```json
{
  "success": true,
  "message": "Logging service configured successfully"
}
```

#### Error Responses
- `400 Bad Request`: Invalid level name, invalid regex pattern, or out-of-range integer values.
- `401 Unauthorized`: Missing or invalid access token.
- `403 Forbidden`: User does not have `superadmin` role.

---

## 4. Key Frontend Integration Notes
1. **No `enabled` field**: Use `logging` as the boolean master switch.
2. **Independent `console_output`**: Setting `logging: false` stops saving log files, while `console_output` can remain `true` to keep console output active.
3. **Regex Pattern Safety**: Validate regex patterns before submitting to prevent 400 Bad Request errors.
