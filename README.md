# CodeSena Auth

Production-ready authentication and authorization for FastAPI.

- **Python package**: `tc-auth`
- **Documentation**: https://auth.codesena.me/
- **AI documentation**: https://auth.codesena.me/llms.txt
- **Full AI documentation**: https://auth.codesena.me/llms-full.txt
- **API reference**: https://auth.codesena.me/documents/api/
- **OpenAPI**: https://auth.codesena.me/openapi.json

---

## Table of Contents
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Authentication](#authentication)
- [Authorization / RBAC](#authorization--rbac)
- [OAuth](#oauth)
- [OTP / Magic Links](#otp--magic-links)
- [Sessions](#sessions)
- [REST API](#rest-api)
- [Error Handling](#error-handling)
- [Configuration](#configuration)
- [Architecture & ERD Diagrams (MODELS.md)](MODELS.md)
- [FAQ & Comparison (FAQ.md)](FAQ.md)
- [Documentation](#documentation)

---

## Installation

Install `tc-auth` using pip or your preferred package manager:

```bash
pip install tc-auth
```

Ensure you have your database driver installed (e.g. `psycopg2-binary` for PostgreSQL, `asyncpg`, or `pymysql`):

```bash
pip install psycopg2-binary
```

---

## Quick Start

### Recommended Decoupled Structure (`connect.py` + `run.py`)

To eliminate circular imports across modular routers, decouple database and auth initialization from the FastAPI app lifecycle:

```text
my_project/
├── connect.py            # 1. Database engine, Auth instantiation & service configs
├── run.py                # 2. FastAPI app assembly, middleware & route registration
├── routers/
│   ├── items.py          # Imports `auth` from `connect` safely
│   └── users.py
```

#### 1. `connect.py` (Database Engine & Auth Configuration)
```python
from sqlalchemy import create_engine
from tc_auth import Auth

# Create SQLAlchemy engine
engine = create_engine("postgresql://user:password@localhost:5432/my_db")

# Initialize Auth with database engine
auth = Auth(engine=engine)

# Optional: Configure JWT (built-in defaults available)
auth.jwt.config(
    secret_key="your-super-secret-key",
    algorithm="HS256",
    session_duration_days=7,
    dual_token_mode=True,            # Optional: Enable short-lived access + rotating refresh tokens
    access_token_expire_minutes=15,  # Optional: Access token lifespan in minutes
    refresh_token_expire_days=7,     # Optional: Refresh token lifespan in days
)

# Optional: Configure Email SMTP
auth.email.config(
    host="smtp.example.com",
    port=587,
    username="mailer@example.com",
    password="smtp-password",
    sender="noreply@example.com",
    sender_name="My App",
    use_tls=True,
)

# Optional: Configure Google, GitHub & Discord OAuth
auth.google.config(
    client_id="YOUR_GOOGLE_CLIENT_ID",
    client_secret="YOUR_GOOGLE_CLIENT_SECRET",
    redirect_uri="https://api.example.com/tc-auth/google/callback",
)
```

#### 2. `routers/items.py` (Feature Router using Dependencies)
```python
from fastapi import APIRouter, Depends
from connect import auth

router = APIRouter(prefix="/items", tags=["Items"])

# Protected route using auth dependency
@router.get("/")
def get_items(current_user=Depends(auth.deps.get_current_user)):
    account = current_user["account"]
    return {"user_id": account["id"], "name": account["name"], "items": []}

# Admin-only route using role dependency
@router.post("/admin-only")
def create_special_item(admin=Depends(auth.role.require("admin"))):
    return {"status": "created by admin", "account_id": admin["id"]}
```

#### 3. `run.py` (FastAPI App Mounting & Server Startup)
```python
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from connect import auth
from routers.items import router as items_router

app = FastAPI(title="My Application")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database tables
auth.init()

# Wire tc_auth routes (prefix defaults to "/tc-auth")
auth.include_routes(app, prefix="/tc-auth")

# Include your custom feature routers
app.include_router(items_router)

if __name__ == "__main__":
    uvicorn.run("run:app", host="0.0.0.0", port=8000, reload=True)
```

---

## Architecture

`tc_auth` provides a multi-tier security and session validation engine backed by SQLAlchemy:

```text
[ Incoming API Request with Bearer Token ]
                    │
                    ▼
     1. Verify JWT Signature & Expiry
                    │ (Extracts aid, sid, token secret)
                    ▼
     2. Lookup Session in DB by sid
                    │
                    ▼
     3. Verify SHA-256(token secret) == session.token_hash
                    │
                    ▼
     4. Check session.expires_at > now()
                    │
                    ▼
     5. Lookup Account by aid
                    │
                    ▼
   [ Grant Access & Inject Dependencies ]
```

### Core Database Models
1. **`Account` (`accounts`)**: Primary user model with `id`, `uid` (UUID), `email`, `handle`, `phone`, `password_hash`, `avatar_url`, `role`, `status`, and timestamps.
2. **`Session` (`sessions`)**: Server-side active sessions with `token_hash` (`sha256(secret)`), `ip_address`, `user_agent`, and `expires_at`.
3. **`OTP` (`otps`)**: 6-digit numeric verification codes with `code_hash`, `purpose` (`signup`, `login`, `reset`, `verify`), `attempts`, and `expires_at`.
4. **`OAuthAccount` (`oauth_accounts`)**: Third-party provider links (`google`, `github`, `discord`) bound to `account_id` with cascade deletion.

---

## Authentication

### Password Authentication
- **Signup**: `POST /tc-auth/signup/password` with `{ "name", "email", "password", "handle"? }`
- **Login**: `POST /tc-auth/login/password` with `{ "identifier", "password" }`
- **Password Strength Engine**: Enforces minimum 6 characters with $\ge 1$ uppercase letter, $\ge 1$ lowercase letter, and $\ge 1$ numeric digit.

### Dual-Token Architecture
- **Single-Token Mode** *(Default)*: Returns a long-lived signed JWT access token.
- **Dual-Token Mode** *(Enabled via `dual_token_mode=True`)*: Returns a short-lived **Access Token (15 min)** and a long-lived **Refresh Token (7 days)**.
- **Refresh Token Endpoint**: `POST /tc-auth/token/refresh` with `{ "refresh_token": "..." }`.

---

## Authorization / RBAC

Declarative dependency injection guards for FastAPI routes:

```python
from fastapi import APIRouter, Depends
from connect import auth

router = APIRouter()

# 1. Inject Current User Context (account + session + JWT claims)
@router.get("/me")
def get_me(user=Depends(auth.deps.get_current_user)):
    return user["account"]

# 2. Require Exact Role
@router.delete("/admin/purge")
def admin_purge(admin=Depends(auth.role.require("admin"))):
    return {"status": "purged"}

# 3. Allow Any of Specified Roles
@router.get("/analytics")
def analytics(user=Depends(auth.role.allow("admin", "manager", "auditor"))):
    return {"data": [1, 2, 3]}

# 4. Block Blacklisted Roles
@router.post("/comment")
def post_comment(user=Depends(auth.role.block("banned", "guest"))):
    return {"message": "Comment posted"}

# 5. Enforce Account Status Guards
@router.post("/transfer")
def transfer_funds(account=Depends(auth.status.require("active"))):
    return {"message": "Transfer successful"}
```

---

## OAuth

Native integration for **Google**, **GitHub**, and **Discord** OAuth 2.0 / OpenID Connect:

### Features:
- **Verified Email Auto-Linking**: If a user signs in via OAuth with an email matching an existing account, the provider is automatically linked safely.
- **Authenticated Account Linking**: Logged-in users can link secondary providers via `POST /tc-auth/account/oauth/link/{provider}`.
- **Lockout Prevention Guardrails**: Users cannot unlink their last provider via `DELETE /tc-auth/account/oauth/{provider}` if no password is set, preventing account lockout.

### Configuration in `connect.py`:
```python
auth.google.config(client_id="...", client_secret="...", redirect_uri="https://api.app.com/tc-auth/google/callback")
auth.github.config(client_id="...", client_secret="...", redirect_uri="https://api.app.com/tc-auth/github/callback")
auth.discord.config(client_id="...", client_secret="...", redirect_uri="https://api.app.com/tc-auth/discord/callback")
```

---

## OTP / Magic Links

Dual-pathway authentication inside every email:

1. **One-Click CTA Button ("Click to Proceed")**: Clicking the Magic Link verifies and authenticates the user directly.
2. **Manual 6-Digit OTP Code**: Prominently displayed for users opening email on a separate device.

### Endpoints:
- `POST /tc-auth/send/email/otp/{purpose}`: Dispatches OTP + Magic Link email (`signup`, `login`, `reset`, `verify`).
- `POST /tc-auth/send/email/link/{purpose}`: Dedicated Magic Link request route.
- `GET /tc-auth/link/{purpose}`: Browser click redirect endpoint (HTTP 307 to frontend callback router).
- `POST /tc-auth/link/{purpose}`: Bot-safe headless verification endpoint for SPAs and enterprise email filters.

---

## Sessions

- **Server-Side Session Hashing**: Tokens are hashed with SHA-256 before being stored in the database.
- **Single-Device Logout**: `POST /tc-auth/logout` revokes the current session immediately.
- **Logout Everywhere**: `POST /tc-auth/logout-all` terminates all active sessions across all devices for the user.
- **Session Cleanup**: `DELETE /tc-auth/session/cleanup` (superadmin) purges expired sessions.

---

## REST API

All routes are mounted under `/tc-auth` by default:

| Method | Endpoint | Description | Auth Required |
|---|---|---|:---:|
| `POST` | `/tc-auth/signup/password` | Register with password | Public |
| `POST` | `/tc-auth/signup/otp` | Register and verify OTP simultaneously | Public |
| `POST` | `/tc-auth/login/password` | Login with email/handle/phone & password | Public |
| `POST` | `/tc-auth/login/otp` | Passwordless login with email OTP | Public |
| `POST` | `/tc-auth/forgot/password` | Reset password using verified OTP | Public |
| `POST` | `/tc-auth/token/refresh` | Exchange refresh token for fresh access token | Public |
| `POST` | `/tc-auth/send/email/otp/{purpose}` | Send email OTP & magic link | Public |
| `POST` | `/tc-auth/send/email/link/{purpose}` | Send dedicated magic link email | Public |
| `GET` | `/tc-auth/link/{purpose}` | Browser magic link redirect handler | Public |
| `POST` | `/tc-auth/link/{purpose}` | Programmatic bot-safe magic link verification | Public |
| `GET` | `/tc-auth/me` | Fetch user profile, session, and JWT claims | `Bearer` |
| `PATCH` | `/tc-auth/me` | Update user profile fields | `Bearer` |
| `PUT` | `/tc-auth/update/password` | Update current user's password | `Bearer` |
| `POST` | `/tc-auth/logout` | Revoke current session | `Bearer` |
| `POST` | `/tc-auth/logout-all` | Revoke all sessions across all devices | `Bearer` |
| `GET` | `/tc-auth/account/oauth/links` | List connected OAuth providers | `Bearer` |
| `POST` | `/tc-auth/account/oauth/link/{provider}` | Link secondary OAuth provider | `Bearer` |
| `DELETE` | `/tc-auth/account/oauth/{provider}` | Safely unlink OAuth provider | `Bearer` |
| `GET` | `/tc-auth/{provider}/login` | Initiate OAuth login flow | Public |
| `GET` | `/tc-auth/{provider}/callback` | Provider OAuth redirect callback | Public |
| `GET` | `/tc-auth/config/pulse` | Public system health check | Public |
| `GET` | `/tc-auth/config/load/` | Inspect active service configuration | `superadmin` |
| `GET` | `/tc-auth/config/counts` | Return total counts across all tables | `superadmin` |

---

## Error Handling

All domain exceptions inherit from `AuthError` with automatic HTTP status code mapping and standardized JSON responses:

```json
{
  "status": false,
  "error": {
    "code": "InvalidCredentialsError",
    "message": "Invalid credentials",
    "details": null
  }
}
```

### Exception Status Code Mapping:
- **`400 Bad Request`**: `AuthError`, `WeakPasswordError`, `InvalidFieldError`, `InvalidEmailPurposeError`, `InvalidConfigError`, `OAuthCallbackError`.
- **`401 Unauthorized`**: `InvalidCredentialsError`, `InvalidTokenError`, `OTPInvalidError`, `OTPExpiredError`.
- **`403 Forbidden`**: `PermissionDeniedError` (role failure), `AccountStatusError` (status failure).
- **`404 Not Found`**: `UserNotFoundError`, `SessionNotFoundError`, `OTPNotFoundError`, `OAuthLinkNotFoundError`.
- **`409 Conflict`**: `EmailAlreadyExistsError`, `HandleAlreadyExistsError`, `PhoneAlreadyExistsError`, `OAuthAlreadyLinkedError`.
- **`500 Internal Error`**: `DatabaseError`, `EmailNotConfiguredError`, `OAuthNotConfiguredError`.
- **`502 Bad Gateway`**: `EmailSendError`.

---

## Configuration

Configure services live or dynamically on the `auth` instance:

```python
# JWT Configuration
auth.jwt.config(
    secret_key="your-jwt-secret",
    algorithm="HS256",               # "HS256", "HS384", "HS512"
    session_duration_days=7,
    dual_token_mode=True,
    access_token_expire_minutes=15,
    refresh_token_expire_days=7,
)

# SMTP Email Configuration
auth.email.config(
    host="smtp.resend.com",
    port=587,
    username="resend",
    password="re_your_api_key",
    sender="auth@yourdomain.com",
    sender_name="Your App Security",
    use_tls=True,
)
```

---

## Documentation

- **[Full Documentation Hub](https://auth.codesena.me/)**: Official documentation portal.
- **[AI Documentation Manifest (`llms.txt`)](https://auth.codesena.me/llms.txt)**: Standardized LLM manifest for AI agents.
- **[Consolidated AI Reference (`llms-full.txt`)](https://auth.codesena.me/llms-full.txt)**: High-density reference file for LLM system prompts.
- **[HTTP REST API Reference](https://auth.codesena.me/documents/api/)** (Local: [`api_docs/ROUTES_INDEX.md`](api_docs/ROUTES_INDEX.md)): Detailed endpoint payloads and schemas.
- **[Python SDK Reference](https://auth.codesena.me/documents/sdk/)** (Local: [`usage/connect/connect.md`](usage/connect/connect.md)): In-depth SDK service documentation.
- **[Architecture, Models & ERD Diagrams](MODELS.md)**: Visual Mermaid ER diagrams, SQL table schemas, and relational flowcharts.
- **[Frequently Asked Questions & Comparison](FAQ.md)**: Deep architectural comparison against FastAPI-Users, Auth0, and Supabase.
- **[Frontend Token Guide](token_usage_guide.md)**: Production Axios client with automatic 401 token refresh queue.
- **[Changelog](changes.md)**: Detailed version history and architectural changes.
