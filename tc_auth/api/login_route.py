from fastapi import applications
from fastapi import APIRouter, Request

from ..schema import (
    SendOTPRequest,
    LoginPasswordRequest,
    LoginOTPRequest,
    SignupPasswordRequest,
    SignupOTPRequest,
)


class AuthRoutes:
    def __init__(
        self,
        email_service,
        auth_service,
        otp_service,
        get_user,
    ):
        self.email_service = email_service
        self.auth_service = auth_service
        self.otp_service = otp_service
        self.get_user = get_user

        self.router = APIRouter(tags=["Sign UP / IN"])

        self.router.post("/send/email/otp/{purpose}")(self.send_email_otp)
        self.router.post("/signup/otp")(self.signup_with_otp)
        self.router.post("/signup/password")(self.signup_with_password)
        self.router.post("/login/otp")(self.login_with_otp)
        self.router.post("/login/password")(self.login_with_password)
        self.router.post("/forgot/password")(self.forgot_password)

    # ==========================================================
    # EMAIL OTP
    # ==========================================================

    def send_email_otp(
        self,
        purpose: str,
        body: SendOTPRequest,
    ):
        # purpose must be signup , login , reset , verify
        return self.email_service.send_otp(
            email=body.email,
            purpose=purpose,
        )

    # ==========================================================
    # SIGNUP WITH OTP
    # ==========================================================

    def signup_with_otp(
        self,
        request: Request,
        body: SignupOTPRequest,
    ):
        self.otp_service.verify(
            identifier=body.email,
            purpose="signup",
            otp=body.otp,
        )

        return self.auth_service.signup(
            name=body.name,
            email=body.email,
            password=body.password,
            handle=body.handle,
            **self._request_meta(request),
        )
    
    # ==========================================================
    # SIGNUP WITH PASSWORD
    # ==========================================================

    def signup_with_password(
        self,
        request: Request,
        body: SignupPasswordRequest,
    ):
        return self.auth_service.signup(
            name=body.name,
            email=body.email,
            handle=body.handle,
            password=body.password,
            **self._request_meta(request),
        )

    # ==========================================================
    # LOGIN WITH OTP
    # ==========================================================

    def login_with_otp(
        self,
        request: Request,
        body: LoginOTPRequest,
    ):
        self.otp_service.verify(
            identifier=body.email,
            purpose="login",
            otp=body.otp,
        )

        account = self.get_user.by_email(
            email=body.email,
        )

        return self.auth_service.create_login_response(
            account=account,
            **self._request_meta(request),
        )


    # ==========================================================
    # LOGIN WITH PASSWORD
    # ==========================================================

    def login_with_password(
        self,
        request: Request,
        body: LoginPasswordRequest,
    ):
        return self.auth_service.login(
            identifier=body.identifier,
            password=body.password,
            **self._request_meta(request),
        )
    
    # ==========================================================
    # FORGOT PASSWORD
    # ==========================================================
    
    def forgot_password(
        self,
        request: Request,
        body: LoginOTPRequest,
    ):
        
        self.otp_service.verify(
            identifier=body.email,
            purpose="reset",
            otp=body.otp,
        )

        account = self.get_user.by_email(
            email=body.email,
        )

        self.auth_service.update_password(
            account["id"],
            password=body.password
        )


        return self.auth_service.create_login_response(
            account=account,
            **self._request_meta(request),
        )

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