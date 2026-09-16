from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class CreateSnapshotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Snapshot identifier name (alphanumeric, hyphens, and underscores only)",
    )
    source: Literal["tcauth", "server"] = Field(
        ...,
        description="Source primary log to snapshot ('tcauth' or 'server')",
    )


class LoggingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    logging: bool | None = Field(
        default=None,
        description="Whether logging is globally enabled or disabled.",
    )
    enabled: bool | None = Field(
        default=None,
        description="Alias for logging toggle.",
    )
    logs_dir: str | None = Field(
        default=None,
        description="Base directory for log files. Defaults to 'logs/' in working directory.",
    )
    static_mount_logs: bool | None = Field(
        default=None,
        description="Whether to expose the logs directory via a static mount at /logs",
    )
    static_mount_log: bool | None = Field(
        default=None,
        description="Alias for static_mount_logs toggle.",
    )
    level: str | None = Field(
        default=None,
        description="Logging level threshold (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    console_output: bool | None = Field(
        default=None,
        description="Whether to echo application logs to the console/stdout",
    )
    capture_terminal: bool | None = Field(
        default=None,
        description="Whether to capture all terminal print() statements to server.log",
    )
    redact_sensitive: bool | None = Field(
        default=None,
        description="Whether to automatically redact sensitive fields (tokens, passwords, cookies)",
    )
    redact_patterns: list[str] | None = Field(
        default=None,
        description="List of custom regex patterns to redact in application logs and captured prints",
    )

