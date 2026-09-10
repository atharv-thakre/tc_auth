from uuid import UUID
from ..db.models import Account
from ..utils.get_helper import to_dict
from ..exceptions.error import UserNotFoundError


class GetUserService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    # ==========================================================
    # PRIVATE
    # ==========================================================

    _QUERY_FIELDS = {
        "id": Account.id,
        "uid": Account.uid,
        "phone": Account.phone,
        "email": Account.email,
        "handle": Account.handle,
    }

    def _get_by(
        self,
        column,
        value,
        include_password: bool = False,
    ):
        if value is None:
            raise UserNotFoundError(field=column.key, value=None)

        with self.session_factory() as db:
            account = (
                db.query(Account)
                .filter(column == value)
                .first()
            )

            if account is None:
                raise UserNotFoundError(field=column.key, value=value)

            exclude = [] if include_password else ["password_hash"]
            return to_dict(account, exclude=exclude)

    # ==========================================================
    # PUBLIC
    # ==========================================================

    def by_id(
        self,
        account_id: int,
        include_password: bool = False,
    ):
        try:
            parsed_id = int(account_id)
        except (ValueError, TypeError):
            raise UserNotFoundError("id", account_id)

        return self._get_by(
            Account.id,
            parsed_id,
            include_password,
        )

    def by_uid(
        self,
        uid: str,
        include_password: bool = False,
    ):
        try:
            parsed_uid = UUID(str(uid))
        except (ValueError, TypeError):
            raise UserNotFoundError("uid", uid)

        return self._get_by(
            Account.uid,
            parsed_uid,
            include_password,
        )

    def by_email(
        self,
        email: str,
        include_password: bool = False,
    ):
        if not email or not isinstance(email, str) or not email.strip():
            raise UserNotFoundError("email", email)

        return self._get_by(
            Account.email,
            email.strip(),
            include_password,
        )

    def by_handle(
        self,
        handle: str,
        include_password: bool = False,
    ):
        if not handle or not isinstance(handle, str) or not handle.strip():
            raise UserNotFoundError("handle", handle)

        return self._get_by(
            Account.handle,
            handle.strip(),
            include_password,
        )

    def by_phone(
        self,
        phone: str,
        include_password: bool = False,
    ):
        if not phone or not isinstance(phone, str) or not phone.strip():
            raise UserNotFoundError("phone", phone)

        return self._get_by(
            Account.phone,
            phone.strip(),
            include_password,
        )

    def find_by_email(
        self,
        email: str,
        include_password: bool = False,
    ):
        if not email or not isinstance(email, str) or not email.strip():
            return None

        with self.session_factory() as db:
            account = (
                db.query(Account)
                .filter(Account.email == email.strip())
                .first()
            )

            if account is None:
                return None

            exclude = [] if include_password else ["password_hash"]
            return to_dict(account, exclude=exclude)