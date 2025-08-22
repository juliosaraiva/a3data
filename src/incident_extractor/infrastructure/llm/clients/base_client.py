"""Base LLM client interface and common functionality."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLMRequest(BaseModel):
    """Standard request structure for LLM clients."""

    prompt: str
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    context: dict[str, Any] | None = None


class LLMResponse(BaseModel):
    """Standard response structure from LLM clients."""

    content: str
    model: str
    token_usage: dict[str, int] | None = None
    processing_time_ms: int
    provider: str
    raw_response: dict[str, Any] | None = None


class BaseLLMClient(ABC):
    """Abstract base class for all LLM clients."""

    def __init__(self, name: str, config: dict[str, Any]):
        """Initialize the LLM client.

        Args:
            name: Human-readable name for this client
            config: Configuration parameters for the client
        """
        self.name = name
        self.config = config

    @abstractmethod
    async def generate_text(self, request: LLMRequest) -> LLMResponse:
        """Generate text using the LLM.

        Args:
            request: The LLM request containing prompt and parameters

        Returns:
            LLM response with generated content and metadata

        Raises:
            LLMClientError: If the generation fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM service is available.

        Returns:
            True if the service is healthy, False otherwise
        """
        pass

    @abstractmethod
    def get_supported_models(self) -> list[str]:
        """Get list of supported models for this client.

        Returns:
            List of model identifiers
        """
        pass


class LLMClientError(Exception):
    """Base exception for LLM client errors."""

    def __init__(self, message: str, provider: str, original_error: Exception | None = None):
        """Initialize LLM client error.

        Args:
            message: Error description
            provider: LLM provider name
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.provider = provider
        self.original_error = original_error


class LLMTimeoutError(LLMClientError):
    """Raised when LLM request times out."""

    pass


class LLMQuotaExceededError(LLMClientError):
    """Raised when LLM quota/rate limit is exceeded."""

    pass


class LLMModelNotFoundError(LLMClientError):
    """Raised when requested LLM model is not available."""

    pass


class LLMServiceUnavailableError(LLMClientError):
    """Raised when LLM service is temporarily unavailable."""

    pass
