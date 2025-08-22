"""Factory for creating LLM clients based on configuration."""

from __future__ import annotations

import logging
from typing import Any

from .clients.base_client import BaseLLMClient, LLMClientError
from .clients.mock_client import MockClient, MockConfig
from .clients.ollama_client import OllamaClient, OllamaConfig
from .clients.openai_client import OpenAIClient, OpenAIConfig

logger = logging.getLogger(__name__)


class LLMClientFactory:
    """Factory for creating LLM clients."""

    @staticmethod
    def create_client(provider: str, config: dict[str, Any]) -> BaseLLMClient:
        """Create an LLM client based on provider and configuration.

        Args:
            provider: LLM provider name (openai, ollama, mock)
            config: Provider-specific configuration

        Returns:
            Configured LLM client

        Raises:
            LLMClientError: If provider is not supported or configuration is invalid
        """
        provider_lower = provider.lower()

        try:
            if provider_lower == "openai":
                return LLMClientFactory._create_openai_client(config)
            elif provider_lower == "ollama":
                return LLMClientFactory._create_ollama_client(config)
            elif provider_lower == "mock":
                return LLMClientFactory._create_mock_client(config)
            else:
                raise LLMClientError(f"Unsupported LLM provider: {provider}", provider=provider)

        except Exception as e:
            if isinstance(e, LLMClientError):
                raise e
            else:
                raise LLMClientError(f"Failed to create {provider} client: {e}", provider=provider, original_error=e) from e

    @staticmethod
    def _create_openai_client(config: dict[str, Any]) -> OpenAIClient:
        """Create OpenAI client.

        Args:
            config: OpenAI configuration

        Returns:
            Configured OpenAI client
        """
        openai_config = OpenAIConfig(**config)
        return OpenAIClient(openai_config)

    @staticmethod
    def _create_ollama_client(config: dict[str, Any]) -> OllamaClient:
        """Create Ollama client.

        Args:
            config: Ollama configuration

        Returns:
            Configured Ollama client
        """
        ollama_config = OllamaConfig(**config)
        return OllamaClient(ollama_config)

    @staticmethod
    def _create_mock_client(config: dict[str, Any]) -> MockClient:
        """Create Mock client.

        Args:
            config: Mock configuration

        Returns:
            Configured Mock client
        """
        mock_config = MockConfig(**config)
        return MockClient(mock_config)

    @staticmethod
    def create_clients_from_config(llm_config: dict[str, Any]) -> tuple[BaseLLMClient, list[BaseLLMClient]]:
        """Create primary and fallback clients from configuration.

        Args:
            llm_config: LLM configuration with primary and fallback providers

        Returns:
            Tuple of (primary_client, fallback_clients)

        Raises:
            LLMClientError: If configuration is invalid
        """
        if "primary" not in llm_config:
            raise LLMClientError("Missing 'primary' provider in LLM configuration", provider="unknown")

        primary_config = llm_config["primary"]
        if "provider" not in primary_config:
            raise LLMClientError("Missing 'provider' in primary LLM configuration", provider="unknown")

        # Create primary client
        primary_provider = primary_config["provider"]
        primary_client_config = {k: v for k, v in primary_config.items() if k != "provider"}
        primary_client = LLMClientFactory.create_client(primary_provider, primary_client_config)

        logger.info(f"Created primary LLM client: {primary_provider}")

        # Create fallback clients
        fallback_clients = []
        fallbacks_config = llm_config.get("fallbacks", [])

        for i, fallback_config in enumerate(fallbacks_config):
            try:
                if "provider" not in fallback_config:
                    logger.warning(f"Skipping fallback {i}: missing 'provider'")
                    continue

                fallback_provider = fallback_config["provider"]
                fallback_client_config = {k: v for k, v in fallback_config.items() if k != "provider"}

                fallback_client = LLMClientFactory.create_client(fallback_provider, fallback_client_config)
                fallback_clients.append(fallback_client)

                logger.info(f"Created fallback LLM client: {fallback_provider}")

            except Exception as e:
                logger.warning(f"Failed to create fallback client {i}: {e}")
                # Continue with other fallbacks even if one fails

        return primary_client, fallback_clients

    @staticmethod
    def get_supported_providers() -> list[str]:
        """Get list of supported LLM providers.

        Returns:
            List of provider names
        """
        return ["openai", "ollama", "mock"]

    @staticmethod
    def get_provider_config_schema(provider: str) -> dict[str, Any]:
        """Get configuration schema for a provider.

        Args:
            provider: Provider name

        Returns:
            Configuration schema

        Raises:
            LLMClientError: If provider is not supported
        """
        provider_lower = provider.lower()

        if provider_lower == "openai":
            return {
                "api_key": {"type": "string", "required": True, "description": "OpenAI API key"},
                "base_url": {"type": "string", "required": False, "default": "https://api.openai.com/v1"},
                "default_model": {"type": "string", "required": False, "default": "gpt-3.5-turbo"},
                "timeout": {"type": "number", "required": False, "default": 60.0},
                "max_tokens": {"type": "integer", "required": False, "default": 1000},
            }

        elif provider_lower == "ollama":
            return {
                "base_url": {"type": "string", "required": False, "default": "http://localhost:11434"},
                "default_model": {"type": "string", "required": False, "default": "llama2"},
                "timeout": {"type": "number", "required": False, "default": 120.0},
            }

        elif provider_lower == "mock":
            return {
                "default_model": {"type": "string", "required": False, "default": "mock-gpt"},
                "simulate_delay": {"type": "boolean", "required": False, "default": True},
                "min_delay_ms": {"type": "integer", "required": False, "default": 100},
                "max_delay_ms": {"type": "integer", "required": False, "default": 2000},
                "failure_rate": {"type": "number", "required": False, "default": 0.0},
                "response_templates": {"type": "object", "required": False, "default": None},
            }

        else:
            raise LLMClientError(f"Unsupported provider: {provider}", provider=provider)
