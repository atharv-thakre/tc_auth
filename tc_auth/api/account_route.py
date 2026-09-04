from fastapi import APIRouter , Depends
from ..schema import UpdatePassword, UpdateSchema



class AccountRoutes:
    def __init__(self, app, session_service, account_service, deps):
        self.session_service = session_service
        self.account_service = account_service
        self.deps = deps

        self.router = APIRouter()
        self.register()
        app.include_router(self.router, prefix="/tc-auth", tags=["Profile Routes"])

    def register(self):
        current = Depends(self.deps.get_current)

        @self.router.post("/logout")
        def logout(user=current):
            return self.session_service.destroy_session(user["session"]["id"])

        @self.router.post("/logout-all")
        def logout_all(user=current):
            return self.session_service.destroy_all(user["account"]["id"])

        @self.router.get("/me")
        def me(user=current):
            return user
        
        @self.router.patch("/me")
        def patch_me(body: UpdateSchema, user=current):
            return self.account_service.update_user(account_id=user["account"]["id"], **body.model_dump())
        
        @self.router.put("/update/password")
        def update_password(body: UpdatePassword, user=current):
            return self.account_service.update_password(account_id=user["account"]["id"], password=body.password)
        

    # ==========================================================
