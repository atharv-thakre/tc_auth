from fastapi import APIRouter, Depends
from ..schema import UpdatePassword, UpdateSchema


class AccountRoutes:
    def __init__(self, session_service, account_service, deps):
        self.session_service = session_service
        self.account_service = account_service
        self.deps = deps

        self.router = APIRouter(tags=["Profile Routes"])
        self.register()

    def register(self):
        current = Depends(self.deps.get_current)

        @self.router.post("/logout")
        def logout(user=current):
            self.session_service.destroy_session(user["session"]["id"])
            return {"success": True, "message": "Logged out successfully"}

        @self.router.post("/logout-all")
        def logout_all(user=current):
            self.session_service.destroy_all(user["account"]["id"])
            return {"success": True, "message": "Logged out from all devices successfully"}

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
            self.account_service.update_password(
                account_id=user["account"]["id"],
                password=body.password,
            )
            return {"success": True, "message": "Password updated successfully"}
