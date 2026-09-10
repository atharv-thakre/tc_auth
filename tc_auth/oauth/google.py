from authlib.integrations.starlette_client import OAuth
from fastapi import Request
from fastapi.responses import RedirectResponse

from ..exceptions.error import (
    AuthError,
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
        self.redirect_uri = redirect_uri
        self.client_id = client_id
        self.client_secret = client_secret

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
        if self.client is None:
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
        if self.client is None:
            raise OAuthNotConfiguredError("Google")

        frontend_url = request.session.get("frontend_url", "").rstrip("/")
        request.session.pop("frontend_url", None)

        if not frontend_url:
            frontend_url = ""

        try:
            token = await self.client.authorize_access_token(request)
        except Exception as e:
            raise OAuthCallbackError(f"Google authorization failed: {str(e)}")

        if not token or not isinstance(token, dict):
            raise OAuthCallbackError("Failed to obtain Google access token")

        user = token.get("userinfo")
        if not user or not isinstance(user, dict) or "sub" not in user:
            try:
                user = await self.client.userinfo(token=token)
            except Exception:
                pass

        if not user or not isinstance(user, dict) or "sub" not in user:
            raise OAuthCallbackError("Failed to obtain Google user information")

        result = self.oauth_service.login(
            provider="google",
            provider_user_id=user["sub"],
            name=user.get("name"),
            email=user.get("email"),
            avatar_url=user.get("picture"),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        callback_url = f"{frontend_url}/oauth/callback" if frontend_url else "/oauth/callback"
        return RedirectResponse(
            f"{callback_url}?access_token={result['access_token']}"
        )