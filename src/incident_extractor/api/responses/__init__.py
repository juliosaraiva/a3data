"""
API Response Module

This module provides standardized response models and custom exceptions
for consistent API behavior across all endpoints.

Components:
- models: Standardized response schemas with metadata
- exceptions: Domain-specific exception classes with HTTP status mapping
"""

from .exceptions import (
    # Base exception
    APIException,
    ExtractionException,
    HealthCheckException,
    LLMServiceException,
    MetricsException,
    ProcessingException,
    # Infrastructure exceptions
    ServiceException,
    # Specific exceptions
    TextValidationException,
    # Business logic exceptions
    ValidationException,
    WorkflowException,
    # Utilities
    create_error_detail_from_exception,
    handle_common_exceptions,
)
from .models import (
    # Base response models
    BaseResponse,
    DebugData,
    DebugResponse,
    ErrorDetail,
    ErrorResponse,
    ExtractionData,
    ExtractionResponse,
    # Data models
    HealthData,
    # Typed response aliases
    HealthResponse,
    MetricsData,
    MetricsResponse,
    # Metadata models
    ResponseMetadata,
    ResponseStatus,
    SuccessResponse,
    create_error_response,
    # Helper functions
    create_success_response,
)

__all__ = [
    # Response models
    "BaseResponse",
    "SuccessResponse",
    "ErrorResponse",
    "ResponseMetadata",
    "ResponseStatus",
    "ErrorDetail",
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
    # Exception classes
    "APIException",
    "ValidationException",
    "ExtractionException",
    "ProcessingException",
    "ServiceException",
    "HealthCheckException",
    "MetricsException",
    "TextValidationException",
    "LLMServiceException",
    "WorkflowException",
    # Exception utilities
    "create_error_detail_from_exception",
    "handle_common_exceptions",
]
