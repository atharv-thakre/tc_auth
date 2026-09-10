from sqlalchemy.exc import IntegrityError
from uuid import UUID

from ..utils.hasher import hash_password
from ..utils.get_helper import to_list_dict
from ..db.models import Account
from ..exceptions.error import (
    EmailAlreadyExistsError,
    HandleAlreadyExistsError,
    PhoneAlreadyExistsError,
    UserNotFoundError,
    InvalidFieldError,
    DatabaseError,
)


class AccountService:
    def __init__(self, session_factory, get_user):
        self.session_factory = session_factory
        self.get_user = get_user

    # ==========================================================
    # PRIVATE
    # ==========================================================

    _QUERY_FIELDS = {
        "id": Account.id,
        "uid": Account.uid,
        "phone": Account.phone,
        "email": Account.email,
        "name": Account.name,
        "handle": Account.handle,
    }

    # ===========================Internal Helpers===========================
    # GET ACCOUNT BY ID & UserNotFoundError HANDLER

    def _get_account(
        self,
        db,
        account_id: int,
    ):
        try:
            parsed_id = int(account_id)
        except (ValueError, TypeError):
            raise UserNotFoundError("id", account_id)

        account = (
            db.query(Account)
            .filter(Account.id == parsed_id)
            .first()
        )

        if account is None:
            raise UserNotFoundError("id", account_id)

        return account

    # HANDLE INTEGRITY ERROR & ROLLBACK SESSION

    def _handle_integrity_error(
        self,
        db,
        error: IntegrityError,
    ):
        db.rollback()

        message = str(error.orig) if error.orig else str(error)
        msg_lower = message.lower()

        if (
            "uq_accounts_email" in msg_lower
            or "accounts.email" in msg_lower
            or ("unique" in msg_lower and "email" in msg_lower)
        ):
            raise EmailAlreadyExistsError()

        if (
            "uq_accounts_handle" in msg_lower
            or "accounts.handle" in msg_lower
            or ("unique" in msg_lower and "handle" in msg_lower)
        ):
            raise HandleAlreadyExistsError()

        if (
            "uq_accounts_phone" in msg_lower
            or "accounts.phone" in msg_lower
            or ("unique" in msg_lower and "phone" in msg_lower)
        ):
            raise PhoneAlreadyExistsError()

        raise DatabaseError(f"Database integrity error: {message}")

    # =============================Public Methods===========================
    # CREATE USER

    def create_user(
        self,
        name: str | None = None,
        email: str | None = None,
        password: str | None = None,
        handle: str | None = None,
        avatar_url: str | None = None,
        phone: str | None = None,
        role: str | None = None,
        status: str | None = None,
    ):
        with self.session_factory() as db:
            account = Account()

            if name is not None:
                account.name = name

            if email is not None:
                account.email = email

            if password is not None:
                account.password_hash = hash_password(password)

            if handle is not None:
                account.handle = handle

            if avatar_url is not None:
                account.avatar_url = avatar_url

            if phone is not None:
                account.phone = phone

            if role is not None:
                account.role = role

            if status is not None:
                account.status = status

            try:
                db.add(account)
                db.commit()
                db.refresh(account)
            except IntegrityError as e:
                self._handle_integrity_error(db, e)
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to create account: {str(e)}")

            return self.get_user.by_id(account.id)

    # UPDATE USER

    def update_user(
        self,
        account_id: int,
        *,
        name: str | None = None,
        email: str | None = None,
        handle: str | None = None,
        avatar_url: str | None = None,
        phone: str | None = None,
    ):
        with self.session_factory() as db:
            account = self._get_account(db, account_id)

            if name is not None:
                account.name = name

            if email is not None:
                account.email = email

            if handle is not None:
                account.handle = handle

            if avatar_url is not None:
                account.avatar_url = avatar_url

            if phone is not None:
                account.phone = phone

            try:
                db.commit()
                db.refresh(account)
            except IntegrityError as e:
                self._handle_integrity_error(db, e)
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to update account: {str(e)}")

            return self.get_user.by_id(account.id)

    # DELETE ACCOUNT

    def delete_user(
        self,
        account_id: int,
    ):
        with self.session_factory() as db:
            account = self._get_account(db, account_id)
            try:
                db.delete(account)
                db.commit()
                return {"success": True, "message": "Account deleted successfully"}
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to delete account: {str(e)}")

    # CHANGE PASSWORD

    def update_password(
        self,
        account_id: int,
        password: str,
    ):
        if not password or not isinstance(password, str):
            raise InvalidFieldError("password", "Password cannot be empty")

        with self.session_factory() as db:
            account = self._get_account(db, account_id)
            account.password_hash = hash_password(password)
            try:
                db.commit()
                return {"success": True, "message": "Password updated successfully"}
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to update password: {str(e)}")

    # CHANGE ROLE

    def update_role(
        self,
        account_id: int,
        role: str,
    ):
        if not role or not isinstance(role, str):
            raise InvalidFieldError("role", "Role cannot be empty")

        with self.session_factory() as db:
            account = self._get_account(db, account_id)
            account.role = role
            try:
                db.commit()
                return {"success": True, "message": "Role updated successfully"}
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to update role: {str(e)}")

    # CHANGE STATUS

    def update_status(
        self,
        account_id: int,
        status: str | None,
    ):
        with self.session_factory() as db:
            account = self._get_account(db, account_id)
            account.status = status
            try:
                db.commit()
                return {"success": True, "message": "Status updated successfully"}
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to update status: {str(e)}")

    # SUPER UPDATE USER

    def super_update(
        self,
        account_id: int,
        *,
        name: str | None = None,
        email: str | None = None,
        handle: str | None = None,
        avatar_url: str | None = None,
        phone: str | None = None,
        role: str | None = None,
        status: str | None = None,
        password: str | None = None,
    ):
        with self.session_factory() as db:
            account = self._get_account(db, account_id)

            if name is not None:
                account.name = name

            if email is not None:
                account.email = email

            if handle is not None:
                account.handle = handle

            if avatar_url is not None:
                account.avatar_url = avatar_url

            if phone is not None:
                account.phone = phone

            if role is not None:
                account.role = role

            if status is not None:
                account.status = status

            if password is not None:
                account.password_hash = hash_password(password)

            try:
                db.commit()
                db.refresh(account)
            except IntegrityError as e:
                self._handle_integrity_error(db, e)
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to super update account: {str(e)}")

            return self.get_user.by_id(account.id)

    def get_all(self, page: int = 1, limit: int = 10):
        with self.session_factory() as db:
            page = max(1, page)
            limit = max(1, limit)
            offset = (page - 1) * limit

            accounts = (
                db.query(Account)
                .order_by(Account.id.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            return to_list_dict(accounts)

    def query(self, field: str, value: str):
        column = self._QUERY_FIELDS.get(field)

        if column is None:
            raise InvalidFieldError(
                field,
                f"Invalid query field: '{field}'. Supported fields: {list(self._QUERY_FIELDS.keys())}",
            )

        with self.session_factory() as db:
            if field == "id":
                try:
                    parsed_value = int(value)
                except (ValueError, TypeError):
                    raise InvalidFieldError("id", "Field 'id' must be an integer")

                accounts = (
                    db.query(Account)
                    .filter(Account.id == parsed_value)
                    .all()
                )

            elif field == "uid":
                try:
                    parsed_value = UUID(str(value))
                except (ValueError, TypeError):
                    raise InvalidFieldError("uid", "Field 'uid' must be a valid UUID")

                accounts = (
                    db.query(Account)
                    .filter(Account.uid == parsed_value)
                    .all()
                )

            else:
                accounts = (
                    db.query(Account)
                    .filter(column.ilike(f"%{value}%"))
                    .all()
                )

            return to_list_dict(accounts)