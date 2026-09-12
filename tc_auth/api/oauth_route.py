from fastapi import APIRouter, Request
from ..exceptions.error import OAuthNotConfiguredError


class OAuthRoutes:
    def __init__(
        self,
        google,
        github,
        discord=None,
    ):
        self.google = google
        self.github = github
        self.discord = discord

        self.router = APIRouter(tags=["OAuth Login"])

        self.router.get("/google/login")(self.google_login)
        self.router.get("/google/callback")(self.google_callback)
        self.router.get("/github/login")(self.github_login)
        self.router.get("/github/callback")(self.github_callback)
        self.router.get("/discord/login")(self.discord_login)
        self.router.get("/discord/callback")(self.discord_callback)

    # ==========================================================
    # GOOGLE OAUTH
    # ==========================================================

    async def google_login(
        self,
        request: Request,
        frontend_url: str,
    ):
        return await self.google.login(request, frontend_url=frontend_url)

    async def google_callback(
        self,
        request: Request,
    ):
        meta = self._request_meta(request)
        return await self.google.callback(request, **meta)

    # ==========================================================
    # GITHUB OAUTH
    # ==========================================================

    async def github_login(
        self,
        request: Request,
        frontend_url: str,
    ):
        return await self.github.login(request, frontend_url=frontend_url)

    async def github_callback(
        self,
        request: Request,
    ):
        meta = self._request_meta(request)
        return await self.github.callback(request, **meta)

    # ==========================================================
    # DISCORD OAUTH
    # ==========================================================

    async def discord_login(
        self,
        request: Request,
        frontend_url: str,
    ):
        if not self.discord:
            raise OAuthNotConfiguredError("Discord")
        return await self.discord.login(request, frontend_url=frontend_url)

    async def discord_callback(
        self,
        request: Request,
    ):
        if not self.discord:
            raise OAuthNotConfiguredError("Discord")
        meta = self._request_meta(request)
        return await self.discord.callback(request, **meta)

    # ==========================================================
    # PRIVATE
    # ==========================================================

    def _request_meta(
        self,
        request: Request,
    ):
        ip = (
            request.headers.get("cf-connecting-ip")
            or request.headers.get("x-forwarded-for")
            or (
                request.client.host
                if request.client
                else None
            )
        )

        return {
            "ip_address": ip,
            "user_agent": request.headers.get(
                "user-agent",
                "",
            ),
        }