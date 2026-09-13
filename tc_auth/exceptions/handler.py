from fastapi import Request
from fastapi.responses import JSONResponse

from .error import AuthError


async def auth_exception_handler(
    request: Request,
    exc: AuthError,
):
    content = {
        "success": False,
        "message": str(exc),
        "error_code": getattr(exc, "error_code", "auth_error"),
    }
    if getattr(exc, "details", None) is not None:
        content["details"] = exc.details

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
    )