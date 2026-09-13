from fastapi import Request, Response
from .exceptions.error import InvalidConfigError
from . import jwt_handler


VALID_SAMESITE = {"lax", "strict", "none"}


class CookieService:
    def __init__(self):
        self.cookie_mode: bool = False
        self.access_cookie_name: str = "access_token"
        self.refresh_cookie_name: str = "refresh_token"
        self.path: str = "/"
        self.domain: str | None = None
        self.secure: bool = False
        self.httponly: bool = True
        self.samesite: str = "lax"
        self.max_age: int | None = None

    def is_cookie_mode(self) -> bool:
        return self.cookie_mode

    def config(
        self,
        *,
        cookie_mode: bool = False,
        access_cookie_name: str = "access_token",
        refresh_cookie_name: str = "refresh_token",
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = True,
        samesite: str = "lax",
        max_age: int | None = None,
    ) -> dict:
        if not isinstance(cookie_mode, bool):
            raise InvalidConfigError("Cookie", "cookie_mode must be a boolean")

        if not access_cookie_name or not isinstance(access_cookie_name, str) or not access_cookie_name.strip():
            raise InvalidConfigError("Cookie", "access_cookie_name must be a non-empty string")

        if not refresh_cookie_name or not isinstance(refresh_cookie_name, str) or not refresh_cookie_name.strip():
            raise InvalidConfigError("Cookie", "refresh_cookie_name must be a non-empty string")

        if not path or not isinstance(path, str) or not path.strip():
            raise InvalidConfigError("Cookie", "path must be a non-empty string")

        clean_samesite = str(samesite).strip().lower() if samesite else "lax"
        if clean_samesite not in VALID_SAMESITE:
            raise InvalidConfigError(
                "Cookie",
                f"Invalid samesite '{samesite}'. Supported values: {', '.join(sorted(VALID_SAMESITE))}",
            )

        if not isinstance(secure, bool):
            raise InvalidConfigError("Cookie", "secure must be a boolean")

        if not isinstance(httponly, bool):
            raise InvalidConfigError("Cookie", "httponly must be a boolean")

        if clean_samesite == "none" and not secure:
            raise InvalidConfigError(
                "Cookie",
                "SameSite='none' requires secure=True (browsers reject insecure SameSite=None cookies)",
            )

        if max_age is not None:
            if not isinstance(max_age, int) or max_age < 1:
                raise InvalidConfigError("Cookie", "max_age must be an integer >= 1")

        self.cookie_mode = cookie_mode
        self.access_cookie_name = access_cookie_name.strip()
        self.refresh_cookie_name = refresh_cookie_name.strip()
        self.path = path.strip()
        self.domain = domain.strip() if domain and isinstance(domain, str) and domain.strip() else None
        self.secure = secure
        self.httponly = httponly
        self.samesite = clean_samesite
        self.max_age = max_age

        return {
            "success": True,
            "message": "Cookie configured successfully",
        }

    def load(self) -> dict:
        return {
            "cookie_mode": self.cookie_mode,
            "access_cookie_name": self.access_cookie_name,
            "refresh_cookie_name": self.refresh_cookie_name,
            "path": self.path,
            "domain": self.domain,
            "secure": self.secure,
            "httponly": self.httponly,
            "samesite": self.samesite,
            "max_age": self.max_age,
        }

    def get_cookie_info(self) -> dict:
        info = {
            "cookie_mode": self.cookie_mode,
            "access_cookie_name": self.access_cookie_name,
            "path": self.path,
            "domain": self.domain,
            "secure": self.secure,
            "samesite": self.samesite,
        }
        if jwt_handler.is_dual_token_mode():
            info["refresh_cookie_name"] = self.refresh_cookie_name
        return info

    def set_auth_cookies(
        self,
        response: Response,
        access_token: str,
        refresh_token: str | None = None,
    ) -> None:
        if not self.cookie_mode:
            return

        # Calculate max_age for access token
        access_max_age = self.max_age
        if access_max_age is None:
            if jwt_handler.is_dual_token_mode():
                access_max_age = jwt_handler.get_access_token_expire_minutes() * 60
            else:
                access_max_age = jwt_handler.get_session_duration_days() * 86400

        response.set_cookie(
            key=self.access_cookie_name,
            value=access_token,
            max_age=access_max_age,
            path=self.path,
            domain=self.domain,
            secure=self.secure,
            httponly=self.httponly,
            samesite=self.samesite,
        )

        if refresh_token:
            refresh_max_age = self.max_age
            if refresh_max_age is None:
                refresh_max_age = jwt_handler.get_refresh_token_expire_days() * 86400

            response.set_cookie(
                key=self.refresh_cookie_name,
                value=refresh_token,
                max_age=refresh_max_age,
                path=self.path,
                domain=self.domain,
                secure=self.secure,
                httponly=self.httponly,
                samesite=self.samesite,
            )

    def clear_auth_cookies(self, response: Response) -> None:
        response.delete_cookie(
            key=self.access_cookie_name,
            path=self.path,
            domain=self.domain,
            secure=self.secure,
            httponly=self.httponly,
            samesite=self.samesite,
        )
        response.delete_cookie(
            key=self.refresh_cookie_name,
            path=self.path,
            domain=self.domain,
            secure=self.secure,
            httponly=self.httponly,
            samesite=self.samesite,
        )

    def extract_access_token(self, request: Request) -> str | None:
        return request.cookies.get(self.access_cookie_name)

    def extract_refresh_token(self, request: Request) -> str | None:
        return request.cookies.get(self.refresh_cookie_name)
