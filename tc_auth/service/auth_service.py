from datetime import UTC, datetime
from .. import jwt_handler
from ..jwt_handler import create_access_token, create_refresh_token, verify_token
from ..utils.hasher import verify_password, verify_hash
from ..utils.identifier import (
    normalize_identifier,
    get_identifier_type,
)
from ..exceptions.error import (
    AuthError,
    InvalidCredentialsError,
    UserNotFoundError,
    InvalidTokenError,
)


class AuthService:
    def __init__(
        self,
        get_user,
        account,
        session,
        otp=None,
    ):
        self.get_user = get_user
        self.account = account
        self.session = session
        self.otp = otp

    def _authenticate(
        self,
        identifier: str,
        password: str,
    ):
        if not identifier or not isinstance(identifier, str):
            raise InvalidCredentialsError()

        if not password or not isinstance(password, str):
            raise InvalidCredentialsError()

        identifier = normalize_identifier(identifier)

        try:
            if get_identifier_type(identifier) == "email":
                account = self.get_user.by_email(
                    identifier,
                    include_password=True,
                )
            else:
                account = self.get_user.by_handle(
                    identifier,
                    include_password=True,
                )

        except UserNotFoundError:
            raise InvalidCredentialsError()

        password_hash = account.get("password_hash")
        if not password_hash:
            raise InvalidCredentialsError()

        if not verify_password(
            password,
            password_hash,
        ):
            raise InvalidCredentialsError()

        account.pop("password_hash", None)

        return account

    def create_login_response(
        self,
        account: dict,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        if not account or not isinstance(account, dict) or "id" not in account:
            raise AuthError("Invalid account data for login response")

        session = self.session.create_session(
            account_id=account["id"],
            ip_address=ip_address,
            user_agent=user_agent,
        )

        token_payload = {
            "aid": account["id"],
            "sid": session["session_id"],
            "token": session["token"],
        }

        access_token = create_access_token(token_payload)

        response = {
            "access_token": access_token,
            "token_type": "Bearer",
            "account": account,
        }

        if jwt_handler.is_dual_token_mode():
            response["refresh_token"] = create_refresh_token(token_payload)

        return response

    def refresh_tokens(
        self,
        refresh_token: str,
    ):
        if not refresh_token or not isinstance(refresh_token, str) or not refresh_token.strip():
            raise InvalidTokenError(field="refresh_token", message="Missing refresh token")

        payload = verify_token(refresh_token.strip())
        if not isinstance(payload, dict):
            raise InvalidTokenError(field="refresh_token", message="Invalid refresh token payload")

        if payload.get("type") != "refresh":
            raise InvalidTokenError(field="refresh_token", message="Provided token is not a refresh token")

        sid = payload.get("sid")
        aid = payload.get("aid")
        token_secret = payload.get("token")

        if sid is None or aid is None or token_secret is None:
            raise InvalidTokenError(field="refresh_token", message="Invalid refresh token payload")

        try:
            session = self.session.by_id(sid)
        except Exception:
            raise InvalidTokenError(field="session", message="Session not found or expired")

        if session is None or session.get("account_id") != aid:
            raise InvalidTokenError(field="session", message="Invalid session for this user")

        expires_at_val = session.get("expires_at")
        if not expires_at_val:
            raise InvalidTokenError(field="session", message="Session has expired")

        if isinstance(expires_at_val, str):
            try:
                expires_at = datetime.fromisoformat(expires_at_val)
            except Exception:
                raise InvalidTokenError(field="session", message="Session has expired")
        elif isinstance(expires_at_val, datetime):
            expires_at = expires_at_val
        else:
            raise InvalidTokenError(field="session", message="Session has expired")

        now = datetime.now(UTC) if expires_at.tzinfo is not None else datetime.now()
        if expires_at < now:
            raise InvalidTokenError(field="session", message="Session has expired")

        token_hash = session.get("token_hash")
        if not token_hash or not verify_hash(token_secret, token_hash):
            raise InvalidTokenError(field="refresh_token", message="Invalid refresh token secret")

        try:
            account = self.get_user.by_id(aid)
        except Exception:
            raise UserNotFoundError("id", aid)

        if not account:
            raise UserNotFoundError("id", aid)

        token_payload = {
            "aid": aid,
            "sid": sid,
            "token": token_secret,
        }

        new_access_token = create_access_token(token_payload)
        new_refresh_token = create_refresh_token(token_payload)

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer",
        }

    def signup(
        self,
        name: str,
        email: str,
        password: str,
        handle: str | None = None,
        phone: str | None = None,
        role: str | None = None,
        status: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        if not email or not password:
            raise AuthError("Email and password are required")

        account = self.account.create_user(
            name=name,
            email=email,
            password=password,
            handle=handle,
            phone=phone,
            role=role,
            status=status,
        )

        return self.create_login_response(
            account,
            ip_address,
            user_agent,
        )

    def login(
        self,
        identifier: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        account = self._authenticate(
            identifier,
            password,
        )

        return self.create_login_response(
            account,
            ip_address,
            user_agent,
        )

    def update_password(
        self,
        account_id: int,
        password: str,
    ):
        return self.account.update_password(
            account_id=account_id,
            password=password,
        )

    def login_magic_link(
        self,
        email: str,
        otp: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        if self.otp:
            self.otp.verify(
                identifier=email,
                purpose="login",
                otp=otp,
            )

        account = self.get_user.by_email(email=email)
        return self.create_login_response(
            account=account,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def verify_email_magic_link(
        self,
        email: str,
        otp: str,
    ):
        if self.otp:
            self.otp.verify(
                identifier=email,
                purpose="verify",
                otp=otp,
            )

        account = self.get_user.by_email(email=email)
        self.account.update_status(account["id"], "active")
        return {
            "success": True,
            "message": "Email verified successfully",
            "email": email,
        }