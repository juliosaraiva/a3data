"""Configuration management for the incident extractor API."""

import os
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Configuration
    llm_provider: Literal["ollama", "openai", "mock"] = Field(
        default="ollama",
        description="LLM provider to use for text processing",
    )
    ollama_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API endpoint URL",
    )
    model_name: str = Field(
        default="gemma:7b",
        description="Name of the model to use",
    )
    request_timeout: int = Field(
        default=30,
        description="Request timeout in seconds",
        ge=1,
        le=300,
    )

    # API Configuration
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port", ge=1, le=65535)
    debug: bool = Field(default=False, description="Enable debug mode")
    api_title: str = Field(
        default="Incident Extractor API",
        description="API title for documentation",
    )
    api_version: str = Field(
        default="1.0.0",
        description="API version",
    )

    # Preprocessing Configuration
    max_input_length: int = Field(
        default=2000,
        description="Maximum input text length",
        ge=100,
        le=10000,
    )
    enable_text_normalization: bool = Field(
        default=True,
        description="Enable text normalization preprocessing",
    )

    # Logging Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level",
    )

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.debug or os.getenv("ENVIRONMENT", "").lower() in [
            "dev",
            "development",
        ]


# Global settings instance
settings = Settings()
