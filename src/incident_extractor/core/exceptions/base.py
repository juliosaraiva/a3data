"""Base exception classes for the incident extractor application."""

from typing import Any


class IncidentExtractorError(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.details = details or {}

    def __str__(self) -> str:
        """Return string representation of the exception."""
        if self.details:
            return f"{self.message}. Details: {self.details}"
        return self.message


class DomainError(IncidentExtractorError):
    """Base class for domain layer errors."""

    pass


class ApplicationError(IncidentExtractorError):
    """Base class for application layer errors."""

    pass


class InfrastructureError(IncidentExtractorError):
    """Base class for infrastructure layer errors."""

    pass


class PresentationError(IncidentExtractorError):
    """Base class for presentation layer errors."""

    pass
