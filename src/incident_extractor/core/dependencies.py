"""Dependency injection container for the application."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import Depends

from ..application.use_cases.extract_incident_use_case import ExtractIncidentUseCase
from ..core.config.config import Settings
from ..domain.repositories.llm_repository import LLMRepository
from ..domain.services.incident_enrichment_service import IncidentEnrichmentService
from ..domain.services.incident_extraction_service import IncidentExtractionService
from ..domain.services.incident_validation_service import IncidentValidationService
from ..infrastructure.llm.factory import LLMClientFactory
from ..infrastructure.llm.repository.llm_repository_impl import LLMRepositoryImpl
from ..infrastructure.logging.structured_logger import get_logger
from ..infrastructure.monitoring.metrics_collector import MetricsCollector
from ..infrastructure.preprocessing.text_processor import TextProcessor

logger = get_logger(__name__)


# --- Configuration Dependencies ---


@lru_cache
def get_settings() -> Settings:
    """Get application settings (cached singleton).

    Returns:
        Application settings instance
    """
    return Settings()


# --- Core Infrastructure Dependencies ---


@lru_cache
def get_metrics_collector() -> MetricsCollector:
    """Get metrics collector instance (singleton).

    Returns:
        MetricsCollector instance
    """
    return MetricsCollector()


@lru_cache
def get_text_processor(settings: Settings = Depends(get_settings)) -> TextProcessor:
    """Get text processor instance (singleton).

    Args:
        settings: Application settings

    Returns:
        TextProcessor instance
    """
    return TextProcessor(
        max_length=settings.TEXT_PROCESSING_MAX_LENGTH,
        min_length=settings.TEXT_PROCESSING_MIN_LENGTH,
        normalize_unicode=settings.TEXT_PROCESSING_NORMALIZE_UNICODE,
        remove_extra_spaces=settings.TEXT_PROCESSING_REMOVE_EXTRA_SPACES,
    )


# --- LLM Dependencies ---


def get_llm_repository(settings: Settings = Depends(get_settings)) -> LLMRepository:
    """Get LLM repository instance.

    Args:
        settings: Application settings

    Returns:
        LLMRepository implementation
    """
    # Prepare configuration for the LLM client
    llm_config = settings.llm_config

    # Convert SecretStr to string if needed
    api_key = llm_config.api_key.get_secret_value() if llm_config.api_key else None

    config = {
        "model_name": llm_config.model_name,
        "temperature": llm_config.temperature,
        "max_tokens": llm_config.max_tokens,
        "timeout": llm_config.timeout,
    }

    # Add provider-specific configuration
    if llm_config.provider.value == "openai":
        config["api_key"] = api_key
        if llm_config.base_url:
            config["base_url"] = llm_config.base_url
    elif llm_config.provider.value == "ollama":
        config["base_url"] = llm_config.base_url or "http://localhost:11434"
    elif llm_config.provider.value == "mock":
        # Mock client doesn't need additional config
        pass

    try:
        # Create LLM client using factory
        llm_client = LLMClientFactory.create_client(provider=llm_config.provider.value, config=config)

        # Return repository implementation
        return LLMRepositoryImpl(
            primary_client=llm_client,
            fallback_clients=None,  # TODO: Add fallback clients configuration
        )

    except Exception as e:
        logger.error("Failed to create LLM repository", error=str(e), provider=llm_config.provider.value)
        raise


# --- Domain Service Dependencies ---


def get_incident_extraction_service(
    llm_repository: LLMRepository = Depends(get_llm_repository),
    text_processor: TextProcessor = Depends(get_text_processor),
) -> IncidentExtractionService:
    """Get incident extraction service.

    Args:
        llm_repository: LLM repository instance
        text_processor: Text processor instance

    Returns:
        IncidentExtractionService instance
    """
    return IncidentExtractionService(
        llm_repository=llm_repository,
        text_processor=text_processor,
    )


def get_incident_validation_service(
    settings: Settings = Depends(get_settings),
) -> IncidentValidationService:
    """Get incident validation service.

    Args:
        settings: Application settings

    Returns:
        IncidentValidationService instance
    """
    return IncidentValidationService(
        max_description_length=settings.TEXT_PROCESSING_MAX_LENGTH,
        min_description_length=settings.TEXT_PROCESSING_MIN_LENGTH,
    )


def get_incident_enrichment_service(
    llm_repository: LLMRepository = Depends(get_llm_repository),
) -> IncidentEnrichmentService:
    """Get incident enrichment service.

    Args:
        llm_repository: LLM repository instance

    Returns:
        IncidentEnrichmentService instance
    """
    return IncidentEnrichmentService(llm_repository=llm_repository)


# --- Application Service Dependencies ---


def get_extract_incident_use_case(
    extraction_service: IncidentExtractionService = Depends(get_incident_extraction_service),
    validation_service: IncidentValidationService = Depends(get_incident_validation_service),
    enrichment_service: IncidentEnrichmentService = Depends(get_incident_enrichment_service),
    llm_repository: LLMRepository = Depends(get_llm_repository),
) -> ExtractIncidentUseCase:
    """Get extract incident use case.

    Args:
        extraction_service: Incident extraction service
        validation_service: Incident validation service
        enrichment_service: Incident enrichment service
        llm_repository: LLM repository instance

    Returns:
        ExtractIncidentUseCase instance
    """
    return ExtractIncidentUseCase(
        extraction_service=extraction_service,
        validation_service=validation_service,
        enrichment_service=enrichment_service,
        llm_repository=llm_repository,
    )


# --- Health Check Dependencies ---


async def get_health_check_dependencies(
    llm_repository: LLMRepository = Depends(get_llm_repository),
    metrics_collector: MetricsCollector = Depends(get_metrics_collector),
) -> dict[str, Any]:
    """Get dependencies for health checks.

    Args:
        llm_repository: LLM repository instance
        metrics_collector: Metrics collector instance

    Returns:
        Dictionary containing health check dependencies
    """
    return {
        "llm_repository": llm_repository,
        "metrics_collector": metrics_collector,
    }
