"""Logging middleware for request/response logging."""

import time
from typing import Any, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from structlog import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging.

    This middleware logs all HTTP requests and responses with structured data
    including request IDs, timing metrics, status codes, and error details.
    """

    def __init__(
        self,
        app,
        skip_paths: set[str] | None = None,
        log_request_body: bool = False,
        log_response_body: bool = False,
    ):
        """Initialize logging middleware.

        Args:
            app: FastAPI application instance
            skip_paths: Set of paths to skip logging (e.g., health checks)
            log_request_body: Whether to log request body content
            log_response_body: Whether to log response body content
        """
        super().__init__(app)
        self.skip_paths = skip_paths or {"/health", "/metrics"}
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details with timing.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware/endpoint in the chain

        Returns:
            Response from the endpoint handler
        """
        # Skip logging for specified paths
        if request.url.path in self.skip_paths:
            return await call_next(request)

        # Extract request information
        request_id = getattr(request.state, "request_id", "unknown")
        start_time = time.time()

        # Log request start
        request_info = await self._get_request_info(request)
        logger.info(
            "request_started",
            request_id=request_id,
            **request_info,
        )

        # Process request and capture response
        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Log successful response
            response_info = await self._get_response_info(response)
            logger.info(
                "request_completed",
                request_id=request_id,
                duration_ms=round(duration * 1000, 2),
                **response_info,
            )

            return response

        except Exception as exc:
            # Log failed request
            duration = time.time() - start_time
            logger.error(
                "request_failed",
                request_id=request_id,
                duration_ms=round(duration * 1000, 2),
                error=str(exc),
                error_type=exc.__class__.__name__,
            )
            raise

    async def _get_request_info(self, request: Request) -> dict[str, Any]:
        """Extract structured information from the request.

        Args:
            request: The HTTP request

        Returns:
            Dictionary of request information
        """
        info = {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": {key: value for key, value in request.headers.items() if key.lower() not in {"authorization", "cookie"}},
            "client_ip": request.client.host if request.client else None,
        }

        # Add request body if configured
        if self.log_request_body and request.method in {"POST", "PUT", "PATCH"}:
            try:
                body = await request.body()
                if body:
                    # Only log first 1000 characters to avoid log spam
                    info["body_preview"] = body.decode("utf-8")[:1000]
            except Exception:
                info["body_preview"] = "[Failed to decode body]"

        return info

    async def _get_response_info(self, response: Response) -> dict[str, Any]:
        """Extract structured information from the response.

        Args:
            response: The HTTP response

        Returns:
            Dictionary of response information
        """
        info = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
        }

        # Add response body if configured and not too large
        if self.log_response_body:
            try:
                # Note: This is a simplified example. In practice, you'd need
                # to handle streaming responses differently
                info["response_logged"] = True
            except Exception:
                info["response_logged"] = False

        return info
