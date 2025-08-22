"""Infrastructure layer - LLM clients and adapters."""

from .clients.base_client import BaseLLMClient, LLMClientError, LLMRequest, LLMResponse
from .clients.mock_client import MockClient, MockConfig
from .clients.ollama_client import OllamaClient, OllamaConfig
from .clients.openai_client import OpenAIClient, OpenAIConfig
from .factory import LLMClientFactory
from .repository.llm_repository_impl import LLMRepositoryImpl
from .resilience.circuit_breaker import CircuitBreaker, CircuitBreakerError
from .resilience.retry import RetryableClient, RetryConfig, RetryExhaustedError

__all__ = [
    # Base classes
    "BaseLLMClient",
    "LLMRequest",
    "LLMResponse",
    "LLMClientError",
    # Client implementations
    "OpenAIClient",
    "OpenAIConfig",
    "OllamaClient",
    "OllamaConfig",
    "MockClient",
    "MockConfig",
    # Factory and repository
    "LLMClientFactory",
    "LLMRepositoryImpl",
    # Resilience
    "CircuitBreaker",
    "CircuitBreakerError",
    "RetryConfig",
    "RetryExhaustedError",
    "RetryableClient",
]
