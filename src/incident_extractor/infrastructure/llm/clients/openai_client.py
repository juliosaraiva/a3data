"""OpenAI LLM client implementation."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
from pydantic import BaseModel

from ..resilience.circuit_breaker import CircuitBreaker
from ..resilience.retry import RetryableClient, RetryConfig
from .base_client import BaseLLMClient, LLMClientError, LLMRequest, LLMResponse, LLMServiceUnavailableError, LLMTimeoutError


class OpenAIConfig(BaseModel):
    """Configuration for OpenAI client."""

    api_key: str
    base_url: str = "https://api.openai.com/v1"
    default_model: str = "gpt-3.5-turbo"
    timeout: float = 60.0
    max_tokens: int = 1000


class OpenAIMessage(BaseModel):
    """OpenAI message format."""

    role: str
    content: str


class OpenAIRequest(BaseModel):
    """OpenAI API request format."""

    model: str
    messages: list[OpenAIMessage]
    temperature: float = 0.7
    max_tokens: int | None = None


class OpenAIUsage(BaseModel):
    """OpenAI usage statistics."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class OpenAIChoice(BaseModel):
    """OpenAI response choice."""

    message: OpenAIMessage
    finish_reason: str
    index: int


class OpenAIResponse(BaseModel):
    """OpenAI API response format."""

    id: str
    object: str
    created: int
    model: str
    choices: list[OpenAIChoice]
    usage: OpenAIUsage | None = None


class OpenAIClient(BaseLLMClient, RetryableClient):
    """OpenAI LLM client implementation."""

    def __init__(self, config: OpenAIConfig):
        """Initialize OpenAI client.

        Args:
            config: OpenAI configuration
        """
        super().__init__("OpenAI", config.model_dump())
        RetryableClient.__init__(
            self,
            RetryConfig(
                max_attempts=3,
                base_delay=1.0,
                retryable_exceptions=(LLMTimeoutError, LLMServiceUnavailableError, httpx.TimeoutException),
            ),
        )

        self.config = config
        self.circuit_breaker = CircuitBreaker(
            name="openai_client",
            failure_threshold=3,
            recovery_timeout=30.0,
            expected_exception=(LLMTimeoutError, LLMServiceUnavailableError, httpx.HTTPStatusError),
        )

        # Setup HTTP client
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=httpx.Timeout(config.timeout),
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
        )

    async def generate_text(self, request: LLMRequest) -> LLMResponse:
        """Generate text using OpenAI API.

        Args:
            request: LLM request

        Returns:
            LLM response with generated text

        Raises:
            LLMClientError: If generation fails
        """
        start_time = time.time()

        try:
            # Prepare OpenAI request
            openai_request = self._prepare_request(request)

            # Execute with circuit breaker and retry
            response = await self.circuit_breaker.call(self.execute_with_retry, self._make_api_call, openai_request)

            # Process response
            return self._process_response(response, start_time)

        except Exception as e:
            if isinstance(e, LLMClientError):
                raise e
            else:
                raise LLMClientError(f"OpenAI generation failed: {e}", provider="openai", original_error=e) from e

    async def _make_api_call(self, openai_request: OpenAIRequest) -> OpenAIResponse:
        """Make actual API call to OpenAI.

        Args:
            openai_request: Formatted OpenAI request

        Returns:
            OpenAI API response

        Raises:
            LLMTimeoutError: If request times out
            LLMServiceUnavailableError: If service is unavailable
            LLMClientError: For other API errors
        """
        try:
            response = await self._client.post("/chat/completions", json=openai_request.model_dump(exclude_none=True))

            if response.status_code == 200:
                return OpenAIResponse.model_validate(response.json())
            elif response.status_code == 429:
                # Rate limit exceeded - should be handled by retry logic
                raise LLMServiceUnavailableError("OpenAI rate limit exceeded", provider="openai")
            elif response.status_code >= 500:
                # Server error - retryable
                raise LLMServiceUnavailableError(f"OpenAI server error: {response.status_code}", provider="openai")
            else:
                # Client error - not retryable
                error_detail = response.text
                raise LLMClientError(f"OpenAI API error {response.status_code}: {error_detail}", provider="openai")

        except httpx.TimeoutException as e:
            raise LLMTimeoutError("OpenAI request timed out", provider="openai", original_error=e) from e

        except httpx.HTTPError as e:
            raise LLMServiceUnavailableError(f"OpenAI network error: {e}", provider="openai", original_error=e) from e

    def _prepare_request(self, request: LLMRequest) -> OpenAIRequest:
        """Prepare OpenAI API request from generic LLM request.

        Args:
            request: Generic LLM request

        Returns:
            Formatted OpenAI request
        """
        model = request.model or self.config.default_model
        max_tokens = request.max_tokens or self.config.max_tokens

        # Format prompt as messages
        messages = [OpenAIMessage(role="user", content=request.prompt)]

        # Add context as system message if provided
        if request.context:
            context_str = json.dumps(request.context, ensure_ascii=False)
            system_message = OpenAIMessage(role="system", content=f"Context: {context_str}")
            messages.insert(0, system_message)

        return OpenAIRequest(model=model, messages=messages, temperature=request.temperature, max_tokens=max_tokens)

    def _process_response(self, response: OpenAIResponse, start_time: float) -> LLMResponse:
        """Process OpenAI response into generic LLM response.

        Args:
            response: OpenAI API response
            start_time: Request start time

        Returns:
            Generic LLM response
        """
        processing_time = int((time.time() - start_time) * 1000)

        if not response.choices:
            raise LLMClientError("No choices in OpenAI response", provider="openai")

        content = response.choices[0].message.content
        if content is None:
            raise LLMClientError("Empty content in OpenAI response", provider="openai")

        # Extract token usage
        token_usage = None
        if response.usage:
            token_usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return LLMResponse(
            content=content,
            model=response.model,
            token_usage=token_usage,
            processing_time_ms=processing_time,
            provider="openai",
            raw_response=response.model_dump(),
        )

    async def health_check(self) -> bool:
        """Check if OpenAI API is available.

        Returns:
            True if service is healthy
        """
        try:
            response = await self._client.get("/models")
            return response.status_code == 200
        except Exception:
            return False

    def get_supported_models(self) -> list[str]:
        """Get list of supported OpenAI models.

        Returns:
            List of model identifiers
        """
        return [
            "gpt-4",
            "gpt-4-turbo-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
        ]

    async def close(self) -> None:
        """Close HTTP client connections."""
        await self._client.aclose()

    def get_circuit_breaker_status(self) -> dict[str, Any]:
        """Get circuit breaker status information.

        Returns:
            Circuit breaker status
        """
        return self.circuit_breaker.get_status()
