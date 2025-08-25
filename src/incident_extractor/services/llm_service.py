"""LLM service abstraction layer for the incident extractor application."""

import asyncio
import json
from abc import ABC, abstractmethod

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import OllamaLLM
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from incident_extractor.config.llm import LLMConfig, LLMProvider, get_model_parameters, get_settings
from incident_extractor.config.logging import get_logger, log_error


class LLMServiceError(Exception):
    """Base exception for LLM service errors."""

    pass


class LLMConnectionError(LLMServiceError):
    """LLM connection error."""

    pass


class LLMTimeoutError(LLMServiceError):
    """LLM timeout error."""

    pass


class LLMValidationError(LLMServiceError):
    """LLM validation error."""

    pass


class BaseLLMService(ABC):
    """Abstract base class for LLM services."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = get_logger(f"llm.{config.provider}")

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate text using the LLM."""
        pass

    @abstractmethod
    async def is_healthy(self) -> bool:
        """Check if the LLM service is healthy."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close any open connections."""
        pass


class OllamaLLMService(BaseLLMService):
    """Ollama LLM service implementation."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client: OllamaLLM | None = None
        self._http_client: httpx.AsyncClient | None = None

    async def _initialize_client(self) -> None:
        """Initialize the Ollama client."""
        if self.client is None:
            try:
                params = get_model_parameters(self.config)
                self.client = OllamaLLM(
                    model=self.config.model,
                    temperature=self.config.temperature,
                    base_url=self.config.base_url,
                    **params,
                )
                self.logger.info(f"Initialized Ollama client with model {self.config.model}")
            except Exception as e:
                self.logger.error(f"Failed to initialize Ollama client: {e}")
                raise LLMConnectionError(f"Failed to connect to Ollama: {e}")

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get HTTP client for health checks."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout), limits=httpx.Limits(max_connections=10)
            )
        return self._http_client

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate text using Ollama."""
        await self._initialize_client()

        if self.client is None:
            raise LLMConnectionError("Ollama client is not initialized")

        # Combine system prompt with user prompt
        full_prompt = prompt
        if system_prompt or self.config.system_prompt:
            system_text = system_prompt or self.config.system_prompt
            full_prompt = f"System: {system_text}\n\nUser: {prompt}\n\nAssistant:"

        try:
            self.logger.info("Generating response with Ollama", model=self.config.model, prompt_length=len(prompt))

            # Use asyncio to run the synchronous call with timeout
            # Use asyncio.wait_for with proper timeout handling
            try:
                response = await asyncio.wait_for(asyncio.to_thread(self.client.invoke, full_prompt), timeout=self.config.timeout)
            except asyncio.TimeoutError:
                raise LLMTimeoutError(f"Ollama request timed out after {self.config.timeout} seconds")

            self.logger.info("Successfully generated response", response_length=len(response))
            return response

        except asyncio.TimeoutError:
            error_msg = f"Ollama request timed out after {self.config.timeout} seconds"
            self.logger.error(error_msg)
            raise LLMTimeoutError(error_msg)
        except Exception as e:
            error_msg = f"Ollama generation failed: {e}"
            self.logger.error(error_msg)
            log_error(e, {"model": self.config.model, "prompt_length": len(prompt)})
            raise LLMServiceError(error_msg)

    async def is_healthy(self) -> bool:
        """Check if Ollama is healthy."""
        try:
            client = await self._get_http_client()
            response = await client.get(f"{self.config.base_url}/api/tags")

            if response.status_code == 200:
                # Check if our model is available
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                is_healthy = self.config.model in models

                self.logger.info("Health check completed", healthy=is_healthy, available_models=len(models))
                return is_healthy
            else:
                self.logger.warning("Ollama health check failed", status_code=response.status_code)
                return False

        except Exception as e:
            self.logger.error("Ollama health check error", error=str(e))
            return False

    async def close(self) -> None:
        """Close HTTP client connections."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


class OpenAILLMService(BaseLLMService):
    """OpenAI LLM service implementation."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client: ChatOpenAI | None = None

    async def _initialize_client(self) -> None:
        """Initialize the OpenAI client."""
        if self.client is None:
            try:
                if not self.config.api_key:
                    raise LLMConnectionError("OpenAI API key is not configured")

                if self.config.api_key:
                    params = get_model_parameters(self.config)
                    self.client = ChatOpenAI(model=self.config.model, api_key=SecretStr(self.config.api_key), **params)
                    self.logger.info(f"Initialized OpenAI client with model {self.config.model}")
                    self.logger.info(f"Initialized OpenAI client with model {self.config.model}")
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI client: {e}")
                raise LLMConnectionError(f"Failed to connect to OpenAI: {e}")

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate text using OpenAI."""
        await self._initialize_client()

        if self.client is None:
            raise LLMConnectionError("OpenAI client is not initialized")

        messages: list[SystemMessage | HumanMessage] = []
        system_text = system_prompt or self.config.system_prompt
        if system_text:  # Additional check to ensure system_text is not None
            messages.append(SystemMessage(content=system_text))

        messages.append(HumanMessage(content=prompt))

        try:
            self.logger.info("Generating response with OpenAI", model=self.config.model, prompt_length=len(prompt))

            response = await self.client.ainvoke(messages)

            # Ensure we return a string, handling different response content types
            content = response.content
            if isinstance(content, str):
                response_text = content
            elif isinstance(content, list):
                # Join list elements into a single string
                response_text = " ".join(str(item) for item in content)
            else:
                response_text = str(content)

            self.logger.info("Successfully generated response", response_length=len(response_text))
            return response_text

        except Exception as e:
            error_msg = f"OpenAI generation failed: {e}"
            self.logger.error(error_msg)
            log_error(e, {"model": self.config.model, "prompt_length": len(prompt)})
            raise LLMServiceError(error_msg)

    async def is_healthy(self) -> bool:
        """Check if OpenAI is healthy."""
        try:
            await self._initialize_client()
            # Try a simple generation to test connectivity
            test_response = await self.generate("Hello", "Respond with 'OK'")
            return len(test_response.strip()) > 0
        except Exception as e:
            self.logger.error("OpenAI health check error", error=str(e))
            return False

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get HTTP client for health checks."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout), limits=httpx.Limits(max_connections=10)
            )
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client connections."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


class MockLLMService(BaseLLMService):
    """Mock LLM service for testing."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate mock response."""
        self.logger.info("Generating mock response")

        # Simulate processing delay
        await asyncio.sleep(0.1)

        # Return mock extraction data if this looks like an extraction prompt
        if "json" in prompt.lower() or "extraia" in prompt.lower():
            return json.dumps(
                {
                    "data_ocorrencia": "2025-08-23 14:00",
                    "local": "São Paulo",
                    "tipo_incidente": "Falha no servidor",
                    "impacto": "Sistema de faturamento indisponível por 2 horas",
                },
                ensure_ascii=False,
                indent=2,
            )

        return "Mock response for testing purposes."

    async def is_healthy(self) -> bool:
        """Mock service is always healthy."""
        return True

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get HTTP client for health checks."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout), limits=httpx.Limits(max_connections=10)
            )
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client connections."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


class LLMServiceFactory:
    """Factory for creating LLM services."""

    @staticmethod
    def create_service(config: LLMConfig) -> BaseLLMService:
        """Create LLM service based on configuration."""
        if config.provider == LLMProvider.OLLAMA:
            return OllamaLLMService(config)
        elif config.provider == LLMProvider.OPENAI:
            return OpenAILLMService(config)
        elif config.provider == LLMProvider.MOCK:
            return MockLLMService(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")


class LLMServiceManager:
    """Manager for LLM services with fallback support."""

    def __init__(self):
        self.services: dict[str, BaseLLMService] = {}
        self.logger = get_logger("llm.manager")

    def register_service(self, name: str, service: BaseLLMService) -> None:
        """Register an LLM service."""
        self.services[name] = service
        self.logger.info(f"Registered LLM service: {name}")

    async def generate_with_fallback(self, service_names: list[str], prompt: str, system_prompt: str | None = None) -> str:
        """Generate text with fallback services."""

        for service_name in service_names:
            if service_name not in self.services:
                self.logger.warning(f"Service {service_name} not found, skipping")
                continue

            service = self.services[service_name]

            try:
                # Check if service is healthy before using it
                if not await service.is_healthy():
                    self.logger.warning(f"Service {service_name} is not healthy, trying fallback")
                    continue

                response = await service.generate(prompt, system_prompt)
                self.logger.info(f"Successfully generated response using {service_name}")
                return response

            except Exception as e:
                self.logger.error(f"Service {service_name} failed: {e}")
                if service_name == service_names[-1]:  # Last service
                    raise LLMServiceError(f"All LLM services failed. Last error: {e}")
                continue

        raise LLMServiceError("No healthy LLM services available")

    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all registered services."""
        results = {}
        for name, service in self.services.items():
            try:
                results[name] = await service.is_healthy()
            except Exception as e:
                self.logger.error(f"Health check failed for {name}: {e}")
                results[name] = False
        return results

    async def close_all(self) -> None:
        """Close all service connections."""
        for name, service in self.services.items():
            try:
                if hasattr(service, "close"):
                    await service.close()
                self.logger.info(f"Closed service: {name}")
            except Exception as e:
                self.logger.error(f"Error closing service {name}: {e}")


# Global service manager instance
_service_manager: LLMServiceManager | None = None


async def get_llm_service_manager() -> LLMServiceManager:
    """Get the global LLM service manager."""
    global _service_manager
    if _service_manager is None:
        _service_manager = LLMServiceManager()

        # Initialize services based on configuration
        settings = get_settings()

        # Add mock service for testing
        mock_config = LLMConfig(provider=LLMProvider.MOCK, model="mock")
        _service_manager.register_service("mock", LLMServiceFactory.create_service(mock_config))

        # Add Ollama service if configured
        try:
            ollama_config = LLMConfig(
                provider=LLMProvider.OLLAMA,
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
                timeout=settings.ollama_timeout,
                max_retries=settings.ollama_max_retries,
                temperature=0.1,
            )
            _service_manager.register_service("ollama", LLMServiceFactory.create_service(ollama_config))
        except Exception as e:
            get_logger("llm.manager").warning(f"Failed to initialize Ollama service: {e}")

        # Add OpenAI service if API key is available
        if settings.openai_api_key:
            try:
                openai_config = LLMConfig(
                    provider=LLMProvider.OPENAI,
                    model=settings.openai_model,
                    api_key=settings.openai_api_key,
                    timeout=60,
                    temperature=0.1,
                )
                _service_manager.register_service("openai", LLMServiceFactory.create_service(openai_config))
            except Exception as e:
                get_logger("llm.manager").warning(f"Failed to initialize OpenAI service: {e}")

    return _service_manager
