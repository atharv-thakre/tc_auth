# Dashboard / Config Routes

Base path: `/tc-auth/config`

Authentication:

- `GET /pulse` is public.
- All other routes in this group require `Authorization: Bearer <access_token>` and the `superadmin` role.

Notes:

- The current code exposes `GET /load/`; there is no separate `/redirect` route in the route module anymore.
- Configuration is stored in memory on the running service instance.

## GET `/pulse`

Health and readiness-style probe.

Response:

```json
{
  "system_time": "2026-08-12T10:00:00.000000",
  "response": "Hello",
  "status": "healthy",
  "state": "active"
}
```

Example:

```js
const res = await fetch(`${baseUrl}/tc-auth/config/pulse`);
const data = await res.json();
```

## GET `/load/`

Loads the current email, GitHub, Google, Discord, and JWT configuration.

Response:

```json
{
  "email": {
    "host": "smtp.example.com",
    "port": 587,
    "username": "mailer@example.com",
    "password": "***",
    "sender": "noreply@example.com",
    "sender_name": "Auth Module",
    "use_tls": true
  },
  "github": {
    "client_id": "...",
    "client_secret": "...",
    "redirect_uri": "https://app.example.com/tc-auth/github/callback"
  },
  "google": {
    "client_id": "...",
    "client_secret": "...",
    "redirect_uri": "https://app.example.com/tc-auth/google/callback"
  },
  "discord": {
    "client_id": "...",
    "client_secret": "...",
    "redirect_uri": "https://app.example.com/tc-auth/discord/callback"
  },
  "jwt": {
    "secret_key": "...",
    "algorithm": "HS256",
    "session_duration_days": 7
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
    "logs_dir": "/path/to/logs",
    "store_dir": "/path/to/logs/store",
    "static_mount_logs": false,
    "static_mount_log": false,
    "level": "INFO",
    "console_output": true,
    "capture_terminal": false,
    "redact_sensitive": true,
    "redact_patterns": []
  }
}
```

Example:

```js
const res = await fetch(`${baseUrl}/tc-auth/config/load/`, {
  method: "GET",
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
});

const config = await res.json();
```

## GET `/counts`

Returns counts for the main tables.

Response:

```json
{
  "accounts": 123,
  "oauth": 7,
  "sessions": 42,
  "otp": 3
}
```

Example:

```js
const res = await fetch(`${baseUrl}/tc-auth/config/counts`, {
  method: "GET",
  headers: { Authorization: `Bearer ${accessToken}` },
});

const counts = await res.json();
```

## POST `/email`

Configures the email service.

Body:

```json
{
  "host": "smtp.example.com",
  "port": 587,
  "username": "mailer@example.com",
  "password": "secret",
  "sender": "noreply@example.com",
  "sender_name": "Auth Module",
  "use_tls": true
}
```

Response:

```json
{
  "success": true,
  "message": "Email service configured successfully"
}
```

## POST `/github`

Configures GitHub OAuth.

Body:

```json
{
  "client_id": "...",
  "client_secret": "...",
  "redirect_uri": "https://app.example.com/tc-auth/github/callback"
}
```

Response:

```json
{
  "success": true,
  "message": "GitHub OAuth configured successfully"
}
```

## POST `/google`

Configures Google OAuth.

Body:

```json
{
  "client_id": "...",
  "client_secret": "...",
  "redirect_uri": "https://app.example.com/tc-auth/google/callback"
}
```

Response:

```json
{
  "success": true,
  "message": "Google OAuth configured successfully"
}
```

## POST `/discord`

Configures Discord OAuth.

Body:

```json
{
  "client_id": "...",
  "client_secret": "...",
  "redirect_uri": "https://app.example.com/tc-auth/discord/callback"
}
```

Response:

```json
{
  "success": true,
  "message": "Discord OAuth configured successfully"
}
```

## POST `/jwt`

Configures JWT signing, session lifetime, and optional dual-token architecture.

Body:

```json
{
  "secret_key": "super-secret",
  "algorithm": "HS256",
  "session_duration_days": 7,
  "dual_token_mode": false,
  "access_token_expire_minutes": 15,
  "refresh_token_expire_days": 7
}
```

- `session_duration_days` (required): Integer $\ge 1$. Controls single-token access expiration and database session lifetime. Default is `7`.
- `dual_token_mode` (optional): Boolean. When `true`, login and signup issue both a short-lived `access_token` and a long-lived `refresh_token`.
- `access_token_expire_minutes` (optional): Integer $\ge 1$. Lifespan of access tokens when dual-token mode is enabled (default `15`).
- `refresh_token_expire_days` (optional): Integer $\ge 1$. Lifespan of refresh tokens when dual-token mode is enabled (defaults to `session_duration_days`).

Response:

```json
{
  "success": true,
  "message": "JWT configured successfully"
}
```

## POST `/cookie`

Configures cookie-based authentication settings.

Body:

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

Response:

```json
{
  "success": true,
  "message": "Cookie settings updated successfully"
}
```

## POST `/logging`

Dynamically updates logging service settings at runtime. Accepts full or partial configurations.

Body:

```json
{
  "logging": true,
  "level": "INFO",
  "console_output": true,
  "capture_terminal": true,
  "redact_sensitive": true,
  "redact_patterns": [
    "(?i)authorization:\\s*bearer\\s+\\S+",
    "(?i)api[_-]?key\\s*[:=]\\s*\\S+"
  ],
  "static_mount_logs": false,
  "logs_dir": "/path/to/logs"
}
```

- `logging` (optional): Boolean. Globally enable (`true`) or disable (`false`) the logging subsystem.
- `level` (optional): String (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). Log verbosity threshold.
- `console_output` (optional): Boolean. Mirror logs to terminal/stdout.
- `capture_terminal` (optional): Boolean. When `true`, all process `print()` outputs are captured into `server.log`.
- `redact_sensitive` (optional): Boolean. Automatically sanitize tokens, passwords, cookies, and secret keys.
- `redact_patterns` (optional): Array of regex strings. Custom regular expressions to mask as `[REDACTED]`.
- `static_mount_logs` / `static_mount_log` (optional): Boolean. Dynamic gate for static log file access at `/logs/<filename>`. When `true`, files are served directly; when `false`, requests return `404 Not Found`. Can be toggled at runtime without remounting or restarting.
- `logs_dir` (optional): String. Custom directory path where log files are stored.

Response:

```json
{
  "success": true,
  "message": "Logging service configured successfully"
}
```

Example:

```js
// Dynamically toggle logging or change level to DEBUG
const res = await fetch(`${baseUrl}/tc-auth/config/logging`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${accessToken}`,
  },
  body: JSON.stringify({
    logging: true,
    level: "DEBUG"
  }),
});

const data = await res.json();
```


