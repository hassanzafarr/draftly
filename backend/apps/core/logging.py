"""Structured logging helpers for Django and Celery."""

from __future__ import annotations

import contextvars
import json
import logging
from collections.abc import Mapping
from datetime import UTC, date, datetime
from typing import Any

_LOG_CONTEXT: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "draftly_log_context",
    default={},
)

_STANDARD_LOG_RECORD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()) | {
    "asctime",
    "message",
}


def set_logging_context(**context: Any) -> contextvars.Token:
    """Replace the current async/thread-local log context."""
    return _LOG_CONTEXT.set(_clean_context(context))


def bind_logging_context(**context: Any) -> contextvars.Token:
    """Merge fields into the current async/thread-local log context."""
    current = dict(_LOG_CONTEXT.get() or {})
    current.update(_clean_context(context))
    return _LOG_CONTEXT.set(current)


def reset_logging_context(token: contextvars.Token) -> None:
    """Restore a previous log context token."""
    _LOG_CONTEXT.reset(token)


def get_logging_context() -> dict[str, Any]:
    """Return a copy of the current log context."""
    return dict(_LOG_CONTEXT.get() or {})


class RequestContextFilter(logging.Filter):
    """Attach contextual fields to every log record handled by dictConfig."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in get_logging_context().items():
            if not hasattr(record, key):
                setattr(record, key, value)
        return True


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log line for production log aggregation."""

    def __init__(self, *, service: str = "draftly-backend", environment: str = ""):
        super().__init__()
        self.service = service
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service,
            "environment": self.environment,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.threadName,
        }

        payload.update(_clean_context(get_logging_context()))

        for key, value in record.__dict__.items():
            if key in _STANDARD_LOG_RECORD_ATTRS or key.startswith("_"):
                continue
            if key not in payload:
                payload[key] = _json_safe(value)

        if record.exc_info:
            exc_type, exc, _ = record.exc_info
            payload["exception"] = {
                "type": exc_type.__name__ if exc_type else "",
                "message": str(exc) if exc else "",
                "stacktrace": self.formatException(record.exc_info),
            }

        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


def _clean_context(context: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): _json_safe(value)
        for key, value in context.items()
        if value is not None and value != ""
    }


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple | list | set):
        return [_json_safe(item) for item in value]
    return str(value)
