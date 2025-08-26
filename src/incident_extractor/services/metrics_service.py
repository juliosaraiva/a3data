"""
Thread-safe metrics collection service.

This module provides a production-ready metrics collection service with
thread-safe operations, proper state management, and dependency injection support.
"""

import threading
from datetime import datetime
from typing import Any

from ..config.logging import get_logger
from ..models.schemas import ProcessingMetrics, ProcessingStatus


class MetricsService:
    """
    Thread-safe metrics collection and management service.

    This service manages application metrics with thread-safe operations,
    providing real-time statistics about API usage, performance, and errors.
    """

    def __init__(self) -> None:
        """Initialize the metrics service with thread-safe storage."""
        self._lock = threading.RLock()
        self._metrics = ProcessingMetrics()
        self._logger = get_logger("metrics.service")
        self._processing_times: list[float] = []
        self._max_processing_times_stored = 1000  # Keep last 1000 processing times

        self._logger.info("Metrics service initialized")

    def increment_total_requests(self) -> None:
        """Thread-safe increment of total requests counter."""
        with self._lock:
            self._metrics.total_requests += 1
            self._metrics.last_updated = datetime.now()

    def increment_successful_extractions(self) -> None:
        """Thread-safe increment of successful extractions counter."""
        with self._lock:
            self._metrics.successful_extractions += 1
            self._metrics.last_updated = datetime.now()

    def increment_failed_extractions(self) -> None:
        """Thread-safe increment of failed extractions counter."""
        with self._lock:
            self._metrics.failed_extractions += 1
            self._metrics.last_updated = datetime.now()

    def record_processing_time(self, processing_time: float) -> None:
        """
        Record processing time and update average.

        Args:
            processing_time: Processing time in seconds
        """
        with self._lock:
            # Add to processing times list
            self._processing_times.append(processing_time)

            # Keep only the most recent processing times
            if len(self._processing_times) > self._max_processing_times_stored:
                self._processing_times = self._processing_times[-self._max_processing_times_stored :]

            # Calculate new average
            self._metrics.average_processing_time = sum(self._processing_times) / len(self._processing_times)
            self._metrics.last_updated = datetime.now()

    def increment_supervisor_calls(self) -> None:
        """Thread-safe increment of supervisor agent calls."""
        with self._lock:
            self._metrics.supervisor_calls += 1
            self._metrics.last_updated = datetime.now()

    def increment_preprocessor_calls(self) -> None:
        """Thread-safe increment of preprocessor agent calls."""
        with self._lock:
            self._metrics.preprocessor_calls += 1
            self._metrics.last_updated = datetime.now()

    def increment_extractor_calls(self) -> None:
        """Thread-safe increment of extractor agent calls."""
        with self._lock:
            self._metrics.extractor_calls += 1
            self._metrics.last_updated = datetime.now()

    def increment_validation_errors(self) -> None:
        """Thread-safe increment of validation errors counter."""
        with self._lock:
            self._metrics.validation_errors += 1
            self._metrics.last_updated = datetime.now()

    def increment_llm_errors(self) -> None:
        """Thread-safe increment of LLM errors counter."""
        with self._lock:
            self._metrics.llm_errors += 1
            self._metrics.last_updated = datetime.now()

    def increment_timeout_errors(self) -> None:
        """Thread-safe increment of timeout errors counter."""
        with self._lock:
            self._metrics.timeout_errors += 1
            self._metrics.last_updated = datetime.now()

    def record_extraction_result(self, status: ProcessingStatus, processing_time: float) -> None:
        """
        Record extraction result with status and processing time.

        Args:
            status: The processing status of the extraction
            processing_time: Time taken to process the extraction in seconds
        """
        with self._lock:
            # Update status-specific counters
            if status == ProcessingStatus.SUCCESS:
                self.increment_successful_extractions()
            elif status in (ProcessingStatus.ERROR, ProcessingStatus.PARTIAL_SUCCESS):
                self.increment_failed_extractions()

            # Record processing time
            self.record_processing_time(processing_time)

            self._logger.debug("Recorded extraction result", status=status, processing_time=processing_time)

    def get_current_metrics(self) -> ProcessingMetrics:
        """
        Get current metrics snapshot.

        Returns:
            ProcessingMetrics: Current metrics data
        """
        with self._lock:
            # Create a copy to avoid race conditions
            return ProcessingMetrics(
                total_requests=self._metrics.total_requests,
                successful_extractions=self._metrics.successful_extractions,
                failed_extractions=self._metrics.failed_extractions,
                average_processing_time=self._metrics.average_processing_time,
                supervisor_calls=self._metrics.supervisor_calls,
                preprocessor_calls=self._metrics.preprocessor_calls,
                extractor_calls=self._metrics.extractor_calls,
                validation_errors=self._metrics.validation_errors,
                llm_errors=self._metrics.llm_errors,
                timeout_errors=self._metrics.timeout_errors,
                last_updated=self._metrics.last_updated,
            )

    def get_processing_statistics(self) -> dict[str, Any]:
        """
        Get detailed processing statistics.

        Returns:
            Dict[str, Any]: Detailed processing statistics
        """
        with self._lock:
            total_processed = self._metrics.successful_extractions + self._metrics.failed_extractions
            success_rate = (self._metrics.successful_extractions / total_processed * 100) if total_processed > 0 else 0.0

            processing_stats = {
                "success_rate_percent": round(success_rate, 2),
                "total_processed": total_processed,
                "error_rate_percent": round(100 - success_rate, 2),
                "average_processing_time_ms": round(self._metrics.average_processing_time * 1000, 2),
                "recent_processing_times_count": len(self._processing_times),
            }

            # Add percentile information if we have enough data
            if len(self._processing_times) >= 10:
                sorted_times = sorted(self._processing_times)
                processing_stats.update(
                    {
                        "p50_processing_time_ms": round(sorted_times[len(sorted_times) // 2] * 1000, 2),
                        "p95_processing_time_ms": round(sorted_times[int(len(sorted_times) * 0.95)] * 1000, 2),
                        "p99_processing_time_ms": round(sorted_times[int(len(sorted_times) * 0.99)] * 1000, 2),
                        "min_processing_time_ms": round(min(sorted_times) * 1000, 2),
                        "max_processing_time_ms": round(max(sorted_times) * 1000, 2),
                    }
                )

            return processing_stats

    def reset_metrics(self) -> None:
        """
        Reset all metrics to initial values.

        This method is primarily for testing and administrative purposes.
        """
        with self._lock:
            self._metrics = ProcessingMetrics()
            self._processing_times.clear()
            self._logger.info("All metrics reset to initial values")

    async def get_health_status(self) -> dict[str, Any]:
        """
        Get metrics service health status.

        Returns:
            Dict[str, Any]: Health status information
        """
        with self._lock:
            return {
                "status": "healthy",
                "metrics_count": len(self._processing_times),
                "last_updated": self._metrics.last_updated.isoformat(),
                "total_requests": self._metrics.total_requests,
                "uptime_info": "operational",
            }


# Global metrics service instance (singleton pattern)
_metrics_service_instance: MetricsService | None = None
_metrics_service_lock = threading.Lock()


def get_metrics_service() -> MetricsService:
    """
    Get the global metrics service instance (singleton).

    This function provides a thread-safe way to access the global
    metrics service instance, creating it if it doesn't exist.

    Returns:
        MetricsService: The global metrics service instance
    """
    global _metrics_service_instance

    if _metrics_service_instance is None:
        with _metrics_service_lock:
            # Double-check locking pattern
            if _metrics_service_instance is None:
                _metrics_service_instance = MetricsService()

    return _metrics_service_instance


async def get_metrics_service_async() -> MetricsService:
    """
    Async wrapper for getting the metrics service.

    Returns:
        MetricsService: The global metrics service instance
    """
    return get_metrics_service()
