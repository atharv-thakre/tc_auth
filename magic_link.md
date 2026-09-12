# Magic Link Authentication System

The **Magic Link** system in `tc_auth` provides seamless, passwordless authentication built directly on top of the battle-tested email OTP infrastructure.

Instead of introducing redundant database tables or conflicting token stores, Magic Links utilize the core `OTP` table (`identifier`, `purpose`, `code_hash`, `expires_at`, `attempts`) and `OTPService`.

---

## 1. UI Design & Intent Guideline: When to Use Which Route

To ensure the best user experience and clear separation of intent, follow this rule when integrating frontend forms:

| User Action in UI | Endpoint to Call | Rationale |
| :--- | :--- | :--- |
| User explicitly clicks **"Send me Magic Link"** / **"Sign In with Magic Link"** button | **`POST /tc-auth/send/email/link/{purpose}`** | **Use this route ONLY when the user explicitly requests a magic link.** When a user clicks a dedicated magic link button, their primary expectation is a one-click login link. This endpoint communicates explicit intent, sets descriptive subject lines (e.g., *"Sign-In Link & Code"*), and requires/resolves the frontend destination. |
| User submits standard form or clicks **"Send OTP"** / **"Sign In"** | **`POST /tc-auth/send/email/otp/{purpose}`** | Use for your standard email OTP screens. The email will still conveniently provide the one-click Magic Link button if `frontend_url` is provided or automatically detected via the `Origin` header, but the primary user context remains standard OTP verification. |

---

## 2. Note: Existing Send OTP Route Also Mails Magic Links!

> [!IMPORTANT]
> **Existing integrations do NOT need to change endpoints to get Magic Link capabilities.**
> 
> The existing `POST /tc-auth/send/email/otp/{purpose}` endpoint automatically generates and emails the one-click Magic Link button alongside the 6-digit OTP code whenever a frontend URL is detected.

### Automatic `frontend_url` Resolution:
The endpoint looks for `frontend_url` across three locations (in order of priority):
1. **JSON Body**:
   ```json
   {
     "email": "jane@example.com",
     "frontend_url": "https://app.example.com"
   }
   ```
2. **Query Parameter**:
   ```http
   POST /tc-auth/send/email/otp/login?frontend_url=https://app.example.com
   ```
3. **Automatic Browser Header (`Origin`)**:
   When your frontend web application issues a standard `fetch` or `axios` call, modern browsers automatically attach the `Origin` header (e.g. `Origin: https://app.example.com`). `tc_auth` detects this header and automatically generates the Magic Link pointing back to your frontend with **zero frontend code changes needed**!

---

## 3. Dual Authentication Inside Every Email

Every email dispatched through the Magic Link / OTP system renders **two authentication pathways** in a single email:

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

1. **One-Click CTA Button ("Click to Proceed")**: Clicking this button directly verifies and authenticates the user.
2. **Manual 6-Digit OTP Code**: Displayed prominently below the button so users who open the email on a separate device (e.g. email on phone, application on desktop) can enter the 6-digit code manually.

---

## 4. Full Support for Both Token Modes (Single & Dual Token)

The Magic Link system automatically detects and respects `tc_auth`'s token mode configuration:

| Mode | `GET /tc-auth/link/login` (Browser Redirect) | `POST /tc-auth/link/login` (API JSON Response) |
| :--- | :--- | :--- |
| **Single-Token Mode** *(Default)* | Redirects `307` to:<br>`{frontend_url}/oauth/callback?access_token=...` | Returns JSON:<br>`{ "access_token": "...", "token_type": "Bearer", "account": {...} }` |
| **Dual-Token Mode** *(When enabled via `dual_token_mode=True`)* | Redirects `307` to:<br>`{frontend_url}/oauth/callback?access_token=...&refresh_token=...` | Returns JSON:<br>`{ "access_token": "...", "refresh_token": "...", "token_type": "Bearer", "account": {...} }` |

> [!TIP]
> **Why redirect to `{frontend_url}/oauth/callback`?**
> By using the exact same callback URL structure as Google, GitHub, and Discord OAuth logins, your frontend application can reuse its existing OAuth callback handler for Magic Links without writing any duplicate callback logic!

---

## 5. Dual-Mode Verification Architecture

To provide maximum flexibility and safeguard against enterprise corporate email scanners (antivirus bots that crawl and pre-fetch incoming links), `tc_auth` supports **two verification mechanisms**:

```
                            Email Received by User
                                       │
           ┌───────────────────────────┴───────────────────────────┐
           ▼                                                       ▼
Direct Browser Verification                                SPA Bot-Safe Verification
GET /tc-auth/link/{purpose}                               POST /tc-auth/link/{purpose}
(Direct click in email client)                            (SPA confirmation / button)
           │                                                       │
           ▼                                                       ▼
Backend verifies single-use OTP                           Frontend sends JSON via fetch
Creates session & generates JWTs                          Returns JSON tokens & user
Redirects HTTP 307 to:                                    Persisted in localStorage / cookies
{frontend_url}/oauth/callback                                      │
?access_token=...&refresh_token=...                                ▼
           │                                              User Authenticated!
           ▼
Reuses Existing Frontend OAuth Router!
```

---

## 6. API Endpoints Reference

### 6.1 Requesting a Magic Link

#### `POST /tc-auth/send/email/link/{purpose}` (Dedicated Magic Link Route)
Call this route when the user explicitly clicks **"Send me Magic Link"**.

- **Path Parameter**: `purpose` (`signup` | `login` | `reset` | `verify`)
- **Query Parameter (Optional)**: `?frontend_url=https://app.example.com`
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

#### `POST /tc-auth/send/email/otp/{purpose}` (Enhanced OTP Route)
Call this route for standard email OTP submission.

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

### 6.2 Verifying a Magic Link

#### Method 1: Direct Browser Verification (GET)
```http
GET /tc-auth/link/{purpose}?email={email}&otp={otp}&frontend_url={frontend_url}
```

Triggered when the user clicks the magic link in their email inbox.

| Purpose | Action on Success | HTTP Status & Redirect Destination |
| :--- | :--- | :--- |
| **`login`** | Validates OTP, burns code, creates session, issues tokens. | **HTTP 307 Redirect** to `{frontend_url}/oauth/callback?access_token=...(&refresh_token=...)` |
| **`verify`** | Validates OTP, burns code, sets account status to `"active"`. | **HTTP 307 Redirect** to `{frontend_url}/magic-link/callback?verified=true&email=...` |
| **`reset`** | Validates OTP **without burning it**, keeps OTP valid for password submission. | **HTTP 307 Redirect** to `{frontend_url}/reset-password?email=...&otp=...` |
| **`signup`** | Validates OTP **without burning it**, keeps OTP valid for signup completion. | **HTTP 307 Redirect** to `{frontend_url}/signup?email=...&otp=...&verified=true` |

#### Error Redirect (Expired / Replayed / Invalid):
If the link is expired or already used, the endpoint redirects:
```http
HTTP/1.1 307 Temporary Redirect
Location: {frontend_url}/magic-link/callback?error={url_encoded_error}
```

---

#### Method 2: Programmatic Bot-Safe Verification (POST)
```http
POST /tc-auth/link/{purpose}
Content-Type: application/json
```
For applications requiring protection against enterprise email scanners (which automatically pre-fetch links). Point your email links to a frontend landing page (e.g. `{frontend_url}/confirm-login?email=...&otp=...`) with a "Confirm Sign In" button that triggers this POST endpoint.

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

---

## 7. Sample cURL Commands

### 7.1 Explicit Magic Link Request
```bash
curl -X POST "http://localhost:8000/tc-auth/send/email/link/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane@example.com",
    "frontend_url": "http://localhost:3000"
  }'
```

### 7.2 Programmatic Verification (Bot-Safe)
```bash
curl -X POST "http://localhost:8000/tc-auth/link/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane@example.com",
    "otp": "123456"
  }'
```

---

## 8. Frontend Integration Guide

### 8.1 Reusing the OAuth Callback Page for Magic Link Login
Your existing `/oauth/callback` route handles both OAuth and Magic Links seamlessly:

```tsx
// app/oauth/callback/page.tsx or src/pages/OAuthCallback.tsx
"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function CallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const accessToken = searchParams.get("access_token");
    const refreshToken = searchParams.get("refresh_token");

    if (accessToken) {
      // 1. Store access token
      localStorage.setItem("access_token", accessToken);
      
      // 2. Store refresh token if dual-token mode is active
      if (refreshToken) {
        localStorage.setItem("refresh_token", refreshToken);
      } else {
        localStorage.removeItem("refresh_token");
      }

      // 3. Clean tokens from browser history URL
      window.history.replaceState({}, document.title, window.location.pathname);

      // 4. Redirect to authenticated dashboard
      router.replace("/dashboard");
    }
  }, [searchParams, router]);

  return <p>Signing you in...</p>;
}
```

### 8.2 Email Verification & Error Callback Route
Create a dedicated route at `/magic-link/callback` to display verification status or errors:

```tsx
// app/magic-link/callback/page.tsx
"use client";

import { useSearchParams } from "next/navigation";

export default function MagicLinkCallback() {
  const searchParams = useSearchParams();
  const verified = searchParams.get("verified");
  const email = searchParams.get("email");
  const error = searchParams.get("error");

  if (error) {
    return (
      <div className="card error">
        <h2>Authentication Failed</h2>
        <p>{error}</p>
        <a href="/login">Request New Link</a>
      </div>
    );
  }

  if (verified === "true") {
    return (
      <div className="card success">
        <h2>Email Verified!</h2>
        <p>Your email ({email}) has been successfully verified.</p>
        <a href="/login">Proceed to Sign In</a>
      </div>
    );
  }

  return <p>Verifying, please wait...</p>;
}
```

---

## 9. Python SDK & Backend Usage

```python
from connect import auth

# 1. Send Magic Link directly (when user explicitly requests it)
auth.email.send_magic_link(
    email="jane@example.com",
    purpose="login",
    frontend_url="https://app.example.com",
    expiry=300,
)

# 2. Send OTP with frontend_url (standard OTP flow with magic link button)
auth.email.send_otp(
    email="jane@example.com",
    purpose="login",
    frontend_url="https://app.example.com",
)

# 3. Purpose helpers supporting frontend_url
auth.email.send_login_otp(email="jane@example.com", frontend_url="https://app.example.com")
auth.email.send_verify_email(email="jane@example.com", frontend_url="https://app.example.com")
auth.email.send_reset_otp(email="jane@example.com", frontend_url="https://app.example.com")
auth.email.send_signup_otp(email="jane@example.com", frontend_url="https://app.example.com")

# 4. Programmatic service-level verification
login_data = auth.service.login_magic_link(
    email="jane@example.com",
    otp="123456",
)

verify_result = auth.service.verify_email_magic_link(
    email="jane@example.com",
    otp="123456",
)
```

---

## 10. Security Features & Edge Cases

1. **Replay Attack Prevention**:
   - Single-use OTPs are permanently burned and deleted from the database upon successful verification for `login` and `verify`.
   - Repeated clicks on the same link are immediately rejected with an error redirect.
2. **Non-Destructive Validation for Reset & Signup**:
   - For `reset` and `signup`, `GET /tc-auth/link/{purpose}` validates that the OTP is genuine and unexpired **without deleting it**, allowing the user to safely submit their password on the subsequent form.
3. **Reverse-Proxy Support**:
   - Generates accurate verification URLs behind SSL terminators and reverse proxies using `X-Forwarded-Proto` and `X-Forwarded-Host`.
4. **Adaptive Token Modes**:
   - Fully compatible with both Single-Token Mode (`access_token` only) and Dual-Token Mode (`access_token` + `refresh_token`).
