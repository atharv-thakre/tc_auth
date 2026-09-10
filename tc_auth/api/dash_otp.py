from fastapi import APIRouter, Depends, Query
from ..schema import (
    CreateOTP,
    DeleteOTP,
)


class DashOTPRoutes:
    def __init__(self, otp_service, role_deps):
        self.otp_service = otp_service
        self.role_deps = role_deps

        self.router = APIRouter(prefix="/otp", tags=["OTP ops"])
        self.register()

    def register(self):
        current = Depends(self.role_deps.require("superadmin"))

        @self.router.get("/")
        def get_otp_codes(
            user=current,
            page: int = Query(1, ge=1),
            limit: int = Query(10, ge=1, le=100),
        ):
            return self.otp_service.get_all(
                page=page,
                limit=limit,
            )

        @self.router.get("/query")
        def query_otp_codes(
            user=current,
            identifier: str = Query(..., description="OTP identifier"),
        ):
            return self.otp_service.query(
                identifier=identifier,
            )

        @self.router.post("/")
        def create_otp(body: CreateOTP, user=current):
            return self.otp_service.create(**body.model_dump())

        @self.router.delete("/")
        def delete_otp(body: DeleteOTP, user=current):    
            self.otp_service.revoke(**body.model_dump())
            return {"success": True, "message": "OTP revoked successfully"}

        @self.router.delete("/cleanup")
        def cleanup(user=current):
            self.otp_service.cleanup()
            return {"success": True, "message": "Expired OTPs cleaned up successfully"}

        @self.router.delete("/clear")
        def clear(user=current):
            self.otp_service.clear_all()
            return {"success": True, "message": "All OTPs cleared successfully"}
