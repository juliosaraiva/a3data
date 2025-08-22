"""Domain service for incident enrichment with additional context and metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from incident_extractor.core.exceptions.domain import DomainError
from incident_extractor.domain.entities.incident import Incident
from incident_extractor.domain.value_objects import IncidentDateTime, Location

logger = structlog.get_logger(__name__)


class IncidentEnrichmentError(DomainError):
    """Exception raised when incident enrichment fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, "INCIDENT_ENRICHMENT_ERROR", details)


@dataclass
class EnrichmentResult:
    """Result of incident enrichment."""

    enriched_incident: Incident
    was_enriched: bool
    enriched_fields: list[str] = field(default_factory=list)
    confidence_improvements: dict[str, float] = field(default_factory=dict)


class EnrichmentContext:
    """Context information for incident enrichment."""

    def __init__(self, confidence_level: float = 0.0, enrichment_source: str = "system", metadata: dict[str, Any] | None = None):
        self.confidence_level = confidence_level
        self.enrichment_source = enrichment_source
        self.metadata = metadata or {}


class IncidentEnrichmentService:
    """
    Domain service responsible for enriching incidents with additional context and metadata.

    This service applies business logic to enhance incident information with
    derived data, contextual information, and standardized classifications.
    """

    def __init__(self):
        self._logger = logger.bind(service="IncidentEnrichmentService")

    async def enrich_incident(self, incident: Incident) -> EnrichmentResult:
        """Enrich incident with additional context and standardized information.

        Args:
            incident: The incident entity to enrich

        Returns:
            Tuple of (enriched_incident, enrichment_context)
        """
        self._logger.info("Starting incident enrichment")

        context = EnrichmentContext()
        enriched_data = {}

        # Apply enrichment strategies
        self._enrich_temporal_context(incident, enriched_data, context)
        self._enrich_location_context(incident, enriched_data, context)
        self._enrich_incident_classification(incident, enriched_data, context)
        self._enrich_severity_assessment(incident, enriched_data, context)

        # Create enriched incident
        enriched_incident = incident.with_extracted_data(
            data_ocorrencia=enriched_data.get("data_ocorrencia", incident.data_ocorrencia),
            local=enriched_data.get("local", incident.local),
            tipo_incidente=enriched_data.get("tipo_incidente", incident.tipo_incidente),
            impacto=enriched_data.get("impacto", incident.impacto),
        )

        # Calculate overall confidence
        context.confidence_level = self._calculate_enrichment_confidence(incident, enriched_incident)

        self._logger.info(
            "Incident enrichment completed",
            confidence_level=context.confidence_level,
            enrichment_source=context.enrichment_source,
        )

        # Determine which fields were enriched
        enriched_fields = []
        confidence_improvements = {}

        if enriched_data.get("data_ocorrencia") and not incident.data_ocorrencia:
            enriched_fields.append("data_ocorrencia")
            confidence_improvements["data_ocorrencia"] = context.confidence_level

        if enriched_data.get("local") and not incident.local:
            enriched_fields.append("local")
            confidence_improvements["local"] = context.confidence_level

        if enriched_data.get("tipo_incidente") and not incident.tipo_incidente:
            enriched_fields.append("tipo_incidente")
            confidence_improvements["tipo_incidente"] = context.confidence_level

        if enriched_data.get("impacto") and not incident.impacto:
            enriched_fields.append("impacto")
            confidence_improvements["impacto"] = context.confidence_level

        return EnrichmentResult(
            enriched_incident=enriched_incident,
            was_enriched=len(enriched_fields) > 0,
            enriched_fields=enriched_fields,
            confidence_improvements=confidence_improvements,
        )

    async def health_check(self) -> bool:
        """Check the health of the enrichment service."""
        try:
            # Basic health check - could be expanded to check dependencies
            return True
        except Exception:
            return False

    def _enrich_temporal_context(self, incident: Incident, enriched_data: dict[str, Any], context: EnrichmentContext) -> None:
        """Enrich incident with temporal context and business rules."""
        if not incident.data_ocorrencia:
            # Business rule: Try to infer time context from description
            inferred_time = self._infer_time_from_description(incident.raw_description)
            if inferred_time:
                enriched_data["data_ocorrencia"] = inferred_time
                context.metadata["time_inferred"] = True
                context.metadata["inference_method"] = "description_analysis"
        else:
            # Business rule: Add business context to existing dates
            business_context = self._get_business_time_context(incident.data_ocorrencia)
            context.metadata.update(business_context)

    def _enrich_location_context(self, incident: Incident, enriched_data: dict[str, Any], context: EnrichmentContext) -> None:
        """Enrich incident with location context and geographical information."""
        if incident.local:
            # Business rule: Add geographical hierarchy and timezone info
            geo_context = self._get_geographical_context(incident.local)
            context.metadata.update(geo_context)

            # Business rule: Standardize location format if needed
            if not incident.local.city and not incident.local.state:
                enhanced_location = self._enhance_location_parsing(incident.local.raw)
                if enhanced_location and enhanced_location != incident.local:
                    enriched_data["local"] = enhanced_location
                    context.metadata["location_enhanced"] = True

    def _enrich_incident_classification(
        self, incident: Incident, enriched_data: dict[str, Any], context: EnrichmentContext
    ) -> None:
        """Enrich incident with standardized classification and categories."""
        # Business rule: Infer incident type from description if missing
        if not incident.tipo_incidente:
            inferred_type = self._infer_incident_type(incident.raw_description)
            if inferred_type:
                enriched_data["tipo_incidente"] = inferred_type
                context.metadata["type_inferred"] = True
                context.metadata["inference_confidence"] = self._get_type_inference_confidence(
                    incident.raw_description, inferred_type
                )

        # Business rule: Add incident subcategory and tags
        if incident.tipo_incidente or enriched_data.get("tipo_incidente"):
            incident_type = enriched_data.get("tipo_incidente", incident.tipo_incidente)
            subcategory = self._get_incident_subcategory(incident_type, incident.raw_description)
            if subcategory:
                context.metadata["subcategory"] = subcategory

            tags = self._generate_incident_tags(incident.raw_description, incident_type)
            if tags:
                context.metadata["tags"] = tags

    def _enrich_severity_assessment(self, incident: Incident, enriched_data: dict[str, Any], context: EnrichmentContext) -> None:
        """Enrich incident with severity assessment based on business rules."""
        severity = self._assess_incident_severity(incident)
        context.metadata["severity_assessment"] = severity

        # Business rule: Enhance impact description with severity context
        if incident.impacto:
            enhanced_impact = self._enhance_impact_description(incident.impacto, severity)
            if enhanced_impact != incident.impacto:
                enriched_data["impacto"] = enhanced_impact
                context.metadata["impact_enhanced"] = True

    def _infer_time_from_description(self, description: str) -> IncidentDateTime | None:
        """Infer time information from incident description."""
        time_indicators = {
            "agora": "now",
            "hoje": "today",
            "ontem": "yesterday",
            "manhã": "morning",
            "tarde": "afternoon",
            "noite": "evening",
            "madrugada": "dawn",
        }

        description_lower = description.lower()

        for indicator, time_type in time_indicators.items():
            if indicator in description_lower:
                try:
                    # Create approximate time based on indicator
                    if time_type == "now":
                        return IncidentDateTime.now()
                    elif time_type == "today":
                        return IncidentDateTime.from_string("hoje")
                    elif time_type == "yesterday":
                        return IncidentDateTime.from_string("ontem")
                except Exception:
                    continue

        return None

    def _get_business_time_context(self, incident_time: IncidentDateTime) -> dict[str, Any]:
        """Get business context for incident timing."""
        context = {}

        dt = incident_time.to_datetime()

        # Business hours classification
        hour = dt.hour
        if 6 <= hour < 12:
            context["business_period"] = "morning"
        elif 12 <= hour < 18:
            context["business_period"] = "afternoon"
        elif 18 <= hour < 22:
            context["business_period"] = "evening"
        else:
            context["business_period"] = "night"

        # Weekend/weekday classification
        weekday = dt.weekday()
        if weekday < 5:  # Monday = 0, Sunday = 6
            context["day_type"] = "weekday"
        else:
            context["day_type"] = "weekend"

        # Business hours flag
        context["is_business_hours"] = weekday < 5 and 8 <= hour < 18

        return context

    def _get_geographical_context(self, location: Location) -> dict[str, Any]:
        """Get geographical context for incident location."""
        context = {}

        if location.state:
            # Add timezone information based on Brazilian states
            timezone_mapping = {
                "AC": "America/Rio_Branco",  # Acre
                "AL": "America/Maceio",  # Alagoas
                "AP": "America/Belem",  # Amapá
                "AM": "America/Manaus",  # Amazonas
                "BA": "America/Bahia",  # Bahia
                "CE": "America/Fortaleza",  # Ceará
                "DF": "America/Sao_Paulo",  # Distrito Federal
                "ES": "America/Sao_Paulo",  # Espírito Santo
                "GO": "America/Sao_Paulo",  # Goiás
                "MA": "America/Fortaleza",  # Maranhão
                "MT": "America/Cuiaba",  # Mato Grosso
                "MS": "America/Campo_Grande",  # Mato Grosso do Sul
                "MG": "America/Sao_Paulo",  # Minas Gerais
                "PA": "America/Belem",  # Pará
                "PB": "America/Fortaleza",  # Paraíba
                "PR": "America/Sao_Paulo",  # Paraná
                "PE": "America/Recife",  # Pernambuco
                "PI": "America/Fortaleza",  # Piauí
                "RJ": "America/Sao_Paulo",  # Rio de Janeiro
                "RN": "America/Fortaleza",  # Rio Grande do Norte
                "RS": "America/Sao_Paulo",  # Rio Grande do Sul
                "RO": "America/Porto_Velho",  # Rondônia
                "RR": "America/Boa_Vista",  # Roraima
                "SC": "America/Sao_Paulo",  # Santa Catarina
                "SP": "America/Sao_Paulo",  # São Paulo
                "SE": "America/Maceio",  # Sergipe
                "TO": "America/Araguaina",  # Tocantins
            }

            context["timezone"] = timezone_mapping.get(location.state, "America/Sao_Paulo")
            context["region"] = self._get_brazilian_region(location.state)

        if location.is_likely_brazilian_location():
            context["country"] = "Brazil"
            context["country_code"] = "BR"

        return context

    def _get_brazilian_region(self, state: str) -> str:
        """Get Brazilian region for given state."""
        regions = {
            "Norte": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
            "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
            "Centro-Oeste": ["DF", "GO", "MT", "MS"],
            "Sudeste": ["ES", "MG", "RJ", "SP"],
            "Sul": ["PR", "RS", "SC"],
        }

        for region, states in regions.items():
            if state in states:
                return region

        return "Unknown"

    def _enhance_location_parsing(self, raw_location: str) -> Location | None:
        """Enhanced location parsing with business intelligence."""
        # Apply more sophisticated parsing for common Brazilian patterns
        try:
            enhanced_location = Location(raw_location)

            # If original parsing failed but we can apply business rules
            if not enhanced_location.city and not enhanced_location.state:
                # Try to extract from common Brazilian address patterns
                # This could be enhanced with external geocoding APIs
                pass

            return enhanced_location

        except Exception:
            return None

    def _infer_incident_type(self, description: str) -> str | None:
        """Infer incident type from description using business rules."""
        description_lower = description.lower()

        type_patterns = {
            "Falha de Sistema": [
                "sistema caiu",
                "sistema parou",
                "sistema indisponível",
                "falha do sistema",
                "erro interno",
                "server error",
                "500",
                "sistema fora do ar",
            ],
            "Problema de Rede": [
                "sem internet",
                "conexão perdida",
                "rede fora",
                "problemas de conectividade",
                "timeout",
                "não consegue conectar",
                "sem acesso à rede",
            ],
            "Erro de Aplicação": [
                "aplicação não abre",
                "erro na aplicação",
                "app crashou",
                "software travou",
                "erro de javascript",
                "página não carrega",
            ],
            "Lentidão de Sistema": [
                "sistema lento",
                "muito devagar",
                "performance ruim",
                "demora para carregar",
                "resposta lenta",
                "travando",
                "lentidão",
            ],
            "Problema de Segurança": [
                "vírus detectado",
                "possível invasão",
                "senha comprometida",
                "acesso não autorizado",
                "malware",
                "phishing",
                "segurança",
            ],
            "Erro de Usuário": ["não consigo", "como fazer", "não sei usar", "dúvida sobre", "tutorial", "não funciona para mim"],
        }

        best_match = None
        max_matches = 0

        for incident_type, patterns in type_patterns.items():
            matches = sum(1 for pattern in patterns if pattern in description_lower)
            if matches > max_matches:
                max_matches = matches
                best_match = incident_type

        # Only return if we have reasonable confidence
        return best_match if max_matches >= 1 else None

    def _get_type_inference_confidence(self, description: str, inferred_type: str) -> float:
        """Calculate confidence level for type inference."""
        # Simple confidence calculation based on keyword matches
        # This could be enhanced with ML models
        return 0.7 if inferred_type else 0.0

    def _get_incident_subcategory(self, incident_type: str, description: str) -> str | None:
        """Get incident subcategory based on type and description."""
        subcategories = {
            "Falha de Sistema": {
                "Hardware": ["hardware", "disco", "memória", "cpu", "servidor físico"],
                "Software": ["software", "aplicação", "bug", "código", "programa"],
                "Base de Dados": ["banco", "database", "sql", "dados", "query"],
            },
            "Problema de Rede": {
                "Conectividade": ["internet", "wi-fi", "cabo", "roteador"],
                "Performance": ["lento", "latência", "timeout", "performance"],
                "DNS": ["dns", "resolução", "domínio"],
            },
        }

        description_lower = description.lower()

        if incident_type in subcategories:
            for subcategory, keywords in subcategories[incident_type].items():
                if any(keyword in description_lower for keyword in keywords):
                    return subcategory

        return None

    def _generate_incident_tags(self, description: str, incident_type: str) -> list[str]:
        """Generate relevant tags for the incident."""
        tags = []
        description_lower = description.lower()

        # System/technology tags
        tech_keywords = {
            "web": ["web", "site", "página", "browser"],
            "mobile": ["mobile", "celular", "app móvel", "smartphone"],
            "email": ["email", "e-mail", "outlook", "gmail"],
            "erp": ["sap", "erp", "sistema integrado"],
        }

        for tag, keywords in tech_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                tags.append(tag)

        # Urgency tags
        urgency_keywords = {
            "urgent": ["urgente", "crítico", "emergência", "imediato"],
            "high_impact": ["muitos usuários", "produção", "clientes afetados"],
        }

        for tag, keywords in urgency_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                tags.append(tag)

        return tags

    def _assess_incident_severity(self, incident: Incident) -> dict[str, Any]:
        """Assess incident severity based on business rules."""
        severity_score = 0
        factors = []

        description_lower = incident.raw_description.lower()

        # High severity indicators
        high_severity_keywords = [
            "crítico",
            "urgente",
            "produção parada",
            "sistema fora do ar",
            "muitos usuários",
            "clientes afetados",
            "perda de dados",
        ]

        for keyword in high_severity_keywords:
            if keyword in description_lower:
                severity_score += 3
                factors.append(f"High severity keyword: {keyword}")

        # Medium severity indicators
        medium_severity_keywords = ["lento", "problema", "erro", "não funciona", "falha"]

        for keyword in medium_severity_keywords:
            if keyword in description_lower:
                severity_score += 1
                factors.append(f"Medium severity keyword: {keyword}")

        # Determine severity level
        if severity_score >= 5:
            severity_level = "HIGH"
        elif severity_score >= 2:
            severity_level = "MEDIUM"
        else:
            severity_level = "LOW"

        return {"level": severity_level, "score": severity_score, "factors": factors}

    def _enhance_impact_description(self, impact: str, severity: dict[str, Any]) -> str:
        """Enhance impact description with severity context."""
        if severity["level"] == "HIGH" and "crítico" not in impact.lower():
            return f"{impact} [Impacto crítico identificado]"
        elif severity["level"] == "MEDIUM" and len(impact) < 50:
            return f"{impact} - Requer atenção para resolução adequada"

        return impact

    def _calculate_enrichment_confidence(self, original: Incident, enriched: Incident) -> float:
        """Calculate overall confidence level for enrichment process."""
        base_confidence = 0.5

        # Increase confidence based on successful enrichments
        if enriched.data_ocorrencia and not original.data_ocorrencia:
            base_confidence += 0.1

        if enriched.local and not original.local:
            base_confidence += 0.1

        if enriched.tipo_incidente and not original.tipo_incidente:
            base_confidence += 0.2

        if enriched.impacto and not original.impacto:
            base_confidence += 0.1

        return min(1.0, base_confidence)
