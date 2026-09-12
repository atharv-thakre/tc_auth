from ..exceptions.error import WeakPasswordError


def validate_password_strength(password: str) -> None:
    if not password or not isinstance(password, str):
        raise WeakPasswordError("Password is required and must be a string")

    if len(password) < 6:
        raise WeakPasswordError("Password must be at least 6 characters long")

    if not any(c.isupper() for c in password):
        raise WeakPasswordError("Password must contain at least one uppercase letter")

    if not any(c.islower() for c in password):
        raise WeakPasswordError("Password must contain at least one lowercase letter")

    if not any(c.isdigit() for c in password):
        raise WeakPasswordError("Password must contain at least one number")
