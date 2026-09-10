from datetime import UTC, datetime

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..exceptions.error import InvalidTokenError
from ..jwt_handler import verify_token
from ..utils.hasher import verify_hash

security_jwt = HTTPBearer(auto_error=True)


class AuthDeps:
    def __init__(self, get_user, session):
        self.get_user = get_user
        self.session = session

    # ==========================================================
    # PRIVATE
    # ==========================================================

    def _authenticate(
        self,
        token: str,
    ):
        payload = verify_token(token)

        if not isinstance(payload, dict):
            raise InvalidTokenError(field="payload")

        sid = payload.get("sid")
        aid = payload.get("aid")
        token_secret = payload.get("token")

        if sid is None or aid is None or token_secret is None:
            raise InvalidTokenError(field="payload")

        try:
            session = self.session.by_id(sid)
        except Exception:
            raise InvalidTokenError(field="session")

        if session is None:
            raise InvalidTokenError(field="session")

        if session.get("account_id") != aid:
            raise InvalidTokenError(field="account_id")

        expires_at_val = session.get("expires_at")
        if not expires_at_val:
            raise InvalidTokenError(field="session")

        if isinstance(expires_at_val, str):
            try:
                expires_at = datetime.fromisoformat(expires_at_val)
            except Exception:
                raise InvalidTokenError(field="session")
        elif isinstance(expires_at_val, datetime):
            expires_at = expires_at_val
        else:
            raise InvalidTokenError(field="session")

        now = datetime.now(UTC) if expires_at.tzinfo is not None else datetime.now()
        if expires_at < now:
            raise InvalidTokenError(field="session", message="Session has expired")

        token_hash = session.get("token_hash")
        if not token_hash or not verify_hash(token_secret, token_hash):
            raise InvalidTokenError(field="token")

        return payload, session

    # ==========================================================
    # CURRENT
    # ==========================================================

    def get_current(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security_jwt),
    ):
        if not credentials or not credentials.credentials:
            raise InvalidTokenError(field="credentials", message="Missing authorization credentials")

        payload, session = self._authenticate(
            credentials.credentials
        )

        try:
            account = self.get_user.by_id(
                payload["aid"]
            )
        except Exception:
            raise InvalidTokenError(field="user", message="User account not found")

        if not account:
            raise InvalidTokenError(field="user", message="User account not found")

        return {
            "account": account,
            "session": session,
            "payload": payload,
        }

    # ==========================================================
    # HELPERS
    # ==========================================================

    def get_current_account(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security_jwt),
    ):
        current = self.get_current(credentials)
        return current["account"]

    def get_current_session(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security_jwt),
    ):
        current = self.get_current(credentials)
        return current["session"]

    def get_current_payload(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security_jwt),
    ):
        current = self.get_current(credentials)
        return current["payload"]