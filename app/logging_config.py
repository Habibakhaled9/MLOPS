import logging
import os
import sys

SERVICE_NAME = "llm-question-api"

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | "
    f"service={SERVICE_NAME} | environment={{environment}} | "
    "%(name)s | %(message)s"
)

SUPPORTED_LOG_LEVELS = (
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
)


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
) -> None:
    """Configure application-wide console logging."""

    resolved_level = _resolve_log_level(level)
    resolved_environment = environment or os.getenv("APP_ENV", "development")

    logging.basicConfig(
        level=resolved_level,
        format=LOG_FORMAT.format(environment=resolved_environment),
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )