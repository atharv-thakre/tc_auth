# Architecture, Database Models & Entity Relations (ERD)

This document provides a comprehensive visual and architectural breakdown of **CodeSena Auth (`tc_auth`)**, including Entity-Relationship (ER) diagrams, relational constraints, system architecture flowcharts, and security lifecycles.

---

## 1. Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    ACCOUNTS ||--o{ SESSIONS : "has active (1:N, cascade delete)"
    ACCOUNTS ||--o{ OAUTH_ACCOUNTS : "links third-party (1:N, cascade delete)"
    ACCOUNTS ||--o{ OTPS : "identified by email/phone (logical)"

    ACCOUNTS {
        int id PK "Autoincrement"
        uuid uid UK "UUIDv4, Indexed, Non-nullable"
        string name "Nullable, max 100"
        string handle UK "Unique, Indexed, Nullable, max 30"
        string email UK "Unique, Indexed, Nullable, max 255"
        string phone UK "Unique, Indexed, Nullable, max 20"
        text password_hash "Argon2/Bcrypt hash, Nullable"
        text avatar_url "Profile avatar URL, Nullable"
        string role "Default: 'user', Non-nullable, max 50"
        string status "Default: 'active', Nullable, max 100"
        timestamp created_at "Server Default: now()"
        timestamp updated_at "Server Default: now(), onupdate"
    }

    SESSIONS {
        int id PK "Autoincrement"
        int account_id FK "References accounts.id (CASCADE)"
        text token_hash UK "SHA-256(session_token_secret), Non-nullable"
        string ip_address "Client IPv4/IPv6, Nullable, max 45"
        text user_agent "Client User-Agent header, Nullable"
        timestamp expires_at "Session expiry timestamp, Non-nullable"
        timestamp created_at "Server Default: now()"
    }

    OAUTH_ACCOUNTS {
        int id PK "Autoincrement"
        int account_id FK "References accounts.id (CASCADE)"
        string provider "google | github | discord, max 30"
        string provider_user_id "External user ID (sub), max 255"
        timestamp created_at "Server Default: now()"
    }

    OTPS {
        int id PK "Autoincrement"
        string identifier "Email address or phone, Indexed, max 255"
        string purpose "signup | login | reset | verify, max 100"
        text code_hash "SHA-256(6-digit numeric OTP), Non-nullable"
        int attempts "Failed verification attempts counter, default 0"
        timestamp expires_at "OTP expiration timestamp, Non-nullable"
        timestamp created_at "Server Default: now()"
    }
```

---

## 2. Table Schemas & Relational Constraints

### 2.1 `accounts` Table
The primary identity record. Supports password authentication, social logins, or passwordless OTP logins.

```sql
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    uid UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    name VARCHAR(100),
    handle VARCHAR(30) UNIQUE,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20) UNIQUE,
    password_hash TEXT,
    avatar_url TEXT,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    status VARCHAR(100) DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_accounts_uid ON accounts(uid);
CREATE INDEX ix_accounts_handle ON accounts(handle);
CREATE INDEX ix_accounts_email ON accounts(email);
CREATE INDEX ix_accounts_phone ON accounts(phone);
```

### 2.2 `sessions` Table
Stores active user sessions with cryptographically hashed secrets. Raw session secret tokens are never stored in plaintext.

```sql
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    token_hash TEXT UNIQUE NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_sessions_account_id ON sessions(account_id);
```

### 2.3 `oauth_accounts` Table
Binds external OAuth 2.0 / OpenID Connect identity providers (Google, GitHub, Discord) to an account.

```sql
CREATE TABLE oauth_accounts (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    provider VARCHAR(30) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_oauth_provider_user UNIQUE (provider, provider_user_id),
    CONSTRAINT uq_account_provider UNIQUE (account_id, provider)
);

CREATE INDEX ix_oauth_accounts_account_id ON oauth_accounts(account_id);
CREATE INDEX ix_oauth_accounts_provider ON oauth_accounts(provider);
CREATE INDEX ix_oauth_accounts_provider_user_id ON oauth_accounts(provider_user_id);
```

### 2.4 `otps` Table
Stores short-lived 6-digit numeric verification codes for signup, login, password reset, and email verification.

```sql
CREATE TABLE otps (
    id SERIAL PRIMARY KEY,
    identifier VARCHAR(255) NOT NULL,
    purpose VARCHAR(100) NOT NULL,
    code_hash TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_otps_identifier ON otps(identifier);
CREATE INDEX idx_otp_identifier_purpose ON otps(identifier, purpose);
```

---

## 3. System Architecture & Lifecycle Flowcharts

### 3.1 Decoupled Initialization (`connect.py` vs `run.py`)

Eliminates circular import issues across modular FastAPI applications:

```mermaid
flowchart TD
    subgraph ConnectLayer["1. Database & Config Layer (connect.py)"]
        DBEngine["create_engine(DATABASE_URL)"] --> AuthInst["auth = Auth(engine=engine)"]
        AuthInst --> ServiceConfigs["auth.jwt.config()\nauth.email.config()\nauth.google.config()"]
    end

    subgraph FeatureRouters["2. Modular Domain Routers (routers/*.py)"]
        RouterItems["routers/items.py\nDepends(auth.deps.get_current_user)"]
        RouterPosts["routers/posts.py\nDepends(auth.role.require('admin'))"]
    end

    subgraph RunLayer["3. FastAPI Assembly & Server (run.py)"]
        App["app = FastAPI()"]
        IncludeAuthRoutes["auth.include_routes(app, prefix='/tc-auth')"]
        IncludeDomainRoutes["app.include_router(items_router)\napp.include_router(posts_router)"]
        UvicornRun["uvicorn.run('run:app')"]
    end

    ConnectLayer -->|Imports 'auth' safely| FeatureRouters
    ConnectLayer -->|Mounts routes| RunLayer
    FeatureRouters -->|Mounted on app| RunLayer
```

---

### 3.2 Dual-Layer Request Authentication & Session Validation

Every protected API request validates both the signed JWT claims and the server-side hashed session:

```mermaid
flowchart TD
    Req["Incoming API Request\nAuthorization: Bearer <access_token>"] --> Step1{"1. Validate JWT\nSignature & Expiry"}
    
    Step1 -->|Invalid / Expired| Err1["Raise InvalidTokenError (HTTP 401)"]
    Step1 -->|Valid Claims| Step2["Extract payload: aid, sid, token_secret"]
    
    Step2 --> Step3{"2. Lookup Session in DB\nby session_id (sid)"}
    Step3 -->|Not Found / Deleted| Err2["Raise InvalidTokenError (HTTP 401)\nSession Revoked"]
    
    Step3 -->|Session Found| Step4{"3. Verify SHA-256(token_secret)\n== session.token_hash"}
    Step4 -->|Mismatch| Err3["Raise InvalidTokenError (HTTP 401)\nTampered Secret"]
    
    Step4 -->|Match| Step5{"4. Check Session Expiry\nsession.expires_at > now()"}
    Step5 -->|Expired| Err4["Raise InvalidTokenError (HTTP 401)\nSession Expired"]
    
    Step5 -->|Active| Step6["5. Lookup Account in DB\nby account_id (aid)"]
    Step6 -->|User Missing / Banned| Err5["Raise InvalidTokenError (HTTP 401)"]
    
    Step6 -->|User Active| Grant["Inject Context into FastAPI Handler:\n{'account': ..., 'session': ..., 'payload': ...}"]
```

---

### 3.3 Dual-Token Lifecycle (Short-Lived Access + Rotating Refresh Token)

```mermaid
sequenceDiagram
    autonumber
    actor Client as Frontend Client (SPA / Mobile)
    participant API as FastAPI Protected Route
    participant AuthAPI as /tc-auth/token/refresh
    participant DB as PostgreSQL Database

    Client->>API: GET /items (Bearer access_token [15 min])
    API->>DB: Validate Session & Hash
    DB-->>API: Session Active
    API-->>Client: 200 OK (Data Payload)

    Note over Client,API: 15 minutes pass -> Access Token Expires

    Client->>API: GET /items (Expired access_token)
    API-->>Client: 401 Unauthorized (InvalidTokenError)

    Note over Client: Axios Interceptor catches 401, queues pending requests

    Client->>AuthAPI: POST /tc-auth/token/refresh { refresh_token }
    AuthAPI->>DB: Validate Session & Refresh Token
    DB-->>AuthAPI: Session Valid
    AuthAPI-->>Client: 200 OK { access_token (fresh 15m), refresh_token (rotated) }

    Note over Client: Interceptor replays queued requests with fresh access_token

    Client->>API: GET /items (Fresh access_token)
    API-->>Client: 200 OK (Data Payload)
```

---

### 3.4 OAuth 2.0 / OIDC Multi-Provider Linking Flow

```mermaid
flowchart TD
    UserClick["User clicks 'Sign in with Google'"] --> InitLogin["GET /tc-auth/google/login?frontend_url=https://app.com"]
    InitLogin --> GoogleConsent["Redirect (307) to Google OAuth Consent Screen"]
    GoogleConsent --> GoogleRedirect["Google redirects to GET /tc-auth/google/callback?code=..."]
    
    GoogleRedirect --> ExchangeCode["tc_auth exchanges code for Google Profile\n(email, sub, name, avatar)"]
    
    ExchangeCode --> CheckExisting{"Does oauth_accounts record\nexist for (google, sub)?"}
    
    CheckExisting -->|Yes| LoginUser["Authenticate existing Account"]
    CheckExisting -->|No| CheckEmail{"Does email match\nan existing account?"}
    
    CheckEmail -->|Yes| AutoLink["Auto-link Google provider to existing Account"]
    CheckEmail -->|No| CreateAccount["Create new Account (status='active')\nand link Google provider"]
    
    AutoLink --> IssueTokens["Create Session & Generate JWT Access + Refresh Tokens"]
    LoginUser --> IssueTokens
    CreateAccount --> IssueTokens
    
    IssueTokens --> FinalRedirect["Redirect (307) to:\nhttps://app.com/oauth/callback?access_token=...&refresh_token=..."]
```

---

### 3.5 Dual-Pathway Email Verification (Magic Link + Numeric OTP)

```mermaid
flowchart TD
    SendReq["User requests email verification / signup / login"] --> Dispatch["tc_auth creates OTP in DB (SHA-256 hash)\nSends branded HTML email via SMTP"]
    
    Dispatch --> EmailArrives["Email arrives in User Inbox\n(Contains: One-Click Button + 6-digit manual OTP)"]
    
    EmailArrives --> Choice{"How does the user proceed?"}
    
    Choice -->|Clicks One-Click Button| BrowserGET["GET /tc-auth/link/{purpose}?email=...&otp=..."]
    BrowserGET --> ValidateGET{"Validate OTP in DB"}
    ValidateGET -->|Valid| Burn1["Burn OTP (if login/verify)\nCreate Session & JWTs"]
    Burn1 --> RedirectFE["HTTP 307 Redirect to Frontend Callback Router"]
    
    Choice -->|Enters 6-Digit Code manually| FormPOST["POST /tc-auth/login/otp OR /tc-auth/signup/otp"]
    FormPOST --> ValidatePOST{"Validate OTP in DB"}
    ValidatePOST -->|Valid| Burn2["Burn OTP & Issue JWTs"]
    Burn2 --> JSONResp["Return 200 OK JSON with tokens and account"]
```

---

### 3.6 Safe OAuth Unlinking with Account Lockout Prevention

```mermaid
flowchart TD
    UnlinkReq["DELETE /tc-auth/account/oauth/{provider}\n(Authenticated Request)"] --> FetchAccount["Fetch Account & linked OAuth providers"]
    
    FetchAccount --> CheckPassword{"Does account have a\npassword set (password_hash != null)?"}
    
    CheckPassword -->|Yes| AllowUnlink["Delete OAuthAccount record from DB\nReturn 200 OK"]
    CheckPassword -->|No| CheckOtherProviders{"Are there other linked\nOAuth providers?"}
    
    CheckOtherProviders -->|Yes| AllowUnlink
    CheckOtherProviders -->|No (Only 1 Provider & No Password)| BlockUnlink["Raise AuthError (HTTP 400)\n'Cannot unlink provider: Account has no password\nand this is the only linked OAuth provider'"]
```
