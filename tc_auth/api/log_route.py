from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import StreamingResponse

from ..exceptions.error import LoggingDisabledError
from ..schema.log import CreateSnapshotRequest
from ..service.log_service import LogService


class LogRoutes:
    """
    API Routes for log management, snapshots, resets, and SSE streaming.
    All routes require administrative privileges ('superadmin' role).
    """

    def __init__(self, log_service: LogService, role_deps):
        self.log_service = log_service
        self.role_deps = role_deps

        def check_logging_enabled():
            if not getattr(self.log_service, "logging", True):
                raise LoggingDisabledError("Logging is disabled")

        self.router = APIRouter(
            prefix="/log",
            tags=["Log Management"],
            dependencies=[Depends(check_logging_enabled)],
        )
        self.register()

    def register(self):
        current = Depends(self.role_deps.require("superadmin"))

        # ------------------------------------------------------
        # 1. Summary & Snapshot Creation
        # ------------------------------------------------------

        @self.router.get("", summary="List all primary logs and snapshots")
        @self.router.get("/", include_in_schema=False)
        def get_logs(user=current):
            return self.log_service.list_logs()

        @self.router.post(
            "",
            status_code=status.HTTP_201_CREATED,
            summary="Create a snapshot of a primary log",
        )
        @self.router.post(
            "/",
            status_code=status.HTTP_201_CREATED,
            include_in_schema=False,
        )
        def create_snapshot(body: CreateSnapshotRequest, user=current):
            return self.log_service.create_snapshot(name=body.name, source=body.source)

        # ------------------------------------------------------
        # 2. SSE Streams (Registered before parameter paths)
        # ------------------------------------------------------

        @self.router.get(
            "/tcauth/stream",
            summary="Real-time SSE stream of tcauth application logs",
        )
        async def stream_tcauth(request: Request, user=current):
            return StreamingResponse(
                self.log_service.stream_logs("tcauth", request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        @self.router.get(
            "/server/stream",
            summary="Real-time SSE stream of Uvicorn server logs",
        )
        async def stream_server(request: Request, user=current):
            return StreamingResponse(
                self.log_service.stream_logs("server", request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        # ------------------------------------------------------
        # 3. Primary Log Resets
        # ------------------------------------------------------

        @self.router.post(
            "/tcauth/reset",
            summary="Reset tcauth.log (truncate to 0 bytes)",
        )
        def reset_tcauth(user=current):
            return self.log_service.reset_log("tcauth")

        @self.router.post(
            "/server/reset",
            summary="Reset server.log (truncate to 0 bytes)",
        )
        def reset_server(user=current):
            return self.log_service.reset_log("server")

        # ------------------------------------------------------
        # 4. Primary Log Contents
        # ------------------------------------------------------

        @self.router.get(
            "/tcauth",
            summary="Get tcauth.log application log contents",
        )
        def get_tcauth(
            user=current,
            limit: int | None = Query(None, ge=1, le=5000, description="Max records to return"),
            offset: int = Query(0, ge=0, description="Record offset"),
        ):
            return self.log_service.get_log_content("tcauth", limit=limit, offset=offset)

        @self.router.get(
            "/server",
            summary="Get server.log Uvicorn server log contents",
        )
        def get_server(
            user=current,
            limit: int | None = Query(None, ge=1, le=5000, description="Max lines to return"),
            offset: int = Query(0, ge=0, description="Line offset"),
        ):
            return self.log_service.get_log_content("server", limit=limit, offset=offset)

        # ------------------------------------------------------
        # 5. Generic Snapshot / Log by Name
        # ------------------------------------------------------

        @self.router.get(
            "/{name}",
            summary="Get log content by name (primary log or snapshot)",
        )
        def get_log_by_name(
            name: str,
            user=current,
            limit: int | None = Query(None, ge=1, le=5000, description="Max records/lines to return"),
            offset: int = Query(0, ge=0, description="Offset"),
        ):
            return self.log_service.get_log_content(name=name, limit=limit, offset=offset)

        @self.router.delete(
            "/{name}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Delete a stored log snapshot",
        )
        def delete_snapshot(name: str, user=current):
            self.log_service.delete_snapshot(name=name)
            return Response(status_code=status.HTTP_204_NO_CONTENT)


# Alias
LogRoute = LogRoutes
