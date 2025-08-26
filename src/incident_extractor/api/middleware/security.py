"""
Security middleware.

This module provides security headers and validation middleware for the FastAPI application.
Implements production-ready security features including security headers, request validation,
and rate limiting preparation.

Features:
- Security headers (HSTS, CSP, X-Frame-Options, etc.)
- Request size validation and limits
- Input sanitization and validation
- Rate limiting infrastructure preparation
- Security event logging
- Content type validation
"""

import logging
from typing import Optional

from fastapi import HTTPException, Request, Response, status


class SecurityMiddleware:
    """
    Production-ready security middleware.

    Provides comprehensive security features including security headers,
    request validation, and protection against common attacks.
    """

    def __init__(
        self,
        logger_name: str = "api.security",
        max_request_size: int = 10 * 1024 * 1024,  # 10MB
        max_header_size: int = 8192,  # 8KB
        enable_hsts: bool = True,
        hsts_max_age: int = 31536000,  # 1 year
        enable_csp: bool = True,
        allowed_origins: Optional[list[str]] = None,
        exclude_paths: Optional[list[str]] = None,
    ):
        """
        Initialize security middleware.

        Args:
            logger_name: Name for the security logger
            max_request_size: Maximum request body size in bytes
            max_header_size: Maximum header size in bytes
            enable_hsts: Whether to enable HSTS headers
            hsts_max_age: HSTS max-age in seconds
            enable_csp: Whether to enable Content Security Policy
            allowed_origins: List of allowed origins for CORS
            exclude_paths: Paths to exclude from security checks
        """
        self.logger = logging.getLogger(logger_name)
        self.max_request_size = max_request_size
        self.max_header_size = max_header_size
        self.enable_hsts = enable_hsts
        self.hsts_max_age = hsts_max_age
        self.enable_csp = enable_csp
        self.allowed_origins = allowed_origins or ["*"]
        self.exclude_paths = exclude_paths or ["/docs", "/openapi.json", "/redoc"]

    async def __call__(self, request: Request, call_next) -> Response:
        """
        Process requests with comprehensive security validation.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler

        Returns:
            Response: The HTTP response with security headers
        """
        # Get request ID for correlation
        request_id = getattr(request.state, "request_id", "unknown")

        try:
            # Skip security checks for excluded paths
            if not self._should_exclude_path(str(request.url.path)):
                # Validate request security
                await self._validate_request_security(request, request_id)

            # Process request
            response = await call_next(request)

            # Add security headers
            self._add_security_headers(response, request)

            return response

        except HTTPException:
            # Re-raise HTTP exceptions without logging (already handled by error middleware)
            raise
        except Exception as e:
            # Log security-related errors
            self.logger.error(
                "Security middleware error",
                extra={
                    "request_id": request_id,
                    "path": str(request.url.path),
                    "method": request.method,
                    "error": str(e),
                },
            )
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Security validation failed")

    async def _validate_request_security(self, request: Request, request_id: str) -> None:
        """Validate request against security policies."""
        # Validate request size
        await self._validate_request_size(request, request_id)

        # Validate headers
        await self._validate_headers(request, request_id)

        # Validate content type
        await self._validate_content_type(request, request_id)

        # Check for suspicious patterns
        await self._check_suspicious_patterns(request, request_id)

    async def _validate_request_size(self, request: Request, request_id: str) -> None:
        """Validate request body size limits."""
        content_length = request.headers.get("content-length")

        if content_length:
            try:
                size = int(content_length)
                if size > self.max_request_size:
                    self.logger.warning(
                        "Request size limit exceeded",
                        extra={
                            "request_id": request_id,
                            "path": str(request.url.path),
                            "method": request.method,
                            "content_length": size,
                            "max_allowed": self.max_request_size,
                        },
                    )
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Request body too large. Maximum size: {self.max_request_size} bytes",
                    )
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Content-Length header")

    async def _validate_headers(self, request: Request, request_id: str) -> None:
        """Validate request headers for security issues."""
        # Check total header size
        total_header_size = sum(len(key) + len(value) for key, value in request.headers.items())

        if total_header_size > self.max_header_size:
            self.logger.warning(
                "Header size limit exceeded",
                extra={
                    "request_id": request_id,
                    "path": str(request.url.path),
                    "method": request.method,
                    "header_size": total_header_size,
                    "max_allowed": self.max_header_size,
                },
            )
            raise HTTPException(status_code=status.HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE, detail="Request headers too large")

        # Check for suspicious headers
        suspicious_headers = [
            "x-forwarded-host",
            "x-original-url",
            "x-rewrite-url",
        ]

        for header in suspicious_headers:
            if header in request.headers:
                self.logger.info(
                    "Suspicious header detected",
                    extra={
                        "request_id": request_id,
                        "path": str(request.url.path),
                        "method": request.method,
                        "suspicious_header": header,
                        "header_value": request.headers[header][:100],  # Log first 100 chars
                    },
                )

    async def _validate_content_type(self, request: Request, request_id: str) -> None:
        """Validate content type for POST/PUT requests."""
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "").lower()

            # List of allowed content types
            allowed_types = [
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data",
                "text/plain",
            ]

            # Check if content type is allowed (considering charset parameters)
            if content_type and not any(content_type.startswith(allowed) for allowed in allowed_types):
                self.logger.warning(
                    "Unsupported content type",
                    extra={
                        "request_id": request_id,
                        "path": str(request.url.path),
                        "method": request.method,
                        "content_type": content_type,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"Unsupported content type: {content_type}"
                )

    async def _check_suspicious_patterns(self, request: Request, request_id: str) -> None:
        """Check for suspicious patterns in requests."""
        path = str(request.url.path).lower()

        # Check for common attack patterns
        suspicious_patterns = [
            "../",  # Path traversal
            "script>",  # XSS
            "union select",  # SQL injection
            "cmd.exe",  # Command injection
            "eval(",  # Code injection
        ]

        for pattern in suspicious_patterns:
            if pattern in path or pattern in str(request.url.query).lower():
                self.logger.warning(
                    "Suspicious pattern detected",
                    extra={
                        "request_id": request_id,
                        "path": path,
                        "method": request.method,
                        "pattern": pattern,
                        "query": str(request.url.query)[:200],  # Log first 200 chars
                    },
                )
                # Don't block automatically, just log for monitoring
                break

    def _add_security_headers(self, response: Response, request: Request) -> None:
        """Add comprehensive security headers to response."""
        # Basic security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Remove server information
        response.headers["Server"] = "FastAPI"

        # Add HSTS for HTTPS
        if self.enable_hsts and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = f"max-age={self.hsts_max_age}; includeSubDomains; preload"

        # Content Security Policy
        if self.enable_csp:
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https:; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
            response.headers["Content-Security-Policy"] = csp_policy

        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

    def _should_exclude_path(self, path: str) -> bool:
        """Check if path should be excluded from security checks."""
        return any(path.startswith(excluded) for excluded in self.exclude_paths)


class RateLimitingPreparation:
    """
    Preparation infrastructure for rate limiting.

    This class provides the foundation for implementing rate limiting
    in future versions of the application.
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize rate limiting preparation.

        Args:
            redis_url: Redis URL for distributed rate limiting (future use)
        """
        self.redis_url = redis_url
        self.logger = logging.getLogger("api.ratelimit")

    def prepare_rate_limiting(self) -> dict[str, str]:
        """Prepare rate limiting configuration."""
        return {
            "strategy": "token_bucket",
            "storage": "memory",  # Will be Redis in production
            "default_limit": "100/minute",
            "burst_limit": "200/minute",
        }

    def get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Check for authenticated user ID first
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"

        # Fall back to IP address
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"

        if request.client:
            return f"ip:{request.client.host}"

        return "unknown"


# Create middleware instance with production settings
security_middleware = SecurityMiddleware(
    max_request_size=10 * 1024 * 1024,  # 10MB
    max_header_size=8192,  # 8KB
    enable_hsts=True,
    enable_csp=True,
)

__all__ = [
    "SecurityMiddleware",
    "security_middleware",
    "RateLimitingPreparation",
]
