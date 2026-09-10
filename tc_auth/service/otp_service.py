import random
from datetime import datetime, timedelta
from ..utils.get_helper import to_list_dict
from ..db.models import OTP
from ..utils.hasher import simple_hash, verify_hash 
from ..exceptions.error import (
    AuthError,
    DatabaseError,
    OTPExpiredError,
    OTPInvalidError,
    OTPNotFoundError,
)


class OTPService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    # ==========================================================
    # CREATE
    # ==========================================================

    def create(
        self,
        *,
        identifier: str,
        purpose: str,
        expiry: int = 300,
        length: int = 6,
    ):
        if not identifier or not isinstance(identifier, str) or not identifier.strip():
            raise AuthError("OTP identifier is required")

        if not purpose or not isinstance(purpose, str) or not purpose.strip():
            raise AuthError("OTP purpose is required")

        if expiry < 1:
            raise AuthError("OTP expiry must be at least 1 second")

        if length < 1 or length > 12:
            raise AuthError("OTP length must be between 1 and 12")

        identifier = identifier.strip()
        purpose = purpose.strip()

        otp = self._generate_otp(length)
        expires_at = datetime.now() + timedelta(seconds=expiry)

        with self.session_factory() as db:
            try:
                db.query(OTP).filter_by(
                    identifier=identifier,
                    purpose=purpose,
                ).delete()

                db.add(
                    OTP(
                        identifier=identifier,
                        purpose=purpose,
                        code_hash=simple_hash(otp),
                        expires_at=expires_at,
                    )
                )

                db.commit()
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to create OTP: {str(e)}")

        return {
            "otp": otp,
            "expires_at": int(expires_at.timestamp()),
        }

    # ==========================================================
    # VERIFY
    # ==========================================================

    def verify(
        self,
        *,
        identifier: str,
        purpose: str,
        otp: str,
    ):
        if not identifier or not purpose:
            raise OTPNotFoundError()

        if not otp or not isinstance(otp, str) or not otp.strip():
            raise OTPInvalidError()

        identifier = identifier.strip()
        purpose = purpose.strip()
        otp = otp.strip()

        with self.session_factory() as db:
            record = self._get(
                db,
                identifier,
                purpose,
            )

            if record is None:
                raise OTPNotFoundError()

            if record.expires_at < datetime.now():
                try:
                    db.delete(record)
                    db.commit()
                except Exception:
                    db.rollback()
                raise OTPExpiredError()

            if not verify_hash(
                otp,
                record.code_hash,
            ):
                raise OTPInvalidError()

            try:
                db.delete(record)
                db.commit()
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to clear verified OTP: {str(e)}")

    # ==========================================================
    # DELETE
    # ==========================================================

    def revoke(
        self,
        *,
        identifier: str,
        purpose: str,
    ):
        if not identifier or not purpose:
            return

        identifier = identifier.strip()
        purpose = purpose.strip()

        with self.session_factory() as db:
            try:
                db.query(OTP).filter_by(
                    identifier=identifier,
                    purpose=purpose,
                ).delete()
                db.commit()
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to revoke OTP: {str(e)}")

    # ==========================================================
    # CLEANUP
    # ==========================================================

    def cleanup(self):
        with self.session_factory() as db:
            try:
                db.query(OTP).filter(
                    OTP.expires_at < datetime.now()
                ).delete()
                db.commit()
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to cleanup OTPs: {str(e)}")

    def get_all(self, page: int = 1, limit: int = 10):
        with self.session_factory() as db:
            page = max(1, page)
            limit = max(1, limit)
            offset = (page - 1) * limit

            otps = (
                db.query(OTP)
                .order_by(OTP.id.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            return to_list_dict(otps)

    def query(self, identifier: str):
        if not identifier or not isinstance(identifier, str):
            return []

        with self.session_factory() as db:
            otps = (
                db.query(OTP)
                .filter(OTP.identifier.ilike(f"%{identifier.strip()}%"))
                .order_by(OTP.id.desc())
                .all()
            )
            return to_list_dict(otps)

    # ==========================================================
    # CLEAR ALL
    # ==========================================================

    def clear_all(self):
        with self.session_factory() as db:
            try:
                db.query(OTP).delete(synchronize_session=False)
                db.commit()
            except Exception as e:
                db.rollback()
                raise DatabaseError(f"Failed to clear all OTPs: {str(e)}")

    # ==========================================================
    # PRIVATE
    # ==========================================================

    def _get(
        self,
        db,
        identifier: str,
        purpose: str,
    ):
        return (
            db.query(OTP)
            .filter_by(
                identifier=identifier,
                purpose=purpose,
            )
            .first()
        )

    def _generate_otp(
        self,
        length: int,
    ):
        length = max(1, min(12, length))
        minimum = 10 ** (length - 1)
        maximum = (10 ** length) - 1

        return str(
            random.randint(
                minimum,
                maximum,
            )
        )