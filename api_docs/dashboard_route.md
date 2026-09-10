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

Loads the current email, GitHub, Google, and JWT configuration.

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
  "jwt": {
    "secret_key": "...",
    "algorithm": "HS256",
    "session_duration_days": 1
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

## POST `/jwt`

Configures JWT signing and session lifetime.

Body:

```json
{
  "secret_key": "super-secret",
  "algorithm": "HS256",
  "session_duration_days": 1
}
```

Response:

```json
{
  "success": true,
  "message": "JWT configured successfully"
}
```
