"""Logging configuration and setup for the incident extractor API."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator
from structlog import configure, get_logger
from structlog.processors import JSONRenderer, add_log_level
from structlog.types import EventDict, WrappedLogger


class LogLevel(str, Enum):
    """Supported logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Supported logging output formats."""

    JSON = "json"
    TEXT = "text"


class LoggingConfig(BaseModel):
    """Centralized logging configuration."""

    # Basic Configuration
    level: LogLevel = Field(default=LogLevel.INFO, description="Logging level for the application")
    format: LogFormat = Field(default=LogFormat.JSON, description="Output format for log messages")

    # Output Configuration
    console_enabled: bool = Field(default=True, description="Enable console output")
    file_enabled: bool = Field(default=True, description="Enable file output")
    file_path: str = Field(default="logs/app.log", description="Log file path")

    # Advanced Configuration
    max_file_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Maximum log file size in bytes",
    )

    backup_count: int = Field(default=5, description="Number of backup files to keep")
    correlation_id_enabled: bool = Field(default=True, description="Include correlation IDs in logs")

    # Third-party Logging Levels
    third_party_levels: dict[str, LogLevel] = Field(
        default_factory=lambda: {
            "httpx": LogLevel.WARNING,
            "uvicorn": LogLevel.INFO,
            "fastapi": LogLevel.INFO,
            "sqlalchemy": LogLevel.WARNING,
        },
        description="Logging levels for third-party libraries",
    )

    @field_validator("file_path")
    @classmethod
    def create_log_directory(cls, v: str) -> str:
        """Ensure log directory exists."""
        log_path = Path(v)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return str(log_path)

    @field_validator("max_file_size")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        """Validate file size is reasonable."""
        if v < 1024 * 1024:  # 1MB minimum
            raise ValueError("Max file size must be at least 1MB")
        if v > 100 * 1024 * 1024:  # 100MB maximum
            raise ValueError("Max file size cannot exceed 100MB")
        return v


class StructuredLogger:
    """Structured logging utility with correlation ID support."""

    _instance: StructuredLogger | None = None
    _configured: bool = False

    def __new__(cls) -> StructuredLogger:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def configure(cls, config: LoggingConfig) -> None:
        """Configure structured logging."""
        if cls._configured:
            return

        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Set up handlers
        handlers: list[logging.Handler] = []

        if config.console_enabled:
            handlers.append(cls._create_console_handler(config))

        if config.file_enabled:
            handlers.append(cls._create_file_handler(config))

        # Configure root logger
        logging.basicConfig(level=config.level.value, handlers=handlers, force=True)

        # Configure third-party loggers
        for lib_name, level in config.third_party_levels.items():
            logging.getLogger(lib_name).setLevel(level.value)

        # Configure structlog
        configure(
            processors=[
                add_log_level,
                cls._add_timestamp,
                cls._add_correlation_id if config.correlation_id_enabled else lambda _, __, event_dict: event_dict,
                JSONRenderer() if config.format == LogFormat.JSON else cls._text_renderer,
            ],
            logger_factory=lambda name: logging.getLogger(str(name)),
            cache_logger_on_first_use=True,
        )

        cls._configured = True

        # Log successful configuration
        logger = get_logger(__name__)
        logger.info(
            "Logging system initialized",
            level=config.level.value,
            format=config.format.value,
            console_enabled=config.console_enabled,
            file_enabled=config.file_enabled,
            file_path=config.file_path if config.file_enabled else None,
        )

    @staticmethod
    def _create_console_handler(config: LoggingConfig) -> logging.StreamHandler[Any]:
        """Create console handler with appropriate formatter."""
        handler = logging.StreamHandler(sys.stdout)

        if config.format == LogFormat.JSON:
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(TextFormatter())

        return handler

    @staticmethod
    def _create_file_handler(config: LoggingConfig) -> logging.Handler:
        """Create rotating file handler."""
        from logging.handlers import RotatingFileHandler

        handler = RotatingFileHandler(
            filename=config.file_path,
            maxBytes=config.max_file_size,
            backupCount=config.backup_count,
            encoding="utf-8",
        )

        if config.format == LogFormat.JSON:
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(TextFormatter())

        return handler

    @staticmethod
    def _add_timestamp(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
        """Add timestamp to log entry."""
        event_dict["timestamp"] = datetime.now(UTC).isoformat()
        return event_dict

    @staticmethod
    def _add_correlation_id(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
        """Add correlation ID to log entry."""
        # This will be enhanced with request context in middleware
        import uuid

        event_dict.setdefault("correlation_id", str(uuid.uuid4()))
        return event_dict

    @staticmethod
    def _text_renderer(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> str:
        """Render log entry as text."""
        timestamp = event_dict.pop("timestamp", "")
        level = event_dict.pop("level", "INFO")
        logger_name = event_dict.pop("logger", "")
        event = event_dict.pop("event", "")

        # Format main message
        msg_parts: list[str] = [
            str(timestamp),
            str(level),
            str(logger_name),
            str(event),
        ]

        # Add extra fields
        if event_dict:
            extra = " ".join(f"{k}={v}" for k, v in event_dict.items())
            msg_parts.append(f"[{extra}]")

        return " | ".join(filter(None, msg_parts))


class JSONFormatter(logging.Formatter):
    """JSON log formatter with structured output."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id

        # Add any extra attributes
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
            }:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_logging(config: LoggingConfig) -> None:
    """Set up application logging."""
    StructuredLogger.configure(config)


def get_structured_logger(name: str) -> Any:
    """Get a structured logger instance."""
    return get_logger(name)
