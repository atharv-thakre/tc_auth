from fastapi import APIRouter, Depends, Query
from ..schema import (
    CreateOAuth,
    DeleteOAuth,
)

class DashOAuthRoutes:
    def __init__(self, oauth_service, role_deps):
        self.oauth_service = oauth_service  
        self.role_deps = role_deps

        self.router = APIRouter(prefix="/oauth", tags=["OAuth ops"])
        self.register()

    def register(self):
        current = Depends(self.role_deps.require("superadmin"))

        @self.router.get("/")
        def get_oauth_links(
            user=current,
            page: int = Query(1, ge=1),
            limit: int = Query(10, ge=1, le=100)
        ):
            return self.oauth_service.get_all(
                page=page,
                limit=limit
            )
        
        @self.router.get("/query")
        def query(
            user=current,
            field: str = Query(...),
            value: str = Query(...)
        ):
            return self.oauth_service.query(
                field=field,
                value=value
            )
        
        @self.router.post("/")
        def create(body : CreateOAuth , user=current):
            return self.oauth_service.link_account(**body.model_dump())


        @self.router.delete("/")
        def delete(body : DeleteOAuth, user=current):
            return self.oauth_service.unlink_account(**body.model_dump())
        

    # ==========================================================
