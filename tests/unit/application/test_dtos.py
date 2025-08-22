"""Tests for application layer DTOs."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from src.incident_extractor.application.dtos.incident_dtos import (
    ExtractIncidentRequest,
    ExtractIncidentResponse,
    IncidentEnrichmentResult,
    IncidentExtractionResult,
    IncidentValidationResult,
    ProcessingMetadata,
)
from src.incident_extractor.domain.entities.incident import Incident
from src.incident_extractor.domain.enums import IncidentSeverity, IncidentType
from src.incident_extractor.domain.value_objects.incident import IncidentDateTime
from src.incident_extractor.domain.value_objects.location import Location


class TestExtractIncidentRequest:
    """Test ExtractIncidentRequest DTO."""

    def test_valid_request(self):
        """Test creating a valid extraction request."""
        request = ExtractIncidentRequest(text="Um acidente de trânsito ocorreu na Avenida Paulista ontem às 14:30")

        assert request.text == "Um acidente de trânsito ocorreu na Avenida Paulista ontem às 14:30"
        assert request.context is None
        assert request.extraction_mode == "comprehensive"
        assert request.validation_level == "standard"
        assert request.enrich_data is True

    def test_request_with_custom_parameters(self):
        """Test request with custom parameters."""
        context = {"source": "news_feed", "priority": "high"}

        request = ExtractIncidentRequest(
            text="Incêndio em prédio comercial",
            context=context,
            extraction_mode="quick",
            validation_level="minimal",
            enrich_data=False,
        )

        assert request.text == "Incêndio em prédio comercial"
        assert request.context == context
        assert request.extraction_mode == "quick"
        assert request.validation_level == "minimal"
        assert request.enrich_data is False

    def test_invalid_extraction_mode(self):
        """Test validation of extraction mode."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractIncidentRequest(text="Valid text", extraction_mode="invalid_mode")

        assert "extraction_mode must be one of" in str(exc_info.value)

    def test_invalid_validation_level(self):
        """Test validation of validation level."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractIncidentRequest(text="Valid text", validation_level="invalid_level")

        assert "validation_level must be one of" in str(exc_info.value)

    def test_text_too_short(self):
        """Test validation of minimum text length."""
        with pytest.raises(ValidationError):
            ExtractIncidentRequest(text="short")

    def test_text_too_long(self):
        """Test validation of maximum text length."""
        long_text = "x" * 50001
        with pytest.raises(ValidationError):
            ExtractIncidentRequest(text=long_text)


class TestIncidentExtractionResult:
    """Test IncidentExtractionResult DTO."""

    def test_successful_extraction(self):
        """Test successful extraction result."""
        incident_data = {"title": "Acidente na Paulista", "description": "Colisão entre dois veículos", "severity": "medium"}

        result = IncidentExtractionResult(
            success=True, incident_data=incident_data, confidence_score=0.85, extraction_time_ms=1500, errors=[]
        )

        assert result.success is True
        assert result.incident_data == incident_data
        assert result.confidence_score == 0.85
        assert result.extraction_time_ms == 1500
        assert result.errors == []

    def test_failed_extraction(self):
        """Test failed extraction result."""
        result = IncidentExtractionResult(
            success=False,
            incident_data=None,
            confidence_score=0.0,
            extraction_time_ms=500,
            errors=["LLM timeout", "Connection error"],
        )

        assert result.success is False
        assert result.incident_data is None
        assert result.confidence_score == 0.0
        assert result.extraction_time_ms == 500
        assert result.errors == ["LLM timeout", "Connection error"]

    def test_confidence_score_bounds(self):
        """Test confidence score validation bounds."""
        # Test lower bound
        with pytest.raises(ValidationError):
            IncidentExtractionResult(success=True, incident_data={}, confidence_score=-0.1, extraction_time_ms=100)

        # Test upper bound
        with pytest.raises(ValidationError):
            IncidentExtractionResult(success=True, incident_data={}, confidence_score=1.1, extraction_time_ms=100)


class TestIncidentValidationResult:
    """Test IncidentValidationResult DTO."""

    def test_valid_incident_result(self):
        """Test validation result for valid incident."""
        result = IncidentValidationResult(
            is_valid=True, validation_errors=[], quality_score=0.9, completeness_score=0.85, validation_time_ms=200
        )

        assert result.is_valid is True
        assert result.validation_errors == []
        assert result.quality_score == 0.9
        assert result.completeness_score == 0.85
        assert result.validation_time_ms == 200

    def test_invalid_incident_result(self):
        """Test validation result for invalid incident."""
        errors = ["Missing location", "Invalid date format"]

        result = IncidentValidationResult(
            is_valid=False, validation_errors=errors, quality_score=0.3, completeness_score=0.5, validation_time_ms=150
        )

        assert result.is_valid is False
        assert result.validation_errors == errors
        assert result.quality_score == 0.3
        assert result.completeness_score == 0.5


class TestIncidentEnrichmentResult:
    """Test IncidentEnrichmentResult DTO."""

    def test_successful_enrichment(self):
        """Test successful enrichment result."""
        enriched_fields = ["location", "severity"]
        confidence_improvements = {"location": 0.2, "severity": 0.15}

        result = IncidentEnrichmentResult(
            enriched=True,
            enrichment_fields=enriched_fields,
            confidence_improvements=confidence_improvements,
            enrichment_time_ms=800,
            errors=[],
        )

        assert result.enriched is True
        assert result.enrichment_fields == enriched_fields
        assert result.confidence_improvements == confidence_improvements
        assert result.enrichment_time_ms == 800
        assert result.errors == []

    def test_no_enrichment(self):
        """Test no enrichment performed."""
        result = IncidentEnrichmentResult(
            enriched=False,
            enrichment_fields=[],
            confidence_improvements={},
            enrichment_time_ms=50,
            errors=["No enrichment data available"],
        )

        assert result.enriched is False
        assert result.enrichment_fields == []
        assert result.confidence_improvements == {}
        assert result.errors == ["No enrichment data available"]


class TestProcessingMetadata:
    """Test ProcessingMetadata DTO."""

    def test_metadata_creation(self):
        """Test creating processing metadata."""
        processed_at = datetime.now()

        metadata = ProcessingMetadata(
            total_processing_time_ms=2500,
            processed_at=processed_at,
            processing_id="test-123",
            llm_provider="ollama",
            model_version="llama3.1",
        )

        assert metadata.total_processing_time_ms == 2500
        assert metadata.processed_at == processed_at
        assert metadata.processing_id == "test-123"
        assert metadata.llm_provider == "ollama"
        assert metadata.model_version == "llama3.1"

    def test_metadata_without_model_version(self):
        """Test metadata without model version."""
        metadata = ProcessingMetadata(
            total_processing_time_ms=1000, processed_at=datetime.now(), processing_id="test-456", llm_provider="openai"
        )

        assert metadata.model_version is None


class TestExtractIncidentResponse:
    """Test ExtractIncidentResponse DTO."""

    def test_successful_response_creation(self):
        """Test creating successful response."""
        extraction_result = IncidentExtractionResult(
            success=True, incident_data={"title": "Test incident"}, confidence_score=0.8, extraction_time_ms=1000
        )

        validation_result = IncidentValidationResult(
            is_valid=True, validation_errors=[], quality_score=0.9, completeness_score=0.85, validation_time_ms=200
        )

        metadata = ProcessingMetadata(
            total_processing_time_ms=2000, processed_at=datetime.now(), processing_id="test-789", llm_provider="ollama"
        )

        response = ExtractIncidentResponse(
            success=True,
            incident={"id": "incident-123", "title": "Test incident"},
            extraction_result=extraction_result,
            validation_result=validation_result,
            metadata=metadata,
            errors=[],
            warnings=[],
        )

        assert response.success is True
        assert response.incident is not None
        assert response.extraction_result == extraction_result
        assert response.validation_result == validation_result
        assert response.metadata == metadata
        assert response.errors == []
        assert response.warnings == []

    def test_from_incident_factory_method(self):
        """Test creating response from incident entity."""
        # Create mock incident
        incident = MagicMock(spec=Incident)
        incident.id = "incident-123"
        incident.title = "Test Incident"
        incident.description = "Test description"
        incident.severity = IncidentSeverity.MEDIUM
        incident.incident_type = IncidentType.TRAFFIC_ACCIDENT
        incident.confidence_score = 0.85
        incident.created_at = datetime.now()
        incident.updated_at = None
        incident.involved_parties = []
        incident.extracted_metadata = {}

        # Mock datetime and location
        incident.datetime = MagicMock(spec=IncidentDateTime)
        incident.datetime.value = datetime.now()
        incident.datetime.original_text = "ontem"
        incident.datetime.confidence = 0.8
        incident.datetime.is_relative = True

        incident.location = MagicMock(spec=Location)
        incident.location.address = "Rua das Flores, 123"
        incident.location.city = "São Paulo"
        incident.location.state = "SP"
        incident.location.coordinates = None
        incident.location.confidence = 0.7

        # Create other required objects
        extraction_result = IncidentExtractionResult(
            success=True, incident_data={"title": "Test incident"}, confidence_score=0.8, extraction_time_ms=1000
        )

        validation_result = IncidentValidationResult(
            is_valid=True, validation_errors=[], quality_score=0.9, completeness_score=0.85, validation_time_ms=200
        )

        metadata = ProcessingMetadata(
            total_processing_time_ms=2000, processed_at=datetime.now(), processing_id="test-789", llm_provider="ollama"
        )

        # Test factory method
        response = ExtractIncidentResponse.from_incident(
            incident=incident, extraction_result=extraction_result, validation_result=validation_result, metadata=metadata
        )

        assert response.success is True
        assert response.incident is not None
        assert response.incident["id"] == "incident-123"
        assert response.incident["title"] == "Test Incident"

    def test_from_error_factory_method(self):
        """Test creating error response."""
        error_message = "Processing failed"

        response = ExtractIncidentResponse.from_error(error_message)

        assert response.success is False
        assert response.incident is None
        assert response.errors == [error_message]
        assert response.extraction_result.success is False
        assert response.validation_result.is_valid is False
