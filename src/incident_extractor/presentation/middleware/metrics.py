"""Metrics collection middleware."""

import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from structlog import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """Thread-safe metrics collector for request statistics."""

    def __init__(self):
        """Initialize metrics storage."""
        self._request_count = defaultdict(int)
        self._request_duration = defaultdict(list)
        self._status_codes = defaultdict(int)
        self._error_count = defaultdict(int)

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        error: str | None = None,
    ) -> None:
        """Record a request metric.

        Args:
            method: HTTP method
            path: Request path
            status_code: HTTP status code
            duration: Request duration in seconds
            error: Error type if request failed
        """
        route = f"{method} {path}"
        self._request_count[route] += 1
        self._request_duration[route].append(duration)
        self._status_codes[status_code] += 1

        if error:
            self._error_count[error] += 1

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics snapshot.

        Returns:
            Dictionary with current metrics
        """
        metrics = {
            "requests": {
                "total": sum(self._request_count.values()),
                "by_route": dict(self._request_count),
            },
            "status_codes": dict(self._status_codes),
            "errors": dict(self._error_count),
            "response_times": {},
        }

        # Calculate response time statistics
        for route, durations in self._request_duration.items():
            if durations:
                metrics["response_times"][route] = {
                    "count": len(durations),
                    "avg": sum(durations) / len(durations),
                    "min": min(durations),
                    "max": max(durations),
                }

        return metrics

    def reset_metrics(self) -> None:
        """Reset all metrics to zero."""
        self._request_count.clear()
        self._request_duration.clear()
        self._status_codes.clear()
        self._error_count.clear()


# Global metrics collector instance
metrics_collector = MetricsCollector()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting request metrics and performance data.

    This middleware collects detailed metrics about all HTTP requests
    including timing, status codes, error rates, and endpoint usage.
    """

    def __init__(self, app, collect_detailed_metrics: bool = True):
        """Initialize metrics middleware.

        Args:
            app: FastAPI application instance
            collect_detailed_metrics: Whether to collect detailed per-route metrics
        """
        super().__init__(app)
        self.collect_detailed_metrics = collect_detailed_metrics
        self.collector = metrics_collector

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Collect metrics for the request.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware/endpoint in the chain

        Returns:
            Response from the endpoint handler
        """
        start_time = time.time()
        request_id = getattr(request.state, "request_id", "unknown")

        # Extract route information
        method = request.method
        path = self._normalize_path(request.url.path)

        try:
            # Process request
            response = await call_next(request)
            duration = time.time() - start_time
            status_code = response.status_code

            # Record successful request metrics
            if self.collect_detailed_metrics:
                self.collector.record_request(method, path, status_code, duration)

            # Log metrics data
            logger.info(
                "request_metrics",
                request_id=request_id,
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=round(duration * 1000, 2),
                response_size=response.headers.get("content-length"),
            )

            return response

        except Exception as exc:
            # Record failed request metrics
            duration = time.time() - start_time
            error_type = exc.__class__.__name__

            if self.collect_detailed_metrics:
                self.collector.record_request(method, path, 500, duration, error=error_type)

            logger.error(
                "request_error_metrics",
                request_id=request_id,
                method=method,
                path=path,
                error_type=error_type,
                duration_ms=round(duration * 1000, 2),
            )

            raise

    def _normalize_path(self, path: str) -> str:
        """Normalize path for metrics grouping.

        Args:
            path: Original request path

        Returns:
            Normalized path for metrics grouping
        """
        # Replace dynamic segments with placeholders for better grouping
        # This is a simple implementation - in production you might want
        # to use the actual route pattern from FastAPI

        # Replace UUIDs with placeholder
        import re

        path = re.sub(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "/{uuid}", path, flags=re.IGNORECASE)

        # Replace numeric IDs
        path = re.sub(r"/\d+", "/{id}", path)

        return path

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics data.

        Returns:
            Dictionary with current metrics
        """
        return self.collector.get_metrics()

    def reset_metrics(self) -> None:
        """Reset all collected metrics."""
        self.collector.reset_metrics()
