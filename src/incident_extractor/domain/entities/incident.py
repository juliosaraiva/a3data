"""Core incident entity for the domain layer"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from incident_extractor.domain.value_objects import IncidentDateTime, Location

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class Incident:
    """Core incident entity representing extracted incident information.

    This entity encapsulates the business rules and invariants for incidents.
    It's immutable to ensure data integrity and thread safety.
    """

    # Original input - always required
    raw_description: str

    # Extracted fields - optional as extraction might not find all information
    data_ocorrencia: IncidentDateTime | None = None
    local: Location | None = None
    tipo_incidente: str | None = None
    impacto: str | None = None

    def __post_init__(self) -> None:
        """Validate business rules on entity creation"""
        if not self.raw_description or not self.raw_description.strip():
            raise ValueError("Raw description is required")

        # Validate description length (business rule: max 10,000 characters)
        if len(self.raw_description) > 10000:
            raise ValueError("Raw description must be at most 10,000 characters")

    def to_dict(self) -> dict[str, Any]:
        """Convert entity to dictionary representation for serialization"""
        return {
            "raw_description": self.raw_description,
            "data_ocorrencia": self.data_ocorrencia.to_iso() if self.data_ocorrencia else None,
            "local": self.local.to_dict() if self.local else None,
            "tipo_incidente": self.tipo_incidente,
            "impacto": self.impacto,
        }

    @property
    def is_complete(self) -> bool:
        """Check if all required fields are populated"""
        return all(
            [
                self.raw_description,
                self.data_ocorrencia is not None,
                self.local is not None,
                self.tipo_incidente is not None,
                self.impacto is not None,
            ]
        )

    @property
    def extraction_score(self) -> float:
        """Calculate completeness score based on extracted fields

        Returns:
            Score from 0.0 to 1.0 representing extraction completeness.
        """
        fields = [self.data_ocorrencia, self.local, self.tipo_incidente, self.impacto]
        populated_fields = sum(1 for field in fields if field is not None)
        return populated_fields / len(fields)

    def with_extracted_data(
        self,
        data_ocorrencia: IncidentDateTime | None = None,
        local: Location | None = None,
        tipo_incidente: str | None = None,
        impacto: str | None = None,
    ) -> Incident:
        """Create a new Incident instance with updated extracted data.

        Args:
            data_ocorrencia: New incident date/time
            local: New incident location
            tipo_incidente: New incident type
            impacto: New incident impact

        Returns:
            A new Incident instance with updated fields.
        """
        return Incident(
            raw_description=self.raw_description,
            data_ocorrencia=data_ocorrencia or self.data_ocorrencia,
            local=local or self.local,
            tipo_incidente=tipo_incidente or self.tipo_incidente,
            impacto=impacto or self.impacto,
        )
