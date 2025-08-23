"""Health check API endpoints."""

import time
from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.incident_extractor.infrastructure.health.health_checker import HealthChecker, HealthStatus

# Create health router
router = APIRouter()


@router.get("/", status_code=status.HTTP_200_OK)
async def basic_health_check() -> dict[str, Any]:
    """Basic health check endpoint.

    Returns:
        Simple health status response
    """
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "incident-extractor-api",
        "version": "1.0.0",
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> JSONResponse:
    """Readiness check endpoint with dependency health verification.

    Checks if the service is ready to handle requests by verifying:
    - System resources availability
    - LLM provider connectivity
    - All registered health checks

    Returns:
        Detailed readiness status
    """
    try:
        # Create health checker instance for now
        # TODO: Use dependency injection when container is properly configured
        health_checker = HealthChecker()
        health_results = await health_checker.get_overall_health(use_cache=False)

        # Determine HTTP status based on overall health
        if health_results["overall_status"] == HealthStatus.HEALTHY.value:
            status_code = status.HTTP_200_OK
        elif health_results["overall_status"] == HealthStatus.DEGRADED.value:
            status_code = status.HTTP_200_OK  # Still ready but with warnings
        else:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return JSONResponse(
            status_code=status_code,
            content={
                "ready": health_results["overall_status"] in [HealthStatus.HEALTHY.value, HealthStatus.DEGRADED.value],
                "status": health_results["overall_status"],
                "timestamp": health_results["timestamp"],
                "service": "incident-extractor-api",
                "version": "1.0.0",
                "checks": health_results["checks"],
                "summary": health_results["summary"],
            },
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "ready": False,
                "status": "error",
                "timestamp": time.time(),
                "service": "incident-extractor-api",
                "version": "1.0.0",
                "error": str(e),
                "message": "Health check system failure",
            },
        )


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> dict[str, Any]:
    """Liveness check endpoint.

    Simple endpoint to verify the service is running.
    Used by container orchestration platforms like Kubernetes.

    Returns:
        Basic liveness confirmation
    """
    return {
        "alive": True,
        "status": "running",
        "timestamp": time.time(),
        "service": "incident-extractor-api",
        "version": "1.0.0",
        "uptime_seconds": time.time(),  # This would be more accurate with a start time
    }


@router.get("/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check() -> JSONResponse:
    """Comprehensive health check with detailed system information.

    Provides detailed health status including:
    - Individual component status
    - Performance metrics
    - Resource utilization
    - Dependency connectivity

    Returns:
        Detailed health report
    """
    try:
        # Create health checker instance for now
        # TODO: Use dependency injection when container is properly configured
        health_checker = HealthChecker()

        # Get comprehensive health status
        health_results = await health_checker.get_overall_health(use_cache=True)

        # Add additional system information
        system_info = {
            "service": "incident-extractor-api",
            "version": "1.0.0",
            "environment": "production",  # This should come from config
            "registered_checks": health_checker.get_registered_checks(),
        }

        # Combine health results with system info
        detailed_response = {
            **system_info,
            **health_results,
        }

        # Determine HTTP status
        if health_results["overall_status"] == HealthStatus.HEALTHY.value:
            status_code = status.HTTP_200_OK
        elif health_results["overall_status"] == HealthStatus.DEGRADED.value:
            status_code = status.HTTP_200_OK
        else:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return JSONResponse(status_code=status_code, content=detailed_response)

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "timestamp": time.time(),
                "service": "incident-extractor-api",
                "version": "1.0.0",
                "error": str(e),
                "message": "Detailed health check failed",
            },
        )


@router.post("/checks/{check_name}/run")
async def run_specific_health_check(check_name: str) -> JSONResponse:
    """Run a specific health check by name.

    Args:
        check_name: Name of the health check to run

    Returns:
        Result of the specific health check
    """
    try:
        # Create health checker instance for now
        # TODO: Use dependency injection when container is properly configured
        health_checker = HealthChecker()

        # Check if the health check exists
        registered_checks = health_checker.get_registered_checks()
        if check_name not in registered_checks:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": "Health check not found",
                    "check_name": check_name,
                    "available_checks": registered_checks,
                },
            )

        # Run the specific health check
        result = await health_checker.run_check(check_name, use_cache=False)

        # Determine status code based on health check result
        if result.status == HealthStatus.HEALTHY:
            status_code = status.HTTP_200_OK
        elif result.status == HealthStatus.DEGRADED:
            status_code = status.HTTP_200_OK
        else:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return JSONResponse(
            status_code=status_code,
            content={
                "check_name": check_name,
                "result": result.to_dict(),
                "timestamp": time.time(),
            },
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Health check execution failed",
                "check_name": check_name,
                "message": str(e),
                "timestamp": time.time(),
            },
        )
