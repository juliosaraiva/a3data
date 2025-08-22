"""Application-specific exception classes."""

from .base import ApplicationError


class UseCaseError(ApplicationError):
    """Base exception for use case errors."""

    pass


class ValidationError(ApplicationError):
    """Raised when input validation fails."""

    pass


class AuthorizationError(ApplicationError):
    """Raised when user is not authorized for an action."""

    pass
