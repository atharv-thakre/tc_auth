from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from ..db.models import OAuthAccount, Account
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
        norm_provider = str(provider).strip().lower() if provider else ""
        norm_uid = str(provider_user_id).strip() if provider_user_id else ""

        if not norm_provider or not norm_uid:
            raise AuthError("Provider and provider_user_id are required for OAuth login")

        clean_name = name.strip() if name and isinstance(name, str) and name.strip() else None
        clean_email = email.strip() if email and isinstance(email, str) and email.strip() else None
        clean_avatar = avatar_url.strip() if avatar_url and isinstance(avatar_url, str) and avatar_url.strip() else None

        oauth = self.find_oauth(
            provider=norm_provider,
            provider_user_id=norm_uid,
        )

        if oauth is not None:
            try:
                account = self.get_user.by_id(oauth.account_id)
                self._initialize_profile(
                    provider=norm_provider,
                    account=account,
                    name=clean_name,
                    email=clean_email,
                    avatar_url=clean_avatar,
                )
                account = self.get_user.by_id(oauth.account_id)
            except UserNotFoundError:
                account = self._find_or_create_account(
                    provider=norm_provider,
                    provider_user_id=norm_uid,
                    name=clean_name,
                    email=clean_email,
                    avatar_url=clean_avatar,
                )
        else:
            account = self._find_or_create_account(
                provider=norm_provider,
                provider_user_id=norm_uid,
                name=clean_name,
                email=clean_email,
                avatar_url=clean_avatar,
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
        norm_provider = str(provider).strip().lower()
        norm_uid = str(provider_user_id).strip()
        clean_email = email.strip() if email and isinstance(email, str) and email.strip() else None
        clean_name = name.strip() if name and isinstance(name, str) and name.strip() else None
        clean_avatar = avatar_url.strip() if avatar_url and isinstance(avatar_url, str) and avatar_url.strip() else None

        account = None

        # Direct linking on login/signup based on email
        if clean_email is not None:
            account = self.get_user.find_by_email(clean_email)

        if account is None:
            account = self.account.create_user(
                name=clean_name,
                email=clean_email,
                avatar_url=clean_avatar,
            )
        else:
            self._initialize_profile(
                provider=norm_provider,
                account=account,
                name=clean_name,
                email=clean_email,
                avatar_url=clean_avatar,
            )
            account = self.get_user.by_id(account["id"])

        self.link_account(
            account_id=account["id"],
            provider=norm_provider,
            provider_user_id=norm_uid,
        )

        return account

    def _initialize_profile(
        self,
        *,
        provider: str | None = None,
        account: dict,
        name: str | None,
        email: str | None,
        avatar_url: str | None,
    ):
        updates = {}

        existing_name = account.get("name")
        is_name_empty = not existing_name or not str(existing_name).strip()

        existing_avatar = account.get("avatar_url")
        is_avatar_empty = not existing_avatar or not str(existing_avatar).strip()

        existing_email = account.get("email")
        is_email_empty = not existing_email or not str(existing_email).strip()

        clean_name = name.strip() if name and isinstance(name, str) and name.strip() else None
        clean_avatar = avatar_url.strip() if avatar_url and isinstance(avatar_url, str) and avatar_url.strip() else None
        clean_email = email.strip() if email and isinstance(email, str) and email.strip() else None

        # 1. NAME: If existing field is empty (None or ""), all 3 providers can set it
        if is_name_empty and clean_name:
            updates["name"] = clean_name

        # 2. AVATAR URL: If existing field is empty (None or ""), all 3 providers can set it
        if is_avatar_empty and clean_avatar:
            updates["avatar_url"] = clean_avatar

        # 3. EMAIL:
        # If existing email is empty (None or ""), ALL 3 providers can set it!
        # If existing email is already present (non-empty):
        # ONLY Google OAuth is permitted to overwrite it.
        # GitHub and Discord must NOT overwrite non-empty email.
        if clean_email:
            if is_email_empty:
                updates["email"] = clean_email
            elif provider and provider.lower() == "google":
                if str(existing_email).strip().lower() != clean_email.lower():
                    updates["email"] = clean_email

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
        norm_provider = str(provider).strip().lower()
        norm_uid = str(provider_user_id).strip()
        with self.session_factory() as db:
            return (
                db.query(OAuthAccount)
                .filter(
                    func.lower(OAuthAccount.provider) == norm_provider,
                    OAuthAccount.provider_user_id == norm_uid,
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
        norm_provider = str(provider).strip().lower()
        norm_uid = str(provider_user_id).strip()

        if not norm_provider or not norm_uid:
            raise AuthError("Provider and provider_user_id are required")

        with self.session_factory() as db:
            account = db.query(Account).filter_by(id=account_id).first()
            if not account:
                raise UserNotFoundError("id", account_id)

            # Check if this account already has this provider linked
            existing_for_account = (
                db.query(OAuthAccount)
                .filter(
                    OAuthAccount.account_id == account_id,
                    func.lower(OAuthAccount.provider) == norm_provider,
                )
                .first()
            )
            if existing_for_account:
                if existing_for_account.provider_user_id == norm_uid:
                    return to_dict(existing_for_account)
                raise OAuthAlreadyLinkedError(
                    f"Account is already linked to a different '{norm_provider}' account"
                )

            # Check if this provider_user_id is already linked to another account
            existing_for_user = (
                db.query(OAuthAccount)
                .filter(
                    func.lower(OAuthAccount.provider) == norm_provider,
                    OAuthAccount.provider_user_id == norm_uid,
                )
                .first()
            )
            if existing_for_user:
                raise OAuthAlreadyLinkedError(
                    f"OAuth account for '{norm_provider}' is already linked to another user profile"
                )

            oauth = OAuthAccount(
                account_id=account_id,
                provider=norm_provider,
                provider_user_id=norm_uid,
            )

            try:
                db.add(oauth)
                db.commit()
                db.refresh(oauth)
            except IntegrityError as e:
                db.rollback()
                msg = str(e.orig).lower() if e.orig else str(e).lower()
                if "uq_oauth_provider_user" in msg or "uq_account_provider" in msg or "unique" in msg:
                    raise OAuthAlreadyLinkedError(f"OAuth account for '{norm_provider}' is already linked")
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
        enforce_active_auth: bool = False,
    ):
        norm_provider = str(provider).strip().lower()
        with self.session_factory() as db:
            account = db.query(Account).filter_by(id=account_id).first()
            if not account:
                raise UserNotFoundError("id", account_id)

            links = (
                db.query(OAuthAccount)
                .filter_by(account_id=account_id)
                .all()
            )

            target = next((l for l in links if l.provider.lower() == norm_provider), None)
            if not target:
                raise OAuthLinkNotFoundError(
                    f"No OAuth link found for account {account_id} with provider '{norm_provider}'"
                )

            if enforce_active_auth:
                has_password = bool(account.password_hash and str(account.password_hash).strip())
                other_links = [l for l in links if l.provider.lower() != norm_provider]
                if not has_password and len(other_links) == 0:
                    raise AuthError(
                        "Cannot unlink provider: account must have a password or at least one other active authentication method"
                    )

            db.delete(target)
            db.commit()
            return {
                "success": True,
                "message": f"OAuth link for '{norm_provider}' removed successfully",
            }

    def get_account_links(self, account_id: int):
        with self.session_factory() as db:
            links = (
                db.query(OAuthAccount)
                .filter_by(account_id=account_id)
                .order_by(OAuthAccount.id.asc())
                .all()
            )
            return [to_dict(link) for link in links]

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