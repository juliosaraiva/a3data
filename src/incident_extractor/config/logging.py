"""
Production-ready logging configuration for the incident extractor application.

This module provides comprehensive logging setup with environment-specific
configurations, structured logging, and production features like rotation.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, MutableMapping

import structlog
from rich.console import Console
from rich.logging import RichHandler

from .config import Settings, get_settings


def configure_logging() -> None:
    """
    Configure application logging with production-ready features.

    Sets up both standard library logging and structured logging
    with appropriate handlers, formatters, and rotation.
    """
    settings: Settings = get_settings()

    # Configure standard library logging first
    _configure_stdlib_logging(settings)

    # Configure structured logging
    _configure_structured_logging(settings)

    # Log configuration applied
    logger = get_logger("config.logging")
    logger.info(
        "Logging configuration applied",
        log_level=settings.log_level,
        log_format=settings.log_format,
        log_file=settings.log_file,
        environment=settings.environment,
        log_rotation=settings.log_rotation,
    )


def _configure_stdlib_logging(settings: Settings) -> None:
    """Configure standard library logging with production features."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handlers = []

    # Console handler configuration
    if settings.is_development:
        # Development: Rich console output with colors and tracebacks
        console = Console(stderr=True, force_terminal=True)
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            log_time_format="[%X]",
        )
        console_handler.setLevel(log_level)

        # Create formatter for development
        formatter = logging.Formatter(
            fmt="%(name)s - %(funcName)s:%(lineno)d - %(message)s",
            datefmt="[%X]",
        )
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    else:
        # Production: JSON logging to stdout
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        # Production JSON formatter
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s", '
            '"module": "%(module)s", "function": "%(funcName)s", '
            '"line": %(lineno)d, "process": %(process)d, "thread": %(thread)d}'
        )
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    # File handler with rotation (if specified)
    if settings.log_file:
        log_path = Path(settings.log_file)

        # Ensure log directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)

        if settings.log_rotation and not settings.is_development:
            # Production: Rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                settings.log_file,
                maxBytes=_parse_size(settings.log_max_size),
                backupCount=settings.log_backup_count,
                encoding="utf-8",
            )
        else:
            # Development or no rotation: Simple file handler
            file_handler = logging.FileHandler(settings.log_file, encoding="utf-8")

        file_handler.setLevel(log_level)

        # File formatter (always JSON for consistency)
        file_formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s", '
            '"module": "%(module)s", "function": "%(funcName)s", '
            '"line": %(lineno)d, "process": %(process)d, "thread": %(thread)d, '
            '"environment": "' + settings.environment + '"}'
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(level=log_level, handlers=handlers, force=True)

    # Configure third-party loggers
    _configure_third_party_loggers(settings)


def _configure_third_party_loggers(settings: Settings) -> None:
    """Configure third-party library loggers."""
    # Silence noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO if settings.is_development else logging.WARNING)

    if not settings.debug:
        logging.getLogger("uvicorn").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)
        logging.getLogger("concurrent.futures").setLevel(logging.WARNING)

    # LangGraph and LLM related loggers
    logging.getLogger("langgraph").setLevel(logging.INFO)
    logging.getLogger("langchain").setLevel(logging.WARNING)

    # Production: Reduce verbosity further
    if settings.is_production:
        logging.getLogger("multipart").setLevel(logging.ERROR)
        logging.getLogger("charset_normalizer").setLevel(logging.ERROR)


def _configure_structured_logging(settings: Settings) -> None:
    """Configure structured logging with structlog."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        _add_environment_processor,
        _add_request_id_processor,
    ]

    if settings.is_development:
        # Development: Pretty console output with colors
        processors.extend([structlog.dev.set_exc_info, structlog.dev.ConsoleRenderer(colors=True)])
    else:
        # Production: JSON output for log aggregation
        processors.extend([structlog.processors.format_exc_info, structlog.processors.JSONRenderer()])

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, settings.log_level.upper(), logging.INFO)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


def _add_environment_processor(logger, method_name, event_dict):
    """Add environment information to log records."""
    settings = get_settings()
    event_dict["environment"] = settings.environment
    event_dict["app_version"] = settings.app_version
    return event_dict


def _add_request_id_processor(logger, method_name, event_dict):
    """Add request ID to log records if available."""
    try:
        # Try to get request ID from structlog context
        if "request_id" in event_dict:
            return event_dict

        # Could be enhanced to get from actual request context
        # For now, we'll rely on middleware to add it to the context
        pass
    except (LookupError, AttributeError):
        pass

    return event_dict


def _parse_size(size_str: str) -> int:
    """
    Parse size string to bytes.

    Args:
        size_str: Size string like "100MB", "1GB", etc.

    Returns:
        int: Size in bytes
    """
    size_str = size_str.upper().strip()

    if size_str.endswith("KB"):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith("MB"):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith("GB"):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        # Assume bytes
        return int(size_str)


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name

    Returns:
        structlog.BoundLogger: Configured logger instance
    """
    return structlog.get_logger(name)


def log_agent_activity(agent_name: str, activity: str, **kwargs: Any) -> None:
    """
    Log agent activity with structured logging and context.

    Args:
        agent_name: Name of the agent
        activity: Description of the activity
        **kwargs: Additional context information
    """
    logger = get_logger(f"agent.{agent_name}")
    logger.info(activity, agent=agent_name, activity_type="agent_action", **kwargs)


def log_error(error: Exception, context: dict[str, Any] | None = None, **kwargs: Any) -> None:
    """
    Log errors with comprehensive context and structured information.

    Args:
        error: The exception that occurred
        context: Additional context information
        **kwargs: Additional keyword arguments
    """
    logger = get_logger("error")

    error_context = {
        "error": str(error),
        "error_type": type(error).__name__,
        "error_module": getattr(error, "__module__", "unknown"),
        **(context or {}),
        **kwargs,
    }

    logger.error("Error occurred", **error_context, exc_info=True)


def log_performance(operation: str, duration_ms: float, **kwargs: Any) -> None:
    """
    Log performance metrics with structured information.

    Args:
        operation: Name of the operation
        duration_ms: Duration in milliseconds
        **kwargs: Additional performance context
    """
    logger = get_logger("performance")
    logger.info("Performance metric", operation=operation, duration_ms=duration_ms, metric_type="performance", **kwargs)


def log_security_event(event_type: str, severity: str, details: dict[str, Any]) -> None:
    """
    Log security events with proper categorization.

    Args:
        event_type: Type of security event
        severity: Event severity (low, medium, high, critical)
        details: Event details and context
    """
    logger = get_logger("security")

    log_method = getattr(logger, severity.lower(), logger.info)
    log_method(f"Security event: {event_type}", event_type=event_type, severity=severity, category="security", **details)


class RequestLoggingMiddleware:
    """
    Production-ready middleware for logging HTTP requests.

    Provides comprehensive request logging with performance metrics,
    error tracking, and security monitoring.
    """

    def __init__(self, app: Any):
        self.app = app
        self.logger = get_logger("middleware.request")

    async def __call__(self, scope: MutableMapping[str, Any], receive: Any, send: Any):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import time

        start_time = time.time()

        # Extract request information
        request_info = {
            "method": scope["method"],
            "path": scope["path"],
            "query_string": scope.get("query_string", b"").decode(),
            "client": scope.get("client"),
            "headers": dict(scope.get("headers", [])),
        }

        # Log request start
        self.logger.info("Request started", **request_info)

        try:
            await self.app(scope, receive, send)

            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000

            # Log successful request completion
            self.logger.info("Request completed", processing_time_ms=processing_time, **request_info)

        except Exception as e:
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000

            # Log request error
            self.logger.error(
                "Request failed",
                processing_time_ms=processing_time,
                error=str(e),
                error_type=type(e).__name__,
                **request_info,
                exc_info=True,
            )
            raise
