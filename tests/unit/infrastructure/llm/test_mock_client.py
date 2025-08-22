"""Tests for Mock LLM client."""

import pytest

from src.incident_extractor.infrastructure.llm.clients.base_client import LLMClientError, LLMRequest
from src.incident_extractor.infrastructure.llm.clients.mock_client import MockClient, MockConfig


class TestMockClient:
    """Test cases for Mock LLM client."""

    def test_mock_client_creation(self):
        """Test creating a mock client."""
        client = MockClient()

        assert client.name == "Mock"
        assert client.config.default_model == "mock-gpt"

    def test_mock_client_with_config(self):
        """Test creating mock client with custom configuration."""
        config = MockConfig(default_model="custom-mock", simulate_delay=False, failure_rate=0.5)

        client = MockClient(config)

        assert client.config.default_model == "custom-mock"
        assert client.config.simulate_delay is False
        assert client.config.failure_rate == 0.5

    @pytest.mark.asyncio
    async def test_generate_text_success(self):
        """Test successful text generation."""
        config = MockConfig(simulate_delay=False)
        client = MockClient(config)

        request = LLMRequest(prompt="Extract incident information", temperature=0.7)

        response = await client.generate_text(request)

        assert response.content
        assert response.model == "mock-gpt"
        assert response.provider == "mock"
        assert response.processing_time_ms >= 0
        assert response.token_usage is not None

    @pytest.mark.asyncio
    async def test_generate_text_with_context(self):
        """Test text generation with context."""
        config = MockConfig(simulate_delay=False)
        client = MockClient(config)

        context = {"source": "police_report", "priority": "high"}
        request = LLMRequest(prompt="Extract incident data", context=context)

        response = await client.generate_text(request)

        assert "Context:" in response.content
        assert "police_report" in response.content

    @pytest.mark.asyncio
    async def test_generate_text_incident_template(self):
        """Test that incident-related prompts use incident template."""
        config = MockConfig(simulate_delay=False)
        client = MockClient(config)

        request = LLMRequest(prompt="Extract incident information from this text")

        response = await client.generate_text(request)

        assert "tipo_incidente" in response.content
        assert "gravidade" in response.content

    @pytest.mark.asyncio
    async def test_generate_text_failure_simulation(self):
        """Test failure simulation."""
        config = MockConfig(simulate_delay=False, failure_rate=1.0)
        client = MockClient(config)

        request = LLMRequest(prompt="test")

        with pytest.raises(LLMClientError, match="Mock client simulated failure"):
            await client.generate_text(request)

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check (always returns True for mock)."""
        client = MockClient()

        is_healthy = await client.health_check()

        assert is_healthy is True

    def test_get_supported_models(self):
        """Test getting supported models."""
        client = MockClient()

        models = client.get_supported_models()

        assert "mock-gpt" in models
        assert "mock-llama" in models
        assert len(models) > 0

    def test_set_failure_rate(self):
        """Test setting failure rate."""
        client = MockClient()

        client.set_failure_rate(0.5)
        assert client.config.failure_rate == 0.5

        # Test bounds
        client.set_failure_rate(-0.1)
        assert client.config.failure_rate == 0.0

        client.set_failure_rate(1.5)
        assert client.config.failure_rate == 1.0

    def test_add_response_template(self):
        """Test adding custom response templates."""
        client = MockClient()

        client.add_response_template("custom", "Custom response template")

        assert client.config.response_templates is not None
        assert client.config.response_templates["custom"] == "Custom response template"

    def test_set_delay_range(self):
        """Test setting delay range."""
        client = MockClient()

        client.set_delay_range(500, 1000)

        assert client.config.min_delay_ms == 500
        assert client.config.max_delay_ms == 1000

        # Test bounds
        client.set_delay_range(-100, 500)
        assert client.config.min_delay_ms == 0
        assert client.config.max_delay_ms == 500

    def test_get_stats(self):
        """Test getting client statistics."""
        config = MockConfig(failure_rate=0.3)
        client = MockClient(config)

        stats = client.get_stats()

        assert stats["provider"] == "mock"
        assert stats["failure_rate"] == 0.3
        assert "delay_enabled" in stats
        assert "templates_count" in stats
