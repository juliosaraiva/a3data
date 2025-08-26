"""
CORS middleware configuration.

This module provides CORS (Cross-Origin Resource Sharing) middleware configuration
for the FastAPI application with production-ready settings and security considerations.

Features:
- Environment-specific CORS origins configuration
- Security-aware CORS headers
- Configurable CORS policies for different environments
- Integration with application settings
"""

import logging
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


class CORSConfiguration:
    """
    Production-ready CORS configuration.

    Provides environment-specific CORS settings with security considerations
    and proper configuration management.
    """

    def __init__(
        self,
        allowed_origins: Optional[list[str]] = None,
        allow_credentials: bool = True,
        allowed_methods: Optional[list[str]] = None,
        allowed_headers: Optional[list[str]] = None,
        expose_headers: Optional[list[str]] = None,
        max_age: int = 600,  # 10 minutes
        logger_name: str = "api.cors",
    ):
        """
        Initialize CORS configuration.

        Args:
            allowed_origins: List of allowed origins (defaults to environment settings)
            allow_credentials: Whether to allow credentials in CORS requests
            allowed_methods: List of allowed HTTP methods
            allowed_headers: List of allowed headers
            expose_headers: List of headers to expose to the client
            max_age: Max age for preflight requests in seconds
            logger_name: Name for the CORS logger
        """
        self.logger = logging.getLogger(logger_name)
        self.allowed_origins = allowed_origins or self._get_default_origins()
        self.allow_credentials = allow_credentials
        self.allowed_methods = allowed_methods or [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "OPTIONS",
            "HEAD",
            "PATCH",
        ]
        self.allowed_headers = allowed_headers or [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-Request-ID",
            "X-API-Key",
        ]
        self.expose_headers = expose_headers or [
            "X-Request-ID",
            "X-Processing-Time",
            "X-Response-Time",
            "X-Performance-Category",
        ]
        self.max_age = max_age

    def _get_default_origins(self) -> list[str]:
        """Get default CORS origins based on environment."""
        try:
            # Lazy import to avoid circular dependencies
            from ...config import get_settings

            settings = get_settings()
            return settings.cors_origins
        except Exception as e:
            self.logger.warning("Failed to get CORS origins from settings, using defaults", extra={"error": str(e)})
            # Safe defaults for development
            return [
                "http://localhost:3000",  # React dev server
                "http://localhost:8080",  # Vue dev server
                "http://localhost:5173",  # Vite dev server
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8080",
                "http://127.0.0.1:5173",
            ]

    def add_cors_middleware(self, app: FastAPI) -> None:
        """
        Add CORS middleware to FastAPI application.

        Args:
            app: The FastAPI application instance
        """
        self.logger.info(
            "Adding CORS middleware",
            extra={
                "allowed_origins": self.allowed_origins,
                "allow_credentials": self.allow_credentials,
                "allowed_methods": self.allowed_methods,
                "max_age": self.max_age,
            },
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.allowed_origins,
            allow_credentials=self.allow_credentials,
            allow_methods=self.allowed_methods,
            allow_headers=self.allowed_headers,
            expose_headers=self.expose_headers,
            max_age=self.max_age,
        )

        self.logger.info("CORS middleware added successfully")

    def validate_origin(self, origin: str) -> bool:
        """
        Validate if an origin is allowed.

        Args:
            origin: The origin to validate

        Returns:
            bool: True if origin is allowed, False otherwise
        """
        if "*" in self.allowed_origins:
            return True

        return origin in self.allowed_origins

    def get_cors_info(self) -> dict[str, str | list[str] | bool | int]:
        """Get CORS configuration information for debugging."""
        return {
            "allowed_origins": self.allowed_origins,
            "allow_credentials": self.allow_credentials,
            "allowed_methods": self.allowed_methods,
            "allowed_headers": self.allowed_headers,
            "expose_headers": self.expose_headers,
            "max_age": self.max_age,
        }


# Create default CORS configuration instance
default_cors_config = CORSConfiguration()


# Helper function for easy integration
def configure_cors(app: FastAPI, cors_config: Optional[CORSConfiguration] = None) -> None:
    """
    Configure CORS for FastAPI application.

    Args:
        app: The FastAPI application instance
        cors_config: Optional CORS configuration (uses default if None)
    """
    config = cors_config or default_cors_config
    config.add_cors_middleware(app)


__all__ = [
    "CORSMiddleware",
    "CORSConfiguration",
    "default_cors_config",
    "configure_cors",
]
