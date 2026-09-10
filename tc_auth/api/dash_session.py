from fastapi import APIRouter, Depends, Query
from ..schema import (
    DestroySession,
    DestroyAllSession,
)


class DashSessionRoutes:
    def __init__(self, session_service, role_deps):
        self.session_service = session_service
        self.role_deps = role_deps
        
        self.router = APIRouter(prefix="/session", tags=["Session ops"])
        self.register()

    def register(self):
        current = Depends(self.role_deps.require("superadmin"))

        @self.router.get("/")
        def get_sessions(
            user=current,
            page: int = Query(1, ge=1),
            limit: int = Query(10, ge=1, le=100),
        ):
            return self.session_service.get_all(
                page=page,
                limit=limit,
            )

        @self.router.get("/query")
        def query(
            user=current,
            field: str = Query(...),
            value: str = Query(...),
        ):
            return self.session_service.query(
                field=field,
                value=value,
            )

        @self.router.delete("/")
        def destroy_session(body: DestroySession, user=current):
            self.session_service.destroy_session(**body.model_dump())
            return {"success": True, "message": "Session destroyed successfully"}

        @self.router.delete("/all")
        def destroy_all(body: DestroyAllSession, user=current):    
            self.session_service.destroy_all(**body.model_dump())
            return {"success": True, "message": "All sessions destroyed for account"}

        @self.router.delete("/cleanup")
        def cleanup(user=current):
            self.session_service.cleanup_expired()
            return {"success": True, "message": "Expired sessions cleaned up successfully"}

        @self.router.delete("/clear")
        def clear(user=current):
            self.session_service.clear_all()
            return {"success": True, "message": "All sessions cleared successfully"}
