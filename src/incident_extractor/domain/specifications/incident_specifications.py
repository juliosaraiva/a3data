"""Business rule specifications for incident entities."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytz

from incident_extractor.domain.entities.incident import Incident

from .base import Specification


class IncidentCompletenessSpecification(Specification[Incident]):
    """Specification that checks if an incident has sufficient completeness."""

    def __init__(self, minimum_score: float = 0.5):
        self._minimum_score = minimum_score

    def is_satisfied_by(self, incident: Incident) -> bool:
        """Check if incident meets minimum completeness requirements."""
        return incident.extraction_score >= self._minimum_score

    def why_not_satisfied(self, incident: Incident) -> str | None:
        """Return reason if completeness requirement is not met."""
        if self.is_satisfied_by(incident):
            return None

        return (
            f"Incident completeness score ({incident.extraction_score:.1%}) "
            f"is below minimum requirement ({self._minimum_score:.1%})"
        )


class ValidIncidentDateSpecification(Specification[Incident]):
    """Specification that validates incident date business rules."""

    def __init__(self, max_future_days: int = 7, max_past_days: int = 365):
        self._max_future_days = max_future_days
        self._max_past_days = max_past_days

    def is_satisfied_by(self, incident: Incident) -> bool:
        """Check if incident date is within acceptable business range."""
        if not incident.data_ocorrencia:
            # Incident without date is acceptable
            return True

        now = datetime.now(pytz.timezone("America/Sao_Paulo"))
        incident_dt = incident.data_ocorrencia.to_datetime()

        # Check future limit
        max_future = now + timedelta(days=self._max_future_days)
        if incident_dt > max_future:
            return False

        # Check past limit
        min_past = now - timedelta(days=self._max_past_days)
        if incident_dt < min_past:
            return False

        return True

    def why_not_satisfied(self, incident: Incident) -> str | None:
        """Return reason if date validation fails."""
        if not incident.data_ocorrencia or self.is_satisfied_by(incident):
            return None

        now = datetime.now(pytz.timezone("America/Sao_Paulo"))
        incident_dt = incident.data_ocorrencia.to_datetime()

        max_future = now + timedelta(days=self._max_future_days)
        if incident_dt > max_future:
            return (
                f"Incident date ({incident.data_ocorrencia.to_iso()}) is too far in the future "
                f"(maximum {self._max_future_days} days from now)"
            )

        min_past = now - timedelta(days=self._max_past_days)
        if incident_dt < min_past:
            return f"Incident date ({incident.data_ocorrencia.to_iso()}) is too old (maximum {self._max_past_days} days ago)"

        return None


class ValidIncidentLocationSpecification(Specification[Incident]):
    """Specification that validates incident location business rules."""

    def __init__(self, minimum_location_length: int = 3):
        self._minimum_location_length = minimum_location_length

    def is_satisfied_by(self, incident: Incident) -> bool:
        """Check if incident location meets business requirements."""
        if not incident.local:
            # Incident without location is acceptable
            return True

        # Check minimum length requirement
        if len(incident.local.normalized) < self._minimum_location_length:
            return False

        # Business rule: Location should not be overly generic
        generic_locations = [
            "sistema",
            "aplicação",
            "servidor",
            "rede",
            "internet",
            "computador",
            "máquina",
            "equipamento",
            "local",
            "lugar",
        ]

        location_lower = incident.local.normalized.lower()

        # If location is only generic terms, it's not valid
        if any(generic in location_lower and len(incident.local.normalized.split()) <= 2 for generic in generic_locations):
            return False

        return True

    def why_not_satisfied(self, incident: Incident) -> str | None:
        """Return reason if location validation fails."""
        if not incident.local or self.is_satisfied_by(incident):
            return None

        if len(incident.local.normalized) < self._minimum_location_length:
            return (
                f"Location '{incident.local.normalized}' is too short "
                f"(minimum {self._minimum_location_length} characters required)"
            )

        generic_locations = [
            "sistema",
            "aplicação",
            "servidor",
            "rede",
            "internet",
            "computador",
            "máquina",
            "equipamento",
            "local",
            "lugar",
        ]

        location_lower = incident.local.normalized.lower()

        for generic in generic_locations:
            if generic in location_lower and len(incident.local.normalized.split()) <= 2:
                return f"Location '{incident.local.normalized}' is too generic, please provide more specific location information"

        return None


class HighQualityIncidentSpecification(Specification[Incident]):
    """Composite specification that defines a high-quality incident."""

    def __init__(self):
        self._completeness_spec = IncidentCompletenessSpecification(minimum_score=0.75)
        self._date_spec = ValidIncidentDateSpecification()
        self._location_spec = ValidIncidentLocationSpecification()
        self._quality_spec = self._completeness_spec.and_(self._date_spec).and_(self._location_spec)

    def is_satisfied_by(self, incident: Incident) -> bool:
        """Check if incident meets high quality standards."""
        # Base quality check
        if not self._quality_spec.is_satisfied_by(incident):
            return False

        # Additional high-quality requirements
        if not self._has_meaningful_description(incident):
            return False

        if not self._has_coherent_information(incident):
            return False

        return True

    def why_not_satisfied(self, incident: Incident) -> str | None:
        """Return reason if high quality requirements are not met."""
        if self.is_satisfied_by(incident):
            return None

        # Check base quality requirements first
        base_reason = self._quality_spec.why_not_satisfied(incident)
        if base_reason:
            return f"Base quality requirements not met: {base_reason}"

        # Check additional requirements
        if not self._has_meaningful_description(incident):
            return "Description lacks meaningful content or detail"

        if not self._has_coherent_information(incident):
            return "Extracted information appears inconsistent or incoherent"

        return None

    def _has_meaningful_description(self, incident: Incident) -> bool:
        """Check if incident has meaningful description content."""
        description = incident.raw_description.strip()

        # Minimum length requirement
        if len(description) < 20:
            return False

        # Check for trivial content
        trivial_patterns = [
            "erro",
            "problema",
            "não funciona",
            "quebrado",
            "parou",
            "não carrega",
            "deu erro",
            "não abre",
            "travou",
        ]

        words = description.lower().split()

        # If description is mostly trivial words, it's not meaningful
        trivial_word_count = sum(1 for word in words if any(pattern in word for pattern in trivial_patterns))

        # More than 60% trivial words indicates low quality
        if len(words) > 0 and (trivial_word_count / len(words)) > 0.6:
            return False

        return True

    def _has_coherent_information(self, incident: Incident) -> bool:
        """Check if extracted information is coherent with description."""
        # If we have incident type, check it's coherent with description
        if incident.tipo_incidente:
            type_keywords = {
                "Falha de Sistema": ["falha", "erro", "sistema", "parou", "indisponível"],
                "Problema de Rede": ["rede", "conexão", "internet", "wi-fi"],
                "Erro de Aplicação": ["aplicação", "app", "software"],
                "Lentidão de Sistema": ["lento", "devagar", "demora", "performance"],
                "Problema de Segurança": ["segurança", "hack", "vírus", "invasão"],
            }

            description_lower = incident.raw_description.lower()

            if incident.tipo_incidente in type_keywords:
                keywords = type_keywords[incident.tipo_incidente]
                # At least one keyword should match
                if not any(keyword in description_lower for keyword in keywords):
                    return False

        # If we have location and it's very generic but description has specific details
        if incident.local:
            if (
                len(incident.local.normalized) < 10
                and len(incident.raw_description) > 100
                and any(word in incident.raw_description.lower() for word in ["sala", "andar", "prédio", "endereço"])
            ):
                return False

        return True
