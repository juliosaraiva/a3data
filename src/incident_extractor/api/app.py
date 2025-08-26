"""
FastAPI application factory.

This module provides the create_app() factory function for creating and configuring
the FastAPI application instance with proper middleware, routing, and lifecycle management.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..config import configure_logging, get_logger, get_settings
from ..graph.workflow import get_workflow
from ..services.llm_service import get_llm_service_manager

# Import Phase 3 middleware components
from .middleware.cors import configure_cors
from .middleware.error_handling import error_handling_middleware
from .middleware.logging import request_logging_middleware
from .middleware.security import security_middleware
from .middleware.timing import timing_middleware


@asynccontextmanager
async def create_lifespan_manager(app: FastAPI):
    """
    Create application lifespan manager.

    Handles startup and shutdown procedures with proper error handling
    and resource cleanup.

    Args:
        app: The FastAPI application instance

    Yields:
        None: Control back to the application after startup
    """
    logger = get_logger("app.lifespan")

    # Startup procedures
    logger.info("Starting Incident Extractor API")

    try:
        # Initialize LLM services
        service_manager = await get_llm_service_manager()
        logger.info("LLM services initialized")

        # Initialize workflow
        workflow = await get_workflow()
        workflow_info = workflow.get_workflow_info()
        logger.info("Workflow initialized", workflow_info=workflow_info)

        # Validate system health
        health_results = await service_manager.health_check_all()
        logger.info("System health check completed", health=health_results)

        logger.info("Application startup completed successfully")

    except Exception as e:
        logger.error("Application startup failed", error=str(e), exc_info=True)
        raise

    yield

    # Shutdown procedures
    logger.info("Shutting down Incident Extractor API")

    try:
        # Clean up resources
        service_manager = await get_llm_service_manager()
        await service_manager.close_all()
        logger.info("Application shutdown completed successfully")
    except Exception as e:
        logger.error("Application shutdown error", error=str(e), exc_info=True)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    This factory function creates a FastAPI instance with all necessary
    configuration including middleware, CORS, logging, and lifecycle management.

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    # Get application settings
    settings = get_settings()

    # Configure logging before creating the app
    configure_logging()
    logger = get_logger("app.factory")

    logger.info(
        "Creating FastAPI application", app_name=settings.app_name, version=settings.app_version, environment=settings.environment
    )

    # Create FastAPI application with lifespan
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Sistema de extração de informações de incidentes de TI usando multi-agentes LangGraph",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=create_lifespan_manager,
        # Additional production-ready settings
        debug=settings.debug,
        openapi_tags=[
            {"name": "health", "description": "System health and status endpoints"},
            {"name": "extraction", "description": "Incident information extraction endpoints"},
            {"name": "metrics", "description": "Application metrics and monitoring"},
            {"name": "debug", "description": "Debug and diagnostic endpoints"},
        ],
    )

    # Configure CORS middleware (first in chain) using Phase 3 CORS configuration
    configure_cors(app)

    # Add Phase 3 middleware in proper order (outer to inner)
    # 1. Security middleware (first for request validation)
    app.middleware("http")(security_middleware)

    # 2. Error handling (catch all errors)
    app.middleware("http")(error_handling_middleware)

    # 3. Request logging (log after security/error validation)
    app.middleware("http")(request_logging_middleware)

    # 4. Timing middleware (innermost for accurate timing)
    app.middleware("http")(timing_middleware)

    # Include API routers in logical order
    from .routers import debug, extraction, health, metrics

    logger.info("Registering API routers")

    # Health endpoints - highest priority for monitoring
    app.include_router(health.router, prefix="/api")
    logger.debug("Registered health router")

    # Core business logic endpoints
    app.include_router(extraction.router, prefix="/api")
    logger.debug("Registered extraction router")

    # Monitoring and metrics endpoints
    app.include_router(metrics.router, prefix="/api")
    logger.debug("Registered metrics router")

    # Debug endpoints - lowest priority, development focused
    app.include_router(debug.router, prefix="/api")
    logger.debug("Registered debug router")

    logger.info("All API routers registered successfully")

    logger.info("FastAPI application created successfully")

    return app
