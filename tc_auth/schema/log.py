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

    logs_dir: str | None = Field(
        default=None,
        description="Base directory for log files. Defaults to 'logs/' in working directory.",
    )
    static_mount_logs: bool = Field(
        default=False,
        description="Whether to expose the logs directory via a static mount at /logs",
    )
    level: str = Field(
        default="INFO",
        description="Logging level threshold (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    console_output: bool = Field(
        default=True,
        description="Whether to echo application logs to the console/stdout",
    )
    redact_sensitive: bool = Field(
        default=True,
        description="Whether to automatically redact sensitive fields (tokens, passwords, cookies)",
    )
