from fastapi import APIRouter, Depends, Query
from ..schema import (
    SuperCreateSchema,
    SuperUpdateSchema,
    SuperDeleteSchema,
)


class DashAccountRoutes:
    def __init__(self, account_service, role_deps):
        self.account_service = account_service
        self.role_deps = role_deps

        self.router = APIRouter(prefix="/account", tags=["Account ops"])
        self.register()

    def register(self):
        current = Depends(self.role_deps.require("superadmin"))

        @self.router.get("/")
        def get_accounts(
            user=current,
            page: int = Query(1, ge=1),
            limit: int = Query(10, ge=1, le=100),
        ):
            return self.account_service.get_all(
                page=page,
                limit=limit,
            )

        @self.router.get("/query")
        def query_account(
            user=current,
            field: str = Query(...),
            value: str = Query(...),
        ):
            return self.account_service.query(
                field=field,
                value=value,
            )

        @self.router.post("/")
        def create(body: SuperCreateSchema, user=current):
            return self.account_service.create_user(**body.model_dump())

        @self.router.patch("/")
        def update(body: SuperUpdateSchema, user=current):
            return self.account_service.super_update(**body.model_dump())

        @self.router.delete("/")
        def delete(body: SuperDeleteSchema, user=current):
            self.account_service.delete_user(**body.model_dump())
            return {"success": True, "message": "Account deleted successfully"}
