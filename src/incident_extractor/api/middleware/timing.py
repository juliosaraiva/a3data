"""
Request timing middleware.

This module provides middleware for tracking request processing time and performance metrics.
Implements production-ready performance monitoring with detailed timing analysis and slow query detection.

Features:
- Request performance monitoring and tracking
- Response time measurement with high precision
- Performance metrics integration with metrics service
- Slow query detection and alerting
- Percentile-based performance analysis
- Request timing headers for client debugging
"""

import logging
import time
from datetime import datetime
from typing import Optional

from fastapi import Request, Response


class TimingMiddleware:
    """
    Production-ready request timing middleware.

    Provides comprehensive request performance monitoring with metrics collection,
    slow query detection, and performance analytics.
    """

    def __init__(
        self,
        logger_name: str = "api.timing",
        slow_request_threshold: float = 2.0,
        very_slow_request_threshold: float = 5.0,
        exclude_paths: Optional[list[str]] = None,
        add_timing_headers: bool = True,
    ):
        """
        Initialize timing middleware.

        Args:
            logger_name: Name for the timing logger
            slow_request_threshold: Threshold in seconds for slow request warnings
            very_slow_request_threshold: Threshold in seconds for very slow request errors
            exclude_paths: Paths to exclude from timing (e.g., health checks)
            add_timing_headers: Whether to add timing headers to responses
        """
        self.logger = logging.getLogger(logger_name)
        self.slow_request_threshold = slow_request_threshold
        self.very_slow_request_threshold = very_slow_request_threshold
        self.exclude_paths = exclude_paths or ["/health/", "/metrics/"]
        self.add_timing_headers = add_timing_headers

    async def __call__(self, request: Request, call_next) -> Response:
        """
        Process requests with comprehensive timing analysis.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler

        Returns:
            Response: The HTTP response with timing headers
        """
        # Skip timing for excluded paths
        if self._should_exclude_path(str(request.url.path)):
            return await call_next(request)

        # Get request ID for correlation
        request_id = getattr(request.state, "request_id", "unknown")

        # Record detailed timing information
        timing_data = await self._track_request_timing(request, call_next, request_id)

        # Process the response
        response = timing_data["response"]

        # Add timing headers if enabled
        if self.add_timing_headers:
            self._add_timing_headers(response, timing_data)

        # Update metrics service
        await self._update_metrics(timing_data)

        # Log performance information
        await self._log_performance(timing_data)

        return response

    async def _track_request_timing(self, request: Request, call_next, request_id: str) -> dict:
        """Track detailed request timing with multiple measurement points."""
        # Initialize timing data
        timing_data = {
            "request_id": request_id,
            "method": request.method,
            "path": str(request.url.path),
            "timestamp": datetime.now(),
            "start_time": time.perf_counter(),
            "start_process_time": time.process_time(),
            "response": None,
            "total_time": 0.0,
            "process_time": 0.0,
            "success": False,
            "status_code": 0,
            "error": None,
        }

        try:
            # Process request
            response = await call_next(request)

            # Record completion
            end_time = time.perf_counter()
            end_process_time = time.process_time()

            timing_data.update(
                {
                    "response": response,
                    "total_time": end_time - timing_data["start_time"],
                    "process_time": end_process_time - timing_data["start_process_time"],
                    "success": True,
                    "status_code": response.status_code,
                }
            )

        except Exception as e:
            # Record error timing
            end_time = time.perf_counter()
            end_process_time = time.process_time()

            timing_data.update(
                {
                    "total_time": end_time - timing_data["start_time"],
                    "process_time": end_process_time - timing_data["start_process_time"],
                    "success": False,
                    "error": str(e),
                }
            )
            raise

        return timing_data

    def _add_timing_headers(self, response: Response, timing_data: dict) -> None:
        """Add timing headers to response for client debugging."""
        # Add high-precision timing headers
        response.headers["X-Response-Time"] = f"{timing_data['total_time']:.4f}s"
        response.headers["X-Process-Time"] = f"{timing_data['process_time']:.4f}s"
        response.headers["X-Timestamp"] = timing_data["timestamp"].isoformat()

        # Add performance category
        category = self._categorize_performance(timing_data["total_time"])
        response.headers["X-Performance-Category"] = category

    async def _update_metrics(self, timing_data: dict) -> None:
        """Update metrics service with timing data."""
        try:
            # Lazy import to avoid circular dependencies
            from ...services.metrics_service import get_metrics_service

            metrics = get_metrics_service()

            # Update metrics with timing data
            if timing_data["success"]:
                metrics.record_processing_time(timing_data["total_time"])
                metrics.increment_successful_extractions()
            else:
                metrics.increment_failed_extractions()

        except Exception as e:
            self.logger.warning(
                "Failed to update metrics service",
                extra={
                    "request_id": timing_data["request_id"],
                    "error": str(e),
                },
            )

    async def _log_performance(self, timing_data: dict) -> None:
        """Log performance information with appropriate log levels."""
        total_time = timing_data["total_time"]
        log_level = self._get_log_level_for_timing(total_time)

        # Prepare performance context
        performance_context = {
            "request_id": timing_data["request_id"],
            "method": timing_data["method"],
            "path": timing_data["path"],
            "total_time": round(total_time, 4),
            "process_time": round(timing_data["process_time"], 4),
            "total_time_ms": round(total_time * 1000, 2),
            "process_time_ms": round(timing_data["process_time"] * 1000, 2),
            "success": timing_data["success"],
            "status_code": timing_data.get("status_code", 0),
            "performance_category": self._categorize_performance(total_time),
        }

        # Add error information if request failed
        if timing_data["error"]:
            performance_context["error"] = timing_data["error"]

        # Log with appropriate level based on performance
        log_message = self._get_log_message(total_time, timing_data["success"])

        self.logger.log(log_level, log_message, extra=performance_context)

    def _should_exclude_path(self, path: str) -> bool:
        """Check if path should be excluded from timing."""
        return any(path.startswith(excluded) for excluded in self.exclude_paths)

    def _categorize_performance(self, total_time: float) -> str:
        """Categorize request performance for monitoring."""
        if total_time >= self.very_slow_request_threshold:
            return "very_slow"
        elif total_time >= self.slow_request_threshold:
            return "slow"
        elif total_time >= 1.0:
            return "moderate"
        elif total_time >= 0.5:
            return "normal"
        else:
            return "fast"

    def _get_log_level_for_timing(self, total_time: float) -> int:
        """Determine appropriate log level based on request timing."""
        if total_time >= self.very_slow_request_threshold:
            return logging.ERROR
        elif total_time >= self.slow_request_threshold:
            return logging.WARNING
        else:
            return logging.INFO

    def _get_log_message(self, total_time: float, success: bool) -> str:
        """Generate appropriate log message based on performance."""
        status = "completed" if success else "failed"

        if total_time >= self.very_slow_request_threshold:
            return f"Very slow request {status}"
        elif total_time >= self.slow_request_threshold:
            return f"Slow request {status}"
        else:
            return f"Request {status}"


class PerformanceAnalyzer:
    """
    Helper class for advanced performance analysis.

    Provides utilities for performance tracking and analysis beyond basic timing.
    """

    @staticmethod
    def calculate_percentiles(timings: list[float]) -> dict[str, float]:
        """Calculate performance percentiles."""
        if not timings:
            return {}

        sorted_timings = sorted(timings)
        length = len(sorted_timings)

        return {
            "p50": sorted_timings[int(length * 0.5)],
            "p90": sorted_timings[int(length * 0.9)],
            "p95": sorted_timings[int(length * 0.95)],
            "p99": sorted_timings[int(length * 0.99)],
        }

    @staticmethod
    def detect_performance_regression(current_avg: float, historical_avg: float, threshold: float = 0.2) -> bool:
        """Detect if there's a performance regression."""
        if historical_avg == 0:
            return False

        regression_ratio = (current_avg - historical_avg) / historical_avg
        return regression_ratio > threshold


# Create middleware instance with production settings
timing_middleware = TimingMiddleware(
    slow_request_threshold=2.0,  # 2 seconds
    very_slow_request_threshold=5.0,  # 5 seconds
    add_timing_headers=True,
)

__all__ = [
    "TimingMiddleware",
    "timing_middleware",
    "PerformanceAnalyzer",
]
