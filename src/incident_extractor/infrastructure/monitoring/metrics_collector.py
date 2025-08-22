"""Metrics collection service for monitoring incident extraction performance."""

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import structlog
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

logger = structlog.get_logger(__name__)


@dataclass
class MetricsConfig:
    """Configuration for metrics collection."""

    # Prometheus settings
    enable_prometheus: bool = True
    registry: CollectorRegistry | None = None
    metric_prefix: str = "incident_extractor"

    # Custom metrics settings
    track_response_times: bool = True
    track_error_rates: bool = True
    track_throughput: bool = True
    track_llm_usage: bool = True
    track_extraction_quality: bool = True

    # Retention settings
    metrics_retention_days: int = 7
    cleanup_interval_hours: int = 24


class MetricsCollector:
    """Prometheus-based metrics collector for incident extraction system."""

    def __init__(self, config: MetricsConfig | None = None) -> None:
        """Initialize metrics collector with configuration."""
        self.config = config or MetricsConfig()
        self.registry = self.config.registry or CollectorRegistry()

        # Initialize Prometheus metrics
        self._init_prometheus_metrics()

        # Internal tracking
        self._start_time = time.time()
        self._custom_metrics: dict[str, Any] = {}
        self._last_cleanup = datetime.now()

    def _init_prometheus_metrics(self) -> None:
        """Initialize Prometheus metrics."""
        prefix = self.config.metric_prefix

        # Request metrics
        self.requests_total = Counter(
            f"{prefix}_requests_total",
            "Total number of extraction requests",
            labelnames=["method", "status"],
            registry=self.registry,
        )

        self.request_duration = Histogram(
            f"{prefix}_request_duration_seconds",
            "Request processing time in seconds",
            labelnames=["method", "status"],
            registry=self.registry,
        )

        # LLM metrics
        self.llm_requests_total = Counter(
            f"{prefix}_llm_requests_total",
            "Total LLM requests by provider",
            labelnames=["provider", "model", "status"],
            registry=self.registry,
        )

        self.llm_request_duration = Histogram(
            f"{prefix}_llm_request_duration_seconds",
            "LLM request processing time",
            labelnames=["provider", "model"],
            registry=self.registry,
        )

        self.llm_tokens_used = Counter(
            f"{prefix}_llm_tokens_used_total",
            "Total tokens used by LLM provider",
            labelnames=["provider", "model", "type"],
            registry=self.registry,
        )

        # Extraction quality metrics
        self.extraction_confidence = Histogram(
            f"{prefix}_extraction_confidence_score",
            "Confidence score of extractions",
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry,
        )

        self.validation_score = Histogram(
            f"{prefix}_validation_score",
            "Validation quality score",
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry,
        )

        # System metrics
        self.active_processing_gauge = Gauge(
            f"{prefix}_active_processing_requests", "Number of currently processing requests", registry=self.registry
        )

        self.circuit_breaker_state = Gauge(
            f"{prefix}_circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=open, 2=half-open)",
            labelnames=["provider"],
            registry=self.registry,
        )

        # Error metrics
        self.errors_total = Counter(
            f"{prefix}_errors_total", "Total errors by type", labelnames=["error_type", "component"], registry=self.registry
        )

        logger.info("Prometheus metrics initialized", prefix=prefix)

    def record_request(self, method: str, status: str, duration_seconds: float) -> None:
        """Record API request metrics."""
        if not self.config.track_response_times:
            return

        self.requests_total.labels(method=method, status=status).inc()
        self.request_duration.labels(method=method, status=status).observe(duration_seconds)

        logger.debug("Request recorded", method=method, status=status, duration_seconds=duration_seconds)

    def record_llm_request(
        self,
        provider: str,
        model: str,
        status: str,
        duration_seconds: float,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> None:
        """Record LLM request metrics."""
        if not self.config.track_llm_usage:
            return

        self.llm_requests_total.labels(provider=provider, model=model, status=status).inc()

        self.llm_request_duration.labels(provider=provider, model=model).observe(duration_seconds)

        if input_tokens is not None:
            self.llm_tokens_used.labels(provider=provider, model=model, type="input").inc(input_tokens)

        if output_tokens is not None:
            self.llm_tokens_used.labels(provider=provider, model=model, type="output").inc(output_tokens)

        logger.debug(
            "LLM request recorded",
            provider=provider,
            model=model,
            status=status,
            duration_seconds=duration_seconds,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def record_extraction_quality(self, confidence_score: float, validation_score: float | None = None) -> None:
        """Record extraction quality metrics."""
        if not self.config.track_extraction_quality:
            return

        self.extraction_confidence.observe(confidence_score)

        if validation_score is not None:
            self.validation_score.observe(validation_score)

        logger.debug(
            "Extraction quality recorded",
            confidence_score=confidence_score,
            validation_score=validation_score,
        )

    def record_error(self, error_type: str, component: str) -> None:
        """Record error metrics."""
        if not self.config.track_error_rates:
            return

        self.errors_total.labels(error_type=error_type, component=component).inc()

        logger.debug("Error recorded", error_type=error_type, component=component)

    def increment_active_processing(self) -> None:
        """Increment active processing counter."""
        self.active_processing_gauge.inc()

    def decrement_active_processing(self) -> None:
        """Decrement active processing counter."""
        self.active_processing_gauge.dec()

    def set_circuit_breaker_state(self, provider: str, state: int) -> None:
        """Set circuit breaker state (0=closed, 1=open, 2=half-open)."""
        self.circuit_breaker_state.labels(provider=provider).set(state)

        logger.debug("Circuit breaker state updated", provider=provider, state=state)

    def record_custom_metric(self, name: str, value: int | float, labels: dict[str, str] | None = None) -> None:
        """Record custom metric value."""
        timestamp = datetime.now()

        if name not in self._custom_metrics:
            self._custom_metrics[name] = []

        self._custom_metrics[name].append(
            {
                "value": value,
                "labels": labels or {},
                "timestamp": timestamp,
            }
        )

        # Cleanup old metrics
        self._cleanup_custom_metrics()

        logger.debug("Custom metric recorded", name=name, value=value, labels=labels)

    def get_custom_metrics(self, name: str | None = None) -> dict[str, list[dict[str, Any]]]:
        """Get custom metrics data."""
        if name:
            return {name: self._custom_metrics.get(name, [])}
        return self._custom_metrics.copy()

    def _cleanup_custom_metrics(self) -> None:
        """Cleanup old custom metrics based on retention policy."""
        now = datetime.now()

        # Only cleanup if enough time has passed
        if (now - self._last_cleanup).seconds < self.config.cleanup_interval_hours * 3600:
            return

        cutoff_time = now - timedelta(days=self.config.metrics_retention_days)

        for name, metrics in self._custom_metrics.items():
            self._custom_metrics[name] = [metric for metric in metrics if metric["timestamp"] > cutoff_time]

        self._last_cleanup = now
        logger.debug("Custom metrics cleanup completed", cutoff_time=cutoff_time.isoformat())

    def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics in text format."""
        if not self.config.enable_prometheus:
            return ""

        return generate_latest(self.registry).decode("utf-8")

    def get_system_stats(self) -> dict[str, Any]:
        """Get system statistics and metrics summary."""
        uptime_seconds = time.time() - self._start_time

        return {
            "uptime_seconds": uptime_seconds,
            "uptime_human": str(timedelta(seconds=int(uptime_seconds))),
            "metrics_config": {
                "enable_prometheus": self.config.enable_prometheus,
                "track_response_times": self.config.track_response_times,
                "track_error_rates": self.config.track_error_rates,
                "track_throughput": self.config.track_throughput,
                "track_llm_usage": self.config.track_llm_usage,
                "track_extraction_quality": self.config.track_extraction_quality,
            },
            "custom_metrics_count": len(self._custom_metrics),
            "last_cleanup": self._last_cleanup.isoformat(),
        }

    def reset_metrics(self) -> None:
        """Reset all metrics (for testing purposes)."""
        # Clear custom metrics
        self._custom_metrics.clear()

        # Reset gauges
        self.active_processing_gauge.set(0)

        # Re-initialize registry (this clears counters and histograms)
        self.registry = CollectorRegistry()
        self._init_prometheus_metrics()

        logger.warning("All metrics have been reset")


class MetricsContext:
    """Context manager for tracking request metrics automatically."""

    def __init__(
        self,
        metrics_collector: MetricsCollector,
        method: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize metrics context."""
        self.metrics = metrics_collector
        self.method = method
        self.provider = provider
        self.model = model
        self.start_time = time.time()
        self.status = "success"
        self.input_tokens: int | None = None
        self.output_tokens: int | None = None

    def __enter__(self) -> "MetricsContext":
        """Enter context and start tracking."""
        self.metrics.increment_active_processing()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and record metrics."""
        duration = time.time() - self.start_time

        # Determine status from exception
        if exc_type is not None:
            self.status = "error"
            if hasattr(exc_val, "__class__"):
                error_type = exc_val.__class__.__name__
                component = self.provider or "api"
                self.metrics.record_error(error_type, component)

        # Record metrics
        self.metrics.record_request(self.method, self.status, duration)

        if self.provider and self.model:
            self.metrics.record_llm_request(
                self.provider,
                self.model,
                self.status,
                duration,
                self.input_tokens,
                self.output_tokens,
            )

        self.metrics.decrement_active_processing()

    def set_status(self, status: str) -> None:
        """Set the status for this request."""
        self.status = status

    def set_token_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Set token usage for LLM requests."""
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
