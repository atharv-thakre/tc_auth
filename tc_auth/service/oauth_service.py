from sqlalchemy.exc import IntegrityError
from ..db.models import OAuthAccount
from ..utils.get_helper import to_list_dict, to_dict
from ..exceptions.error import (
    AuthError,
    UserNotFoundError,
    OAuthAlreadyLinkedError,
    OAuthLinkNotFoundError,
    InvalidFieldError,
    DatabaseError,
)


class OAuthService:
    def __init__(
        self,
        get_user,
        session_factory,
        account,
        auth_service,
    ):
        self.get_user = get_user
        self.session_factory = session_factory
        self.account = account
        self.auth_service = auth_service

    # ==========================================================
    # LOGIN
    # ==========================================================

    def login(
        self,
        *,
        provider: str,
        provider_user_id: str,
        name: str | None = None,
        email: str | None = None,
        avatar_url: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        if not provider or not provider_user_id:
            raise AuthError("Provider and provider_user_id are required for OAuth login")

        oauth = self.find_oauth(
            provider=provider,
            provider_user_id=provider_user_id,
        )

        if oauth is not None:
            try:
                account = self.get_user.by_id(oauth.account_id)
            except UserNotFoundError:
                account = self._find_or_create_account(
                    provider=provider,
                    provider_user_id=provider_user_id,
                    name=name,
                    email=email,
                    avatar_url=avatar_url,
                )
        else:
            account = self._find_or_create_account(
                provider=provider,
                provider_user_id=provider_user_id,
                name=name,
                email=email,
                avatar_url=avatar_url,
            )

        if not account:
            raise AuthError("Unable to retrieve or create account for OAuth login")

        result = self.auth_service.create_login_response(
            account=account,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return result

    # ==========================================================
    # PRIVATE
    # ==========================================================
    _QUERY_FIELDS = {
        "id": OAuthAccount.id,
        "provider_id": OAuthAccount.provider_user_id,
        "account_id": OAuthAccount.account_id,
    }

    def _find_or_create_account(
        self,
        *,
        provider: str,
        provider_user_id: str,
        name: str | None,
        email: str | None,
        avatar_url: str | None,
    ):
        account = None

        if email is not None:
            account = self.get_user.find_by_email(email)

        if account is None:
            account = self.account.create_user(
                name=name,
                email=email,
                avatar_url=avatar_url,
            )
        else:
            self._initialize_profile(
                account=account,
                name=name,
                email=email,
                avatar_url=avatar_url,
            )

        self.link_account(
            account_id=account["id"],
            provider=provider,
            provider_user_id=provider_user_id,
        )

        return account

    def _initialize_profile(
        self,
        *,
        account: dict,
        name: str | None,
        email: str | None,
        avatar_url: str | None,
    ):
        updates = {}

        if account.get("name") is None and name is not None:
            updates["name"] = name

        if account.get("email") is None and email is not None:
            updates["email"] = email

        if account.get("avatar_url") is None and avatar_url is not None:
            updates["avatar_url"] = avatar_url

        if updates:
            self.account.update_user(
                account["id"],
                **updates,
            )

    # ==========================================================
    # OAUTH LINKS
    # ==========================================================

    def find_oauth(
        self,
        *,
        provider: str,
        provider_user_id: str,
    ):
        with self.session_factory() as db:
            return (
                db.query(OAuthAccount)
                .filter_by(
                    provider=provider,
                    provider_user_id=provider_user_id,
                )
                .first()
            )

    def link_account(
        self,
        *,
        account_id: int,
        provider: str,
        provider_user_id: str,
    ):
        if not provider or not provider_user_id:
            raise AuthError("Provider and provider_user_id are required")

        with self.session_factory() as db:
            oauth = OAuthAccount(
                account_id=account_id,
                provider=provider,
                provider_user_id=provider_user_id,
            )

            try:
                db.add(oauth)
                db.commit()
                db.refresh(oauth)
            except IntegrityError as e:
                db.rollback()
                msg = str(e.orig).lower() if e.orig else str(e).lower()
                if "uq_oauth_provider_user" in msg or "uq_account_provider" in msg or "unique" in msg:
                    raise OAuthAlreadyLinkedError(f"OAuth account for '{provider}' is already linked")
                if "account_id" in msg or "foreign key" in msg:
                    raise UserNotFoundError("id", account_id)
                raise DatabaseError(f"Failed to link OAuth account: {msg}")
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to link OAuth account: {str(e)}")

            return to_dict(oauth)

    def unlink_account(
        self,
        *,
        account_id: int,
        provider: str,
    ):
        with self.session_factory() as db:
            try:
                deleted_count = (
                    db.query(OAuthAccount)
                    .filter_by(
                        account_id=account_id,
                        provider=provider,
                    )
                    .delete()
                )
                db.commit()

                if deleted_count == 0:
                    raise OAuthLinkNotFoundError(
                        f"No OAuth link found for account {account_id} with provider '{provider}'"
                    )
            except (OAuthLinkNotFoundError, AuthError):
                raise
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to unlink OAuth account: {str(e)}")

    def get_all(self, page: int = 1, limit: int = 10):
        with self.session_factory() as db:
            page = max(1, page)
            limit = max(1, limit)
            offset = (page - 1) * limit

            oauth_links = (
                db.query(OAuthAccount)
                .order_by(OAuthAccount.id.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            return to_list_dict(oauth_links)

    def query(self, field: str, value: str):
        column = self._QUERY_FIELDS.get(field)

        if column is None:
            raise InvalidFieldError(
                field,
                f"Invalid query field: '{field}'. Supported fields: {list(self._QUERY_FIELDS.keys())}",
            )

        if field in ["id", "account_id"]:
            try:
                parsed_value = int(value)
            except (ValueError, TypeError):
                raise InvalidFieldError(field, f"Field '{field}' must be an integer")
        else:
            parsed_value = value

        with self.session_factory() as db:
            oauth_records = (
                db.query(OAuthAccount)
                .filter(column == parsed_value)
                .all()
            )

            return to_list_dict(oauth_records)