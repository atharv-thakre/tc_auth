class AuthError(Exception):
    status_code = 400

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class UserNotFoundError(AuthError):
    status_code = 404

    def __init__(self, field: str, value=None):
        self.field = field
        self.value = value
        super().__init__(f"User not found by {field}")


class InvalidCredentialsError(AuthError):
    status_code = 401

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message)


class EmailAlreadyExistsError(AuthError):
    status_code = 409

    def __init__(self, message: str = "Email already exists"):
        super().__init__(message)


class HandleAlreadyExistsError(AuthError):
    status_code = 409

    def __init__(self, message: str = "Handle already exists"):
        super().__init__(message)


class PhoneAlreadyExistsError(AuthError):
    status_code = 409

    def __init__(self, message: str = "Phone already exists"):
        super().__init__(message)


class OTPNotFoundError(AuthError):
    status_code = 404

    def __init__(self, message: str = "OTP not found."):
        super().__init__(message)


class OTPInvalidError(AuthError):
    status_code = 401

    def __init__(self, message: str = "Invalid OTP."):
        super().__init__(message)


class OTPExpiredError(AuthError):
    status_code = 401

    def __init__(self, message: str = "OTP has expired."):
        super().__init__(message)


class InvalidTokenError(AuthError):
    status_code = 401

    def __init__(self, field: str = "token", message: str | None = None):
        self.field = field
        msg = message or f"Invalid or expired token, failed {field}"
        super().__init__(msg)


class SessionNotFoundError(AuthError):
    status_code = 404

    def __init__(self, field: str, value=None):
        self.field = field
        self.value = value
        super().__init__(f"Session not found by {field}")


class PermissionDeniedError(AuthError):
    status_code = 403

    def __init__(
        self,
        current: str | None = None,
        required: tuple[str, ...] | list[str] | str | None = None,
        field: str = "role",
        message: str | None = None,
    ):
        self.role = current
        self.current = current
        self.required = required
        self.field = field

        if message:
            super().__init__(message)
        elif required is None:
            super().__init__(f"Permission denied for {field} '{current}'")
        else:
            if isinstance(required, str):
                allowed = required
            else:
                allowed = ", ".join(str(r) for r in required)
            super().__init__(
                f"{field.capitalize()} '{current}' is not permitted. "
                f"Required: {allowed}"
            )


class AccountStatusError(PermissionDeniedError):
    status_code = 403

    def __init__(
        self,
        status: str | None = None,
        required: tuple[str, ...] | list[str] | str | None = None,
        message: str | None = None,
    ):
        super().__init__(
            current=status,
            required=required,
            field="status",
            message=message,
        )


class InvalidFieldError(AuthError):
    status_code = 400

    def __init__(self, field: str, message: str | None = None):
        self.field = field
        msg = message or f"Invalid field: {field}"
        super().__init__(msg)


class DatabaseError(AuthError):
    status_code = 500

    def __init__(self, message: str = "Database error occurred"):
        super().__init__(message)


class OAuthError(AuthError):
    status_code = 400

    def __init__(self, message: str = "OAuth error occurred"):
        super().__init__(message)


class OAuthNotConfiguredError(OAuthError):
    status_code = 500

    def __init__(self, provider: str = "OAuth"):
        super().__init__(f"{provider} service is not configured")


class OAuthAlreadyLinkedError(OAuthError):
    status_code = 409

    def __init__(self, message: str = "OAuth account is already linked"):
        super().__init__(message)


class OAuthLinkNotFoundError(OAuthError):
    status_code = 404

    def __init__(self, message: str = "OAuth account link not found"):
        super().__init__(message)


class OAuthCallbackError(OAuthError):
    status_code = 400

    def __init__(self, message: str = "OAuth callback failed"):
        super().__init__(message)


class EmailError(AuthError):
    status_code = 500

    def __init__(self, message: str = "Email error occurred"):
        super().__init__(message)


class EmailNotConfiguredError(EmailError):
    status_code = 500

    def __init__(self, message: str = "Email service is not configured"):
        super().__init__(message)


class EmailSendError(EmailError):
    status_code = 502

    def __init__(self, message: str = "Failed to send email"):
        super().__init__(message)


class InvalidEmailPurposeError(EmailError):
    status_code = 400

    def __init__(self, purpose: str):
        self.purpose = purpose
        super().__init__(f"Invalid email OTP purpose: '{purpose}'")


class InvalidConfigError(AuthError):
    status_code = 400

    def __init__(self, service: str, message: str | None = None):
        self.service = service
        msg = message or f"Invalid configuration for {service}"
        super().__init__(msg)


class WeakPasswordError(AuthError):
    status_code = 400

    def __init__(
        self,
        message: str = "Password must be at least 6 characters long and contain at least one uppercase letter, one lowercase letter, and one number",
    ):
        super().__init__(message)