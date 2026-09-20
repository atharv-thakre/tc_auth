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
        description="Master switch for persistent logging infrastructure (also enables all log files).",
    )
    logs_dir: str | None = Field(
        default=None,
        description="Where persistent logs live. Defaults to 'logs/'.",
    )
    level: str | None = Field(
        default=None,
        description="Logging severity/filtering (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    console_output: bool | None = Field(
        default=None,
        description="Whether logging output is shown in the console (independent of logging).",
    )
    capture_terminal: bool | None = Field(
        default=None,
        description="Capture terminal print/stdout/stderr into the logging system (server.log).",
    )
    redact_sensitive: bool | None = Field(
        default=None,
        description="Existing/default sensitive-data redaction.",
    )
    redact_patterns: list[str] | None = Field(
        default=None,
        description="User-defined regex redaction patterns.",
    )
    max_log_lines: int | None = Field(
        default=None,
        ge=10,
        description="Maximum retained lines for server.log/tcauth.log.",
    )
    trim_log_lines: int | None = Field(
        default=None,
        ge=1,
        description="Number of oldest lines removed when the limit is reached.",
    )

