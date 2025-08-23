"""Incident extraction API endpoints."""

import time
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from src.incident_extractor.application.dtos.incident_dtos import ExtractIncidentRequest
from src.incident_extractor.infrastructure.preprocessing.text_processor import TextProcessor

# Create incidents router
router = APIRouter()


class IncidentExtractionRequest(BaseModel):
    """Request schema for incident extraction."""

    text: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="Text containing incident information to extract",
        json_schema_extra={"example": "Acidente de trânsito na Av. Paulista com dois feridos leves às 14:30 de hoje"},
    )

    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional extraction options",
        json_schema_extra={"example": {"extraction_mode": "comprehensive", "validation_level": "standard", "enrich_data": True}},
    )

    @field_validator("text")
    @classmethod
    def validate_text_content(cls, v: str) -> str:
        """Validate text content."""
        if not v or not v.strip():
            raise ValueError("Text cannot be empty or contain only whitespace")

        return v.strip()


class IncidentExtractionResponse(BaseModel):
    """Response schema for incident extraction."""

    success: bool = Field(..., description="Whether extraction was successful")

    incident: dict[str, Any] | None = Field(None, description="Extracted incident information")

    confidence_score: float | None = Field(None, ge=0.0, le=1.0, description="Confidence score of the extraction (0-1)")

    processing_time_ms: int = Field(..., description="Processing time in milliseconds")

    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the extraction process")

    errors: list[str] = Field(default_factory=list, description="List of errors encountered during processing")

    warnings: list[str] = Field(default_factory=list, description="List of warnings encountered during processing")


@router.post(
    "/extract",
    response_model=IncidentExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract incident information from text",
    description="Extract structured incident information from unstructured text using LLM analysis",
)
async def extract_incident(request: IncidentExtractionRequest) -> IncidentExtractionResponse:
    """Extract incident information from text.

    This endpoint processes unstructured text and extracts structured incident information
    including type, severity, location, date/time, and other relevant details.

    Args:
        request: Incident extraction request with text and options

    Returns:
        Structured incident information with confidence scores and metadata

    Raises:
        HTTPException: If extraction fails due to validation or processing errors
    """
    start_time = time.time()
    errors: list[str] = []
    warnings: list[str] = []

    try:
        # Create text processor instance
        text_processor = TextProcessor()

        # Preprocess the text
        processed_text_result = None
        try:
            processed_text_result = await text_processor.process_text(request.text)
            processed_text = processed_text_result.normalized_text

            # Add preprocessing metadata
            preprocessing_metadata = {
                "original_length": len(request.text),
                "processed_length": len(processed_text),
                "word_count": processed_text_result.word_count,
                "extracted_dates": len(processed_text_result.extracted_dates),
                "extracted_locations": len(processed_text_result.extracted_locations),
                "extracted_numbers": len(processed_text_result.extracted_numbers),
            }

        except Exception as e:
            warnings.append(f"Text preprocessing warning: {str(e)}")
            processed_text = request.text.strip()
            preprocessing_metadata = {}

        # Create use case request for validation (unused for now but validates the DTO)
        _ = ExtractIncidentRequest(
            text=processed_text,
            extraction_mode=request.options.get("extraction_mode", "comprehensive"),
            validation_level=request.options.get("validation_level", "standard"),
            enrich_data=request.options.get("enrich_data", True),
            context=request.options.get("context"),
        )

        # For now, return a mock response since full dependency setup is needed
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Analyze text for basic incident information
        incident_keywords = {
            "acidente": "accident",
            "emergência": "emergency",
            "incêndio": "fire",
            "assalto": "robbery",
            "furto": "theft",
            "colisão": "collision",
            "ferido": "injury",
        }

        detected_type = "unknown"
        for keyword, incident_type in incident_keywords.items():
            if keyword in processed_text.lower():
                detected_type = incident_type
                break

        # Extract basic location information
        location_info = None
        if processed_text_result:
            for location in processed_text_result.extracted_locations:
                if location:
                    location_info = {"address": location, "confidence": 0.7}
                    break

        # Create mock incident data based on text analysis
        extracted_dates = []
        if processed_text_result:
            extracted_dates = [date.isoformat() for date in processed_text_result.extracted_dates]

        mock_incident_data = {
            "title": f"Incidente detectado: {detected_type}",
            "description": processed_text[:200] + "..." if len(processed_text) > 200 else processed_text,
            "incident_type": detected_type,
            "severity": "medium",
            "datetime": {
                "extracted_dates": extracted_dates,
                "confidence": 0.5 if processed_text_result and processed_text_result.extracted_dates else 0.2,
            },
            "location": location_info or {"address": "Not specified", "confidence": 0.1},
            "extracted_numbers": processed_text_result.extracted_numbers if processed_text_result else [],
            "confidence_score": 0.6,
        }

        return IncidentExtractionResponse(
            success=True,
            incident=mock_incident_data,
            confidence_score=0.6,
            processing_time_ms=processing_time_ms,
            metadata={
                "preprocessing": preprocessing_metadata,
                "extraction_method": "basic_text_analysis",
                "note": "This is a basic implementation. Full LLM-based extraction requires complete dependency setup.",
                "detected_keywords": [k for k in incident_keywords.keys() if k in processed_text.lower()],
            },
            errors=errors,
            warnings=warnings,
        )

    except ValueError as e:
        # Input validation errors
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "Validation error", "message": str(e), "type": "validation_error"},
        )

    except Exception as e:
        # Unexpected errors
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Log the error (this should use proper structured logging)
        print(f"Unexpected error in incident extraction: {e}")

        return IncidentExtractionResponse(
            success=False,
            incident=None,
            confidence_score=0.0,
            processing_time_ms=processing_time_ms,
            metadata={
                "error_type": "unexpected_error",
                "error_message": str(e),
            },
            errors=[f"Internal server error: {str(e)}"] + errors,
            warnings=warnings,
        )


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Check incidents service health",
    description="Health check specific to the incident extraction service",
)
async def incidents_service_health() -> dict[str, Any]:
    """Check the health of the incident extraction service.

    Returns:
        Health status of the incident extraction components
    """
    try:
        # Test basic functionality
        text_processor = TextProcessor()
        stats = text_processor.get_processing_stats()

        return {
            "status": "healthy",
            "service": "incident-extraction",
            "timestamp": time.time(),
            "components": {
                "text_processor": {"status": "healthy", "config": stats["config"]},
                "extraction_engine": {"status": "partial", "note": "Basic text analysis available, full LLM integration pending"},
            },
        }

    except Exception as e:
        return {"status": "unhealthy", "service": "incident-extraction", "timestamp": time.time(), "error": str(e)}
