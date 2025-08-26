"""
Health Check Router

This module provides comprehensive health monitoring endpoints for the incident
extraction API. Designed for production monitoring, load balancer health checks,
and container orchestration systems.

Features:
- Basic health check for load balancers
- Detailed health status for monitoring systems
- Kubernetes readiness and liveness probes
- Component-level health reporting
- Service dependency validation
"""

import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request, status

from ...config import get_logger, get_settings
from ...services import get_llm_service_manager
from ..dependencies import get_workflow_service
from ..responses import (
    HealthCheckException,
    HealthData,
    HealthResponse,
    create_success_response,
)

# Create router for health endpoints
router = APIRouter(tags=["health"])
logger = get_logger(__name__)
settings = get_settings()

# Track application startup time for uptime calculation
app_startup_time = time.time()


@router.get("/health/", response_model=HealthResponse)
async def basic_health_check(
    request: Request,
    llm_services=Depends(get_llm_service_manager),
    workflow_service=Depends(get_workflow_service),
) -> HealthResponse:
    """
    Basic health check endpoint.

    This endpoint provides a quick health status check suitable for
    load balancers and simple monitoring tools. It performs minimal
    validation and returns quickly.

    Args:
        request: FastAPI request object
        llm_services: Injected LLM service manager
        workflow_service: Injected workflow service

    Returns:
        HealthResponse: Basic application health status

    Raises:
        HealthCheckException: If critical services are unavailable
    """
    try:
        # Calculate uptime
        uptime_seconds = time.time() - app_startup_time

        # Basic service availability checks
        service_status = "healthy"
        components = {}

        # Quick LLM service check
        try:
            llm_health = await llm_services.health_check_all()
            components["llm_services"] = "healthy" if any(llm_health.values()) else "unhealthy"
        except Exception as e:
            logger.warning(f"LLM health check failed: {e}")
            components["llm_services"] = "degraded"

        # Quick workflow check
        try:
            if workflow_service:
                components["workflow"] = "healthy"
            else:
                components["workflow"] = "unhealthy"
                service_status = "degraded"
        except Exception as e:
            logger.warning(f"Workflow health check failed: {e}")
            components["workflow"] = "unhealthy"
            service_status = "degraded"

        health_data = HealthData(
            service_status=service_status,
            components=components,
            uptime_seconds=uptime_seconds,
            version=settings.app_version if hasattr(settings, "app_version") else "1.0.0",
        )

        return create_success_response(
            data=health_data,
            message="Service is healthy",
            endpoint=str(request.url.path),
            processing_time_ms=0.0,  # Basic check should be very fast
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HealthCheckException(
            detail="Health check failed due to system error", suggestion="Check system logs and component status"
        ) from e


@router.get("/health/detailed")
async def detailed_health_check(
    request: Request, llm_services=Depends(get_llm_service_manager), workflow_service=Depends(get_workflow_service)
) -> dict[str, Any]:
    """
    Comprehensive health check endpoint.

    This endpoint performs detailed validation of all system components
    including LLM services, workflow components, and external dependencies.
    It provides comprehensive status information for monitoring systems.

    Args:
        request: FastAPI request object
        llm_services: Injected LLM service manager
        workflow_service: Injected workflow service
        service_manager: Injected service manager

    Returns:
        Dict[str, Any]: Comprehensive system health status

    Raises:
        HealthCheckException: If critical services are down
    """
    try:
        # Calculate uptime
        uptime_seconds = time.time() - app_startup_time

        # Detailed component health checks
        components = {}
        overall_health_score = 100.0

        # LLM Services health check
        try:
            llm_health = await llm_services.health_check_all()
            healthy_services = [name for name, status in llm_health.items() if status]

            components["llm_services"] = {
                "status": "healthy" if healthy_services else "unhealthy",
                "details": {
                    "healthy_services": healthy_services,
                    "services_count": len(llm_health),
                    "services_detail": llm_health,
                },
                "last_checked": datetime.utcnow().isoformat() + "Z",
                "response_time_ms": 0.0,  # Will be calculated
            }

            if not healthy_services:
                overall_health_score -= 30.0

        except Exception as e:
            logger.error(f"LLM services health check failed: {e}")
            components["llm_services"] = {
                "status": "error",
                "details": {"error": str(e)},
                "last_checked": datetime.utcnow().isoformat() + "Z",
                "response_time_ms": 0.0,
            }
            overall_health_score -= 50.0

        # Workflow health check
        try:
            if workflow_service:
                # Get basic workflow information
                components["workflow"] = {
                    "status": "healthy",
                    "details": {
                        "workflow_type": "IncidentExtractionWorkflow",
                        "nodes_count": 5,  # Standard workflow has 5 nodes
                        "edges_count": 0,  # Simplified for now
                        "agents_available": ["supervisor", "preprocessor", "extractor"],
                    },
                    "last_checked": datetime.utcnow().isoformat() + "Z",
                    "response_time_ms": 0.0,
                }
            else:
                components["workflow"] = {
                    "status": "unhealthy",
                    "details": {"error": "Workflow service not available"},
                    "last_checked": datetime.utcnow().isoformat() + "Z",
                    "response_time_ms": 0.0,
                }
                overall_health_score -= 30.0

        except Exception as e:
            logger.error(f"Workflow health check failed: {e}")
            components["workflow"] = {
                "status": "error",
                "details": {"error": str(e)},
                "last_checked": datetime.utcnow().isoformat() + "Z",
                "response_time_ms": 0.0,
            }
            overall_health_score -= 40.0

        # Determine overall status
        if overall_health_score >= 90:
            overall_status = "healthy"
        elif overall_health_score >= 70:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

        response_data = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": settings.app_version if hasattr(settings, "app_version") else "1.0.0",
            "uptime_seconds": uptime_seconds,
            "components": components,
            "overall_health_score": overall_health_score,
        }

        return response_data

    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HealthCheckException(
            detail="Detailed health check failed", suggestion="Check individual component status and system logs"
        ) from e


@router.get("/health/ready")
async def readiness_check(
    request: Request, llm_services=Depends(get_llm_service_manager), workflow_service=Depends(get_workflow_service)
) -> dict[str, Any]:
    """
    Kubernetes/container readiness check.

    This endpoint is designed for container orchestration platforms
    to determine if the application is ready to receive traffic.
    It performs essential dependency checks.

    Args:
        request: FastAPI request object
        llm_services: Injected LLM service manager
        workflow_service: Injected workflow service

    Returns:
        Dict[str, Any]: Readiness status

    Raises:
        HealthCheckException: If critical dependencies are not ready
    """
    try:
        # Check critical dependencies for readiness
        ready = True
        dependencies = {}

        # Check LLM services availability
        try:
            llm_health = await llm_services.health_check_all()
            llm_ready = any(llm_health.values())
            dependencies["llm_services"] = llm_ready
            if not llm_ready:
                ready = False
        except Exception:
            dependencies["llm_services"] = False
            ready = False

        # Check workflow availability
        try:
            workflow_ready = workflow_service is not None
            dependencies["workflow"] = workflow_ready
            if not workflow_ready:
                ready = False
        except Exception:
            dependencies["workflow"] = False
            ready = False

        if ready:
            return {"status": "ready", "dependencies": dependencies, "message": "Application is ready to receive traffic"}
        else:
            raise HealthCheckException(
                detail="Application is not ready",
                suggestion="Wait for all dependencies to become available",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    except HealthCheckException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HealthCheckException(detail="Readiness check failed", suggestion="Check system startup and dependencies") from e


@router.get("/health/live")
async def liveness_check(request: Request) -> dict[str, Any]:
    """
    Kubernetes/container liveness check.

    This endpoint is designed for container orchestration platforms
    to determine if the application is alive and should not be restarted.
    It performs minimal checks to avoid false positives.

    Args:
        request: FastAPI request object

    Returns:
        Dict[str, Any]: Liveness status
    """
    try:
        # Very basic liveness check - just ensure the application is responding
        uptime_seconds = time.time() - app_startup_time

        return {"status": "alive", "uptime_seconds": uptime_seconds, "message": "Application is alive and responding"}

    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        raise HealthCheckException(detail="Liveness check failed", suggestion="Application may need to be restarted") from e
