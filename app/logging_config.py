import logging
import os
from contextvars import ContextVar, Token
from logging.handlers import RotatingFileHandler
from pathlib import Path

SERVICE_NAME = "llm-question-api"
DEFAULT_LOG_FILE = Path("logs/app.log")

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | "
    f"service={SERVICE_NAME} | environment={{environment}} | "
    "correlation_id=%(correlation_id)s | "
    "%(name)s | %(message)s"
)

SUPPORTED_LOG_LEVELS = (
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
)

_correlation_id_context: ContextVar[str] = ContextVar(
    "correlation_id",
    default="-",
)


class CorrelationIdFilter(logging.Filter):
    """Add the current correlation ID to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = _correlation_id_context.get()
        return True


def set_correlation_id(correlation_id: str) -> Token:
    """Set the correlation ID and return a token for restoring it."""

    return _correlation_id_context.set(correlation_id)


def reset_correlation_id(token: Token) -> None:
    """Restore the previous correlation ID."""

    _correlation_id_context.reset(token)


def _resolve_log_level(level: str | None) -> int:
    """Convert a log-level name into the value expected by logging."""

    level_name = (level or os.getenv("LOG_LEVEL", "INFO")).upper()

    if level_name not in SUPPORTED_LOG_LEVELS:
        supported_levels = ", ".join(SUPPORTED_LOG_LEVELS)
        raise ValueError(
            f"Unsupported log level {level_name!r}. "
            f"Choose from: {supported_levels}."
        )

    return getattr(logging, level_name)


def configure_logging(
    level: str | None = None,
    environment: str | None = None,
    log_file: str | Path | None = None,
) -> None:
    """Configure rotating file logging with correlation IDs."""

    resolved_level = _resolve_log_level(level)
    resolved_environment = environment or os.getenv("APP_ENV", "development")
    resolved_log_file = Path(
        log_file or os.getenv("LOG_FILE") or DEFAULT_LOG_FILE
    )

    resolved_log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        filename=resolved_log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.addFilter(CorrelationIdFilter())

    logging.basicConfig(
        level=resolved_level,
        format=LOG_FORMAT.format(environment=resolved_environment),
        handlers=[file_handler],
        force=True,
    )