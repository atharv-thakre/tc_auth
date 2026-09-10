from datetime import UTC, datetime, timedelta
import secrets
from sqlalchemy.exc import IntegrityError

from ..utils.get_helper import to_list_dict
from ..jwt_handler import SESSION_DURATION_DAYS
from ..db.models import Session
from ..utils.get_helper import to_dict
from ..utils.hasher import simple_hash
from ..exceptions.error import (
    SessionNotFoundError,
    UserNotFoundError,
    InvalidFieldError,
    DatabaseError,
)


class SessionService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    _QUERY_FIELDS = {
        "id": Session.account_id,
        "sid": Session.id,
        "token": Session.token_hash,
        "ip": Session.ip_address,
    }

    def _get_session(
        self,
        db,
        session_id: int,
    ):
        try:
            parsed_id = int(session_id)
        except (ValueError, TypeError):
            raise SessionNotFoundError("id", session_id)

        session = (
            db.query(Session)
            .filter(Session.id == parsed_id)
            .first()
        )

        if session is None:
            raise SessionNotFoundError("id", session_id)

        return session

    def create_session(
        self,
        account_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        token = secrets.token_urlsafe(48)

        with self.session_factory() as db:
            session = Session(
                account_id=account_id,
                token_hash=simple_hash(token),
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=datetime.now(UTC)
                + timedelta(days=SESSION_DURATION_DAYS),
            )

            try:
                db.add(session)
                db.commit()
                db.refresh(session)
            except IntegrityError:
                db.rollback()
                raise UserNotFoundError("id", account_id)
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to create session: {str(e)}")

            return {
                "session_id": session.id,
                "token": token,
            }

    def by_id(
        self,
        session_id: int,
    ):
        with self.session_factory() as db:
            session = self._get_session(db, session_id)
            return to_dict(session)

    def by_account(
        self,
        account_id: int,
    ):
        with self.session_factory() as db:
            sessions = (
                db.query(Session)
                .filter(Session.account_id == account_id)
                .order_by(Session.created_at.desc())
                .all()
            )

            return [
                to_dict(session)
                for session in sessions
            ]

    def destroy_session(
        self,
        session_id: int,
    ):
        with self.session_factory() as db:
            session = self._get_session(db, session_id)
            try:
                db.delete(session)
                db.commit()
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to destroy session: {str(e)}")

    def destroy_all(
        self,
        account_id: int,
    ):
        with self.session_factory() as db:
            try:
                (
                    db.query(Session)
                    .filter(Session.account_id == account_id)
                    .delete(synchronize_session=False)
                )
                db.commit()
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to destroy all sessions: {str(e)}")

    def cleanup_expired(self):
        with self.session_factory() as db:
            try:
                (
                    db.query(Session)
                    .filter(
                        Session.expires_at < datetime.now(UTC)
                    )
                    .delete(synchronize_session=False)
                )
                db.commit()
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to cleanup expired sessions: {str(e)}")

    def get_all(self, page: int = 1, limit: int = 10):
        with self.session_factory() as db:
            page = max(1, page)
            limit = max(1, limit)
            offset = (page - 1) * limit

            sessions = (
                db.query(Session)
                .order_by(Session.id.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            return to_list_dict(sessions)

    def query(self, field: str, value: str):
        column = self._QUERY_FIELDS.get(field)

        if column is None:
            raise InvalidFieldError(
                field,
                f"Invalid query field: '{field}'. Supported fields: {list(self._QUERY_FIELDS.keys())}",
            )

        with self.session_factory() as db:
            if field in ("id", "sid"):
                try:
                    parsed_value = int(value)
                except (ValueError, TypeError):
                    raise InvalidFieldError(field, f"Field '{field}' must be an integer")

                sessions = (
                    db.query(Session)
                    .filter(column == parsed_value)
                    .all()
                )

            else:
                sessions = (
                    db.query(Session)
                    .filter(column.ilike(f"%{value}%"))
                    .all()
                )

            return to_list_dict(sessions)

    def clear_all(self):
        with self.session_factory() as db:
            try:
                db.query(Session).delete(synchronize_session=False)
                db.commit()
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to clear sessions: {str(e)}")
