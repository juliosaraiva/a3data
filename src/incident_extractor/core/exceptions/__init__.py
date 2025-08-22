"""Core exception classes for the incident extractor application.

This module provides a hierarchy of custom exceptions that are used
throughout the application to provide clear error handling and proper
HTTP status code mapping.
"""

from .application import (
    AuthorizationError,
    UseCaseError,
    ValidationError,
)
from .base import (
    ApplicationError,
    DomainError,
    IncidentExtractorError,
    InfrastructureError,
    PresentationError,
)
from .domain import (
    InvalidDateTimeError,
    InvalidIncidentError,
    InvalidLocationError,
    InvalidValueObjectError,
)
from .infrastructure import (
    LLMClientError,
    LLMRateLimitError,
    LLMTimeoutError,
    TextProcessingError,
)

__all__ = [
    # Base exceptions
    "IncidentExtractorError",
    "ApplicationError",
    "DomainError",
    "InfrastructureError",
    "PresentationError",
    # Domain exceptions
    "InvalidIncidentError",
    "InvalidValueObjectError",
    "InvalidDateTimeError",
    "InvalidLocationError",
    # Infrastructure exceptions
    "LLMClientError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "TextProcessingError",
    # Application exceptions
    "UseCaseError",
    "ValidationError",
    "AuthorizationError",
]
