# TC Auth — Complete API, Usage & Response Changelog

This document tracks all new and updated APIs, request payloads, response structures, query parameters, status codes, and usage patterns across `tc_auth`.

All endpoints are mounted under the base prefix `/tc-auth` by default (configurable via `auth.include_routes(app, prefix="/tc-auth")`).

---

## Table of Contents

1. [Security & Authentication Architecture](#1-security--authentication-architecture)
   - [Dual-Token Architecture (Access + Refresh)](#11-dual-token-architecture-access--refresh)
   - [Password Policy & Strength Enforcement](#12-password-policy--strength-enforcement)
   - [Email OTP Purpose Restriction](#13-email-otp-purpose-restriction)
   - [Magic Link System (Built on Email OTP)](#14-magic-link-system-built-on-email-otp)
2. [OAuth Architecture & Enhancements](#2-oauth-architecture--enhancements)
   - [Discord OAuth Provider](#21-discord-oauth-provider)
   - [Multi-Provider Account Linking](#22-multi-provider-account-linking)
   - [Safe OAuth Unlinking & Lockout Prevention](#23-safe-oauth-unlinking--lockout-prevention)
   - [Profile & Email Overwrite Policy](#24-profile--email-overwrite-policy)
   - [Direct Account Linking on OAuth Login / Signup](#25-direct-account-linking-on-oauth-login--signup)
3. [Complete API Endpoints & Request/Response Reference](#3-complete-api-endpoints--requestresponse-reference)
   - [3.1 Authentication & Registration](#31-authentication--registration)
   - [3.2 Profile, Session & User OAuth Linking](#32-profile-session--user-oauth-linking)
   - [3.3 OAuth Browser Login & Callback Routes](#33-oauth-browser-login--callback-routes)
   - [3.4 System, Health & Dashboard Configuration](#34-system-health--dashboard-configuration)
   - [3.5 Admin Resource Management (Superadmin Only)](#35-admin-resource-management-superadmin-only)
4. [FastAPI Dependencies & Auth Context](#4-fastapi-dependencies--auth-context)
5. [Standard Error Format & Status Code Reference](#5-standard-error-format--status-code-reference)

---

## 1. Security & Authentication Architecture

### 1.1 Dual-Token Architecture (Access + Refresh)

By default, `tc_auth` operates in **Single-Token Mode** for backwards compatibility (`SESSION_DURATION_DAYS = 7`). 

When **Dual-Token Mode** is enabled via `auth.jwt.config(..., dual_token_mode=True)` or `POST /tc-auth/config/jwt`:
- **Access Token**: Short-lived JWT (default `15` minutes) embedded with claim `"type": "access"`.
- **Refresh Token**: Long-lived JWT (default `7` days) embedded with claim `"type": "refresh"`.
- **Token Rotation**: The `POST /tc-auth/token/refresh` endpoint accepts a valid refresh token, checks it against active database sessions, and issues a new access token along with a rotated refresh token.
- **Refresh Token Abuse Prevention**: Attempting to use a refresh token in `Authorization: Bearer <token>` on protected routes is rejected with **HTTP 401 Unauthorized** (`"Refresh token cannot be used as an access token"`).

### 1.2 Password Policy & Strength Enforcement

All password creation and update flows enforce a strict 4-point password complexity rule:
1. **Minimum Length**: At least 6 characters.
2. **Uppercase Character**: At least 1 uppercase letter (`A-Z`).
3. **Lowercase Character**: At least 1 lowercase letter (`a-z`).
4. **Number**: At least 1 digit (`0-9`).

**Enforced On**:
- `POST /tc-auth/signup/password` (`SignupPasswordRequest`)
- `POST /tc-auth/signup/otp` (`SignupOTPRequest`)
- `POST /tc-auth/forgot/password` (`ForgotPasswordRequest`)
- `PUT /tc-auth/update/password` (`UpdatePassword`)
- Admin user creation & super-updates (`POST /tc-auth/account/`, `PATCH /tc-auth/account/`)
- SDK Service calls: `auth.account.create_user()` and `auth.account.update_password()`

Failing validation raises `WeakPasswordError` (**HTTP 400 Bad Request**):
```json
{
  "success": false,
  "message": "Password must be at least 6 characters long and contain at least one uppercase letter, one lowercase letter, and one number"
}
```

### 1.3 Email OTP Purpose Restriction

The email OTP service strictly enforces 4 allowed purposes:
- `signup`: User registration
- `login`: Passwordless OTP login
- `reset`: Password reset verification
- `verify`: Email address ownership verification

Any unapproved purpose is rejected with **HTTP 400 Bad Request** (`InvalidEmailPurposeError`).

### 1.4 Magic Link System (Built on Email OTP)

The Magic Link system is implemented directly on top of `tc_auth`'s existing email OTP infrastructure, eliminating redundant database models while maintaining single-use token lifecycle, expiry, and attempt limits.

- **Explicit Intent Guideline**:
  - `POST /tc-auth/send/email/link/{purpose}`: Recommended **ONLY when the user explicitly clicks a "Send me Magic Link" / "Sign in with Magic Link" button**. Sets dedicated subject line (*"Sign-In Link & Code"*).
  - `POST /tc-auth/send/email/otp/{purpose}`: Used for default email sign-in forms. Automatically includes the magic link button if `frontend_url` is provided in body, query param, or detected via the `Origin` header.
- **Dual Authentication Email Content**: Every magic link email contains both:
  1. A one-click CTA button ("Click to Proceed") that performs direct authentication.
  2. A fallback manual 6-digit verification code below the button (for cross-device access).
- **Single-Token & Dual-Token Mode Support**:
  - Single-Token Mode: `GET /link/login` redirects to `{frontend_url}/oauth/callback?access_token=...`; `POST /link/login` returns `{access_token, account}`.
  - Dual-Token Mode: `GET /link/login` redirects to `{frontend_url}/oauth/callback?access_token=...&refresh_token=...`; `POST /link/login` returns `{access_token, refresh_token, account}`.
- **Direct Browser Verification (`GET /tc-auth/link/{purpose}`)**:
  - `login`: Verifies OTP, logs user in, and redirects (HTTP 307) to `{frontend_url}/oauth/callback?access_token=...(&refresh_token=...)`, reusing the frontend OAuth callback handler.
  - `verify`: Verifies OTP, sets user status to `"active"`, and redirects (HTTP 307) to `{frontend_url}/magic-link/callback?verified=true&email=...`.
  - `reset`: Validates OTP without consuming, redirects to `{frontend_url}/reset-password?email=...&otp=...`.
  - `signup`: Validates OTP without consuming, redirects to `{frontend_url}/signup?email=...&otp=...&verified=true`.
  - On error (expired or invalid OTP): Redirects (HTTP 307) to `{frontend_url}/magic-link/callback?error={error_message}`.
- **Bot-Safe Programmatic Verification (`POST /tc-auth/link/{purpose}`)**:
  Accepts `{"email": "...", "otp": "..."}` and returns standard JSON payloads (tokens & user profile for `login`, success object for `verify`). This protects against corporate email antivirus scanner bots that pre-fetch and burn links.

---

## 2. OAuth Architecture & Enhancements

### 2.1 Discord OAuth Provider

`tc_auth` includes Discord as a first-class OAuth 2.0 provider (`auth.discord`, `GET /tc-auth/discord/login`, `GET /tc-auth/discord/callback`, `POST /tc-auth/config/discord`).

- **Scopes**: `identify email`
- **User Data Mapping**:
  - `id` $\rightarrow$ `provider_user_id` (string)
  - `global_name` or `username` $\rightarrow$ `name`
  - `email` $\rightarrow$ `email` (only trusted if verified)
  - `avatar` $\rightarrow$ `avatar_url` (supports animated `.gif` via `a_` prefix, standard `.png`, and default embed CDN avatars `(id >> 22) % 6`).
- **Account Takeover Protection**: Discord permits unverified emails. To protect existing users from unauthorized takeover, Discord accounts with `verified: False` have their email ignored for automatic linking.

### 2.2 Multi-Provider Account Linking

Logged-in users can link secondary OAuth providers (Google, GitHub, Discord) to their single profile:
- **Redirect Mode**: Pass `?frontend_url=...` to `POST /tc-auth/account/oauth/link/{provider}`. Redirects to provider authorization; upon callback, links provider to the current account and redirects back to `{frontend_url}/oauth/callback?linked=true&provider={provider}`.
- **Direct Mode**: Send JSON `{"provider_user_id": "..."}` to `POST /tc-auth/account/oauth/link/{provider}`.
- **Inspect Links**: `GET /tc-auth/account/oauth/links`.

### 2.3 Safe OAuth Unlinking & Lockout Prevention

- **Endpoint**: `DELETE /tc-auth/account/oauth/{provider}`
- **Lockout Prevention**: Unlinking is safely rejected (**HTTP 400 Bad Request**) if the user does not have a password (`password_hash`) and has no other linked OAuth providers:
```json
{
  "success": false,
  "message": "Cannot unlink provider: account must have a password or at least one other active authentication method"
}
```

### 2.4 Profile & Email Overwrite Policy

| Provider | Overwrites Existing Non-Empty Email? | Overwrites Existing Name / Avatar? | Sets Empty / Missing Fields? | Auto-Links by Verified Email? |
| :--- | :--- | :--- | :--- | :--- |
| **Google** | **YES** (always set or updated) | **NO** (preserved if already present) | **YES** (sets all empty fields) | **YES** (case-insensitive) |
| **GitHub** | **NO** (preserved if already present) | **NO** (preserved if already present) | **YES** (sets all empty fields) | **YES** (case-insensitive primary verified) |
| **Discord** | **NO** (preserved if already present) | **NO** (preserved if already present) | **YES** (sets all empty fields) | **YES** (case-insensitive verified only) |

### 2.5 Direct Account Linking on OAuth Login / Signup

- **Case-Insensitive Matching**: `USER@EXAMPLE.COM` matches `user@example.com`.
- **Idempotency**: Repeated logins with an already-linked provider succeed gracefully without duplicate key errors.
- **Conflict Detection**:
  - Account already linked to a different ID for that provider $\rightarrow$ **HTTP 409 Conflict** (`OAuthAlreadyLinkedError`).
  - Provider ID already claimed by another user profile $\rightarrow$ **HTTP 409 Conflict** (`OAuthAlreadyLinkedError`).

---

## 3. Complete API Endpoints & Request/Response Reference

### 3.1 Authentication & Registration

#### POST `/tc-auth/send/email/otp/{purpose}`
Sends an email OTP for the specified purpose (`signup`, `login`, `reset`, `verify`). If `frontend_url` is provided, the email also includes the one-click Magic Link button.

- **Headers**: `Content-Type: application/json`
- **Path Parameter**: `purpose` (`signup` | `login` | `reset` | `verify`)
- **Request Body**:
```json
{
  "email": "jane@example.com",
  "frontend_url": "https://app.example.com"
}
```
*(Note: `frontend_url` is optional for backward compatibility).*
- **Response (HTTP 200 OK)**:
```json
{
  "expires_at": 1735689600
}
```

---

#### POST `/tc-auth/send/email/link/{purpose}`
Directly requests a Magic Link email for the specified purpose (`signup`, `login`, `reset`, `verify`).

- **Headers**: `Content-Type: application/json`
- **Path Parameter**: `purpose` (`signup` | `login` | `reset` | `verify`)
- **Request Body**:
```json
{
  "email": "jane@example.com",
  "frontend_url": "https://app.example.com"
}
```
- **Response (HTTP 200 OK)**:
```json
{
  "expires_at": 1735689600
}
```

---

#### GET `/tc-auth/link/{purpose}`
Direct browser verification endpoint when the user clicks the magic link in their email.

- **Query Parameters**:
  - `email` (string, required): User email address.
  - `otp` (string, required): Single-use OTP code.
  - `frontend_url` (string, required): Frontend base URL.
- **Success Redirects (HTTP 307)**:
  - `login`: `{frontend_url}/oauth/callback?access_token=...(&refresh_token=...)`
  - `verify`: `{frontend_url}/magic-link/callback?verified=true&email=...`
  - `reset`: `{frontend_url}/reset-password?email=...&otp=...`
  - `signup`: `{frontend_url}/signup?email=...&otp=...&verified=true`
- **Error Redirect (HTTP 307)**:
  - `{frontend_url}/magic-link/callback?error={url_encoded_error}`

---

#### POST `/tc-auth/link/{purpose}`
Bot-safe programmatic verification endpoint for Single-Page Apps (SPAs) or confirmation screens.

- **Headers**: `Content-Type: application/json`
- **Path Parameter**: `purpose` (`signup` | `login` | `reset` | `verify`)
- **Request Body**:
```json
{
  "email": "jane@example.com",
  "otp": "123456"
}
```
- **Response (HTTP 200 OK - login, Dual-Token Mode)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "account": {
    "id": 1,
    "email": "jane@example.com",
    "name": "Jane Doe",
    "role": "user",
    "status": "active"
  }
}
```
- **Response (HTTP 200 OK - verify)**:
```json
{
  "success": true,
  "message": "Email verified successfully",
  "email": "jane@example.com"
}
```

---

#### POST `/tc-auth/signup/password`
Registers a new account using email/handle and password.

- **Headers**: `Content-Type: application/json`
- **Request Body**:
```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "password": "Password123",
  "handle": "jane"
}
```
- **Response (HTTP 200 OK - Single-Token Mode)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "account": {
    "id": 1,
    "uid": "2d7b5f8e-8d8a-4cc4-9c3d-2f2c6c4d2e28",
    "name": "Jane Doe",
    "handle": "jane",
    "email": "jane@example.com",
    "phone": null,
    "avatar_url": null,
    "role": "user",
    "status": null,
    "created_at": "2026-09-12T12:00:00",
    "updated_at": "2026-09-12T12:00:00"
  }
}
```
- **Response (HTTP 200 OK - Dual-Token Mode)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "account": {
    "id": 1,
    "uid": "2d7b5f8e-8d8a-4cc4-9c3d-2f2c6c4d2e28",
    "name": "Jane Doe",
    "handle": "jane",
    "email": "jane@example.com",
    "phone": null,
    "avatar_url": null,
    "role": "user",
    "status": null,
    "created_at": "2026-09-12T12:00:00",
    "updated_at": "2026-09-12T12:00:00"
  }
}
```

---

#### POST `/tc-auth/signup/otp`
Verifies signup OTP and creates a new account.

- **Headers**: `Content-Type: application/json`
- **Request Body**:
```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "password": "Password123",
  "otp": "123456",
  "handle": "jane"
}
```
- **Response (HTTP 200 OK)**: Same login payload (Single/Dual Token).

---

#### POST `/tc-auth/login/password`
Authenticates an existing user via identifier (email or handle) and password.

- **Headers**: `Content-Type: application/json`
- **Request Body**:
```json
{
  "identifier": "jane@example.com",
  "password": "Password123"
}
```
- **Response (HTTP 200 OK)**: Same login payload (Single/Dual Token).

---

#### POST `/tc-auth/login/otp`
Authenticates an existing user via email OTP.

- **Headers**: `Content-Type: application/json`
- **Request Body**:
```json
{
  "email": "jane@example.com",
  "otp": "123456"
}
```
- **Response (HTTP 200 OK)**: Same login payload (Single/Dual Token).

---

#### POST `/tc-auth/forgot/password`
Verifies reset OTP and updates user's password.

- **Headers**: `Content-Type: application/json`
- **Request Body**:
```json
{
  "email": "jane@example.com",
  "otp": "123456",
  "password": "NewPassword123"
}
```
- **Response (HTTP 200 OK)**: Same login payload (Single/Dual Token).

---

#### POST `/tc-auth/token/refresh` [NEW]
Exchanges a valid refresh token for a newly issued access token and rotated refresh token.

- **Headers**: `Content-Type: application/json`
- **Request Body**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
- **Response (HTTP 200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer"
}
```
- **Error Responses**:
  - Missing/invalid token $\rightarrow$ `401 Unauthorized` (`InvalidTokenError`)
  - Session expired/not found $\rightarrow$ `401 Unauthorized` (`InvalidTokenError`)

---

### 3.2 Profile, Session & User OAuth Linking

#### GET `/tc-auth/me`
Retrieves authenticated user profile, session, and JWT payload.

- **Headers**: `Authorization: Bearer <access_token>`
- **Response (HTTP 200 OK)**:
```json
{
  "account": {
    "id": 1,
    "uid": "2d7b5f8e-8d8a-4cc4-9c3d-2f2c6c4d2e28",
    "name": "Jane Doe",
    "handle": "jane",
    "email": "jane@example.com",
    "phone": null,
    "avatar_url": null,
    "role": "user",
    "status": null,
    "created_at": "2026-09-12T12:00:00",
    "updated_at": "2026-09-12T12:00:00"
  },
  "session": {
    "id": 9,
    "account_id": 1,
    "token_hash": "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b",
    "ip_address": "127.0.0.1",
    "user_agent": "Mozilla/5.0",
    "expires_at": "2026-09-19T12:00:00",
    "created_at": "2026-09-12T12:00:00"
  },
  "payload": {
    "aid": 1,
    "sid": 9,
    "type": "access",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "exp": 1787129867
  }
}
```

---

#### PATCH `/tc-auth/me`
Updates profile information for the authenticated user.

- **Headers**:
  - `Authorization: Bearer <access_token>`
  - `Content-Type: application/json`
- **Request Body**:
```json
{
  "name": "Jane Smith",
  "avatar_url": "https://example.com/new_avatar.png",
  "phone": "+15555550100"
}
```
- **Response (HTTP 200 OK)**: Updated account object.

---

#### PUT `/tc-auth/update/password`
Updates the password for the authenticated user.

- **Headers**:
  - `Authorization: Bearer <access_token>`
  - `Content-Type: application/json`
- **Request Body**:
```json
{
  "password": "NewStrongPassword123"
}
```
- **Response (HTTP 200 OK)**:
```json
{
  "success": true,
  "message": "Password updated successfully"
}
```

---

#### POST `/tc-auth/logout`
Destroys the current active session.

- **Headers**: `Authorization: Bearer <access_token>`
- **Response (HTTP 200 OK)**:
```json
{
  "success": true,
  "message": "Session destroyed successfully"
}
```

---

#### POST `/tc-auth/logout-all`
Destroys all active sessions for the authenticated user.

- **Headers**: `Authorization: Bearer <access_token>`
- **Response (HTTP 200 OK)**:
```json
{
  "success": true,
  "message": "All sessions destroyed for account",
  "count": 3
}
```

---

#### POST `/tc-auth/account/oauth/link/{provider}` [NEW]
Aliases:
- `POST /tc-auth/account/oauth/link/google`
- `POST /tc-auth/account/oauth/link/github`
- `POST /tc-auth/account/oauth/link/discord`

- **Headers**: `Authorization: Bearer <access_token>`
- **Option 1 (Browser Redirect Flow)**:
  - Query: `?frontend_url=https://app.example.com/settings/security`
  - Body: `{"frontend_url": "https://app.example.com/settings/security"}`
  - Response: `HTTP 307 Temporary Redirect` to provider authorization page.
- **Option 2 (Direct Payload Flow)**:
  - Body: `{"provider_user_id": "google-user-12345"}`
  - Response (HTTP 200 OK):
```json
{
  "id": 2,
  "account_id": 1,
  "provider": "google",
  "provider_user_id": "google-user-12345",
  "created_at": "2026-09-12T12:00:00"
}
```

---

#### DELETE `/tc-auth/account/oauth/{provider}` [NEW]
Safely unlinks a connected OAuth provider (`google`, `github`, `discord`) from the authenticated account.

- **Headers**: `Authorization: Bearer <access_token>`
- **Path Parameter**: `provider` (`google` | `github` | `discord`)
- **Response (HTTP 200 OK)**:
```json
{
  "success": true,
  "message": "OAuth link for 'discord' removed successfully"
}
```
- **Error Response (HTTP 400 Bad Request on Lockout Prevention)**:
```json
{
  "success": false,
  "message": "Cannot unlink provider: account must have a password or at least one other active authentication method"
}
```

---

#### GET `/tc-auth/account/oauth/links` [NEW]
Retrieves all connected OAuth providers for the authenticated user.

- **Headers**: `Authorization: Bearer <access_token>`
- **Response (HTTP 200 OK)**:
```json
[
  {
    "id": 1,
    "account_id": 1,
    "provider": "google",
    "provider_user_id": "1048291039",
    "created_at": "2026-09-12T12:00:00"
  },
  {
    "id": 2,
    "account_id": 1,
    "provider": "discord",
    "provider_user_id": "928371948271049281",
    "created_at": "2026-09-12T12:05:00"
  }
]
```

---

### 3.3 OAuth Browser Login & Callback Routes

| Endpoint | Method | Query Parameters | Response / Behavior |
| :--- | :--- | :--- | :--- |
| `GET /tc-auth/google/login` | `GET` | `frontend_url` | `307 Redirect` $\rightarrow$ Google OAuth |
| `GET /tc-auth/google/callback` | `GET` | `code`, `state` | `307 Redirect` $\rightarrow$ `{frontend_url}/oauth/callback?access_token=...` (plus `&refresh_token=...` or `?linked=true&provider=google`) |
| `GET /tc-auth/github/login` | `GET` | `frontend_url` | `307 Redirect` $\rightarrow$ GitHub OAuth |
| `GET /tc-auth/github/callback` | `GET` | `code`, `state` | `307 Redirect` $\rightarrow$ `{frontend_url}/oauth/callback?access_token=...` (plus `&refresh_token=...` or `?linked=true&provider=github`) |
| `GET /tc-auth/discord/login` | `GET` | `frontend_url` | `307 Redirect` $\rightarrow$ Discord OAuth |
| `GET /tc-auth/discord/callback` | `GET` | `code`, `state` | `307 Redirect` $\rightarrow$ `{frontend_url}/oauth/callback?access_token=...` (plus `&refresh_token=...` or `?linked=true&provider=discord`) |

---

### 3.4 System, Health & Dashboard Configuration

#### GET `/tc-auth/config/pulse`
Health check and system liveness probe. Public endpoint.

- **Response (HTTP 200 OK)**:
```json
{
  "system_time": "2026-09-12T12:00:00.000000",
  "response": "Hello",
  "status": "healthy",
  "state": "active"
}
```

---

#### GET `/tc-auth/config/load/`
Loads the active in-memory configuration for all services. Requires `superadmin` role.

- **Headers**: `Authorization: Bearer <access_token>`
- **Response (HTTP 200 OK)**:
```json
{
  "email": {
    "host": "smtp.gmail.com",
    "port": 587,
    "username": "mailer@example.com",
    "password": "***",
    "sender": "noreply@example.com",
    "sender_name": "TC Auth",
    "use_tls": true
  },
  "github": {
    "client_id": "github-client-id",
    "client_secret": "***",
    "redirect_uri": "https://api.example.com/tc-auth/github/callback"
  },
  "google": {
    "client_id": "google-client-id",
    "client_secret": "***",
    "redirect_uri": "https://api.example.com/tc-auth/google/callback"
  },
  "discord": {
    "client_id": "discord-client-id",
    "client_secret": "***",
    "redirect_uri": "https://api.example.com/tc-auth/discord/callback"
  },
  "jwt": {
    "secret_key": "jwt-secret-key",
    "algorithm": "HS256",
    "session_duration_days": 7
  }
}
```

---

#### GET `/tc-auth/config/counts`
Returns table record counts. Requires `superadmin` role.

- **Headers**: `Authorization: Bearer <access_token>`
- **Response (HTTP 200 OK)**:
```json
{
  "accounts": 128,
  "oauth": 45,
  "sessions": 89,
  "otp": 4
}
```

---

#### POST `/tc-auth/config/jwt`
Updates JWT configuration, session lifespan, and dual-token mode settings. Requires `superadmin` role.

- **Headers**:
  - `Authorization: Bearer <access_token>`
  - `Content-Type: application/json`
- **Request Body**:
```json
{
  "secret_key": "new-super-secret-key",
  "algorithm": "HS256",
  "session_duration_days": 7,
  "dual_token_mode": true,
  "access_token_expire_minutes": 15,
  "refresh_token_expire_days": 7
}
```
- **Response (HTTP 200 OK)**:
```json
{
  "success": true,
  "message": "JWT configured successfully"
}
```

---

#### POST `/tc-auth/config/discord` [NEW]
Configures Discord OAuth credentials. Requires `superadmin` role.

- **Headers**:
  - `Authorization: Bearer <access_token>`
  - `Content-Type: application/json`
- **Request Body**:
```json
{
  "client_id": "discord-app-id",
  "client_secret": "discord-client-secret",
  "redirect_uri": "https://api.example.com/tc-auth/discord/callback"
}
```
- **Response (HTTP 200 OK)**:
```json
{
  "success": true,
  "message": "Discord OAuth configured successfully"
}
```

---

#### POST `/tc-auth/config/google` & POST `/tc-auth/config/github`
Configures Google and GitHub OAuth credentials. Requires `superadmin` role.

- **Request Body**:
```json
{
  "client_id": "provider-client-id",
  "client_secret": "provider-client-secret",
  "redirect_uri": "https://api.example.com/tc-auth/{provider}/callback"
}
```
- **Response (HTTP 200 OK)**: `{"success": true, "message": "Google/GitHub OAuth configured successfully"}`

---

#### POST `/tc-auth/config/email`
Configures SMTP email credentials. Requires `superadmin` role.

- **Request Body**:
```json
{
  "host": "smtp.gmail.com",
  "port": 587,
  "username": "mailer@example.com",
  "password": "smtp-app-password",
  "sender": "mailer@example.com",
  "sender_name": "TC Auth Service",
  "use_tls": true
}
```
- **Response (HTTP 200 OK)**: `{"success": true, "message": "Email service configured successfully"}`

---

### 3.5 Admin Resource Management (Superadmin Only)

All endpoints in this group require `Authorization: Bearer <access_token>` with `superadmin` role.

#### Admin Accounts (`/tc-auth/account`)
- `GET /tc-auth/account?page=1&limit=10` $\rightarrow$ `[{ "id": 1, "name": "...", ... }]`
- `GET /tc-auth/account/query?field=email&value=jane@example.com` $\rightarrow$ `[{ ... }]`
- `POST /tc-auth/account/` (Create User):
  - Body:
    ```json
    {
      "name": "Jane Doe",
      "email": "jane@example.com",
      "handle": "jane",
      "password": "Password123",
      "role": "user",
      "status": "active"
    }
    ```
  - Response: Created account object.
- `PATCH /tc-auth/account/` (Super Update):
  - Body:
    ```json
    {
      "account_id": 1,
      "role": "admin",
      "status": "active",
      "password": "NewPassword123"
    }
    ```
  - Response: Updated account object.
- `DELETE /tc-auth/account/`:
  - Body: `{"account_id": 1}`
  - Response: `{"success": true, "message": "Account deleted successfully"}`

#### Admin Sessions (`/tc-auth/session`)
- `GET /tc-auth/session?page=1&limit=10` $\rightarrow$ `[{ "id": 1, "account_id": 1, "ip_address": "...", ... }]`
- `GET /tc-auth/session/query?field=ip&value=127.0.0.1` $\rightarrow$ `[{ ... }]`
- `DELETE /tc-auth/session/` $\rightarrow$ Body: `{"session_id": 9}` $\rightarrow$ `{"success": true, "message": "Session destroyed successfully"}`
- `DELETE /tc-auth/session/all` $\rightarrow$ Body: `{"account_id": 1}` $\rightarrow$ `{"success": true, "message": "All sessions destroyed for account", "count": 2}`
- `DELETE /tc-auth/session/cleanup` $\rightarrow$ `{"success": true, "message": "Expired sessions cleaned up successfully", "count": 5}`
- `DELETE /tc-auth/session/clear` $\rightarrow$ `{"success": true, "message": "All sessions cleared successfully", "count": 20}`

#### Admin OAuth Links (`/tc-auth/oauth`)
- `GET /tc-auth/oauth?page=1&limit=10` $\rightarrow$ `[{ "id": 1, "account_id": 1, "provider": "google", ... }]`
- `GET /tc-auth/oauth/query?field=provider_id&value=12345` $\rightarrow$ `[{ ... }]`
- `POST /tc-auth/oauth/` $\rightarrow$ Body: `{"account_id": 1, "provider": "google", "provider_user_id": "12345"}` $\rightarrow$ Created link object.
- `DELETE /tc-auth/oauth/` $\rightarrow$ Body: `{"account_id": 1, "provider": "google"}` $\rightarrow$ `{"success": true, "message": "OAuth link removed successfully"}`

#### Admin OTP Records (`/tc-auth/otp`)
- `GET /tc-auth/otp?page=1&limit=10` $\rightarrow$ `[{ "id": 1, "identifier": "jane@example.com", "purpose": "login", ... }]`
- `GET /tc-auth/otp/query?identifier=jane@example.com` $\rightarrow$ `[{ ... }]`
- `POST /tc-auth/otp/` $\rightarrow$ Body: `{"identifier": "jane@example.com", "purpose": "login", "expiry": 300}` $\rightarrow$ `{"otp": "123456", "expires_at": 1735689600}`
- `DELETE /tc-auth/otp/` $\rightarrow$ Body: `{"identifier": "jane@example.com", "purpose": "login"}` $\rightarrow$ `{"success": true, "message": "OTP revoked successfully", "count": 1}`
- `DELETE /tc-auth/otp/cleanup` $\rightarrow$ `{"success": true, "message": "Expired OTPs cleaned successfully", "count": 3}`
- `DELETE /tc-auth/otp/clear` $\rightarrow$ `{"success": true, "message": "All OTPs cleared successfully", "count": 10}`

---

## 4. FastAPI Dependencies & Auth Context

`auth.deps` provides dependencies for protecting custom application endpoints:

```python
from fastapi import APIRouter, Depends
from connect import auth

router = APIRouter()

# 1. Complete Auth Context (account, session, payload)
@router.get("/me")
def get_me(user: dict = Depends(auth.deps.get_current_user)):
    return user

# 2. Account Object Only
@router.get("/profile")
def get_profile(account: dict = Depends(auth.deps.get_current_account)):
    return account

# 3. Session Object Only
@router.get("/session")
def get_session(session: dict = Depends(auth.deps.get_current_session)):
    return session

# 4. Role Requirement (Returns 403 if role does not match)
@router.get("/admin")
def admin_area(admin: dict = Depends(auth.role.require("admin", "superadmin"))):
    return {"message": "Welcome admin", "admin": admin}

# 5. Status Guard (Returns 403 if status does not match)
@router.get("/active-only")
def active_area(user: dict = Depends(auth.status.require("active"))):
    return {"message": "Welcome active user", "user": user}
```

---

## 5. Standard Error Format & Status Code Reference

All exceptions in `tc_auth` inherit from `AuthError` and produce a uniform JSON format:

```json
{
  "success": false,
  "message": "Human-readable description of what went wrong"
}
```

### Complete Status Code Mapping

| Exception Class | Status Code | Reason / Example Trigger |
| :--- | :--- | :--- |
| `InvalidEmailPurposeError` | `400 Bad Request` | Purpose not in `signup`, `login`, `reset`, `verify` |
| `InvalidConfigError` | `400 Bad Request` | Missing or malformed parameters in `.config(...)` |
| `WeakPasswordError` | `400 Bad Request` | Password fails length, uppercase, lowercase, or digit rules |
| `OAuthCallbackError` | `400 Bad Request` | OAuth code exchange failure, state mismatch, or profile fetch failure |
| `AuthError` (Lockout) | `400 Bad Request` | Attempting to unlink last remaining authentication method on an account |
| `OTPInvalidError` | `401 Unauthorized` | Invalid OTP code entered |
| `OTPExpiredError` | `401 Unauthorized` | Expired OTP code |
| `InvalidTokenError` | `401 Unauthorized` | Expired/invalid JWT access token, or refresh token used on protected route |
| `NotAuthenticatedError` | `401 Unauthorized` | Missing `Authorization: Bearer <token>` header or invalid session |
| `PermissionDeniedError` | `403 Forbidden` | Insufficient user role (e.g. non-superadmin hitting `/config/*`) |
| `AccountBlockedError` | `403 Forbidden` | Account status blocked or inactive |
| `UserNotFoundError` | `404 Not Found` | Requested user does not exist |
| `OTPNotFoundError` | `404 Not Found` | Target OTP record not found |
| `UserAlreadyExistsError` | `409 Conflict` | Email, handle, or phone already registered |
| `ConflictError` | `409 Conflict` | OAuth provider account already linked to another user profile |
| `OAuthAlreadyLinkedError` | `409 Conflict` | Provider account is already linked to this or another account |
| `EmailNotConfiguredError` | `500 Internal Error` | SMTP settings not configured before sending email |
| `OAuthNotConfiguredError` | `500 Internal Error` | OAuth provider not configured before starting OAuth flow |
| `EmailSendError` | `502 Bad Gateway` | SMTP server connection, timeout, or transmission error |
