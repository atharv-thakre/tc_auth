from datetime import datetime
from fastapi import APIRouter, Depends

from ..schema import (
    OAuthConfig,
    EmailConfig,
    JWTConfig,
)


class DashboardRoute:
    def __init__(
        self,
        email_service,
        github_service,
        google_service,
        jwt_service,
        role_deps,
        dashboard_service,
    ):
        self.email_service = email_service
        self.github_service = github_service
        self.google_service = google_service
        self.jwt_service = jwt_service
        self.role_deps = role_deps
        self.dashboard_service = dashboard_service

        self.router = APIRouter(prefix="/config", tags=["CONFIG"])
        self.register()

    def register(self):
        current = Depends(self.role_deps.require("superadmin"))

        @self.router.get("/pulse")
        def pulse():
            return {
                "system_time": datetime.now().isoformat(),
                "response": "Hello",
                "status": "healthy",
                "state": "active",
            }

        @self.router.get("/load/")
        def load_config(user=current):
            return {
                "email": self.email_service.load(),
                "github": self.github_service.load(),
                "google": self.google_service.load(),
                "jwt": self.jwt_service.load(),
            }

        @self.router.get("/counts")
        def load_counts(user=current):
            return self.dashboard_service.get_counts()

        @self.router.post("/email")
        def configure_email(config: EmailConfig, user=current):
            self.email_service.config(**config.model_dump())
            return {"success": True, "message": "Email service configured successfully"}

        @self.router.post("/github")
        def configure_github(config: OAuthConfig, user=current):
            self.github_service.config(**config.model_dump())
            return {"success": True, "message": "GitHub OAuth configured successfully"}

        @self.router.post("/google")
        def configure_google(config: OAuthConfig, user=current):
            self.google_service.config(**config.model_dump())
            return {"success": True, "message": "Google OAuth configured successfully"}

        @self.router.post("/jwt")
        def configure_jwt(config: JWTConfig, user=current):    
            self.jwt_service.config(**config.model_dump())
            return {"success": True, "message": "JWT configured successfully"}
