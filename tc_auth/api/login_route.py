from urllib.parse import quote_plus
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from ..schema import (
    SendOTPRequest,
    SendMagicLinkRequest,
    VerifyMagicLinkRequest,
    LoginPasswordRequest,
    LoginOTPRequest,
    ForgotPasswordRequest,
    SignupPasswordRequest,
    SignupOTPRequest,
    RefreshTokenRequest,
)
from ..exceptions.error import (
    AuthError,
    InvalidEmailPurposeError,
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
        self.router.post("/send/email/link/{purpose}")(self.send_email_link)
        self.router.get("/link/{purpose}", name="verify_magic_link_get")(self.verify_magic_link_get)
        self.router.post("/link/{purpose}", name="verify_magic_link_post")(self.verify_magic_link_post)
        self.router.post("/signup/otp")(self.signup_with_otp)
        self.router.post("/signup/password")(self.signup_with_password)
        self.router.post("/login/otp")(self.login_with_otp)
        self.router.post("/login/password")(self.login_with_password)
        self.router.post("/forgot/password")(self.forgot_password)
        self.router.post("/token/refresh")(self.refresh_token)

    # ==========================================================
    # EMAIL OTP
    # ==========================================================

    def send_email_otp(
        self,
        request: Request,
        purpose: str,
        body: SendOTPRequest,
    ):
        normalized_purpose = purpose.strip().lower()
        valid_purposes = {"signup", "login", "reset", "verify"}
        if normalized_purpose not in valid_purposes:
            raise InvalidEmailPurposeError(purpose)

        backend_url = self._get_backend_url(request)
        frontend_url = (
            body.frontend_url
            or request.query_params.get("frontend_url")
            or request.headers.get("origin")
        )

        return self.email_service.send_otp(
            email=body.email,
            purpose=normalized_purpose,
            frontend_url=frontend_url,
            backend_url=backend_url,
        )

    # ==========================================================
    # MAGIC LINK
    # ==========================================================

    def send_email_link(
        self,
        request: Request,
        purpose: str,
        body: SendMagicLinkRequest,
    ):
        normalized_purpose = purpose.strip().lower()
        valid_purposes = {"signup", "login", "reset", "verify"}
        if normalized_purpose not in valid_purposes:
            raise InvalidEmailPurposeError(purpose)

        backend_url = self._get_backend_url(request)
        frontend_url = (
            body.frontend_url
            or request.query_params.get("frontend_url")
            or request.headers.get("origin")
            or backend_url
        )

        return self.email_service.send_magic_link(
            email=body.email,
            purpose=normalized_purpose,
            frontend_url=frontend_url,
            backend_url=backend_url,
        )

    def verify_magic_link_get(
        self,
        request: Request,
        purpose: str,
        email: str,
        otp: str,
        frontend_url: str | None = None,
    ):
        normalized_purpose = purpose.strip().lower()
        valid_purposes = {"signup", "login", "reset", "verify"}
        base_fe = (
            frontend_url.rstrip("/")
            if frontend_url and frontend_url.strip()
            else (request.headers.get("origin") or self._get_backend_url(request)).rstrip("/")
        )

        if normalized_purpose not in valid_purposes:
            return RedirectResponse(
                url=f"{base_fe}/magic-link/callback?error={quote_plus('Invalid purpose')}",
                status_code=307,
            )

        try:
            if normalized_purpose == "login":
                login_data = self.auth_service.login_magic_link(
                    email=email,
                    otp=otp,
                    **self._request_meta(request),
                )
                access_token = login_data["access_token"]
                refresh_token = login_data.get("refresh_token")
                params = [f"access_token={quote_plus(access_token)}"]
                if refresh_token:
                    params.append(f"refresh_token={quote_plus(refresh_token)}")
                target = f"{base_fe}/oauth/callback?{'&'.join(params)}"
                return RedirectResponse(url=target, status_code=307)

            elif normalized_purpose == "verify":
                self.auth_service.verify_email_magic_link(
                    email=email,
                    otp=otp,
                )
                target = f"{base_fe}/magic-link/callback?verified=true&email={quote_plus(email)}"
                return RedirectResponse(url=target, status_code=307)

            elif normalized_purpose == "reset":
                self.otp_service.check(
                    identifier=email,
                    purpose="reset",
                    otp=otp,
                )
                target = f"{base_fe}/reset-password?email={quote_plus(email)}&otp={quote_plus(otp)}"
                return RedirectResponse(url=target, status_code=307)

            elif normalized_purpose == "signup":
                self.otp_service.check(
                    identifier=email,
                    purpose="signup",
                    otp=otp,
                )
                target = f"{base_fe}/signup?email={quote_plus(email)}&otp={quote_plus(otp)}&verified=true"
                return RedirectResponse(url=target, status_code=307)

        except Exception as e:
            error_msg = getattr(e, "message", str(e))
            return RedirectResponse(
                url=f"{base_fe}/magic-link/callback?error={quote_plus(error_msg)}",
                status_code=307,
            )

    def verify_magic_link_post(
        self,
        request: Request,
        purpose: str,
        body: VerifyMagicLinkRequest,
    ):
        normalized_purpose = purpose.strip().lower()
        valid_purposes = {"signup", "login", "reset", "verify"}
        if normalized_purpose not in valid_purposes:
            raise InvalidEmailPurposeError(purpose)

        if normalized_purpose == "login":
            return self.auth_service.login_magic_link(
                email=body.email,
                otp=body.otp,
                **self._request_meta(request),
            )

        elif normalized_purpose == "verify":
            return self.auth_service.verify_email_magic_link(
                email=body.email,
                otp=body.otp,
            )

        elif normalized_purpose in {"reset", "signup"}:
            self.otp_service.check(
                identifier=body.email,
                purpose=normalized_purpose,
                otp=body.otp,
            )
            return {
                "success": True,
                "message": f"OTP verified successfully for {normalized_purpose}",
                "email": body.email,
            }

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
        body: ForgotPasswordRequest,
    ):
        if not getattr(body, "password", None):
            raise AuthError("New password is required to reset password")

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
            password=body.password,
        )

        return self.auth_service.create_login_response(
            account=account,
            **self._request_meta(request),
        )

    # ==========================================================
    # REFRESH TOKEN
    # ==========================================================

    def refresh_token(
        self,
        body: RefreshTokenRequest,
    ):
        return self.auth_service.refresh_tokens(body.refresh_token)

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

    def _get_backend_url(
        self,
        request: Request,
    ) -> str:
        proto = request.headers.get("x-forwarded-proto") or request.url.scheme
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
        if proto and host:
            return f"{proto}://{host}".rstrip("/")
        return str(request.base_url).rstrip("/")