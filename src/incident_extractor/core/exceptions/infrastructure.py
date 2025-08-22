"""Infrastructure-specific exception classes."""

from .base import InfrastructureError


class LLMClientError(InfrastructureError):
    """Base exception for LLM client errors."""

    pass


class LLMTimeoutError(LLMClientError):
    """Raised when LLM request times out."""

    pass


class LLMRateLimitError(LLMClientError):
    """Raised when LLM service rate limit is exceeded."""

    pass


class TextProcessingError(InfrastructureError):
    """Raised when text preprocessing fails."""

    pass
