"""Dependency injection container for the incident extractor application.

This module provides the main DI container that wires together all
the dependencies across different layers of the application.
"""

from dependency_injector import containers, providers

from .config import Config

# TODO: Import these when modules are implemented
# from ...domain.repositories.llm_repository import LLMRepository
# from ...application.use_cases.extract_incident import ExtractIncidentUseCase
# from ...infrastructure.llm.factory import LLMClientFactory
# from ...infrastructure.preprocessing.text_processor import TextProcessor
# from ...infrastructure.monitoring.metrics_collector import MetricsCollector


class Container(containers.DeclarativeContainer):
    """Main DI container for the application."""

    # Configuration
    config = providers.Configuration()

    # TODO: Add providers when modules are implemented


# Global container instance
container = Container()


def wire_container(config: Config) -> None:
    """Wire the container with configuration."""
    # Set configuration
    container.config.from_dict(config.model_dump())

    # TODO: Wire dependencies when modules are implemented
