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
    ) -> dict:
    global SECRET_KEY, ALGORITHM, SESSION_DURATION_DAYS
    SECRET_KEY = secret_key
    ALGORITHM = algorithm
    SESSION_DURATION_DAYS = session_duration_days
    return {
        "success": True,
        "message": "JWT configured successfully",
    }

def load():
    return {
        "secret_key": SECRET_KEY,
        "algorithm": ALGORITHM,
        "session_duration_days": SESSION_DURATION_DAYS,
    }


def create_access_token(data: dict) -> str:
    if not isinstance(data, dict):
        raise ValueError("Data payload for access token must be a dict")

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
    if not token or not isinstance(token, str):
        raise InvalidTokenError(field="token", message="Token is missing or invalid")

    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise InvalidTokenError(field="token", message="Token has expired")
    except jwt.PyJWTError as e:
        raise InvalidTokenError(field="token", message=f"Invalid token: {str(e)}")
    except Exception:
        raise InvalidTokenError(field="token", message="Invalid or expired token")
