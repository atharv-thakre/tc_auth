from .account import (
    SuperUpdateSchema,
    SuperCreateSchema,
    SuperDeleteSchema,
    UpdatePassword,
    UpdateSchema,
)

from .dashboard import (
    OAuthConfig,
    EmailConfig,
    JWTConfig,
)

from .login import (
    SendOTPRequest,
    SendMagicLinkRequest,
    VerifyMagicLinkRequest,
    LoginPasswordRequest,
    LoginOTPRequest,
    ForgotPasswordRequest,
    SignupPasswordRequest,
    SignupOTPRequest,
    RefreshTokenRequest,
)

from .oauth import (
    CreateOAuth,
    DeleteOAuth,
    LinkOAuthRequest,
)

from .otp import (
    CreateOTP,
    DeleteOTP,
)

from .sessions import (
    DestroySession,
    DestroyAllSession,
)

__all__ = [
    # account
    "SuperUpdateSchema",
    "SuperCreateSchema",
    "SuperDeleteSchema",
    "UpdatePassword",
    "UpdateSchema",

    # dashboard
    "OAuthConfig",
    "EmailConfig",
    "JWTConfig",

    # login
    "SendOTPRequest",
    "SendMagicLinkRequest",
    "VerifyMagicLinkRequest",
    "LoginPasswordRequest",
    "LoginOTPRequest",
    "ForgotPasswordRequest",
    "SignupPasswordRequest",
    "SignupOTPRequest",
    "RefreshTokenRequest",

    # oauth
    "CreateOAuth",
    "DeleteOAuth",
    "LinkOAuthRequest",

    # otp
    "CreateOTP",
    "DeleteOTP",

    # sessions
    "DestroySession",
    "DestroyAllSession",
]