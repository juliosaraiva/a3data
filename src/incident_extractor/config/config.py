"""Configuration settings for the incident extractor application."""

import os
from functools import lru_cache

from pydantic import Field, computed_field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with production-ready configuration management.

    This class provides comprehensive configuration for both development
    and production environments with proper validation and defaults.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    # Application settings
    app_name: str = Field(default="Incident Extractor API", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment (development, staging, production)")

    # API settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_prefix: str = Field(default="/api/v1", description="API prefix")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"], description="CORS allowed origins"
    )

    # Production security settings
    secret_key: str = Field(default="change-me-in-production-use-secrets-manager", description="Secret key for signing tokens")
    allowed_hosts: list[str] = Field(default=["localhost", "127.0.0.1"], description="Allowed hosts for production")
    enable_docs: bool = Field(default=True, description="Enable OpenAPI docs endpoints")
    enable_metrics: bool = Field(default=True, description="Enable metrics endpoints")

    # LLM settings
    llm_base_url: str = Field(default="http://localhost:11434", description="Ollama base URL", alias="ollama_base_url")
    llm_model_name: str = Field(default="gemma3:4b", description="Default Ollama model", alias="ollama_model")
    llm_timeout: int = Field(default=60, description="Ollama request timeout in seconds", alias="ollama_timeout")
    llm_max_retries: int = Field(default=3, description="Maximum retries for Ollama requests", alias="ollama_max_retries")

    # Maintain backward compatibility
    @computed_field
    @property
    def ollama_base_url(self) -> str:
        return self.llm_base_url

    @computed_field
    @property
    def ollama_model(self) -> str:
        return self.llm_model_name

    @computed_field
    @property
    def ollama_timeout(self) -> int:
        return self.llm_timeout

    @computed_field
    @property
    def ollama_max_retries(self) -> int:
        return self.llm_max_retries

    # Fallback LLM settings (for testing or backup)
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-3.5-turbo", description="OpenAI model")

    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    log_file: str | None = Field(default=None, description="Log file path")
    log_rotation: bool = Field(default=True, description="Enable log rotation")
    log_max_size: str = Field(default="100MB", description="Maximum log file size")
    log_backup_count: int = Field(default=5, description="Number of backup log files")

    # Performance settings
    max_concurrent_requests: int = Field(default=10, description="Maximum concurrent requests")
    request_timeout: int = Field(default=120, description="Request timeout in seconds")
    worker_processes: int = Field(default=1, description="Number of worker processes")
    worker_connections: int = Field(default=1000, description="Worker connections per process")

    # Agent settings
    max_preprocessing_length: int = Field(default=5000, description="Maximum text length for preprocessing")
    extraction_max_retries: int = Field(default=2, description="Maximum extraction retries")

    # Health check settings
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    service_timeout: int = Field(default=5, description="Service health check timeout")

    # Rate limiting settings
    rate_limit_enabled: bool = Field(default=False, description="Enable rate limiting")
    rate_limit_requests_per_minute: int = Field(default=60, description="Requests per minute limit")
    rate_limit_burst_size: int = Field(default=10, description="Burst size for rate limiting")

    # Monitoring and observability
    enable_tracing: bool = Field(default=False, description="Enable distributed tracing")
    metrics_port: int = Field(default=9090, description="Metrics server port")
    sentry_dsn: str | None = Field(default=None, description="Sentry DSN for error tracking")

    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value."""
        allowed = ["development", "dev", "local", "staging", "stage", "production", "prod"]
        if v.lower() not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v.lower()

    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of: {allowed}")
        return v.upper()

    @computed_field
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment in ("development", "dev", "local")

    @computed_field
    @property
    def is_staging(self) -> bool:
        """Check if running in staging mode."""
        return self.environment in ("staging", "stage")

    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment in ("production", "prod")

    @computed_field
    @property
    def uvicorn_log_config(self) -> dict:
        """Get uvicorn logging configuration."""
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
                "access": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(client_addr)s - %(request_line)s - %(status_code)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
                "access": {
                    "formatter": "access",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "uvicorn": {"handlers": ["default"], "level": self.log_level, "propagate": False},
                "uvicorn.error": {"level": self.log_level},
                "uvicorn.access": {"handlers": ["access"], "level": self.log_level, "propagate": False},
            },
        }

    def get_database_url(self) -> str:
        """
        Get database URL with environment-specific configuration.

        Returns:
            str: Database connection URL
        """
        if self.is_production:
            # Production database configuration
            return os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/incident_extractor")
        else:
            # Development database configuration
            return os.getenv("DATABASE_URL", "sqlite:///./incident_extractor.db")

    def get_cors_settings(self) -> dict:
        """
        Get CORS settings based on environment.

        Returns:
            dict: CORS configuration
        """
        if self.is_production:
            return {
                "allow_origins": self.cors_origins,
                "allow_credentials": True,
                "allow_methods": ["GET", "POST"],
                "allow_headers": ["Authorization", "Content-Type"],
            }
        else:
            return {
                "allow_origins": ["*"],
                "allow_credentials": True,
                "allow_methods": ["*"],
                "allow_headers": ["*"],
            }

    def get_security_headers(self) -> dict:
        """
        Get security headers for production.

        Returns:
            dict: Security headers configuration
        """
        if self.is_production:
            return {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Content-Security-Policy": "default-src 'self'",
            }
        else:
            return {}


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
