import os
from dotenv import load_dotenv
load_dotenv()


class Config:
    # ======================================================
    # JWT
    # ======================================================

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_SESSION_DURATION_DAYS = int(
        os.getenv("JWT_SESSION_DURATION_DAYS", "7")
    )
    JWT_DUAL_TOKEN_MODE = os.getenv("JWT_DUAL_TOKEN_MODE", "false").lower() == "true"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(
        os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", str(JWT_SESSION_DURATION_DAYS))
    )

    # ======================================================
    # EMAIL
    # ======================================================

    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_USE_TLS = os.getenv(
        "EMAIL_USE_TLS", "true"
    ).lower() == "true"

    # ======================================================
    # GOOGLE
    # ======================================================

    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

    # ======================================================
    # GITHUB
    # ======================================================

    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
    GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")

    # ======================================================
    # DISCORD
    # ======================================================

    DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
    DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
    DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")

    # ======================================================
    # COOKIE
    # ======================================================

    COOKIE_MODE = os.getenv("COOKIE_MODE", "false").lower() == "true"
    COOKIE_ACCESS_NAME = os.getenv("COOKIE_ACCESS_NAME", "access_token")
    COOKIE_REFRESH_NAME = os.getenv("COOKIE_REFRESH_NAME", "refresh_token")
    COOKIE_PATH = os.getenv("COOKIE_PATH", "/")
    COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN")
    COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_HTTPONLY = os.getenv("COOKIE_HTTPONLY", "true").lower() == "true"
    COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")
    COOKIE_MAX_AGE = int(os.getenv("COOKIE_MAX_AGE")) if os.getenv("COOKIE_MAX_AGE") else None

    # ======================================================
    # LOGGING
    # ======================================================

    LOGGING = os.getenv("LOGGING", os.getenv("LOG_ENABLED", "true")).lower() == "true"
    LOG_ENABLED = LOGGING
    LOG_DIR = os.getenv("LOG_DIR")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_CONSOLE_OUTPUT = os.getenv("LOG_CONSOLE_OUTPUT", "true").lower() == "true"
    LOG_CAPTURE_TERMINAL = os.getenv("LOG_CAPTURE_TERMINAL", "false").lower() == "true"
    LOG_REDACT_SENSITIVE = os.getenv("LOG_REDACT_SENSITIVE", "true").lower() == "true"

    _raw_patterns = os.getenv("LOG_REDACT_PATTERNS")
    if _raw_patterns:
        try:
            import json
            LOG_REDACT_PATTERNS = json.loads(_raw_patterns)
            if not isinstance(LOG_REDACT_PATTERNS, list):
                LOG_REDACT_PATTERNS = [p.strip() for p in _raw_patterns.split(",") if p.strip()]
        except Exception:
            LOG_REDACT_PATTERNS = [p.strip() for p in _raw_patterns.split(",") if p.strip()]
    else:
        LOG_REDACT_PATTERNS = []


config = Config()