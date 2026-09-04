import time
import jwt
from .exceptions.error import InvalidTokenError


SECRET_KEY = "this-is-my-super-secret-key-for-jwt-auth"
ALGORITHM = "HS256"
SESSION_DURATION_DAYS = 1

def config(
        secret_key: str,
        algorithm: str,
        session_duration_days: int,
    ) -> None:
    global SECRET_KEY, ALGORITHM, SESSION_DURATION_DAYS
    SECRET_KEY = secret_key
    ALGORITHM = algorithm
    SESSION_DURATION_DAYS = session_duration_days

def load():
    return {
        "secret_key": SECRET_KEY,
        "algorithm": ALGORITHM,
        "session_duration_days": SESSION_DURATION_DAYS,
    }


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = (
        int(time.time())
        + (SESSION_DURATION_DAYS * 24 * 60 * 60)
    )

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
    except Exception:
        raise InvalidTokenError("invalid")
