"""Configuration settings for the incident extractor application."""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    # Application settings
    app_name: str = Field(default="Incident Extractor API", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment (development, production)")

    # API settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_prefix: str = Field(default="/api/v1", description="API prefix")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"], description="CORS allowed origins"
    )

    # LLM settings
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama base URL")
    ollama_model: str = Field(default="llama3.2", description="Default Ollama model")
    ollama_timeout: int = Field(default=60, description="Ollama request timeout in seconds")
    ollama_max_retries: int = Field(default=3, description="Maximum retries for Ollama requests")

    # Fallback LLM settings (for testing or backup)
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-3.5-turbo", description="OpenAI model")

    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    log_file: Optional[str] = Field(default=None, description="Log file path")

    # Performance settings
    max_concurrent_requests: int = Field(default=10, description="Maximum concurrent requests")
    request_timeout: int = Field(default=120, description="Request timeout in seconds")

    # Agent settings
    max_preprocessing_length: int = Field(default=5000, description="Maximum text length for preprocessing")
    extraction_max_retries: int = Field(default=2, description="Maximum extraction retries")

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() in ("development", "dev", "local")

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() in ("production", "prod")


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
