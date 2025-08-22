"""Ollama LLM client implementation."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
from pydantic import BaseModel

from ..resilience.circuit_breaker import CircuitBreaker
from ..resilience.retry import RetryableClient, RetryConfig
from .base_client import BaseLLMClient, LLMClientError, LLMRequest, LLMResponse, LLMServiceUnavailableError, LLMTimeoutError


class OllamaConfig(BaseModel):
    """Configuration for Ollama client."""

    base_url: str = "http://localhost:11434"
    default_model: str = "llama2"
    timeout: float = 120.0  # Ollama can be slower than cloud APIs


class OllamaRequest(BaseModel):
    """Ollama API request format."""

    model: str
    prompt: str
    stream: bool = False
    context: list[int] | None = None
    options: dict[str, Any] | None = None


class OllamaResponse(BaseModel):
    """Ollama API response format."""

    model: str
    created_at: str
    response: str
    done: bool
    context: list[int] | None = None
    total_duration: int | None = None
    load_duration: int | None = None
    prompt_eval_count: int | None = None
    prompt_eval_duration: int | None = None
    eval_count: int | None = None
    eval_duration: int | None = None


class OllamaClient(BaseLLMClient, RetryableClient):
    """Ollama LLM client implementation."""

    def __init__(self, config: OllamaConfig):
        """Initialize Ollama client.

        Args:
            config: Ollama configuration
        """
        super().__init__("Ollama", config.model_dump())
        RetryableClient.__init__(
            self,
            RetryConfig(
                max_attempts=3,
                base_delay=2.0,  # Longer delay for Ollama
                retryable_exceptions=(LLMTimeoutError, LLMServiceUnavailableError, httpx.TimeoutException),
            ),
        )

        self.config = config
        self.circuit_breaker = CircuitBreaker(
            name="ollama_client",
            failure_threshold=3,
            recovery_timeout=60.0,  # Longer recovery for Ollama
            expected_exception=(LLMTimeoutError, LLMServiceUnavailableError, httpx.HTTPStatusError),
        )

        # Setup HTTP client
        self._client = httpx.AsyncClient(
            base_url=config.base_url, timeout=httpx.Timeout(config.timeout), headers={"Content-Type": "application/json"}
        )

    async def generate_text(self, request: LLMRequest) -> LLMResponse:
        """Generate text using Ollama API.

        Args:
            request: LLM request

        Returns:
            LLM response with generated text

        Raises:
            LLMClientError: If generation fails
        """
        start_time = time.time()

        try:
            # Prepare Ollama request
            ollama_request = self._prepare_request(request)

            # Execute with circuit breaker and retry
            response = await self.circuit_breaker.call(self.execute_with_retry, self._make_api_call, ollama_request)

            # Process response
            return self._process_response(response, start_time)

        except Exception as e:
            if isinstance(e, LLMClientError):
                raise e
            else:
                raise LLMClientError(f"Ollama generation failed: {e}", provider="ollama", original_error=e) from e

    async def _make_api_call(self, ollama_request: OllamaRequest) -> OllamaResponse:
        """Make actual API call to Ollama.

        Args:
            ollama_request: Formatted Ollama request

        Returns:
            Ollama API response

        Raises:
            LLMTimeoutError: If request times out
            LLMServiceUnavailableError: If service is unavailable
            LLMClientError: For other API errors
        """
        try:
            response = await self._client.post("/api/generate", json=ollama_request.model_dump(exclude_none=True))

            if response.status_code == 200:
                return OllamaResponse.model_validate(response.json())
            elif response.status_code == 404:
                # Model not found
                raise LLMClientError(f"Ollama model not found: {ollama_request.model}", provider="ollama")
            elif response.status_code >= 500:
                # Server error - retryable
                raise LLMServiceUnavailableError(f"Ollama server error: {response.status_code}", provider="ollama")
            else:
                # Other client error
                error_detail = response.text
                raise LLMClientError(f"Ollama API error {response.status_code}: {error_detail}", provider="ollama")

        except httpx.TimeoutException as e:
            raise LLMTimeoutError("Ollama request timed out", provider="ollama", original_error=e) from e

        except httpx.HTTPError as e:
            raise LLMServiceUnavailableError(f"Ollama network error: {e}", provider="ollama", original_error=e) from e

    def _prepare_request(self, request: LLMRequest) -> OllamaRequest:
        """Prepare Ollama API request from generic LLM request.

        Args:
            request: Generic LLM request

        Returns:
            Formatted Ollama request
        """
        model = request.model or self.config.default_model

        # Build enhanced prompt with context
        prompt = request.prompt
        if request.context:
            context_str = json.dumps(request.context, ensure_ascii=False)
            prompt = f"Context: {context_str}\n\nTask: {request.prompt}"

        # Prepare options
        options = {
            "temperature": request.temperature,
        }

        if request.max_tokens:
            options["num_predict"] = request.max_tokens

        return OllamaRequest(model=model, prompt=prompt, stream=False, options=options)

    def _process_response(self, response: OllamaResponse, start_time: float) -> LLMResponse:
        """Process Ollama response into generic LLM response.

        Args:
            response: Ollama API response
            start_time: Request start time

        Returns:
            Generic LLM response
        """
        processing_time = int((time.time() - start_time) * 1000)

        if not response.response:
            raise LLMClientError("Empty response from Ollama", provider="ollama")

        # Extract token usage if available
        token_usage = None
        if response.prompt_eval_count or response.eval_count:
            token_usage = {
                "prompt_tokens": response.prompt_eval_count or 0,
                "completion_tokens": response.eval_count or 0,
                "total_tokens": (response.prompt_eval_count or 0) + (response.eval_count or 0),
            }

        return LLMResponse(
            content=response.response,
            model=response.model,
            token_usage=token_usage,
            processing_time_ms=processing_time,
            provider="ollama",
            raw_response=response.model_dump(),
        )

    async def health_check(self) -> bool:
        """Check if Ollama API is available.

        Returns:
            True if service is healthy
        """
        try:
            response = await self._client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    def get_supported_models(self) -> list[str]:
        """Get list of supported Ollama models.

        Note: This is a static list. In practice, you would query
        the /api/tags endpoint to get available models.

        Returns:
            List of common model identifiers
        """
        return [
            "llama2",
            "llama2:13b",
            "llama2:70b",
            "mistral",
            "mistral:7b",
            "codellama",
            "codellama:13b",
            "vicuna",
        ]

    async def list_available_models(self) -> list[str]:
        """Get actual list of available models from Ollama.

        Returns:
            List of available model identifiers

        Raises:
            LLMClientError: If unable to fetch models
        """
        try:
            response = await self._client.get("/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            else:
                raise LLMClientError(f"Failed to fetch Ollama models: {response.status_code}", provider="ollama")
        except httpx.HTTPError as e:
            raise LLMClientError(f"Error fetching Ollama models: {e}", provider="ollama", original_error=e) from e

    async def close(self) -> None:
        """Close HTTP client connections."""
        await self._client.aclose()

    def get_circuit_breaker_status(self) -> dict[str, Any]:
        """Get circuit breaker status information.

        Returns:
            Circuit breaker status
        """
        return self.circuit_breaker.get_status()
