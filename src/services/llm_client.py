"""LLM client abstraction and implementations."""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LLMResponse(BaseModel):
    """Response model for LLM interactions."""

    text: str
    success: bool = True
    error: Optional[str] = None


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate(self, prompt: str) -> LLMResponse:
        """Generate text based on the given prompt."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the LLM service is available."""
        pass


class OllamaClient(LLMClient):
    """Ollama LLM client implementation."""

    def __init__(self, base_url: str, model_name: str, timeout: int = 30):
        """Initialize the Ollama client."""
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def generate(self, prompt: str) -> LLMResponse:
        """Generate text using Ollama API."""
        try:
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent extraction
                    "top_p": 0.9,
                }
            }

            logger.debug(f"Sending request to Ollama: {url}")
            response = await self.client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            return LLMResponse(text=data.get("response", ""))

        except httpx.TimeoutException:
            error_msg = f"Request to Ollama timed out after {self.timeout}s"
            logger.error(error_msg)
            return LLMResponse(text="", success=False, error=error_msg)

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error from Ollama: {e.response.status_code}"
            logger.error(error_msg)
            return LLMResponse(text="", success=False, error=error_msg)

        except Exception as e:
            error_msg = f"Unexpected error communicating with Ollama: {str(e)}"
            logger.error(error_msg)
            return LLMResponse(text="", success=False, error=error_msg)

    async def is_available(self) -> bool:
        """Check if Ollama service is available."""
        try:
            url = f"{self.base_url}/api/tags"
            response = await self.client.get(url, timeout=5)
            response.raise_for_status()
            
            # Check if our specific model is available
            data = response.json()
            models = [model.get("name", "") for model in data.get("models", [])]
            return self.model_name in models

        except Exception as e:
            logger.warning(f"Ollama availability check failed: {str(e)}")
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


class MockLLMClient(LLMClient):
    """Mock LLM client for testing purposes."""

    def __init__(self, mock_response: Optional[str] = None):
        """Initialize the mock client."""
        self.mock_response = mock_response or self._default_response()
        self.available = True

    def _default_response(self) -> str:
        """Default mock response."""
        return json.dumps({
            "data_ocorrencia": "2025-08-20 14:00",
            "local": "São Paulo",
            "tipo_incidente": "Falha no servidor",
            "impacto": "Sistema indisponível por 2 horas"
        })

    async def generate(self, prompt: str) -> LLMResponse:
        """Generate mock text response."""
        if not self.available:
            return LLMResponse(
                text="",
                success=False,
                error="Mock LLM service unavailable"
            )
        return LLMResponse(text=self.mock_response)

    async def is_available(self) -> bool:
        """Check mock availability."""
        return self.available

    def set_availability(self, available: bool) -> None:
        """Set mock availability status."""
        self.available = available

    def set_response(self, response: str) -> None:
        """Set mock response."""
        self.mock_response = response


class LLMClientFactory:
    """Factory for creating LLM clients."""

    @staticmethod
    def create_client(
        provider: str,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: int = 30,
        **kwargs: Any
    ) -> LLMClient:
        """Create an LLM client based on provider type."""
        
        if provider.lower() == "ollama":
            if not base_url or not model_name:
                raise ValueError("Ollama client requires base_url and model_name")
            return OllamaClient(base_url, model_name, timeout)
        
        elif provider.lower() == "mock":
            return MockLLMClient(kwargs.get("mock_response"))
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")