"""Domain events for incident processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import DomainEvent


@dataclass(frozen=True)
class IncidentExtracted(DomainEvent):
    """Event raised when incident information is successfully extracted."""

    incident_id: str = ""
    extracted_data: dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0
    processing_id: str = ""


@dataclass(frozen=True)
class IncidentValidated(DomainEvent):
    """Event raised when incident validation is completed."""

    incident_id: str = ""
    is_valid: bool = False
    quality_score: float = 0.0
    validation_errors: list[str] = field(default_factory=list)
    processing_id: str = ""


@dataclass(frozen=True)
class IncidentEnriched(DomainEvent):
    """Event raised when incident enrichment is completed."""

    incident_id: str = ""
    enriched_fields: list[str] = field(default_factory=list)
    confidence_improvements: dict[str, float] = field(default_factory=dict)
    processing_id: str = ""


@dataclass(frozen=True)
class IncidentProcessingFailed(DomainEvent):
    """Event raised when incident processing fails."""

    processing_id: str = ""
    error_message: str = ""
    error_type: str = ""
