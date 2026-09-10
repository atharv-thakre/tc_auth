from authlib.integrations.starlette_client import OAuth
from fastapi.responses import RedirectResponse
from fastapi import Request

from ..exceptions.error import (
    AuthError,
    OAuthCallbackError,
    OAuthNotConfiguredError,
)


class GitHubOAuth:
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
            name="github",
            client_id=client_id,
            client_secret=client_secret,
            access_token_url="https://github.com/login/oauth/access_token",
            authorize_url="https://github.com/login/oauth/authorize",
            api_base_url="https://api.github.com/",
            client_kwargs={
                "scope": "read:user user:email",
            },
        )

    async def login(
        self,
        request: Request,
        frontend_url: str,
    ):
        if self.client is None:
            raise OAuthNotConfiguredError("GitHub")

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
            raise OAuthNotConfiguredError("GitHub")

        frontend_url = request.session.get("frontend_url", "").rstrip("/")
        request.session.pop("frontend_url", None)

        if not frontend_url:
            frontend_url = ""

        try:
            token = await self.client.authorize_access_token(request)
        except Exception as e:
            raise OAuthCallbackError(f"GitHub authorization failed: {str(e)}")

        if not token or not isinstance(token, dict):
            raise OAuthCallbackError("Failed to obtain GitHub access token")

        try:
            user_response = await self.client.get(
                "user",
                token=token,
            )
            user = user_response.json()
        except Exception as e:
            raise OAuthCallbackError(f"Failed to fetch GitHub profile: {str(e)}")

        if not isinstance(user, dict) or "id" not in user:
            raise OAuthCallbackError("Invalid GitHub profile response")

        email = user.get("email")

        if email is None:
            try:
                emails_response = await self.client.get(
                    "user/emails",
                    token=token,
                )
                emails = emails_response.json()

                if isinstance(emails, list):
                    for item in emails:
                        if (
                            isinstance(item, dict)
                            and item.get("primary")
                            and item.get("verified")
                        ):
                            email = item.get("email")
                            break
            except Exception:
                pass

        result = self.oauth_service.login(
            provider="github",
            provider_user_id=str(user["id"]),
            name=user.get("name"),
            email=email,
            avatar_url=user.get("avatar_url"),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        callback_url = f"{frontend_url}/oauth/callback" if frontend_url else "/oauth/callback"
        return RedirectResponse(
            f"{callback_url}?access_token={result['access_token']}"
        )