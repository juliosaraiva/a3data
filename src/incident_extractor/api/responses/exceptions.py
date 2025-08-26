"""
Custom API Exception Classes

This module provides a comprehensive exception hierarchy for structured
error handling throughout the application with proper HTTP status code
mapping and standardized error messages.
"""

from typing import Any

from fastapi import HTTPException, status


class APIException(HTTPException):
    """
    Base API exception class providing standardized error handling.

    This base class ensures consistent error structure across all
    custom exceptions with proper HTTP status codes and error details.
    """

    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "Internal server error",
        error_code: str = "INTERNAL_ERROR",
        error_type: str = "InternalError",
        field: str | None = None,
        suggestion: str | None = None,
        headers: dict[str, Any] | None = None,
    ):
        """
        Initialize API exception with structured error information.

        Args:
            status_code: HTTP status code
            detail: Human-readable error description
            error_code: Machine-readable error code
            error_type: Error category/type
            field: Specific field that caused the error (if applicable)
            suggestion: Suggested resolution or next steps
            headers: Optional HTTP headers
        """
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code
        self.error_type = error_type
        self.field = field
        self.suggestion = suggestion


# Business Logic Exceptions


class ValidationException(APIException):
    """
    Exception for input validation errors.

    Raised when user input fails validation checks including
    format validation, range validation, or business rule validation.
    """

    def __init__(
        self,
        detail: str,
        field: str | None = None,
        suggestion: str | None = None,
        status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
    ):
        """
        Initialize validation exception.

        Args:
            detail: Specific validation error description
            field: Field that failed validation
            suggestion: Suggested correction
            status_code: HTTP status code (default: 422)
        """
        super().__init__(
            status_code=status_code,
            detail=detail,
            error_code="VALIDATION_ERROR",
            error_type="ValidationError",
            field=field,
            suggestion=suggestion,
        )


class ExtractionException(APIException):
    """
    Exception for incident extraction processing errors.

    Raised when the LLM-based extraction process fails due to
    text processing issues, model errors, or workflow failures.
    """

    def __init__(
        self,
        detail: str,
        extraction_step: str | None = None,
        suggestion: str | None = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        """
        Initialize extraction exception.

        Args:
            detail: Specific extraction error description
            extraction_step: Processing step where error occurred
            suggestion: Suggested resolution
            status_code: HTTP status code (default: 500)
        """
        super().__init__(
            status_code=status_code,
            detail=detail,
            error_code="EXTRACTION_ERROR",
            error_type="ExtractionError",
            field=extraction_step,
            suggestion=suggestion,
        )


class ProcessingException(APIException):
    """
    Exception for general processing errors.

    Raised when business logic processing fails due to
    data issues, computation errors, or workflow problems.
    """

    def __init__(
        self,
        detail: str,
        process_name: str | None = None,
        suggestion: str | None = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        """
        Initialize processing exception.

        Args:
            detail: Specific processing error description
            process_name: Name of the process that failed
            suggestion: Suggested resolution
            status_code: HTTP status code (default: 500)
        """
        super().__init__(
            status_code=status_code,
            detail=detail,
            error_code="PROCESSING_ERROR",
            error_type="ProcessingError",
            field=process_name,
            suggestion=suggestion,
        )


# Infrastructure Exceptions


class ServiceException(APIException):
    """
    Exception for external service integration errors.

    Raised when external services (LLM providers, databases,
    third-party APIs) are unavailable or return errors.
    """

    def __init__(
        self,
        detail: str,
        service_name: str | None = None,
        suggestion: str | None = None,
        status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE,
    ):
        """
        Initialize service exception.

        Args:
            detail: Specific service error description
            service_name: Name of the failing service
            suggestion: Suggested resolution or retry guidance
            status_code: HTTP status code (default: 503)
        """
        super().__init__(
            status_code=status_code,
            detail=detail,
            error_code="SERVICE_ERROR",
            error_type="ServiceError",
            field=service_name,
            suggestion=suggestion or "Please try again later or contact support if the issue persists",
        )


class HealthCheckException(APIException):
    """
    Exception for health check failures.

    Raised when health checks detect critical system issues
    that prevent normal operation.
    """

    def __init__(
        self,
        detail: str,
        component_name: str | None = None,
        suggestion: str | None = None,
        status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE,
    ):
        """
        Initialize health check exception.

        Args:
            detail: Specific health check error description
            component_name: Name of the failing component
            suggestion: Suggested resolution
            status_code: HTTP status code (default: 503)
        """
        super().__init__(
            status_code=status_code,
            detail=detail,
            error_code="HEALTH_CHECK_ERROR",
            error_type="HealthCheckError",
            field=component_name,
            suggestion=suggestion or "Check system status and component health",
        )


class MetricsException(APIException):
    """
    Exception for metrics collection errors.

    Raised when metrics collection or processing fails,
    affecting monitoring and observability.
    """

    def __init__(
        self,
        detail: str,
        metric_name: str | None = None,
        suggestion: str | None = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        """
        Initialize metrics exception.

        Args:
            detail: Specific metrics error description
            metric_name: Name of the metric that failed
            suggestion: Suggested resolution
            status_code: HTTP status code (default: 500)
        """
        super().__init__(
            status_code=status_code,
            detail=detail,
            error_code="METRICS_ERROR",
            error_type="MetricsError",
            field=metric_name,
            suggestion=suggestion or "Check metrics collection system status",
        )


# Specific validation exceptions for common use cases


class TextValidationException(ValidationException):
    """Exception for text input validation errors."""

    def __init__(self, detail: str, text_length: int | None = None):
        """
        Initialize text validation exception.

        Args:
            detail: Specific validation error
            text_length: Length of the invalid text
        """
        suggestion = None
        if text_length is not None:
            if text_length < 10:
                suggestion = "Provide at least 10 characters of incident description"
            elif text_length > 5000:
                suggestion = "Reduce text length to maximum 5000 characters"

        super().__init__(
            detail=detail,
            field="text",
            suggestion=suggestion,
        )


class LLMServiceException(ServiceException):
    """Exception for LLM service integration errors."""

    def __init__(self, detail: str, provider: str | None = None):
        """
        Initialize LLM service exception.

        Args:
            detail: Specific LLM service error
            provider: LLM provider name (e.g., "ollama", "openai")
        """
        super().__init__(
            detail=detail,
            service_name=f"LLM Service ({provider})" if provider else "LLM Service",
            suggestion="Check LLM service availability and configuration",
        )


class WorkflowException(ProcessingException):
    """Exception for LangGraph workflow errors."""

    def __init__(self, detail: str, node_name: str | None = None):
        """
        Initialize workflow exception.

        Args:
            detail: Specific workflow error
            node_name: Name of the workflow node that failed
        """
        super().__init__(
            detail=detail,
            process_name=f"Workflow Node ({node_name})" if node_name else "Workflow",
            suggestion="Check workflow configuration and agent availability",
        )


# Exception handling utilities


def create_error_detail_from_exception(exception: APIException) -> dict[str, Any]:
    """
    Convert APIException to error detail dictionary.

    Args:
        exception: APIException instance

    Returns:
        Dictionary containing structured error information
    """
    error_detail = {
        "error_code": exception.error_code,
        "error_type": exception.error_type,
        "description": exception.detail,
    }

    if exception.field:
        error_detail["field"] = exception.field

    if exception.suggestion:
        error_detail["suggestion"] = exception.suggestion

    return error_detail


def handle_common_exceptions(func):
    """
    Decorator to handle common exceptions and convert them to APIExceptions.

    This decorator catches standard Python exceptions and converts them
    to appropriate APIException subclasses for consistent error handling.
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            raise ValidationException(
                detail=str(e),
                suggestion="Check input data format and values",
            ) from e
        except KeyError as e:
            raise ValidationException(
                detail=f"Missing required field: {str(e)}",
                field=str(e).strip("\"'"),
                suggestion="Ensure all required fields are provided",
            ) from e
        except TimeoutError as e:
            raise ServiceException(
                detail="Request timeout",
                suggestion="Try again with a shorter request or contact support",
            ) from e
        except ConnectionError as e:
            raise ServiceException(
                detail="Service connection failed",
                suggestion="Check service availability and network connectivity",
            ) from e
        except Exception as e:
            # Log unexpected exceptions for debugging
            raise ProcessingException(
                detail=f"Unexpected error: {str(e)}",
                suggestion="Contact support if this error persists",
            ) from e

    return wrapper


__all__ = [
    # Base exception
    "APIException",
    # Business logic exceptions
    "ValidationException",
    "ExtractionException",
    "ProcessingException",
    # Infrastructure exceptions
    "ServiceException",
    "HealthCheckException",
    "MetricsException",
    # Specific exceptions
    "TextValidationException",
    "LLMServiceException",
    "WorkflowException",
    # Utilities
    "create_error_detail_from_exception",
    "handle_common_exceptions",
]
