# OAuth Login Routes

Base path: Configurable (defaults to `/tc-auth` via `auth.include_routes(app, prefix="/tc-auth")`).
All routes and code examples below are relative to your auth `baseUrl` (e.g. `const baseUrl = "https://api.example.com/tc-auth"`).

Authentication:

- These routes are part of the browser OAuth flow and are public.
- The callback endpoints rely on the session cookie (`session`) set during the `/login` step to maintain state and carry `frontend_url` across provider redirects.

Mode Handling (Single/Dual Token & Cookie/Local Storage):

- **Single-Token Mode**: The callback redirects to `${frontend_url}/oauth/callback?access_token=...`
- **Dual-Token Mode**: The callback redirects to `${frontend_url}/oauth/callback?access_token=...&refresh_token=...`
- **Cookie Mode (`AUTH_SEND_TOKENS_IN_COOKIE=True`)**: In addition to query parameters, the backend sets `HttpOnly`, `SameSite`, and `Secure` cookies (`access_token`, and `refresh_token` if dual-token mode is enabled) directly on the redirect response.
- **Account Linking Flow**: When linking an existing logged-in account, the callback redirects to `${frontend_url}/oauth/callback?linked=true&provider=<provider>` (or `?linked=false&provider=<provider>&error=<message>`).

For full frontend implementation details across all combinations, see the [OAuth Frontend Integration Guide](oauth_integration.md).

Common response:

- Login endpoints return a redirect response (`HTTP 307`) rather than JSON.
- Callback endpoints return a redirect response (`HTTP 307`) rather than JSON.

## GET `/google/login`

Starts the Google OAuth login flow.

Query parameters:

- `frontend_url` (*required*) - frontend callback base URL to return to after the OAuth exchange (e.g. `https://app.example.com`).

Response:

- Redirect to Google authorization consent screen.

Example:

```js
window.location.href = `${baseUrl}/google/login?frontend_url=${encodeURIComponent(frontendUrl)}`;
```

## GET `/google/callback`

Google OAuth callback endpoint.

Request parameters:

- Provider query parameters (`code`, `state`, `scope`, etc.) are supplied automatically by Google.

Response:

- **Login/Signup**: Redirects to `${frontend_url}/oauth/callback?access_token=...` (plus `&refresh_token=...` if dual-token mode). If cookie mode is active, `Set-Cookie` headers are also sent.
- **Linking**: Redirects to `${frontend_url}/oauth/callback?linked=true&provider=google`.

Example:

```js
// Handled automatically via browser redirect to frontend callback router
```

## GET `/github/login`

Starts the GitHub OAuth login flow.

Query parameters:

- `frontend_url` (*required*) - frontend callback base URL to return to after the OAuth exchange.

Response:

- Redirect to GitHub authorization screen.

Example:

```js
window.location.href = `${baseUrl}/github/login?frontend_url=${encodeURIComponent(frontendUrl)}`;
```

## GET `/github/callback`

GitHub OAuth callback endpoint.

Request parameters:

- Provider query parameters (`code`, `state`, etc.) are supplied automatically by GitHub.

Response:

- **Login/Signup**: Redirects to `${frontend_url}/oauth/callback?access_token=...` (plus `&refresh_token=...` if dual-token mode). If cookie mode is active, `Set-Cookie` headers are also sent.
- **Linking**: Redirects to `${frontend_url}/oauth/callback?linked=true&provider=github`.

Example:

```js
// Handled automatically via browser redirect to frontend callback router
```

## GET `/discord/login`

Starts the Discord OAuth login flow.

Query parameters:

- `frontend_url` (*required*) - frontend callback base URL to return to after the OAuth exchange.

Response:

- Redirect to Discord authorization screen.

Example:

```js
window.location.href = `${baseUrl}/discord/login?frontend_url=${encodeURIComponent(frontendUrl)}`;
```

## GET `/discord/callback`

Discord OAuth callback endpoint.

Request parameters:

- Provider query parameters (`code`, `state`, etc.) are supplied automatically by Discord.

Response:

- **Login/Signup**: Redirects to `${frontend_url}/oauth/callback?access_token=...` (plus `&refresh_token=...` if dual-token mode). If cookie mode is active, `Set-Cookie` headers are also sent.
- **Linking**: Redirects to `${frontend_url}/oauth/callback?linked=true&provider=discord`.

Example:

```js
// Handled automatically via browser redirect to frontend callback router
```


