from ..db.models import Account, OAuthAccount, Session, OTP
from ..exceptions.error import DatabaseError


class DashboardService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def get_counts(self):
        with self.session_factory() as db:
            try:
                accounts = db.query(Account).count()
                oauth = db.query(OAuthAccount).count()
                sessions = db.query(Session).count()
                otp = db.query(OTP).count()

                return {
                    "accounts": accounts,
                    "oauth": oauth,
                    "sessions": sessions,
                    "otp": otp,
                }
            except Exception as e:
                raise DatabaseError(f"Failed to retrieve dashboard counts: {str(e)}")