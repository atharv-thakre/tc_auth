# Changelog & Updates Summary

This document details all the architectural enhancements, bug fixes, response standardizations, error handling improvements, and documentation updates made to the project.

---

## 1. Architecture & Circular Dependency Prevention

### The `connect.py` + `run.py` Pattern
In modular FastAPI applications, importing an `Auth` instance across multiple router modules can easily trigger circular import errors if the FastAPI `app` and `Auth` instance are initialized in the same file.

- **`connect.py` (Engine & Auth Initialization)**:
  - Initializes database engine and `Auth(engine=engine)`.
  - Exports `auth`, which can be safely imported into route handlers, dependency injectors, background tasks, and service layers.
- **`run.py` (FastAPI App & Route Registration)**:
  - Initializes `FastAPI()` app.
  - Calls `auth.include_routes(app, prefix="/tc-auth")` to mount all authentication, OAuth, dashboard, and account routers as well as middleware and exception handlers.
- **`Auth` Class Updates**:
  - Accepts optional `app` parameter (`Auth(engine, app=None)`).
  - Explicit method `auth.include_routes(app, prefix="/tc-auth")` for flexible mounting.

---

## 2. Standardized Error Handling & Exception Hierarchy

All library exceptions inherit from `AuthError`, guaranteeing structured error responses with HTTP status codes:

- **Exception Hierarchy**:
  - `AuthError` (Base class, returns `status_code` & `message`)
  - `InvalidTokenError` (401)
  - `TokenExpiredError` (401)
  - `AccountNotFoundError` (404)
  - `AccountInactiveError` (403)
  - `DuplicateAccountError` (409)
  - `InvalidCredentialsError` (401)
  - `InvalidOTPError` (400)
  - `OTPExpiredError` (400)
  - `ProviderNotConfiguredError` (500)
  - `PermissionDeniedError` (403)
  - `DatabaseError` (500)
- **FastAPI Exception Handler**:
  - `auth_exception_handler` automatically catches `AuthError` instances and translates them to `JSONResponse(status_code=exc.status_code, content={"detail": exc.message})`.
- **Harden Provider Validation**:
  - Added checks in `tc_auth/oauth/google.py` and `tc_auth/oauth/github.py` to raise `ProviderNotConfiguredError` with clear diagnostics if client credentials are not configured.

---

## 3. Dependency Injection Refactoring

- **Decoupled Helper Dependencies (`tc_auth/dependencies/auth_deps.py`)**:
  - Fixed FastAPI runtime bug where helper dependency methods (`get_current_account`, `get_current_session`, `get_current_payload`) declared default `Depends(get_current)` parameter inside instance methods, which caused FastAPI to treat `self` as a query parameter or fail resolution.
  - Refactored helper methods to independently extract tokens, verify JWT, validate active sessions, and look up accounts directly.
- **Status & Role Guards**:
  - Fixed `tc_auth/dependencies/status_deps.py` to inspect `account.get("status")` accurately.
  - Standardized dependency call syntax across docs (`Depends(auth.deps.get_current)` without trailing `()`).

---

## 4. Response Standardization (Eliminating `null` Returns)

All service methods and HTTP endpoints across the library now return structured dictionary responses. No operations return `None` or `null`.

### Service Layer Standardized Returns
| Service Method | Standardized Return Value |
|---|---|
| `auth.account.delete_by_id(id)` | `{"success": True, "message": "Account deleted successfully", "deleted_id": id}` |
| `auth.account.delete_by_uid(uid)` | `{"success": True, "message": "Account deleted successfully", "deleted_uid": uid}` |
| `auth.account.delete_by_email(email)` | `{"success": True, "message": "Account deleted successfully", "deleted_email": email}` |
| `auth.account.change_password(...)` | `{"success": True, "message": "Password changed successfully"}` |
| `auth.account.set_role(...)` | `{"success": True, "message": "Role updated successfully", "account": {...}}` |
| `auth.account.set_status(...)` | `{"success": True, "message": "Status updated successfully", "account": {...}}` |
| `auth.session.revoke(session_id)` | `{"success": True, "message": "Session revoked successfully", "session_id": session_id}` |
| `auth.session.revoke_all(account_id)` | `{"success": True, "message": "All sessions revoked successfully", "count": N}` |
| `auth.session.cleanup_expired()` | `{"success": True, "message": "Expired sessions cleaned up successfully", "count": N}` |
| `auth.oauth.unlink_oauth(account_id, provider)` | `{"success": True, "message": "OAuth provider unlinked successfully", "provider": provider}` |
| `auth.otp.verify_otp(identifier, otp, purpose)` | `{"success": True, "message": "OTP verified successfully", "identifier": identifier, "purpose": purpose}` |
| `auth.otp.cleanup_expired()` | `{"success": True, "message": "Expired OTPs cleaned up successfully", "count": N}` |
| `auth.jwt.config(...)` | `{"success": True, "message": "JWT configuration updated successfully"}` |
| `auth.email.config(...)` | `{"success": True, "message": "Email service configured successfully"}` |
| `auth.email.send(...)` | `{"success": True, "message": "Email sent successfully"}` |
| `auth.google.config(...)` | `{"success": True, "message": "Google OAuth configured successfully"}` |
| `auth.github.config(...)` | `{"success": True, "message": "GitHub OAuth configured successfully"}` |

### API Endpoint Standardized Returns
| Route | Method | Standardized Response |
|---|---|---|
| `/tc-auth/account/password/change` | `POST` | `{"success": True, "message": "Password changed successfully"}` |
| `/tc-auth/account/sessions/revoke` | `POST` | `{"success": True, "message": "Session revoked successfully", "session_id": sid}` |
| `/tc-auth/account/sessions/revoke-all` | `POST` | `{"success": True, "message": "All sessions revoked successfully", "count": N}` |
| `/tc-auth/account/oauth/unlink` | `POST` | `{"success": True, "message": "OAuth provider unlinked successfully", "provider": provider}` |
| `/tc-auth/dashboard/otp/cleanup` | `POST` | `{"success": True, "message": "Expired OTPs cleaned up successfully", "count": N}` |
| `/tc-auth/dashboard/sessions/revoke` | `POST` | `{"success": True, "message": "Session revoked successfully", "session_id": sid}` |
| `/tc-auth/dashboard/sessions/cleanup` | `POST` | `{"success": True, "message": "Expired sessions cleaned up successfully", "count": N}` |
| `/tc-auth/dashboard/accounts/{id}` | `DELETE` | `{"success": True, "message": "Account deleted successfully", "deleted_id": id}` |
| `/tc-auth/dashboard/accounts/{id}/role` | `PUT` | `{"success": True, "message": "Role updated successfully", "account": {...}}` |
| `/tc-auth/dashboard/accounts/{id}/status` | `PUT` | `{"success": True, "message": "Status updated successfully", "account": {...}}` |
| `/tc-auth/dashboard/config/jwt` | `POST` | `{"success": True, "message": "JWT configuration updated successfully"}` |
| `/tc-auth/dashboard/config/email` | `POST` | `{"success": True, "message": "Email service configured successfully"}` |
| `/tc-auth/dashboard/config/oauth/google` | `POST` | `{"success": True, "message": "Google OAuth configured successfully"}` |
| `/tc-auth/dashboard/config/oauth/github` | `POST` | `{"success": True, "message": "GitHub OAuth configured successfully"}` |

---

## 5. Documentation & Usage Corrections

- **`README.md`**:
  - Rewritten with full architecture documentation, decoupled `connect.py` / `run.py` guides, complete SDK service guides, dependency injection examples, and dashboard configuration guides.
- **`api_docs/`**:
  - Updated all markdown route specs (`account_route.md`, `dash_account.md`, `dash_oauth.md`, `dash_otp.md`, `dash_session.md`, `dashboard_route.md`, `ROUTES_INDEX.md`).
  - Documented updated response schemas, replaced `page_size` query parameter with `limit` (matching actual implementation), and documented authentication & role dependencies.
- **`usage/` (SDK Reference Documentation & Code Snippets)**:
  - Corrected SDK property names (`auth.roles` -> `auth.role`, `auth.github_oauth` -> `auth.github`, `auth.google_oauth` -> `auth.google`).
  - Fixed dependency usage syntax (`Depends(auth.deps.get_current)` without trailing `()`).
  - Updated all imports in code samples to `from connect import auth`.
  - Updated all doc return tables to reflect standardized dictionaries instead of `None`.
  - Created `usage/connect/connect.py` and `usage/connect/connect.md` detailing the modular `connect.py` + `run.py` pattern.
- **`tc_auth/API_RESPONSES.md`**:
  - Dedicated reference detailing all service and route response envelopes.
