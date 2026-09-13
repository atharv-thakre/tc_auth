import bcrypt
import hashlib


from ..exceptions.error import InvalidFieldError


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    """
    if not password or not isinstance(password, str):
        raise InvalidFieldError("password", "Password must be a non-empty string")

    return bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt(),
    ).decode()


def verify_password(
    password: str | None,
    password_hash: str | None,
) -> bool:
    """
    Verify a password against its hash safely.
    Returns False if either password or password_hash is missing or invalid.
    """
    if not password or not password_hash:
        return False

    try:
        return bcrypt.checkpw(
            password.encode(),
            password_hash.encode(),
        )
    except Exception:
        return False


def simple_hash(value: str) -> str:
    """
    Generate a SHA-256 hash.
    """
    if not isinstance(value, str):
        value = str(value)

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def verify_hash(
    value: str | None,
    hash_value: str | None,
) -> bool:
    """
    Verify a value against its SHA-256 hash safely.
    Returns False if either value or hash_value is missing.
    """
    if not value or not hash_value:
        return False

    return simple_hash(value) == hash_value