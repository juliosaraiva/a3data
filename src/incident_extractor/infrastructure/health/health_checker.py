"""Health checking service for incident extraction system."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class HealthStatus(str, Enum):
    """Health check status enumeration."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    name: str
    status: HealthStatus
    message: str
    duration_ms: float
    timestamp: datetime
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {},
        }


class HealthChecker:
    """Comprehensive health checking service for all system components."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        """Initialize health checker."""
        self.timeout_seconds = timeout_seconds
        self._checks: dict[str, Callable[[], Awaitable[HealthCheckResult]]] = {}
        self._cached_results: dict[str, HealthCheckResult] = {}
        self._cache_duration = timedelta(seconds=30)

        # Register default health checks
        self._register_default_checks()

    def _register_default_checks(self) -> None:
        """Register default system health checks."""
        self.register_check("system_time", self._check_system_time)
        self.register_check("memory_usage", self._check_memory_usage)

    def register_check(self, name: str, check_func: Callable[[], Awaitable[HealthCheckResult]]) -> None:
        """Register a health check function.

        Args:
            name: Unique name for the health check
            check_func: Async function that returns HealthCheckResult
        """
        self._checks[name] = check_func
        logger.info("Health check registered", name=name)

    async def run_check(self, name: str, use_cache: bool = True) -> HealthCheckResult:
        """Run a specific health check.

        Args:
            name: Name of the health check to run
            use_cache: Whether to use cached results if available

        Returns:
            HealthCheckResult with status and details

        Raises:
            KeyError: If health check is not registered
        """
        if name not in self._checks:
            raise KeyError(f"Health check '{name}' not registered")

        # Check cache first
        if use_cache and name in self._cached_results:
            cached_result = self._cached_results[name]
            if datetime.now() - cached_result.timestamp < self._cache_duration:
                return cached_result

        # Run the health check with timeout
        try:
            result = await asyncio.wait_for(self._checks[name](), timeout=self.timeout_seconds)

            # Cache the result
            self._cached_results[name] = result
            return result

        except TimeoutError:
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout_seconds}s",
                duration_ms=self.timeout_seconds * 1000,
                timestamp=datetime.now(),
                metadata={"timeout": True},
            )
            self._cached_results[name] = result
            return result

        except Exception as e:
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {e}",
                duration_ms=0.0,
                timestamp=datetime.now(),
                metadata={"error": str(e), "exception_type": type(e).__name__},
            )
            self._cached_results[name] = result
            return result

    async def run_all_checks(self, use_cache: bool = True) -> dict[str, HealthCheckResult]:
        """Run all registered health checks concurrently.

        Args:
            use_cache: Whether to use cached results if available

        Returns:
            Dictionary mapping check names to results
        """
        # Run all checks concurrently
        tasks = [self.run_check(name, use_cache) for name in self._checks]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        check_results = {}
        for check_name, result in zip(self._checks.keys(), results, strict=False):
            if isinstance(result, Exception):
                check_results[check_name] = HealthCheckResult(
                    name=check_name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check execution failed: {result}",
                    duration_ms=0.0,
                    timestamp=datetime.now(),
                    metadata={"error": str(result)},
                )
            else:
                check_results[check_name] = result

        return check_results

    async def get_overall_health(self, use_cache: bool = True) -> dict[str, Any]:
        """Get overall system health status.

        Args:
            use_cache: Whether to use cached results

        Returns:
            Overall health summary with individual check results
        """
        results = await self.run_all_checks(use_cache)

        # Determine overall status
        statuses = [result.status for result in results.values()]

        if all(status == HealthStatus.HEALTHY for status in statuses):
            overall_status = HealthStatus.HEALTHY
        elif any(status == HealthStatus.UNHEALTHY for status in statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.UNKNOWN

        # Calculate summary statistics
        total_checks = len(results)
        healthy_checks = sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY)
        unhealthy_checks = sum(1 for r in results.values() if r.status == HealthStatus.UNHEALTHY)
        degraded_checks = sum(1 for r in results.values() if r.status == HealthStatus.DEGRADED)

        return {
            "overall_status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_checks": total_checks,
                "healthy": healthy_checks,
                "unhealthy": unhealthy_checks,
                "degraded": degraded_checks,
                "health_percentage": (healthy_checks / total_checks * 100) if total_checks > 0 else 0,
            },
            "checks": {name: result.to_dict() for name, result in results.items()},
        }

    def register_llm_health_check(self, provider: str, base_url: str, api_key: str | None = None) -> None:
        """Register health check for LLM provider.

        Args:
            provider: Name of the LLM provider (e.g., 'openai', 'ollama')
            base_url: Base URL for the LLM service
            api_key: API key if required
        """

        async def check_llm_health() -> HealthCheckResult:
            start_time = time.time()
            check_name = f"llm_{provider}"

            try:
                async with httpx.AsyncClient() as client:
                    headers = {}
                    if api_key:
                        headers["Authorization"] = f"Bearer {api_key}"

                    # Try to make a simple health check request
                    if provider == "openai":
                        response = await client.get(f"{base_url}/models", headers=headers, timeout=10.0)
                    elif provider == "ollama":
                        response = await client.get(f"{base_url}/api/tags", timeout=10.0)
                    else:
                        # Generic health check
                        response = await client.get(f"{base_url}/health", headers=headers, timeout=10.0)

                    duration_ms = (time.time() - start_time) * 1000

                    if response.status_code == 200:
                        return HealthCheckResult(
                            name=check_name,
                            status=HealthStatus.HEALTHY,
                            message=f"LLM {provider} is responding",
                            duration_ms=duration_ms,
                            timestamp=datetime.now(),
                            metadata={"status_code": response.status_code, "provider": provider, "base_url": base_url},
                        )
                    else:
                        return HealthCheckResult(
                            name=check_name,
                            status=HealthStatus.DEGRADED,
                            message=f"LLM {provider} returned status {response.status_code}",
                            duration_ms=duration_ms,
                            timestamp=datetime.now(),
                            metadata={"status_code": response.status_code, "provider": provider, "base_url": base_url},
                        )

            except httpx.TimeoutException:
                return HealthCheckResult(
                    name=check_name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"LLM {provider} health check timed out",
                    duration_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.now(),
                    metadata={"provider": provider, "base_url": base_url, "timeout": True},
                )

            except Exception as e:
                return HealthCheckResult(
                    name=check_name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"LLM {provider} health check failed: {e}",
                    duration_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.now(),
                    metadata={"provider": provider, "base_url": base_url, "error": str(e), "exception_type": type(e).__name__},
                )

        self.register_check(f"llm_{provider}", check_llm_health)

    async def _check_system_time(self) -> HealthCheckResult:
        """Check system time health."""
        start_time = time.time()

        try:
            current_time = datetime.now()

            # Basic sanity check - time should be reasonable
            year = current_time.year
            if year < 2023 or year > 2030:
                return HealthCheckResult(
                    name="system_time",
                    status=HealthStatus.UNHEALTHY,
                    message=f"System time appears incorrect: {current_time.isoformat()}",
                    duration_ms=(time.time() - start_time) * 1000,
                    timestamp=current_time,
                    metadata={"current_time": current_time.isoformat()},
                )

            return HealthCheckResult(
                name="system_time",
                status=HealthStatus.HEALTHY,
                message="System time is normal",
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=current_time,
                metadata={"current_time": current_time.isoformat()},
            )

        except Exception as e:
            return HealthCheckResult(
                name="system_time",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check system time: {e}",
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                metadata={"error": str(e)},
            )

    async def _check_memory_usage(self) -> HealthCheckResult:
        """Check system memory usage."""
        start_time = time.time()

        try:
            import psutil

            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            if memory_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"High memory usage: {memory_percent:.1f}%"
            elif memory_percent > 75:
                status = HealthStatus.DEGRADED
                message = f"Elevated memory usage: {memory_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage normal: {memory_percent:.1f}%"

            return HealthCheckResult(
                name="memory_usage",
                status=status,
                message=message,
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                metadata={
                    "memory_percent": memory_percent,
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                },
            )

        except ImportError:
            # psutil not available
            return HealthCheckResult(
                name="memory_usage",
                status=HealthStatus.UNKNOWN,
                message="Memory monitoring not available (psutil not installed)",
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                metadata={"psutil_available": False},
            )

        except Exception as e:
            return HealthCheckResult(
                name="memory_usage",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check memory usage: {e}",
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                metadata={"error": str(e)},
            )

    def get_registered_checks(self) -> list[str]:
        """Get list of registered health check names."""
        return list(self._checks.keys())

    def clear_cache(self) -> None:
        """Clear all cached health check results."""
        self._cached_results.clear()
        logger.info("Health check cache cleared")

    def remove_check(self, name: str) -> bool:
        """Remove a registered health check.

        Args:
            name: Name of the health check to remove

        Returns:
            True if check was removed, False if it didn't exist
        """
        if name in self._checks:
            del self._checks[name]
            if name in self._cached_results:
                del self._cached_results[name]
            logger.info("Health check removed", name=name)
            return True
        return False
