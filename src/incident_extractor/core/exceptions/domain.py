"""Domain-specific exception classes."""

from .base import DomainError


class InvalidIncidentError(DomainError):
    """Raised when incident data is invalid."""

    pass


class InvalidValueObjectError(DomainError):
    """Raised when a value object cannot be created due to invalid data."""

    pass


class InvalidDateTimeError(InvalidValueObjectError):
    """Raised when incident datetime cannot be parsed or is invalid."""

    pass


class InvalidLocationError(InvalidValueObjectError):
    """Raised when location data is invalid or cannot be processed."""

    pass
