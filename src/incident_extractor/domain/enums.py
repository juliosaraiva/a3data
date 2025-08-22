"""Domain enums for incident classification."""

from enum import Enum


class IncidentSeverity(Enum):
    """Enumeration of incident severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentType(Enum):
    """Enumeration of incident types."""

    TRAFFIC_ACCIDENT = "traffic_accident"
    FIRE = "fire"
    FLOOD = "flood"
    THEFT = "theft"
    VANDALISM = "vandalism"
    MEDICAL_EMERGENCY = "medical_emergency"
    NATURAL_DISASTER = "natural_disaster"
    OTHER = "other"
