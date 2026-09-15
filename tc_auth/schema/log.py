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
    logs_dir: str | None = Field(
        default=None,
        description="Base directory for log files. Defaults to 'logs/' in working directory.",
    )
    static_mount_logs: bool | None = Field(
        default=None,
        description="Whether to expose the logs directory via a static mount at /logs",
    )
    level: str | None = Field(
        default=None,
        description="Logging level threshold (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    console_output: bool | None = Field(
        default=None,
        description="Whether to echo application logs to the console/stdout",
    )
    redact_sensitive: bool | None = Field(
        default=None,
        description="Whether to automatically redact sensitive fields (tokens, passwords, cookies)",
    )
    custom_redact_keys: list[str] | None = Field(
        default=None,
        description="List of custom field names to redact in logs",
    )

