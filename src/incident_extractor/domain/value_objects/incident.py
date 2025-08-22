"""Incident-related value objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import pytz
import structlog
from babel.dates import parse_date

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class IncidentDateTime:
    """Value object representing incident date and time with Brazilian locale support."""

    dt: datetime

    def __post_init__(self) -> None:
        """Validate the datetime is timezone-aware."""
        if self.dt.tzinfo is None:
            raise ValueError("IncidentDateTime must be timezone-aware")

    @classmethod
    def now(cls) -> IncidentDateTime:
        """Create IncidentDateTime for current time in Brazilian timezone."""
        return cls(dt=datetime.now(pytz.timezone("America/Sao_Paulo")))

    @classmethod
    def from_string(cls, date_str: str) -> IncidentDateTime:
        """Create IncidentDateTime from Brazilian Portuguese string.

        Supports various formats including:
        - Absolute dates: "15/03/2024", "15/03/2024 14:30"
        - Relative dates: "hoje", "ontem", "segunda passada"
        - Time expressions: "14:30", "2 horas atrás"
        """
        if not date_str or not date_str.strip():
            raise ValueError("Date string cannot be empty")

        date_str = date_str.strip()
        br_tz = pytz.timezone("America/Sao_Paulo")
        now = datetime.now(br_tz)

        # Handle relative date expressions
        relative_dates = {
            "hoje": 0,
            "ontem": -1,
            "anteontem": -2,
            "segunda passada": -7,  # Approximate
            "semana passada": -7,
            "mês passado": -30,
        }

        date_str_lower = date_str.lower()
        for relative, days_offset in relative_dates.items():
            if relative in date_str_lower:
                target_date = now + timedelta(days=days_offset)
                return cls(dt=target_date)

        # Handle time-only expressions (assume today)
        if ":" in date_str and "/" not in date_str:
            try:
                time_part = date_str.strip()
                hour, minute = map(int, time_part.split(":"))
                target_date = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                return cls(dt=target_date)
            except (ValueError, IndexError):
                pass

        # Handle Brazilian date formats with Babel
        try:
            # Try parsing with Babel for Brazilian locale
            parsed_date = parse_date(date_str, locale="pt_BR")
            if parsed_date:
                # Convert to datetime and add Brazilian timezone
                dt = datetime.combine(parsed_date, datetime.min.time())
                dt = br_tz.localize(dt)
                return cls(dt=dt)
        except Exception:
            pass

        # Handle DD/MM/YYYY format
        try:
            if "/" in date_str:
                parts = date_str.split()
                date_part = parts[0]

                if date_part.count("/") == 2:
                    day, month, year = map(int, date_part.split("/"))
                    dt = datetime(year, month, day)

                    # Handle time part if present
                    if len(parts) > 1 and ":" in parts[1]:
                        time_part = parts[1]
                        hour, minute = map(int, time_part.split(":"))
                        dt = dt.replace(hour=hour, minute=minute)

                    dt = br_tz.localize(dt)
                    return cls(dt=dt)
        except (ValueError, IndexError):
            pass

        # Fallback: assume current time if all parsing fails
        logger.warning("Could not parse date string, using current time", date_str=date_str)
        return cls.now()

    def to_datetime(self) -> datetime:
        """Get the underlying datetime object."""
        return self.dt

    def to_iso(self) -> str:
        """Convert to ISO format string."""
        return self.dt.isoformat()

    def to_brazilian_format(self) -> str:
        """Format as Brazilian standard (DD/MM/YYYY HH:MM)."""
        return self.dt.strftime("%d/%m/%Y %H:%M")

    def __str__(self) -> str:
        """String representation in Brazilian format."""
        return self.to_brazilian_format()


@dataclass(frozen=True)
class IncidentExtractionResult:
    """Value object representing the result of incident data extraction."""

    success: bool
    incident_data: dict[str, Any] | None
    confidence_score: float
    extraction_time_ms: int
    errors: list[str]
    provider_used: str | None = None
    raw_response: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate the extraction result."""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")

        if self.extraction_time_ms < 0:
            raise ValueError("Extraction time cannot be negative")

        if self.success and self.incident_data is None:
            raise ValueError("Successful extraction must have incident data")

    @classmethod
    def success_result(
        cls,
        incident_data: dict[str, Any],
        confidence_score: float,
        extraction_time_ms: int,
        provider_used: str | None = None,
        raw_response: dict[str, Any] | None = None,
    ) -> IncidentExtractionResult:
        """Create a successful extraction result."""
        return cls(
            success=True,
            incident_data=incident_data,
            confidence_score=confidence_score,
            extraction_time_ms=extraction_time_ms,
            errors=[],
            provider_used=provider_used,
            raw_response=raw_response,
        )

    @classmethod
    def failure_result(
        cls,
        errors: list[str],
        confidence_score: float = 0.0,
        extraction_time_ms: int = 0,
        provider_used: str | None = None,
        raw_response: dict[str, Any] | None = None,
    ) -> IncidentExtractionResult:
        """Create a failed extraction result."""
        return cls(
            success=False,
            incident_data=None,
            confidence_score=confidence_score,
            extraction_time_ms=extraction_time_ms,
            errors=errors,
            provider_used=provider_used,
            raw_response=raw_response,
        )
