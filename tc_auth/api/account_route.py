from fastapi import APIRouter, Depends, Request, Response
from ..schema import UpdatePassword, UpdateSchema, LinkOAuthRequest
from ..exceptions.error import (
    AuthError,
    OAuthNotConfiguredError,
    UnsupportedOAuthProviderError,
    MissingRequiredFieldError,
)


class AccountRoutes:
    def __init__(
        self,
        session_service,
        account_service,
        deps,
        oauth_service=None,
        google=None,
        github=None,
        discord=None,
        cookie_service=None,
        log_service=None,
    ):
        self.session_service = session_service
        self.account_service = account_service
        self.deps = deps
        self.oauth_service = oauth_service
        self.google = google
        self.github = github
        self.discord = discord
        self.cookie_service = cookie_service
        self.log_service = log_service

        self.router = APIRouter(tags=["Profile Routes"])
        self.register()

    def register(self):
        current = Depends(self.deps.get_current_user)

        @self.router.post("/logout")
        def logout(response: Response, user=current):
            result = self.session_service.destroy_session(user["session"]["id"])
            if self.cookie_service and self.cookie_service.is_cookie_mode():
                self.cookie_service.clear_auth_cookies(response)
            if self.log_service:
                self.log_service.info(
                    "LOGOUT",
                    f"User '{user['account'].get('email') or user['account'].get('handle')}' logged out successfully",
                    metadata={"account_id": user["account"]["id"], "session_id": user["session"]["id"]},
                )
            return result

        @self.router.post("/logout-all")
        def logout_all(response: Response, user=current):
            result = self.session_service.destroy_all(user["account"]["id"])
            if self.cookie_service and self.cookie_service.is_cookie_mode():
                self.cookie_service.clear_auth_cookies(response)
            if self.log_service:
                self.log_service.info(
                    "LOGOUT_ALL",
                    f"All sessions destroyed for user '{user['account'].get('email') or user['account'].get('handle')}'",
                    metadata={"account_id": user["account"]["id"]},
                )
            return result


        @self.router.get("/me")
        def me(user=current):
            return user

        @self.router.patch("/me")
        def patch_me(body: UpdateSchema, user=current):
            return self.account_service.update_user(
                account_id=user["account"]["id"],
                **body.model_dump(),
            )

        @self.router.put("/update/password")
        def update_password(body: UpdatePassword, user=current):
            return self.account_service.update_password(
                account_id=user["account"]["id"],
                password=body.password,
            )

        @self.router.post("/account/oauth/link/{provider}")
        async def link_provider(
            provider: str,
            request: Request,
            frontend_url: str | None = None,
            body: LinkOAuthRequest | None = None,
            user=current,
        ):
            normalized_provider = provider.strip().lower()
            if normalized_provider not in ("google", "github", "discord"):
                raise UnsupportedOAuthProviderError(provider)

            account_id = user["account"]["id"]

            if body and body.provider_user_id:
                if not self.oauth_service:
                    raise OAuthNotConfiguredError("OAuth", "OAuth service is not available")
                return self.oauth_service.link_account(
                    account_id=account_id,
                    provider=normalized_provider,
                    provider_user_id=body.provider_user_id,
                )

            resolved_frontend_url = frontend_url or (body.frontend_url if body else None)
            if not resolved_frontend_url:
                raise MissingRequiredFieldError("frontend_url/provider_user_id", "frontend_url parameter or provider_user_id body is required")

            request.session["link_account_id"] = account_id

            provider_service = getattr(self, normalized_provider, None)
            if not provider_service or not provider_service.is_configured:
                raise OAuthNotConfiguredError(normalized_provider.capitalize())

            return await provider_service.login(request, frontend_url=resolved_frontend_url)

        @self.router.post("/account/oauth/link/google")
        async def link_google(
            request: Request,
            frontend_url: str | None = None,
            body: LinkOAuthRequest | None = None,
            user=current,
        ):
            return await link_provider("google", request, frontend_url, body, user)

        @self.router.post("/account/oauth/link/github")
        async def link_github(
            request: Request,
            frontend_url: str | None = None,
            body: LinkOAuthRequest | None = None,
            user=current,
        ):
            return await link_provider("github", request, frontend_url, body, user)

        @self.router.post("/account/oauth/link/discord")
        async def link_discord(
            request: Request,
            frontend_url: str | None = None,
            body: LinkOAuthRequest | None = None,
            user=current,
        ):
            return await link_provider("discord", request, frontend_url, body, user)

        @self.router.delete("/account/oauth/{provider}")
        def unlink_provider(
            provider: str,
            user=current,
        ):
            normalized_provider = provider.strip().lower()
            if not self.oauth_service:
                raise OAuthNotConfiguredError("OAuth", "OAuth service is not available")
            return self.oauth_service.unlink_account(
                account_id=user["account"]["id"],
                provider=normalized_provider,
                enforce_active_auth=True,
            )

        @self.router.get("/account/oauth/links")
        def get_oauth_links(
            user=current,
        ):
            if not self.oauth_service:
                return []
            return self.oauth_service.get_account_links(user["account"]["id"])
