from ..jwt_handler import create_access_token
from ..utils.hasher import verify_password
from ..utils.identifier import (
    normalize_identifier,
    get_identifier_type,
)
from ..exceptions.error import (
    AuthError,
    InvalidCredentialsError,
    UserNotFoundError,
)


class AuthService:
    def __init__(
        self,
        get_user,
        account,
        session,
    ):
        self.get_user = get_user
        self.account = account
        self.session = session

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

        access_token = create_access_token(
            {
                "aid": account["id"],
                "sid": session["session_id"],
                "token": session["token"],
            }
        )

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "account": account,
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