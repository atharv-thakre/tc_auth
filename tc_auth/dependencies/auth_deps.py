from datetime import UTC, datetime

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..exceptions.error import (
    InvalidTokenError,
    TokenMissingError,
    TokenMalformedError,
    TokenSignatureError,
    TokenRevokedError,
    SessionExpiredError,
    SessionNotFoundError,
    UserNotFoundError,
)
from ..jwt_handler import verify_token
from ..utils.hasher import verify_hash

security_jwt = HTTPBearer(auto_error=False)


class AuthDeps:
    def __init__(self, get_user, session, cookie_service=None):
        self.get_user = get_user
        self.session = session
        self.cookie_service = cookie_service

    # ==========================================================
    # PRIVATE
    # ==========================================================

    def _authenticate(
        self,
        token: str,
    ):
        payload = verify_token(token)

        if not isinstance(payload, dict):
            raise TokenMalformedError("Invalid token payload")

        if payload.get("type") == "refresh":
            raise TokenMalformedError("Refresh token cannot be used as an access token")

        sid = payload.get("sid")
        aid = payload.get("aid")
        token_secret = payload.get("token")

        if sid is None or aid is None or token_secret is None:
            raise TokenMalformedError("Incomplete token claims")

        try:
            session = self.session.by_id(sid)
        except Exception:
            raise TokenRevokedError("Session not found or revoked")

        if session is None:
            raise TokenRevokedError("Session not found or revoked")

        if session.get("account_id") != aid:
            raise TokenRevokedError("Invalid session for account")

        expires_at_val = session.get("expires_at")
        if not expires_at_val:
            raise SessionExpiredError("Session has expired")

        if isinstance(expires_at_val, str):
            try:
                expires_at = datetime.fromisoformat(expires_at_val)
            except Exception:
                raise SessionExpiredError("Session has expired")
        elif isinstance(expires_at_val, datetime):
            expires_at = expires_at_val
        else:
            raise SessionExpiredError("Session has expired")

        now = datetime.now(UTC) if expires_at.tzinfo is not None else datetime.now()
        if expires_at < now:
            raise SessionExpiredError("Session has expired")

        token_hash = session.get("token_hash")
        if not token_hash or not verify_hash(token_secret, token_hash):
            raise TokenSignatureError("Invalid token secret")

        return payload, session

    # ==========================================================
    # CURRENT
    # ==========================================================

    def get_current(
        self,
        credentials: str,
    ):
        if not credentials or not isinstance(credentials, str) or not credentials.strip():
            raise TokenMissingError("Missing authorization credentials")

        payload, session = self._authenticate(
            credentials.strip()
        )

        try:
            account = self.get_user.by_id(
                payload["aid"]
            )
        except Exception:
            raise UserNotFoundError("id", payload["aid"])

        if not account:
            raise UserNotFoundError("id", payload["aid"])

        return {
            "account": account,
            "session": session,
            "payload": payload,
        }

    # ==========================================================
    # FASTAPI DEPENDENCIES
    # ==========================================================

    def get_current_user(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(security_jwt),
    ):
        token = None
        if credentials and credentials.credentials:
            token = credentials.credentials
        elif self.cookie_service and self.cookie_service.is_cookie_mode():
            token = self.cookie_service.extract_access_token(request)
        elif request.cookies.get("access_token"):
            token = request.cookies.get("access_token")

        if not token:
            raise TokenMissingError("Missing authorization credentials")

        return self.get_current(token)

    def get_current_account(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(security_jwt),
    ):
        current = self.get_current_user(request=request, credentials=credentials)
        return current["account"]

    def get_current_session(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(security_jwt),
    ):
        current = self.get_current_user(request=request, credentials=credentials)
        return current["session"]

    def get_current_payload(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(security_jwt),
    ):
        current = self.get_current_user(request=request, credentials=credentials)
        return current["payload"]