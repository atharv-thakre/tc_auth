from authlib.integrations.starlette_client import OAuth
from fastapi.responses import RedirectResponse
from fastapi import Request

from ..exceptions.error import (
    AuthError,
    InvalidConfigError,
    OAuthCallbackError,
    OAuthNotConfiguredError,
    MissingRequiredFieldError,
)


class GitHubOAuth:
    def __init__(self, oauth_service, cookie_service=None):
        self.oauth_service = oauth_service
        self.cookie_service = cookie_service
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
            raise InvalidConfigError("GitHub OAuth", "GitHub client_id is required and must be a non-empty string")

        if not client_secret or not isinstance(client_secret, str) or not client_secret.strip():
            raise InvalidConfigError("GitHub OAuth", "GitHub client_secret is required and must be a non-empty string")

        if not redirect_uri or not isinstance(redirect_uri, str) or not redirect_uri.strip():
            raise InvalidConfigError("GitHub OAuth", "GitHub redirect_uri is required and must be a non-empty string")

        self.redirect_uri = redirect_uri.strip()
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()


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

        return {
            "success": True,
            "message": "GitHub OAuth configured successfully",
        }

    async def login(
        self,
        request: Request,
        frontend_url: str,
    ):
        if not self.is_configured:
            raise OAuthNotConfiguredError("GitHub")

        if not frontend_url or not isinstance(frontend_url, str):
            raise MissingRequiredFieldError("frontend_url", "frontend_url parameter is required")

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
            raise OAuthNotConfiguredError("GitHub")

        frontend_url = request.session.get("frontend_url", "").rstrip("/")
        request.session.pop("frontend_url", None)

        if not frontend_url:
            frontend_url = ""

        try:
            token = await self.client.authorize_access_token(request)
        except Exception as e:
            raise OAuthCallbackError(f"GitHub authorization failed (invalid credentials or authorization code): {str(e)}")

        if not token or not isinstance(token, dict):
            raise OAuthCallbackError("Failed to obtain GitHub access token")

        if "error" in token:
            error_desc = token.get("error_description") or token.get("error")
            raise OAuthCallbackError(f"GitHub authorization failed (invalid credentials): {error_desc}")

        if not token.get("access_token"):
            raise OAuthCallbackError("GitHub authorization failed: Missing access token in response")

        try:
            user_response = await self.client.get(
                "user",
                token=token,
            )
            if hasattr(user_response, "status_code") and user_response.status_code != 200:
                raise OAuthCallbackError(f"GitHub API returned status {user_response.status_code}")
            user = user_response.json()
        except OAuthCallbackError:
            raise
        except Exception as e:
            raise OAuthCallbackError(f"Failed to fetch GitHub profile: {str(e)}")

        if not isinstance(user, dict) or "id" not in user:
            raise OAuthCallbackError("Invalid GitHub profile response: Missing user ID")


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

        provider_user_id = str(user["id"])
        link_account_id = request.session.pop("link_account_id", None)
        callback_url = f"{frontend_url}/oauth/callback" if frontend_url else "/oauth/callback"

        if link_account_id:
            try:
                self.oauth_service.link_account(
                    account_id=int(link_account_id),
                    provider="github",
                    provider_user_id=provider_user_id,
                )
                acc = self.oauth_service.get_user.by_id(int(link_account_id))
                self.oauth_service._initialize_profile(
                    provider="github",
                    account=acc,
                    name=user.get("name"),
                    email=email,
                    avatar_url=user.get("avatar_url"),
                )
                return RedirectResponse(
                    f"{callback_url}?linked=true&provider=github"
                )
            except Exception as e:
                return RedirectResponse(
                    f"{callback_url}?linked=false&provider=github&error={str(e)}"
                )

        result = self.oauth_service.login(
            provider="github",
            provider_user_id=provider_user_id,
            name=user.get("name"),
            email=email,
            avatar_url=user.get("avatar_url"),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        redirect_params = f"access_token={result['access_token']}"
        if result.get("refresh_token"):
            redirect_params += f"&refresh_token={result['refresh_token']}"

        response = RedirectResponse(
            f"{callback_url}?{redirect_params}"
        )
        if self.cookie_service and self.cookie_service.is_cookie_mode():
            self.cookie_service.set_auth_cookies(
                response=response,
                access_token=result["access_token"],
                refresh_token=result.get("refresh_token"),
            )

        return response