"""Logging configuration for the incident extractor application."""

import logging
import sys
from typing import Any, MutableMapping

import structlog
from rich.console import Console
from rich.logging import RichHandler

from .config import Settings, get_settings


def configure_logging() -> None:
    """Configure application logging."""
    settings: Settings = get_settings()

    # Configure standard library logging first
    _configure_stdlib_logging(settings)

    # Configure structured logging
    _configure_structured_logging(settings)


def _configure_stdlib_logging(settings: Settings) -> None:
    """Configure standard library logging."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Create console handler with rich formatting for development
    if settings.is_development:
        console = Console(stderr=True, force_terminal=True)
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
        )
        console_handler.setLevel(log_level)

        # Create formatter
        formatter = logging.Formatter(
            fmt="%(name)s - %(funcName)s:%(lineno)d - %(message)s",
            datefmt="[%X]",
        )
        console_handler.setFormatter(formatter)

        handlers = [console_handler]
    else:
        # Production: JSON logging to stdout
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s", '
            '"module": "%(module)s", "line": %(lineno)d}'
        )
        console_handler.setFormatter(formatter)
        handlers: list[logging.Handler] = [console_handler]

    # Add file handler if specified
    if settings.log_file:
        file_handler = logging.FileHandler(settings.log_file)
        file_handler.setLevel(log_level)

        file_formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s", '
            '"module": "%(module)s", "line": %(lineno)d, '
            '"process": %(process)d, "thread": %(thread)d}'
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(level=log_level, handlers=handlers, force=True)

    # Silence noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    if not settings.debug:
        logging.getLogger("uvicorn").setLevel(logging.WARNING)


def _configure_structured_logging(settings: Settings) -> None:
    """Configure structured logging with structlog."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_development:
        # Development: Pretty console output
        processors.extend([structlog.dev.set_exc_info, structlog.dev.ConsoleRenderer(colors=True)])
    else:
        # Production: JSON output
        processors.extend([structlog.processors.format_exc_info, structlog.processors.JSONRenderer()])

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, settings.log_level.upper(), logging.INFO)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class RequestLoggingMiddleware:
    """Middleware for logging HTTP requests."""

    def __init__(self, app: Any):
        self.app = app
        self.logger = get_logger("middleware.request")

    async def __call__(self, scope: MutableMapping[str, Any], receive: Any, send: Any):
        if scope["type"] == "http":
            # Log request start
            self.logger.info(
                "Request started",
                method=scope["method"],
                path=scope["path"],
                query_string=scope.get("query_string", b"").decode(),
                client=scope.get("client"),
            )

        await self.app(scope, receive, send)


def log_agent_activity(agent_name: str, activity: str, **kwargs: Any) -> None:
    """Log agent activity with structured logging."""
    logger = get_logger(f"agent.{agent_name}")
    logger.info(activity, **kwargs)


def log_error(error: Exception, context: dict[str, Any] | None = None) -> None:
    """Log errors with context."""
    logger = get_logger("error")
    logger.error("Error occurred", error=str(error), error_type=type(error).__name__, context=context or {}, exc_info=True)
