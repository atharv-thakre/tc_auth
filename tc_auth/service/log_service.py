import asyncio
import json
import logging
import os
import re
import shutil
import sys
import threading
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, AsyncGenerator

from ..exceptions.error import (
    InvalidConfigError,
    LogCannotDeletePrimaryError,
    LoggingDisabledError,
    LogSnapshotAlreadyExistsError,
    LogSnapshotNotFoundError,
    LogSourceInvalidError,
    LogUnsafeNameError,
)

# Standard logging levels
VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
PRIMARY_SOURCES = {"tcauth", "server"}

# Keys that must ALWAYS be redacted centrally
DEFAULT_SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "new_password",
    "old_password",
    "confirm_password",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "token_secret",
    "token_hash",
    "secret",
    "secret_key",
    "client_secret",
    "authorization_code",
    "session_secret",
    "private_key",
    "api_key",
    "apikey",
    "csrf_token",
    "cookie",
    "cookies",
    "set-cookie",
    "authorization",
    "proxy-authorization",
    "oauth_state",
    "state",
}

SAFE_METADATA_KEYS = {
    "error_code",
    "code",
    "event",
    "error",
    "exception",
    "token_type",
    "auth_type",
    "provider",
    "operation",
    "status",
    "status_code",
    "type",
    "field",
    "message",
    "timestamp",
    "level",
    "request_id",
    "method",
    "path",
    "client_ip",
    "user_agent",
    "duration_ms",
    "environment",
    "details",
    "metadata",
    "extra",
}


# Regex patterns for sensitive tokens in free text
JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]*")
BEARER_PATTERN = re.compile(r"Bearer\s+([A-Za-z0-9_\-\.]+)", re.IGNORECASE)
BASIC_AUTH_PATTERN = re.compile(r"Basic\s+([A-Za-z0-9+/=]+)", re.IGNORECASE)
NAME_VALIDATION_REGEX = re.compile(r"^[a-zA-Z0-9_-]+$")


class UvicornLogInterceptor(logging.Handler):
    """
    Custom logging handler attached to Uvicorn loggers to mirror terminal output
    to server.log and broadcast new lines to active SSE subscribers.
    """

    def __init__(self, log_service: "LogService"):
        super().__init__()
        self.log_service = log_service

    def emit(self, record: logging.LogRecord):
        try:
            if not getattr(self.log_service, "logging", True):
                return
            msg = self.format(record)
            self.log_service._append_server_log(msg)
        except Exception:
            self.handleError(record)


_current_log_service: "LogService | None" = None


class LogService:
    """
    Centralized logging service for tc-auth.
    Manages JSONL application logs (tcauth.log), Uvicorn server logs (server.log),
    snapshot storage (logs/store/), redaction, resetting, and real-time SSE streaming.
    """

    @classmethod
    def get_current(cls) -> "LogService":
        """Returns the current active LogService instance or creates a default one."""
        global _current_log_service
        if _current_log_service is None:
            _current_log_service = LogService()
        return _current_log_service

    @classmethod
    def set_current(cls, service: "LogService"):
        """Registers an active LogService instance."""
        global _current_log_service
        _current_log_service = service

    def __init__(
        self,
        logs_dir: str | Path | None = None,
        static_mount_logs: bool = False,
        level: str = "INFO",
        console_output: bool = True,
        redact_sensitive: bool = True,
        custom_redact_keys: list[str] | None = None,
        logging: bool = True,
        enabled: bool | None = None,
    ):
        self.logging = bool(enabled) if enabled is not None else bool(logging)
        self.logs_dir = Path(logs_dir).resolve() if logs_dir else (Path.cwd() / "logs").resolve()
        self.store_dir = self.logs_dir / "store"
        self.static_mount_logs = bool(static_mount_logs)
        self.level = level.upper() if isinstance(level, str) and level.upper() in VALID_LEVELS else "INFO"
        self.console_output = bool(console_output)
        self.redact_sensitive = bool(redact_sensitive)
        self.custom_redact_keys = set(k.lower() for k in custom_redact_keys) if custom_redact_keys else set()
        self._all_sensitive_keys = DEFAULT_SENSITIVE_KEYS.union(self.custom_redact_keys)

        # Thread safety locks
        self._tcauth_lock = threading.Lock()
        self._server_lock = threading.Lock()

        # SSE subscribers: source -> set of (loop, asyncio.Queue)
        self._subscribers: dict[str, set[tuple[asyncio.AbstractEventLoop, asyncio.Queue]]] = {
            "tcauth": set(),
            "server": set(),
        }
        self._subscriber_lock = threading.Lock()

        # Ensure directory structure and primary log files exist
        self._init_filesystem()

        # Attach Uvicorn logging interceptor
        self._uvicorn_handler: UvicornLogInterceptor | None = None
        self._setup_uvicorn_logging()

        # Set as current active logger
        LogService.set_current(self)


    # ==========================================================
    # INITIALIZATION & CONFIGURATION
    # ==========================================================

    def _init_filesystem(self):
        """Creates logs/ and logs/store/ directories and primary log files if missing."""
        try:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            self.store_dir.mkdir(parents=True, exist_ok=True)

            tcauth_path = self.logs_dir / "tcauth.log"
            if not tcauth_path.exists():
                tcauth_path.touch(exist_ok=True)

            server_path = self.logs_dir / "server.log"
            if not server_path.exists():
                server_path.touch(exist_ok=True)
        except Exception as e:
            sys.stderr.write(f"[tc-auth LogService] Error creating log directories: {e}\n")

    def _setup_uvicorn_logging(self):
        """Hooks into Uvicorn loggers so standard server output is written to server.log."""
        try:
            if self._uvicorn_handler is None:
                self._uvicorn_handler = UvicornLogInterceptor(self)
                formatter = logging.Formatter(
                    fmt="%(levelname)s:\t%(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
                self._uvicorn_handler.setFormatter(formatter)

                for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
                    target_logger = logging.getLogger(logger_name)
                    if self._uvicorn_handler not in target_logger.handlers:
                        target_logger.addHandler(self._uvicorn_handler)
        except Exception as e:
            sys.stderr.write(f"[tc-auth LogService] Error setting up Uvicorn logger: {e}\n")

    @property
    def enabled(self) -> bool:
        return self.logging

    @enabled.setter
    def enabled(self, value: bool):
        self.logging = bool(value)

    @property
    def is_configured(self) -> bool:
        return self.logs_dir.exists() and self.store_dir.exists()

    def _check_enabled(self):
        """Raises LoggingDisabledError if logging is disabled."""
        if not self.logging:
            raise LoggingDisabledError("Logging is disabled")

    def config(
        self,
        *,
        logging: bool | None = None,
        enabled: bool | None = None,
        logs_dir: str | Path | None = None,
        static_mount_logs: bool = False,
        level: str = "INFO",
        console_output: bool = True,
        redact_sensitive: bool = True,
        custom_redact_keys: list[str] | None = None,
    ) -> dict:
        """
        Configures the logging service settings.
        """
        if logging is not None:
            if not isinstance(logging, bool):
                raise InvalidConfigError("Logging", "logging must be a boolean")
            self.logging = logging

        if enabled is not None:
            if not isinstance(enabled, bool):
                raise InvalidConfigError("Logging", "enabled must be a boolean")
            self.logging = enabled

        if logs_dir is not None:
            if not isinstance(logs_dir, (str, Path)) or not str(logs_dir).strip():
                raise InvalidConfigError("Logging", "logs_dir must be a non-empty string or Path")
            new_logs_dir = Path(logs_dir).resolve()
            self.logs_dir = new_logs_dir
            self.store_dir = self.logs_dir / "store"

        if not isinstance(static_mount_logs, bool):
            raise InvalidConfigError("Logging", "static_mount_logs must be a boolean")

        if not isinstance(level, str) or level.upper() not in VALID_LEVELS:
            raise InvalidConfigError(
                "Logging",
                f"Invalid level '{level}'. Supported levels: {', '.join(sorted(VALID_LEVELS))}",
            )

        if not isinstance(console_output, bool):
            raise InvalidConfigError("Logging", "console_output must be a boolean")

        if not isinstance(redact_sensitive, bool):
            raise InvalidConfigError("Logging", "redact_sensitive must be a boolean")

        if custom_redact_keys is not None:
            if not isinstance(custom_redact_keys, list) or not all(isinstance(k, str) for k in custom_redact_keys):
                raise InvalidConfigError("Logging", "custom_redact_keys must be a list of strings")
            self.custom_redact_keys = set(k.lower() for k in custom_redact_keys)

        self.static_mount_logs = static_mount_logs
        self.level = level.upper()
        self.console_output = console_output
        self.redact_sensitive = redact_sensitive
        self._all_sensitive_keys = DEFAULT_SENSITIVE_KEYS.union(self.custom_redact_keys)

        self._init_filesystem()
        self._setup_uvicorn_logging()

        return {
            "success": True,
            "message": "Logging service configured successfully",
        }

    def load(self) -> dict:
        """
        Returns the current logging configuration.
        """
        return {
            "logging": self.logging,
            "enabled": self.logging,
            "logs_dir": str(self.logs_dir),
            "store_dir": str(self.store_dir),
            "static_mount_logs": self.static_mount_logs,
            "level": self.level,
            "console_output": self.console_output,
            "redact_sensitive": self.redact_sensitive,
            "custom_redact_keys": sorted(list(self.custom_redact_keys)),
        }

    # ==========================================================
    # SENSITIVE DATA REDACTION
    # ==========================================================

    def redact(self, value: Any) -> Any:
        """
        Recursively redacts sensitive keys and values from dictionaries, lists, strings, and query params.
        """
        if not self.redact_sensitive:
            return value

        if isinstance(value, dict):
            redacted_dict = {}
            for k, v in value.items():
                k_str = str(k)
                k_lower = k_str.lower().replace("-", "_")

                # If key is explicitly marked as safe metadata, recursively redact its children
                if k_lower in SAFE_METADATA_KEYS:
                    redacted_dict[k] = self.redact(v)
                elif (
                    k_lower in self._all_sensitive_keys
                    or any(
                        s in k_lower
                        for s in ("password", "secret", "private_key", "api_key", "apikey", "csrf_token")
                    )
                    or (
                        any(s in k_lower for s in ("token", "cookie", "auth"))
                        and not any(safe in k_lower for safe in ("token_type", "auth_type", "error", "event", "code", "type", "provider", "operation"))
                    )
                ):
                    redacted_dict[k] = "[REDACTED]"
                else:
                    redacted_dict[k] = self.redact(v)
            return redacted_dict


        if isinstance(value, list):
            return [self.redact(item) for item in value]

        if isinstance(value, tuple):
            return tuple(self.redact(item) for item in value)

        if isinstance(value, set):
            return {self.redact(item) for item in value}

        if isinstance(value, str):
            # Check for JWT pattern
            val = JWT_PATTERN.sub("[REDACTED]", value)
            val = BEARER_PATTERN.sub("Bearer [REDACTED]", val)
            val = BASIC_AUTH_PATTERN.sub("Basic [REDACTED]", val)
            return val

        return value

    # ==========================================================
    # APPLICATION LOGGING (tcauth.log - JSONL)
    # ==========================================================

    def log_event(
        self,
        level: str,
        event: str,
        message: str,
        *,
        request_id: str | None = None,
        method: str | None = None,
        path: str | None = None,
        status_code: int | None = None,
        client_ip: str | None = None,
        user_agent: str | None = None,
        duration_ms: float | None = None,
        provider: str | None = None,
        operation: str | None = None,
        environment: str | None = None,
        error: dict[str, Any] | None = None,
        exception: dict[str, Any] | None = None,
        stack_trace: str | None = None,
        metadata: dict[str, Any] | None = None,
        **extra,
    ):
        """
        Logs an application event in JSONL format to tcauth.log and broadcasts to SSE subscribers.
        """
        if not self.logging:
            return

        clean_level = level.upper() if isinstance(level, str) and level.upper() in VALID_LEVELS else "INFO"

        record: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": clean_level,
            "event": str(event),
            "message": str(message),
        }

        # Include optional metadata if provided (never fabricate)
        if request_id is not None:
            record["request_id"] = str(request_id)
        if method is not None:
            record["method"] = str(method)
        if path is not None:
            record["path"] = str(path)
        if status_code is not None:
            record["status_code"] = int(status_code)
        if client_ip is not None:
            record["client_ip"] = str(client_ip)
        if user_agent is not None:
            record["user_agent"] = str(user_agent)
        if duration_ms is not None:
            record["duration_ms"] = round(float(duration_ms), 2)
        if provider is not None:
            record["provider"] = str(provider)
        if operation is not None:
            record["operation"] = str(operation)
        if environment is not None:
            record["environment"] = str(environment)
        if error is not None:
            record["error"] = error
        if exception is not None:
            record["exception"] = exception
        if stack_trace is not None:
            record["stack_trace"] = str(stack_trace)
        if metadata is not None:
            record["metadata"] = metadata
        if extra:
            record["extra"] = extra

        # Redact sensitive data
        sanitized_record = self.redact(record)

        try:
            json_line = json.dumps(sanitized_record, default=str, ensure_ascii=False)
        except Exception as json_err:
            json_line = json.dumps({
                "timestamp": datetime.now(UTC).isoformat(),
                "level": "ERROR",
                "event": "LOG_SERIALIZATION_FAILED",
                "message": f"Failed to serialize log record: {str(json_err)}",
            })

        # Append to tcauth.log safely
        self._append_tcauth_log(json_line)

        # Output to console if enabled
        if self.console_output:
            try:
                print(f"[tc-auth] {clean_level} [{event}]: {message}")
            except Exception:
                pass

    def _append_tcauth_log(self, json_line: str):
        """Thread-safely appends a JSON line to tcauth.log and broadcasts to subscribers."""
        if not self.logging:
            return
        try:
            tcauth_path = self.logs_dir / "tcauth.log"
            with self._tcauth_lock:
                with open(tcauth_path, "a", encoding="utf-8") as f:
                    f.write(json_line + "\n")
                    f.flush()
        except Exception as e:
            sys.stderr.write(f"[tc-auth LogService] Failed to write to tcauth.log: {e}\n")

        self._broadcast_sse("tcauth", json_line)

    def _append_server_log(self, text_line: str):
        """Thread-safely appends a line to server.log and broadcasts to subscribers."""
        if not self.logging:
            return
        try:
            server_path = self.logs_dir / "server.log"
            with self._server_lock:
                with open(server_path, "a", encoding="utf-8") as f:
                    f.write(text_line + "\n")
                    f.flush()
        except Exception as e:
            sys.stderr.write(f"[tc-auth LogService] Failed to write to server.log: {e}\n")

        self._broadcast_sse("server", text_line)

    # ==========================================================
    # CONVENIENCE LOGGING METHODS
    # ==========================================================

    def info(self, event: str, message: str, **kwargs):
        self.log_event("INFO", event, message, **kwargs)

    def debug(self, event: str, message: str, **kwargs):
        self.log_event("DEBUG", event, message, **kwargs)

    def warning(self, event: str, message: str, **kwargs):
        self.log_event("WARNING", event, message, **kwargs)

    def error(
        self,
        event: str,
        message: str,
        *,
        error: dict[str, Any] | None = None,
        exc_info: Exception | None = None,
        **kwargs,
    ):
        exception_data = None
        stack_trace = None
        if exc_info is not None:
            exception_data = {
                "type": exc_info.__class__.__name__,
                "message": str(exc_info),
            }
            stack_trace = "".join(traceback.format_exception(type(exc_info), exc_info, exc_info.__traceback__))

        self.log_event(
            "ERROR",
            event,
            message,
            error=error,
            exception=exception_data,
            stack_trace=stack_trace,
            **kwargs,
        )

    def critical(
        self,
        event: str,
        message: str,
        *,
        error: dict[str, Any] | None = None,
        exc_info: Exception | None = None,
        **kwargs,
    ):
        exception_data = None
        stack_trace = None
        if exc_info is not None:
            exception_data = {
                "type": exc_info.__class__.__name__,
                "message": str(exc_info),
            }
            stack_trace = "".join(traceback.format_exception(type(exc_info), exc_info, exc_info.__traceback__))

        self.log_event(
            "CRITICAL",
            event,
            message,
            error=error,
            exception=exception_data,
            stack_trace=stack_trace,
            **kwargs,
        )

    def log_auth_error(
        self,
        exc: Exception,
        event: str = "AUTH_ERROR",
        message: str | None = None,
        **kwargs,
    ):
        """Specialized helper for logging tc-auth AuthError exceptions."""
        error_details = {
            "type": exc.__class__.__name__,
            "code": getattr(exc, "error_code", "auth_error"),
            "message": str(exc),
        }
        if getattr(exc, "details", None) is not None:
            error_details["details"] = getattr(exc, "details")

        msg = message or str(exc)
        self.error(event=event, message=msg, error=error_details, exc_info=exc, **kwargs)

    # ==========================================================
    # PATH SAFETY & VALIDATION
    # ==========================================================

    def _validate_source(self, source: str) -> str:
        """Validates primary source is 'tcauth' or 'server'."""
        if not source or not isinstance(source, str):
            raise LogSourceInvalidError(source=str(source))
        src = source.strip().lower()
        if src not in PRIMARY_SOURCES:
            raise LogSourceInvalidError(source=src)
        return src

    def _validate_snapshot_name(self, name: str) -> str:
        """Validates snapshot name for security and path traversal prevention."""
        if not name or not isinstance(name, str):
            raise LogUnsafeNameError(name=str(name))

        cleaned = name.strip()
        if not cleaned or len(cleaned) > 64 or not NAME_VALIDATION_REGEX.match(cleaned):
            raise LogUnsafeNameError(
                name=cleaned,
                message=f"Invalid snapshot name '{cleaned}'. Name must be 1-64 characters (alphanumeric, hyphens, underscores only).",
            )

        if ".." in cleaned or "/" in cleaned or "\\" in cleaned or ":" in cleaned or "\0" in cleaned:
            raise LogUnsafeNameError(name=cleaned, message="Snapshot name contains unsafe characters.")

        return cleaned

    def _get_primary_path(self, source: str) -> Path:
        src = self._validate_source(source)
        return self.logs_dir / f"{src}.log"

    def _get_snapshot_path(self, source: str, name: str) -> Path:
        src = self._validate_source(source)
        clean_name = self._validate_snapshot_name(name)
        target_file = self.store_dir / f"{src}-{clean_name}.log"

        # Verify path containment inside store_dir
        try:
            resolved_target = target_file.resolve()
            resolved_store = self.store_dir.resolve()
            if not str(resolved_target).startswith(str(resolved_store)):
                raise LogUnsafeNameError(name=name, message="Snapshot path escapes store directory.")
        except Exception:
            raise LogUnsafeNameError(name=name, message="Invalid snapshot path resolution.")

        return target_file

    # ==========================================================
    # SNAPSHOT MANAGEMENT
    # ==========================================================

    def create_snapshot(self, name: str, source: str) -> dict:
        """
        Creates a snapshot copy of a primary log file into logs/store/{source}-{name}.log.
        """
        self._check_enabled()
        src = self._validate_source(source)
        clean_name = self._validate_snapshot_name(name)
        src_path = self._get_primary_path(src)
        dst_path = self._get_snapshot_path(src, clean_name)

        if dst_path.exists():
            raise LogSnapshotAlreadyExistsError(
                name=clean_name,
                message=f"Snapshot '{clean_name}' for source '{src}' already exists.",
            )

        # Acquire lock to copy a consistent snapshot
        lock = self._tcauth_lock if src == "tcauth" else self._server_lock
        with lock:
            if not src_path.exists():
                src_path.touch(exist_ok=True)
            shutil.copyfile(src_path, dst_path)

        size_bytes = dst_path.stat().st_size if dst_path.exists() else 0
        created_at = datetime.fromtimestamp(dst_path.stat().st_ctime, UTC).isoformat() if dst_path.exists() else datetime.now(UTC).isoformat()

        return {
            "success": True,
            "message": f"Snapshot '{clean_name}' created successfully",
            "snapshot": {
                "name": dst_path.name[:-4],
                "source": src,
                "filename": dst_path.name,
                "format": "jsonl" if src == "tcauth" else "text",
                "size_bytes": size_bytes,
                "created_at": created_at,
            },
        }

    def list_logs(self) -> dict:
        """
        Returns a summary of primary logs and all stored snapshots.
        """
        self._check_enabled()
        primary_logs = []
        for src in ("tcauth", "server"):
            path = self.logs_dir / f"{src}.log"
            size_bytes = path.stat().st_size if path.exists() else 0
            updated_at = datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat() if path.exists() else None
            primary_logs.append({
                "name": src,
                "source": src,
                "filename": f"{src}.log",
                "format": "jsonl" if src == "tcauth" else "text",
                "size_bytes": size_bytes,
                "streamable": True,
                "resettable": True,
                "deletable": False,
                "updated_at": updated_at,
            })

        snapshots = []
        if self.store_dir.exists():
            for entry in sorted(self.store_dir.glob("*.log")):
                if not entry.is_file():
                    continue
                filename = entry.name
                snap_full_name = filename[:-4] if filename.endswith(".log") else filename
                # Parse source
                if filename.startswith("tcauth-"):
                    source = "tcauth"
                    log_format = "jsonl"
                elif filename.startswith("server-"):
                    source = "server"
                    log_format = "text"
                else:
                    source = "unknown"
                    log_format = "text"

                stat = entry.stat()
                snapshots.append({
                    "name": snap_full_name,
                    "source": source,
                    "filename": filename,
                    "format": log_format,
                    "size_bytes": stat.st_size,
                    "streamable": False,
                    "resettable": False,
                    "deletable": True,
                    "created_at": datetime.fromtimestamp(stat.st_ctime, UTC).isoformat(),
                    "updated_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
                })

        return {
            "success": True,
            "primary_logs": primary_logs,
            "snapshots": snapshots,
        }

    def get_log_content(
        self,
        name: str,
        limit: int | None = None,
        offset: int = 0,
    ) -> dict:
        """
        Retrieves log content for primary logs ('tcauth', 'server') or stored snapshots.
        """
        self._check_enabled()
        clean_name = name.strip()
        if clean_name.endswith(".log"):
            clean_name = clean_name[:-4]

        # 1. Primary logs
        if clean_name in PRIMARY_SOURCES:
            src = clean_name
            path = self._get_primary_path(src)
            if not path.exists():
                path.touch(exist_ok=True)
            return self._read_file_records(path, is_jsonl=(src == "tcauth"), limit=limit, offset=offset)

        # 2. Snapshot in store
        # Search by exact name, tcauth-{name}.log, server-{name}.log, or {name}.log
        matching_file: Path | None = None
        for candidate in (
            self.store_dir / f"tcauth-{clean_name}.log",
            self.store_dir / f"server-{clean_name}.log",
            self.store_dir / f"{clean_name}.log",
            self.store_dir / clean_name,
        ):
            if candidate.is_file():
                matching_file = candidate
                break

        if matching_file is None:
            raise LogSnapshotNotFoundError(name=clean_name)

        is_jsonl = matching_file.name.startswith("tcauth-")
        return self._read_file_records(matching_file, is_jsonl=is_jsonl, limit=limit, offset=offset)

    def _read_file_records(
        self,
        file_path: Path,
        is_jsonl: bool,
        limit: int | None = None,
        offset: int = 0,
    ) -> dict:
        """Reads file lines safely, optionally parsing JSON objects for JSONL logs."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read file: {str(e)}",
                "total_records": 0,
                "records": [],
            }

        total_records = len(lines)
        selected_lines = lines[offset:] if offset > 0 else lines
        if limit is not None and limit > 0:
            selected_lines = selected_lines[:limit]

        if is_jsonl:
            parsed_records = []
            for line in selected_lines:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    parsed_records.append(json.loads(line_str))
                except Exception:
                    parsed_records.append({"raw": line_str})
            return {
                "success": True,
                "filename": file_path.name,
                "format": "jsonl",
                "total_records": total_records,
                "count": len(parsed_records),
                "offset": offset,
                "records": parsed_records,
            }
        else:
            return {
                "success": True,
                "filename": file_path.name,
                "format": "text",
                "total_records": total_records,
                "count": len(selected_lines),
                "offset": offset,
                "records": [l.rstrip("\r\n") for l in selected_lines],
            }

    def delete_snapshot(self, name: str) -> dict:
        """
        Deletes a stored snapshot. Rejects deletion of primary logs.
        """
        self._check_enabled()
        clean_name = name.strip()
        if clean_name.endswith(".log"):
            clean_name = clean_name[:-4]

        if clean_name in PRIMARY_SOURCES:
            raise LogCannotDeletePrimaryError(source=clean_name)

        matching_file: Path | None = None
        for candidate in (
            self.store_dir / f"tcauth-{clean_name}.log",
            self.store_dir / f"server-{clean_name}.log",
            self.store_dir / f"{clean_name}.log",
            self.store_dir / clean_name,
        ):
            if candidate.is_file():
                matching_file = candidate
                break

        if matching_file is None:
            raise LogSnapshotNotFoundError(name=clean_name)

        try:
            matching_file.unlink()
        except Exception as e:
            sys.stderr.write(f"[tc-auth LogService] Error deleting snapshot: {e}\n")

        return {
            "success": True,
            "message": f"Snapshot '{clean_name}' deleted successfully",
        }

    def reset_log(self, source: str) -> dict:
        """
        Truncates the primary log file to 0 bytes and continues logging.
        """
        self._check_enabled()
        src = self._validate_source(source)
        path = self._get_primary_path(src)
        lock = self._tcauth_lock if src == "tcauth" else self._server_lock

        with lock:
            with open(path, "w", encoding="utf-8") as f:
                f.truncate(0)

        return {
            "success": True,
            "message": f"Primary log '{src}' has been reset successfully",
        }

    # ==========================================================
    # REAL-TIME SSE STREAMING
    # ==========================================================

    def _get_tail_records(self, source: str, count: int = 10) -> list[str]:
        """Reads the last `count` records from primary log file efficiently."""
        path = self._get_primary_path(source)
        if not path.exists():
            return []

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            records = [line.strip() for line in lines if line.strip()]
            return records[-count:] if len(records) > count else records
        except Exception:
            return []

    def _broadcast_sse(self, source: str, item: str):
        """Thread-safely pushes a new log item to all active SSE queues for source."""
        with self._subscriber_lock:
            subscribers = list(self._subscribers.get(source, set()))

        for loop, queue in subscribers:
            if loop.is_closed():
                continue
            try:
                loop.call_soon_threadsafe(self._safe_queue_put, queue, item)
            except Exception:
                pass

    @staticmethod
    def _safe_queue_put(queue: asyncio.Queue, item: str):
        try:
            if queue.full():
                # Drop oldest if queue is full to prevent memory buildup
                queue.get_nowait()
            queue.put_nowait(item)
        except Exception:
            pass

    def _register_subscriber(self, source: str, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue):
        with self._subscriber_lock:
            self._subscribers.setdefault(source, set()).add((loop, queue))

    def _unregister_subscriber(self, source: str, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue):
        with self._subscriber_lock:
            if source in self._subscribers:
                self._subscribers[source].discard((loop, queue))

    async def stream_logs(
        self,
        source: str,
        request: Any,
        tail_count: int = 10,
    ) -> AsyncGenerator[str, None]:
        """
        Async generator for Server-Sent Events (SSE).
        1. Immediately sends last `tail_count` records.
        2. Streams newly arriving events in real time.
        3. Sends periodic ping comments to keep connection active.
        """
        self._check_enabled()
        src = self._validate_source(source)
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue(maxsize=500)

        # 1. Send initial tail records
        initial_records = self._get_tail_records(src, count=tail_count)
        for record in initial_records:
            yield f"event: log\ndata: {record}\n\n"

        # 2. Register subscriber for live events
        self._register_subscriber(src, loop, queue)
        try:
            while True:
                # Check for client disconnect
                if hasattr(request, "is_disconnected") and await request.is_disconnected():
                    break

                try:
                    line = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: log\ndata: {line}\n\n"
                except asyncio.TimeoutError:
                    # Send keep-alive comment
                    yield ": ping\n\n"
        finally:
            self._unregister_subscriber(src, loop, queue)


# Alias for compatibility with instructions
Logging = LogService
