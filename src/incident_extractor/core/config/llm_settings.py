"""LLM configuration for the incident extractor API."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, SecretStr, field_validator


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    PERPLEXITY = "perplexity"
    MOCK = "mock"  # For testing


class LLMSettings(BaseModel):
    """LLM configuration with sensible defaults and validation."""

    # Core Configuration
    provider: LLMProvider = Field(default=LLMProvider.OLLAMA, description="The LLM provider to use")
    api_key: SecretStr | None = Field(
        default=None,
        description="API key for cloud providers (OpenAI, Gemini, Perplexity)",
    )

    # Model Configuration
    model_name: str = Field(
        default="",  # Will be set by validator
        description="The model name to use",
    )

    # Request Configuration
    temperature: float = Field(
        default=0.1,  # Low for consistent extraction
        ge=0.0,
        le=2.0,
        description="Sampling temperature for responses",
    )
    max_tokens: int = Field(default=1000, ge=50, le=4000, description="Maximum tokens to generate")
    timeout: int = Field(default=30, ge=5, le=300, description="Request timeout in seconds")

    # Provider-specific Configuration
    base_url: str | None = Field(default=None, description="Base URL for API (mainly for Ollama)")
    extra_params: dict[str, Any] = Field(default_factory=dict, description="Additional provider-specific parameters")

    @field_validator("model_name")
    @classmethod
    def set_default_model(cls: Any, v: str, info: Any) -> str:
        """Set default model name based on provider."""
        if v:  # If model name is explicitly provided
            return v

        # Get provider from validation context
        provider_value = info.data.get("provider") if info.data else LLMProvider.OLLAMA

        # Default models for each provider
        defaults = {
            LLMProvider.OPENAI: "gpt-4o-mini",
            LLMProvider.OLLAMA: "llama3.2:3b",
            LLMProvider.GEMINI: "gemini-1.5-flash",
            LLMProvider.PERPLEXITY: "llama-3.1-sonar-small-128k-online",
            LLMProvider.MOCK: "mock-model",
        }

        return defaults.get(provider_value, defaults[LLMProvider.OLLAMA])

    @field_validator("base_url")
    @classmethod
    def set_default_base_url(cls: Any, v: str | None, info: Any) -> str | None:
        """Set default base URL for Ollama."""
        if v:  # If base URL is explicitly provided
            return v.rstrip("/")

        # Get provider from validation context
        provider_value = info.data.get("provider") if info.data else LLMProvider.OLLAMA

        # Only Ollama needs a base URL by default
        if provider_value == LLMProvider.OLLAMA:
            return "http://localhost:11434"

        return None

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls: Any, v: SecretStr | None, info: Any) -> SecretStr | None:
        """Validate API key requirements."""
        provider_value = info.data.get("provider") if info.data else LLMProvider.OLLAMA

        # API key required for cloud providers
        cloud_providers = {
            LLMProvider.OPENAI,
            LLMProvider.GEMINI,
            LLMProvider.PERPLEXITY,
        }

        if provider_value in cloud_providers and not v:
            raise ValueError(f"API key is required for {provider_value.value}")

        return v

    @property
    def requires_api_key(self: Any) -> bool:
        """Check if provider requires an API key."""
        return self.provider in {
            LLMProvider.OPENAI,
            LLMProvider.GEMINI,
            LLMProvider.PERPLEXITY,
        }

    @property
    def is_local(self: Any) -> bool:
        """Check if provider runs locally."""
        return self.provider in {LLMProvider.OLLAMA, LLMProvider.MOCK}

    def get_client_config(self: Any) -> dict[str, Any]:
        """Get configuration for LLM client initialization."""
        config = {
            "provider": self.provider.value,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
        }

        if self.api_key:
            config["api_key"] = self.api_key.get_secret_value()

        if self.base_url:
            config["base_url"] = self.base_url

        if self.extra_params:
            config.update(self.extra_params)

        return config

    def model_dump_safe(self: Any) -> dict[str, Any]:
        """Dump model data without exposing secrets."""
        data = self.model_dump()
        if "api_key" in data and data["api_key"]:
            data["api_key"] = "***masked***"
        return data
