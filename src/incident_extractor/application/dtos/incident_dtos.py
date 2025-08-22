"""Incident extraction DTOs for request/response handling."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, validator

from ...domain.entities.incident import Incident


class ExtractIncidentRequest(BaseModel):
    """Request DTO for incident extraction."""

    text: str = Field(..., min_length=10, max_length=50000, description="Raw text to extract incident information from")

    context: dict[str, Any] | None = Field(default=None, description="Additional context information for extraction")

    extraction_mode: str = Field(default="comprehensive", description="Extraction mode: 'comprehensive', 'quick', or 'detailed'")

    validation_level: str = Field(default="standard", description="Validation level: 'minimal', 'standard', or 'strict'")

    enrich_data: bool = Field(default=True, description="Whether to enrich extracted data with additional context")

    @validator("extraction_mode")
    def validate_extraction_mode(cls, v: str) -> str:
        """Validate extraction mode."""
        allowed_modes = ["comprehensive", "quick", "detailed"]
        if v not in allowed_modes:
            raise ValueError(f"extraction_mode must be one of {allowed_modes}")
        return v

    @validator("validation_level")
    def validate_validation_level(cls, v: str) -> str:
        """Validate validation level."""
        allowed_levels = ["minimal", "standard", "strict"]
        if v not in allowed_levels:
            raise ValueError(f"validation_level must be one of {allowed_levels}")
        return v


class IncidentExtractionResult(BaseModel):
    """Result of incident extraction process."""

    success: bool = Field(..., description="Whether extraction was successful")
    incident_data: dict[str, Any] | None = Field(default=None, description="Raw extracted incident data")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score of extraction (0.0 to 1.0)")
    extraction_time_ms: int = Field(..., ge=0, description="Time taken for extraction in milliseconds")
    errors: list[str] = Field(default_factory=list, description="List of extraction errors")


class IncidentValidationResult(BaseModel):
    """Result of incident validation process."""

    is_valid: bool = Field(..., description="Whether incident data is valid")
    validation_errors: list[str] = Field(default_factory=list, description="List of validation errors")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Quality score of incident data (0.0 to 1.0)")
    completeness_score: float = Field(..., ge=0.0, le=1.0, description="Completeness score of incident data (0.0 to 1.0)")
    validation_time_ms: int = Field(..., ge=0, description="Time taken for validation in milliseconds")


class IncidentEnrichmentResult(BaseModel):
    """Result of incident enrichment process."""

    enriched: bool = Field(..., description="Whether enrichment was performed")
    enrichment_fields: list[str] = Field(default_factory=list, description="List of fields that were enriched")
    confidence_improvements: dict[str, float] = Field(default_factory=dict, description="Confidence score improvements by field")
    enrichment_time_ms: int = Field(..., ge=0, description="Time taken for enrichment in milliseconds")
    errors: list[str] = Field(default_factory=list, description="List of enrichment errors")


class ProcessingMetadata(BaseModel):
    """Metadata about the processing pipeline."""

    total_processing_time_ms: int = Field(..., ge=0, description="Total processing time in milliseconds")
    processed_at: datetime = Field(..., description="Timestamp when processing completed")
    processing_id: str = Field(..., description="Unique identifier for this processing request")
    llm_provider: str = Field(..., description="LLM provider used for extraction")
    model_version: str | None = Field(default=None, description="Model version used for extraction")

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class ExtractIncidentResponse(BaseModel):
    """Response DTO for incident extraction."""

    success: bool = Field(..., description="Overall success of the operation")

    incident: dict[str, Any] | None = Field(default=None, description="Extracted incident data in serialized format")

    extraction_result: IncidentExtractionResult = Field(..., description="Detailed extraction results")

    validation_result: IncidentValidationResult = Field(..., description="Validation results")

    enrichment_result: IncidentEnrichmentResult | None = Field(default=None, description="Enrichment results (if requested)")

    metadata: ProcessingMetadata = Field(..., description="Processing metadata")

    errors: list[str] = Field(default_factory=list, description="List of overall processing errors")

    warnings: list[str] = Field(default_factory=list, description="List of processing warnings")

    @staticmethod
    def from_incident(
        incident: Incident,
        extraction_result: IncidentExtractionResult,
        validation_result: IncidentValidationResult,
        metadata: ProcessingMetadata,
        enrichment_result: IncidentEnrichmentResult | None = None,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> ExtractIncidentResponse:
        """Create response from domain incident."""
        # Serialize incident to dict
        incident_dict = {
            "id": str(incident.id),
            "title": incident.title,
            "description": incident.description,
            "severity": incident.severity.value,
            "incident_type": incident.incident_type.value,
            "datetime": {
                "value": incident.datetime.value.isoformat() if incident.datetime.value else None,
                "original_text": incident.datetime.original_text,
                "confidence": incident.datetime.confidence,
                "is_relative": incident.datetime.is_relative,
            },
            "location": {
                "address": incident.location.address,
                "city": incident.location.city,
                "state": incident.location.state,
                "coordinates": incident.location.coordinates,
                "confidence": incident.location.confidence,
            },
            "involved_parties": [party.name for party in incident.involved_parties],
            "extracted_metadata": incident.extracted_metadata,
            "confidence_score": incident.confidence_score,
            "created_at": incident.created_at.isoformat(),
            "updated_at": incident.updated_at.isoformat() if incident.updated_at else None,
        }

        return ExtractIncidentResponse(
            success=True,
            incident=incident_dict,
            extraction_result=extraction_result,
            validation_result=validation_result,
            enrichment_result=enrichment_result,
            metadata=metadata,
            errors=errors or [],
            warnings=warnings or [],
        )

    @staticmethod
    def from_error(
        error_message: str,
        extraction_result: IncidentExtractionResult | None = None,
        validation_result: IncidentValidationResult | None = None,
        metadata: ProcessingMetadata | None = None,
    ) -> ExtractIncidentResponse:
        """Create error response."""
        import uuid
        from datetime import datetime

        default_metadata = metadata or ProcessingMetadata(
            total_processing_time_ms=0, processed_at=datetime.now(), processing_id=str(uuid.uuid4()), llm_provider="unknown"
        )

        default_extraction = extraction_result or IncidentExtractionResult(
            success=False, confidence_score=0.0, extraction_time_ms=0, errors=[error_message]
        )

        default_validation = validation_result or IncidentValidationResult(
            is_valid=False, quality_score=0.0, completeness_score=0.0, validation_time_ms=0, validation_errors=[error_message]
        )

        return ExtractIncidentResponse(
            success=False,
            incident=None,
            extraction_result=default_extraction,
            validation_result=default_validation,
            enrichment_result=None,
            metadata=default_metadata,
            errors=[error_message],
            warnings=[],
        )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}
