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

    def __init__(self):
        super().__init__("Invalid credentials")


class EmailAlreadyExistsError(AuthError):
    status_code = 409

    def __init__(self):
        super().__init__("Email already exists")


class HandleAlreadyExistsError(AuthError):
    status_code = 409

    def __init__(self):
        super().__init__("Handle already exists")


class PhoneAlreadyExistsError(AuthError):
    status_code = 409

    def __init__(self):
        super().__init__("Phone already exists")


class OTPNotFoundError(AuthError):
    status_code = 404

    def __init__(self):
        super().__init__("OTP not found.")


class OTPInvalidError(AuthError):
    status_code = 401

    def __init__(self):
        super().__init__("Invalid OTP.")


class OTPExpiredError(AuthError):
    status_code = 401

    def __init__(self):
        super().__init__("OTP has expired.")


class InvalidTokenError(AuthError):
    status_code = 401

    def __init__(self, field:str = "token"):
        super().__init__(f"Invalid or expired token, failed {field}")


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
        role: str,
        required: tuple[str, ...] | None = None,
    ):
        self.role = role
        self.required = required

        if required is None:
            message = f"Permission denied for role '{role}'"
        else:
            allowed = ", ".join(required)
            message = (
                f"Role '{role}' is not permitted. "
                f"Required: {allowed}"
            )

        super().__init__(message)