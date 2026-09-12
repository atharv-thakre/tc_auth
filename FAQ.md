# CodeSena Auth (`tc_auth`) — Frequently Asked Questions (FAQ) & Architecture Comparison

This document answers common architectural questions and compares **CodeSena Auth (`tc_auth`)** against traditional authentication libraries, managed SaaS auth providers, and custom DIY setups.

---

## 🚀 Why Choose CodeSena Auth? (Key Advantages)

| Dimension | CodeSena Auth (`tc_auth`) | FastAPI-Users | Managed SaaS (Auth0 / Clerk / Supabase) | Custom DIY (Hand-rolled JWT) |
|---|---|---|---|---|
| **Data Ownership & Privacy** | **100% On-Premise / In-DB**: All accounts, credentials, and sessions stay in your own database. | 100% In-DB | External Cloud Vendor: Vendor lock-in, recurring per-user bills, compliance overhead (GDPR / HIPAA). | 100% In-DB |
| **Decoupled Architecture** | **Built-in `connect.py` / `run.py` separation**: Eliminates circular imports across modular routers by design. | Prone to circular imports when injecting user managers across routers. | N/A (Client SDK calls third-party APIs). | High risk of messy global state and circular imports. |
| **Instant Token Revocation** | **Cryptographically Hashed Server Sessions**: Revoking a session in the DB immediately invalidates active JWTs on the next request. | Requires complex custom DB strategy or Redis backend. | Revocation latency depending on token cache. | Pure JWTs cannot be revoked until expiry unless stateful blacklist is built. |
| **Dual-Token Mode + Refresh Rotation** | **Native Built-in**: 15m short-lived access token + rotating 7-day refresh token with automatic fallback. | Complex custom implementation needed. | Supported, but proprietary SDK required. | Very difficult to implement correctly without race conditions. |
| **OAuth & Auto-Linking** | **Native Google, GitHub, Discord**: Verified email auto-linking, multi-provider linking, and lockout prevention guardrails. | Basic OAuth with manual account linking logic. | Supported with heavy configuration. | High complexity to implement state, token exchange, and linking safely. |
| **Email OTP & Magic Links** | **Zero-Dependency Built-in SMTP**: Dual-pathway emails (one-click Magic Link button + 6-digit numeric OTP) with bot-safe verification. | Requires separate plugin / extensions. | Costly per-email or add-on pricing. | Requires building OTP tables, hashing, attempt tracking, and SMTP templates. |
| **Password Policy Engine** | **Built-in Complexity Enforcement**: 6+ chars, uppercase, lowercase, numeric validation. | Basic validator or manual regex. | Built-in. | Must be manually written and maintained across all update endpoints. |
| **FastAPI RBAC & Status Gates** | **Declarative Dependencies**: `auth.role.require("admin")`, `auth.status.require("active")`. | Basic role check dependencies. | Proprietary claims mapping. | Boilerplate dependency code needed for every route. |
| **Standardized Error System** | **Hierarchical `AuthError`**: Zero unhandled generic 500s; clean JSON envelopes with explicit error codes. | Standard FastAPI HTTPExceptions. | Proprietary error formats. | Inconsistent error schemas across team members. |
| **AI / LLM Readiness** | **Complete `llms.txt`, `llms-full.txt`, and explicit schemas**: Optimized for coding LLMs (Cursor, Antigravity, Copilot). | Standard docs only. | Standard docs only. | Undocumented internal logic. |

---

## ❓ Frequently Asked Questions

### 1. How does `tc_auth` prevent circular import errors in FastAPI?
In modular FastAPI applications, feature routers (e.g. `routers/items.py`, `routers/users.py`) need authentication dependencies (`auth.deps.get_current_user`, `auth.role.require("admin")`). If both the FastAPI `app` and database engine are created in a single file (like `main.py`), importing `app` into routers while `main.py` imports routers creates a circular dependency loop.

`tc_auth` solves this with a clean **2-file decoupled pattern**:
- **`connect.py`**: Initializes the SQLAlchemy `engine`, creates `auth = Auth(engine=engine)`, and configures JWT/SMTP/OAuth. Feature routers import `auth` directly from `connect.py`.
- **`run.py`**: Creates the FastAPI `app`, mounts CORS middleware, registers `auth.include_routes(app)`, includes feature routers, and runs Uvicorn.

---

### 2. What makes `tc_auth` sessions more secure than standard JWTs?
Pure JWT authentication is stateless, which means once a JWT is issued, the server cannot invalidate it until it naturally expires (even if a user changes their password, gets banned, or clicks "Log out of all devices").

`tc_auth` implements **Dual-Layer Cryptographic Verification**:
1. When a session is created, a high-entropy 32-byte secret is generated.
2. The database stores only `token_hash = sha256(secret)`.
3. The JWT token embeds the raw secret alongside `aid` (account ID) and `sid` (session ID).
4. On every request, `tc_auth` verifies the JWT signature AND checks that `sha256(secret)` matches the active, unexpired database session.

**Advantages**:
- **Instant Revocation**: Deleting a session row in the database revokes the token instantly.
- **Data Leak Protection**: If your database is ever compromised, the attacker only sees SHA-256 hashes, which cannot be used to forge tokens.

---

### 3. What is the difference between Single-Token Mode and Dual-Token Mode?
- **Single-Token Mode** *(Default)*:
  - Issues a single, long-lived Access Token (e.g. 7 days).
  - Great for prototypes, internal tools, and mobile apps.
- **Dual-Token Mode** *(Enabled via `dual_token_mode=True`)*:
  - Issues a **short-lived Access Token (15 minutes)** for API authentication and a **long-lived Refresh Token (7 days)**.
  - When the access token expires (HTTP 401), the frontend client calls `POST /tc-auth/token/refresh` with the refresh token to receive a fresh access token without interrupting the user.
  - Enhances security by minimizing the exposure window if an access token is intercepted.

---

### 4. How does `tc_auth` protect against OAuth account lockout?
When a user attempts to unlink an OAuth provider using `DELETE /tc-auth/account/oauth/{provider}`, `tc_auth` checks whether:
1. The user has a non-null `password_hash` set, OR
2. The user has at least one other active linked OAuth provider.

If neither condition is met, the unlinking operation is rejected with an `AuthError` (HTTP 400), preventing the user from accidentally locking themselves out of their account.

---

### 5. How do Magic Links protect against enterprise email security scanners?
Many corporate email clients (like Microsoft Outlook / Defender) automatically click and pre-fetch links in incoming emails to check for malware. If a magic link is a simple single-use GET link, the antivirus bot might consume the link before the user opens the email.

`tc_auth` solves this with **Dual-Mode Verification**:
1. **Direct Browser Verification (`GET /tc-auth/link/{purpose}`)**: For standard consumer users. Clicking the email link authenticates the user and redirects to your frontend.
2. **Bot-Safe Programmatic Verification (`POST /tc-auth/link/{purpose}`)**: For enterprise setups. You can direct the email link to a frontend confirmation screen (e.g. `https://app.com/confirm?email=...&otp=...`) with a "Click to Confirm Sign In" button that executes the POST verification.

---

### 6. Can I use `tc_auth` with existing SQLAlchemy database tables?
Yes! `tc_auth` uses standard SQLAlchemy `Base` models (`Account`, `Session`, `OTP`, `OAuthAccount`). You can:
- Use `auth.init()` to create the tables automatically.
- Integrate the models into Alembic migrations.
- Create foreign keys from your domain models (e.g. `Post`, `Order`, `Organization`) referencing `accounts.id`.

---

### 7. How are exceptions and errors formatted?
Every exception in `tc_auth` inherits from `AuthError`. When an error is raised, the built-in exception handler intercepts it and returns a consistent JSON payload:

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
Zero generic 500 tracebacks leak to the client, and all errors map to appropriate HTTP status codes (`400`, `401`, `403`, `404`, `409`, `500`, `502`).
