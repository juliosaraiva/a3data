"""Domain service for incident validation business rules."""

from __future__ import annotations

from typing import Any

import structlog

from incident_extractor.core.exceptions.domain import DomainError
from incident_extractor.domain.entities.incident import Incident

logger = structlog.get_logger(__name__)


class IncidentValidationError(DomainError):
    """Exception raised when incident validation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, "INCIDENT_VALIDATION_ERROR", details)


class ValidationResult:
    """Result of incident validation containing details about validation status."""

    def __init__(
        self, is_valid: bool, violations: list[str] | None = None, warnings: list[str] | None = None, score: float = 0.0
    ):
        self.is_valid = is_valid
        self.violations = violations or []
        self.warnings = warnings or []
        self.score = score

    def add_violation(self, violation: str) -> None:
        """Add a validation violation."""
        self.violations.append(violation)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add a validation warning."""
        self.warnings.append(warning)


class IncidentValidationService:
    """
    Domain service responsible for validating incidents against business rules.

    This service implements comprehensive validation logic that goes beyond
    simple field validation to enforce complex business rules and constraints.
    """

    def __init__(self):
        self._logger = logger.bind(service="IncidentValidationService")

    def validate_incident(self, incident: Incident) -> ValidationResult:
        """Validate incident against all business rules.

        Args:
            incident: The incident entity to validate

        Returns:
            ValidationResult with validation status and details
        """
        self._logger.info("Starting incident validation")

        result = ValidationResult(is_valid=True)

        # Apply all validation rules
        self._validate_basic_requirements(incident, result)
        self._validate_date_consistency(incident, result)
        self._validate_location_specificity(incident, result)
        self._validate_incident_type_coherence(incident, result)
        self._validate_impact_assessment(incident, result)
        self._validate_completeness_score(incident, result)

        # Calculate overall validation score
        result.score = self._calculate_validation_score(incident, result)

        self._logger.info(
            "Incident validation completed",
            is_valid=result.is_valid,
            violations_count=len(result.violations),
            warnings_count=len(result.warnings),
            validation_score=result.score,
        )

        return result

    def _validate_basic_requirements(self, incident: Incident, result: ValidationResult) -> None:
        """Validate basic incident requirements."""
        # Business rule: Raw description must exist and be meaningful
        if not incident.raw_description or len(incident.raw_description.strip()) < 10:
            result.add_violation("Raw description must be at least 10 characters long")

        # Business rule: Description should not be too long
        if len(incident.raw_description) > 10000:
            result.add_violation("Raw description exceeds maximum length of 10,000 characters")

        # Business rule: Description should contain meaningful content
        if self._is_trivial_description(incident.raw_description):
            result.add_warning("Description appears to contain minimal meaningful information")

    def _validate_date_consistency(self, incident: Incident, result: ValidationResult) -> None:
        """Validate date-related business rules."""
        if incident.data_ocorrencia:
            # Business rule: Incident date should not be in the far future
            from datetime import datetime, timedelta

            import pytz

            now = datetime.now(pytz.timezone("America/Sao_Paulo"))
            max_future = now + timedelta(days=7)  # Allow up to 7 days in future for scheduled incidents

            incident_dt = incident.data_ocorrencia.to_datetime()

            if incident_dt > max_future:
                result.add_violation(f"Incident date {incident.data_ocorrencia.to_iso()} is too far in the future")

            # Business rule: Incident date should not be too old (beyond reasonable reporting period)
            min_past = now - timedelta(days=365)  # 1 year back is reasonable limit

            if incident_dt < min_past:
                result.add_warning(f"Incident date {incident.data_ocorrencia.to_iso()} is very old, please verify accuracy")

    def _validate_location_specificity(self, incident: Incident, result: ValidationResult) -> None:
        """Validate location specificity business rules."""
        if incident.local:
            # Business rule: Location should provide meaningful information
            if len(incident.local.normalized) < 3:
                result.add_violation("Location information is too vague or short")

            # Business rule: Prefer specific locations over generic ones
            generic_locations = ["sistema", "aplicação", "servidor", "rede", "internet", "computador", "máquina", "equipamento"]

            if any(generic in incident.local.normalized.lower() for generic in generic_locations):
                result.add_warning("Location appears to be generic, consider providing more specific information")

            # Business rule: Brazilian locations should be recognizable
            if incident.local.city is None and incident.local.state is None:
                if incident.local.is_likely_brazilian_location():
                    result.add_warning("Location appears to be Brazilian but city/state could not be identified")

    def _validate_incident_type_coherence(self, incident: Incident, result: ValidationResult) -> None:
        """Validate incident type coherence with description."""
        if incident.tipo_incidente:
            # Business rule: Incident type should be coherent with description content
            type_keywords = {
                "Falha de Sistema": ["falha", "erro", "quebrou", "parou", "indisponível"],
                "Problema de Rede": ["rede", "conexão", "internet", "wi-fi", "cabo"],
                "Erro de Aplicação": ["aplicação", "app", "software", "programa"],
                "Lentidão de Sistema": ["lento", "devagar", "demora", "performance"],
                "Problema de Segurança": ["segurança", "hack", "vírus", "invasão", "senha"],
            }

            description_lower = incident.raw_description.lower()

            if incident.tipo_incidente in type_keywords:
                keywords = type_keywords[incident.tipo_incidente]
                if not any(keyword in description_lower for keyword in keywords):
                    result.add_warning(f"Incident type '{incident.tipo_incidente}' may not match the content of the description")

    def _validate_impact_assessment(self, incident: Incident, result: ValidationResult) -> None:
        """Validate impact assessment business rules."""
        if incident.impacto:
            # Business rule: Impact should provide meaningful information
            if len(incident.impacto.strip()) < 5:
                result.add_warning("Impact description is very brief, consider providing more details")

            # Business rule: Impact should indicate severity or consequences
            impact_indicators = [
                "usuário",
                "cliente",
                "sistema",
                "processo",
                "produção",
                "receita",
                "dados",
                "segurança",
                "disponibilidade",
            ]

            impact_lower = incident.impacto.lower()
            has_impact_indicator = any(indicator in impact_lower for indicator in impact_indicators)

            if not has_impact_indicator:
                result.add_warning(
                    "Impact description might benefit from indicating affected users, systems, or business processes"
                )

    def _validate_completeness_score(self, incident: Incident, result: ValidationResult) -> None:
        """Validate incident completeness against business requirements."""
        completeness_score = incident.extraction_score

        # Business rule: Minimum completeness threshold for production incidents
        if completeness_score < 0.5:  # Less than 50% complete
            result.add_violation(f"Incident completeness score ({completeness_score:.1%}) is below minimum threshold of 50%")
        elif completeness_score < 0.75:  # Less than 75% complete
            result.add_warning(
                f"Incident completeness score ({completeness_score:.1%}) could be improved for better incident tracking"
            )

    def _is_trivial_description(self, description: str) -> bool:
        """Check if description contains only trivial information."""
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

        description_lower = description.lower().strip()

        # If description is mostly trivial patterns, it's not meaningful
        trivial_matches = sum(1 for pattern in trivial_patterns if pattern in description_lower)

        # If more than half the "content" is trivial patterns, flag as trivial
        return trivial_matches > 0 and len(description_lower.split()) < 10

    def _calculate_validation_score(self, incident: Incident, result: ValidationResult) -> float:
        """Calculate overall validation score based on completeness and violations."""
        base_score = incident.extraction_score

        # Penalty for violations (each violation reduces score)
        violation_penalty = len(result.violations) * 0.2

        # Minor penalty for warnings
        warning_penalty = len(result.warnings) * 0.05

        final_score = max(0.0, base_score - violation_penalty - warning_penalty)

        return min(1.0, final_score)
