"""Common/shared schemas used across the API."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
        extra="forbid",
    )


class StatusEnum(str, Enum):
    """Common status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SeverityEnum(str, Enum):
    """Incident severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ValidationLevelEnum(str, Enum):
    """Validation level options."""

    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"


class ExtractionModeEnum(str, Enum):
    """Extraction mode options."""

    FAST = "fast"
    BALANCED = "balanced"
    COMPREHENSIVE = "comprehensive"


class ErrorDetail(BaseSchema):
    """Detailed error information."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    field: str | None = Field(None, description="Field that caused the error")
    details: dict[str, Any] | None = Field(None, description="Additional error details")


class PaginationParams(BaseSchema):
    """Pagination parameters."""

    page: int = Field(1, ge=1, description="Page number (1-based)")
    size: int = Field(20, ge=1, le=100, description="Number of items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.size


class PaginationInfo(BaseSchema):
    """Pagination information in responses."""

    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Items per page")
    total: int = Field(..., description="Total number of items")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")


class TimestampMixin(BaseSchema):
    """Mixin for timestamp fields."""

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")


class ProcessingMetadata(BaseSchema):
    """Metadata about processing operations."""

    processing_id: UUID = Field(..., description="Unique processing identifier")
    correlation_id: str = Field(..., description="Request correlation ID")
    user_id: str | None = Field(None, description="User who initiated the request")
    session_id: str | None = Field(None, description="Session identifier")
    client_info: dict[str, Any] | None = Field(None, description="Client information")
    processing_time_ms: int | None = Field(None, description="Processing time in milliseconds")
    created_at: datetime = Field(..., description="Processing start time")
    completed_at: datetime | None = Field(None, description="Processing completion time")


class HealthStatus(BaseSchema):
    """Health check status."""

    status: str = Field(..., description="Health status (healthy/unhealthy/degraded)")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Application version")
    uptime_seconds: int = Field(..., description="Application uptime in seconds")
    checks: dict[str, Any] = Field(default_factory=dict, description="Individual health checks")


class MetricsSummary(BaseSchema):
    """Summary of system metrics."""

    requests_total: int = Field(..., description="Total number of requests")
    requests_per_minute: float = Field(..., description="Requests per minute")
    average_response_time_ms: float = Field(..., description="Average response time")
    error_rate_percent: float = Field(..., description="Error rate percentage")
    active_connections: int = Field(..., description="Active connections")
    memory_usage_mb: float = Field(..., description="Memory usage in MB")
    cpu_usage_percent: float = Field(..., description="CPU usage percentage")


class APIInfo(BaseSchema):
    """API information and capabilities."""

    name: str = Field(..., description="API name")
    version: str = Field(..., description="API version")
    description: str = Field(..., description="API description")
    supported_languages: list[str] = Field(..., description="Supported languages for processing")
    supported_formats: list[str] = Field(..., description="Supported input formats")
    max_text_length: int = Field(..., description="Maximum text length for processing")
    rate_limits: dict[str, int] = Field(..., description="Rate limit information")
    features: list[str] = Field(..., description="Available features")
    contact: dict[str, str] | None = Field(None, description="Contact information")
    documentation_url: str | None = Field(None, description="Documentation URL")


__all__ = [
    "BaseSchema",
    "StatusEnum",
    "SeverityEnum",
    "ValidationLevelEnum",
    "ExtractionModeEnum",
    "ErrorDetail",
    "PaginationParams",
    "PaginationInfo",
    "TimestampMixin",
    "ProcessingMetadata",
    "HealthStatus",
    "MetricsSummary",
    "APIInfo",
]
