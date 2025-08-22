"""Use case for extracting incidents from text."""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any

import structlog

from ...core.exceptions import ApplicationError
from ...domain.entities.incident import Incident
from ...domain.events.incident_events import (
    IncidentEnriched,
    IncidentExtracted,
    IncidentProcessingFailed,
    IncidentValidated,
)
from ...domain.repositories.llm_repository import LLMRepository
from ...domain.services.incident_enrichment_service import IncidentEnrichmentService
from ...domain.services.incident_extraction_service import IncidentExtractionService
from ...domain.services.incident_validation_service import IncidentValidationService
from ..dtos.incident_dtos import (
    ExtractIncidentRequest,
    ExtractIncidentResponse,
    IncidentEnrichmentResult,
    IncidentExtractionResult,
    IncidentValidationResult,
    ProcessingMetadata,
)
from ..interfaces.incident_service_interface import IncidentExtractionServiceInterface

logger = structlog.get_logger(__name__)


class ExtractIncidentUseCase(IncidentExtractionServiceInterface):
    """
    Use case for extracting incident information from text.

    This orchestrates the domain services to perform extraction, validation,
    and enrichment following the Clean Architecture principles.
    """

    def __init__(
        self,
        extraction_service: IncidentExtractionService,
        validation_service: IncidentValidationService,
        enrichment_service: IncidentEnrichmentService,
        llm_repository: LLMRepository,
    ) -> None:
        """
        Initialize the use case with required services.

        Args:
            extraction_service: Domain service for incident extraction
            validation_service: Domain service for incident validation
            enrichment_service: Domain service for incident enrichment
            llm_repository: Repository for LLM operations
        """
        self._extraction_service = extraction_service
        self._validation_service = validation_service
        self._enrichment_service = enrichment_service
        self._llm_repository = llm_repository
        self._processing_status: dict[str, dict[str, Any]] = {}

    async def extract_incident(
        self, request: ExtractIncidentRequest, processing_id: str | None = None, context: dict[str, Any] | None = None
    ) -> ExtractIncidentResponse:
        """
        Extract incident information from text.

        Args:
            request: Extraction request with text and parameters
            processing_id: Optional processing identifier for tracking
            context: Optional additional context for processing

        Returns:
            Complete extraction response with incident data and metadata

        Raises:
            ApplicationError: If extraction fails due to application logic
            ValidationError: If request validation fails
            InfrastructureError: If external services fail
        """
        start_time = time.time()
        processing_id = processing_id or str(uuid.uuid4())

        logger.info(
            "Starting incident extraction",
            processing_id=processing_id,
            text_length=len(request.text),
            extraction_mode=request.extraction_mode,
            validation_level=request.validation_level,
        )

        # Update processing status
        self._processing_status[processing_id] = {
            "status": "processing",
            "step": "initialization",
            "started_at": datetime.now().isoformat(),
            "progress": 0.0,
        }

        try:
            # Step 1: Validate request
            await self.validate_extraction_request(request)
            self._processing_status[processing_id]["step"] = "validation_complete"
            self._processing_status[processing_id]["progress"] = 0.1

            # Step 2: Extract incident data
            extraction_result = await self._extract_incident_data(request, processing_id, context)

            self._processing_status[processing_id]["step"] = "extraction_complete"
            self._processing_status[processing_id]["progress"] = 0.5

            if not extraction_result.success:
                return ExtractIncidentResponse.from_error(
                    error_message="Extraction failed",
                    extraction_result=extraction_result,
                    metadata=self._create_metadata(processing_id, start_time),
                )

            # Step 3: Create incident entity
            try:
                incident = await self._create_incident_from_data(extraction_result.incident_data, processing_id)

                # Publish extraction event
                event = IncidentExtracted(
                    incident_id=incident.id,
                    extracted_data=extraction_result.incident_data,
                    confidence_score=extraction_result.confidence_score,
                    processing_id=processing_id,
                )
                await self._publish_event(event)

            except Exception as e:
                logger.error("Failed to create incident entity", processing_id=processing_id, error=str(e), exc_info=True)
                return ExtractIncidentResponse.from_error(
                    error_message=f"Failed to create incident: {str(e)}",
                    extraction_result=extraction_result,
                    metadata=self._create_metadata(processing_id, start_time),
                )

            self._processing_status[processing_id]["step"] = "entity_creation_complete"
            self._processing_status[processing_id]["progress"] = 0.6

            # Step 4: Validate incident
            validation_result = await self._validate_incident(incident, request.validation_level, processing_id)

            self._processing_status[processing_id]["step"] = "validation_complete"
            self._processing_status[processing_id]["progress"] = 0.8

            # Step 5: Enrich data (if requested)
            enrichment_result = None
            if request.enrich_data:
                incident, enrichment_result = await self._enrich_incident(incident, processing_id)
                self._processing_status[processing_id]["step"] = "enrichment_complete"
                self._processing_status[processing_id]["progress"] = 0.9

            # Step 6: Create response
            total_time = int((time.time() - start_time) * 1000)
            metadata = ProcessingMetadata(
                total_processing_time_ms=total_time,
                processed_at=datetime.now(),
                processing_id=processing_id,
                llm_provider=await self._get_llm_provider(),
                model_version=await self._get_model_version(),
            )

            # Update final status
            self._processing_status[processing_id] = {
                "status": "completed",
                "step": "finished",
                "completed_at": datetime.now().isoformat(),
                "progress": 1.0,
                "total_time_ms": total_time,
            }

            response = ExtractIncidentResponse.from_incident(
                incident=incident,
                extraction_result=extraction_result,
                validation_result=validation_result,
                metadata=metadata,
                enrichment_result=enrichment_result,
            )

            logger.info(
                "Incident extraction completed successfully",
                processing_id=processing_id,
                total_time_ms=total_time,
                confidence_score=incident.confidence_score,
            )

            return response

        except Exception as e:
            # Handle any unexpected errors
            error_msg = f"Unexpected error during extraction: {str(e)}"
            logger.error("Extraction failed with unexpected error", processing_id=processing_id, error=str(e), exc_info=True)

            # Publish failure event
            failure_event = IncidentProcessingFailed(
                processing_id=processing_id, error_message=error_msg, error_type=type(e).__name__
            )
            await self._publish_event(failure_event)

            # Update status
            self._processing_status[processing_id] = {
                "status": "failed",
                "step": "error",
                "error": error_msg,
                "failed_at": datetime.now().isoformat(),
            }

            return ExtractIncidentResponse.from_error(
                error_message=error_msg, metadata=self._create_metadata(processing_id, start_time)
            )

    async def validate_extraction_request(self, request: ExtractIncidentRequest) -> bool:
        """
        Validate extraction request parameters.

        Args:
            request: Request to validate

        Returns:
            True if request is valid

        Raises:
            ValidationError: If request is invalid
        """
        try:
            # Pydantic validation happens automatically
            # Additional business validation here
            if len(request.text.strip()) == 0:
                raise ApplicationError(
                    message="Text cannot be empty", error_code="EMPTY_TEXT", details={"text_length": len(request.text)}
                )

            # Check if text is too short for meaningful extraction
            if len(request.text.strip()) < 10:
                raise ApplicationError(
                    message="Text too short for meaningful extraction",
                    error_code="TEXT_TOO_SHORT",
                    details={"text_length": len(request.text.strip())},
                )

            # Validate context if provided
            if request.context:
                if not isinstance(request.context, dict):
                    raise ApplicationError(
                        message="Context must be a dictionary",
                        error_code="INVALID_CONTEXT_TYPE",
                        details={"context_type": type(request.context).__name__},
                    )

            return True

        except Exception as e:
            logger.error(
                "Request validation failed", error=str(e), text_length=len(request.text), extraction_mode=request.extraction_mode
            )
            raise

    async def get_processing_status(self, processing_id: str) -> dict[str, Any] | None:
        """
        Get processing status for async operations.

        Args:
            processing_id: Processing identifier

        Returns:
            Status information or None if not found
        """
        return self._processing_status.get(processing_id)

    async def health_check(self) -> dict[str, Any]:
        """
        Check health of extraction service and dependencies.

        Returns:
            Health status information
        """
        try:
            start_time = time.time()

            # Check LLM repository health
            llm_healthy = await self._llm_repository.health_check()

            # Check domain services
            extraction_healthy = await self._extraction_service.health_check()
            validation_healthy = await self._validation_service.health_check()
            enrichment_healthy = await self._enrichment_service.health_check()

            response_time = int((time.time() - start_time) * 1000)

            overall_healthy = all([llm_healthy, extraction_healthy, validation_healthy, enrichment_healthy])

            return {
                "healthy": overall_healthy,
                "response_time_ms": response_time,
                "components": {
                    "llm_repository": llm_healthy,
                    "extraction_service": extraction_healthy,
                    "validation_service": validation_healthy,
                    "enrichment_service": enrichment_healthy,
                },
                "active_processes": len(self._processing_status),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error("Health check failed", error=str(e), exc_info=True)
            return {"healthy": False, "error": str(e), "timestamp": datetime.now().isoformat()}

    # Private helper methods

    async def _extract_incident_data(
        self, request: ExtractIncidentRequest, processing_id: str, context: dict[str, Any] | None = None
    ) -> IncidentExtractionResult:
        """Extract incident data using domain service."""
        try:
            start_time = time.time()

            # Merge request context with additional context
            extraction_context = {
                **(request.context or {}),
                **(context or {}),
                "processing_id": processing_id,
                "extraction_mode": request.extraction_mode,
            }

            # Use domain service for extraction
            incident_data = await self._extraction_service.extract_from_text(text=request.text, context=extraction_context)

            extraction_time = int((time.time() - start_time) * 1000)

            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(incident_data)

            return IncidentExtractionResult(
                success=True,
                incident_data=incident_data,
                confidence_score=confidence_score,
                extraction_time_ms=extraction_time,
                errors=[],
            )

        except Exception as e:
            extraction_time = int((time.time() - start_time) * 1000)
            logger.error("Incident data extraction failed", processing_id=processing_id, error=str(e), exc_info=True)

            return IncidentExtractionResult(
                success=False, incident_data=None, confidence_score=0.0, extraction_time_ms=extraction_time, errors=[str(e)]
            )

    async def _create_incident_from_data(self, incident_data: dict[str, Any], processing_id: str) -> Incident:
        """Create incident entity from extracted data."""
        try:
            return Incident.from_extracted_data(incident_data)
        except Exception as e:
            logger.error(
                "Failed to create incident from data",
                processing_id=processing_id,
                incident_data=incident_data,
                error=str(e),
                exc_info=True,
            )
            raise ApplicationError(
                message=f"Failed to create incident entity: {str(e)}",
                error_code="INCIDENT_CREATION_FAILED",
                details={"incident_data": incident_data},
            ) from e

    async def _validate_incident(self, incident: Incident, validation_level: str, processing_id: str) -> IncidentValidationResult:
        """Validate incident using domain service."""
        try:
            start_time = time.time()

            validation_result = await self._validation_service.validate_incident(
                incident=incident, validation_level=validation_level
            )

            validation_time = int((time.time() - start_time) * 1000)

            # Publish validation event
            event = IncidentValidated(
                incident_id=incident.id,
                is_valid=validation_result.is_valid,
                quality_score=validation_result.quality_score,
                validation_errors=validation_result.validation_errors,
                processing_id=processing_id,
            )
            await self._publish_event(event)

            return IncidentValidationResult(
                is_valid=validation_result.is_valid,
                validation_errors=validation_result.validation_errors,
                quality_score=validation_result.quality_score,
                completeness_score=validation_result.completeness_score,
                validation_time_ms=validation_time,
            )

        except Exception as e:
            validation_time = int((time.time() - start_time) * 1000)
            logger.error(
                "Incident validation failed",
                processing_id=processing_id,
                incident_id=str(incident.id),
                error=str(e),
                exc_info=True,
            )

            return IncidentValidationResult(
                is_valid=False,
                validation_errors=[str(e)],
                quality_score=0.0,
                completeness_score=0.0,
                validation_time_ms=validation_time,
            )

    async def _enrich_incident(self, incident: Incident, processing_id: str) -> tuple[Incident, IncidentEnrichmentResult]:
        """Enrich incident using domain service."""
        try:
            start_time = time.time()

            enrichment_result = await self._enrichment_service.enrich_incident(incident=incident)

            enrichment_time = int((time.time() - start_time) * 1000)

            # Publish enrichment event
            event = IncidentEnriched(
                incident_id=incident.id,
                enriched_fields=enrichment_result.enriched_fields,
                confidence_improvements=enrichment_result.confidence_improvements,
                processing_id=processing_id,
            )
            await self._publish_event(event)

            return enrichment_result.enriched_incident, IncidentEnrichmentResult(
                enriched=enrichment_result.was_enriched,
                enrichment_fields=enrichment_result.enriched_fields,
                confidence_improvements=enrichment_result.confidence_improvements,
                enrichment_time_ms=enrichment_time,
                errors=[],
            )

        except Exception as e:
            enrichment_time = int((time.time() - start_time) * 1000)
            logger.error(
                "Incident enrichment failed",
                processing_id=processing_id,
                incident_id=str(incident.id),
                error=str(e),
                exc_info=True,
            )

            return incident, IncidentEnrichmentResult(
                enriched=False,
                enrichment_fields=[],
                confidence_improvements={},
                enrichment_time_ms=enrichment_time,
                errors=[str(e)],
            )

    def _calculate_confidence_score(self, incident_data: dict[str, Any] | None) -> float:
        """Calculate confidence score based on extracted data completeness."""
        if not incident_data:
            return 0.0

        # Base score for having any data
        score = 0.1

        # Key fields and their weights
        field_weights = {
            "title": 0.2,
            "description": 0.2,
            "datetime": 0.15,
            "location": 0.15,
            "severity": 0.1,
            "incident_type": 0.1,
            "involved_parties": 0.1,
        }

        for field, weight in field_weights.items():
            if field in incident_data and incident_data[field]:
                score += weight

        return min(score, 1.0)

    def _create_metadata(self, processing_id: str, start_time: float) -> ProcessingMetadata:
        """Create processing metadata."""
        return ProcessingMetadata(
            total_processing_time_ms=int((time.time() - start_time) * 1000),
            processed_at=datetime.now(),
            processing_id=processing_id,
            llm_provider="unknown",  # Will be updated by actual implementation
        )

    async def _get_llm_provider(self) -> str:
        """Get current LLM provider name."""
        try:
            return await self._llm_repository.get_provider_name()
        except Exception:
            return "unknown"

    async def _get_model_version(self) -> str | None:
        """Get current model version."""
        try:
            return await self._llm_repository.get_model_version()
        except Exception:
            return None

    async def _publish_event(self, event) -> None:
        """Publish domain event."""
        try:
            # In a real implementation, this would publish to an event bus
            # For now, we just log the event
            logger.info("Domain event published", event_type=type(event).__name__, event_data=event.__dict__)
        except Exception as e:
            logger.error("Failed to publish event", event_type=type(event).__name__, error=str(e), exc_info=True)
