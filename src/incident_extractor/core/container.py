"""Dependency injection container for the incident extractor application.

This module provides the main DI container that wires together all
the dependencies across different layers of the application.
"""

from dependency_injector import containers, providers

from ..infrastructure.health.health_checker import HealthChecker
from ..infrastructure.logging.structured_logger import LoggerConfig, LogLevel, StructuredLogger
from ..infrastructure.monitoring.metrics_collector import MetricsCollector, MetricsConfig
from ..infrastructure.preprocessing.text_processor import TextProcessor, TextProcessorConfig
from .config import Config

# TODO: Import these when modules are implemented
# from ...domain.repositories.llm_repository import LLMRepository
# from ...application.use_cases.extract_incident import ExtractIncidentUseCase
# from ...infrastructure.llm.factory import LLMClientFactory


class Container(containers.DeclarativeContainer):
    """Main DI container for the application."""

    # Configuration
    config = providers.Configuration()

    # Infrastructure services
    health_checker = providers.Singleton(HealthChecker, timeout_seconds=config.MONITORING_HEALTH_CHECK_TIMEOUT)

    metrics_config = providers.Factory(
        MetricsConfig,
        enable_prometheus=config.MONITORING_METRICS_ENABLED,
        metric_prefix="incident_extractor",
        track_response_times=True,
        track_error_rates=True,
        track_throughput=True,
        track_llm_usage=True,
        track_extraction_quality=True,
    )

    metrics_collector = providers.Singleton(MetricsCollector, config=metrics_config)

    text_processor_config = providers.Factory(
        TextProcessorConfig,
        locale="pt_BR",
        timezone="America/Sao_Paulo",
        min_text_length=config.TEXT_PROCESSING_MIN_LENGTH,
        max_text_length=config.TEXT_PROCESSING_MAX_LENGTH,
        normalize_unicode=config.TEXT_PROCESSING_NORMALIZE_UNICODE,
        normalize_whitespace=config.TEXT_PROCESSING_REMOVE_EXTRA_SPACES,
    )

    text_processor = providers.Singleton(TextProcessor, config=text_processor_config)

    logger_config = providers.Factory(
        LoggerConfig,
        level=LogLevel.INFO,  # Convert from config.LOG_LEVEL
        enable_json_format=True,
        enable_console_output=config.LOG_CONSOLE_ENABLED,
        enable_file_output=config.LOG_FILE_ENABLED,
    )

    structured_logger = providers.Factory(StructuredLogger, name="incident_extractor", config=logger_config)

    # TODO: Add providers when modules are implemented


# Global container instance
container = Container()


def wire_container(config: Config) -> None:
    """Wire the container with configuration."""
    # Set configuration
    container.config.from_dict(config.model_dump())

    # TODO: Wire dependencies when modules are implemented
