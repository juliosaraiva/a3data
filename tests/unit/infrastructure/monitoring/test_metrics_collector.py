"""Tests for metrics collection functionality."""

import pytest

from src.incident_extractor.infrastructure.monitoring import MetricsCollector, MetricsConfig


class TestMetricsConfig:
    """Test MetricsConfig functionality."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = MetricsConfig()

        assert config.enable_prometheus is True
        assert config.metric_prefix == "incident_extractor"
        assert config.track_response_times is True
        assert config.track_error_rates is True
        assert config.track_throughput is True
        assert config.track_llm_usage is True
        assert config.track_extraction_quality is True


class TestMetricsCollector:
    """Test MetricsCollector functionality."""

    @pytest.fixture
    def collector(self) -> MetricsCollector:
        """Create a metrics collector with default config."""
        return MetricsCollector()

    def test_initialization(self, collector: MetricsCollector) -> None:
        """Test metrics collector initialization."""
        assert collector.config is not None
        assert collector.registry is not None
        assert hasattr(collector, "requests_total")
        assert hasattr(collector, "llm_requests_total")
        assert hasattr(collector, "extraction_confidence")

    def test_record_request(self, collector: MetricsCollector) -> None:
        """Test recording request metrics."""
        # This should not raise an exception
        collector.record_request("POST", "success", 0.5)
        collector.record_request("GET", "error", 1.2)

    def test_record_llm_request(self, collector: MetricsCollector) -> None:
        """Test recording LLM request metrics."""
        collector.record_llm_request(
            provider="openai", model="gpt-3.5-turbo", status="success", duration_seconds=1.5, input_tokens=100, output_tokens=50
        )

    def test_record_extraction_quality(self, collector: MetricsCollector) -> None:
        """Test recording extraction quality metrics."""
        collector.record_extraction_quality(0.85, 0.9)
        collector.record_extraction_quality(0.75)  # Without validation score

    def test_record_error(self, collector: MetricsCollector) -> None:
        """Test recording error metrics."""
        collector.record_error("validation_error", "application")
        collector.record_error("timeout_error", "llm_client")

    def test_active_processing_counter(self, collector: MetricsCollector) -> None:
        """Test active processing counter."""
        collector.increment_active_processing()
        collector.increment_active_processing()
        collector.decrement_active_processing()

    def test_circuit_breaker_state(self, collector: MetricsCollector) -> None:
        """Test circuit breaker state tracking."""
        collector.set_circuit_breaker_state("openai", 0)  # closed
        collector.set_circuit_breaker_state("ollama", 1)  # open
        collector.set_circuit_breaker_state("mock", 2)  # half-open

    def test_custom_metrics(self, collector: MetricsCollector) -> None:
        """Test custom metrics recording."""
        collector.record_custom_metric("test_metric", 42.0, {"label": "value"})
        collector.record_custom_metric("another_metric", 100)

        metrics = collector.get_custom_metrics("test_metric")
        assert "test_metric" in metrics
        assert len(metrics["test_metric"]) == 1
        assert metrics["test_metric"][0]["value"] == 42.0

    def test_system_stats(self, collector: MetricsCollector) -> None:
        """Test system statistics retrieval."""
        stats = collector.get_system_stats()

        assert "uptime_seconds" in stats
        assert "uptime_human" in stats
        assert "metrics_config" in stats
        assert "custom_metrics_count" in stats

    def test_prometheus_metrics_export(self, collector: MetricsCollector) -> None:
        """Test Prometheus metrics export."""
        # Record some metrics first
        collector.record_request("POST", "success", 0.5)

        metrics_output = collector.get_prometheus_metrics()
        assert isinstance(metrics_output, str)
        # Should contain our metric prefix
        if collector.config.enable_prometheus:
            assert "incident_extractor" in metrics_output

    def test_disabled_tracking(self) -> None:
        """Test behavior when tracking is disabled."""
        config = MetricsConfig(
            track_response_times=False, track_llm_usage=False, track_extraction_quality=False, track_error_rates=False
        )
        collector = MetricsCollector(config)

        # These should not raise exceptions even when disabled
        collector.record_request("POST", "success", 0.5)
        collector.record_llm_request("openai", "gpt-3.5", "success", 1.0)
        collector.record_extraction_quality(0.8)
        collector.record_error("test_error", "test_component")

    def test_reset_metrics(self, collector: MetricsCollector) -> None:
        """Test metrics reset functionality."""
        # Record some data first
        collector.record_request("POST", "success", 0.5)
        collector.record_custom_metric("test", 42.0)
        collector.increment_active_processing()

        # Reset all metrics
        collector.reset_metrics()

        # Custom metrics should be cleared
        metrics = collector.get_custom_metrics()
        assert len(metrics) == 0
