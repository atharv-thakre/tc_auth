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
    LoginPasswordRequest,
    LoginOTPRequest,
    ForgotPasswordRequest,
    SignupPasswordRequest,
    SignupOTPRequest,
)

from .oauth import (
    CreateOAuth,
    DeleteOAuth,
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
    "LoginPasswordRequest",
    "LoginOTPRequest",
    "ForgotPasswordRequest",
    "SignupPasswordRequest",
    "SignupOTPRequest",

    # oauth
    "CreateOAuth",
    "DeleteOAuth",

    # otp
    "CreateOTP",
    "DeleteOTP",

    # sessions
    "DestroySession",
    "DestroyAllSession",
]