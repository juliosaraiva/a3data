"""Mock LLM client for testing and development."""

from __future__ import annotations

import asyncio
import json
import random
import time
from typing import Any

from pydantic import BaseModel

from .base_client import BaseLLMClient, LLMClientError, LLMRequest, LLMResponse


class MockConfig(BaseModel):
    """Configuration for Mock client."""

    default_model: str = "mock-gpt"
    simulate_delay: bool = True
    min_delay_ms: int = 100
    max_delay_ms: int = 2000
    failure_rate: float = 0.0  # 0.0 = no failures, 1.0 = always fail
    response_templates: dict[str, str] | None = None


class MockClient(BaseLLMClient):
    """Mock LLM client for testing and development."""

    def __init__(self, config: MockConfig | None = None):
        """Initialize Mock client.

        Args:
            config: Mock configuration
        """
        self._typed_config = config or MockConfig()
        super().__init__("Mock", self._typed_config.model_dump())

        # Override the dict config with typed config for easier access
        self.config = self._typed_config

        # Default response templates for different scenarios
        self._default_templates = {
            "incident": """
            {
                "tipo_incidente": "acidente_transito",
                "gravidade": "moderada",
                "local": {
                    "endereco": "Av. Paulista, 1000 - Bela Vista, São Paulo - SP",
                    "coordenadas": {
                        "latitude": -23.561414,
                        "longitude": -46.655981
                    }
                },
                "data_hora": "2023-12-15T14:30:00-03:00",
                "descricao": "Colisão entre dois veículos na Av. Paulista com feridos leves",
                "envolvidos": [
                    {
                        "tipo": "veiculo",
                        "detalhes": "Carro de passeio cor branca"
                    },
                    {
                        "tipo": "veiculo",
                        "detalhes": "Motocicleta preta"
                    }
                ],
                "feridos": 2,
                "orgaos_acionados": ["Bombeiros", "SAMU"],
                "status": "em_andamento"
            }
            """,
            "default": "Informação processada com sucesso. Este é um mock response para fins de teste.",
            "error": "Mock error simulation activated",
        }

    async def generate_text(self, request: LLMRequest) -> LLMResponse:
        """Generate mock text response.

        Args:
            request: LLM request

        Returns:
            Mock LLM response

        Raises:
            LLMClientError: If mock failure is simulated
        """
        start_time = time.time()

        # Simulate failure if configured
        if self.config.failure_rate > 0 and random.random() < self.config.failure_rate:
            await self._simulate_delay()
            raise LLMClientError("Mock client simulated failure", provider="mock", original_error=Exception("Simulated error"))

        # Simulate processing delay
        await self._simulate_delay()

        # Generate response content
        content = self._generate_content(request)

        processing_time = int((time.time() - start_time) * 1000)

        # Mock token usage
        prompt_tokens = len(request.prompt.split())
        completion_tokens = len(content.split())
        token_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

        return LLMResponse(
            content=content,
            model=request.model or self.config.default_model,
            token_usage=token_usage,
            processing_time_ms=processing_time,
            provider="mock",
            raw_response={"mock": True, "request_id": f"mock_{int(time.time())}", "config": self.config.model_dump()},
        )

    def _generate_content(self, request: LLMRequest) -> str:
        """Generate mock content based on request.

        Args:
            request: LLM request

        Returns:
            Generated content
        """
        # Use custom templates if provided
        templates = self.config.response_templates or {}

        # Try to match request content to appropriate template
        prompt_lower = request.prompt.lower()

        if "incident" in prompt_lower or "acident" in prompt_lower:
            template = templates.get("incident", self._default_templates["incident"])
        elif "error" in prompt_lower or "fail" in prompt_lower:
            template = templates.get("error", self._default_templates["error"])
        else:
            template = templates.get("default", self._default_templates["default"])

        # Add context information if provided
        if request.context:
            context_str = json.dumps(request.context, ensure_ascii=False, indent=2)
            template = f"[Context: {context_str}]\n\n{template}"

        return template.strip()

    async def _simulate_delay(self) -> None:
        """Simulate processing delay if configured."""
        if self.config.simulate_delay:
            delay_ms = random.randint(self.config.min_delay_ms, self.config.max_delay_ms)
            delay_seconds = delay_ms / 1000.0
            await asyncio.sleep(delay_seconds)

    async def health_check(self) -> bool:
        """Check if mock service is available (always returns True).

        Returns:
            Always True for mock client
        """
        return True

    def get_supported_models(self) -> list[str]:
        """Get list of supported mock models.

        Returns:
            List of mock model identifiers
        """
        return [
            "mock-gpt",
            "mock-llama",
            "mock-claude",
            "mock-test-fast",
            "mock-test-slow",
            "mock-test-error",
        ]

    def set_failure_rate(self, rate: float) -> None:
        """Set the failure simulation rate.

        Args:
            rate: Failure rate between 0.0 and 1.0
        """
        self.config.failure_rate = max(0.0, min(1.0, rate))

    def add_response_template(self, key: str, template: str) -> None:
        """Add or update a response template.

        Args:
            key: Template key
            template: Response template
        """
        if self.config.response_templates is None:
            self.config.response_templates = {}
        self.config.response_templates[key] = template

    def set_delay_range(self, min_ms: int, max_ms: int) -> None:
        """Set the delay simulation range.

        Args:
            min_ms: Minimum delay in milliseconds
            max_ms: Maximum delay in milliseconds
        """
        self.config.min_delay_ms = max(0, min_ms)
        self.config.max_delay_ms = max(min_ms, max_ms)

    def get_stats(self) -> dict[str, Any]:
        """Get mock client statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "provider": "mock",
            "model": self.config.default_model,
            "failure_rate": self.config.failure_rate,
            "delay_enabled": self.config.simulate_delay,
            "delay_range_ms": [self.config.min_delay_ms, self.config.max_delay_ms],
            "templates_count": len(self.config.response_templates or {}),
        }
