import time
import jwt
from .exceptions.error import InvalidConfigError, InvalidTokenError


SECRET_KEY = "this-is-my-super-secret-key-for-jwt-auth"
ALGORITHM = "HS256"
SESSION_DURATION_DAYS = 7

# Dual-Token Configuration (Default: False to preserve single-token behavior)
DUAL_TOKEN_MODE = False
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

VALID_ALGORITHMS = {"HS256", "HS384", "HS512"}


def is_dual_token_mode() -> bool:
    return DUAL_TOKEN_MODE


def get_session_duration_days() -> int:
    return SESSION_DURATION_DAYS


def get_access_token_expire_minutes() -> int:
    return ACCESS_TOKEN_EXPIRE_MINUTES


def get_refresh_token_expire_days() -> int:
    return REFRESH_TOKEN_EXPIRE_DAYS


def config(
    secret_key: str,
    algorithm: str,
    session_duration_days: int,
    dual_token_mode: bool = False,
    access_token_expire_minutes: int | None = None,
    refresh_token_expire_days: int | None = None,
) -> dict:
    global SECRET_KEY, ALGORITHM, SESSION_DURATION_DAYS
    global DUAL_TOKEN_MODE, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

    if not secret_key or not isinstance(secret_key, str) or not secret_key.strip():
        raise InvalidConfigError("JWT", "JWT secret_key is required and must be a non-empty string")

    if not algorithm or not isinstance(algorithm, str) or algorithm.upper() not in VALID_ALGORITHMS:
        raise InvalidConfigError(
            "JWT",
            f"Invalid JWT algorithm '{algorithm}'. Supported algorithms: {', '.join(sorted(VALID_ALGORITHMS))}"
        )

    if not isinstance(session_duration_days, int) or session_duration_days < 1:
        raise InvalidConfigError("JWT", "JWT session_duration_days must be an integer >= 1")

    if not isinstance(dual_token_mode, bool):
        raise InvalidConfigError("JWT", "JWT dual_token_mode must be a boolean")

    if access_token_expire_minutes is not None:
        if not isinstance(access_token_expire_minutes, int) or access_token_expire_minutes < 1:
            raise InvalidConfigError("JWT", "JWT access_token_expire_minutes must be an integer >= 1")
    else:
        access_token_expire_minutes = 15

    if refresh_token_expire_days is not None:
        if not isinstance(refresh_token_expire_days, int) or refresh_token_expire_days < 1:
            raise InvalidConfigError("JWT", "JWT refresh_token_expire_days must be an integer >= 1")
    else:
        refresh_token_expire_days = session_duration_days

    SECRET_KEY = secret_key.strip()
    ALGORITHM = algorithm.upper()
    SESSION_DURATION_DAYS = session_duration_days
    DUAL_TOKEN_MODE = dual_token_mode
    ACCESS_TOKEN_EXPIRE_MINUTES = access_token_expire_minutes
    REFRESH_TOKEN_EXPIRE_DAYS = refresh_token_expire_days

    return {
        "success": True,
        "message": "JWT configured successfully",
    }


def load():
    return {
        "secret_key": SECRET_KEY,
        "algorithm": ALGORITHM,
        "session_duration_days": SESSION_DURATION_DAYS,
        "dual_token_mode": DUAL_TOKEN_MODE,
        "access_token_expire_minutes": ACCESS_TOKEN_EXPIRE_MINUTES,
        "refresh_token_expire_days": REFRESH_TOKEN_EXPIRE_DAYS,
    }


def create_access_token(data: dict) -> str:
    if not isinstance(data, dict):
        raise ValueError("Data payload for access token must be a dict")

    payload = data.copy()
    payload["type"] = "access"

    if DUAL_TOKEN_MODE:
        payload["exp"] = (
            int(time.time())
            + (ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        )
    else:
        payload["exp"] = (
            int(time.time())
            + (SESSION_DURATION_DAYS * 24 * 60 * 60)
        )

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def create_refresh_token(data: dict) -> str:
    if not isinstance(data, dict):
        raise ValueError("Data payload for refresh token must be a dict")

    payload = data.copy()
    payload["type"] = "refresh"
    payload["exp"] = (
        int(time.time())
        + (REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
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
