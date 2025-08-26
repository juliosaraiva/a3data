"""
FastAPI dependencies module.

This module provides dependency injection functions for services, utilities,
and request processing components used throughout the FastAPI application.
"""

import time
from collections.abc import Generator

from fastapi import Depends

from ..graph.workflow import IncidentExtractionWorkflow, get_workflow
from ..services.llm_service import LLMServiceManager, get_llm_service_manager


def get_request_start_time() -> float:
    """
    Dependency to capture request start time.

    This dependency is used to measure request processing time
    and is typically injected at the beginning of endpoint handlers.

    Returns:
        float: Request start timestamp
    """
    return time.time()


async def get_llm_services() -> LLMServiceManager:
    """
    Dependency to inject LLM service manager.

    Provides access to the configured LLM services for the request lifecycle.
    The service manager handles connection pooling and health checking.

    Returns:
        LLMServiceManager: Configured LLM service manager instance
    """
    return await get_llm_service_manager()


async def get_workflow_service() -> IncidentExtractionWorkflow:
    """
    Dependency to inject workflow service.

    Provides access to the IncidentExtractionWorkflow for incident extraction processing.

    Returns:
        IncidentExtractionWorkflow: Configured workflow instance
    """
    return await get_workflow()


async def get_metrics_service():
    """
    Dependency to inject metrics service.

    Provides access to the thread-safe metrics collection service
    for tracking application performance and usage statistics.

    Returns:
        MetricsService: Global metrics service instance
    """
    from ..services.metrics_service import get_metrics_service_async

    return await get_metrics_service_async()


async def get_health_service():
    """
    Dependency to inject health service.

    Provides access to the comprehensive health checking service
    for monitoring system components and service availability.

    Returns:
        HealthService: Global health service instance
    """
    from ..services.health_service import get_health_service_async

    return await get_health_service_async()


def get_processing_timer() -> Generator[dict[str, float]]:
    """
    Dependency to provide request processing timing context.

    This dependency creates a timing context that can be used to measure
    different phases of request processing. It yields a dictionary with
    start time and can be updated with phase timings.

    Yields:
        dict[str, float]: Timing context with timestamps
    """
    start_time = time.time()
    timing_context = {"request_start": start_time, "current_time": start_time}

    yield timing_context

    # Can be extended to log final timing information
    end_time = time.time()
    timing_context["request_end"] = end_time
    timing_context["total_duration"] = end_time - start_time


def get_request_id() -> str:
    """
    Dependency to generate unique request identifier.

    Creates a unique request ID for tracking and logging purposes.
    This is a simple implementation that can be enhanced with
    UUID generation or correlation ID extraction from headers.

    Returns:
        str: Unique request identifier
    """
    return f"req_{int(time.time() * 1000000)}"


# Convenience dependency combinations
RequestTimer = Depends(get_request_start_time)
LLMServices = Depends(get_llm_services)
WorkflowService = Depends(get_workflow_service)
ProcessingTimer = Depends(get_processing_timer)
RequestID = Depends(get_request_id)
MetricsService = Depends(get_metrics_service)
HealthService = Depends(get_health_service)
