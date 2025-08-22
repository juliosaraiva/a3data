"""Application service interface for incident extraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..dtos.incident_dtos import (
    ExtractIncidentRequest,
    ExtractIncidentResponse,
)


class IncidentExtractionServiceInterface(ABC):
    """Interface for application-level incident extraction service."""

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def get_processing_status(self, processing_id: str) -> dict[str, Any] | None:
        """
        Get processing status for async operations.

        Args:
            processing_id: Processing identifier

        Returns:
            Status information or None if not found
        """
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """
        Check health of extraction service and dependencies.

        Returns:
            Health status information
        """
        pass
