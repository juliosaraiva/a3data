"""FastAPI application for the incident extractor service."""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Dict

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from incident_extractor.config import RequestLoggingMiddleware, configure_logging, get_logger, get_settings
from incident_extractor.graph.workflow import extract_incident_info, get_workflow
from incident_extractor.models import (
    ExtractionRequest,
    HealthStatus,
    IncidentData,
    ProcessingMetrics,
    ProcessingStatus,
)
from incident_extractor.services.llm_service import get_llm_service_manager

# Global metrics tracking
metrics = ProcessingMetrics()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown procedures.
    """
    logger = get_logger("app.lifespan")

    # Startup
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
        logger.error(f"Application startup failed: {e}", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("Shutting down Incident Extractor API")

    try:
        # Clean up resources
        service_manager = await get_llm_service_manager()
        await service_manager.close_all()
        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error(f"Application shutdown error: {e}", exc_info=True)


# Initialize FastAPI application
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Sistema de extração de informações de incidentes de TI usando multi-agentes LangGraph",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Configure logging
configure_logging()
logger = get_logger("app.main")


# Dependency for request timing
async def get_request_timer():
    """Dependency to track request timing."""
    start_time = time.time()
    yield start_time


@app.get("/", response_model=Dict[str, Any])
async def root():
    """
    Root endpoint with API information.

    Returns:
        API information and status
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "running",
        "docs_url": "/docs",
        "health_check_url": "/health",
        "extraction_endpoint": "/extract",
    }


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """
    Health check endpoint.

    Returns:
        System health status including component checks
    """
    logger.info("Health check requested")

    try:
        # Check LLM services
        service_manager = await get_llm_service_manager()
        llm_health = await service_manager.health_check_all()

        # Check workflow
        workflow = await get_workflow()
        workflow_validation = await workflow.validate_workflow()

        # Determine overall health
        overall_healthy = (
            any(llm_health.values())  # At least one LLM service is healthy
            and all(workflow_validation.values())  # Workflow validation passes
        )

        components = {
            "llm_services": {"status": "healthy" if any(llm_health.values()) else "unhealthy", "details": llm_health},
            "workflow": {
                "status": "healthy" if all(workflow_validation.values()) else "unhealthy",
                "details": workflow_validation,
            },
            "metrics": {"status": "healthy", "details": metrics.model_dump()},
        }

        health_status = HealthStatus(
            status="healthy" if overall_healthy else "unhealthy", version=settings.app_version, components=components
        )

        logger.info("Health check completed", overall_healthy=overall_healthy)
        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)

        health_status = HealthStatus(
            status="unhealthy",
            version=settings.app_version,
            components={"error": {"status": "error", "details": {"message": str(e)}}},
        )
        return health_status


@app.post("/extract", response_model=IncidentData)
async def extract_incident(request: ExtractionRequest, start_time: float = Depends(get_request_timer)):
    """
    Extract incident information from Portuguese text.

    Args:
        request: Extraction request containing incident text
        start_time: Request start time (injected by dependency)

    Returns:
        Structured incident data containing data_ocorrencia, local, tipo_incidente, and impacto

    Raises:
        HTTPException: For various error conditions
    """
    request_id = id(request)  # Simple request ID for tracking

    logger.info("Extraction request received", request_id=request_id, text_length=len(request.text), options=request.options)

    # Update metrics
    metrics.total_requests += 1

    try:
        # Validate input length
        if len(request.text) < 10:
            metrics.validation_errors += 1
            raise HTTPException(status_code=422, detail="Texto muito curto. Mínimo de 10 caracteres necessários.")

        if len(request.text) > settings.max_preprocessing_length:
            metrics.validation_errors += 1
            raise HTTPException(
                status_code=422, detail=f"Texto muito longo. Máximo de {settings.max_preprocessing_length} caracteres."
            )

        # Execute extraction workflow
        logger.info("Starting extraction workflow", request_id=request_id)

        final_state = await extract_incident_info(text=request.text, options=request.options)

        # Calculate processing time
        processing_time = time.time() - start_time

        # Update metrics
        if final_state.status == ProcessingStatus.SUCCESS:
            metrics.successful_extractions += 1
        else:
            metrics.failed_extractions += 1

        # Update average processing time
        total_processed = metrics.successful_extractions + metrics.failed_extractions
        metrics.average_processing_time = (
            metrics.average_processing_time * (total_processed - 1) + processing_time
        ) / total_processed

        # Update agent metrics
        if final_state.supervisor_output:
            metrics.supervisor_calls += 1
        if final_state.preprocessor_output:
            metrics.preprocessor_calls += 1
        if final_state.extractor_output:
            metrics.extractor_calls += 1

        # Log detailed information for monitoring
        logger.info(
            "Extraction completed",
            request_id=request_id,
            status=final_state.status,
            processing_time=processing_time,
            extracted_fields=_count_extracted_fields(final_state.extracted_data),
            processing_details=_get_processing_details(final_state),
        )

        # Return only the extracted data as per task requirements
        return final_state.extracted_data

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except asyncio.TimeoutError:
        metrics.timeout_errors += 1
        logger.error("Extraction timed out", request_id=request_id)
        raise HTTPException(status_code=408, detail="Processamento excedeu tempo limite. Tente novamente com texto mais curto.")
    except Exception as e:
        metrics.llm_errors += 1
        logger.error(f"Extraction failed: {e}", request_id=request_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno no processamento. Tente novamente em alguns instantes.")


@app.get("/metrics", response_model=ProcessingMetrics)
async def get_metrics():
    """
    Get processing metrics.

    Returns:
        Current processing metrics
    """
    logger.info("Metrics requested")
    metrics.last_updated = metrics.last_updated  # Update timestamp
    return metrics


@app.post("/debug/workflow-info")
async def get_workflow_info():
    """
    Debug endpoint to get workflow information.

    Returns:
        Workflow structure and configuration
    """
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        workflow = await get_workflow()
        workflow_info = workflow.get_workflow_info()

        # Add runtime information
        service_manager = await get_llm_service_manager()
        llm_health = await service_manager.health_check_all()

        return {
            "workflow": workflow_info,
            "llm_services": llm_health,
            "settings": {
                "environment": settings.environment,
                "debug": settings.debug,
                "ollama_model": settings.ollama_model,
                "max_preprocessing_length": settings.max_preprocessing_length,
            },
        }
    except Exception as e:
        logger.error(f"Debug info request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper logging."""
    logger.warning(f"HTTP exception: {exc.status_code}", detail=exc.detail, path=request.url.path)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", path=request.url.path, exc_info=True)
    return JSONResponse(
        status_code=500, content={"detail": "Erro interno do servidor. Contate o suporte se o problema persistir."}
    )


# Helper functions
def _get_status_message(state) -> str:
    """Generate human-readable status message."""
    status_messages = {
        ProcessingStatus.SUCCESS: "Extração realizada com sucesso",
        ProcessingStatus.PARTIAL_SUCCESS: "Extração parcialmente realizada",
        ProcessingStatus.ERROR: "Erro durante o processamento",
        ProcessingStatus.PROCESSING: "Processamento em andamento",
    }

    base_message = status_messages.get(state.status, "Status desconhecido")

    if state.warnings:
        base_message += f" ({len(state.warnings)} avisos)"

    return base_message


def _get_processing_details(state) -> Dict[str, Any]:
    """Get processing details from workflow state."""
    details = {
        "etapa_final": state.current_status,
        "tentativas_extracao": state.extraction_attempts,
        "total_erros": len(state.errors),
        "total_avisos": len(state.warnings),
    }

    # Add agent outputs if available
    if state.supervisor_output:
        details["supervisor"] = state.supervisor_output
    if state.preprocessor_output:
        details["preprocessor"] = state.preprocessor_output
    if state.extractor_output:
        details["extractor"] = state.extractor_output

    return details


def _count_extracted_fields(data) -> int:
    """Count number of extracted fields."""
    if not data:
        return 0

    fields = [data.data_ocorrencia, data.local, data.tipo_incidente, data.impacto]
    return sum(1 for field in fields if field is not None)


# Development server
if __name__ == "__main__":
    logger.info("Starting development server")
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
        access_log=True,
    )
