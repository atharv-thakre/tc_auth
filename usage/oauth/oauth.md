# OAuth API

The `auth.oauth` module provides methods for OAuth authentication and
management of OAuth provider links.

## Available Methods

  -----------------------------------------------------------------------
  Method                              Purpose
  ----------------------------------- -----------------------------------
  `login()`                           Authenticate through an OAuth
                                      provider and return a login
                                      response.

  `find_oauth()`                      Find an existing OAuth account
                                      link.

  `link_account()`                    Link an OAuth provider account to
                                      an existing account.

  `unlink_account()`                  Remove an OAuth provider link.

  `get_all()`                         Get a paginated list of OAuth
                                      accounts.

  `query()`                           Search OAuth accounts using exact
                                      matching.
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# `login()`

Authenticates a user through an OAuth provider.

``` python
auth.oauth.login(...)
```

## Required Parameters

  Parameter            Type    Description
  -------------------- ------- -----------------------------------------
  `provider`           `str`   OAuth provider name, such as `github`.
  `provider_user_id`   `str`   User ID provided by the OAuth provider.

## Optional Parameters

  Parameter      Type    Default   Description
  -------------- ------- --------- ------------------------------------
  `name`         `str`   `None`    User's name.
  `email`        `str`   `None`    User's email address.
  `avatar_url`   `str`   `None`    User's avatar URL.
  `ip_address`   `str`   `None`    Client IP address for the session.
  `user_agent`   `str`   `None`    Client User-Agent for the session.

## Behavior

When an OAuth login is performed:

1.  If the OAuth account is already linked, the linked account is used.
2.  If the OAuth account is not linked to an account, a new account is
    created.
3.  The new account is automatically linked to the OAuth provider
    account using the user's email.
4.  A login response is returned.
5.  A session record is created.

`ip_address` and `user_agent` are optional. If they are not provided,
`None` is used.

## Example

``` python
response = auth.oauth.login(
    provider="github",
    provider_user_id="1234567890",
    name="testuser",
    email="testuser@example.com",
    avatar_url="https://example.com/avatar.jpg",
    ip_address="127.0.0.1",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
)
```

## Returns

Returns the standard login response:

``` python
{
    "access_token": access_token,
    "token_type": "Bearer",
    "account": account
}
```

------------------------------------------------------------------------

# `find_oauth()`

Finds an OAuth account link using the provider and provider-specific
user ID.

``` python
auth.oauth.find_oauth(...)
```

## Parameters

  Parameter            Type    Required
  -------------------- ------- ----------
  `provider`           `str`   Yes
  `provider_user_id`   `str`   Yes

Both parameters are mandatory.

## Example

``` python
oauth_account = auth.oauth.find_oauth(
    provider="github",
    provider_user_id="1234567890",
)
```

## Returns

Returns an OAuth account object:

``` python
{
    "id": 1,
    "account_id": 1,
    "provider": "github",
    "provider_user_id": "1234567890",
    "created_at": "2026-08-11T18:11:00.001639"
}
```

------------------------------------------------------------------------

# `link_account()`

Links an OAuth provider account to an existing account.

``` python
auth.oauth.link_account(...)
```

## Parameters

  Parameter            Type    Required
  -------------------- ------- ----------
  `account_id`         `int`   Yes
  `provider`           `str`   Yes
  `provider_user_id`   `str`   Yes

All parameters are mandatory.

## Example

``` python
oauth_account = auth.oauth.link_account(
    account_id=1,
    provider="github",
    provider_user_id="1234567890",
)
```

## Returns

Returns the OAuth account object using the same structure as
`find_oauth()`.

------------------------------------------------------------------------

# `unlink_account()`

Removes an OAuth provider link from an existing account.

``` python
auth.oauth.unlink_account(...)
```

## Parameters

  Parameter      Type    Required
  -------------- ------- ----------
  `account_id`   `int`   Yes
  `provider`     `str`   Yes

All parameters are mandatory.

## Example

``` python
response = auth.oauth.unlink_account(
    account_id=1,
    provider="github",
)
```

## Returns

``` python
{
    "success": True,
    "message": "OAuth link removed successfully"
}
```

------------------------------------------------------------------------

# `get_all()`

Returns a paginated list of OAuth account records.

``` python
auth.oauth.get_all(...)
```

## Parameters

  Parameter     Type    Default   Description
  ------------- ------- --------- --------------------------------------
  `page`        `int`   `1`       Page number.
  `limit`       `int`   `10`      Number of records returned per page.

Both parameters are optional.

## Pagination

Results are returned from the latest OAuth account record.

For example, with:

``` python
limit=10
```

the results are divided as follows:

  Request    Records
  ---------- -------------------
  `page=1`   Latest 10 records
  `page=2`   Next 10 records
  `page=3`   Next 10 records

Increase the page number to retrieve the next set of records.

## Example

``` python
oauth_accounts = auth.oauth.get_all(
    page=1,
    limit=10,
)
```

## Returns

Returns:

``` text
list[dict]
```

Each dictionary uses the same OAuth account structure returned by
`find_oauth()`.

------------------------------------------------------------------------

# `query()`

Searches OAuth account records using an exact field value.

``` python
auth.oauth.query(...)
```

## Parameters

  Parameter   Type    Required
  ----------- ------- ----------
  `field`     `str`   Yes
  `value`     `str`   Yes

Both parameters are mandatory.

## Supported Fields

The following fields can be queried:

-   `id`
-   `account_id`
-   `provider_id`

## Matching Behavior

Queries use **exact/absolute matching**.

Partial matching is **not supported**.

For example:

``` python
field="id"
value="1"
```

matches the record with ID `1`, but does not perform a partial search.

## Value Type

`value` should be provided as a string.

The SDK automatically handles typecasting internally when required.

## Example

``` python
oauth_accounts = auth.oauth.query(
    field="id",
    value="1",
)
```

## Returns

Returns:

``` text
list[dict]
```

Each dictionary uses the same OAuth account structure returned by
`find_oauth()`.

If no records match the query, an empty list is returned:

``` python
[]
```

------------------------------------------------------------------------

# OAuth Account Object

The OAuth account object returned by:

-   `find_oauth()`
-   `link_account()`
-   `get_all()`
-   `query()`

uses the following structure:

``` python
{
    "id": 1,
    "account_id": 1,
    "provider": "github",
    "provider_user_id": "1234567890",
    "created_at": "2026-08-11T18:11:00.001639"
}
```

  Field                Type    Description
  -------------------- ------- -----------------------------------------
  `id`                 `int`   OAuth link record ID.
  `account_id`         `int`   ID of the linked account.
  `provider`           `str`   OAuth provider name.
  `provider_user_id`   `str`   User ID assigned by the OAuth provider.
  `created_at`         `str`   Time when the OAuth link was created.

------------------------------------------------------------------------

# Return Summary

  Method               Return
  -------------------- ------------------------------------------
  `login()`            `dict` --- Login response
  `find_oauth()`       `dict` --- OAuth account
  `link_account()`     `dict` --- OAuth account
  `unlink_account()`   `dict` --- `{"success": True, "message": "..."}`
  `get_all()`          `list[dict]` --- OAuth accounts
  `query()`            `list[dict]` --- Matching OAuth accounts

------------------------------------------------------------------------

# Quick Usage

``` python
from connect import auth


# OAuth login
response = auth.oauth.login(
    provider="github",
    provider_user_id="1234567890",
    name="testuser",
    email="testuser@example.com",
)


# Find OAuth link
oauth_account = auth.oauth.find_oauth(
    provider="github",
    provider_user_id="1234567890",
)


# Link OAuth account
oauth_account = auth.oauth.link_account(
    account_id=1,
    provider="github",
    provider_user_id="1234567890",
)


# Unlink OAuth account
result = auth.oauth.unlink_account(
    account_id=1,
    provider="github",
)


# Get all OAuth accounts
oauth_accounts = auth.oauth.get_all(
    page=1,
    limit=10,
)


# Query OAuth accounts
oauth_accounts = auth.oauth.query(
    field="id",
    value="1",
)
```
