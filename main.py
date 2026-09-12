# from tc_auth.auth import Auth
from sqlalchemy import create_engine
from fastapi.middleware.cors import CORSMiddleware
from tc_auth import Auth 
from fastapi import FastAPI
from config import config

engine = create_engine("postgresql://workspace:admin@localhost:5432/tc_auth", echo=False)

app = FastAPI()
auth = Auth(engine)

auth.include_routes(app=app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


auth.jwt.config(
    secret_key=config.JWT_SECRET_KEY,
    algorithm=config.JWT_ALGORITHM,
    session_duration_days=config.JWT_SESSION_DURATION_DAYS,
    dual_token_mode=config.JWT_DUAL_TOKEN_MODE,
    access_token_expire_minutes=config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    refresh_token_expire_days=config.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
)


# auth.email.config(
#     host=config.EMAIL_HOST,
#     port=config.EMAIL_PORT,
#     username=config.EMAIL_USERNAME,
#     password=config.EMAIL_PASSWORD,
#     sender=config.EMAIL_SENDER,
#     use_tls=config.EMAIL_USE_TLS,
# )


# if config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_SECRET:
#     auth.google.config(
#         client_id=config.GOOGLE_CLIENT_ID,
#         client_secret=config.GOOGLE_CLIENT_SECRET,
#         redirect_uri=config.GOOGLE_REDIRECT_URI,
#     )


# if config.GITHUB_CLIENT_ID and config.GITHUB_CLIENT_SECRET:
#     auth.github.config(
#         client_id=config.GITHUB_CLIENT_ID,
#         client_secret=config.GITHUB_CLIENT_SECRET,
#         redirect_uri=config.GITHUB_REDIRECT_URI,
#     )


# if config.DISCORD_CLIENT_ID and config.DISCORD_CLIENT_SECRET:
#     auth.discord.config(
#         client_id=config.DISCORD_CLIENT_ID,
#         client_secret=config.DISCORD_CLIENT_SECRET,
#         redirect_uri=config.DISCORD_REDIRECT_URI,
#     )


def run():
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )



if __name__ == "__main__":
    run()
    