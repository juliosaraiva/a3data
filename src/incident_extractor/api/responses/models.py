"""
Standardized API Response Models

This module provides production-ready response models for consistent
API responses across all endpoints with proper metadata inclusion,
error handling, and structured data formatting.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

# Generic type for response data
T = TypeVar("T")


class ResponseStatus(str, Enum):
    """Standard response status values."""

    SUCCESS = "success"
    ERROR = "error"
    PARTIAL_SUCCESS = "partial_success"
    WARNING = "warning"


class ResponseMetadata(BaseModel):
    """
    Standard metadata included in all API responses.

    Provides tracking, timing, and context information for
    monitoring and debugging purposes.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "request_id": "req_123456",
                "timestamp": "2025-08-25T20:30:00Z",
                "processing_time_ms": 125.5,
                "api_version": "1.0.0",
                "endpoint": "/api/v1/incidents/extract",
            }
        }
    )

    request_id: str = Field(
        default_factory=lambda: f"req_{uuid4().hex[:12]}", description="Unique request identifier for tracking and correlation"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z", description="Response timestamp in ISO 8601 format"
    )
    processing_time_ms: float | None = Field(default=None, description="Processing time in milliseconds", ge=0.0)
    api_version: str = Field(default="1.0.0", description="API version used for this response")
    endpoint: str | None = Field(default=None, description="API endpoint that generated this response")


class BaseResponse(BaseModel, Generic[T]):
    """
    Base response model providing consistent structure for all API responses.

    This generic model ensures all responses have consistent metadata,
    status information, and structured data formatting.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "data": {},
                "metadata": {"request_id": "req_123456", "timestamp": "2025-08-25T20:30:00Z", "processing_time_ms": 125.5},
            }
        }
    )

    status: ResponseStatus = Field(description="Response status indicating success, error, or partial success")
    message: str = Field(description="Human-readable status message")
    data: T | None = Field(None, description="Response payload data")
    metadata: ResponseMetadata = Field(
        default_factory=lambda: ResponseMetadata(), description="Response metadata for tracking and monitoring"
    )


class SuccessResponse(BaseResponse[T]):
    """
    Success response model for successful operations.

    Pre-configured with success status and positive messaging
    patterns for consistent success responses.
    """

    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS, description="Success status")
    message: str = Field(default="Operation completed successfully", description="Success message")


class ErrorDetail(BaseModel):
    """
    Structured error detail information.

    Provides comprehensive error information including error codes,
    context, and potential resolution guidance.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_code": "VALIDATION_ERROR",
                "error_type": "ValidationError",
                "field": "text",
                "description": "Input text is too short for processing",
                "suggestion": "Provide at least 10 characters of incident description",
            }
        }
    )

    error_code: str = Field(description="Machine-readable error code for programmatic handling")
    error_type: str = Field(description="Error category/type for classification")
    field: str | None = Field(None, description="Specific field that caused the error (if applicable)")
    description: str = Field(description="Human-readable error description")
    suggestion: str | None = Field(None, description="Suggested resolution or next steps")


class ErrorResponse(BaseResponse[None]):
    """
    Error response model for failed operations.

    Provides structured error information with details for debugging
    and user guidance while maintaining consistent response format.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "error",
                "message": "Validation failed",
                "errors": [
                    {
                        "error_code": "VALIDATION_ERROR",
                        "error_type": "ValidationError",
                        "description": "Input text is too short for processing",
                    }
                ],
                "metadata": {"request_id": "req_123456", "timestamp": "2025-08-25T20:30:00Z"},
            }
        }
    )

    status: ResponseStatus = Field(default=ResponseStatus.ERROR, description="Error status")
    errors: list[ErrorDetail] = Field(default_factory=list, description="List of error details")
    data: None = Field(default=None, description="No data in error responses")


# Domain-specific response models


class HealthData(BaseModel):
    """Health check response data structure."""

    service_status: str = Field(description="Overall service health status")
    components: dict[str, Any] = Field(default_factory=dict, description="Individual component health status")
    uptime_seconds: float | None = Field(None, description="Service uptime in seconds")
    version: str | None = Field(None, description="Application version")


class ExtractionData(BaseModel):
    """Incident extraction response data structure."""

    extracted_fields: dict[str, Any] = Field(description="Extracted incident information fields")
    confidence_scores: dict[str, float] | None = Field(None, description="Confidence scores for extracted fields")
    processing_steps: list[str] | None = Field(None, description="Processing steps taken during extraction")
    warnings: list[str] | None = Field(None, description="Processing warnings (non-fatal issues)")


class MetricsData(BaseModel):
    """Metrics response data structure."""

    performance_metrics: dict[str, Any] = Field(description="Application performance metrics")
    system_metrics: dict[str, Any] | None = Field(None, description="System-level metrics")
    health_score: float | None = Field(None, description="Overall system health score", ge=0.0, le=100.0)
    collection_period: str | None = Field(None, description="Metrics collection time period")


class DebugData(BaseModel):
    """Debug information response data structure."""

    system_info: dict[str, Any] = Field(description="System diagnostic information")
    configuration: dict[str, Any] | None = Field(None, description="Application configuration (sanitized)")
    component_status: list[dict[str, Any]] | None = Field(None, description="Individual component status information")
    diagnostics: dict[str, Any] | None = Field(None, description="Additional diagnostic information")


# Typed response aliases for common use cases
HealthResponse = SuccessResponse[HealthData]
ExtractionResponse = SuccessResponse[ExtractionData]
MetricsResponse = SuccessResponse[MetricsData]
DebugResponse = SuccessResponse[DebugData]


def create_success_response(
    data: T,
    message: str = "Operation completed successfully",
    request_id: str | None = None,
    processing_time_ms: float | None = None,
    endpoint: str | None = None,
) -> SuccessResponse[T]:
    """
    Helper function to create standardized success responses.

    Args:
        data: Response data payload
        message: Success message
        request_id: Optional request ID (generated if not provided)
        processing_time_ms: Processing time in milliseconds
        endpoint: API endpoint path

    Returns:
        Standardized success response with metadata
    """
    metadata = ResponseMetadata()
    if request_id:
        metadata.request_id = request_id
    if processing_time_ms is not None:
        metadata.processing_time_ms = processing_time_ms
    if endpoint:
        metadata.endpoint = endpoint

    return SuccessResponse[T](data=data, message=message, metadata=metadata)


def create_error_response(
    message: str,
    errors: list[ErrorDetail],
    status: ResponseStatus = ResponseStatus.ERROR,
    request_id: str | None = None,
    endpoint: str | None = None,
) -> ErrorResponse:
    """
    Helper function to create standardized error responses.

    Args:
        message: Error message
        errors: List of error details
        status: Response status (default: ERROR)
        request_id: Optional request ID (generated if not provided)
        endpoint: API endpoint path

    Returns:
        Standardized error response with metadata
    """
    metadata = ResponseMetadata()
    if request_id:
        metadata.request_id = request_id
    if endpoint:
        metadata.endpoint = endpoint

    return ErrorResponse(message=message, errors=errors, status=status, metadata=metadata)


__all__ = [
    # Base models
    "BaseResponse",
    "SuccessResponse",
    "ErrorResponse",
    "ResponseMetadata",
    "ErrorDetail",
    # Enums
    "ResponseStatus",
    # Data models
    "HealthData",
    "ExtractionData",
    "MetricsData",
    "DebugData",
    # Typed responses
    "HealthResponse",
    "ExtractionResponse",
    "MetricsResponse",
    "DebugResponse",
    # Helper functions
    "create_success_response",
    "create_error_response",
]
