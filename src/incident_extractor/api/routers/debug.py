"""
Debug router.

This module provides debug and diagnostic endpoints for development and troubleshooting.
Designed for production-safe debugging with configurable information exposure levels.

Features:
- System configuration inspection
- Workflow diagnostics and visualization
- Component status checking
- Environment variable inspection (sanitized)
- Agent state debugging
- Performance profiling information
- Development-only endpoints (when debug mode enabled)
"""

import os
import platform
import sys
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from ...config import get_logger, get_settings
from ...graph.workflow import get_workflow
from ...models.schemas import ExtractionRequest
from ...services import get_llm_service_manager

# Create router for debug endpoints
router = APIRouter(prefix="/debug", tags=["debug"])

# Set up logger
logger = get_logger("api.debug")


class SystemInfo(BaseModel):
    """System information model for debugging."""

    python_version: str = Field(..., description="Python version")
    platform: str = Field(..., description="Operating system platform")
    architecture: str = Field(..., description="System architecture")
    hostname: str = Field(..., description="System hostname")
    current_working_directory: str = Field(..., description="Current working directory")
    process_id: int = Field(..., description="Current process ID")
    timestamp: datetime = Field(default_factory=datetime.now)


class WorkflowInfo(BaseModel):
    """Workflow debugging information model."""

    workflow_type: str = Field(..., description="Type of workflow")
    nodes: List[str] = Field(..., description="List of workflow nodes")
    edges: List[Dict[str, str]] = Field(..., description="Workflow edges/transitions")
    entry_point: str = Field(..., description="Workflow entry point")
    configuration: Dict[str, Any] = Field(..., description="Workflow configuration")
    validation_status: str = Field(..., description="Workflow validation status")


class ComponentStatus(BaseModel):
    """Individual component debugging status."""

    component_name: str = Field(..., description="Name of the component")
    status: str = Field(..., description="Component status")
    details: Dict[str, Any] = Field(default_factory=dict, description="Component details")
    last_checked: datetime = Field(default_factory=datetime.now)
    errors: List[str] = Field(default_factory=list, description="Component errors")


class ConfigurationInfo(BaseModel):
    """Application configuration information (sanitized)."""

    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment (dev/prod)")
    debug_mode: bool = Field(..., description="Debug mode status")
    api_host: str = Field(..., description="API host")
    api_port: int = Field(..., description="API port")
    log_level: str = Field(..., description="Logging level")
    llm_configuration: Dict[str, Any] = Field(..., description="LLM configuration (sanitized)")
    environment_variables: Dict[str, str] = Field(..., description="Sanitized environment variables")


def _sanitize_config_value(key: str, value: Any) -> Any:
    """Sanitize configuration values to hide sensitive information."""
    sensitive_keys = ["key", "token", "password", "secret", "credential", "auth"]

    if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
        if isinstance(value, str) and value:
            return f"***{value[-4:]}" if len(value) > 4 else "***"
        return "***"

    return value


def _get_sanitized_env_vars() -> Dict[str, str]:
    """Get sanitized environment variables for debugging."""
    sanitized_env = {}
    relevant_prefixes = ["INCIDENT_", "API_", "LLM_", "DEBUG_", "LOG_"]

    for key, value in os.environ.items():
        if any(key.startswith(prefix) for prefix in relevant_prefixes):
            sanitized_env[key] = _sanitize_config_value(key, value)

    return sanitized_env


async def get_debug_enabled_dependency() -> bool:
    """Dependency to check if debug endpoints are enabled."""
    settings = get_settings()
    if not settings.debug:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug endpoints are only available in debug mode",
        )
    return True


@router.get("/system-info", response_model=SystemInfo)
async def get_system_info(request: Request) -> SystemInfo:
    """
    Get system information for debugging.

    This endpoint provides basic system information useful for debugging
    deployment and environment issues.

    Args:
        request: FastAPI request object for context

    Returns:
        SystemInfo: System information details

    Raises:
        HTTPException: If system info collection fails
    """
    request_id = getattr(request.state, "request_id", None)

    try:
        logger.debug("Collecting system information", extra={"request_id": request_id})

        system_info = SystemInfo(
            python_version=sys.version,
            platform=platform.platform(),
            architecture=platform.architecture()[0],
            hostname=platform.node(),
            current_working_directory=os.getcwd(),
            process_id=os.getpid(),
            timestamp=datetime.now(),
        )

        logger.debug(
            "System information collected",
            extra={
                "request_id": request_id,
                "platform": system_info.platform,
                "python_version": system_info.python_version.split()[0],
            },
        )

        return system_info

    except Exception as e:
        logger.error(
            "Failed to collect system information",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to collect system information",
        ) from e


@router.get("/workflow-info", response_model=WorkflowInfo)
async def get_workflow_info(request: Request) -> WorkflowInfo:
    """
    Get workflow configuration and diagnostic information.

    This endpoint provides detailed information about the LangGraph workflow
    including node structure, transitions, and configuration.

    Args:
        request: FastAPI request object for context

    Returns:
        WorkflowInfo: Workflow diagnostic information

    Raises:
        HTTPException: If workflow info collection fails
    """
    request_id = getattr(request.state, "request_id", None)

    try:
        logger.debug("Collecting workflow information", extra={"request_id": request_id})

        # Get workflow instance
        workflow = await get_workflow()
        workflow_details = workflow.get_workflow_info()

        workflow_info = WorkflowInfo(
            workflow_type=type(workflow).__name__,
            nodes=workflow_details.get("nodes", []),
            edges=workflow_details.get("edges", []),
            entry_point=workflow_details.get("entry_point", "unknown"),
            configuration={
                "timeout": workflow_details.get("timeout", 120),
                "max_attempts": workflow_details.get("max_attempts", 3),
                "agents_count": len(workflow_details.get("agents", [])),
            },
            validation_status="valid",  # Workflow creation succeeded
        )

        logger.info(
            "Workflow information collected",
            extra={
                "request_id": request_id,
                "workflow_type": workflow_info.workflow_type,
                "nodes_count": len(workflow_info.nodes),
                "edges_count": len(workflow_info.edges),
            },
        )

        return workflow_info

    except Exception as e:
        logger.error(
            "Failed to collect workflow information",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to collect workflow information",
        ) from e


@router.get("/components", response_model=List[ComponentStatus])
async def get_components_status(request: Request) -> List[ComponentStatus]:
    """
    Get status of all system components.

    This endpoint provides detailed status information about all system
    components including LLM services, workflow, and other dependencies.

    Args:
        request: FastAPI request object for context

    Returns:
        List[ComponentStatus]: List of component statuses

    Raises:
        HTTPException: If component status collection fails
    """
    request_id = getattr(request.state, "request_id", None)

    try:
        logger.debug("Collecting component status", extra={"request_id": request_id})

        components = []

        # Check LLM Services
        try:
            llm_manager = await get_llm_service_manager()
            llm_health = await llm_manager.health_check_all()

            # llm_health is dict[str, bool]
            healthy_services = [name for name, is_healthy in llm_health.items() if is_healthy]
            all_healthy = all(llm_health.values())

            components.append(
                ComponentStatus(
                    component_name="LLM Services",
                    status="healthy" if all_healthy else "degraded",
                    details={
                        "services_count": len(llm_health),
                        "services_detail": {name: "healthy" if healthy else "unhealthy" for name, healthy in llm_health.items()},
                        "healthy_services": healthy_services,
                    },
                    last_checked=datetime.now(),
                    errors=[f"{name}: service unavailable" for name, is_healthy in llm_health.items() if not is_healthy],
                )
            )

        except Exception as e:
            components.append(
                ComponentStatus(
                    component_name="LLM Services",
                    status="error",
                    details={"error_type": type(e).__name__},
                    last_checked=datetime.now(),
                    errors=[str(e)],
                )
            )

        # Check Workflow
        try:
            workflow = await get_workflow()
            workflow_info = workflow.get_workflow_info()

            components.append(
                ComponentStatus(
                    component_name="Workflow Engine",
                    status="healthy",
                    details={
                        "workflow_type": type(workflow).__name__,
                        "nodes_count": len(workflow_info.get("nodes", [])),
                        "edges_count": len(workflow_info.get("edges", [])),
                        "agents_available": workflow_info.get("agents", []),
                    },
                    last_checked=datetime.now(),
                    errors=[],
                )
            )

        except Exception as e:
            components.append(
                ComponentStatus(
                    component_name="Workflow Engine",
                    status="error",
                    details={"error_type": type(e).__name__},
                    last_checked=datetime.now(),
                    errors=[str(e)],
                )
            )

        logger.info(
            "Component status collected",
            extra={
                "request_id": request_id,
                "components_count": len(components),
                "healthy_components": sum(1 for c in components if c.status == "healthy"),
            },
        )

        return components

    except Exception as e:
        logger.error(
            "Failed to collect component status",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to collect component status",
        ) from e


@router.get("/configuration", response_model=ConfigurationInfo, dependencies=[Depends(get_debug_enabled_dependency)])
async def get_configuration_info(request: Request) -> ConfigurationInfo:
    """
    Get application configuration information (sanitized).

    This endpoint provides configuration information with sensitive data
    sanitized. Only available in debug mode for security.

    Args:
        request: FastAPI request object for context

    Returns:
        ConfigurationInfo: Sanitized configuration information

    Raises:
        HTTPException: If configuration collection fails or debug mode is disabled
    """
    request_id = getattr(request.state, "request_id", None)

    try:
        logger.debug("Collecting configuration information", extra={"request_id": request_id})

        settings = get_settings()

        # Get LLM configuration (sanitized)
        llm_config = {
            "default_provider": getattr(settings, "default_llm_provider", "unknown"),
            "providers_configured": getattr(settings, "llm_providers", []),
            "timeout": getattr(settings, "llm_timeout", 30),
        }

        config_info = ConfigurationInfo(
            app_name=settings.app_name,
            version=settings.app_version,
            environment=settings.environment,
            debug_mode=settings.debug,
            api_host=settings.api_host,
            api_port=settings.api_port,
            log_level=getattr(settings, "log_level", "INFO"),
            llm_configuration=llm_config,
            environment_variables=_get_sanitized_env_vars(),
        )

        logger.debug(
            "Configuration information collected",
            extra={
                "request_id": request_id,
                "environment": config_info.environment,
                "debug_mode": config_info.debug_mode,
                "env_vars_count": len(config_info.environment_variables),
            },
        )

        return config_info

    except Exception as e:
        logger.error(
            "Failed to collect configuration information",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to collect configuration information",
        ) from e


@router.post("/test-extraction", dependencies=[Depends(get_debug_enabled_dependency)])
async def test_extraction_workflow(
    request: ExtractionRequest,
    http_request: Request,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Test the extraction workflow with detailed debugging information.

    This endpoint allows testing the extraction workflow with additional
    debugging output including intermediate states and agent interactions.
    Only available in debug mode.

    Args:
        request: Extraction request with test text
        http_request: FastAPI request object for context
        verbose: Whether to include verbose debugging information

    Returns:
        Dict[str, Any]: Detailed extraction results with debug information

    Raises:
        HTTPException: If test extraction fails or debug mode is disabled
    """
    request_id = getattr(http_request.state, "request_id", None)

    try:
        logger.debug(
            "Starting test extraction",
            extra={
                "request_id": request_id,
                "text_length": len(request.text),
                "verbose": verbose,
            },
        )

        # Import here to avoid circular imports
        from ...graph.workflow import extract_incident_info

        # Run extraction with detailed logging
        workflow_result = await extract_incident_info(text=request.text, options=request.options or {})

        debug_info = {
            "workflow_state": {
                "status": workflow_result.status,
                "current_step": workflow_result.current_status,
                "extraction_attempts": workflow_result.extraction_attempts,
                "processing_time": workflow_result.processing_time,
                "errors": workflow_result.errors,
                "warnings": workflow_result.warnings,
            },
            "extracted_data": workflow_result.extracted_data.model_dump() if workflow_result.extracted_data else None,
            "metadata": {
                "request_id": request_id,
                "text_length": len(request.text),
                "timestamp": datetime.now().isoformat(),
            },
        }

        if verbose:
            debug_info["verbose_details"] = {
                "supervisor_output": workflow_result.supervisor_output,
                "preprocessor_output": workflow_result.preprocessor_output,
                "extractor_output": workflow_result.extractor_output,
                "preprocessed_text": workflow_result.preprocessed_text,
            }

        logger.info(
            "Test extraction completed",
            extra={
                "request_id": request_id,
                "final_status": workflow_result.status,
                "errors_count": len(workflow_result.errors),
                "warnings_count": len(workflow_result.warnings),
            },
        )

        return debug_info

    except Exception as e:
        logger.error(
            "Test extraction failed",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test extraction failed: {str(e)}",
        ) from e


__all__ = ["router"]
