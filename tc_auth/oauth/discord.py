from authlib.integrations.starlette_client import OAuth
from fastapi.responses import RedirectResponse
from fastapi import Request

from ..exceptions.error import (
    AuthError,
    InvalidConfigError,
    OAuthCallbackError,
    OAuthNotConfiguredError,
)


class DiscordOAuth:
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
            raise InvalidConfigError("Discord OAuth", "Discord client_id is required and must be a non-empty string")

        if not client_secret or not isinstance(client_secret, str) or not client_secret.strip():
            raise InvalidConfigError("Discord OAuth", "Discord client_secret is required and must be a non-empty string")

        if not redirect_uri or not isinstance(redirect_uri, str) or not redirect_uri.strip():
            raise InvalidConfigError("Discord OAuth", "Discord redirect_uri is required and must be a non-empty string")

        self.redirect_uri = redirect_uri.strip()
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()

        oauth = OAuth()

        self.client = oauth.register(
            name="discord",
            client_id=client_id,
            client_secret=client_secret,
            access_token_url="https://discord.com/api/oauth2/token",
            authorize_url="https://discord.com/api/oauth2/authorize",
            api_base_url="https://discord.com/api/",
            client_kwargs={
                "scope": "identify email",
            },
        )

        return {
            "success": True,
            "message": "Discord OAuth configured successfully",
        }

    async def login(
        self,
        request: Request,
        frontend_url: str,
    ):
        if not self.is_configured:
            raise OAuthNotConfiguredError("Discord")

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
            raise OAuthNotConfiguredError("Discord")

        frontend_url = request.session.get("frontend_url", "").rstrip("/")
        request.session.pop("frontend_url", None)

        link_account_id = request.session.pop("link_account_id", None)

        if not frontend_url:
            frontend_url = ""

        try:
            token = await self.client.authorize_access_token(request)
        except Exception as e:
            raise OAuthCallbackError(f"Discord authorization failed (invalid credentials or authorization code): {str(e)}")

        if not token or not isinstance(token, dict):
            raise OAuthCallbackError("Failed to obtain Discord access token")

        if "error" in token:
            error_desc = token.get("error_description") or token.get("error")
            raise OAuthCallbackError(f"Discord authorization failed (invalid credentials): {error_desc}")

        if not token.get("access_token"):
            raise OAuthCallbackError("Discord authorization failed: Missing access token in response")

        try:
            user_response = await self.client.get(
                "users/@me",
                token=token,
            )
            if hasattr(user_response, "status_code") and user_response.status_code != 200:
                raise OAuthCallbackError(f"Discord API returned status {user_response.status_code}")
            user = user_response.json()
        except OAuthCallbackError:
            raise
        except Exception as e:
            raise OAuthCallbackError(f"Failed to fetch Discord profile: {str(e)}")

        if not isinstance(user, dict) or "id" not in user:
            raise OAuthCallbackError("Invalid Discord profile response: Missing user ID")

        provider_user_id = str(user["id"])
        name = user.get("global_name") or user.get("username")

        # Handle Discord email verification edge cases
        email = None
        raw_email = user.get("email")
        if raw_email and isinstance(raw_email, str) and raw_email.strip():
            # If user has an email and verified is not False, use it
            if user.get("verified") is not False:
                email = raw_email.strip().lower()

        # Handle Discord avatar edge cases (GIF if 'a_' prefix, PNG otherwise, default avatar fallback)
        avatar_hash = user.get("avatar")
        if avatar_hash and isinstance(avatar_hash, str) and avatar_hash.strip():
            ext = "gif" if avatar_hash.startswith("a_") else "png"
            avatar_url = f"https://cdn.discordapp.com/avatars/{user['id']}/{avatar_hash}.{ext}"
        else:
            try:
                discrim = user.get("discriminator", "0")
                if discrim and discrim != "0":
                    default_idx = int(discrim) % 5
                else:
                    default_idx = (int(user["id"]) >> 22) % 6
                avatar_url = f"https://cdn.discordapp.com/embed/avatars/{default_idx}.png"
            except Exception:
                avatar_url = None

        callback_url = f"{frontend_url}/oauth/callback" if frontend_url else "/oauth/callback"

        # Account linking flow for existing logged-in user
        if link_account_id:
            try:
                self.oauth_service.link_account(
                    account_id=int(link_account_id),
                    provider="discord",
                    provider_user_id=provider_user_id,
                )
                acc = self.oauth_service.get_user.by_id(int(link_account_id))
                self.oauth_service._initialize_profile(
                    provider="discord",
                    account=acc,
                    name=name,
                    email=email,
                    avatar_url=avatar_url,
                )
                return RedirectResponse(
                    f"{callback_url}?linked=true&provider=discord"
                )
            except Exception as e:
                return RedirectResponse(
                    f"{callback_url}?linked=false&provider=discord&error={str(e)}"
                )

        result = self.oauth_service.login(
            provider="discord",
            provider_user_id=provider_user_id,
            name=name,
            email=email,
            avatar_url=avatar_url,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        redirect_params = f"access_token={result['access_token']}"
        if result.get("refresh_token"):
            redirect_params += f"&refresh_token={result['refresh_token']}"

        return RedirectResponse(
            f"{callback_url}?{redirect_params}"
        )
