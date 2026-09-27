# CodeSena Auth (`tc_auth`) — Release Catalog

This catalog documents the complete feature set, enhancements, and architectural evolution of `tc-auth` across all official releases from **v1.5.0** to **v1.5.3**.

---

## Release Quick Matrix

| Version | Release Date | Key Themes & Focus Areas | Installation |
| :--- | :--- | :--- | :--- |
| **`v1.5.3`** | **2026-09-27** | **HttpOnly Cookie Mode, Centralized Logging & Real-Time SSE, Multi-Mode OAuth Guides** | `pip install tc-auth==1.5.3` |
| **`v1.5.2`** | **2026-09-12** | **Magic Links, Discord OAuth, Dual-Token Architecture & Token Rotation, Password Policy** | `pip install tc-auth==1.5.2` |
| **`v1.5.1`** | **2026-09-12** | **Dependency Injection Refinements, JWT & Error Handling Improvements, Dependency Lock** | `pip install tc-auth==1.5.1` |
| **`v1.5.0`** | **2026-08-14** | **Initial Release: Decoupled Auth, Password/OTP/JWT, Google/GitHub OAuth, RBAC, Sessions** | `pip install tc-auth==1.5.0` |

---

## [v1.5.3] — 2026-09-27 (Latest Release)

`v1.5.3` introduces full enterprise-grade **HttpOnly Cookie Mode**, **Centralized Logging Subsystem with SSE Streaming**, and a complete **Multi-Mode OAuth Integration Architecture**.

### 🍪 1. HttpOnly Cookie Mode & Zero-Leakage Architecture
- **Zero-Leakage Security Model**:
  - When `cookie_mode = True`, tokens are strictly set via `HttpOnly`, `Secure`, `SameSite` cookies on HTTP responses.
  - JWT strings (`access_token`, `refresh_token`) are **completely removed from the JSON response body** to eliminate Cross-Site Scripting (XSS) extraction risks.
  - Returns safe response metadata (`token_type: "Cookie"` and non-sensitive cookie configuration block) for frontend validation.
- **Configurable Cookie Attributes**:
  - Full runtime control over `access_cookie_name`, `refresh_cookie_name`, `path`, `domain`, `secure`, `httponly`, `samesite` (`lax`, `strict`, `none`), and `max_age`.
  - Enforces `secure=True` when `samesite="none"` to maintain modern browser compliance.
- **OAuth & Magic Link Cookie Integration**:
  - Backend callback redirect automatically attaches `Set-Cookie` headers directly onto the `RedirectResponse`.
- **Automatic Token Invalidation**:
  - Dedicated cookie destruction on `/logout` and `/logout-all`.

### 📊 2. Centralized Structured Logging & Real-Time SSE Streaming
- **Dual-Stream File Architecture**:
  - `logs/tcauth.log`: Structured JSONL log stream capturing all authentication, user, and security lifecycle events with execution durations, client IP, user agent, and contextual metadata.
  - `logs/server.log`: Captures raw server/Uvicorn console output and application terminal logs.
- **Real-Time Server-Sent Events (SSE)**:
  - `GET /log/tcauth/stream` & `GET /log/server/stream`: Live real-time event feeds.
  - Automatically replays the last 10 log records upon connection.
  - 15-second `: ping\n\n` heartbeat keep-alive pings to prevent proxy/load-balancer timeouts.
- **Point-in-Time Snapshots & Log Management**:
  - `POST /log`: Snapshot active log files into timestamped files in `logs/store/`.
  - `POST /log/tcauth/reset` & `POST /log/server/reset`: Truncate active logs to 0 bytes without stopping the process.
  - `DELETE /log/{name}`: Safely prune old snapshot files.
  - Directory traversal protection strictly preventing access outside `logs/`.
- **Automatic Sensitive Data Redaction**:
  - Automatic masking of passwords, Bearer tokens, cookies, and secret keys.
  - Custom user-defined regex redaction patterns via `POST /config/logging`.

### 🌐 3. Multi-Mode OAuth Integration & Clean Base URL Standardization
- **4-Quadrant Integration Matrix**:
  - Complete integration recipes covering all permutations:
    1. Single-Token + Local Storage
    2. Dual-Token + Local Storage
    3. Single-Token + HttpOnly Cookie Mode
    4. Dual-Token + HttpOnly Cookie Mode
- **Universal Callback Component**:
  - Production-ready callback router that auto-detects query parameters, cookie sessions, account linking states, and errors.
- **Relative Base URL Standardization**:
  - Cleaned all documentation examples to use relative paths (`${baseUrl}/...`), eliminating hardcoded prefix duplication.

### 📦 Installation
```bash
pip install tc-auth==1.5.3
```

---

## [v1.5.2] — 2026-09-12

`v1.5.2` added **Magic Link passwordless authentication**, **Discord OAuth provider**, **Dual-Token JWT architecture**, and strict **Password Policy enforcement**.

### 🔗 1. Magic Link Passwordless Authentication
- **SMTP Magic Link Dispatch**:
  - `POST /send/email/link/{purpose}`: Dispatches emails containing one-click authentication buttons and 6-digit backup OTP codes.
  - Supported purposes: `login`, `signup`, `reset`, `verify`.
- **Browser-Based Verification Flow**:
  - `GET /link/{purpose}`: Direct inbox link verification with automatic browser redirect to `{frontend_url}/oauth/callback` or `{frontend_url}/magic-link/callback`.
- **Bot-Safe Intermediate Confirmation**:
  - `POST /link/{purpose}`: Programmatic verification endpoint for intermediate confirmation pages, preventing enterprise antivirus scanners from pre-fetching and burning single-use links.

### 🎮 2. Discord OAuth 2.0 Provider
- Added Discord as a first-class OAuth provider alongside Google and GitHub:
  - `GET /discord/login` & `GET /discord/callback`.
  - Configuration endpoint `POST /config/discord`.
- **Discord Security Guard**:
  - Enforces verified email checks (`verified: True`) to protect existing user accounts against takeover via unverified Discord accounts.

### 🔄 3. Dual-Token JWT Architecture & Token Rotation
- **Configurable Token Lifespans**:
  - Short-lived Access Tokens (e.g. 15 minutes) for API authorization.
  - Long-lived Refresh Tokens (e.g. 7 days) stored server-side.
- **Rotating Refresh Tokens**:
  - `POST /token/refresh`: Exchanges a valid refresh token for a newly minted access token and rotated refresh token.
  - Refresh token reuse and abuse detection.

### 🔒 4. Password Policy & Security Enhancements
- **Complexity Enforcement**:
  - Passwords must be at least 6 characters long and contain at least one uppercase letter, one lowercase letter, and one number (`WeakPasswordError`).
- **OAuth Safe Linking & Lockout Prevention**:
  - `POST /account/oauth/link/{provider}` & `DELETE /account/oauth/{provider}`.
  - Prevents users from unlinking their last login method if no password is set.

### 📦 Installation
```bash
pip install tc-auth==1.5.2
```

---

## [v1.5.1] — 2026-09-12

`v1.5.1` delivered internal stability improvements, refined error hierarchies, and dependency lock updates.

### ⚙️ Enhancements & Bug Fixes
- **Authentication & Dependency Injection**:
  - Improved dependency resolution in `auth.deps.get_current_user` and `auth.deps.get_current_session`.
- **Account & Session Route Handling**:
  - Improved account update validations and session lookup efficiency.
- **JWT Handling & Validation**:
  - Refined token decoding exceptions and payload validation.
- **Error Handling System**:
  - Structured exception hierarchy with standardized JSON response schemas and error codes.
- **Dependency Locking**:
  - Added `requirements-lock.txt` for reproducible production environments.

### 📦 Installation
```bash
pip install tc-auth==1.5.1
```

---

## [v1.5.0] — 2026-08-14

Initial public release of `tc-auth`, a modular authentication and authorization framework built for FastAPI applications using SQLAlchemy.

### 🚀 Core Features
- **Decoupled Architecture**:
  - Clean separation of database engine creation (`connect.py`) and FastAPI route mounting (`run.py`), eliminating circular imports.
- **Multi-Factor & Passwordless Auth**:
  - Traditional email/handle + password authentication with bcrypt hashing.
  - 6-digit numeric email OTP authentication (`signup`, `login`, `reset`, `verify`).
- **OAuth 2.0 / OpenID Connect**:
  - Google OAuth (`/google/login`, `/google/callback`).
  - GitHub OAuth (`/github/login`, `/github/callback`).
- **Session Management**:
  - Server-side database sessions with cryptographic SHA-256 token hashing.
  - Device and IP tracking with single-session logout (`/logout`) and global account logout (`/logout-all`).
- **Role-Based Access Control (RBAC) & Status Guards**:
  - FastAPI dependency injection guards: `auth.role.require("admin")`, `auth.status.require("active")`.
- **Administrative Dashboard & Health Probes**:
  - `GET /config/pulse`: Readiness health check.
  - `GET /config/counts`: Live table entity counters.
  - Runtime service credential loading (`GET /config/load/`).
- **SQLAlchemy Database Integration**:
  - Automated table metadata creation (`auth.init()`) and teardown (`auth.destroy()`).

### 📦 Installation
```bash
pip install tc-auth==1.5.0
```
