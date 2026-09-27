# OAuth Frontend Integration Guide

This guide covers integrating `tc_auth` OAuth (Google, GitHub, Discord) with any frontend application. It contains modular, labeled sections designed so you can easily reference or extract the specific combination of **Token Mode** (Single vs Dual) and **Storage / Transport Mode** (Local Storage vs HttpOnly Cookie) matching your backend configuration.

> [!NOTE]
> **Base URL Note**: In all code examples below, `baseUrl` represents the root endpoint where the auth module is mounted (e.g. `https://api.example.com/tc-auth` by default, or your custom prefix configured via `auth.include_routes(app, prefix=...)`).

---

## Table of Contents

1. [Architecture & Mode Matrix](#1-architecture--mode-matrix)
2. [Initiating OAuth Login / Signup](#2-initiating-oauth-login--signup)
3. [Account Linking & Unlinking (Authenticated Flow)](#3-account-linking--unlinking-authenticated-flow)
4. [Profile & Email Overwrite Policy](#4-profile--email-overwrite-policy)
5. [Mode-Specific Callback Implementations](#5-mode-specific-callback-implementations)
   - [[SECTION 1] Single-Token Mode + Local Storage (Auth Header)](#section-1-single-token-mode--local-storage-auth-header)
   - [[SECTION 2] Dual-Token Mode + Local Storage (Auth Header)](#section-2-dual-token-mode--local-storage-auth-header)
   - [[SECTION 3] Single-Token Mode + HttpOnly Cookie Mode](#section-3-single-token-mode--httponly-cookie-mode)
   - [[SECTION 4] Dual-Token Mode + HttpOnly Cookie Mode](#section-4-dual-token-mode--httponly-cookie-mode)
   - [[SECTION 5] Universal Multi-Mode Callback Router](#section-5-universal-multi-mode-callback-router)
6. [Authenticated API Requests by Mode](#6-authenticated-api-requests-by-mode)
7. [Security & Troubleshooting Checklist](#7-security--troubleshooting-checklist)

---

## 1. Architecture & Mode Matrix

`tc_auth` supports two token issuance strategies and two storage/transport strategies, creating 4 distinct operational modes:

| Mode ID | Token Strategy | Transport / Storage | Backend Callback Behavior | Frontend Token Management |
| :--- | :--- | :--- | :--- | :--- |
| **Mode 1** | **Single-Token** | **Local Storage / Header** | Redirects with `?access_token=...` | Read from query params, store in `localStorage`, send `Authorization: Bearer <token>` |
| **Mode 2** | **Dual-Token** | **Local Storage / Header** | Redirects with `?access_token=...&refresh_token=...` | Read both from query params, store in `localStorage`, manual silent refresh via `POST /refresh` |
| **Mode 3** | **Single-Token** | **HttpOnly Cookies** | Sets `access_token` cookie + redirects | Zero JS token access. Send requests with `credentials: 'include'` |
| **Mode 4** | **Dual-Token** | **HttpOnly Cookies** | Sets `access_token` & `refresh_token` cookies + redirects | Zero JS token access. Automatic cookie rotation on `POST /refresh` with `credentials: 'include'` |

### OAuth Sequence Flow

```
1. Frontend -> GET {baseUrl}/{provider}/login?frontend_url=https://app.com
2. Backend  -> Stores frontend_url in session -> Redirects (307) to Provider Auth Screen
3. User     -> Consents on Provider (Google / GitHub / Discord)
4. Provider -> Redirects back to Backend Callback: GET {baseUrl}/{provider}/callback?code=...
5. Backend  -> Exchanges code -> Finds or creates account -> Creates session & JWT(s)
            -> Sets HttpOnly cookies (if Cookie Mode is enabled)
            -> Redirects (307) to: {frontend_url}/oauth/callback?[tokens or linking params]
6. Frontend -> /oauth/callback router processes tokens/cookies -> Redirects to /dashboard
```

---

## 2. Initiating OAuth Login / Signup

To trigger OAuth login or signup, navigate the user's browser window to the provider login route, passing `frontend_url` as a query parameter.

### Endpoints (Relative to `baseUrl`):
- Google: `GET /google/login?frontend_url={frontendUrl}`
- GitHub: `GET /github/login?frontend_url={frontendUrl}`
- Discord: `GET /discord/login?frontend_url={frontendUrl}`

### Frontend Implementation:

```js
const baseUrl = process.env.NEXT_PUBLIC_AUTH_API_URL || "https://api.example.com/tc-auth";
const FRONTEND_URL = window.location.origin; // e.g. "https://app.example.com"

function loginWithOAuth(provider) {
  // provider: "google" | "github" | "discord"
  const targetUrl = `${baseUrl}/${provider}/login?frontend_url=${encodeURIComponent(FRONTEND_URL)}`;
  window.location.href = targetUrl;
}
```

```jsx
// React Component Example
const baseUrl = process.env.NEXT_PUBLIC_AUTH_API_URL || "https://api.example.com/tc-auth";

export function OAuthLoginButtons() {
  const handleLogin = (provider) => {
    window.location.href = `${baseUrl}/${provider}/login?frontend_url=${encodeURIComponent(window.location.origin)}`;
  };

  return (
    <div className="oauth-buttons">
      <button onClick={() => handleLogin("google")}>Continue with Google</button>
      <button onClick={() => handleLogin("github")}>Continue with GitHub</button>
      <button onClick={() => handleLogin("discord")}>Continue with Discord</button>
    </div>
  );
}
```

---

## 3. Account Linking & Unlinking (Authenticated Flow)

Authenticated users can link additional social accounts to their existing profile or unlink existing providers.

### 3.1 Initiating OAuth Linking (Browser Redirect)

Send a POST request with the user's active session to start the linking flow:

```js
const baseUrl = process.env.NEXT_PUBLIC_AUTH_API_URL || "https://api.example.com/tc-auth";

async function linkProvider(provider, accessToken = null) {
  // For Local Storage Mode, pass accessToken in Authorization header.
  // For Cookie Mode, omit headers and pass credentials: 'include'.
  const headers = { "Content-Type": "application/json" };
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const res = await fetch(`${baseUrl}/account/oauth/link/${provider}`, {
    method: "POST",
    headers,
    credentials: "include",
    body: JSON.stringify({ frontend_url: window.location.origin }),
  });

  const data = await res.json();
  if (data.redirect_url) {
    window.location.href = data.redirect_url;
  }
}
```

### 3.2 Fetching Connected Providers

```js
const baseUrl = process.env.NEXT_PUBLIC_AUTH_API_URL || "https://api.example.com/tc-auth";

async function getConnectedProviders(accessToken = null) {
  const headers = accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
  const res = await fetch(`${baseUrl}/account/oauth/links`, {
    headers,
    credentials: "include",
  });
  return await res.json(); // Array of { id, provider, provider_user_id, created_at }
}
```

### 3.3 Unlinking a Provider

```js
const baseUrl = process.env.NEXT_PUBLIC_AUTH_API_URL || "https://api.example.com/tc-auth";

async function unlinkProvider(provider, accessToken = null) {
  const headers = accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
  const res = await fetch(`${baseUrl}/account/oauth/${provider}`, {
    method: "DELETE",
    headers,
    credentials: "include",
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || error.message || "Failed to unlink provider");
  }

  return await res.json();
}
```

> [!NOTE]
> **Lockout Protection**: The backend rejects unlinking with `HTTP 400` if unlinking would leave the account without any authentication method (no password and no other linked OAuth providers).

---

## 4. Profile & Email Overwrite Policy

When an OAuth account is authenticated or linked:

> [!IMPORTANT]
> **Field Population & Overwrite Rules**:
> - **Empty Fields Rule**: If an account has empty or null fields (`name`, `email`, `avatar_url`), **all 3 providers (Google, GitHub, Discord) are permitted to populate and set all empty data**.
> - **Email Overwrite Rule**: If an account already exists with an email:
>   - **Google**: **Overwrites** existing non-empty email with Google's verified email.
>   - **GitHub**: **Never overwrites** existing non-empty email (preserves current email).
>   - **Discord**: **Never overwrites** existing non-empty email (preserves current email).
> - **Existing Name & Avatar**: Preserved for all providers; existing non-empty names/avatars are never overwritten.

| Provider | Overwrites Existing Non-Empty Email? | Overwrites Existing Name / Avatar? | Populates Empty Fields (`null` / `""`)? | Auto-Links by Verified Email? |
| :--- | :--- | :--- | :--- | :--- |
| **Google** | **YES** | **NO** (preserved) | **YES** | **YES** (verified) |
| **GitHub** | **NO** (preserved) | **NO** (preserved) | **YES** | **YES** (verified primary) |
| **Discord** | **NO** (preserved) | **NO** (preserved) | **YES** | **YES** (verified only; unverified rejected) |

---

## 5. Mode-Specific Callback Implementations

The sections below provide complete, self-contained callback routing code for each combination of settings.

---

### [SECTION 1] Single-Token Mode + Local Storage (Auth Header)

#### Backend Redirect Format:
```
{frontend_url}/oauth/callback?access_token=eyJhbGci...
```
*(Account linking redirects with `?linked=true&provider=google` or `?linked=false&provider=google&error=...`)*

#### Frontend Responsibilities:
1. Extract `access_token` from URL parameters.
2. Save `access_token` to `localStorage`.
3. Clean sensitive query parameters from browser history via `window.history.replaceState`.
4. Redirect user to `/dashboard`.

#### Vanilla JavaScript / HTML (`oauth/callback.html`):
```html
<script>
  (function handleSingleTokenLocalStorage() {
    const params = new URLSearchParams(window.location.search);
    const accessToken = params.get("access_token");
    const linked = params.get("linked");
    const provider = params.get("provider");
    const error = params.get("error");

    if (accessToken) {
      localStorage.setItem("access_token", accessToken);
      window.history.replaceState({}, document.title, window.location.pathname);
      window.location.href = "/dashboard";
      return;
    }

    if (linked === "true") {
      alert(`Successfully linked ${provider}!`);
      window.location.href = "/settings/security";
      return;
    }

    if (linked === "false" || error) {
      alert(`OAuth Error: ${error || "Failed to authenticate"}`);
      window.location.href = "/login";
      return;
    }

    window.location.href = "/login";
  })();
</script>
```

#### React Router Component (`OAuthCallbackSingleLocalStorage.jsx`):
```jsx
import React, { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

export default function OAuthCallbackSingleLocalStorage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const accessToken = params.get("access_token");
    const linked = params.get("linked");
    const provider = params.get("provider");
    const error = params.get("error");

    if (accessToken) {
      localStorage.setItem("access_token", accessToken);
      window.history.replaceState({}, document.title, window.location.pathname);
      navigate("/dashboard", { replace: true });
      return;
    }

    if (linked === "true") {
      navigate(`/settings/security?linked=true&provider=${provider}`, { replace: true });
      return;
    }

    if (error || linked === "false") {
      navigate(`/login?error=${encodeURIComponent(error || "OAuth failed")}`, { replace: true });
      return;
    }

    navigate("/login", { replace: true });
  }, [params, navigate]);

  return <div>Logging you in...</div>;
}
```

#### Next.js App Router (`app/oauth/callback/page.tsx`):
```tsx
"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function OAuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const accessToken = searchParams.get("access_token");
    const linked = searchParams.get("linked");
    const provider = searchParams.get("provider");
    const error = searchParams.get("error");

    if (accessToken) {
      localStorage.setItem("access_token", accessToken);
      router.replace("/dashboard");
      return;
    }

    if (linked === "true") {
      router.replace(`/settings/security?linked=${provider}`);
      return;
    }

    if (error || linked === "false") {
      router.replace(`/login?error=${encodeURIComponent(error || "Authentication failed")}`);
      return;
    }

    router.replace("/login");
  }, [searchParams, router]);

  return <div>Authenticating...</div>;
}
```

---

### [SECTION 2] Dual-Token Mode + Local Storage (Auth Header)

#### Backend Redirect Format:
```
{frontend_url}/oauth/callback?access_token=eyJhbGci...&refresh_token=eyJhbGci...
```

#### Frontend Responsibilities:
1. Extract both `access_token` and `refresh_token` from URL parameters.
2. Store both tokens in `localStorage`.
3. Clean URL query parameters.
4. Implement automatic token refresh when `access_token` expires using `POST /refresh`.

#### React Router Component (`OAuthCallbackDualLocalStorage.jsx`):
```jsx
import React, { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

export default function OAuthCallbackDualLocalStorage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");
    const linked = params.get("linked");
    const provider = params.get("provider");
    const error = params.get("error");

    if (accessToken) {
      localStorage.setItem("access_token", accessToken);
      if (refreshToken) {
        localStorage.setItem("refresh_token", refreshToken);
      }

      window.history.replaceState({}, document.title, window.location.pathname);
      navigate("/dashboard", { replace: true });
      return;
    }

    if (linked === "true") {
      navigate(`/settings/security?linked=true&provider=${provider}`, { replace: true });
      return;
    }

    if (error || linked === "false") {
      navigate(`/login?error=${encodeURIComponent(error || "OAuth failed")}`, { replace: true });
      return;
    }

    navigate("/login", { replace: true });
  }, [params, navigate]);

  return <div>Authenticating (Dual-Token)...</div>;
}
```

#### Axios Client with Auto-Refresh & Request Queueing (`apiClientDualLocalStorage.js`):
```js
import axios from "axios";

const baseUrl = process.env.NEXT_PUBLIC_AUTH_API_URL || "https://api.example.com/tc-auth";

const apiClient = axios.create({
  baseURL: baseUrl,
});

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem("refresh_token");
      if (!refreshToken) {
        localStorage.removeItem("access_token");
        window.location.href = "/login";
        return Promise.reject(error);
      }

      try {
        const res = await axios.post(`${baseUrl}/refresh`, {
          refresh_token: refreshToken,
        });

        const newAccessToken = res.data.access_token;
        const newRefreshToken = res.data.refresh_token;

        localStorage.setItem("access_token", newAccessToken);
        if (newRefreshToken) {
          localStorage.setItem("refresh_token", newRefreshToken);
        }

        processQueue(null, newAccessToken);
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return apiClient(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/login";
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
```

---

### [SECTION 3] Single-Token Mode + HttpOnly Cookie Mode

#### Backend Behavior:
- Sets `access_token` cookie (`HttpOnly; SameSite=Lax; Secure`).
- Redirects to `{frontend_url}/oauth/callback` (or with query params for linking).

#### Frontend Responsibilities:
1. Zero token extraction or storage needed in JavaScript (tokens are protected inside `HttpOnly` cookies).
2. Clean any remaining query params.
3. Verify session via `GET /me` or redirect directly to `/dashboard`.
4. Send all API requests with `credentials: 'include'` (or `withCredentials: true`).

#### React Router Component (`OAuthCallbackSingleCookie.jsx`):
```jsx
import React, { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

const baseUrl = process.env.NEXT_PUBLIC_AUTH_API_URL || "https://api.example.com/tc-auth";

export default function OAuthCallbackSingleCookie() {
  const [params] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const linked = params.get("linked");
    const provider = params.get("provider");
    const error = params.get("error");

    if (error || linked === "false") {
      navigate(`/login?error=${encodeURIComponent(error || "OAuth failed")}`, { replace: true });
      return;
    }

    if (linked === "true") {
      navigate(`/settings/security?linked=true&provider=${provider}`, { replace: true });
      return;
    }

    // Cookie is already set by the browser during redirect.
    // Verify session or navigate straight to dashboard:
    fetch(`${baseUrl}/me`, { credentials: "include" })
      .then((res) => {
        if (res.ok) {
          navigate("/dashboard", { replace: true });
        } else {
          navigate("/login?error=session_verification_failed", { replace: true });
        }
      })
      .catch(() => navigate("/login", { replace: true }));
  }, [params, navigate]);

  return <div>Finalizing secure session...</div>;
}
```

---

### [SECTION 4] Dual-Token Mode + HttpOnly Cookie Mode

#### Backend Behavior:
- Sets both `access_token` and `refresh_token` cookies (`HttpOnly; SameSite=Lax; Secure`).
- Redirects to `{frontend_url}/oauth/callback`.

#### Frontend Responsibilities:
1. No token extraction or storage in JavaScript.
2. All API calls pass `credentials: 'include'`.
3. When `access_token` expires (`HTTP 401`), call `POST /refresh` with `credentials: 'include'`. The backend reads the `refresh_token` cookie, rotates the cookies, and returns success.

#### React Router Component (`OAuthCallbackDualCookie.jsx`):
```jsx
import React, { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

export default function OAuthCallbackDualCookie() {
  const [params] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const linked = params.get("linked");
    const provider = params.get("provider");
    const error = params.get("error");

    if (error || linked === "false") {
      navigate(`/login?error=${encodeURIComponent(error || "OAuth failed")}`, { replace: true });
      return;
    }

    if (linked === "true") {
      navigate(`/settings/security?linked=true&provider=${provider}`, { replace: true });
      return;
    }

    // Cookies are stored in the browser. Navigate to dashboard.
    navigate("/dashboard", { replace: true });
  }, [params, navigate]);

  return <div>Finalizing secure dual-token session...</div>;
}
```

#### Axios Client with Cookie Auto-Refresh (`apiClientDualCookie.js`):
```js
import axios from "axios";

const baseUrl = process.env.NEXT_PUBLIC_AUTH_API_URL || "https://api.example.com/tc-auth";

const apiClient = axios.create({
  baseURL: baseUrl,
  withCredentials: true, // Crucial: sends and receives HttpOnly cookies
});

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve();
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Avoid infinite loop if refresh endpoint itself returns 401
    if (originalRequest.url?.includes("/refresh")) {
      window.location.href = "/login";
      return Promise.reject(error);
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(() => apiClient(originalRequest))
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Backend reads the HttpOnly refresh_token cookie and sets new cookies
        await apiClient.post("/refresh", {});
        processQueue(null);
        return apiClient(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr);
        window.location.href = "/login";
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
```

---

### [SECTION 5] Universal Multi-Mode Callback Router

This universal component dynamically supports **all 4 modes** and account linking scenarios. It inspects URL parameters, safely stores tokens if present (for Header/Local Storage mode), verifies cookie sessions (for Cookie mode), handles linking statuses, cleans the browser URL history, and routes cleanly to destination pages.

```jsx
import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

const baseUrl = process.env.NEXT_PUBLIC_AUTH_API_URL || "https://api.example.com/tc-auth";

export default function UniversalOAuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [statusMessage, setStatusMessage] = useState("Processing authentication...");

  useEffect(() => {
    const accessToken = searchParams.get("access_token");
    const refreshToken = searchParams.get("refresh_token");
    const linked = searchParams.get("linked");
    const provider = searchParams.get("provider");
    const error = searchParams.get("error");

    // Clean sensitive query parameters from history immediately
    if (window.location.search) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    // 1. Handle OAuth Error
    if (error || linked === "false") {
      setStatusMessage(`Error: ${error || "Authentication failed"}`);
      setTimeout(() => {
        navigate(`/login?error=${encodeURIComponent(error || "OAuth failed")}`, { replace: true });
      }, 1500);
      return;
    }

    // 2. Handle Account Linking Success
    if (linked === "true") {
      setStatusMessage(`Successfully linked ${provider || "provider"}!`);
      setTimeout(() => {
        navigate(`/settings/security?linked=true&provider=${provider}`, { replace: true });
      }, 1000);
      return;
    }

    // 3. Handle Local Storage Transport (Single or Dual Token)
    if (accessToken) {
      localStorage.setItem("access_token", accessToken);
      if (refreshToken) {
        localStorage.setItem("refresh_token", refreshToken);
      }
      navigate("/dashboard", { replace: true });
      return;
    }

    // 4. Handle Cookie Transport (Verify session via /me with credentials)
    fetch(`${baseUrl}/me`, { credentials: "include" })
      .then((res) => {
        if (res.ok) {
          navigate("/dashboard", { replace: true });
        } else {
          navigate("/login?error=no_session_found", { replace: true });
        }
      })
      .catch(() => {
        navigate("/login?error=network_error", { replace: true });
      });
  }, [searchParams, navigate]);

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100vh" }}>
      <h2>Authenticating</h2>
      <p>{statusMessage}</p>
    </div>
  );
}
```

---

## 6. Authenticated API Requests by Mode

### 6.1 Local Storage / Authorization Header Mode
Pass the `Authorization: Bearer <access_token>` header on every request:

```js
const baseUrl = process.env.NEXT_PUBLIC_AUTH_API_URL || "https://api.example.com/tc-auth";

async function fetchUserProfile() {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${baseUrl}/me`, {
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });
  return await res.json();
}
```

### 6.2 HttpOnly Cookie Mode
Pass `credentials: "include"` (no manual `Authorization` header required):

```js
const baseUrl = process.env.NEXT_PUBLIC_AUTH_API_URL || "https://api.example.com/tc-auth";

async function fetchUserProfile() {
  const res = await fetch(`${baseUrl}/me`, {
    method: "GET",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  });
  return await res.json();
}
```

---

## 7. Security & Troubleshooting Checklist

### 1. URL Query Parameter Sanitization
Always remove tokens from `window.location.search` immediately using `window.history.replaceState` or client-side navigation (`replace: true`). This prevents tokens from remaining in browser history or leaking via `Referer` headers to external resources.

### 2. CORS & Cookie Configuration
When running the frontend and backend on different origins (e.g. `https://app.example.com` and `https://api.example.com`):
- Backend CORS must set `allow_origins=["https://app.example.com"]` (Wildcard `*` cannot be used with credentials).
- Backend CORS must set `allow_credentials=True`.
- If cookies are cross-site, configure `samesite="none"` and `secure=True` on backend cookies.

### 3. Session State in OAuth Redirects
The OAuth redirect flow requires Starlette `SessionMiddleware` to retain state (such as `frontend_url` and `link_account_id`). Ensure the browser does not block cookies during the provider redirect chain.

### 4. Common Error Codes:
- `OAuthNotConfiguredError (500)`: Missing provider credentials (`client_id`, `client_secret`, or `redirect_uri`). Configure via `POST /config/{provider}`.
- `OAuthCallbackError (400)`: Invalid or expired authorization code from the provider, or user cancelled consent.
- `OAuthAlreadyLinkedError (409)`: The OAuth provider account is already linked to another user profile.
