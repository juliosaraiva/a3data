"""FastAPI main application."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from config import settings
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from models.schemas import (
    ErrorResponse,
    HealthResponse,
    IncidentRequest,
    IncidentResponse,
)
from services.extractor import IncidentExtractor
from services.llm_client import LLMClient, LLMClientFactory
from utils.preprocessing import TextPreprocessor

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global services
llm_client: LLMClient | None = None
preprocessor: TextPreprocessor | None = None
extractor: IncidentExtractor | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    global llm_client, preprocessor, extractor

    # Startup
    logger.info("Starting Incident Extractor API")
    logger.info(f"Configuration: Provider={settings.llm_provider}, Model={settings.model_name}")

    # Initialize services
    try:
        llm_client = LLMClientFactory.create_client(
            provider=settings.llm_provider,
            base_url=settings.ollama_url,
            model_name=settings.model_name,
            timeout=settings.request_timeout,
        )

        preprocessor = TextPreprocessor(
            max_length=settings.max_input_length,
            normalize_text=settings.enable_text_normalization,
        )

        extractor = IncidentExtractor(llm_client, preprocessor)

        # Check LLM availability
        is_available = await llm_client.is_available()
        if not is_available:
            logger.warning("LLM service is not available at startup")
        else:
            logger.info("LLM service is available")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Incident Extractor API")
    if llm_client and hasattr(llm_client, "close"):
        await llm_client.close()


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="API for extracting structured information from incident descriptions using LLM",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail="An unexpected error occurred while processing your request",
        ).model_dump(),
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check the health status of the API and its dependencies",
)
async def health_check():
    """Health check endpoint."""
    try:
        llm_available = await llm_client.is_available() if llm_client else False

        return HealthResponse(
            status="healthy" if llm_available else "degraded",
            timestamp=datetime.now(),
            version=settings.api_version,
            llm_provider=settings.llm_provider,
            llm_available=llm_available,
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            version=settings.api_version,
            llm_provider=settings.llm_provider,
            llm_available=False,
        )


@app.post(
    "/extract",
    response_model=IncidentResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract Incident Information",
    description="Extract structured information from incident description text",
    responses={
        200: {
            "description": "Successfully extracted incident information",
            "model": IncidentResponse,
        },
        400: {
            "description": "Invalid request data",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
        503: {
            "description": "LLM service unavailable",
            "model": ErrorResponse,
        },
    },
)
async def extract_incident_info(request: IncidentRequest):
    """Extract structured information from incident description."""

    try:
        logger.info(f"Processing extraction request: {len(request.description)} chars")

        # Check if services are initialized
        if not extractor:
            logger.error("Extractor service not initialized")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service initialization failed",
            )

        # Check LLM availability
        if not await llm_client.is_available():
            logger.warning("LLM service unavailable, proceeding with fallback")

        # Extract incident information
        result = await extractor.extract_incident_info(request.description)

        logger.info("Extraction completed successfully")
        return result

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process incident description",
        ) from e


@app.get(
    "/",
    summary="API Information",
    description="Get basic information about the API",
)
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "description": "LLM-powered incident information extraction API",
        "endpoints": {
            "health": "/health",
            "extract": "/extract",
            "docs": "/docs" if settings.is_development else None,
        },
        "provider": settings.llm_provider,
        "model": settings.model_name,
    }


# Additional middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    start_time = datetime.now()

    # Process request
    response = await call_next(request)

    # Log request details
    process_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")

    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
