# Magic Link Authentication Guide

Base path: Configurable (defaults to `/tc-auth` via `auth.include_routes(app, prefix="/tc-auth")`).
All routes and code examples below are relative to your auth `baseUrl` (e.g. `const baseUrl = "https://api.example.com/tc-auth"`).

The **Magic Link** system in `tc_auth` provides seamless passwordless authentication built directly on top of the email OTP infrastructure. Instead of requiring redundant database tables or conflicting token stores, Magic Links utilize the core `OTP` table and `OTPService`.

---

## 1. UI Intent Guideline: When to Use Which Route

| User Action in UI | Endpoint to Call | Rationale |
| :--- | :--- | :--- |
| User explicitly clicks **"Send me Magic Link"** / **"Sign In with Magic Link"** button | **`POST /send/email/link/{purpose}`** | **Use this route ONLY when the user explicitly requests a magic link.** This endpoint communicates explicit intent, formats dedicated subject lines (*"Sign-In Link & Code"*), and requires/resolves the frontend destination. |
| User submits standard form or clicks **"Send OTP"** / **"Sign In"** | **`POST /send/email/otp/{purpose}`** | Use for standard email OTP screens. The email still includes the one-click Magic Link button if `frontend_url` is provided or detected from the browser's `Origin` header. |

---

## 2. Automatic `frontend_url` Resolution

The backend resolves `frontend_url` using three sources (in order of priority):
1. **JSON Request Body**: `{ "email": "jane@example.com", "frontend_url": "https://app.example.com" }`
2. **Query Parameter**: `POST /send/email/otp/login?frontend_url=https://app.example.com`
3. **Browser Header (`Origin`)**: When frontend applications call `fetch` or `axios`, browsers attach `Origin: https://app.example.com`, which `tc_auth` automatically uses.

---

## 3. Dual Authentication Pathways in Every Email

Every email dispatched through the Magic Link / OTP system provides two ways to complete authentication:

```
+-----------------------------------------------------------+
|               Verification & Authentication               |
+-----------------------------------------------------------+
|                                                           |
|  Click the button below to complete your action:          |
|                                                           |
|             [   CLICK TO PROCEED   ]   <--- (Magic Link)  |
|                                                           |
|  Button not working? Copy and paste this link:            |
|  https://api.example.com/tc-auth/link/login?email=...     |
|                                                           |
|               --- OR USE VERIFICATION CODE ---            |
|                                                           |
|                         [ 8 4 9 2 0 1 ] <--- (Manual OTP) |
|                                                           |
|  This code and link expire in 5 minutes.                  |
+-----------------------------------------------------------+
```

1. **One-Click Action Button**: Directly verifies the OTP and authenticates the user.
2. **Manual 6-Digit OTP Code**: Allows users opening the email on a separate device (e.g. mobile email, desktop app) to input the code manually.

---

## 4. Support for All Modes (Single, Dual Token & Cookie Mode)

The Magic Link system supports all `tc_auth` operational modes:

| Mode | `GET /link/login` (Direct Browser Click) | `POST /link/login` (API Request) |
| :--- | :--- | :--- |
| **Single-Token + Local Storage** | Redirects `307` to `{frontend_url}/oauth/callback?access_token=...` | Returns JSON: `{ "access_token": "...", "token_type": "Bearer", "account": {...} }` |
| **Dual-Token + Local Storage** | Redirects `307` to `{frontend_url}/oauth/callback?access_token=...&refresh_token=...` | Returns JSON: `{ "access_token": "...", "refresh_token": "...", "token_type": "Bearer", "account": {...} }` |
| **Cookie Mode (Single or Dual)** | Sets `HttpOnly` cookies + Redirects `307` to `{frontend_url}/oauth/callback` | Sets `HttpOnly` cookies + Returns JSON: `{ "token_type": "Cookie", "account": {...} }` |

> [!TIP]
> **OAuth Callback Reuse**: Because `GET /link/login` redirects to `{frontend_url}/oauth/callback`, your frontend application reuses the exact same callback router used for Google, GitHub, and Discord OAuth!

---

## 5. Dual Verification Architecture: Browser Direct vs Bot-Safe SPA

```
                            Email Received by User
                                       │
           ┌───────────────────────────┴───────────────────────────┐
           ▼                                                       ▼
Direct Browser Verification                                SPA Bot-Safe Verification
GET /link/{purpose}                                       POST /link/{purpose}
(Direct click in email client)                            (SPA confirmation button)
           │                                                       │
           ▼                                                       ▼
Backend verifies single-use OTP                           Frontend sends JSON via fetch
Creates session & generates JWTs                          Returns JSON tokens & user
Sets cookies (if Cookie Mode enabled)                     Persisted in localStorage / cookies
Redirects HTTP 307 to:                                              │
{frontend_url}/oauth/callback                                      ▼
?access_token=...&refresh_token=...                       User Authenticated!
           │
           ▼
Reuses Existing Frontend OAuth Router!
```

---

## 6. Endpoints Reference

### 6.1 Requesting a Magic Link

#### `POST /send/email/link/{purpose}` (Dedicated Magic Link)
- **Path Parameter**: `purpose` (`signup` | `login` | `reset` | `verify`)
- **Request Body**:
  ```json
  {
    "email": "jane@example.com",
    "frontend_url": "https://app.example.com"
  }
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "expires_at": 1735689600
  }
  ```

JavaScript Example:
```js
const res = await fetch(`${baseUrl}/send/email/link/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    email: "jane@example.com",
    frontend_url: window.location.origin,
  }),
});
const data = await res.json();
```

#### `POST /send/email/otp/{purpose}` (Standard OTP with Magic Link)
- **Path Parameter**: `purpose` (`signup` | `login` | `reset` | `verify`)
- **Request Body**:
  ```json
  {
    "email": "jane@example.com",
    "frontend_url": "https://app.example.com"
  }
  ```

JavaScript Example:
```js
const res = await fetch(`${baseUrl}/send/email/otp/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    email: "jane@example.com",
    frontend_url: window.location.origin,
  }),
});
```

---

### 6.2 Verifying a Magic Link

#### Method 1: Direct Browser Verification (`GET /link/{purpose}`)

Query Parameters:
- `email`: User's email address
- `otp`: Single-use OTP code
- `frontend_url`: Base URL of the frontend application

Behavior by Purpose:
- **`login`**: Validates OTP, burns code, creates session, issues JWTs/cookies, and **redirects (HTTP 307)** to `{frontend_url}/oauth/callback?access_token=...`
- **`verify`**: Validates OTP, burns code, activates account (`status: "active"`), and **redirects (HTTP 307)** to `{frontend_url}/magic-link/callback?verified=true&email=...`
- **`reset`**: Validates OTP **without burning it**, and **redirects (HTTP 307)** to `{frontend_url}/reset-password?email=...&otp=...`
- **`signup`**: Validates OTP **without burning it**, and **redirects (HTTP 307)** to `{frontend_url}/signup?email=...&otp=...&verified=true`

Error Handling (Expired or Replayed Links):
Redirects with `HTTP 307` to:
`{frontend_url}/magic-link/callback?error={url_encoded_error}`

---

#### Method 2: Programmatic Bot-Safe Verification (`POST /link/{purpose}`)

Used when defending against corporate email antivirus scanners that pre-fetch incoming email links. Configure emails to open `{frontend_url}/confirm-login?email=...&otp=...` with a user button that submits this POST request.

- **Path Parameter**: `purpose` (`login` | `verify` | `reset` | `signup`)
- **Request Body**:
  ```json
  {
    "email": "jane@example.com",
    "otp": "123456"
  }
  ```

- **Response for `login` (Single-Token Mode)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
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

- **Response for `login` (Dual-Token Mode)**:
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

- **Response for `verify`**:
  ```json
  {
    "success": true,
    "message": "Email verified successfully",
    "email": "jane@example.com"
  }
  ```

JavaScript Example (Bot-Safe Confirmation):
```js
async function confirmMagicLinkLogin(email, otp) {
  const res = await fetch(`${baseUrl}/link/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include", // Supports both Cookie and Header modes
    body: JSON.stringify({ email, otp }),
  });

  if (res.ok) {
    const data = await res.json();
    if (data.access_token) {
      localStorage.setItem("access_token", data.access_token);
      if (data.refresh_token) {
        localStorage.setItem("refresh_token", data.refresh_token);
      }
    }
    window.location.href = "/dashboard";
  } else {
    const err = await res.json();
    alert(`Login failed: ${err.message || "Invalid or expired link"}`);
  }
}
```

---

## 7. Frontend Callback Router Implementation

### 7.1 Reusing `/oauth/callback` for Magic Link Login

```js
// Vanilla JavaScript / SPA Callback Handler
(function handleAuthCallback() {
  const params = new URLSearchParams(window.location.search);
  const accessToken = params.get("access_token");
  const refreshToken = params.get("refresh_token");

  // Clean sensitive parameters from browser history
  if (window.location.search) {
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  if (accessToken) {
    localStorage.setItem("access_token", accessToken);
    if (refreshToken) {
      localStorage.setItem("refresh_token", refreshToken);
    }
    window.location.href = "/dashboard";
    return;
  }

  // If using Cookie Mode, verify session:
  fetch(`${baseUrl}/me`, { credentials: "include" })
    .then((res) => {
      if (res.ok) {
        window.location.href = "/dashboard";
      } else {
        window.location.href = "/login";
      }
    })
    .catch(() => {
      window.location.href = "/login";
    });
})();
```

### 7.2 Email Verification & Error Callback Router (`/magic-link/callback`)

Handles email verification notifications (`GET /link/verify`) and error alerts:

```js
(function handleMagicLinkCallback() {
  const params = new URLSearchParams(window.location.search);
  const verified = params.get("verified");
  const email = params.get("email");
  const error = params.get("error");

  if (error) {
    alert(`Authentication Error: ${error}`);
    window.location.href = "/login";
    return;
  }

  if (verified === "true") {
    alert(`Email ${email} has been successfully verified! Please log in.`);
    window.location.href = "/login";
    return;
  }

  window.location.href = "/login";
})();
```

---

## 8. Python SDK Usage

```python
from connect import auth

# 1. Send Magic Link explicitly
auth.email.send_magic_link(
    email="jane@example.com",
    purpose="login",
    frontend_url="https://app.example.com",
    expiry=300,
)

# 2. Send standard OTP (automatically attaches magic link button if frontend_url is present)
auth.email.send_otp(
    email="jane@example.com",
    purpose="login",
    frontend_url="https://app.example.com",
)

# 3. Dedicated helpers
auth.email.send_login_otp(email="jane@example.com", frontend_url="https://app.example.com")
auth.email.send_verify_email(email="jane@example.com", frontend_url="https://app.example.com")
auth.email.send_reset_otp(email="jane@example.com", frontend_url="https://app.example.com")
auth.email.send_signup_otp(email="jane@example.com", frontend_url="https://app.example.com")

# 4. Programmatic service verification
login_data = auth.service.login_magic_link(
    email="jane@example.com",
    otp="123456",
)
```

---

## 9. Security Features & Edge Cases

1. **Replay Attack Prevention**:
   - Single-use OTPs are permanently burned and deleted from the database upon successful verification for `login` and `verify`.
   - Repeated clicks on the same link are immediately rejected with an error redirect.
2. **Non-Destructive Validation for Reset & Signup**:
   - For `reset` and `signup`, `GET /link/{purpose}` validates that the OTP is genuine and unexpired **without deleting it**, allowing the user to safely submit their password on the subsequent form.
3. **Reverse-Proxy Support**:
   - Generates accurate verification URLs behind SSL terminators and reverse proxies using `X-Forwarded-Proto` and `X-Forwarded-Host`.
4. **Adaptive Token Modes**:
   - Fully compatible with Single-Token Mode (`access_token` only), Dual-Token Mode (`access_token` + `refresh_token`), and HttpOnly Cookie Mode.
