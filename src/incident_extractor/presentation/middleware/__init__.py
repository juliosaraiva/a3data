"""Middleware components for request/response processing."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ...core.config.config import Settings
from .auth import AuthenticationMiddleware
from .error_handler import ErrorHandlerMiddleware
from .logging import LoggingMiddleware
from .metrics import MetricsMiddleware
from .rate_limiting import RateLimitingMiddleware
from .request_id import RequestIDMiddleware


def setup_middleware(app: FastAPI, settings: Settings | None = None) -> None:
    """Configure all middleware for the FastAPI application.

    Middleware is executed in reverse order of addition, so we add them
    in the opposite order of desired execution.

    Args:
        app: FastAPI application instance
        settings: Application settings for middleware configuration
    """
    if settings is None:
        # Use default settings if none provided
        settings = Settings()

    # Global error handling (executed last)
    app.add_middleware(
        ErrorHandlerMiddleware,
        debug=settings.ENVIRONMENT.value != "production",
        include_traceback=settings.ENVIRONMENT.value == "development",
    )

    # Rate limiting
    app.add_middleware(
        RateLimitingMiddleware,
        enabled=settings.ENVIRONMENT.value == "production",
        default_requests_per_second=10.0,
        default_burst_capacity=20,
    )

    # Authentication and authorization
    app.add_middleware(
        AuthenticationMiddleware,
        enabled=settings.ENVIRONMENT.value == "production",
        secret_key="dev-secret-key",  # TODO: Add to settings
    )

    # Metrics collection
    app.add_middleware(
        MetricsMiddleware,
        collect_detailed_metrics=True,
    )

    # Request/response logging
    app.add_middleware(
        LoggingMiddleware,
        skip_paths={"/health", "/metrics"},
        log_request_body=settings.ENVIRONMENT.value == "development",
        log_response_body=False,
    )

    # Request ID generation (executed first)
    app.add_middleware(RequestIDMiddleware)

    # CORS configuration based on environment
    cors_origins = ["*"] if settings.ENVIRONMENT.value == "development" else []

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )


__all__ = [
    "setup_middleware",
    "AuthenticationMiddleware",
    "ErrorHandlerMiddleware",
    "LoggingMiddleware",
    "MetricsMiddleware",
    "RateLimitingMiddleware",
    "RequestIDMiddleware",
]
