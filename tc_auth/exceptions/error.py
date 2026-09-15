"""
TC Auth Exception Hierarchy

Provides a comprehensive, object-oriented error hierarchy for all authentication,
authorization, validation, database, external service, and configuration failures.
"""

from typing import Any


# ==============================================================================
# BASE EXCEPTION
# ==============================================================================

class AuthError(Exception):
    """
    Root base exception for all TC Auth errors.
    All errors raised within tc_auth inherit from this class.
    """
    status_code: int = 400
    error_code: str = "auth_error"

    def __init__(
        self,
        message: str = "Authentication error occurred",
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | list[Any] | None = None,
    ):
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        self.details = details
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Returns a standardized JSON-serializable dictionary for error responses."""
        payload: dict[str, Any] = {
            "success": False,
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.details is not None:
            payload["details"] = self.details
        return payload

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, status_code={self.status_code}, error_code={self.error_code!r})"


# ==============================================================================
# CATEGORY 1: 400 BAD REQUEST / VALIDATION ERRORS
# ==============================================================================

class BadRequestError(AuthError):
    """Base exception for client request validation errors (HTTP 400)."""
    status_code = 400
    error_code = "bad_request"


class InvalidFieldError(BadRequestError):
    """Raised when a specific request field has an invalid format or value."""
    status_code = 400
    error_code = "invalid_field"

    def __init__(self, field: str, message: str | None = None):
        self.field = field
        msg = message or f"Invalid field: {field}"
        super().__init__(msg)


class MissingRequiredFieldError(InvalidFieldError):
    """Raised when a required parameter or body field is omitted."""
    status_code = 400
    error_code = "missing_required_field"

    def __init__(self, field: str, message: str | None = None):
        msg = message or f"Missing required field: '{field}'"
        super().__init__(field=field, message=msg)


class InvalidIdentifierError(BadRequestError):
    """Raised when an identifier (email, username, handle) format is invalid."""
    status_code = 400
    error_code = "invalid_identifier"

    def __init__(self, identifier: str, message: str | None = None):
        self.identifier = identifier
        msg = message or f"Invalid identifier: '{identifier}'"
        super().__init__(msg)


class WeakPasswordError(BadRequestError):
    """Raised when a proposed password does not satisfy security policy rules."""
    status_code = 400
    error_code = "weak_password"

    def __init__(
        self,
        message: str = "Password must be at least 6 characters long and contain at least one uppercase letter, one lowercase letter, and one number",
    ):
        super().__init__(message)


class OTPValidationError(BadRequestError):
    """Raised when OTP generation arguments (expiry, length, purpose) are invalid."""
    status_code = 400
    error_code = "otp_validation_error"

    def __init__(self, message: str = "Invalid OTP configuration parameters"):
        super().__init__(message)


# ==============================================================================
# CATEGORY 2: 401 UNAUTHORIZED / AUTHENTICATION ERRORS
# ==============================================================================

class AuthenticationError(AuthError):
    """Base exception for authentication failures (HTTP 401)."""
    status_code = 401
    error_code = "authentication_error"


class InvalidCredentialsError(AuthenticationError):
    """Raised when provided credentials (identifier/password or OTP) do not match."""
    status_code = 401
    error_code = "invalid_credentials"

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message)


class InvalidTokenError(AuthenticationError):
    """Raised when a JWT access or refresh token is invalid or missing."""
    status_code = 401
    error_code = "invalid_token"

    def __init__(self, field: str = "token", message: str | None = None):
        self.field = field
        msg = message or f"Invalid or expired token, failed {field}"
        super().__init__(msg)


class TokenMissingError(InvalidTokenError):
    """Raised when an authorization header or cookie token is completely missing."""
    status_code = 401
    error_code = "token_missing"

    def __init__(self, message: str = "Missing authorization credentials"):
        super().__init__(field="credentials", message=message)


class TokenExpiredError(InvalidTokenError):
    """Raised when a cryptographic token's timestamp has passed its expiration."""
    status_code = 401
    error_code = "token_expired"

    def __init__(self, message: str = "Token has expired"):
        super().__init__(field="token", message=message)


class TokenMalformedError(InvalidTokenError):
    """Raised when a JWT cannot be parsed, decoded, or has invalid claims."""
    status_code = 401
    error_code = "token_malformed"

    def __init__(self, message: str = "Token is malformed or contains invalid claims"):
        super().__init__(field="token", message=message)


class TokenSignatureError(InvalidTokenError):
    """Raised when token signature verification fails against secret key."""
    status_code = 401
    error_code = "token_signature_invalid"

    def __init__(self, message: str = "Invalid token signature"):
        super().__init__(field="token", message=message)


class TokenRevokedError(InvalidTokenError):
    """Raised when a token belongs to a session that was destroyed/revoked."""
    status_code = 401
    error_code = "token_revoked"

    def __init__(self, message: str = "Token has been revoked"):
        super().__init__(field="token", message=message)


class SessionExpiredError(AuthenticationError):
    """Raised when a database-backed session has passed its expiration timestamp."""
    status_code = 401
    error_code = "session_expired"

    def __init__(self, message: str = "Session has expired"):
        super().__init__(message)


class OTPInvalidError(AuthenticationError):
    """Raised when the submitted OTP code is incorrect."""
    status_code = 401
    error_code = "invalid_otp"

    def __init__(self, message: str = "Invalid OTP."):
        super().__init__(message)


class OTPExpiredError(AuthenticationError):
    """Raised when the submitted OTP code has exceeded its validity window."""
    status_code = 401
    error_code = "otp_expired"

    def __init__(self, message: str = "OTP has expired."):
        super().__init__(message)


# ==============================================================================
# CATEGORY 3: 403 FORBIDDEN / PERMISSION & ROLE ERRORS
# ==============================================================================

class AuthorizationError(AuthError):
    """Base exception for authorization and access control failures (HTTP 403)."""
    status_code = 403
    error_code = "authorization_error"


class PermissionDeniedError(AuthorizationError):
    """Raised when an authenticated user lacks the required role or privilege."""
    status_code = 403
    error_code = "permission_denied"

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


class RoleMismatchError(PermissionDeniedError):
    """Raised specifically when a user's role does not match required role(s)."""
    status_code = 403
    error_code = "role_mismatch"

    def __init__(
        self,
        current: str | None = None,
        required: tuple[str, ...] | list[str] | str | None = None,
        message: str | None = None,
    ):
        super().__init__(current=current, required=required, field="role", message=message)


class RoleBlockedError(PermissionDeniedError):
    """Raised when a user possesses a role that has been explicitly blocked."""
    status_code = 403
    error_code = "role_blocked"

    def __init__(self, role: str | None = None, message: str | None = None):
        msg = message or f"Role '{role}' is explicitly blocked from this resource"
        super().__init__(current=role, field="role", message=msg)


class AccountStatusError(PermissionDeniedError):
    """Raised when an account's status (e.g. suspended, inactive) prevents access."""
    status_code = 403
    error_code = "account_status_error"

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


class AccountSuspendedError(AccountStatusError):
    """Raised when an account is marked as suspended."""
    status_code = 403
    error_code = "account_suspended"

    def __init__(self, message: str = "Account is suspended"):
        super().__init__(status="suspended", message=message)


class AccountInactiveError(AccountStatusError):
    """Raised when an account is inactive or pending email verification."""
    status_code = 403
    error_code = "account_inactive"

    def __init__(self, message: str = "Account is inactive"):
        super().__init__(status="inactive", message=message)


# ==============================================================================
# CATEGORY 4: 404 NOT FOUND ERRORS
# ==============================================================================

class NotFoundError(AuthError):
    """Base exception for resources that cannot be located (HTTP 404)."""
    status_code = 404
    error_code = "not_found"


class UserNotFoundError(NotFoundError):
    """Raised when an account query yields no matching database record."""
    status_code = 404
    error_code = "user_not_found"

    def __init__(self, field: str, value: Any = None):
        self.field = field
        self.value = value
        super().__init__(f"User not found by {field}")


class SessionNotFoundError(NotFoundError):
    """Raised when a session record cannot be found in the database."""
    status_code = 404
    error_code = "session_not_found"

    def __init__(self, field: str, value: Any = None):
        self.field = field
        self.value = value
        super().__init__(f"Session not found by {field}")


class OTPNotFoundError(NotFoundError):
    """Raised when no matching OTP record exists for the given identifier and purpose."""
    status_code = 404
    error_code = "otp_not_found"

    def __init__(self, message: str = "OTP not found."):
        super().__init__(message)


# ==============================================================================
# CATEGORY 5: 409 CONFLICT ERRORS
# ==============================================================================

class ConflictError(AuthError):
    """Base exception for resource state collisions and uniqueness violations (HTTP 409)."""
    status_code = 409
    error_code = "conflict"


class AlreadyExistsError(ConflictError):
    """Base exception for unique constraint violations."""
    status_code = 409
    error_code = "already_exists"


class EmailAlreadyExistsError(AlreadyExistsError):
    """Raised when an email address is already registered."""
    status_code = 409
    error_code = "email_already_exists"

    def __init__(self, message: str = "Email already exists"):
        super().__init__(message)


class HandleAlreadyExistsError(AlreadyExistsError):
    """Raised when a username / handle is already claimed."""
    status_code = 409
    error_code = "handle_already_exists"

    def __init__(self, message: str = "Handle already exists"):
        super().__init__(message)


class PhoneAlreadyExistsError(AlreadyExistsError):
    """Raised when a telephone number is already registered."""
    status_code = 409
    error_code = "phone_already_exists"

    def __init__(self, message: str = "Phone already exists"):
        super().__init__(message)


# ==============================================================================
# CATEGORY 6: 500 SERVER & CONFIGURATION ERRORS
# ==============================================================================

class ServerError(AuthError):
    """Base exception for internal server, database, or infrastructure faults (HTTP 500)."""
    status_code = 500
    error_code = "server_error"


class DatabaseError(ServerError):
    """Raised when a relational database query or transaction fails."""
    status_code = 500
    error_code = "database_error"

    def __init__(self, message: str = "Database error occurred"):
        super().__init__(message)


class DatabaseIntegrityError(DatabaseError):
    """Raised on relational integrity constraint violations."""
    status_code = 409
    error_code = "database_integrity_error"

    def __init__(self, message: str = "Database integrity constraint violated"):
        super().__init__(message)


class DatabaseConnectionError(DatabaseError):
    """Raised when connection to PostgreSQL/SQLite fails or times out."""
    status_code = 500
    error_code = "database_connection_error"

    def __init__(self, message: str = "Failed to connect to database"):
        super().__init__(message)


class ConfigurationError(ServerError):
    """Base exception for missing or malformed subsystem configuration."""
    status_code = 500
    error_code = "configuration_error"


class InvalidConfigError(ConfigurationError, BadRequestError):
    """Raised when configuration parameters fail validation."""
    status_code = 400
    error_code = "invalid_config"

    def __init__(self, service: str, message: str | None = None):
        self.service = service
        msg = message or f"Invalid configuration for {service}"
        super().__init__(msg)


class CookieNotConfiguredError(ConfigurationError):
    """Raised when cookie operations are attempted but cookie subsystem is misconfigured."""
    status_code = 500
    error_code = "cookie_not_configured"

    def __init__(self, message: str = "Cookie service is not configured"):
        super().__init__(message)


class ServiceUnavailableError(ServerError):
    """Raised when an internal or external dependency is temporarily unreachable (HTTP 503)."""
    status_code = 503
    error_code = "service_unavailable"

    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(message)


# ==============================================================================
# CATEGORY 7: EXTERNAL SERVICES & INTEGRATIONS (EMAIL, OAUTH)
# ==============================================================================

class ExternalServiceError(AuthError):
    """Base exception for third-party communication failures (HTTP 502)."""
    status_code = 502
    error_code = "external_service_error"


# --- EMAIL SUBSYSTEM ERRORS ---

class EmailError(ExternalServiceError):
    """Base exception for email subsystem errors."""
    status_code = 500
    error_code = "email_error"

    def __init__(self, message: str = "Email error occurred"):
        super().__init__(message)


class EmailNotConfiguredError(EmailError, ConfigurationError):
    """Raised when email operations are attempted without configured SMTP credentials."""
    status_code = 500
    error_code = "email_not_configured"

    def __init__(self, message: str = "Email service is not configured"):
        super().__init__(message)


class EmailSendError(EmailError):
    """Raised when SMTP message delivery fails."""
    status_code = 502
    error_code = "email_send_failed"

    def __init__(self, message: str = "Failed to send email"):
        super().__init__(message)


class InvalidEmailPurposeError(EmailError, BadRequestError):
    """Raised when an unrecognized email OTP purpose string is requested."""
    status_code = 400
    error_code = "invalid_email_purpose"

    def __init__(self, purpose: str):
        self.purpose = purpose
        super().__init__(f"Invalid email OTP purpose: '{purpose}'")


# --- OAUTH SUBSYSTEM ERRORS ---

class OAuthError(AuthError):
    """Base exception for OAuth protocol and provider errors."""
    status_code = 400
    error_code = "oauth_error"

    def __init__(self, message: str = "OAuth error occurred"):
        super().__init__(message)


class OAuthNotConfiguredError(OAuthError, ConfigurationError):
    """Raised when an OAuth provider is called before client_id/secret configuration."""
    status_code = 500
    error_code = "oauth_not_configured"

    def __init__(self, provider: str = "OAuth", message: str | None = None):
        self.provider = provider
        msg = message or f"{provider} service is not configured"
        super().__init__(msg)


class UnsupportedOAuthProviderError(OAuthError, BadRequestError):
    """Raised when an unsupported provider name is specified in OAuth routes."""
    status_code = 400
    error_code = "unsupported_oauth_provider"

    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(f"Unsupported OAuth provider: '{provider}'")


class OAuthAlreadyLinkedError(OAuthError, ConflictError):
    """Raised when attempting to link an OAuth account that is already attached to a user."""
    status_code = 409
    error_code = "oauth_already_linked"

    def __init__(self, message: str = "OAuth account is already linked"):
        super().__init__(message)


class OAuthLinkNotFoundError(OAuthError, NotFoundError):
    """Raised when an expected OAuth provider link cannot be found for an account."""
    status_code = 404
    error_code = "oauth_link_not_found"

    def __init__(self, message: str = "OAuth account link not found"):
        super().__init__(message)


class OAuthCallbackError(OAuthError):
    """Raised when provider authorization exchange or user profile retrieval fails."""
    status_code = 400
    error_code = "oauth_callback_failed"

    def __init__(self, message: str = "OAuth callback failed"):
        super().__init__(message)


class OAuthAuthenticationError(OAuthError, AuthenticationError):
    """Raised when an OAuth user cannot be authenticated or account creation fails."""
    status_code = 401
    error_code = "oauth_authentication_failed"

    def __init__(self, message: str = "OAuth authentication failed"):
        super().__init__(message)


class OAuthUnlinkLockoutError(OAuthError, BadRequestError):
    """Raised when unlinking an OAuth provider would leave the user with zero auth methods."""
    status_code = 400
    error_code = "oauth_unlink_lockout"

    def __init__(
        self,
        message: str = "Cannot unlink provider: account must have a password or at least one other active authentication method",
    ):
        super().__init__(message)


class OAuthProviderError(OAuthError, ExternalServiceError):
    """Raised when an external OAuth provider API returns a 5xx error or connection fails."""
    status_code = 502
    error_code = "oauth_provider_error"

    def __init__(self, provider: str, message: str | None = None):
        self.provider = provider
        msg = message or f"External {provider} provider returned an error"
        super().__init__(msg)


# ==============================================================================
# CATEGORY 8: LOGGING SUBSYSTEM ERRORS
# ==============================================================================

class LoggingError(AuthError):
    """Base exception for logging subsystem errors."""
    status_code = 500
    error_code = "logging_error"


class LoggingNotConfiguredError(LoggingError, ConfigurationError):
    """Raised when logging operations are requested before initialization."""
    status_code = 500
    error_code = "logging_not_configured"

    def __init__(self, message: str = "Logging service is not configured"):
        super().__init__(message)


class LogSourceInvalidError(LoggingError, BadRequestError):
    """Raised when an invalid log source is specified (only 'tcauth' or 'server' are allowed)."""
    status_code = 422
    error_code = "invalid_log_source"

    def __init__(self, source: str, message: str | None = None):
        self.source = source
        msg = message or f"Invalid log source '{source}'. Must be 'tcauth' or 'server'."
        super().__init__(msg)


class LogUnsafeNameError(LoggingError, BadRequestError):
    """Raised when a snapshot name contains forbidden characters, separators, or path traversal elements."""
    status_code = 422
    error_code = "invalid_log_name"

    def __init__(self, name: str, message: str | None = None):
        self.name = name
        msg = message or f"Invalid log snapshot name '{name}'. Name must be alphanumeric with hyphens/underscores."
        super().__init__(msg)


class LogSnapshotNotFoundError(LoggingError, NotFoundError):
    """Raised when a requested snapshot file cannot be found in logs/store/."""
    status_code = 404
    error_code = "log_snapshot_not_found"

    def __init__(self, name: str, message: str | None = None):
        self.name = name
        msg = message or f"Log snapshot '{name}' not found"
        super().__init__(msg)


class LogSnapshotAlreadyExistsError(LoggingError, ConflictError):
    """Raised when attempting to create a snapshot that already exists."""
    status_code = 409
    error_code = "log_snapshot_already_exists"

    def __init__(self, name: str, message: str | None = None):
        self.name = name
        msg = message or f"Log snapshot '{name}' already exists"
        super().__init__(msg)


class LogCannotDeletePrimaryError(LoggingError, PermissionDeniedError):
    """Raised when attempting to delete a primary log (tcauth or server)."""
    status_code = 403
    error_code = "log_cannot_delete_primary"

    def __init__(self, source: str, message: str | None = None):
        self.source = source
        msg = message or f"Cannot delete primary log '{source}'. Only stored snapshots can be deleted."
        super().__init__(current=source, field="log_source", message=msg)