# Cookie Configuration (`auth.cookie`)

The `auth.cookie` module provides configuration and utilities for toggling **Cookie mode**.

By default, `tc_auth` operates in **localStorage mode** (`cookie_mode = False`), ensuring full backwards compatibility.

---

## 1. Overview

| Feature | Cookie Mode OFF (`cookie_mode=False`) | Cookie Mode ON (`cookie_mode=True`) |
| :--- | :--- | :--- |
| **Default** | **Yes** | No |
| **Token Delivery** | JSON Response Body (`access_token`, `refresh_token`) | `Set-Cookie` Headers + JSON Response Body |
| **OAuth Callbacks** | `?access_token=...&refresh_token=...` query params | `Set-Cookie` Headers **+** query params (Zero frontend breaking changes) |
| **Client Storage** | `localStorage` / Memory | Secure `HttpOnly` Cookies |
| **XSS Protection** | Requires careful frontend sanitation | **High** (JavaScript cannot access `HttpOnly` cookies) |
| **Request Authentication** | `Authorization: Bearer <token>` | Automatic via Browser Cookies or `Authorization: Bearer <token>` |
| **Logout** | Session deleted in DB; frontend removes token | Session deleted in DB **+** Cookies expired automatically |

---

## 2. SDK Usage

### Load Configuration
```python
from connect import auth

config = auth.cookie.load()
# Returns:
# {
#     "cookie_mode": False,
#     "access_cookie_name": "access_token",
#     "refresh_cookie_name": "refresh_token",
#     "path": "/",
#     "domain": None,
#     "secure": False,
#     "httponly": True,
#     "samesite": "lax",
#     "max_age": None,
# }
```

### Enable Cookie Mode
```python
auth.cookie.config(
    cookie_mode=True,
    access_cookie_name="access_token",
    refresh_cookie_name="refresh_token",
    path="/",
    domain=None,
    secure=True,            # Set to True in production (HTTPS)
    httponly=True,          # Prevents client-side scripts from reading tokens
    samesite="lax",         # "lax", "strict", or "none" (if "none", secure must be True)
    max_age=None,           # None = syncs with JWT duration (e.g. 15 min access, 7 day refresh)
)
```

---

## 3. Dashboard API Endpoints

### Load Configuration
- **Method**: `GET`
- **URL**: `/tc-auth/config/load/`
- **Protected**: `superadmin`
- **Response**: Includes the `"cookie"` configuration object along with `email`, `github`, `google`, `discord`, and `jwt`.

### Update Configuration
- **Method**: `POST`
- **URL**: `/tc-auth/config/cookie`
- **Protected**: `superadmin`
- **Payload**:
```json
{
  "cookie_mode": true,
  "access_cookie_name": "access_token",
  "refresh_cookie_name": "refresh_token",
  "path": "/",
  "secure": false,
  "httponly": true,
  "samesite": "lax",
  "max_age": null
}
```

---

## 4. OAuth Integration (Zero Breaking Changes)

When `cookie_mode` is `True`:
1. The OAuth callback endpoints (`/tc-auth/google/callback`, `/tc-auth/github/callback`, `/tc-auth/discord/callback`) set the `access_token` and `refresh_token` cookies on the HTTP `RedirectResponse`.
2. The redirect URL query parameters (`?access_token=...&refresh_token=...`) are **still preserved**.
3. Direct Python SDK calls to `auth.oauth.login(...)` and `auth.service.create_login_response(...)` continue to return the dictionary format without modification.
