"""Tests for health checking functionality."""

import pytest

from src.incident_extractor.infrastructure.health import HealthChecker, HealthCheckResult, HealthStatus


class TestHealthCheckResult:
    """Test HealthCheckResult functionality."""

    def test_health_check_result_creation(self) -> None:
        """Test creating a health check result."""
        from datetime import datetime

        result = HealthCheckResult(
            name="test_check",
            status=HealthStatus.HEALTHY,
            message="Test passed",
            duration_ms=100.5,
            timestamp=datetime.now(),
            metadata={"key": "value"},
        )

        assert result.name == "test_check"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Test passed"
        assert result.duration_ms == 100.5
        assert result.metadata == {"key": "value"}

    def test_health_check_result_to_dict(self) -> None:
        """Test converting health check result to dictionary."""
        from datetime import datetime

        timestamp = datetime.now()
        result = HealthCheckResult(
            name="test_check", status=HealthStatus.HEALTHY, message="Test passed", duration_ms=100.5, timestamp=timestamp
        )

        result_dict = result.to_dict()

        assert result_dict["name"] == "test_check"
        assert result_dict["status"] == "healthy"
        assert result_dict["message"] == "Test passed"
        assert result_dict["duration_ms"] == 100.5
        assert result_dict["timestamp"] == timestamp.isoformat()
        assert result_dict["metadata"] == {}


class TestHealthChecker:
    """Test HealthChecker functionality."""

    @pytest.fixture
    def health_checker(self) -> HealthChecker:
        """Create a health checker instance."""
        return HealthChecker(timeout_seconds=5.0)

    def test_initialization(self, health_checker: HealthChecker) -> None:
        """Test health checker initialization."""
        assert health_checker.timeout_seconds == 5.0

        # Should have default checks registered
        registered_checks = health_checker.get_registered_checks()
        assert "system_time" in registered_checks
        assert "memory_usage" in registered_checks

    async def test_system_time_check(self, health_checker: HealthChecker) -> None:
        """Test system time health check."""
        result = await health_checker.run_check("system_time")

        assert result.name == "system_time"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.UNHEALTHY]
        assert result.duration_ms >= 0
        assert "current_time" in result.metadata

    async def test_memory_usage_check(self, health_checker: HealthChecker) -> None:
        """Test memory usage health check."""
        result = await health_checker.run_check("memory_usage")

        assert result.name == "memory_usage"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY, HealthStatus.UNKNOWN]
        assert result.duration_ms >= 0

    def test_register_custom_check(self, health_checker: HealthChecker) -> None:
        """Test registering a custom health check."""

        async def custom_check() -> HealthCheckResult:
            from datetime import datetime

            return HealthCheckResult(
                name="custom_test",
                status=HealthStatus.HEALTHY,
                message="Custom check passed",
                duration_ms=50.0,
                timestamp=datetime.now(),
            )

        health_checker.register_check("custom_test", custom_check)

        registered_checks = health_checker.get_registered_checks()
        assert "custom_test" in registered_checks

    async def test_run_custom_check(self, health_checker: HealthChecker) -> None:
        """Test running a custom health check."""

        async def custom_check() -> HealthCheckResult:
            from datetime import datetime

            return HealthCheckResult(
                name="custom_test",
                status=HealthStatus.HEALTHY,
                message="Custom check passed",
                duration_ms=50.0,
                timestamp=datetime.now(),
            )

        health_checker.register_check("custom_test", custom_check)
        result = await health_checker.run_check("custom_test")

        assert result.name == "custom_test"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Custom check passed"

    async def test_run_nonexistent_check(self, health_checker: HealthChecker) -> None:
        """Test running a non-existent health check."""
        with pytest.raises(KeyError, match="Health check 'nonexistent' not registered"):
            await health_checker.run_check("nonexistent")

    async def test_run_all_checks(self, health_checker: HealthChecker) -> None:
        """Test running all health checks."""
        results = await health_checker.run_all_checks()

        assert isinstance(results, dict)
        assert "system_time" in results
        assert "memory_usage" in results

        for name, result in results.items():
            assert isinstance(result, HealthCheckResult)
            assert result.name == name

    async def test_get_overall_health(self, health_checker: HealthChecker) -> None:
        """Test getting overall health status."""
        overall_health = await health_checker.get_overall_health()

        assert "overall_status" in overall_health
        assert "timestamp" in overall_health
        assert "summary" in overall_health
        assert "checks" in overall_health

        summary = overall_health["summary"]
        assert "total_checks" in summary
        assert "healthy" in summary
        assert "unhealthy" in summary
        assert "degraded" in summary
        assert "health_percentage" in summary

    async def test_failing_check_timeout(self, health_checker: HealthChecker) -> None:
        """Test health check timeout handling."""

        async def slow_check() -> HealthCheckResult:
            import asyncio

            await asyncio.sleep(10)  # Longer than timeout
            from datetime import datetime

            return HealthCheckResult(
                name="slow_test",
                status=HealthStatus.HEALTHY,
                message="Should not reach here",
                duration_ms=1000.0,
                timestamp=datetime.now(),
            )

        health_checker.register_check("slow_test", slow_check)
        result = await health_checker.run_check("slow_test", use_cache=False)

        assert result.name == "slow_test"
        assert result.status == HealthStatus.UNHEALTHY
        assert "timed out" in result.message
        assert result.metadata.get("timeout") is True

    async def test_failing_check_exception(self, health_checker: HealthChecker) -> None:
        """Test health check exception handling."""

        async def failing_check() -> HealthCheckResult:
            raise ValueError("Test error")

        health_checker.register_check("failing_test", failing_check)
        result = await health_checker.run_check("failing_test", use_cache=False)

        assert result.name == "failing_test"
        assert result.status == HealthStatus.UNHEALTHY
        assert "Test error" in result.message
        assert result.metadata.get("error") == "Test error"

    def test_remove_check(self, health_checker: HealthChecker) -> None:
        """Test removing a health check."""

        # Register a custom check first
        async def custom_check() -> HealthCheckResult:
            from datetime import datetime

            return HealthCheckResult(
                name="removable_test", status=HealthStatus.HEALTHY, message="Test", duration_ms=10.0, timestamp=datetime.now()
            )

        health_checker.register_check("removable_test", custom_check)
        assert "removable_test" in health_checker.get_registered_checks()

        # Remove the check
        removed = health_checker.remove_check("removable_test")
        assert removed is True
        assert "removable_test" not in health_checker.get_registered_checks()

        # Try removing non-existent check
        removed = health_checker.remove_check("nonexistent")
        assert removed is False

    def test_clear_cache(self, health_checker: HealthChecker) -> None:
        """Test clearing health check cache."""
        # This should not raise an exception
        health_checker.clear_cache()

    def test_llm_health_check_registration(self, health_checker: HealthChecker) -> None:
        """Test LLM health check registration."""
        health_checker.register_llm_health_check(provider="test_provider", base_url="http://localhost:8000", api_key="test_key")

        registered_checks = health_checker.get_registered_checks()
        assert "llm_test_provider" in registered_checks
