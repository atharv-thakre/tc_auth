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


config = Config()