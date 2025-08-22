"""Request schemas for API endpoints."""

from datetime import datetime
from typing import Any

from pydantic import Field, validator

from .common import BaseSchema, ExtractionModeEnum, ValidationLevelEnum


class ExtractIncidentRequest(BaseSchema):
    """Request schema for incident extraction."""

    text: str = Field(
        ...,
        min_length=10,
        max_length=50000,
        description="Text to extract incident information from",
        example="Incidente reportado às 14:30 em São Paulo. Falha do sistema causou interrupção de 2 horas no serviço.",
    )

    extraction_mode: ExtractionModeEnum = Field(
        ExtractionModeEnum.BALANCED,
        description="Extraction mode affecting speed vs accuracy trade-off",
        example="balanced",
    )

    validation_level: ValidationLevelEnum = Field(
        ValidationLevelEnum.STANDARD,
        description="Level of validation to apply to extracted data",
        example="standard",
    )

    context: dict[str, Any] | None = Field(
        None,
        description="Additional context to improve extraction accuracy",
        example={"source": "support_ticket", "priority": "high"},
    )

    metadata: dict[str, Any] | None = Field(
        None,
        description="Request metadata for tracking and analytics",
        example={"client_version": "1.0.0", "source_ip": "192.168.1.1"},
    )

    async_processing: bool = Field(
        True,
        description="Whether to process asynchronously (recommended for large texts)",
        example=True,
    )

    callback_url: str | None = Field(
        None,
        description="URL to receive completion notification (for async processing)",
        example="https://api.example.com/webhooks/extraction-complete",
    )

    @validator("text")
    def validate_text_content(cls, v: str) -> str:
        """Validate text content."""
        if not v.strip():
            raise ValueError("Text cannot be empty or only whitespace")
        return v.strip()

    @validator("callback_url")
    def validate_callback_url(cls, v: str | None) -> str | None:
        """Validate callback URL format."""
        if v is not None:
            if not v.startswith(("http://", "https://")):
                raise ValueError("Callback URL must be a valid HTTP/HTTPS URL")
        return v

    class Config:
        schema_extra = {
            "example": {
                "text": "Incidente reportado às 14:30 em São Paulo. Sistema de pagamento falhou causando interrupção de 2 horas no e-commerce. Perda estimada de R$ 50.000. Prioridade crítica.",
                "extraction_mode": "balanced",
                "validation_level": "standard",
                "context": {"source": "support_ticket", "system": "payment_gateway", "priority": "critical"},
                "async_processing": True,
                "callback_url": "https://api.example.com/webhooks/extraction-complete",
            }
        }


class AuthTokenRequest(BaseSchema):
    """Request schema for authentication token."""

    username: str | None = Field(
        None,
        description="Username for authentication",
        example="user@example.com",
    )

    password: str | None = Field(
        None,
        description="Password for authentication",
        example="secure_password123",
    )

    api_key: str | None = Field(
        None,
        description="API key for authentication",
        example="ak_1234567890abcdef",
    )

    grant_type: str = Field(
        "password",
        description="OAuth2 grant type",
        example="password",
    )

    scopes: list[str] | None = Field(
        None,
        description="Requested access scopes",
        example=["incidents:read", "incidents:write"],
    )

    @validator("grant_type")
    def validate_grant_type(cls, v: str) -> str:
        """Validate grant type."""
        allowed_types = ["password", "api_key", "refresh_token"]
        if v not in allowed_types:
            raise ValueError(f"Grant type must be one of: {allowed_types}")
        return v

    class Config:
        schema_extra = {
            "example": {
                "username": "user@example.com",
                "password": "secure_password123",
                "grant_type": "password",
                "scopes": ["incidents:read", "incidents:write"],
            }
        }


class RefreshTokenRequest(BaseSchema):
    """Request schema for token refresh."""

    refresh_token: str = Field(
        ...,
        description="Valid refresh token",
        example="rt_abcdef1234567890",
    )

    grant_type: str = Field(
        "refresh_token",
        description="Grant type for refresh",
        example="refresh_token",
    )

    class Config:
        schema_extra = {"example": {"refresh_token": "rt_abcdef1234567890", "grant_type": "refresh_token"}}


class ProcessingStatusRequest(BaseSchema):
    """Request parameters for processing status."""

    include_details: bool = Field(
        False,
        description="Whether to include detailed processing information",
        example=True,
    )

    include_logs: bool = Field(
        False,
        description="Whether to include processing logs",
        example=False,
    )


class HealthCheckRequest(BaseSchema):
    """Request parameters for health check."""

    detailed: bool = Field(
        False,
        description="Whether to return detailed health information",
        example=True,
    )

    check_dependencies: bool = Field(
        True,
        description="Whether to check external dependencies",
        example=True,
    )

    timeout_seconds: int = Field(
        30,
        ge=1,
        le=300,
        description="Timeout for health checks in seconds",
        example=30,
    )


class MetricsRequest(BaseSchema):
    """Request parameters for metrics."""

    format: str = Field(
        "json",
        description="Response format (json or prometheus)",
        example="json",
    )

    include_system: bool = Field(
        True,
        description="Whether to include system metrics",
        example=True,
    )

    include_application: bool = Field(
        True,
        description="Whether to include application metrics",
        example=True,
    )

    time_range: str | None = Field(
        None,
        description="Time range for metrics (e.g., '1h', '24h', '7d')",
        example="1h",
    )

    @validator("format")
    def validate_format(cls, v: str) -> str:
        """Validate metrics format."""
        allowed_formats = ["json", "prometheus"]
        if v not in allowed_formats:
            raise ValueError(f"Format must be one of: {allowed_formats}")
        return v


class AdminStatsRequest(BaseSchema):
    """Request parameters for admin statistics."""

    start_date: datetime | None = Field(
        None,
        description="Start date for statistics",
        example="2025-08-22T00:00:00Z",
    )

    end_date: datetime | None = Field(
        None,
        description="End date for statistics",
        example="2025-08-22T23:59:59Z",
    )

    group_by: str | None = Field(
        None,
        description="Group statistics by (hour, day, week, month)",
        example="day",
    )

    include_users: bool = Field(
        False,
        description="Whether to include user statistics",
        example=True,
    )

    @validator("group_by")
    def validate_group_by(cls, v: str | None) -> str | None:
        """Validate group_by parameter."""
        if v is not None:
            allowed_values = ["hour", "day", "week", "month"]
            if v not in allowed_values:
                raise ValueError(f"Group by must be one of: {allowed_values}")
        return v


__all__ = [
    "ExtractIncidentRequest",
    "AuthTokenRequest",
    "RefreshTokenRequest",
    "ProcessingStatusRequest",
    "HealthCheckRequest",
    "MetricsRequest",
    "AdminStatsRequest",
]
