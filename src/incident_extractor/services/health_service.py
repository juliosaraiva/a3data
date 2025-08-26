"""
Comprehensive health checking service.

This module provides a production-ready health checking service that validates
component availability, service health, and overall system status.
"""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any

from ..config import get_settings
from ..config.logging import get_logger
from ..models.schemas import HealthStatus


class ComponentStatus(str, Enum):
    """Component health status enumeration."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class HealthCheckResult:
    """Result of a health check operation."""

    def __init__(self, status: ComponentStatus, details: dict[str, Any], response_time_ms: float = 0.0):
        self.status = status
        self.details = details
        self.response_time_ms = response_time_ms
        self.timestamp = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert health check result to dictionary."""
        return {
            "status": self.status.value,
            "details": self.details,
            "response_time_ms": self.response_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class HealthService:
    """
    Comprehensive health checking service.

    This service provides detailed health checking for all system components
    including LLM services, workflow validation, database connections, and
    external service dependencies.
    """

    def __init__(self) -> None:
        """Initialize the health service."""
        self._logger = get_logger("health.service")
        self._settings = get_settings()
        self._logger.info("Health service initialized")

    async def check_llm_services(self) -> HealthCheckResult:
        """
        Check health of LLM services.

        Returns:
            HealthCheckResult: Health status of LLM services
        """
        start_time = datetime.now()

        try:
            # Lazy import to avoid circular dependency
            from ..services.llm_service import get_llm_service_manager

            service_manager = await get_llm_service_manager()
            llm_health = await service_manager.health_check_all()

            # Calculate response time
            response_time = (datetime.now() - start_time).total_seconds() * 1000

            # Determine overall health status
            healthy_services = sum(1 for is_healthy in llm_health.values() if is_healthy)
            total_services = len(llm_health)

            if healthy_services == 0:
                status = ComponentStatus.UNHEALTHY
            elif healthy_services < total_services:
                status = ComponentStatus.DEGRADED
            else:
                status = ComponentStatus.HEALTHY

            details = {
                "services": llm_health,
                "healthy_count": healthy_services,
                "total_count": total_services,
                "availability_percentage": round((healthy_services / total_services) * 100, 2) if total_services > 0 else 0,
            }

            self._logger.debug(
                "LLM services health check completed",
                status=status.value,
                healthy_services=healthy_services,
                total_services=total_services,
            )

            return HealthCheckResult(status, details, response_time)

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self._logger.error("LLM services health check failed", error=str(e), exc_info=True)

            return HealthCheckResult(ComponentStatus.UNHEALTHY, {"error": str(e), "error_type": type(e).__name__}, response_time)

    async def check_workflow_service(self) -> HealthCheckResult:
        """
        Check health of workflow service.

        Returns:
            HealthCheckResult: Health status of workflow service
        """
        start_time = datetime.now()

        try:
            # Lazy import to avoid circular dependency
            from ..graph.workflow import get_workflow

            workflow = await get_workflow()
            workflow_validation = await workflow.validate_workflow()

            # Calculate response time
            response_time = (datetime.now() - start_time).total_seconds() * 1000

            # Determine workflow health
            all_valid = all(workflow_validation.values())
            status = ComponentStatus.HEALTHY if all_valid else ComponentStatus.UNHEALTHY

            details = {
                "validation_results": workflow_validation,
                "is_valid": all_valid,
                "workflow_info": workflow.get_workflow_info() if hasattr(workflow, "get_workflow_info") else {},
            }

            self._logger.debug("Workflow service health check completed", status=status.value, is_valid=all_valid)

            return HealthCheckResult(status, details, response_time)

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self._logger.error("Workflow service health check failed", error=str(e), exc_info=True)

            return HealthCheckResult(ComponentStatus.UNHEALTHY, {"error": str(e), "error_type": type(e).__name__}, response_time)

    async def check_configuration(self) -> HealthCheckResult:
        """
        Check application configuration health.

        Returns:
            HealthCheckResult: Health status of configuration
        """
        start_time = datetime.now()

        try:
            # Validate critical configuration settings
            config_issues = []

            # Check required settings
            if not self._settings.app_name:
                config_issues.append("Missing app_name configuration")

            if not self._settings.app_version:
                config_issues.append("Missing app_version configuration")

            if self._settings.api_port <= 0 or self._settings.api_port > 65535:
                config_issues.append(f"Invalid API port: {self._settings.api_port}")

            # Check LLM configuration
            if hasattr(self._settings, "ollama_model") and not self._settings.ollama_model:
                config_issues.append("Missing Ollama model configuration")

            response_time = (datetime.now() - start_time).total_seconds() * 1000

            status = ComponentStatus.HEALTHY if not config_issues else ComponentStatus.UNHEALTHY

            details = {
                "issues": config_issues,
                "environment": self._settings.environment,
                "debug_mode": self._settings.debug,
                "api_host": self._settings.api_host,
                "api_port": self._settings.api_port,
                "configuration_valid": len(config_issues) == 0,
            }

            return HealthCheckResult(status, details, response_time)

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self._logger.error("Configuration health check failed", error=str(e), exc_info=True)

            return HealthCheckResult(ComponentStatus.UNHEALTHY, {"error": str(e), "error_type": type(e).__name__}, response_time)

    async def check_metrics_service(self) -> HealthCheckResult:
        """
        Check metrics service health.

        Returns:
            HealthCheckResult: Health status of metrics service
        """
        start_time = datetime.now()

        try:
            from .metrics_service import get_metrics_service_async

            metrics_service = await get_metrics_service_async()
            metrics_health = await metrics_service.get_health_status()

            response_time = (datetime.now() - start_time).total_seconds() * 1000

            status = ComponentStatus.HEALTHY if metrics_health["status"] == "healthy" else ComponentStatus.UNHEALTHY

            return HealthCheckResult(status, metrics_health, response_time)

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self._logger.error("Metrics service health check failed", error=str(e), exc_info=True)

            return HealthCheckResult(ComponentStatus.UNHEALTHY, {"error": str(e), "error_type": type(e).__name__}, response_time)

    async def perform_comprehensive_health_check(self) -> HealthStatus:
        """
        Perform comprehensive health check of all system components.

        Returns:
            HealthStatus: Complete system health status
        """
        self._logger.info("Starting comprehensive health check")
        start_time = datetime.now()

        # Run all health checks concurrently
        health_checks = await asyncio.gather(
            self.check_llm_services(),
            self.check_workflow_service(),
            self.check_configuration(),
            self.check_metrics_service(),
            return_exceptions=True,
        )

        # Process results
        components = {}
        component_names = ["llm_services", "workflow_service", "configuration", "metrics_service"]

        overall_healthy = True
        total_response_time = 0.0

        for i, result in enumerate(health_checks):
            component_name = component_names[i]

            if isinstance(result, Exception):
                self._logger.error(f"Health check failed for {component_name}", error=str(result))
                components[component_name] = {
                    "status": ComponentStatus.UNHEALTHY.value,
                    "details": {"error": str(result), "error_type": type(result).__name__},
                    "response_time_ms": 0.0,
                }
                overall_healthy = False
            elif isinstance(result, HealthCheckResult):
                components[component_name] = result.to_dict()
                total_response_time += result.response_time_ms

                if result.status != ComponentStatus.HEALTHY:
                    overall_healthy = False
            else:
                # Fallback for unexpected result types
                self._logger.warning(f"Unexpected result type for {component_name}: {type(result)}")
                components[component_name] = {
                    "status": ComponentStatus.UNKNOWN.value,
                    "details": {"unexpected_result": str(result)},
                    "response_time_ms": 0.0,
                }
                overall_healthy = False

        # Calculate overall status
        overall_status = "healthy" if overall_healthy else "unhealthy"

        # Add summary information
        components["summary"] = {
            "status": overall_status,
            "total_response_time_ms": round(total_response_time, 2),
            "check_duration_ms": round((datetime.now() - start_time).total_seconds() * 1000, 2),
            "components_checked": len(component_names),
            "healthy_components": sum(
                1 for comp in components.values() if isinstance(comp, dict) and comp.get("status") == "healthy"
            ),
        }

        health_status = HealthStatus(
            status=overall_status, version=self._settings.app_version, components=components, timestamp=datetime.now()
        )

        self._logger.info(
            "Comprehensive health check completed",
            overall_status=overall_status,
            duration_ms=components["summary"]["check_duration_ms"],
        )

        return health_status

    async def get_quick_health_status(self) -> dict[str, str]:
        """
        Get quick health status without detailed checks.

        Returns:
            Dict[str, str]: Quick health status information
        """
        try:
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": self._settings.app_version,
                "environment": self._settings.environment,
            }
        except Exception as e:
            self._logger.error("Quick health check failed", error=str(e))
            return {"status": "unhealthy", "error": str(e), "timestamp": datetime.now().isoformat()}


# Global health service instance (singleton pattern)
_health_service_instance: HealthService | None = None


def get_health_service() -> HealthService:
    """
    Get the global health service instance (singleton).

    Returns:
        HealthService: The global health service instance
    """
    global _health_service_instance

    if _health_service_instance is None:
        _health_service_instance = HealthService()

    return _health_service_instance


async def get_health_service_async() -> HealthService:
    """
    Async wrapper for getting the health service.

    Returns:
        HealthService: The global health service instance
    """
    return get_health_service()
