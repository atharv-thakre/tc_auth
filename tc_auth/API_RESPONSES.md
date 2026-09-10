# API Responses & Standardization Documentation

This document specifies the exact return formats and data structures for all service methods and FastAPI routes in the `tc_auth` module.

---

## 1. Standardization Principles

1. **No Null Responses**: No route or service function returns `null` / `None`.
2. **Preservation of Existing Data Shapes**:
   - Authentication tokens, account objects, session objects, and list query results retain their established field schemas.
3. **Standardized Action Responses**:
   - All deletion, revocation, destruction, cleanup, password updates, and configuration actions return a consistent JSON response:
     ```json
     {
       "success": true,
       "message": "<Description of action performed>",
       "count": 1 // (included on batch / collection modification operations)
     }
     ```

---

## 2. Standardized Response Categories

### A. Authentication & Session Creation
Returned by signup, login, and forgot password endpoints.
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "account": {
    "id": 1,
    "uid": "2d7b5f8e-8d8a-4cc4-9c3d-2f2c6c4d2e28",
    "name": "Jane Doe",
    "handle": "jane",
    "email": "jane@example.com",
    "phone": "+15555550100",
    "avatar_url": "https://example.com/avatar.png",
    "role": "user",
    "status": "active",
    "created_at": "2026-08-07T12:00:00",
    "updated_at": "2026-08-07T12:00:00"
  }
}
```

### B. Account Record (Single)
Returned by `GET /tc-auth/me` (wrapped with session & token payload), `POST /tc-auth/account/`, `PATCH /tc-auth/me`, `PATCH /tc-auth/account/`.
```json
{
  "id": 1,
  "uid": "2d7b5f8e-8d8a-4cc4-9c3d-2f2c6c4d2e28",
  "name": "Jane Doe",
  "handle": "jane",
  "email": "jane@example.com",
  "phone": "+15555550100",
  "avatar_url": "https://example.com/avatar.png",
  "role": "user",
  "status": "active",
  "created_at": "2026-08-07T12:00:00",
  "updated_at": "2026-08-07T12:00:00"
}
```

### C. Current User Profile (`GET /tc-auth/me`)
```json
{
  "account": {
    "id": 1,
    "uid": "2d7b5f8e-8d8a-4cc4-9c3d-2f2c6c4d2e28",
    "name": "Jane Doe",
    "handle": "jane",
    "email": "jane@example.com",
    "phone": null,
    "avatar_url": null,
    "role": "user",
    "status": "active",
    "created_at": "2026-08-07T12:00:00",
    "updated_at": "2026-08-07T12:00:00"
  },
  "session": {
    "id": 9,
    "account_id": 1,
    "token_hash": "...",
    "ip_address": "203.0.113.10",
    "user_agent": "Mozilla/5.0",
    "expires_at": "2026-08-08T12:00:00",
    "created_at": "2026-08-07T12:00:00"
  },
  "payload": {
    "aid": 1,
    "sid": 9,
    "token": "..."
  }
}
```

### D. OTP Dispatch Response
Returned by `POST /tc-auth/send/email/otp/{purpose}`.
```json
{
  "expires_at": 1735689600
}
```

### E. OTP Direct Creation (Admin)
Returned by `POST /tc-auth/otp/`.
```json
{
  "otp": "123456",
  "expires_at": 1735689600
}
```

### F. OAuth Link Record
Returned by `POST /tc-auth/oauth/`.
```json
{
  "id": 1,
  "account_id": 1,
  "provider": "google",
  "provider_user_id": "123456789",
  "created_at": "2026-08-07T12:00:00"
}
```

### G. Paginated / Filtered Query Lists
Returned by all `GET /` and `GET /query` endpoints across accounts, sessions, otps, and oauth links.
```json
[
  { /* entity dict */ }
]
```

### H. System Pulse / Health
Returned by `GET /tc-auth/config/pulse`.
```json
{
  "system_time": "2026-08-12T10:00:00.000000",
  "response": "Hello",
  "status": "healthy",
  "state": "active"
}
```

### I. System Counts
Returned by `GET /tc-auth/config/counts`.
```json
{
  "accounts": 123,
  "oauth": 7,
  "sessions": 42,
  "otp": 3
}
```

### J. System Config
Returned by `GET /tc-auth/config/load/`.
```json
{
  "email": { ... },
  "github": { ... },
  "google": { ... },
  "jwt": { ... }
}
```

---

## 3. Complete Route & Response Change Matrix

| Route | Method | Previous Response | Standardized Response | Status |
|---|---|---|---|---|
| `/tc-auth/logout` | `POST` | `null` | `{"success": true, "message": "Session destroyed successfully"}` | Updated |
| `/tc-auth/logout-all` | `POST` | `null` | `{"success": true, "message": "All sessions destroyed for account", "count": <int>}` | Updated |
| `/tc-auth/me` | `GET` | `User dict` | `User dict` (account, session, payload) | Unchanged |
| `/tc-auth/me` | `PATCH` | `Account dict` | `Account dict` | Unchanged |
| `/tc-auth/update/password` | `PUT` | `null` | `{"success": true, "message": "Password updated successfully"}` | Updated |
| `/tc-auth/send/email/otp/{purpose}` | `POST` | `{"expires_at": <int>}` | `{"expires_at": <int>}` | Unchanged |
| `/tc-auth/signup/otp` | `POST` | `Auth token payload` | `Auth token payload` | Unchanged |
| `/tc-auth/signup/password` | `POST` | `Auth token payload` | `Auth token payload` | Unchanged |
| `/tc-auth/login/otp` | `POST` | `Auth token payload` | `Auth token payload` | Unchanged |
| `/tc-auth/login/password` | `POST` | `Auth token payload` | `Auth token payload` | Unchanged |
| `/tc-auth/forgot/password` | `POST` | `Auth token payload` | `Auth token payload` | Unchanged |
| `/tc-auth/google/login` | `GET` | `RedirectResponse` | `RedirectResponse` | Unchanged |
| `/tc-auth/google/callback` | `GET` | `RedirectResponse` | `RedirectResponse` | Unchanged |
| `/tc-auth/github/login` | `GET` | `RedirectResponse` | `RedirectResponse` | Unchanged |
| `/tc-auth/github/callback` | `GET` | `RedirectResponse` | `RedirectResponse` | Unchanged |
| `/tc-auth/account/` | `GET` | `List[Account]` | `List[Account]` | Unchanged |
| `/tc-auth/account/query` | `GET` | `List[Account]` | `List[Account]` | Unchanged |
| `/tc-auth/account/` | `POST` | `Account dict` | `Account dict` | Unchanged |
| `/tc-auth/account/` | `PATCH` | `Account dict` | `Account dict` | Unchanged |
| `/tc-auth/account/` | `DELETE` | `null` | `{"success": true, "message": "Account deleted successfully"}` | Updated |
| `/tc-auth/oauth/` | `GET` | `List[OAuthAccount]` | `List[OAuthAccount]` | Unchanged |
| `/tc-auth/oauth/query` | `GET` | `List[OAuthAccount]` | `List[OAuthAccount]` | Unchanged |
| `/tc-auth/oauth/` | `POST` | `OAuthAccount dict` | `OAuthAccount dict` | Unchanged |
| `/tc-auth/oauth/` | `DELETE` | `null` | `{"success": true, "message": "OAuth link removed successfully"}` | Updated |
| `/tc-auth/otp/` | `GET` | `List[OTP]` | `List[OTP]` | Unchanged |
| `/tc-auth/otp/query` | `GET` | `List[OTP]` | `List[OTP]` | Unchanged |
| `/tc-auth/otp/` | `POST` | `{"otp": str, "expires_at": int}` | `{"otp": str, "expires_at": int}` | Unchanged |
| `/tc-auth/otp/` | `DELETE` | `null` | `{"success": true, "message": "OTP revoked successfully", "count": <int>}` | Updated |
| `/tc-auth/otp/cleanup` | `DELETE` | `null` | `{"success": true, "message": "Expired OTPs cleaned successfully", "count": <int>}` | Updated |
| `/tc-auth/otp/clear` | `DELETE` | `null` | `{"success": true, "message": "All OTPs cleared successfully", "count": <int>}` | Updated |
| `/tc-auth/session/` | `GET` | `List[Session]` | `List[Session]` | Unchanged |
| `/tc-auth/session/query` | `GET` | `List[Session]` | `List[Session]` | Unchanged |
| `/tc-auth/session/` | `DELETE` | `null` | `{"success": true, "message": "Session destroyed successfully"}` | Updated |
| `/tc-auth/session/all` | `DELETE` | `null` | `{"success": true, "message": "All sessions destroyed for account", "count": <int>}` | Updated |
| `/tc-auth/session/cleanup` | `DELETE` | `null` | `{"success": true, "message": "Expired sessions cleaned up successfully", "count": <int>}` | Updated |
| `/tc-auth/session/clear` | `DELETE` | `null` | `{"success": true, "message": "All sessions cleared successfully", "count": <int>}` | Updated |
| `/tc-auth/config/pulse` | `GET` | `Pulse dict` | `Pulse dict` | Unchanged |
| `/tc-auth/config/load/` | `GET` | `Config dict` | `Config dict` | Unchanged |
| `/tc-auth/config/counts` | `GET` | `Counts dict` | `Counts dict` | Unchanged |
| `/tc-auth/config/email` | `POST` | `null` | `{"success": true, "message": "Email service configured successfully"}` | Updated |
| `/tc-auth/config/github` | `POST` | `null` | `{"success": true, "message": "GitHub OAuth configured successfully"}` | Updated |
| `/tc-auth/config/google` | `POST` | `null` | `{"success": true, "message": "Google OAuth configured successfully"}` | Updated |
| `/tc-auth/config/jwt` | `POST` | `null` | `{"success": true, "message": "JWT configured successfully"}` | Updated |

---

## 4. Service Layer Return Signatures

| Service Method | Return Signature | Notes |
|---|---|---|
| `AccountService.delete_user` | `{"success": True, "message": "Account deleted successfully"}` | Replaces `None` |
| `AccountService.update_password` | `{"success": True, "message": "Password updated successfully"}` | Replaces `None` |
| `SessionService.destroy_session` | `{"success": True, "message": "Session destroyed successfully"}` | Replaces `None` |
| `SessionService.destroy_all` | `{"success": True, "message": "All sessions destroyed for account", "count": <int>}` | Replaces `None` |
| `SessionService.cleanup_expired` | `{"success": True, "message": "Expired sessions cleaned up successfully", "count": <int>}` | Replaces `None` |
| `SessionService.clear_all` | `{"success": True, "message": "All sessions cleared successfully", "count": <int>}` | Replaces `None` |
| `OTPService.verify` | `{"success": True, "message": "OTP verified successfully"}` | Replaces `None` |
| `OTPService.revoke` | `{"success": True, "message": "OTP revoked successfully", "count": <int>}` | Replaces `None` |
| `OTPService.cleanup` | `{"success": True, "message": "Expired OTPs cleaned successfully", "count": <int>}` | Replaces `None` |
| `OTPService.clear_all` | `{"success": True, "message": "All OTPs cleared successfully", "count": <int>}` | Replaces `None` |
| `OAuthService.unlink_account` | `{"success": True, "message": "OAuth link removed successfully"}` | Replaces `None` |
| `EmailService.config` | `{"success": True, "message": "Email service configured successfully"}` | Replaces `None` |
| `EmailService.send` | `{"success": True, "message": "Email sent successfully to <recipient>"}` | Replaces `None` |
| `GitHubOAuth.config` | `{"success": True, "message": "GitHub OAuth configured successfully"}` | Replaces `None` |
| `GoogleOAuth.config` | `{"success": True, "message": "Google OAuth configured successfully"}` | Replaces `None` |
| `jwt_handler.config` | `{"success": True, "message": "JWT configured successfully"}` | Replaces `None` |
