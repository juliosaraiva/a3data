"""Abstract repository interface for LLM (Large Language Model) operations."""

from abc import ABC, abstractmethod
from typing import Any

from incident_extractor.core.exceptions.domain import DomainError


class LLMError(DomainError):
    """Base exception for LLM-related errors."""

    def __init__(self, message: str, error_code: str = "LLM_ERROR", details: dict[str, Any] | None = None):
        super().__init__(message, error_code, details)


class LLMTimeoutError(LLMError):
    """Exception raised when LLM request times out."""

    def __init__(self, message: str = "LLM request timed out", details: dict[str, Any] | None = None):
        super().__init__(message, "LLM_TIMEOUT", details)


class LLMConnectionError(LLMError):
    """Exception raised when connection to LLM fails."""

    def __init__(self, message: str = "Failed to connect to LLM service", details: dict[str, Any] | None = None):
        super().__init__(message, "LLM_CONNECTION_ERROR", details)


class LLMRepository(ABC):
    """
    Abstract repository interface for LLM (Large Language Model) operations.

    This interface defines the contract for LLM implementations,
    enabling dependency inversion and testability.
    """

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text response from LLM.

        Args:
            prompt: Input prompt for the LLM
            **kwargs: Additional parameters for generation

        Returns:
            Generated text response

        Raises:
            LLMError: When generation fails
            LLMTimeoutError: When request times out
            LLMConnectionError: When connection fails
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the LLM service is available.

        Returns:
            True if service is available, False otherwise
        """
        pass

    @abstractmethod
    async def get_model_info(self) -> dict[str, Any]:
        """Get information about the current model.

        Returns:
            Dictionary containing model information (name, version, capabilities, etc.)
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources and close connections."""
        pass
