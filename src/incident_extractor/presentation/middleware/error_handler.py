"""Error handler middleware for global exception handling."""

import traceback
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from structlog import get_logger

from ...domain.exceptions import (
    BusinessRuleViolationError,
    DomainError,
    ExtractionError,
    IncidentValidationError,
    InvalidDateTimeError,
    InvalidLocationError,
    LLMRepositoryError,
)

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for global error handling and exception conversion.

    This middleware catches all exceptions and converts them to proper HTTP responses
    with structured error information and appropriate status codes.
    """

    def __init__(self, app, debug: bool = False, include_traceback: bool = False):
        """Initialize error handler middleware.

        Args:
            app: FastAPI application instance
            debug: Whether to include debug information in error responses
            include_traceback: Whether to include stack traces in error responses
        """
        super().__init__(app)
        self.debug = debug
        self.include_traceback = include_traceback

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle exceptions and convert to proper HTTP responses.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware/endpoint in the chain

        Returns:
            Response with error handling applied
        """
        try:
            response = await call_next(request)
            return response

        except HTTPException as exc:
            # FastAPI HTTP exceptions - pass through with logging
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(
                "http_exception",
                request_id=request_id,
                status_code=exc.status_code,
                detail=exc.detail,
                path=request.url.path,
            )
            raise

        except Exception as exc:
            return await self._handle_exception(request, exc)

    async def _handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """Convert exception to structured JSON response.

        Args:
            request: The HTTP request
            exc: The exception that was raised

        Returns:
            JSON response with error details
        """
        request_id = getattr(request.state, "request_id", "unknown")
        error_data = await self._build_error_response(request, exc)

        # Log the error with appropriate level
        log_data = {
            "request_id": request_id,
            "error_type": exc.__class__.__name__,
            "error_message": str(exc),
            "path": request.url.path,
            "method": request.method,
        }

        if error_data["status_code"] >= 500:
            logger.error("server_error", **log_data, **self._get_debug_info(exc))
        else:
            logger.warning("client_error", **log_data)

        return JSONResponse(
            status_code=error_data["status_code"],
            content=jsonable_encoder(error_data),
        )

    async def _build_error_response(self, request: Request, exc: Exception) -> dict[str, Any]:
        """Build structured error response data.

        Args:
            request: The HTTP request
            exc: The exception that was raised

        Returns:
            Dictionary with error response structure
        """
        request_id = getattr(request.state, "request_id", "unknown")

        # Base error structure
        error_response = {
            "error": True,
            "request_id": request_id,
            "timestamp": "2024-01-20T00:00:00Z",  # You'd use actual timestamp
            "path": request.url.path,
        }

        # Domain-specific error handling
        if isinstance(exc, DomainError):
            return await self._handle_domain_error(error_response, exc)
        elif isinstance(exc, ValidationError):
            return await self._handle_validation_error(error_response, exc)
        elif isinstance(exc, LLMRepositoryError):
            return await self._handle_llm_error(error_response, exc)
        else:
            return await self._handle_generic_error(error_response, exc)

    async def _handle_domain_error(self, base_response: dict[str, Any], exc: DomainError) -> dict[str, Any]:
        """Handle domain-specific errors.

        Args:
            base_response: Base error response structure
            exc: Domain exception

        Returns:
            Complete error response
        """
        error_mapping = {
            IncidentValidationError: (400, "incident_validation_failed"),
            InvalidDateTimeError: (400, "invalid_datetime_format"),
            InvalidLocationError: (400, "invalid_location"),
            ExtractionError: (422, "extraction_failed"),
            BusinessRuleViolationError: (400, "business_rule_violation"),
        }

        status_code, error_code = error_mapping.get(type(exc), (400, "domain_error"))

        return {
            **base_response,
            "status_code": status_code,
            "error_code": error_code,
            "message": exc.message,
            "details": exc.details,
        }

    async def _handle_validation_error(self, base_response: dict[str, Any], exc: ValidationError) -> dict[str, Any]:
        """Handle Pydantic validation errors.

        Args:
            base_response: Base error response structure
            exc: Pydantic validation exception

        Returns:
            Complete error response
        """
        return {
            **base_response,
            "status_code": 422,
            "error_code": "validation_error",
            "message": "Request validation failed",
            "details": {
                "validation_errors": exc.errors(),
            },
        }

    async def _handle_llm_error(self, base_response: dict[str, Any], exc: LLMRepositoryError) -> dict[str, Any]:
        """Handle LLM repository errors.

        Args:
            base_response: Base error response structure
            exc: LLM repository exception

        Returns:
            Complete error response
        """
        return {
            **base_response,
            "status_code": 503,
            "error_code": "llm_service_unavailable",
            "message": "LLM service is temporarily unavailable",
            "details": {"error": str(exc)} if self.debug else {},
        }

    async def _handle_generic_error(self, base_response: dict[str, Any], exc: Exception) -> dict[str, Any]:
        """Handle generic/unexpected errors.

        Args:
            base_response: Base error response structure
            exc: Generic exception

        Returns:
            Complete error response
        """
        return {
            **base_response,
            "status_code": 500,
            "error_code": "internal_server_error",
            "message": "An unexpected error occurred" if not self.debug else str(exc),
            "details": self._get_debug_info(exc) if self.debug else {},
        }

    def _get_debug_info(self, exc: Exception) -> dict[str, Any]:
        """Get debug information for an exception.

        Args:
            exc: Exception to get debug info for

        Returns:
            Dictionary with debug information
        """
        debug_info = {
            "exception_type": exc.__class__.__name__,
            "exception_message": str(exc),
        }

        if self.include_traceback:
            debug_info["traceback"] = traceback.format_exception(type(exc), exc, exc.__traceback__)

        return debug_info
