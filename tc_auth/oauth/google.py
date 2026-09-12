from authlib.integrations.starlette_client import OAuth
from fastapi import Request
from fastapi.responses import RedirectResponse

from ..exceptions.error import (
    AuthError,
    InvalidConfigError,
    OAuthCallbackError,
    OAuthNotConfiguredError,
)


class GoogleOAuth:
    def __init__(self, oauth_service):
        self.oauth_service = oauth_service
        self.client = None
        self.redirect_uri = None
        self.client_id = None
        self.client_secret = None

    @property
    def is_configured(self) -> bool:
        return bool(
            self.client is not None
            and self.client_id
            and self.client_secret
            and self.redirect_uri
        )

    def load(self):
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
        }

    def config(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ):
        if not client_id or not isinstance(client_id, str) or not client_id.strip():
            raise InvalidConfigError("Google OAuth", "Google client_id is required and must be a non-empty string")

        if not client_secret or not isinstance(client_secret, str) or not client_secret.strip():
            raise InvalidConfigError("Google OAuth", "Google client_secret is required and must be a non-empty string")

        if not redirect_uri or not isinstance(redirect_uri, str) or not redirect_uri.strip():
            raise InvalidConfigError("Google OAuth", "Google redirect_uri is required and must be a non-empty string")

        self.redirect_uri = redirect_uri.strip()
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()


        oauth = OAuth()

        self.client = oauth.register(
            name="google",
            client_id=client_id,
            client_secret=client_secret,
            server_metadata_url=(
                "https://accounts.google.com/.well-known/openid-configuration"
            ),
            client_kwargs={
                "scope": "openid email profile",
            },
        )

        return {
            "success": True,
            "message": "Google OAuth configured successfully",
        }

    async def login(
        self,
        request: Request,
        frontend_url: str,
    ):
        if not self.is_configured:
            raise OAuthNotConfiguredError("Google")

        if not frontend_url or not isinstance(frontend_url, str):
            raise AuthError("frontend_url parameter is required")

        request.session["frontend_url"] = frontend_url.strip()
        return await self.client.authorize_redirect(
            request,
            self.redirect_uri,
        )

    async def callback(
        self,
        request: Request,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        if not self.is_configured:
            raise OAuthNotConfiguredError("Google")

        frontend_url = request.session.get("frontend_url", "").rstrip("/")
        request.session.pop("frontend_url", None)

        if not frontend_url:
            frontend_url = ""

        try:
            token = await self.client.authorize_access_token(request)
        except Exception as e:
            raise OAuthCallbackError(f"Google authorization failed (invalid credentials or authorization code): {str(e)}")

        if not token or not isinstance(token, dict):
            raise OAuthCallbackError("Failed to obtain Google access token")

        if "error" in token:
            error_desc = token.get("error_description") or token.get("error")
            raise OAuthCallbackError(f"Google authorization failed (invalid credentials): {error_desc}")

        user = token.get("userinfo")
        if not user or not isinstance(user, dict) or "sub" not in user:
            try:
                user = await self.client.userinfo(token=token)
            except Exception as e:
                raise OAuthCallbackError(f"Failed to obtain Google user information: {str(e)}")

        if not user or not isinstance(user, dict) or "sub" not in user:
            raise OAuthCallbackError("Failed to obtain Google user information")


        link_account_id = request.session.pop("link_account_id", None)

        callback_url = f"{frontend_url}/oauth/callback" if frontend_url else "/oauth/callback"

        if link_account_id:
            try:
                self.oauth_service.link_account(
                    account_id=int(link_account_id),
                    provider="google",
                    provider_user_id=user["sub"],
                )
                acc = self.oauth_service.get_user.by_id(int(link_account_id))
                self.oauth_service._initialize_profile(
                    provider="google",
                    account=acc,
                    name=user.get("name"),
                    email=user.get("email"),
                    avatar_url=user.get("picture"),
                )
                return RedirectResponse(
                    f"{callback_url}?linked=true&provider=google"
                )
            except Exception as e:
                return RedirectResponse(
                    f"{callback_url}?linked=false&provider=google&error={str(e)}"
                )

        result = self.oauth_service.login(
            provider="google",
            provider_user_id=user["sub"],
            name=user.get("name"),
            email=user.get("email"),
            avatar_url=user.get("picture"),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        redirect_params = f"access_token={result['access_token']}"
        if result.get("refresh_token"):
            redirect_params += f"&refresh_token={result['refresh_token']}"

        return RedirectResponse(
            f"{callback_url}?{redirect_params}"
        )