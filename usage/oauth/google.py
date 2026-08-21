# ==========================================================
# GOOGLE OAUTH
# ==========================================================
#
# GoogleOAuth provides a ready-to-use Google OAuth flow for
# FastAPI applications.
#
# It handles:
#
#     1. Google OAuth configuration
#     2. Redirecting users to Google
#     3. Handling the Google OAuth callback
#     4. Reading the authenticated Google user information
#     5. Passing the user information to auth.oauth.login()
#     6. Redirecting the user back to the frontend
#
# The OAuth flow uses Authlib and FastAPI sessions.
#
#
# ==========================================================
# IMPORT
# ==========================================================

from usage import auth
from fastapi import Request


# ==========================================================
# CONFIGURE GOOGLE OAUTH
# ==========================================================
#
# Configure the Google OAuth client before using login()
# or callback().
#
# Required:
#
#     client_id:
#         Google OAuth client ID.
#
#     client_secret:
#         Google OAuth client secret.
#
#     redirect_uri:
#         OAuth callback URL registered in Google Cloud.
#
# Example:
#
auth.google.config(
    client_id="YOUR_GOOGLE_CLIENT_ID",
    client_secret="YOUR_GOOGLE_CLIENT_SECRET",
    redirect_uri="https://api.example.com/oauth/google/callback",
)


# ==========================================================
# LOAD GOOGLE OAUTH CONFIGURATION
# ==========================================================
#
# Returns the currently configured Google OAuth settings.
#
# Returns:
#
#     dict:
#     {
#         "client_id": client_id,
#         "client_secret": client_secret,
#         "redirect_uri": redirect_uri
#     }
#
# NOTE:
#     Avoid exposing client_secret to the frontend or returning
#     the result of this method through a public API endpoint.
#
config = auth.google.load()


# ==========================================================
# GOOGLE LOGIN
# ==========================================================
#
# Starts the Google OAuth login flow.
#
# The method redirects the user to Google's authentication
# page.
#
# Parameters:
#
#     request (Request):
#         FastAPI/Starlette request object.
#
#     frontend_url (str):
#         Frontend URL where the user should be redirected
#         after the OAuth callback is completed.
#
# The frontend URL is temporarily stored in the session so
# that the callback can redirect the user back to the correct
# frontend location.
#
# Returns:
#
#     RedirectResponse:
#         Redirects the user to Google's OAuth authorization
#         page.
#
# NOTE:
#     login() is asynchronous and must be awaited.
#
#
# Example:
#
@app.get("/oauth/google/login")
async def google_login(request: Request):
    return await auth.google.login(
        request=request,
        frontend_url="https://app.example.com",
    )


# ==========================================================
# GOOGLE OAUTH CALLBACK
# ==========================================================
#
# Handles the callback sent by Google after authentication.
#
# The callback:
#
#     1. Retrieves the frontend URL from the session.
#     2. Exchanges the authorization code for an OAuth token.
#     3. Reads the Google user's profile information.
#     4. Passes the user information to auth.oauth.login().
#     5. Creates or retrieves the linked account.
#     6. Creates a login response/session.
#     7. Redirects the user to the frontend OAuth callback.
#
# Optional:
#
#     ip_address:
#         Client IP address.
#
#     user_agent:
#         Client User-Agent.
#
# These values are passed to auth.oauth.login() and can be
# stored with the authentication session.
#
# Returns:
#
#     RedirectResponse:
#         Redirects to:
#
#         {frontend_url}/oauth/callback?access_token=...
#
# NOTE:
#     callback() is asynchronous and must be awaited.
#
#
# Example:
#
@app.get("/oauth/google/callback")
async def google_callback(request: Request):
    return await auth.google.callback(
        request=request,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


# ==========================================================
# GOOGLE OAUTH FLOW
# ==========================================================
#
# Typical request flow:
#
#     Frontend
#        |
#        v
#     /oauth/google/login
#        |
#        v
#     Google
#        |
#        v
#     User authenticates
#        |
#        v
#     /oauth/google/callback
#        |
#        v
#     auth.google.callback()
#        |
#        v
#     auth.oauth.login()
#        |
#        +---- Existing OAuth account
#        |         -> Use linked account
#        |
#        +---- New OAuth account
#                  -> Create account
#                  -> Link Google account
#        |
#        v
#     Login response
#        |
#        v
#     Frontend /oauth/callback
#
#
# ==========================================================
# GOOGLE USER DATA
# ==========================================================
#
# The callback reads Google's OpenID Connect user information.
#
# The following fields are used:
#
#     user["sub"]
#         Google user's unique provider ID.
#
#     user.get("name")
#         User's name.
#
#     user.get("email")
#         User's email address.
#
#     user.get("picture")
#         User's Google profile picture.
#
# These values are passed to:
#
#     auth.oauth.login()
#
# as:
#
#     provider="google"
#     provider_user_id=user["sub"]
#     name=user.get("name")
#     email=user.get("email")
#     avatar_url=user.get("picture")
#
#
# ==========================================================
# IMPORTANT CONFIGURATION
# ==========================================================
#
# The redirect_uri must exactly match the callback URL
# registered with Google.
#
# Example:
#
#     Google Console:
#         https://api.example.com/oauth/google/callback
#
#     Application:
#         redirect_uri="https://api.example.com/oauth/google/callback"
#
# A mismatch between these URLs will cause the OAuth flow
# to fail.
#
#
# ==========================================================
# COMPLETE FASTAPI EXAMPLE
# ==========================================================
#
from fastapi import FastAPI, Request

app = FastAPI()


# Configure OAuth once during application setup.
auth.google.config(
    client_id="YOUR_GOOGLE_CLIENT_ID",
    client_secret="YOUR_GOOGLE_CLIENT_SECRET",
    redirect_uri="https://api.example.com/oauth/google/callback",
)


@app.get("/oauth/google/login")
async def google_login(request: Request):
    return await auth.google.login(
        request=request,
        frontend_url="https://app.example.com",
    )


@app.get("/oauth/google/callback")
async def google_callback(request: Request):
    return await auth.google.callback(
        request=request,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
#
#
# After successful authentication, the user is redirected to:
#
#     https://app.example.com/oauth/callback?access_token=...
#
#
# ==========================================================
# SECURITY NOTES
# ==========================================================
#
# - Keep client_secret private.
# - Do not expose load() through a public endpoint.
# - Register the exact callback URL with Google.
# - Use HTTPS in production.
# - Configure the frontend URL from trusted application
#   configuration rather than accepting arbitrary redirect
#   destinations from untrusted users.
# - The access token returned by the callback should be handled
#   securely by the frontend.
