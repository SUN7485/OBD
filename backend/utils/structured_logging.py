"""Structured logging setup with JSON output for production observability."""
import logging
import sys
import json
import traceback
from typing import Any, Dict, Optional
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Custom JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add standard fields if present
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id
        if hasattr(record, "car_id"):
            log_entry["car_id"] = record.car_id
        if hasattr(record, "org_id"):
            log_entry["org_id"] = record.org_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        if hasattr(record, "status"):
            log_entry["status"] = record.status

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add extra fields from the record
        standard_attrs = {
            "name", "msg", "args", "created", "relativeCreated", "exc_info",
            "exc_text", "stack_info", "lineno", "funcName", "pathname",
            "filename", "module", "levelno", "levelname", "thread",
            "threadName", "process", "processName", "msecs", "message",
            "correlation_id", "car_id", "org_id", "user_id", "duration_ms", "status"
        }
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                log_entry[key] = value

        try:
            return json.dumps(log_entry, default=str)
        except (TypeError, ValueError):
            return json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "ERROR",
                "logger": "logging",
                "message": "Failed to serialize log entry",
                "original_message": str(log_entry.get("message", "")),
            })


def setup_structured_logging(
    level: int = logging.INFO,
    json_output: bool = True,
) -> None:
    """Configure structured logging for the application.
    
    Args:
        level: Logging level (default: INFO)
        json_output: If True, output JSON format; if False, use human-readable format
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if json_output:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Reduce noise from third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def log_with_context(
    logger_instance: logging.Logger,
    level: str,
    message: str,
    correlation_id: Optional[str] = None,
    car_id: Optional[str] = None,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None,
    duration_ms: Optional[float] = None,
    status: Optional[str] = None,
    **extra: Any
) -> None:
    """Log a message with structured context fields.
    
    Args:
        logger_instance: The logger instance to use
        level: Log level ('debug', 'info', 'warning', 'error', 'critical')
        message: The log message
        correlation_id: Optional correlation ID for tracing
        car_id: Optional car UUID string
        org_id: Optional organization UUID string
        user_id: Optional user UUID string
        duration_ms: Optional duration in milliseconds
        status: Optional status string
        **extra: Additional fields to include in the log entry
    """
    log_method = getattr(logger_instance, level.lower(), logger_instance.info)

    # Build extra dict with standard fields
    extra_fields: Dict[str, Any] = {}
    if correlation_id:
        extra_fields["correlation_id"] = correlation_id
    if car_id:
        extra_fields["car_id"] = car_id
    if org_id:
        extra_fields["org_id"] = org_id
    if user_id:
        extra_fields["user_id"] = user_id
    if duration_ms is not None:
        extra_fields["duration_ms"] = duration_ms
    if status:
        extra_fields["status"] = status

    extra_fields.update(extra)

    # Merge with any existing extra from the logger call
    log_method(message, extra=extra_fields)