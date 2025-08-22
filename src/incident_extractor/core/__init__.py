"""Core module containing cross-cutting concerns."""

from .config import Config, settings
from .container import Container, container, wire_container
from .exceptions import (
    ApplicationError,
    AuthorizationError,
    DomainError,
    IncidentExtractorError,
    InfrastructureError,
    InvalidDateTimeError,
    InvalidIncidentError,
    InvalidLocationError,
    InvalidValueObjectError,
    LLMClientError,
    LLMRateLimitError,
    LLMTimeoutError,
    PresentationError,
    TextProcessingError,
    UseCaseError,
    ValidationError,
)

__all__ = [
    # Configuration
    "Config",
    "settings",
    # Dependency Injection
    "Container",
    "container",
    "wire_container",
    # Exceptions
    "IncidentExtractorError",
    "DomainError",
    "ApplicationError",
    "InfrastructureError",
    "PresentationError",
    "InvalidIncidentError",
    "InvalidValueObjectError",
    "InvalidDateTimeError",
    "InvalidLocationError",
    "LLMClientError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "TextProcessingError",
    "UseCaseError",
    "ValidationError",
    "AuthorizationError",
]
