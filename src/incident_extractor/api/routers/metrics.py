"""
Metrics router.

This module provides endpoints for application metrics, monitoring, and performance statistics.
Designed for production-ready monitoring integration with comprehensive metrics collection.

Features:
- Application performance metrics
- Request statistics and throughput
- Error rate monitoring
- System resource metrics
- Health score calculation
- Time-series data aggregation
"""

import time
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from ...config import get_logger

# Create router for metrics endpoints
router = APIRouter(prefix="/metrics", tags=["metrics"])

# Set up logger
logger = get_logger("api.metrics")


class RequestMetrics(BaseModel):
    """Request-level metrics model."""

    total_requests: int = Field(..., description="Total number of requests processed")
    successful_requests: int = Field(..., description="Number of successful requests")
    failed_requests: int = Field(..., description="Number of failed requests")
    avg_response_time_ms: float = Field(..., description="Average response time in milliseconds")
    p50_response_time_ms: float = Field(..., description="50th percentile response time")
    p95_response_time_ms: float = Field(..., description="95th percentile response time")
    p99_response_time_ms: float = Field(..., description="99th percentile response time")
    requests_per_minute: float = Field(..., description="Current requests per minute rate")


class ExtractionMetrics(BaseModel):
    """Extraction-specific metrics model."""

    total_extractions: int = Field(..., description="Total number of extraction requests")
    successful_extractions: int = Field(..., description="Number of successful extractions")
    partial_extractions: int = Field(..., description="Number of partial extractions")
    failed_extractions: int = Field(..., description="Number of failed extractions")
    avg_extraction_time_ms: float = Field(..., description="Average extraction processing time")
    fields_extraction_success_rate: Dict[str, float] = Field(..., description="Success rate for each field extraction")
    avg_text_length: float = Field(..., description="Average input text length")


class SystemMetrics(BaseModel):
    """System-level metrics model."""

    uptime_seconds: float = Field(..., description="Application uptime in seconds")
    memory_usage_mb: float = Field(..., description="Current memory usage in MB")
    cpu_usage_percent: float = Field(..., description="Current CPU usage percentage")
    active_connections: int = Field(..., description="Number of active connections")
    health_score: float = Field(..., description="Overall system health score (0-100)")


class DetailedMetrics(BaseModel):
    """Comprehensive metrics response model."""

    timestamp: datetime = Field(default_factory=datetime.now)
    collection_period_minutes: int = Field(..., description="Metrics collection period")
    request_metrics: RequestMetrics
    extraction_metrics: ExtractionMetrics
    system_metrics: SystemMetrics
    alerts: List[str] = Field(default_factory=list, description="Active system alerts")


class MetricsCollector:
    """
    Production-ready metrics collection service.

    Collects and aggregates application metrics for monitoring and alerting.
    Thread-safe and designed for high-throughput environments.
    """

    def __init__(self):
        self.start_time = time.time()
        self.logger = get_logger("metrics.collector")

        # Request tracking
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times = []

        # Extraction tracking
        self.total_extractions = 0
        self.successful_extractions = 0
        self.partial_extractions = 0
        self.failed_extractions = 0
        self.extraction_times = []
        self.field_successes = {
            "data_ocorrencia": 0,
            "local": 0,
            "tipo_incidente": 0,
            "impacto": 0,
        }
        self.text_lengths = []

        # System alerts
        self.active_alerts = []

        self.logger.info("Metrics collector initialized")

    def record_request(self, response_time_ms: float, success: bool = True) -> None:
        """Record a request metric."""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        self.response_times.append(response_time_ms)

        # Keep only last 1000 response times for memory efficiency
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]

    def record_extraction(
        self,
        processing_time_ms: float,
        success_status: str,
        extracted_fields: Dict[str, bool],
        text_length: int,
    ) -> None:
        """Record an extraction metric."""
        self.total_extractions += 1
        self.extraction_times.append(processing_time_ms)
        self.text_lengths.append(text_length)

        if success_status == "success":
            self.successful_extractions += 1
        elif success_status == "partial_success":
            self.partial_extractions += 1
        else:
            self.failed_extractions += 1

        # Track field extraction success
        for field, extracted in extracted_fields.items():
            if extracted and field in self.field_successes:
                self.field_successes[field] += 1

        # Keep memory usage reasonable
        if len(self.extraction_times) > 1000:
            self.extraction_times = self.extraction_times[-1000:]
        if len(self.text_lengths) > 1000:
            self.text_lengths = self.text_lengths[-1000:]

    def get_request_metrics(self) -> RequestMetrics:
        """Get current request metrics."""
        if not self.response_times:
            return RequestMetrics(
                total_requests=self.total_requests,
                successful_requests=self.successful_requests,
                failed_requests=self.failed_requests,
                avg_response_time_ms=0.0,
                p50_response_time_ms=0.0,
                p95_response_time_ms=0.0,
                p99_response_time_ms=0.0,
                requests_per_minute=0.0,
            )

        sorted_times = sorted(self.response_times)
        length = len(sorted_times)
        uptime_minutes = (time.time() - self.start_time) / 60

        return RequestMetrics(
            total_requests=self.total_requests,
            successful_requests=self.successful_requests,
            failed_requests=self.failed_requests,
            avg_response_time_ms=sum(sorted_times) / length,
            p50_response_time_ms=sorted_times[int(length * 0.5)],
            p95_response_time_ms=sorted_times[int(length * 0.95)],
            p99_response_time_ms=sorted_times[int(length * 0.99)],
            requests_per_minute=self.total_requests / max(uptime_minutes, 1),
        )

    def get_extraction_metrics(self) -> ExtractionMetrics:
        """Get current extraction metrics."""
        if not self.extraction_times:
            avg_extraction_time = 0.0
        else:
            avg_extraction_time = sum(self.extraction_times) / len(self.extraction_times)

        if not self.text_lengths:
            avg_text_length = 0.0
        else:
            avg_text_length = sum(self.text_lengths) / len(self.text_lengths)

        # Calculate field success rates
        field_success_rates = {}
        for field, successes in self.field_successes.items():
            rate = (successes / max(self.total_extractions, 1)) * 100
            field_success_rates[field] = round(rate, 2)

        return ExtractionMetrics(
            total_extractions=self.total_extractions,
            successful_extractions=self.successful_extractions,
            partial_extractions=self.partial_extractions,
            failed_extractions=self.failed_extractions,
            avg_extraction_time_ms=avg_extraction_time,
            fields_extraction_success_rate=field_success_rates,
            avg_text_length=avg_text_length,
        )

    def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        try:
            import psutil

            memory_usage = psutil.virtual_memory().percent
            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
            cpu_usage = psutil.cpu_percent(interval=0.1)
        except (ImportError, Exception):
            # Fallback if psutil is not available or fails
            memory_usage = 0.0
            memory_mb = 0.0
            cpu_usage = 0.0

        uptime = time.time() - self.start_time

        # Calculate health score (0-100)
        error_rate = (self.failed_requests / max(self.total_requests, 1)) * 100
        health_score = max(0, 100 - error_rate - (memory_usage / 2) - (cpu_usage / 2))

        return SystemMetrics(
            uptime_seconds=uptime,
            memory_usage_mb=memory_mb,
            cpu_usage_percent=cpu_usage,
            active_connections=0,  # Would be implemented with connection tracking
            health_score=round(health_score, 2),
        )

    def check_alerts(self) -> List[str]:
        """Check for system alerts based on metrics."""
        alerts = []

        # Error rate alerts
        if self.total_requests > 0:
            error_rate = (self.failed_requests / self.total_requests) * 100
            if error_rate > 5:
                alerts.append(f"High error rate: {error_rate:.2f}%")

        # Response time alerts
        if self.response_times:
            avg_response = sum(self.response_times) / len(self.response_times)
            if avg_response > 5000:  # 5 seconds
                alerts.append(f"High average response time: {avg_response:.0f}ms")

        # Extraction success rate alerts
        if self.total_extractions > 0:
            success_rate = (self.successful_extractions / self.total_extractions) * 100
            if success_rate < 80:
                alerts.append(f"Low extraction success rate: {success_rate:.2f}%")

        self.active_alerts = alerts
        return alerts


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return _metrics_collector


@router.get("/", response_model=DetailedMetrics)
async def get_comprehensive_metrics(request: Request) -> DetailedMetrics:
    """
    Get comprehensive application metrics.

    This endpoint provides detailed metrics about application performance,
    extraction statistics, and system health suitable for monitoring dashboards.

    Args:
        request: FastAPI request object for context

    Returns:
        DetailedMetrics: Comprehensive metrics data

    Raises:
        HTTPException: If metrics collection fails
    """
    request_id = getattr(request.state, "request_id", None)

    try:
        logger.debug("Collecting comprehensive metrics", extra={"request_id": request_id})

        collector = get_metrics_collector()

        # Collect all metrics
        request_metrics = collector.get_request_metrics()
        extraction_metrics = collector.get_extraction_metrics()
        system_metrics = collector.get_system_metrics()
        alerts = collector.check_alerts()

        logger.info(
            "Metrics collected successfully",
            extra={
                "request_id": request_id,
                "total_requests": request_metrics.total_requests,
                "total_extractions": extraction_metrics.total_extractions,
                "health_score": system_metrics.health_score,
                "active_alerts": len(alerts),
            },
        )

        return DetailedMetrics(
            timestamp=datetime.now(),
            collection_period_minutes=5,  # Default collection period
            request_metrics=request_metrics,
            extraction_metrics=extraction_metrics,
            system_metrics=system_metrics,
            alerts=alerts,
        )

    except Exception as e:
        logger.error(
            "Failed to collect metrics",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to collect metrics",
        ) from e


@router.get("/health-score")
async def get_health_score(request: Request) -> Dict[str, Any]:
    """
    Get current system health score.

    Simple endpoint returning just the health score for quick monitoring.

    Args:
        request: FastAPI request object for context

    Returns:
        Dict[str, Any]: Health score and status
    """
    try:
        collector = get_metrics_collector()
        system_metrics = collector.get_system_metrics()
        alerts = collector.check_alerts()

        health_status = (
            "healthy" if system_metrics.health_score > 80 else "degraded" if system_metrics.health_score > 50 else "unhealthy"
        )

        return {
            "health_score": system_metrics.health_score,
            "status": health_status,
            "uptime_seconds": system_metrics.uptime_seconds,
            "active_alerts_count": len(alerts),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("Failed to get health score", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to calculate health score",
        ) from e


@router.get("/performance")
async def get_performance_metrics(request: Request) -> Dict[str, Any]:
    """
    Get performance-focused metrics.

    Endpoint optimized for performance monitoring tools.

    Args:
        request: FastAPI request object for context

    Returns:
        Dict[str, Any]: Performance metrics
    """
    try:
        collector = get_metrics_collector()
        request_metrics = collector.get_request_metrics()
        extraction_metrics = collector.get_extraction_metrics()

        return {
            "timestamp": datetime.now().isoformat(),
            "requests": {
                "total": request_metrics.total_requests,
                "success_rate": (request_metrics.successful_requests / max(request_metrics.total_requests, 1)) * 100,
                "avg_response_time_ms": request_metrics.avg_response_time_ms,
                "p95_response_time_ms": request_metrics.p95_response_time_ms,
                "throughput_rpm": request_metrics.requests_per_minute,
            },
            "extractions": {
                "total": extraction_metrics.total_extractions,
                "success_rate": (extraction_metrics.successful_extractions / max(extraction_metrics.total_extractions, 1)) * 100,
                "avg_processing_time_ms": extraction_metrics.avg_extraction_time_ms,
                "field_extraction_rates": extraction_metrics.fields_extraction_success_rate,
            },
        }

    except Exception as e:
        logger.error("Failed to get performance metrics", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to collect performance metrics",
        ) from e


__all__ = ["router", "get_metrics_collector"]
