# TC Auth — Complete Changelog & Frontend Integration Guide

This document tracks all new features, routes, architectural updates, frontend integration instructions, and documentation changes across `tc_auth`.

---

# Section 1: Features, Routes & Frontend Instructions

## 1.1 Overview: Cookie Mode vs localStorage Mode

`tc_auth` now supports a unified **Cookie Configuration Subsystem** (`auth.cookie`), allowing application backends to toggle between **localStorage mode** and **Cookie mode**.

* **Default Mode**: `cookie_mode = False` (`localStorage` mode).
  * 100% backwards compatible with existing frontend and SDK implementations.
  * No cookies are set; tokens are returned in JSON response bodies and OAuth redirect query parameters.
  * Authenticated requests use `Authorization: Bearer <access_token>`.
* **Cookie Mode**: `cookie_mode = True`.
  * The backend sets secure, `HttpOnly` session cookies on HTTP responses (`access_token`, and `refresh_token` if dual token mode is active).
  * Client browsers automatically send cookies on subsequent requests.
  * Protected routes accept either the `Authorization: Bearer <token>` header or the `access_token` cookie.
  * **Zero Breaking Changes**:
    * Direct SDK methods (`auth.service.create_login_response`, `auth.oauth.login`) continue returning their standard dictionary payloads.
    * OAuth redirects still preserve `?access_token=...&refresh_token=...` in the redirect URL so existing frontend callback parsers never fail.

---

## 1.2 Frontend Guide: Handling Both Modes (Dual-Mode & Single-Mode Architecture)

Frontend developers can easily build applications that support **both localStorage mode and Cookie mode simultaneously**, or support either mode exclusively.

### Mode Comparison for Frontend Developers

| Action | localStorage Mode (`cookie_mode=False`) | Cookie Mode (`cookie_mode=True`) | Universal Handling (Works in Both Modes) |
| :--- | :--- | :--- | :--- |
| **Login / Signup** | Tokens returned in JSON body -> save to `localStorage` | Browser saves `Set-Cookie` automatically | Save JSON body tokens if present; cookies are saved automatically by browser |
| **Protected Requests** | Must send `Authorization: Bearer <token>` | Browser sends cookies automatically | Send `credentials: "include"` AND `Authorization: Bearer <token>` (if present) |
| **OAuth Callback** | Read query param `?access_token=...` -> save to `localStorage` | Cookies already saved by browser on 307 redirect | Read query params into `localStorage` if present; cookies are already in browser |
| **Token Refresh** | Must send `{ refresh_token }` in JSON body | Browser sends cookie automatically; body `{}` | Send `{ refresh_token: localStorage.getItem("refresh_token") \|\| null }` with `credentials: "include"` |
| **Logout** | Call `/logout`, remove tokens from `localStorage` | Call `/logout`, browser cookies are cleared by backend | Call `/logout` with `credentials: "include"`, clear `localStorage` |
| **CORS Requirement** | Standard CORS headers | Backend CORS **must** specify explicit origins (not wildcard `*`) | Explicit origins in CORS backend config (`allow_origins=["http://localhost:3000"]`) |

---

### Universal Production Client (`authClient.js`)

Here is a drop-in universal frontend client that handles **both** modes transparently:

```javascript
// authClient.js
const API_BASE = "https://api.example.com/tc-auth";

/**
 * Universal fetch wrapper supporting both localStorage & Cookie modes
 */
export async function apiRequest(endpoint, options = {}) {
  const token = localStorage.getItem("access_token");

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  // If token is saved in localStorage, attach Bearer header.
  // In Cookie mode, backend accepts either Bearer header or Cookie.
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Always include credentials so cookies are sent if in Cookie mode
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    credentials: "include", // CRITICAL for Cookie mode
  });

  return response;
}

/**
 * Universal Login
 */
export async function login(identifier, password) {
  const res = await apiRequest("/login/password", {
    method: "POST",
    body: JSON.stringify({ identifier, password }),
  });

  const data = await res.json();
  if (res.ok) {
    // If backend returns tokens in body (localStorage mode or dual), save them:
    if (data.access_token) {
      localStorage.setItem("access_token", data.access_token);
    }
    if (data.refresh_token) {
      localStorage.setItem("refresh_token", data.refresh_token);
    }
  }
  return { ok: res.ok, data };
}

/**
 * Universal Token Refresh
 */
export async function refreshToken() {
  const storedRefreshToken = localStorage.getItem("refresh_token");

  // In Cookie mode, body can be empty because the browser sends the refresh_token cookie.
  // In localStorage mode, body carries the refresh token.
  const payload = storedRefreshToken ? { refresh_token: storedRefreshToken } : {};

  const res = await apiRequest("/token/refresh", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (res.ok && data.access_token) {
    localStorage.setItem("access_token", data.access_token);
    if (data.refresh_token) {
      localStorage.setItem("refresh_token", data.refresh_token);
    }
  }
  return { ok: res.ok, data };
}

/**
 * Universal OAuth Callback Handler (/oauth/callback route)
 */
export function handleOAuthCallback() {
  const params = new URLSearchParams(window.location.search);
  const accessToken = params.get("access_token");
  const refreshToken = params.get("refresh_token");

  // If parameters exist in URL (localStorage mode or fallback), persist them:
  if (accessToken) {
    localStorage.setItem("access_token", accessToken);
  }
  if (refreshToken) {
    localStorage.setItem("refresh_token", refreshToken);
  }

  // In Cookie mode, cookies are already set by the browser via Set-Cookie on the 307 redirect!
  
  // Clean URL to avoid keeping tokens in browser history
  window.history.replaceState({}, document.title, window.location.pathname);
}

/**
 * Universal Logout
 */
export async function logout() {
  try {
    await apiRequest("/logout", { method: "POST" });
  } finally {
    // Clear client-side storage regardless of mode
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    window.location.href = "/login";
  }
}
```

---

## 1.3 Backend Configuration

### Environment Variables (`config.py`)
```env
COOKIE_MODE=false
COOKIE_ACCESS_NAME=access_token
COOKIE_REFRESH_NAME=refresh_token
COOKIE_PATH=/
COOKIE_DOMAIN=
COOKIE_SECURE=false
COOKIE_HTTPONLY=true
COOKIE_SAMESITE=lax
COOKIE_MAX_AGE=
```

### SDK Initializer (`main.py` / `connect.py`)
```python
auth.cookie.config(
    cookie_mode=config.COOKIE_MODE,               # bool: True enables cookie mode
    access_cookie_name=config.COOKIE_ACCESS_NAME, # default: "access_token"
    refresh_cookie_name=config.COOKIE_REFRESH_NAME,# default: "refresh_token"
    path=config.COOKIE_PATH,                      # default: "/"
    domain=config.COOKIE_DOMAIN,                  # default: None
    secure=config.COOKIE_SECURE,                  # set to True in HTTPS production
    httponly=config.COOKIE_HTTPONLY,              # default: True (prevents JS XSS access)
    samesite=config.COOKIE_SAMESITE,              # "lax", "strict", or "none" (none requires secure=True)
    max_age=config.COOKIE_MAX_AGE,                # None = automatically synchronized with JWT durations
)
```

---

## 1.3 New & Updated Routes Specification

### 1. New Route: `POST /tc-auth/config/cookie`
Configures cookie behavior dynamically at runtime (Admin Dashboard).

* **Path**: `/tc-auth/config/cookie`
* **Method**: `POST`
* **Authentication**: Required (`superadmin` role)
* **Request Headers**: `Authorization: Bearer <token>`
* **Request Body** (`CookieConfig`):
  ```json
  {
    "cookie_mode": true,
    "access_cookie_name": "access_token",
    "refresh_cookie_name": "refresh_token",
    "path": "/",
    "domain": null,
    "secure": false,
    "httponly": true,
    "samesite": "lax",
    "max_age": null
  }
  ```
* **Success Response** (`200 OK`):
  ```json
  {
    "success": true,
    "message": "Cookie configured successfully"
  }
  ```
* **Error Responses**:
  * `400 Bad Request`: Invalid parameter (e.g. `samesite="none"` without `secure=true`).
  * `401 Unauthorized`: Missing or invalid credentials.
  * `403 Forbidden`: User is not a `superadmin`.

---

### 2. Updated Route: `GET /tc-auth/config/load/`
Returns the current configuration of all auth subsystems, now including the `"cookie"` configuration block.

* **Path**: `/tc-auth/config/load/`
* **Method**: `GET`
* **Authentication**: Required (`superadmin` role)
* **Success Response** (`200 OK`):
  ```json
  {
    "email": { ... },
    "github": { ... },
    "google": { ... },
    "discord": { ... },
    "jwt": { ... },
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
    }
  }
  ```

---

### 3. Updated Route: `POST /tc-auth/token/refresh`
Refreshes the access token (and rotates refresh token if dual token mode).

* **Path**: `/tc-auth/token/refresh`
* **Method**: `POST`
* **Authentication**: None
* **Request Body** (`RefreshTokenRequest`):
  * **localStorage mode**: `{"refresh_token": "<refresh_jwt>"}`
  * **Cookie mode**: `{}` (Request body is optional; token is read automatically from the `refresh_token` cookie)
* **Behavior when `cookie_mode=True`**:
  * Reads `refresh_token` from request body or from `request.cookies["refresh_token"]`.
  * Emits `Set-Cookie` response headers updating the access and refresh token cookies.
  * Returns success status and cookie metadata without leaking tokens in JSON body:
    ```json
    {
      "success": true,
      "message": "Tokens refreshed successfully",
      "token_type": "Cookie",
      "cookie": {
        "cookie_mode": true,
        "access_cookie_name": "access_token",
        "refresh_cookie_name": "refresh_token",
        "path": "/",
        "domain": ".codesena.me",
        "secure": true,
        "samesite": "lax"
      }
    }
    ```
* **Behavior when `cookie_mode=False`**:
  * Returns tokens in JSON response body:
    ```json
    {
      "access_token": "eyJhbGciOi...",
      "refresh_token": "eyJhbGciOi...",
      "token_type": "Bearer"
    }
    ```

---

### 4. Updated Auth Routes (Login, Signup, Magic Link, Forgot Password)
* `POST /tc-auth/signup/password`
* `POST /tc-auth/signup/otp`
* `POST /tc-auth/login/password`
* `POST /tc-auth/login/otp`
* `POST /tc-auth/forgot/password`
* `POST /tc-auth/link/login`
* **Behavior**:
  * If `cookie_mode=False`: Returns standard JSON payload with tokens (`access_token`, `refresh_token`, `token_type`: `"Bearer"`, `account`); no cookies set.
  * If `cookie_mode=True`: Sets `Set-Cookie` headers on HTTP response and returns account and cookie metadata without leaking tokens in the body:
    ```json
    {
      "token_type": "Cookie",
      "account": {
        "id": 1,
        "email": "user@example.com",
        "name": "User Name",
        "role": "user"
      },
      "cookie": {
        "cookie_mode": true,
        "access_cookie_name": "access_token",
        "refresh_cookie_name": "refresh_token",
        "path": "/",
        "domain": ".codesena.me",
        "secure": true,
        "samesite": "lax"
      }
    }
    ```

---

### 5. Updated Magic Link GET Callback: `GET /tc-auth/link/{purpose}`
* **Behavior when `purpose=login`**:
  * Redirects with `307 Temporary Redirect` to `{frontend_url}/oauth/callback?access_token=...&refresh_token=...`.
  * When `cookie_mode=True`: Attaches `Set-Cookie` headers to the `RedirectResponse`.

---

### 6. Updated Logout Routes: `POST /tc-auth/logout` & `POST /tc-auth/logout-all`
* **Path**: `/tc-auth/logout` and `/tc-auth/logout-all`
* **Method**: `POST`
* **Authentication**: Required (`Authorization: Bearer <token>` or `access_token` cookie)
* **Behavior**:
  * Destroys active database session(s).
  * When `cookie_mode=True`: Emits `Set-Cookie` headers with expired max-age to immediately delete `access_token` and `refresh_token` cookies from the browser.
* **Success Response** (`200 OK`):
  ```json
  {
    "success": true,
    "message": "Session deleted successfully"
  }
  ```

---

### 7. Updated OAuth Callbacks: `/google/callback`, `/github/callback`, `/discord/callback`
* **Path**: `/tc-auth/{provider}/callback`
* **Behavior**:
  * Redirects user back to `{frontend_url}/oauth/callback?access_token=...&refresh_token=...`.
  * **When `cookie_mode=True`**:
    * Emits `Set-Cookie` headers on the `RedirectResponse`.
    * **Preserves** `access_token` and `refresh_token` in the redirect query parameters so existing frontend OAuth callback handlers continue functioning without changes.

---

### 8. Updated Protected Routes (`AuthDeps`)
* `GET /tc-auth/me`
* `PATCH /tc-auth/me`
* `PUT /tc-auth/update/password`
* All routes protected by `auth.deps.get_current_user`, `auth.role.require()`, etc.
* **Behavior**:
  * Checks for `Authorization: Bearer <token>` header first.
  * If header is missing, checks `request.cookies.get("access_token")`.
  * If a valid token is found via either mechanism, the request is authenticated.
  * If neither is present, returns `401 Unauthorized` (`"Missing authorization credentials"`).

---

## 1.4 Frontend Integration Guide

### 1. HTTP Client Configuration (CORS & Credentials)

When using **Cookie mode**, the browser must be instructed to include and store cookies across cross-origin requests.

#### Using Native `fetch()`
Add `credentials: "include"` to all requests:
```javascript
const response = await fetch("https://api.example.com/tc-auth/login/password", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  credentials: "include", // CRITICAL: Allows browser to send and receive cookies
  body: JSON.stringify({
    identifier: "user@example.com",
    password: "Password123!",
  }),
});
```

#### Using `axios`
Enable `withCredentials`:
```javascript
import axios from "axios";

const api = axios.create({
  baseURL: "https://api.example.com/tc-auth",
  withCredentials: true, // CRITICAL: Sends and receives cookies automatically
});
```

> [!IMPORTANT]
> **CORS Backend Requirement**: When `credentials: "include"` is used, the browser rejects responses if the backend has `allow_origins=["*"]`. The backend must declare explicit allowed origins (e.g., `allow_origins=["http://localhost:3000", "https://app.example.com"]`).

---

### 2. Authentication Handling: localStorage vs Cookie

#### In localStorage Mode (`cookie_mode=False`, Default)
```javascript
// On Login:
const data = await response.json();
localStorage.setItem("access_token", data.access_token);
if (data.refresh_token) {
  localStorage.setItem("refresh_token", data.refresh_token);
}

// On Subsequent Requests:
const res = await fetch("https://api.example.com/tc-auth/me", {
  headers: {
    Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  },
});
```

#### In Cookie Mode (`cookie_mode=True`)
```javascript
// On Login:
// Browser stores cookies automatically! No localStorage manipulation required.
const data = await response.json();
console.log("Logged in user:", data.account);

// On Subsequent Requests:
// Browser attaches cookies automatically:
const res = await fetch("https://api.example.com/tc-auth/me", {
  credentials: "include",
});
const user = await res.json();
```

---

### 3. Token Refresh in Cookie Mode

In Cookie Mode, the frontend does not need to send the refresh token in the body:
```javascript
async function refreshAccessToken() {
  const response = await fetch("https://api.example.com/tc-auth/token/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include", // Browser sends refresh_token cookie automatically
    body: JSON.stringify({}), // Body can be empty
  });

  if (response.ok) {
    console.log("Tokens refreshed and cookies updated automatically!");
  } else {
    // Refresh failed or session expired -> redirect to login
    window.location.href = "/login";
  }
}
```

---

### 4. OAuth Callback Handling

The OAuth callback redirect URL retains query parameters in both modes:
```javascript
// Frontend route: /oauth/callback
const params = new URLSearchParams(window.location.search);
const accessToken = params.get("access_token");
const refreshToken = params.get("refresh_token");

// If in localStorage mode:
if (accessToken) {
  localStorage.setItem("access_token", accessToken);
  if (refreshToken) localStorage.setItem("refresh_token", refreshToken);
}

// If in Cookie mode:
// Cookies are ALREADY stored in document.cookie / browser jar from the 307 redirect!
// Redirect user directly to dashboard:
window.location.href = "/dashboard";
```

---

### 5. Logout Flow

```javascript
async function logout() {
  await fetch("https://api.example.com/tc-auth/logout", {
    method: "POST",
    credentials: "include", // Required to send session and receive expired cookie headers
  });

  // Clean local storage if applicable
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");

  window.location.href = "/login";
}
```

---

# Section 2: `api_docs` Changes (`api/filename.md`)

Below are the changes made to documentation files in `api_docs/`:

### `api/dashboard_route.md`
- **Added `POST /tc-auth/config/cookie` documentation**:
  - Request schema (`CookieConfig`): `cookie_mode`, `access_cookie_name`, `refresh_cookie_name`, `path`, `domain`, `secure`, `httponly`, `samesite`, `max_age`.
  - Requires `superadmin` role.
  - Return structure: `{"success": true, "message": "Cookie configured successfully"}`.
- **Updated `GET /tc-auth/config/load/`**:
  - Added `"cookie"` object to the returned JSON response showing current cookie status and settings.

### `api/login_route.md`
- **Updated Signup & Login Endpoints**:
  - Added notes to `POST /signup/password`, `POST /signup/otp`, `POST /login/password`, `POST /login/otp`, `POST /forgot/password`: when `cookie_mode=True`, `Set-Cookie` response headers are attached for `access_token` and `refresh_token`.
- **Updated `POST /token/refresh`**:
  - Documented that `refresh_token` field in request body is optional when cookie mode is enabled, as the endpoint extracts it directly from `request.cookies["refresh_token"]`.
  - Documented that updated tokens are emitted via `Set-Cookie` headers.
- **Updated `GET /link/{purpose}` (Magic Link)**:
  - Documented that the HTTP 307 redirect response attaches `Set-Cookie` headers on successful login.

### `api/account_route.md`
- **Updated `POST /logout` & `POST /logout-all`**:
  - Documented that both logout endpoints clear and expire `access_token` and `refresh_token` cookies when `cookie_mode=True`.

### `api/oauth_route.md`
- **Updated OAuth Callback Endpoints** (`/google/callback`, `/github/callback`, `/discord/callback`):
  - Added specification that when `cookie_mode=True`, `Set-Cookie` headers are set on the `RedirectResponse` while preserving URL query parameters.

### `api/oauth_integration.md`
- **Updated Frontend Callback Section**:
  - Added instructions for handling OAuth responses under both `localStorage` and `Cookie` modes.
  - Highlighted that cookie mode automatically populates session cookies before the browser arrives at `/oauth/callback`.

### `api/token_usage_guide.md`
- **Updated Token Storage & Transmission Sections**:
  - Added architectural comparison of `localStorage` vs `Cookie` modes.
  - Added frontend configuration recommendations (`credentials: "include"`, `withCredentials: true`, SameSite attributes, and HTTPS requirements).
  - Documented dual authentication support in backend dependencies (`HTTPBearer` fallback to cookie).

---

# Section 3: `usage` (SDK Changes) (`sdk/folder/filename.md`)

Below are the changes made to SDK code and documentation files in `usage/`:

### `sdk/cookie/cookie.py` (New File)
- **Created SDK Usage Script**:
  - Demonstrates `auth.cookie.load()` to read current cookie configuration.
  - Demonstrates `auth.cookie.config(cookie_mode=False)` for default localStorage mode.
  - Demonstrates `auth.cookie.config(cookie_mode=True, ...)` for enabling cookie mode with custom flags (`secure`, `httponly`, `samesite`, `max_age`).
  - Demonstrates `auth.cookie.is_cookie_mode()` helper.

### `sdk/cookie/cookie.md` (New File)
- **Created SDK Documentation**:
  - Comprehensive guide on `auth.cookie` module methods, parameter definitions, and defaults.
  - Comparison table between localStorage mode and Cookie mode.
  - Dashboard API endpoint reference for `POST /tc-auth/config/cookie` and `GET /tc-auth/config/load/`.
  - OAuth backwards-compatibility explanation.

### `sdk/connect/connect.py`
- **Updated Service Exposure**:
  - Added `# auth.cookie -> CookieService` under section `# 2. INITIALIZE TC-AUTH`.
- **Added Cookie Configuration Section**:
  - Added section `# 8. COOKIE CONFIGURATION (OPTIONAL)` demonstrating `auth.cookie.config(cookie_mode=False, ...)`.

### `sdk/auth/auth.py`
- **Updated `create_login_response()` Documentation**:
  - Documented optional `response: Response | None = None` parameter on `auth.service.create_login_response(...)`, `auth.service.signup(...)`, and `auth.service.login(...)`.
  - Clarified that the method continues to return the standard dictionary (`access_token`, `token_type`, `account`, `refresh_token`), while setting cookies on `response` if provided.

### `sdk/auth/auth.md`
- **Updated Method Descriptions**:
  - Added notes regarding cookie delivery when `response` object is passed into `create_login_response()`.

### `sdk/dependency/dependency.py` & `sdk/dependency/dependency.md`
- **Updated Auth Dependency Usage**:
  - Documented that `auth.deps.get_current_user`, `get_current_account`, and dependent role/status dependencies automatically extract tokens from either `Authorization: Bearer <token>` or request cookies.
