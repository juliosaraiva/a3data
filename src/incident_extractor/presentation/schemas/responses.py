"""Response schemas for API endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from .common import (
    APIInfo,
    BaseSchema,
    ErrorDetail,
    MetricsSummary,
    PaginationInfo,
    ProcessingMetadata,
    SeverityEnum,
    StatusEnum,
    TimestampMixin,
)


class ExtractIncidentResponse(BaseSchema):
    """Response schema for incident extraction initiation."""

    processing_id: UUID = Field(..., description="Unique identifier for tracking the extraction process")
    status: StatusEnum = Field(..., description="Current status of the extraction process")
    estimated_completion_time: datetime | None = Field(None, description="Estimated completion time for the extraction")
    callback_url: str | None = Field(None, description="URL that will receive completion notification")
    message: str = Field(..., description="Human-readable status message")

    class Config:
        schema_extra = {
            "example": {
                "processing_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "in_progress",
                "estimated_completion_time": "2025-08-22T15:35:00Z",
                "message": "Extraction process started successfully",
            }
        }


class IncidentData(BaseSchema):
    """Extracted incident information."""

    title: str | None = Field(None, description="Incident title or summary")
    description: str = Field(..., description="Detailed incident description")
    severity: SeverityEnum = Field(..., description="Incident severity level")
    occurred_at: datetime | None = Field(None, description="When the incident occurred")
    location: str | None = Field(None, description="Where the incident occurred")
    affected_systems: list[str] = Field(default_factory=list, description="Systems affected by the incident")
    impact_description: str | None = Field(None, description="Description of the incident impact")
    financial_impact: str | None = Field(None, description="Financial impact if mentioned")
    duration: str | None = Field(None, description="Incident duration if mentioned")
    root_cause: str | None = Field(None, description="Root cause if identified")
    resolution: str | None = Field(None, description="Resolution if mentioned")
    tags: list[str] = Field(default_factory=list, description="Extracted tags or categories")
    confidence_scores: dict[str, float] = Field(default_factory=dict, description="Confidence scores for each extracted field")

    class Config:
        schema_extra = {
            "example": {
                "title": "Payment System Outage",
                "description": "Sistema de pagamento falhou causando interrupção no e-commerce",
                "severity": "critical",
                "occurred_at": "2025-08-22T14:30:00-03:00",
                "location": "São Paulo",
                "affected_systems": ["payment_gateway", "e-commerce"],
                "impact_description": "E-commerce platform unavailable for 2 hours",
                "financial_impact": "R$ 50.000",
                "duration": "2 hours",
                "tags": ["payment", "outage", "critical"],
                "confidence_scores": {"severity": 0.95, "occurred_at": 0.88, "location": 0.92, "financial_impact": 0.78},
            }
        }


class IncidentExtractionResult(BaseSchema, TimestampMixin):
    """Complete incident extraction result."""

    processing_id: UUID = Field(..., description="Processing identifier")
    status: StatusEnum = Field(..., description="Final processing status")
    incident: IncidentData | None = Field(None, description="Extracted incident data")
    original_text: str = Field(..., description="Original input text")
    processed_text: str = Field(..., description="Preprocessed text used for extraction")
    extraction_metadata: ProcessingMetadata = Field(..., description="Processing metadata")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Overall extraction quality score")
    validation_results: dict[str, Any] | None = Field(None, description="Validation results if requested")
    errors: list[ErrorDetail] = Field(default_factory=list, description="Any errors encountered during processing")
    warnings: list[str] = Field(default_factory=list, description="Processing warnings")

    class Config:
        schema_extra = {
            "example": {
                "processing_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "incident": {
                    "title": "Payment System Outage",
                    "description": "Sistema de pagamento falhou causando interrupção no e-commerce",
                    "severity": "critical",
                    "occurred_at": "2025-08-22T14:30:00-03:00",
                    "location": "São Paulo",
                },
                "quality_score": 0.89,
                "created_at": "2025-08-22T15:30:00Z",
                "updated_at": "2025-08-22T15:32:00Z",
            }
        }


class ProcessingStatusResponse(BaseSchema):
    """Response schema for processing status queries."""

    processing_id: UUID = Field(..., description="Processing identifier")
    status: StatusEnum = Field(..., description="Current processing status")
    progress: float = Field(..., ge=0.0, le=1.0, description="Processing progress (0.0 to 1.0)")
    current_step: str = Field(..., description="Current processing step")
    estimated_completion_time: datetime | None = Field(None, description="Estimated completion time")
    result_available: bool = Field(..., description="Whether results are available for retrieval")
    result_url: str | None = Field(None, description="URL to retrieve results if available")
    errors: list[ErrorDetail] = Field(default_factory=list, description="Any errors encountered")
    logs: list[dict[str, Any]] | None = Field(None, description="Processing logs if requested")

    class Config:
        schema_extra = {
            "example": {
                "processing_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "in_progress",
                "progress": 0.65,
                "current_step": "extracting_incident_data",
                "estimated_completion_time": "2025-08-22T15:35:00Z",
                "result_available": False,
            }
        }


class AuthTokenResponse(BaseSchema):
    """Response schema for authentication tokens."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    refresh_token: str | None = Field(None, description="Refresh token if applicable")
    scopes: list[str] = Field(..., description="Granted access scopes")

    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
                "refresh_token": "rt_abcdef1234567890",
                "scopes": ["incidents:read", "incidents:write"],
            }
        }


class HealthCheckResponse(BaseSchema):
    """Response schema for health checks."""

    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Application version")
    uptime_seconds: int = Field(..., description="Application uptime")
    checks: dict[str, dict[str, Any]] = Field(..., description="Individual component health checks")

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-08-22T15:30:00Z",
                "version": "1.0.0",
                "uptime_seconds": 86400,
                "checks": {
                    "database": {"status": "healthy", "response_time_ms": 15},
                    "llm_service": {"status": "healthy", "response_time_ms": 250},
                },
            }
        }


class MetricsResponse(BaseSchema):
    """Response schema for system metrics."""

    timestamp: datetime = Field(..., description="Metrics collection timestamp")
    summary: MetricsSummary = Field(..., description="Summary metrics")
    detailed_metrics: dict[str, Any] | None = Field(None, description="Detailed metrics if requested")

    class Config:
        schema_extra = {
            "example": {
                "timestamp": "2025-08-22T15:30:00Z",
                "summary": {
                    "requests_total": 1250,
                    "requests_per_minute": 25.5,
                    "average_response_time_ms": 180.5,
                    "error_rate_percent": 0.8,
                    "active_connections": 15,
                },
            }
        }


class APIInfoResponse(BaseSchema):
    """Response schema for API information."""

    api_info: APIInfo = Field(..., description="API information and capabilities")

    class Config:
        schema_extra = {
            "example": {
                "api_info": {
                    "name": "Incident Extractor API",
                    "version": "1.0.0",
                    "description": "LLM-powered incident information extraction API",
                    "supported_languages": ["Portuguese", "English"],
                    "supported_formats": ["text/plain"],
                    "max_text_length": 50000,
                    "features": ["async_processing", "confidence_scores", "validation"],
                }
            }
        }


class AdminStatsResponse(BaseSchema):
    """Response schema for admin statistics."""

    period: dict[str, datetime] = Field(..., description="Statistics time period")
    total_extractions: int = Field(..., description="Total extractions in period")
    successful_extractions: int = Field(..., description="Successful extractions")
    failed_extractions: int = Field(..., description="Failed extractions")
    average_processing_time_ms: float = Field(..., description="Average processing time")
    top_error_types: list[dict[str, Any]] = Field(..., description="Most common error types")
    user_statistics: dict[str, Any] | None = Field(None, description="User statistics if requested")
    system_performance: dict[str, Any] = Field(..., description="System performance metrics")

    class Config:
        schema_extra = {
            "example": {
                "period": {"start": "2025-08-22T00:00:00Z", "end": "2025-08-22T23:59:59Z"},
                "total_extractions": 1250,
                "successful_extractions": 1230,
                "failed_extractions": 20,
                "average_processing_time_ms": 1850.5,
            }
        }


class ErrorResponse(BaseSchema):
    """Standardized error response schema."""

    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    details: list[ErrorDetail] | None = Field(None, description="Detailed error information")
    timestamp: datetime = Field(..., description="Error occurrence timestamp")
    request_id: str | None = Field(None, description="Request correlation ID")

    class Config:
        schema_extra = {
            "example": {
                "error": "validation_error",
                "message": "Input validation failed",
                "details": [{"code": "value_error.missing", "message": "field required", "field": "text"}],
                "timestamp": "2025-08-22T15:30:00Z",
                "request_id": "req_abcdef1234567890",
            }
        }


class PaginatedResponse(BaseSchema):
    """Generic paginated response schema."""

    items: list[Any] = Field(..., description="List of items")
    pagination: PaginationInfo = Field(..., description="Pagination information")

    class Config:
        schema_extra = {
            "example": {
                "items": [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}],
                "pagination": {"page": 1, "size": 20, "total": 100, "pages": 5, "has_next": True, "has_previous": False},
            }
        }


__all__ = [
    "ExtractIncidentResponse",
    "IncidentData",
    "IncidentExtractionResult",
    "ProcessingStatusResponse",
    "AuthTokenResponse",
    "HealthCheckResponse",
    "MetricsResponse",
    "APIInfoResponse",
    "AdminStatsResponse",
    "ErrorResponse",
    "PaginatedResponse",
]
