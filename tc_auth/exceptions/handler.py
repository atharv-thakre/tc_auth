import sys
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse

from .error import AuthError


async def auth_exception_handler(
    request: Request,
    exc: AuthError,
):
    """
    Centralized exception handler for all AuthError instances in tc-auth.
    Logs every error event with complete HTTP context and metadata to tcauth.log,
    and returns a standardized JSON response to the client.
    """
    error_code = getattr(exc, "error_code", "auth_error")
    status_code = getattr(exc, "status_code", 400)
    details = getattr(exc, "details", None)
    event_name = error_code.upper() if error_code else "AUTH_ERROR"

    # Extract HTTP request context safely
    method = None
    path = None
    client_ip = None
    user_agent = None
    request_id = None

    if request is not None:
        try:
            method = getattr(request, "method", None)
            if hasattr(request, "url") and hasattr(request.url, "path"):
                path = str(request.url.path)
            if hasattr(request, "client") and request.client:
                client_ip = request.client.host
            if hasattr(request, "headers"):
                user_agent = request.headers.get("user-agent")
                request_id = request.headers.get("x-request-id") or request.headers.get("x-correlation-id")
        except Exception:
            pass

    # Determine stack trace for 5xx errors or if exception has traceback
    stack_trace = None
    if status_code >= 500:
        tb = getattr(exc, "__traceback__", None)
        if tb:
            stack_trace = "".join(traceback.format_exception(type(exc), exc, tb))

    # Log to tcauth.log via LogService
    try:
        from ..service.log_service import LogService
        log_service = LogService.get_current()
        log_service.log_event(
            level="ERROR",
            event=event_name,
            message=str(exc),
            request_id=request_id,
            method=method,
            path=path,
            status_code=status_code,
            client_ip=client_ip,
            user_agent=user_agent,
            error={
                "type": exc.__class__.__name__,
                "code": error_code,
                "message": str(exc),
                "details": details,
            },
            exception={
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
            stack_trace=stack_trace,
        )
    except Exception as log_err:
        sys.stderr.write(f"[tc-auth] Exception handler logging failed: {log_err}\n")

    content = {
        "success": False,
        "message": str(exc),
        "error_code": error_code,
    }
    if details is not None:
        content["details"] = details

    return JSONResponse(
        status_code=status_code,
        content=content,
    )