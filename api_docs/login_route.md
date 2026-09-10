# Sign In / Sign Up Routes

Base path: `/tc-auth`

Authentication:

- All routes in this group are public.
- Successful signup and login responses return an `access_token` that must be sent as `Authorization: Bearer <access_token>` to protected routes.

Common responses:

- `200 OK` on success.
- `400` / `422` for validation failures.
- `401` for invalid credentials or invalid OTP values.
- `404` when the target account does not exist.

Common login response:

```json
{
  "access_token": "jwt-token",
  "token_type": "Bearer",
  "account": {
    "id": 1,
    "uid": "2d7b5f8e-8d8a-4cc4-9c3d-2f2c6c4d2e28",
    "name": "Jane Doe",
    "handle": "jane",
    "email": "jane@example.com",
    "phone": null,
    "avatar_url": null,
    "role": "user",
    "status": null,
    "created_at": "2026-08-07T12:00:00",
    "updated_at": "2026-08-07T12:00:00"
  }
}
```

## POST `/send/email/otp/{purpose}`

Sends an email OTP for the supplied purpose.

Path parameter:

- `purpose` - OTP purpose key. The route comment indicates `signup`, `login`, `reset`, or `verify`.

Body:

```json
{
  "email": "jane@example.com"
}
```

Response:

```json
{
  "expires_at": 1735689600
}
```

Example:

```js
await fetch(`${baseUrl}/tc-auth/send/email/otp/signup`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "jane@example.com" }),
});
```

## POST `/signup/otp`

Verifies a signup OTP and creates a new account.

Body:

```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "password": "password123",
  "otp": "123456",
  "handle": "jane"
}
```

Response:

Same login payload shown above.

Example:

```js
const res = await fetch(`${baseUrl}/tc-auth/signup/otp`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    name: "Jane Doe",
    email: "jane@example.com",
    password: "password123",
    otp: "123456",
    handle: "jane",
  }),
});

const data = await res.json();
```

## POST `/signup/password`

Creates a new account without an OTP step.

Body:

```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "handle": "jane",
  "password": "password123"
}
```

Response:

Same login payload shown above.

Example:

```js
const res = await fetch(`${baseUrl}/tc-auth/signup/password`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    name: "Jane Doe",
    email: "jane@example.com",
    handle: "jane",
    password: "password123",
  }),
});

const data = await res.json();
```

## POST `/login/otp`

Verifies a login OTP and returns a session token.

Body:

```json
{
  "email": "jane@example.com",
  "otp": "123456"
}
```

Response:

Same login payload shown above.

Example:

```js
const res = await fetch(`${baseUrl}/tc-auth/login/otp`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    email: "jane@example.com",
    otp: "123456",
  }),
});

const data = await res.json();
```

## POST `/login/password`

Logs a user in with email or handle plus password.

Body:

```json
{
  "identifier": "jane@example.com",
  "password": "password123"
}
```

`identifier` can be an email address or a handle.

Response:

Same login payload shown above.

Example:

```js
const res = await fetch(`${baseUrl}/tc-auth/login/password`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    identifier: "jane@example.com",
    password: "password123",
  }),
});

const data = await res.json();
```

## POST `/forgot/password`

Resets the password after verifying a reset OTP, then returns a fresh login token.

The request requires a valid reset OTP along with the new password (minimum 8 characters).

Body:

```json
{
  "email": "jane@example.com",
  "otp": "123456",
  "password": "new-password123"
}
```

Response:

Same login payload shown above.

Example:

```js
const res = await fetch(`${baseUrl}/tc-auth/forgot/password`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    email: "jane@example.com",
    otp: "123456",
    password: "new-password123",
  }),
});

const data = await res.json();
```
