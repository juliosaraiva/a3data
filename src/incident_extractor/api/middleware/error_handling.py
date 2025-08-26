"""
Global error handling middleware.

This module provides centralized error handling and exception processing for the FastAPI application.
Implements production-ready error handling with proper logging, standardized responses, and error categorization.

Features:
- Standardized error response format
- Comprehensive error logging with context
- HTTP status code mapping
- Error categorization and tracking
- Security-aware error responses (no sensitive information leakage)
- Request correlation ID integration
"""

import logging
import traceback
import uuid
from datetime import datetime

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError


class ErrorCategory:
    """Error categories for classification and monitoring."""

    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ErrorResponse(BaseModel):
    """Standardized error response model."""

    error: bool = True
    error_type: str
    error_category: str
    message: str
    details: str | None = None
    request_id: str | None = None
    timestamp: str
    status_code: int


class ErrorHandlingMiddleware:
    """
    Production-ready error handling middleware.

    Provides comprehensive error handling with proper logging, standardized responses,
    and security-aware error processing.
    """

    def __init__(self, logger_name: str = "error_handler"):
        """
        Initialize error handling middleware.

        Args:
            logger_name: Name for the error logger
        """
        self.logger = logging.getLogger(logger_name)

    async def __call__(self, request: Request, call_next) -> Response:
        """
        Process requests with comprehensive error handling.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler

        Returns:
            Response: The HTTP response with proper error handling
        """
        # Generate request ID for correlation
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            return response

        except ValidationError as e:
            return await self._handle_validation_error(e, request_id)

        except HTTPException as e:
            return await self._handle_http_exception(e, request_id, request)

        except Exception as e:
            return await self._handle_generic_exception(e, request_id, request)

    async def _handle_validation_error(self, error: ValidationError, request_id: str) -> JSONResponse:
        """Handle Pydantic validation errors."""
        self.logger.warning(
            "Validation error occurred",
            extra={
                "request_id": request_id,
                "error_count": len(error.errors()),
                "errors": error.errors()[:5],  # Log first 5 errors
            },
        )

        error_response = ErrorResponse(
            error_type="ValidationError",
            error_category=ErrorCategory.VALIDATION,
            message="Input validation failed",
            details=f"Found {len(error.errors())} validation error(s)",
            request_id=request_id,
            timestamp=datetime.now().isoformat(),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error_response.model_dump())

    async def _handle_http_exception(self, error: HTTPException, request_id: str, request: Request) -> JSONResponse:
        """Handle HTTP exceptions with proper categorization."""
        error_category = self._categorize_http_error(error.status_code)

        # Log based on error severity
        log_level = logging.WARNING if error.status_code < 500 else logging.ERROR
        self.logger.log(
            log_level,
            f"HTTP {error.status_code} error occurred",
            extra={
                "request_id": request_id,
                "status_code": error.status_code,
                "path": str(request.url.path),
                "method": request.method,
                "error_category": error_category,
            },
        )

        error_response = ErrorResponse(
            error_type="HTTPException",
            error_category=error_category,
            message=str(error.detail),
            request_id=request_id,
            timestamp=datetime.now().isoformat(),
            status_code=error.status_code,
        )

        return JSONResponse(status_code=error.status_code, content=error_response.model_dump())

    async def _handle_generic_exception(self, error: Exception, request_id: str, request: Request) -> JSONResponse:
        """Handle unexpected exceptions with security-aware logging."""
        # Log full error details for debugging
        self.logger.error(
            f"Unhandled exception occurred: {type(error).__name__}",
            extra={
                "request_id": request_id,
                "path": str(request.url.path),
                "method": request.method,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": traceback.format_exc(),
            },
        )

        # Return generic error response to avoid information leakage
        error_response = ErrorResponse(
            error_type="InternalServerError",
            error_category=ErrorCategory.SYSTEM,
            message="An internal server error occurred",
            details="Please contact support if the problem persists",
            request_id=request_id,
            timestamp=datetime.now().isoformat(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_response.model_dump())

    def _categorize_http_error(self, status_code: int) -> str:
        """Categorize HTTP errors for monitoring and analytics."""
        if status_code == 400:
            return ErrorCategory.VALIDATION
        elif status_code == 401:
            return ErrorCategory.AUTHENTICATION
        elif status_code == 403:
            return ErrorCategory.AUTHORIZATION
        elif status_code == 404:
            return ErrorCategory.NOT_FOUND
        elif status_code == 422:
            return ErrorCategory.VALIDATION
        elif 400 <= status_code < 500:
            return ErrorCategory.BUSINESS_LOGIC
        elif 500 <= status_code < 600:
            return ErrorCategory.SYSTEM
        else:
            return ErrorCategory.UNKNOWN


# Create middleware instance
error_handling_middleware = ErrorHandlingMiddleware()

__all__ = [
    "ErrorHandlingMiddleware",
    "error_handling_middleware",
    "ErrorResponse",
    "ErrorCategory",
]
