from connect import auth

# ==========================================================
# CENTRALIZED LOGGING CONFIGURATION & MANAGEMENT
# ==========================================================
#
# The auth.log (or auth.logging) module provides centralized logging
# using JSONL for application logs and normal text format for server logs.
#
# Available methods:
#
#     config(logging=True, logs_dir=None, level="INFO", console_output=True, capture_terminal=False, redact_sensitive=True, redact_patterns=None)
#         Configure logging enabled status, directory, levels, redaction, and terminal capture.
#
#     load()
#         Get current logging configuration dictionary (includes "logging" key).
#
#     info(event, message, **metadata)
#     debug(event, message, **metadata)
#     warning(event, message, **metadata)
#     error(event, message, exc_info=None, **metadata)
#     critical(event, message, exc_info=None, **metadata)
#         Write structured JSONL log entries to tcauth.log.
#
#     create_snapshot(name, source)
#         Create a snapshot copy of a primary log in logs/store/{source}-{name}.log.
#
#     list_logs()
#         List primary logs and stored snapshots.
#
#     get_log_content(name, limit=None, offset=0)
#         Read lines or JSON records for a log or snapshot.
#
#     reset_log(source)
#         Truncate a primary log to 0 bytes and continue logging.
#
#     delete_snapshot(name)
#         Delete a snapshot file (primary logs cannot be deleted).
#
#     stream_logs(source, request)
#         Async generator for real-time SSE streaming.
#
#
# ==========================================================
# 1. LOAD LOGGING CONFIGURATION
# ==========================================================

config = auth.log.load()
print("Current Logging Config:", config)


# ==========================================================
# 2. CONFIGURE LOGGING
# ==========================================================

auth.log.config(
    logging=True,                    # Master toggle: set False to completely disable logging
    logs_dir="logs",                 # Default: logs/ in application directory
    level="INFO",                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
    console_output=True,             # Echo application logs to stdout
    capture_terminal=True,           # Capture all terminal print() calls into server.log
    redact_sensitive=True,           # Automatically redact passwords, tokens, secrets, cookies
    redact_patterns=[                # Custom regular expressions to mask as [REDACTED]
        r"(?i)authorization:\s*bearer\s+\S+",
        r"(?i)api[_-]?key\s*[:=]\s*\S+",
    ],
)



# ==========================================================
# 3. LOG APPLICATION EVENTS (JSONL)
# ==========================================================

auth.log.info(
    event="USER_ACTION",
    message="User initiated password reset",
    request_id="req-abc-123",
    method="POST",
    path="/tc-auth/forgot/password",
    client_ip="127.0.0.1",
    metadata={"email": "user@example.com"},
)

# Sensitive data is automatically redacted
auth.log.info(
    event="AUTH_TEST",
    message="Sensitive payload test",
    metadata={
        "password": "supersecretpassword123",
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.dummy",
        "safe_field": "hello world",
    },
)


# ==========================================================
# 4. MANAGE SNAPSHOTS
# ==========================================================

# Create a snapshot (physical file created: logs/store/tcauth-debug-session.log)
snapshot = auth.log.create_snapshot(name="debug-session", source="tcauth")
print("Snapshot created:", snapshot)

# List all logs (snapshot name in summary is "tcauth-debug-session")
summary = auth.log.list_logs()
print("All Logs:", summary)

# Read snapshot content using full name without extension ("tcauth-debug-session")
content = auth.log.get_log_content(name="tcauth-debug-session", limit=10)
print("Snapshot Content:", content)

# Delete snapshot using full name without extension ("tcauth-debug-session")
auth.log.delete_snapshot(name="tcauth-debug-session")
print("Snapshot deleted successfully")
