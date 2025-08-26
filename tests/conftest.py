"""
Pytest configuration and shared fixtures for incident extractor tests.

This module provides shared test fixtures and configuration for the test suite,
including FastAPI test client setup, database mocking, and common test data.
"""

import os
from typing import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from freezegun import freeze_time

# Set test environment before imports
os.environ["ENVIRONMENT"] = "development"  # Use 'development' instead of 'test'
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["LLM_MODEL_NAME"] = "gemma3:4b"
os.environ["LOG_LEVEL"] = "INFO"

from src.incident_extractor.main import get_application


@pytest.fixture(scope="session")
def app():
    """Create FastAPI application instance for testing."""
    return get_application()


@pytest.fixture(scope="session")
def client(app) -> Generator[TestClient, None, None]:
    """Create test client for FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_llm_service():
    """Mock LLM service for predictable test responses."""
    mock_service = AsyncMock()
    return mock_service


@pytest.fixture
def base_test_date():
    """Base test date for consistent date testing."""
    return "2025-08-26 10:00:00"  # Monday


@pytest.fixture
def frozen_time(base_test_date):
    """Freeze time for deterministic date testing."""
    with freeze_time(base_test_date):
        yield


# Test markers
pytest_plugins = ["pytest_asyncio"]


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: integration test")
    config.addinivalue_line("markers", "slow: slow running test")
    config.addinivalue_line("markers", "llm: test that requires LLM service")


@pytest.fixture
def sample_extraction_request():
    """Sample extraction request data."""
    return {
        "text": "Ontem às 14:30 o sistema de vendas apresentou falha no servidor principal. "
        "Isso afetou aproximadamente 50 usuários que não conseguiram fazer pedidos online."
    }


@pytest.fixture
def expected_extraction_response():
    """Expected response structure for sample request."""
    return {
        "data_ocorrencia": "2025-08-25 14:30",
        "local": "sistema de vendas",
        "tipo_incidente": "falha no servidor principal",
        "impacto": "aproximadamente 50 usuários que não conseguiram fazer pedidos online",
    }
