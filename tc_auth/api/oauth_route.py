
from fastapi import APIRouter, Request

class OAuthRoutes:
    def __init__(
        self,
        google,
        github,

    ):
        self.google = google
        self.github = github

        self.router = APIRouter(tags=["OAuth Login"])

        self.router.get("/google/login")(self.google_login)
        self.router.get("/google/callback")(self.google_callback)
        self.router.get("/github/login")(self.github_login)
        self.router.get("/github/callback")(self.github_callback)
 
 
    # ==========================================================
    # GOOGLE OAUTH
    # ==========================================================

    async def google_login(
        self,
        request : Request,
        frontend_url: str,
    ):
        return await self.google.login(request,frontend_url=frontend_url)
    
    
    async def google_callback(
        self,
        request : Request,
    ):
        meta = self._request_meta(request)
        return await self.google.callback(request, **meta)

    
    # ==========================================================
    # GITHUB OAUTH
    # ==========================================================

    async def github_login(
        self,
        request : Request,
        frontend_url: str,
    ):
        return await self.github.login(request,frontend_url=frontend_url)
    
    
    async def github_callback(
        self,
        request : Request,
    ):
        meta = self._request_meta(request)
        return await self.github.callback(request, **meta)
        
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