"""Abstract repository interface for incident persistence operations."""

from abc import ABC, abstractmethod
from typing import Any

from incident_extractor.core.exceptions.domain import DomainError
from incident_extractor.domain.entities.incident import Incident


class IncidentRepositoryError(DomainError):
    """Base exception for incident repository errors."""

    def __init__(self, message: str, error_code: str = "INCIDENT_REPO_ERROR", details: dict[str, Any] | None = None):
        super().__init__(message, error_code, details)


class IncidentNotFoundError(IncidentRepositoryError):
    """Exception raised when incident is not found."""

    def __init__(self, incident_id: str, details: dict[str, Any] | None = None):
        message = f"Incident with ID '{incident_id}' not found"
        super().__init__(message, "INCIDENT_NOT_FOUND", details)


class IncidentRepository(ABC):
    """
    Abstract repository interface for incident persistence operations.

    This interface defines the contract for incident storage implementations,
    enabling dependency inversion and testability.
    """

    @abstractmethod
    async def save(self, incident: Incident) -> str:
        """Save an incident and return its ID.

        Args:
            incident: The incident entity to save

        Returns:
            The unique identifier of the saved incident

        Raises:
            IncidentRepositoryError: When save operation fails
        """
        pass

    @abstractmethod
    async def find_by_id(self, incident_id: str) -> Incident | None:
        """Find an incident by its ID.

        Args:
            incident_id: The unique identifier of the incident

        Returns:
            The incident entity if found, None otherwise

        Raises:
            IncidentRepositoryError: When find operation fails
        """
        pass

    @abstractmethod
    async def find_by_criteria(self, limit: int = 100, offset: int = 0, **criteria: Any) -> list[Incident]:
        """Find incidents matching the given criteria.

        Args:
            limit: Maximum number of incidents to return
            offset: Number of incidents to skip (for pagination)
            **criteria: Search criteria (e.g., date_range, location, type)

        Returns:
            List of incidents matching the criteria

        Raises:
            IncidentRepositoryError: When find operation fails
        """
        pass

    @abstractmethod
    async def delete_by_id(self, incident_id: str) -> bool:
        """Delete an incident by its ID.

        Args:
            incident_id: The unique identifier of the incident

        Returns:
            True if incident was deleted, False if not found

        Raises:
            IncidentRepositoryError: When delete operation fails
        """
        pass

    @abstractmethod
    async def count(self, **criteria: Any) -> int:
        """Count incidents matching the given criteria.

        Args:
            **criteria: Search criteria

        Returns:
            Number of incidents matching the criteria

        Raises:
            IncidentRepositoryError: When count operation fails
        """
        pass
