from connect import auth


# ==========================================================
# COOKIE CONFIGURATION & STORAGE MODES
# ==========================================================
#
# The auth.cookie module provides cookie configuration and helpers
# for choosing between localStorage mode and Cookie mode.
#
# Available methods:
#
#     config()
#         Configure Cookie and storage mode settings.
#
#     load()
#         Get the current Cookie configuration.
#
#     is_cookie_mode()
#         Returns True if cookie mode is enabled, False otherwise.
#
#     set_auth_cookies(response, access_token, refresh_token=None)
#         Sets auth cookies on any FastAPI/Starlette Response.
#
#     clear_auth_cookies(response)
#         Clears auth cookies on logout.
#
#     extract_access_token(request)
#         Extracts access token from request cookies.
#
#     extract_refresh_token(request)
#         Extracts refresh token from request cookies.
#
#
# ==========================================================
# 1. LOAD COOKIE CONFIGURATION
# ==========================================================
#
# Returns the currently configured Cookie settings.
#
# Default configuration:
# {
#     "cookie_mode": False,
#     "access_cookie_name": "access_token",
#     "refresh_cookie_name": "refresh_token",
#     "path": "/",
#     "domain": None,
#     "secure": False,
#     "httponly": True,
#     "samesite": "lax",
#     "max_age": None
# }
#
config = auth.cookie.load()
print("Current Cookie Config:", config)


# ==========================================================
# 2. CONFIGURE LOCALSTORAGE MODE (DEFAULT)
# ==========================================================
#
# In localStorage mode (cookie_mode=False):
# - Tokens are returned in JSON response bodies.
# - OAuth redirects include tokens in URL query params.
# - Protected routes read tokens from `Authorization: Bearer <token>` headers.
#
auth.cookie.config(
    cookie_mode=False,
)


# ==========================================================
# 3. CONFIGURE COOKIE MODE
# ==========================================================
#
# In Cookie mode (cookie_mode=True):
# - Login, signup, and OAuth callbacks attach HttpOnly cookies
#   automatically (access_token, refresh_token).
# - Existing OAuth redirects continue to include URL query params
#   to preserve backwards compatibility for frontends and SDKs.
# - Protected routes accept either Bearer headers or Cookies automatically.
# - Logout routes automatically delete the auth cookies.
#
auth.cookie.config(
    cookie_mode=True,
    access_cookie_name="access_token",
    refresh_cookie_name="refresh_token",
    path="/",
    secure=False,        # Set to True in production (HTTPS)
    httponly=True,       # Prevents JavaScript XSS access
    samesite="lax",      # "lax", "strict", or "none" (if "none", secure must be True)
    max_age=None,        # None = automatically synchronized with JWT durations
)

print("Cookie mode enabled:", auth.cookie.is_cookie_mode())
