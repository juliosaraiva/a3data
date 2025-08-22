"""Tests for LLM client factory."""

import pytest

from src.incident_extractor.infrastructure.llm.clients.base_client import LLMClientError
from src.incident_extractor.infrastructure.llm.clients.mock_client import MockClient
from src.incident_extractor.infrastructure.llm.clients.ollama_client import OllamaClient
from src.incident_extractor.infrastructure.llm.clients.openai_client import OpenAIClient
from src.incident_extractor.infrastructure.llm.factory import LLMClientFactory


class TestLLMClientFactory:
    """Test cases for LLM client factory."""

    def test_create_openai_client(self):
        """Test creating OpenAI client."""
        config = {
            "api_key": "test-key",
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-3.5-turbo",
        }

        client = LLMClientFactory.create_client("openai", config)

        assert isinstance(client, OpenAIClient)
        assert client.name == "OpenAI"

    def test_create_ollama_client(self):
        """Test creating Ollama client."""
        config = {
            "base_url": "http://localhost:11434",
            "default_model": "llama2",
        }

        client = LLMClientFactory.create_client("ollama", config)

        assert isinstance(client, OllamaClient)
        assert client.name == "Ollama"

    def test_create_mock_client(self):
        """Test creating Mock client."""
        config = {
            "default_model": "mock-gpt",
            "simulate_delay": False,
        }

        client = LLMClientFactory.create_client("mock", config)

        assert isinstance(client, MockClient)
        assert client.name == "Mock"

    def test_unsupported_provider(self):
        """Test error for unsupported provider."""
        with pytest.raises(LLMClientError, match="Unsupported LLM provider"):
            LLMClientFactory.create_client("unsupported", {})

    def test_case_insensitive_provider(self):
        """Test provider names are case insensitive."""
        config = {"default_model": "test"}

        client1 = LLMClientFactory.create_client("MOCK", config)
        client2 = LLMClientFactory.create_client("Mock", config)
        client3 = LLMClientFactory.create_client("mock", config)

        assert all(isinstance(c, MockClient) for c in [client1, client2, client3])

    def test_create_clients_from_config(self):
        """Test creating clients from full configuration."""
        config = {
            "primary": {
                "provider": "mock",
                "default_model": "primary-model",
                "simulate_delay": False,
            },
            "fallbacks": [
                {
                    "provider": "mock",
                    "default_model": "fallback1-model",
                    "simulate_delay": False,
                },
                {
                    "provider": "mock",
                    "default_model": "fallback2-model",
                    "simulate_delay": False,
                },
            ],
        }

        primary, fallbacks = LLMClientFactory.create_clients_from_config(config)

        assert isinstance(primary, MockClient)
        assert len(fallbacks) == 2
        assert all(isinstance(c, MockClient) for c in fallbacks)

    def test_create_clients_from_config_no_primary(self):
        """Test error when primary provider is missing."""
        config = {"fallbacks": []}

        with pytest.raises(LLMClientError, match="Missing 'primary' provider"):
            LLMClientFactory.create_clients_from_config(config)

    def test_create_clients_from_config_invalid_primary(self):
        """Test error when primary provider configuration is invalid."""
        config = {"primary": {}}

        with pytest.raises(LLMClientError, match="Missing 'provider' in primary"):
            LLMClientFactory.create_clients_from_config(config)

    def test_get_supported_providers(self):
        """Test getting supported providers."""
        providers = LLMClientFactory.get_supported_providers()

        assert "openai" in providers
        assert "ollama" in providers
        assert "mock" in providers

    def test_get_provider_config_schema(self):
        """Test getting configuration schema for providers."""
        openai_schema = LLMClientFactory.get_provider_config_schema("openai")
        assert "api_key" in openai_schema
        assert openai_schema["api_key"]["required"] is True

        ollama_schema = LLMClientFactory.get_provider_config_schema("ollama")
        assert "base_url" in ollama_schema

        mock_schema = LLMClientFactory.get_provider_config_schema("mock")
        assert "simulate_delay" in mock_schema

    def test_get_provider_config_schema_unsupported(self):
        """Test error for unsupported provider schema."""
        with pytest.raises(LLMClientError, match="Unsupported provider"):
            LLMClientFactory.get_provider_config_schema("unsupported")
