"""FastAPI application factory with lifespan management and dependency injection."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config.config import Settings
from ..core.dependencies import get_settings
from ..infrastructure.logging.structured_logger import get_logger
from ..presentation.api.v1 import v1_router
from ..presentation.middleware import setup_middleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan events with startup and shutdown logic.

    Args:
        app: FastAPI application instance

    Yields:
        None during application lifetime
    """
    # Get settings
    settings = get_settings()

    # Startup
    logger.info(
        "Starting Incident Extractor API",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT.value,
        llm_provider=settings.LLM_PROVIDER.value,
    )

    try:
        # Configure structured logging
        from ..infrastructure.logging.structured_logger import LoggerConfig, setup_logging

        log_config = LoggerConfig(
            level=settings.logging_config.level,
            enable_json_format=(settings.logging_config.format.value == "json"),
            enable_console_output=settings.logging_config.console_enabled,
            enable_file_output=settings.logging_config.file_enabled,
        )
        setup_logging(log_config)
        logger.info("Logging configured successfully")

        # Test LLM connectivity during startup
        from ..core.dependencies import get_llm_repository

        llm_repo = get_llm_repository(settings)
        is_available = await llm_repo.is_available()

        if is_available:
            logger.info("LLM service is available", provider=settings.LLM_PROVIDER.value)
        else:
            logger.warning("LLM service is not available", provider=settings.LLM_PROVIDER.value)

        # Store settings in app state for access in endpoints
        app.state.settings = settings

        logger.info("Application startup completed successfully")

    except Exception as e:
        logger.error("Failed to start application", error=str(e), error_type=type(e).__name__)
        raise

    # Application is running
    yield

    # Shutdown
    logger.info("Shutting down Incident Extractor API")

    try:
        # Cleanup resources
        logger.info("Cleaning up application resources")

        # Clear any cached dependencies
        from ..core.dependencies import get_metrics_collector, get_text_processor
        from ..core.dependencies import get_settings as _get_settings

        # Clear LRU caches
        _get_settings.cache_clear()
        get_metrics_collector.cache_clear()
        get_text_processor.cache_clear()

        logger.info("Application shutdown completed successfully")

    except Exception as e:
        logger.error("Error during application shutdown", error=str(e), error_type=type(e).__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure FastAPI application.

    Args:
        settings: Application settings (optional, will create default if None)

    Returns:
        Configured FastAPI application
    """
    if settings is None:
        settings = get_settings()

    # Create FastAPI app with lifespan management
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="LLM-powered incident extraction API following Clean Architecture principles",
        debug=settings.DEBUG,
        docs_url="/docs" if settings.ENVIRONMENT.value != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT.value != "production" else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT.value != "production" else None,
        lifespan=lifespan,
    )

    # Setup middleware (includes CORS, logging, metrics, etc.)
    setup_middleware(app, settings)

    # Add CORS middleware (if not already added by setup_middleware)
    if settings.ENVIRONMENT.value == "development":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allow all origins in development
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Include API routers
    app.include_router(v1_router)

    # Add root endpoint
    @app.get("/", include_in_schema=False)
    async def root():
        """Root endpoint returning basic API information."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT.value,
            "status": "online",
            "docs": "/docs",
        }

    return app


def get_app() -> FastAPI:
    """Get configured FastAPI application instance.

    Returns:
        FastAPI application
    """
    return create_app()
