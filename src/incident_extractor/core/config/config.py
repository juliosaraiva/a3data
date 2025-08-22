"""Configuration management for the incident extractor API."""

from enum import Enum
from typing import Any

from dotenv import load_dotenv
from pydantic import Field, SecretStr, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .llm_settings import LLMProvider, LLMSettings
from .logging import LogFormat, LoggingConfig, LogLevel

load_dotenv()


class Environment(str, Enum):
    """Application environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",  # Allows LLM__PROVIDER=ollama
    )

    # Application Configuration
    APP_NAME: str = Field(default="Incident Extractor API")
    APP_VERSION: str = Field(default="1.0.0")
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: Environment = Field(default=Environment.DEVELOPMENT)

    # LLM Configuration - Individual fields for environment variables
    LLM_PROVIDER: LLMProvider = Field(default=LLMProvider.OLLAMA)
    LLM_API_KEY: SecretStr | None = Field(default=None)
    LLM_MODEL_NAME: str = Field(default="")  # Will use provider default
    LLM_TEMPERATURE: float = Field(default=0.1, ge=0.0, le=2.0)
    LLM_MAX_TOKENS: int = Field(default=1000, ge=50, le=4000)
    LLM_TIMEOUT: int = Field(default=30, ge=5, le=300)
    LLM_BASE_URL: str | None = Field(default=None)

    # Logging Configuration
    LOG_LEVEL: LogLevel = Field(default=LogLevel.INFO, alias="LOGGING_LEVEL")
    LOG_FORMAT: LogFormat = Field(default=LogFormat.JSON)
    LOG_CONSOLE_ENABLED: bool = Field(default=True)
    LOG_FILE_ENABLED: bool = Field(default=True)
    LOG_FILE_PATH: str = Field(default="logs/app.log")
    LOG_MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024)  # 10MB
    LOG_BACKUP_COUNT: int = Field(default=5)
    LOG_CORRELATION_ID_ENABLED: bool = Field(default=True)

    # API Configuration
    DEFAULT_RETRY_ATTEMPTS: int = Field(default=3, ge=1, le=10)
    DEFAULT_RETRY_DELAY: int = Field(default=5, ge=1, le=60)
    DEFAULT_TIMEOUT: int = Field(default=30, ge=5, le=300)

    # Text Processing Configuration
    TEXT_PROCESSING_MAX_LENGTH: int = Field(default=10000, ge=100)
    TEXT_PROCESSING_MIN_LENGTH: int = Field(default=10, ge=1)
    TEXT_PROCESSING_NORMALIZE_UNICODE: bool = Field(default=True)
    TEXT_PROCESSING_REMOVE_EXTRA_SPACES: bool = Field(default=True)

    # Monitoring Configuration
    MONITORING_METRICS_ENABLED: bool = Field(default=True)
    MONITORING_HEALTH_CHECK_TIMEOUT: int = Field(default=10, ge=1, le=60)
    MONITORING_TRACING_ENABLED: bool = Field(default=False)

    @computed_field
    @property
    def llm_config(self: Any) -> LLMSettings:
        """Generate LLM configuration from individual settings."""
        return LLMSettings(
            provider=self.LLM_PROVIDER,
            api_key=self.LLM_API_KEY,
            model_name=self.LLM_MODEL_NAME,
            temperature=self.LLM_TEMPERATURE,
            max_tokens=self.LLM_MAX_TOKENS,
            timeout=self.LLM_TIMEOUT,
            base_url=self.LLM_BASE_URL,
        )

    @computed_field
    @property
    def logging_config(self: Any) -> LoggingConfig:
        """Generate logging configuration from individual settings."""
        return LoggingConfig(
            level=self.LOG_LEVEL,
            format=self.LOG_FORMAT,
            console_enabled=self.LOG_CONSOLE_ENABLED,
            file_enabled=self.LOG_FILE_ENABLED,
            file_path=self.LOG_FILE_PATH,
            max_file_size=self.LOG_MAX_FILE_SIZE,
            backup_count=self.LOG_BACKUP_COUNT,
            correlation_id_enabled=self.LOG_CORRELATION_ID_ENABLED,
        )

    @property
    def is_development(self: Any) -> bool:
        """Check if running in development mode."""
        return self.DEBUG or self.ENVIRONMENT == Environment.DEVELOPMENT

    @field_validator("LLM_API_KEY")
    @classmethod
    def validate_llm_api_key(cls: Any, v: SecretStr | None, info: Any) -> SecretStr | None:
        """Validate API key based on provider."""
        if not info.data:
            return v

        provider = info.data.get("LLM_PROVIDER", LLMProvider.OLLAMA)
        cloud_providers = {
            LLMProvider.OPENAI,
            LLMProvider.GEMINI,
            LLMProvider.PERPLEXITY,
        }

        if provider in cloud_providers and not v:
            raise ValueError(f"LLM_API_KEY is required for {provider.value}")

        return v

    def setup_logging(self: Any) -> None:
        """Initialize logging using the logging configuration."""
        from .logging import setup_logging

        setup_logging(self.logging_config)

    def model_dump_safe(self: Any) -> dict[str, Any]:
        """Dump settings without exposing secrets."""
        data = self.model_dump()

        # Mask sensitive data
        if "LLM_API_KEY" in data and data["LLM_API_KEY"]:
            data["LLM_API_KEY"] = "***masked***"

        return data


# Global settings instance
settings = Settings()

# Alias for dependency injection
Config = Settings
