# tc_auth

`tc_auth` is a production-ready, modular authentication and authorization library designed specifically for **FastAPI** applications with **SQLAlchemy**.

It provides complete services for account management, password and OTP-based signup/login, session lifecycle management, email delivery, OpenID Connect / OAuth integrations (Google & GitHub), JWT token handling, and role/status-based access control dependencies.

---

## Key Features

- **Decoupled Architecture**: Designed to separate database/auth instantiation (`connect.py`) from FastAPI application lifecycle (`run.py`), eliminating circular dependencies across modular applications.
- **Zero Null Responses**: Every API route and service action returns structured, standardized JSON payloads.
- **Hierarchical Error Handling**: All exceptions inherit from `AuthError` with automatic HTTP status code mapping and standardized error formatting.
- **Built-in Session & Token Management**: Dual-layer verification combining cryptographically hashed server-side sessions with signed JWT tokens.
- **FastAPI Dependencies**: Simple dependency injection for current account, session, JWT claims, role authorization, and account status guards.
- **OAuth Providers**: Seamless Google and GitHub OAuth 2.0 / OpenID Connect authorization flows.
- **Email & OTP Service**: SMTP client with built-in HTML templating for signup, login, password reset, and email verification OTPs.
- **Admin & Dashboard APIs**: Pre-configured routes for administrative inspection of accounts, sessions, OTPs, and OAuth links.

---

## Recommended Project Structure (`connect.py` + `run.py`)

In modular FastAPI applications, feature routers often need access to authentication dependencies (`auth.deps`, `auth.role`, `auth.status`) and services. Initializing both `app` and `auth` in a single file often leads to **circular import errors**.

`tc_auth` solves this by decoupling initialization into two files:

```
my_project/
│
├── connect.py            # 1. Database engine, Auth instantiation & service configs
├── run.py                # 2. FastAPI app assembly, middleware & route registration
├── routers/
│   ├── items.py          # Imports `auth` from `connect` safely (no circular imports!)
│   └── users.py
└── ...
```

### 1. `connect.py`
Instantiate the SQLAlchemy engine, create the `Auth` instance, and configure services (JWT, Email, OAuth):

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

# Optional: Configure Google & GitHub OAuth
auth.google.config(
    client_id="YOUR_GOOGLE_CLIENT_ID",
    client_secret="YOUR_GOOGLE_CLIENT_SECRET",
    redirect_uri="https://api.example.com/tc-auth/google/callback",
)

auth.github.config(
    client_id="YOUR_GITHUB_CLIENT_ID",
    client_secret="YOUR_GITHUB_CLIENT_SECRET",
    redirect_uri="https://api.example.com/tc-auth/github/callback",
)
```

### 2. Feature Routers (e.g. `routers/items.py`)
Import `auth` directly from `connect` without touching `app`:

```python
from fastapi import APIRouter, Depends
from connect import auth

router = APIRouter(prefix="/items", tags=["Items"])

# Protected route using auth dependency
@router.get("/")
def get_items(user=Depends(auth.deps.get_current)):
    return {"user_id": user["account"]["id"], "items": []}

# Admin-only route using role dependency
@router.post("/admin-only")
def create_special_item(admin=Depends(auth.role.require("admin"))):
    return {"status": "created by admin", "account": admin}
```

### 3. `run.py`
Assemble the FastAPI app, register `auth` routes, include feature routers, and start Uvicorn:

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
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wire tc_auth routes (prefix defaults to "/tc-auth" and is configurable: auth.include_routes(app, prefix="/tc-auth"))
auth.include_routes(app)

# Include your custom feature routers
app.include_router(items_router)

def run():
    uvicorn.run("run:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    run()
```

---

## Single-File Setup (Quickstart)

For simple scripts or prototypes, you can pass `app` directly to `Auth`:

```python
from fastapi import FastAPI
from sqlalchemy import create_engine
from tc_auth import Auth

app = FastAPI()
engine = create_engine("sqlite:///./test.db")

# Automatically registers exception handlers, session middleware, and routes
auth = Auth(engine=engine, app=app)
```

---

## Core SDK Services & Modules

| Module Attribute | Class / Service | Description |
|---|---|---|
| `auth.account` | `AccountService` | Create, update, super-update, delete, and query accounts |
| `auth.service` | `AuthService` | User signup, credential login, token generation, and password update |
| `auth.session` | `SessionService` | Create, validate, query, destroy, and cleanup active sessions |
| `auth.otp` | `OTPService` | Generate, verify, revoke, query, and cleanup OTP records |
| `auth.get_user` | `GetUserService` | Look up accounts by ID, UID, email, handle, or phone |
| `auth.deps` | `AuthDeps` | FastAPI dependencies (`get_current`, `get_current_account`, etc.) |
| `auth.role` | `RoleDeps` | Role-based access control (`require`, `allow`, `block`) |
| `auth.status` | `StatusDeps` | Account status access control (`require`, `allow`, `block`) |
| `auth.email` | `EmailService` | SMTP email dispatch and OTP email workflows |
| `auth.jwt` | `jwt_handler` | JWT access token encoding, decoding, and verification |
| `auth.google` | `GoogleOAuth` | Google OpenID Connect OAuth authorization and callback |
| `auth.github` | `GitHubOAuth` | GitHub OAuth authorization and callback |
| `auth.dashboard` | `DashboardService` | System counts and administrative statistics |

---

## Database Initialization & Teardown

```python
# Create all database tables
auth.init()

# Drop all database tables (testing / teardown)
auth.destroy()
```

---

## Documentation

- **[API HTTP Route Reference](api_docs/ROUTES_INDEX.md)**: Comprehensive HTTP route endpoint specifications, parameters, and payloads.
- **[Standardized API Responses](tc_auth/API_RESPONSES.md)**: Exact response schemas and route change matrix.
- **[Library SDK Reference (`usage/`)](usage/connect/connect.md)**: In-depth usage guides for each service module, dependency, and OAuth adapter.
- **[Changelog (`changes.md`)](changes.md)**: Full record of recent architecture, error handling, and response standardizations.
