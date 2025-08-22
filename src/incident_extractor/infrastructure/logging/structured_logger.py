"""Enhanced structured logging service for incident extraction."""

import logging
import sys
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import structlog
from structlog.types import EventDict

# Context variables for request tracking
correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)
request_path_ctx: ContextVar[str | None] = ContextVar("request_path", default=None)


class LogLevel(str, Enum):
    """Log level enumeration."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LoggerConfig:
    """Configuration for structured logging."""

    # Basic settings
    level: LogLevel = LogLevel.INFO
    enable_json_format: bool = True
    enable_console_output: bool = True
    enable_file_output: bool = False

    # File logging settings
    log_file_path: Path | None = None
    max_file_size_mb: int = 100
    backup_count: int = 5

    # Structured logging settings
    include_timestamp: bool = True
    include_level: bool = True
    include_logger_name: bool = True
    include_correlation_id: bool = True
    include_request_info: bool = True

    # Security settings
    mask_sensitive_data: bool = True
    sensitive_fields: list[str] = None

    # Performance settings
    async_logging: bool = False
    buffer_size: int = 1000

    def __post_init__(self) -> None:
        """Initialize default sensitive fields if not provided."""
        if self.sensitive_fields is None:
            self.sensitive_fields = [
                "password",
                "token",
                "api_key",
                "secret",
                "authorization",
                "credit_card",
                "ssn",
                "cpf",
                "cnpj",
                "email",
            ]


class StructuredLogger:
    """Enhanced structured logger with context management and security features."""

    def __init__(self, name: str, config: LoggerConfig | None = None) -> None:
        """Initialize structured logger.

        Args:
            name: Logger name (usually __name__)
            config: Logger configuration
        """
        self.name = name
        self.config = config or LoggerConfig()
        self._setup_structlog()
        self.logger = structlog.get_logger(name)

    def _setup_structlog(self) -> None:
        """Configure structlog with custom processors and formatters."""
        processors = []

        # Add correlation ID processor
        if self.config.include_correlation_id:
            processors.append(self._add_correlation_id)

        # Add request info processor
        if self.config.include_request_info:
            processors.append(self._add_request_info)

        # Add sensitive data masking
        if self.config.mask_sensitive_data:
            processors.append(self._mask_sensitive_data)

        # Add timestamp processor
        if self.config.include_timestamp:
            processors.append(structlog.processors.TimeStamper(fmt="iso"))

        # Add standard processors
        processors.extend(
            [
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
            ]
        )

        # Configure renderer
        if self.config.enable_json_format:
            renderer = structlog.processors.JSONRenderer()
        else:
            renderer = structlog.dev.ConsoleRenderer()

        processors.append(renderer)

        # Configure structlog
        structlog.configure(
            processors=processors,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Configure standard library logging
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, self.config.level.value.upper()),
        )

    def _add_correlation_id(self, logger: Any, name: str, event_dict: EventDict) -> EventDict:
        """Add correlation ID to log events."""
        correlation_id = correlation_id_ctx.get()
        if correlation_id:
            event_dict["correlation_id"] = correlation_id
        return event_dict

    def _add_request_info(self, logger: Any, name: str, event_dict: EventDict) -> EventDict:
        """Add request information to log events."""
        user_id = user_id_ctx.get()
        request_path = request_path_ctx.get()

        if user_id:
            event_dict["user_id"] = user_id
        if request_path:
            event_dict["request_path"] = request_path

        return event_dict

    def _mask_sensitive_data(self, logger: Any, name: str, event_dict: EventDict) -> EventDict:
        """Mask sensitive data in log events."""

        def mask_value(key: str, value: Any) -> Any:
            if isinstance(key, str):
                key_lower = key.lower()
                if any(sensitive_field in key_lower for sensitive_field in self.config.sensitive_fields):
                    if isinstance(value, str) and len(value) > 4:
                        return f"{value[:2]}***{value[-2:]}"
                    else:
                        return "***"

            if isinstance(value, dict):
                return {k: mask_value(k, v) for k, v in value.items()}
            elif isinstance(value, list):
                return [mask_value("", item) for item in value]

            return value

        # Mask sensitive data in event dict
        for key, value in event_dict.items():
            event_dict[key] = mask_value(key, value)

        return event_dict

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self.logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        self.logger.critical(message, **kwargs)

    def log_request(
        self, method: str, path: str, status_code: int, duration_ms: float, user_id: str | None = None, **kwargs: Any
    ) -> None:
        """Log HTTP request details.

        Args:
            method: HTTP method
            path: Request path
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
            user_id: User ID if available
            **kwargs: Additional context
        """
        self.info(
            "HTTP request completed",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            user_id=user_id,
            **kwargs,
        )

    def log_llm_request(
        self,
        provider: str,
        model: str,
        prompt_length: int,
        response_length: int,
        duration_ms: float,
        status: str,
        tokens_used: int | None = None,
        cost: float | None = None,
        **kwargs: Any,
    ) -> None:
        """Log LLM request details.

        Args:
            provider: LLM provider name
            model: Model name
            prompt_length: Length of input prompt
            response_length: Length of response
            duration_ms: Request duration
            status: Request status
            tokens_used: Number of tokens used
            cost: Request cost if available
            **kwargs: Additional context
        """
        self.info(
            "LLM request completed",
            provider=provider,
            model=model,
            prompt_length=prompt_length,
            response_length=response_length,
            duration_ms=duration_ms,
            status=status,
            tokens_used=tokens_used,
            cost=cost,
            **kwargs,
        )

    def log_extraction(
        self,
        text_length: int,
        extraction_type: str,
        success: bool,
        confidence_score: float,
        duration_ms: float,
        extracted_fields: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Log incident extraction details.

        Args:
            text_length: Length of input text
            extraction_type: Type of extraction performed
            success: Whether extraction was successful
            confidence_score: Confidence score of extraction
            duration_ms: Processing duration
            extracted_fields: List of successfully extracted fields
            **kwargs: Additional context
        """
        self.info(
            "Incident extraction completed",
            text_length=text_length,
            extraction_type=extraction_type,
            success=success,
            confidence_score=confidence_score,
            duration_ms=duration_ms,
            extracted_fields=extracted_fields or [],
            **kwargs,
        )

    def log_error_with_context(
        self, error: Exception, context: dict[str, Any], component: str = "unknown", **kwargs: Any
    ) -> None:
        """Log error with full context information.

        Args:
            error: Exception that occurred
            context: Context information
            component: Component where error occurred
            **kwargs: Additional context
        """
        self.error(
            "Error occurred",
            error_type=type(error).__name__,
            error_message=str(error),
            component=component,
            context=context,
            **kwargs,
        )

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        user_id: str | None = None,
        ip_address: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Log security-related events.

        Args:
            event_type: Type of security event
            severity: Event severity
            description: Event description
            user_id: User ID if available
            ip_address: Client IP address
            **kwargs: Additional context
        """
        log_level = LogLevel.WARNING if severity in ["medium", "high"] else LogLevel.INFO

        if log_level == LogLevel.WARNING:
            self.warning(
                "Security event",
                event_type=event_type,
                severity=severity,
                description=description,
                user_id=user_id,
                ip_address=ip_address,
                **kwargs,
            )
        else:
            self.info(
                "Security event",
                event_type=event_type,
                severity=severity,
                description=description,
                user_id=user_id,
                ip_address=ip_address,
                **kwargs,
            )

    def create_child_logger(self, **kwargs: Any) -> structlog.stdlib.BoundLogger:
        """Create a child logger with additional context.

        Args:
            **kwargs: Additional context to bind

        Returns:
            Child logger with bound context
        """
        return self.logger.bind(**kwargs)

    @staticmethod
    def set_correlation_id(correlation_id: str | None = None) -> str:
        """Set correlation ID for current context.

        Args:
            correlation_id: Correlation ID to set, generates UUID if None

        Returns:
            The correlation ID that was set
        """
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())

        correlation_id_ctx.set(correlation_id)
        return correlation_id

    @staticmethod
    def set_user_id(user_id: str) -> None:
        """Set user ID for current context."""
        user_id_ctx.set(user_id)

    @staticmethod
    def set_request_path(path: str) -> None:
        """Set request path for current context."""
        request_path_ctx.set(path)

    @staticmethod
    def clear_context() -> None:
        """Clear all context variables."""
        correlation_id_ctx.set(None)
        user_id_ctx.set(None)
        request_path_ctx.set(None)

    @staticmethod
    def get_correlation_id() -> str | None:
        """Get current correlation ID."""
        return correlation_id_ctx.get()


# Convenience functions for common logging scenarios
def get_logger(name: str, config: LoggerConfig | None = None) -> StructuredLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)
        config: Optional logger configuration

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name, config)


def setup_logging(config: LoggerConfig | None = None) -> None:
    """Setup global logging configuration.

    Args:
        config: Logging configuration
    """
    config = config or LoggerConfig()

    # Configure Python's root logger
    logging.basicConfig(
        level=getattr(logging, config.level.value.upper()),
        format="%(message)s",
        stream=sys.stdout,
    )

    # Configure structlog
    processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if config.enable_json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
