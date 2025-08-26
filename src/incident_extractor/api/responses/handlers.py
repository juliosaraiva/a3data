"""
Global exception handlers for FastAPI.

This module provides centralized exception handling to ensure
all errors are transformed into standardized responses with
proper logging and recovery guidance.
"""

import asyncio
import traceback
import uuid
from typing import Dict, Optional

from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from incident_extractor.config import get_logger
from incident_extractor.api.responses.exceptions import (
    BaseAPIException,
    ValidationError,
    ExtractionError,
    ServiceUnavailableError,
    TimeoutError,
    ConfigurationError,
    RateLimitError,
)
from incident_extractor.api.responses.models import ErrorResponse

logger = get_logger("app.exception_handlers")


def get_request_id(request: Request) -> str:
    """
    Extract or generate request ID for correlation.

    Args:
        request: FastAPI request object

    Returns:
        Request ID string
    """
    # Try to get request ID from headers first
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        # Try to get from request state (set by middleware)
        request_id = getattr(request.state, "request_id", None)

    # Generate new ID if none found
    if not request_id:
        request_id = str(uuid.uuid4())

    return request_id


def get_processing_time(request: Request) -> Optional[float]:
    """
    Extract processing time from request state.

    Args:
        request: FastAPI request object

    Returns:
        Processing time in milliseconds or None
    """
    start_time = getattr(request.state, "start_time", None)
    if start_time is None:
        return None

    import time

    return (time.time() - start_time) * 1000


async def base_api_exception_handler(request: Request, exc: BaseAPIException) -> JSONResponse:
    """
    Handle custom BaseAPIException instances.

    Transforms custom exceptions into standardized error responses
    with proper logging and request correlation.

    Args:
        request: FastAPI request object
        exc: Custom exception instance

    Returns:
        Standardized JSON error response
    """
    request_id = get_request_id(request)
    processing_time_ms = get_processing_time(request)

    # Log the exception with context
    logger.error(
        f"API Exception: {exc.error_code}",
        extra={
            "request_id": request_id,
            "error_code": exc.error_code,
            "message": exc.message,
            "context": exc.context,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )

    # Create standardized error response
    error_response = ErrorResponse.create_error(
        message=exc.message,
        error_code=exc.error_code,
        error_type=exc.__class__.__name__,
        field_errors=exc.context.get("field_errors") if exc.context else None,
        context=exc.context,
        recovery_suggestions=exc.recovery_suggestions,
        request_id=request_id,
        processing_time_ms=processing_time_ms,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle standard FastAPI HTTPException instances.

    Transforms standard HTTP exceptions into standardized error responses.

    Args:
        request: FastAPI request object
        exc: HTTP exception instance

    Returns:
        Standardized JSON error response
    """
    request_id = get_request_id(request)
    processing_time_ms = get_processing_time(request)

    # Log standard HTTP exceptions
    logger.warning(
        f"HTTP Exception: {exc.status_code}",
        extra={
            "request_id": request_id,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method,
        },
    )

    # Determine error type and recovery suggestions based on status code
    error_code_map = {
        400: ("BAD_REQUEST", ["Verifique os parâmetros da requisição"]),
        401: ("UNAUTHORIZED", ["Verifique as credenciais de autenticação"]),
        403: ("FORBIDDEN", ["Acesso negado - verifique permissões"]),
        404: ("NOT_FOUND", ["Verifique se o endpoint existe", "Consulte a documentação da API"]),
        405: ("METHOD_NOT_ALLOWED", ["Método HTTP não permitido para este endpoint"]),
        422: ("UNPROCESSABLE_ENTITY", ["Verifique os dados de entrada"]),
        500: ("INTERNAL_SERVER_ERROR", ["Erro interno do servidor", "Tente novamente mais tarde"]),
    }

    error_code, recovery_suggestions = error_code_map.get(exc.status_code, ("HTTP_ERROR", ["Consulte a documentação da API"]))

    # Create standardized error response
    error_response = ErrorResponse.create_error(
        message=str(exc.detail) if exc.detail else f"Erro HTTP {exc.status_code}",
        error_code=error_code,
        error_type="HTTPException",
        context={"status_code": exc.status_code, "original_detail": exc.detail},
        recovery_suggestions=recovery_suggestions,
        request_id=request_id,
        processing_time_ms=processing_time_ms,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle FastAPI request validation errors.

    Transforms validation errors into standardized error responses
    with field-level error details.

    Args:
        request: FastAPI request object
        exc: Request validation error instance

    Returns:
        Standardized JSON error response
    """
    request_id = get_request_id(request)
    processing_time_ms = get_processing_time(request)

    # Process field errors
    field_errors: Dict[str, list[str]] = {}
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        error_msg = error["msg"]

        if field_path not in field_errors:
            field_errors[field_path] = []
        field_errors[field_path].append(error_msg)

    # Log validation error
    logger.warning(
        "Validation Error",
        extra={
            "request_id": request_id,
            "field_errors": field_errors,
            "path": request.url.path,
            "method": request.method,
        },
    )

    # Create standardized error response
    error_response = ErrorResponse.create_error(
        message="Erro de validação nos dados de entrada",
        error_code="VALIDATION_ERROR",
        error_type="RequestValidationError",
        field_errors=field_errors,
        context={
            "validation_type": "request_validation",
            "error_count": len(exc.errors()),
        },
        recovery_suggestions=[
            "Verifique os dados de entrada e corrija os erros indicados",
            "Consulte a documentação da API para o formato esperado",
            "Certifique-se de que todos os campos obrigatórios estão presentes",
        ],
        request_id=request_id,
        processing_time_ms=processing_time_ms,
    )

    return JSONResponse(
        status_code=422,
        content=error_response.model_dump(),
    )


async def pydantic_validation_exception_handler(request: Request, exc: PydanticValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Transforms Pydantic validation errors into standardized responses.

    Args:
        request: FastAPI request object
        exc: Pydantic validation error instance

    Returns:
        Standardized JSON error response
    """
    request_id = get_request_id(request)
    processing_time_ms = get_processing_time(request)

    # Process field errors
    field_errors: Dict[str, list[str]] = {}
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        error_msg = error["msg"]

        if field_path not in field_errors:
            field_errors[field_path] = []
        field_errors[field_path].append(error_msg)

    # Log validation error
    logger.warning(
        "Pydantic Validation Error",
        extra={
            "request_id": request_id,
            "field_errors": field_errors,
            "path": request.url.path,
            "method": request.method,
        },
    )

    # Create standardized error response
    error_response = ErrorResponse.create_error(
        message="Erro de validação nos dados",
        error_code="PYDANTIC_VALIDATION_ERROR",
        error_type="PydanticValidationError",
        field_errors=field_errors,
        context={
            "validation_type": "pydantic_validation",
            "error_count": len(exc.errors()),
        },
        recovery_suggestions=[
            "Verifique se os dados estão no formato correto",
            "Consulte a documentação para os tipos de dados esperados",
        ],
        request_id=request_id,
        processing_time_ms=processing_time_ms,
    )

    return JSONResponse(
        status_code=422,
        content=error_response.model_dump(),
    )


async def timeout_exception_handler(request: Request, exc: asyncio.TimeoutError) -> JSONResponse:
    """
    Handle asyncio timeout errors.

    Transforms timeout errors into standardized timeout responses.

    Args:
        request: FastAPI request object
        exc: Asyncio timeout error instance

    Returns:
        Standardized JSON error response
    """
    request_id = get_request_id(request)
    processing_time_ms = get_processing_time(request)

    # Log timeout error
    logger.error(
        "Request Timeout",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "processing_time_ms": processing_time_ms,
        },
        exc_info=True,
    )

    # Create timeout error response
    error_response = ErrorResponse.create_error(
        message="Operação excedeu tempo limite",
        error_code="REQUEST_TIMEOUT",
        error_type="TimeoutError",
        context={
            "operation_type": "request_processing",
            "processing_time_ms": processing_time_ms,
        },
        recovery_suggestions=[
            "Tente novamente com dados menos complexos",
            "Verifique a conectividade de rede",
            "Se o problema persistir, contate o suporte",
        ],
        request_id=request_id,
        processing_time_ms=processing_time_ms,
    )

    return JSONResponse(
        status_code=408,
        content=error_response.model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all unhandled exceptions.

    Last resort handler for unexpected errors. Provides safe error
    response without exposing internal details in production.

    Args:
        request: FastAPI request object
        exc: Unhandled exception instance

    Returns:
        Standardized JSON error response
    """
    request_id = get_request_id(request)
    processing_time_ms = get_processing_time(request)

    # Get detailed error information for logging
    error_traceback = traceback.format_exc()

    # Log the unhandled exception with full context
    logger.critical(
        f"Unhandled Exception: {exc.__class__.__name__}",
        extra={
            "request_id": request_id,
            "exception_type": exc.__class__.__name__,
            "exception_message": str(exc),
            "path": request.url.path,
            "method": request.method,
            "processing_time_ms": processing_time_ms,
            "traceback": error_traceback,
        },
        exc_info=True,
    )

    # Create safe error response (don't expose internal details)
    error_response = ErrorResponse.create_error(
        message="Erro interno do servidor",
        error_code="INTERNAL_SERVER_ERROR",
        error_type="InternalError",
        context={
            "exception_type": exc.__class__.__name__,
            # Only include exception message in debug mode
            "debug_info": str(exc) if getattr(request.app.state, "debug", False) else None,
        },
        recovery_suggestions=[
            "Tente novamente em alguns minutos",
            "Se o problema persistir, contate o suporte técnico",
            f"Informe o ID da requisição: {request_id}",
        ],
        request_id=request_id,
        processing_time_ms=processing_time_ms,
    )

    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(),
    )


def install_exception_handlers(app) -> None:
    """
    Install all exception handlers on FastAPI app.

    Registers global exception handlers for comprehensive
    error handling across the application.

    Args:
        app: FastAPI application instance
    """
    # Custom API exceptions
    app.add_exception_handler(BaseAPIException, base_api_exception_handler)
    app.add_exception_handler(ValidationError, base_api_exception_handler)
    app.add_exception_handler(ExtractionError, base_api_exception_handler)
    app.add_exception_handler(ServiceUnavailableError, base_api_exception_handler)
    app.add_exception_handler(TimeoutError, base_api_exception_handler)
    app.add_exception_handler(ConfigurationError, base_api_exception_handler)
    app.add_exception_handler(RateLimitError, base_api_exception_handler)

    # Standard FastAPI/Starlette exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PydanticValidationError, pydantic_validation_exception_handler)

    # System exceptions
    app.add_exception_handler(asyncio.TimeoutError, timeout_exception_handler)

    # Catch-all handler (must be last)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Global exception handlers installed successfully")


__all__ = [
    "install_exception_handlers",
    "get_request_id",
    "get_processing_time",
    "base_api_exception_handler",
    "http_exception_handler",
    "validation_exception_handler",
    "generic_exception_handler",
]
