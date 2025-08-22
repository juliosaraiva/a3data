"""Tests for ExtractIncidentUseCase."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.incident_extractor.application.dtos.incident_dtos import (
    ExtractIncidentRequest,
)
from src.incident_extractor.application.use_cases.extract_incident_use_case import (
    ExtractIncidentUseCase,
)
from src.incident_extractor.core.exceptions import ApplicationError
from src.incident_extractor.domain.entities.incident import Incident
from src.incident_extractor.domain.enums import IncidentSeverity, IncidentType
from src.incident_extractor.domain.services.incident_enrichment_service import (
    EnrichmentResult,
    IncidentEnrichmentService,
)
from src.incident_extractor.domain.services.incident_extraction_service import (
    IncidentExtractionService,
)
from src.incident_extractor.domain.services.incident_validation_service import (
    IncidentValidationService,
    ValidationResult,
)
from src.incident_extractor.domain.value_objects.incident import IncidentDateTime
from src.incident_extractor.domain.value_objects.location import Location


@pytest.fixture
def mock_extraction_service():
    """Mock extraction service."""
    service = MagicMock(spec=IncidentExtractionService)
    service.extract_from_text = AsyncMock()
    service.health_check = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_validation_service():
    """Mock validation service."""
    service = MagicMock(spec=IncidentValidationService)
    service.validate_incident = AsyncMock()
    service.health_check = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_enrichment_service():
    """Mock enrichment service."""
    service = MagicMock(spec=IncidentEnrichmentService)
    service.enrich_incident = AsyncMock()
    service.health_check = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_llm_repository():
    """Mock LLM repository."""
    repository = MagicMock()
    repository.health_check = AsyncMock(return_value=True)
    repository.get_provider_name = AsyncMock(return_value="test_provider")
    repository.get_model_version = AsyncMock(return_value="test_model_v1")
    return repository


@pytest.fixture
def mock_incident():
    """Mock incident entity."""
    incident = MagicMock(spec=Incident)
    incident.id = "test-incident-123"
    incident.title = "Test Traffic Accident"
    incident.description = "A collision between two vehicles on Main Street"
    incident.severity = IncidentSeverity.MEDIUM
    incident.incident_type = IncidentType.TRAFFIC_ACCIDENT
    incident.confidence_score = 0.85
    incident.created_at = datetime.now()
    incident.updated_at = None
    incident.involved_parties = []
    incident.extracted_metadata = {}

    # Mock datetime and location value objects
    incident.datetime = MagicMock(spec=IncidentDateTime)
    incident.datetime.value = datetime.now()
    incident.datetime.original_text = "today at 2PM"
    incident.datetime.confidence = 0.8
    incident.datetime.is_relative = True

    incident.location = MagicMock(spec=Location)
    incident.location.address = "123 Main Street"
    incident.location.city = "São Paulo"
    incident.location.state = "SP"
    incident.location.coordinates = None
    incident.location.confidence = 0.7

    return incident


@pytest.fixture
def use_case(mock_extraction_service, mock_validation_service, mock_enrichment_service, mock_llm_repository):
    """Create ExtractIncidentUseCase with mocked dependencies."""
    return ExtractIncidentUseCase(
        extraction_service=mock_extraction_service,
        validation_service=mock_validation_service,
        enrichment_service=mock_enrichment_service,
        llm_repository=mock_llm_repository,
    )


@pytest.fixture
def valid_request():
    """Create valid extraction request."""
    return ExtractIncidentRequest(
        text="Um grave acidente de trânsito ocorreu na Avenida Paulista hoje às 14:30, envolvendo dois carros."
    )


class TestExtractIncidentUseCase:
    """Test ExtractIncidentUseCase class."""

    @pytest.mark.asyncio
    async def test_successful_extraction(
        self, use_case, valid_request, mock_extraction_service, mock_validation_service, mock_enrichment_service, mock_incident
    ):
        """Test successful incident extraction."""
        # Setup mocks
        extracted_data = {
            "title": "Traffic Accident",
            "description": "Collision on Paulista Avenue",
            "severity": "medium",
            "incident_type": "traffic_accident",
        }

        mock_extraction_service.extract_from_text.return_value = extracted_data

        validation_result = ValidationResult(is_valid=True, violations=[], warnings=[], score=0.9)
        mock_validation_service.validate_incident.return_value = validation_result

        enrichment_result = EnrichmentResult(
            enriched_incident=mock_incident,
            was_enriched=True,
            enriched_fields=["location"],
            confidence_improvements={"location": 0.1},
        )
        mock_enrichment_service.enrich_incident.return_value = enrichment_result

        # Mock incident creation
        with patch("src.incident_extractor.domain.entities.incident.Incident.from_extracted_data", return_value=mock_incident):
            # Execute use case
            response = await use_case.extract_incident(valid_request)

            # Verify response
            assert response.success is True
            assert response.incident is not None
            assert response.extraction_result.success is True
            assert response.validation_result.is_valid is True
            assert response.enrichment_result is not None
            assert response.enrichment_result.enriched is True

            # Verify service calls
            mock_extraction_service.extract_from_text.assert_called_once()
            mock_validation_service.validate_incident.assert_called_once_with(incident=mock_incident, validation_level="standard")
            mock_enrichment_service.enrich_incident.assert_called_once_with(incident=mock_incident)

    @pytest.mark.asyncio
    async def test_extraction_without_enrichment(
        self, use_case, mock_extraction_service, mock_validation_service, mock_enrichment_service, mock_incident
    ):
        """Test extraction without enrichment."""
        # Create request without enrichment
        request = ExtractIncidentRequest(text="Simple incident text", enrich_data=False)

        # Setup mocks
        extracted_data = {"title": "Simple Incident"}
        mock_extraction_service.extract_from_text.return_value = extracted_data

        validation_result = ValidationResult(is_valid=True, violations=[], warnings=[], score=0.8)
        mock_validation_service.validate_incident.return_value = validation_result

        with patch("src.incident_extractor.domain.entities.incident.Incident.from_extracted_data", return_value=mock_incident):
            # Execute use case
            response = await use_case.extract_incident(request)

            # Verify response
            assert response.success is True
            assert response.enrichment_result is None

            # Verify enrichment service was not called
            mock_enrichment_service.enrich_incident.assert_not_called()

    @pytest.mark.asyncio
    async def test_extraction_failure(self, use_case, valid_request, mock_extraction_service):
        """Test extraction failure."""
        # Setup extraction failure
        mock_extraction_service.extract_from_text.side_effect = Exception("LLM connection failed")

        # Execute use case
        response = await use_case.extract_incident(valid_request)

        # Verify error response
        assert response.success is False
        assert response.incident is None
        assert len(response.errors) > 0
        assert "LLM connection failed" in str(response.errors)

    @pytest.mark.asyncio
    async def test_incident_creation_failure(self, use_case, valid_request, mock_extraction_service):
        """Test incident entity creation failure."""
        # Setup mocks
        extracted_data = {"invalid": "data"}
        mock_extraction_service.extract_from_text.return_value = extracted_data

        # Mock incident creation failure
        with patch(
            "src.incident_extractor.domain.entities.incident.Incident.from_extracted_data",
            side_effect=ValueError("Invalid incident data"),
        ):
            # Execute use case
            response = await use_case.extract_incident(valid_request)

            # Verify error response
            assert response.success is False
            assert response.incident is None
            assert any("Failed to create incident" in error for error in response.errors)

    @pytest.mark.asyncio
    async def test_validation_failure(
        self, use_case, valid_request, mock_extraction_service, mock_validation_service, mock_incident
    ):
        """Test validation failure."""
        # Setup mocks
        extracted_data = {"title": "Test Incident"}
        mock_extraction_service.extract_from_text.return_value = extracted_data

        validation_result = ValidationResult(
            is_valid=False, validation_errors=["Missing location", "Invalid date"], quality_score=0.3, completeness_score=0.4
        )
        mock_validation_service.validate_incident.return_value = validation_result

        with patch("src.incident_extractor.domain.entities.incident.Incident.from_extracted_data", return_value=mock_incident):
            # Execute use case
            response = await use_case.extract_incident(valid_request)

            # Verify response shows validation failure but processing success
            assert response.success is True  # Overall processing succeeded
            assert response.validation_result.is_valid is False
            assert len(response.validation_result.validation_errors) == 2

    @pytest.mark.asyncio
    async def test_enrichment_failure(
        self, use_case, valid_request, mock_extraction_service, mock_validation_service, mock_enrichment_service, mock_incident
    ):
        """Test enrichment failure."""
        # Setup mocks
        extracted_data = {"title": "Test Incident"}
        mock_extraction_service.extract_from_text.return_value = extracted_data

        validation_result = ValidationResult(is_valid=True, validation_errors=[], quality_score=0.8, completeness_score=0.7)
        mock_validation_service.validate_incident.return_value = validation_result

        # Setup enrichment failure
        mock_enrichment_service.enrich_incident.side_effect = Exception("Enrichment service error")

        with patch("src.incident_extractor.domain.entities.incident.Incident.from_extracted_data", return_value=mock_incident):
            # Execute use case
            response = await use_case.extract_incident(valid_request)

            # Verify response handles enrichment failure gracefully
            assert response.success is True  # Overall processing succeeded
            assert response.enrichment_result is not None
            assert response.enrichment_result.enriched is False
            assert len(response.enrichment_result.errors) > 0

    @pytest.mark.asyncio
    async def test_validate_extraction_request_valid(self, use_case, valid_request):
        """Test request validation with valid request."""
        result = await use_case.validate_extraction_request(valid_request)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_extraction_request_empty_text(self, use_case):
        """Test request validation with empty text."""
        request = ExtractIncidentRequest(text="   ")  # Empty after strip

        with pytest.raises(ApplicationError) as exc_info:
            await use_case.validate_extraction_request(request)

        assert exc_info.value.error_code == "EMPTY_TEXT"

    @pytest.mark.asyncio
    async def test_validate_extraction_request_text_too_short(self, use_case):
        """Test request validation with text too short."""
        request = ExtractIncidentRequest(text="short")

        with pytest.raises(ApplicationError) as exc_info:
            await use_case.validate_extraction_request(request)

        assert exc_info.value.error_code == "TEXT_TOO_SHORT"

    @pytest.mark.asyncio
    async def test_validate_extraction_request_invalid_context(self, use_case):
        """Test request validation with invalid context."""
        request = ExtractIncidentRequest(
            text="Valid text for extraction",
            context="invalid_context",  # Should be dict, not string
        )

        with pytest.raises(ApplicationError) as exc_info:
            await use_case.validate_extraction_request(request)

        assert exc_info.value.error_code == "INVALID_CONTEXT_TYPE"

    @pytest.mark.asyncio
    async def test_get_processing_status(self, use_case, valid_request, mock_extraction_service):
        """Test getting processing status."""
        # Setup mocks for a simple successful extraction
        extracted_data = {"title": "Test"}
        mock_extraction_service.extract_from_text.return_value = extracted_data

        # Start processing (this will create status entry)
        processing_id = "test-processing-123"

        # Initially no status
        status = await use_case.get_processing_status(processing_id)
        assert status is None

        # After starting processing, status should be available
        with patch("src.incident_extractor.domain.entities.incident.Incident.from_extracted_data") as mock_create:
            mock_create.side_effect = Exception("Test error to stop processing early")

            await use_case.extract_incident(valid_request, processing_id=processing_id)

            # Now status should exist
            status = await use_case.get_processing_status(processing_id)
            assert status is not None
            assert status["status"] == "failed"

    @pytest.mark.asyncio
    async def test_health_check(
        self, use_case, mock_extraction_service, mock_validation_service, mock_enrichment_service, mock_llm_repository
    ):
        """Test health check functionality."""
        # All services healthy
        health = await use_case.health_check()

        assert health["healthy"] is True
        assert "response_time_ms" in health
        assert "components" in health
        assert health["components"]["llm_repository"] is True
        assert health["components"]["extraction_service"] is True
        assert health["components"]["validation_service"] is True
        assert health["components"]["enrichment_service"] is True
        assert "active_processes" in health
        assert "timestamp" in health

    @pytest.mark.asyncio
    async def test_health_check_with_unhealthy_service(
        self, use_case, mock_extraction_service, mock_validation_service, mock_enrichment_service, mock_llm_repository
    ):
        """Test health check with unhealthy service."""
        # Make extraction service unhealthy
        mock_extraction_service.health_check.return_value = False

        health = await use_case.health_check()

        assert health["healthy"] is False
        assert health["components"]["extraction_service"] is False

    @pytest.mark.asyncio
    async def test_health_check_with_exception(
        self, use_case, mock_extraction_service, mock_validation_service, mock_enrichment_service, mock_llm_repository
    ):
        """Test health check with service exception."""
        # Make LLM repository raise exception
        mock_llm_repository.health_check.side_effect = Exception("Connection failed")

        health = await use_case.health_check()

        assert health["healthy"] is False
        assert "error" in health

    @pytest.mark.asyncio
    async def test_processing_with_custom_context(
        self, use_case, mock_extraction_service, mock_validation_service, mock_incident
    ):
        """Test processing with custom context."""
        request = ExtractIncidentRequest(
            text="Incident text", context={"source": "news_feed"}, extraction_mode="quick", validation_level="minimal"
        )

        additional_context = {"priority": "high"}

        # Setup mocks
        extracted_data = {"title": "Test"}
        mock_extraction_service.extract_from_text.return_value = extracted_data

        validation_result = ValidationResult(is_valid=True, validation_errors=[], quality_score=0.8, completeness_score=0.7)
        mock_validation_service.validate_incident.return_value = validation_result

        with patch("src.incident_extractor.domain.entities.incident.Incident.from_extracted_data", return_value=mock_incident):
            # Execute with custom context
            await use_case.extract_incident(request, context=additional_context)

            # Verify extraction was called with merged context
            call_args = mock_extraction_service.extract_from_text.call_args
            assert call_args[1]["context"]["source"] == "news_feed"
            assert call_args[1]["context"]["priority"] == "high"
            assert call_args[1]["context"]["extraction_mode"] == "quick"

    def test_calculate_confidence_score(self, use_case):
        """Test confidence score calculation."""
        # Test with no data
        score = use_case._calculate_confidence_score(None)
        assert score == 0.0

        # Test with empty data
        score = use_case._calculate_confidence_score({})
        assert score == 0.1  # Base score

        # Test with partial data
        partial_data = {"title": "Test Incident", "description": "Test description"}
        score = use_case._calculate_confidence_score(partial_data)
        assert 0.1 < score < 1.0

        # Test with complete data
        complete_data = {
            "title": "Test Incident",
            "description": "Test description",
            "datetime": "2023-12-01T10:00:00",
            "location": "Test Location",
            "severity": "medium",
            "incident_type": "traffic_accident",
            "involved_parties": ["Party 1"],
        }
        score = use_case._calculate_confidence_score(complete_data)
        assert score == 1.0  # Maximum score
