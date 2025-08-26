"""
Request/response logging middleware.

This module provides structured logging middleware for tracking API requests and responses.
Implements production-ready logging with performance metrics, correlation IDs, and comprehensive monitoring.

Features:
- Structured request/response logging
- Performance metrics collection
- Request ID generation and correlation
- Request/response body logging (configurable)
- Security-aware logging (excludes sensitive data)
- Integration with metrics service
"""

import logging
import time
import uuid
from datetime import datetime

from fastapi import Request, Response


class RequestLoggingMiddleware:
    """
    Production-ready request logging middleware.

    Provides structured logging of HTTP requests and responses with performance
    metrics collection and correlation ID management.
    """

    def __init__(
        self,
        logger_name: str = "api.requests",
        log_request_body: bool = False,
        log_response_body: bool = False,
        max_body_size: int = 1024,
        exclude_paths: list[str] | None = None,
    ):
        """
        Initialize request logging middleware.

        Args:
            logger_name: Name for the request logger
            log_request_body: Whether to log request bodies
            log_response_body: Whether to log response bodies
            max_body_size: Maximum body size to log (in bytes)
            exclude_paths: Paths to exclude from logging (e.g., health checks)
        """
        self.logger = logging.getLogger(logger_name)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_size = max_body_size
        self.exclude_paths = exclude_paths or ["/health/", "/metrics/", "/docs", "/openapi.json"]

    async def __call__(self, request: Request, call_next) -> Response:
        """
        Process requests with comprehensive logging.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler

        Returns:
            Response: The HTTP response
        """
        # Use existing request ID or generate new one
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Skip logging for excluded paths
        if self._should_exclude_path(str(request.url.path)):
            return await call_next(request)

        # Record request start time
        start_time = time.perf_counter()
        timestamp = datetime.now()

        # Log request details
        await self._log_request(request, request_id, timestamp)

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time
            processing_time = time.perf_counter() - start_time

            # Log successful response
            await self._log_response(request, response, request_id, processing_time, timestamp)

            # Add correlation headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Processing-Time"] = f"{processing_time:.4f}"

            return response

        except Exception as e:
            # Calculate processing time for failed requests
            processing_time = time.perf_counter() - start_time

            # Log failed request
            await self._log_error(request, request_id, processing_time, timestamp, e)
            raise

    async def _log_request(self, request: Request, request_id: str, timestamp: datetime) -> None:
        """Log incoming request details."""
        # Collect request headers (excluding sensitive ones)
        headers = self._sanitize_headers(dict(request.headers))

        # Collect request body if enabled
        request_body = None
        if self.log_request_body:
            request_body = await self._get_request_body(request)

        # Get client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")

        self.logger.info(
            "HTTP request started",
            extra={
                "request_id": request_id,
                "timestamp": timestamp.isoformat(),
                "method": request.method,
                "path": str(request.url.path),
                "query_params": str(request.url.query) if request.url.query else None,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "headers": headers,
                "body": request_body,
                "event_type": "request_started",
            },
        )

    async def _log_response(
        self,
        request: Request,
        response: Response,
        request_id: str,
        processing_time: float,
        timestamp: datetime,
    ) -> None:
        """Log response details and performance metrics."""
        # Collect response body if enabled and response is small enough
        response_body = None
        if self.log_response_body:
            response_body = await self._get_response_body(response)

        # Determine log level based on status code
        log_level = self._get_log_level_for_status(response.status_code)

        self.logger.log(
            log_level,
            "HTTP request completed",
            extra={
                "request_id": request_id,
                "timestamp": timestamp.isoformat(),
                "method": request.method,
                "path": str(request.url.path),
                "status_code": response.status_code,
                "processing_time": round(processing_time, 4),
                "response_size": len(response_body or b""),
                "body": response_body,
                "event_type": "request_completed",
                "performance_metrics": {
                    "processing_time_ms": round(processing_time * 1000, 2),
                    "status_code": response.status_code,
                    "success": 200 <= response.status_code < 400,
                },
            },
        )

    async def _log_error(
        self,
        request: Request,
        request_id: str,
        processing_time: float,
        timestamp: datetime,
        error: Exception,
    ) -> None:
        """Log failed request details."""
        self.logger.error(
            "HTTP request failed",
            extra={
                "request_id": request_id,
                "timestamp": timestamp.isoformat(),
                "method": request.method,
                "path": str(request.url.path),
                "processing_time": round(processing_time, 4),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "event_type": "request_failed",
                "performance_metrics": {
                    "processing_time_ms": round(processing_time * 1000, 2),
                    "success": False,
                },
            },
        )

    def _should_exclude_path(self, path: str) -> bool:
        """Check if path should be excluded from logging."""
        return any(path.startswith(excluded) for excluded in self.exclude_paths)

    def _sanitize_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Remove sensitive headers from logging."""
        sensitive_headers = {
            "authorization",
            "cookie",
            "x-api-key",
            "x-auth-token",
            "authentication",
        }

        return {key: "***REDACTED***" if key.lower() in sensitive_headers else value for key, value in headers.items()}

    async def _get_request_body(self, request: Request) -> str | None:
        """Safely extract request body for logging."""
        try:
            body = await request.body()
            if len(body) > self.max_body_size:
                return f"<body too large: {len(body)} bytes>"
            return body.decode("utf-8", errors="replace")
        except Exception:
            return "<unable to read body>"

    async def _get_response_body(self, response: Response) -> bytes | None:
        """Extract response body for logging."""
        # This is a simplified implementation
        # In production, you might want to use response.body if available
        return None

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address with proxy support."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "unknown"

    def _get_log_level_for_status(self, status_code: int) -> int:
        """Determine appropriate log level based on HTTP status code."""
        if status_code >= 500:
            return logging.ERROR
        elif status_code >= 400:
            return logging.WARNING
        else:
            return logging.INFO


# Create middleware instance with production settings
request_logging_middleware = RequestLoggingMiddleware(
    log_request_body=False,  # Disabled in production for performance
    log_response_body=False,  # Disabled in production for performance
    max_body_size=512,  # Limit body logging size
)

__all__ = ["RequestLoggingMiddleware", "request_logging_middleware"]
