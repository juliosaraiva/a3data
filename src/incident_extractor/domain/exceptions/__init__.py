"""Domain-specific exceptions."""

from typing import Any


class DomainError(Exception):
    """Base class for all domain errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class IncidentValidationError(DomainError):
    """Raised when incident data validation fails."""

    ...


class ExtractionError(DomainError):
    """Raised when data extraction fails."""

    ...


class InvalidDateTimeError(DomainError):
    """Raised when an invalid date-time format is encountered."""

    ...


class InvalidLocationError(DomainError):
    """Raise when location validation fails."""

    ...


class BusinessRuleViolationError(DomainError):
    """Raised when a business rule is violated."""

    ...


class LLMRepositoryError(Exception):
    """Base exception for LLM repository errors."""

    ...


class LLMError(LLMRepositoryError):
    """General LLM operation error."""

    ...


class LLMTimeoutError(LLMRepositoryError):
    """LLM operation timed out."""

    ...


class LLMConnectionError(LLMRepositoryError):
    """LLM connection error."""

    ...


class LLMValidationError(LLMRepositoryError):
    """LLM validation error."""

    ...


__all__ = [
    # Entities
    "Incident",
    # Value Objects
    "IncidentDateTime",
    "Location",
    # Repositories
    "LLMRepository",
    # Exceptions
    "DomainError",
    "IncidentValidationError",
    "ExtractionError",
    "InvalidDateTimeError",
    "InvalidLocationError",
    "BusinessRuleViolationError",
    "LLMRepositoryError",
    "LLMError",
    "LLMTimeoutError",
    "LLMConnectionError",
    "LLMValidationError",
]
