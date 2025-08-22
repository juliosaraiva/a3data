"""Core domain service for incident extraction business logic."""

from __future__ import annotations

from typing import Any

import structlog

from incident_extractor.core.exceptions.domain import DomainError
from incident_extractor.domain.entities.incident import Incident
from incident_extractor.domain.repositories import LLMRepository
from incident_extractor.domain.value_objects import IncidentDateTime, Location

logger = structlog.get_logger(__name__)


class IncidentExtractionError(DomainError):
    """Exception raised when incident extraction fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, "INCIDENT_EXTRACTION_ERROR", details)


class IncidentExtractionService:
    """
    Domain service responsible for the core business logic of extracting incidents from text.

    This service coordinates the extraction process by leveraging LLM capabilities
    while applying domain-specific business rules and validation.
    """

    def __init__(self, llm_repository: LLMRepository):
        self._llm_repository = llm_repository
        self._logger = logger.bind(service="IncidentExtractionService")

    async def extract_incident(self, raw_description: str) -> Incident:
        """Extract incident information from raw text description.

        This method applies business rules for extraction including:
        - Text preprocessing and validation
        - Structured prompt generation
        - LLM response parsing and validation
        - Domain object creation with business rules

        Args:
            raw_description: Raw text containing incident information

        Returns:
            Incident entity with extracted and validated information

        Raises:
            IncidentExtractionError: When extraction fails or business rules are violated
        """
        self._logger.info("Starting incident extraction", raw_text_length=len(raw_description))

        # Apply business rule: minimum text length
        if not self._is_valid_input_text(raw_description):
            raise IncidentExtractionError(
                "Input text does not meet minimum requirements for extraction",
                {"text_length": len(raw_description), "min_length": 10},
            )

        try:
            # Create base incident with raw description
            base_incident = Incident(raw_description=raw_description.strip())

            # Generate structured extraction prompt
            extraction_prompt = self._build_extraction_prompt(raw_description)

            # Get LLM response
            llm_response = await self._llm_repository.generate(
                prompt=extraction_prompt,
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=500,
            )

            # Parse and validate LLM response
            extracted_data = self._parse_llm_response(llm_response)

            # Apply business rules to extracted data
            validated_data = self._apply_business_rules(extracted_data, raw_description)

            # Create final incident with extracted data
            final_incident = base_incident.with_extracted_data(
                data_ocorrencia=validated_data.get("data_ocorrencia"),
                local=validated_data.get("local"),
                tipo_incidente=validated_data.get("tipo_incidente"),
                impacto=validated_data.get("impacto"),
            )

            self._logger.info(
                "Incident extraction completed",
                extraction_score=final_incident.extraction_score,
                is_complete=final_incident.is_complete,
            )

            return final_incident

        except Exception as e:
            self._logger.error("Incident extraction failed", error=str(e))
            raise IncidentExtractionError(
                f"Failed to extract incident information: {str(e)}", {"original_error": str(e), "error_type": type(e).__name__}
            ) from e

    def _is_valid_input_text(self, text: str) -> bool:
        """Validate input text meets business requirements."""
        if not text or not text.strip():
            return False

        # Business rule: minimum meaningful text length
        if len(text.strip()) < 10:
            return False

        # Business rule: maximum text length for processing
        if len(text) > 10000:
            return False

        return True

    def _build_extraction_prompt(self, raw_description: str) -> str:
        """Build structured prompt for LLM extraction with Brazilian context."""
        return f"""
Extraia as informações do seguinte relato de incidente em português brasileiro:

TEXTO: {raw_description}

INSTRUÇÕES:
- Extraia APENAS as informações explícitas no texto
- Use o formato JSON especificado
- Para datas, considere o contexto brasileiro (DD/MM/AAAA)
- Para localização, identifique cidades/estados brasileiros quando possível
- Se uma informação não estiver clara, use null

FORMATO DE RESPOSTA (JSON):
{{
  "data_ocorrencia": "DD/MM/AAAA HH:MM ou expressão temporal em português",
  "local": "localização específica mencionada no texto",
  "tipo_incidente": "categoria/tipo do incidente",
  "impacto": "impacto ou consequências mencionadas"
}}

JSON:"""

    def _parse_llm_response(self, response: str) -> dict[str, Any]:
        """Parse and validate LLM JSON response."""
        import json

        try:
            # Clean response - extract JSON from text
            response = response.strip()

            # Find JSON block
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")

            json_str = response[json_start:json_end]
            extracted_data = json.loads(json_str)

            # Validate expected fields
            expected_fields = ["data_ocorrencia", "local", "tipo_incidente", "impacto"]
            for field in expected_fields:
                if field not in extracted_data:
                    extracted_data[field] = None

            return extracted_data

        except (json.JSONDecodeError, ValueError) as e:
            raise IncidentExtractionError(
                "Failed to parse LLM response as valid JSON", {"response": response[:200], "parse_error": str(e)}
            ) from e

    def _apply_business_rules(self, extracted_data: dict[str, Any], raw_text: str) -> dict[str, Any]:
        """Apply domain business rules to extracted data."""
        validated_data = {}

        # Process date/time with business rules
        if extracted_data.get("data_ocorrencia"):
            try:
                validated_data["data_ocorrencia"] = IncidentDateTime.from_string(extracted_data["data_ocorrencia"])
            except Exception as e:
                self._logger.warning(
                    "Failed to parse extracted date", extracted_date=extracted_data["data_ocorrencia"], error=str(e)
                )
                validated_data["data_ocorrencia"] = None
        else:
            validated_data["data_ocorrencia"] = None

        # Process location with business rules
        if extracted_data.get("local"):
            try:
                validated_data["local"] = Location(extracted_data["local"])
            except Exception as e:
                self._logger.warning(
                    "Failed to parse extracted location", extracted_location=extracted_data["local"], error=str(e)
                )
                validated_data["local"] = None
        else:
            validated_data["local"] = None

        # Process incident type with normalization
        validated_data["tipo_incidente"] = self._normalize_incident_type(extracted_data.get("tipo_incidente"))

        # Process impact description
        validated_data["impacto"] = self._normalize_impact_description(extracted_data.get("impacto"))

        return validated_data

    def _normalize_incident_type(self, incident_type: str | None) -> str | None:
        """Apply business rules to normalize incident type."""
        if not incident_type or not incident_type.strip():
            return None

        # Business rule: standardize common incident types
        incident_type = incident_type.strip().lower()

        type_mappings = {
            "falha de sistema": "Falha de Sistema",
            "erro de aplicacao": "Erro de Aplicação",
            "erro de aplicação": "Erro de Aplicação",
            "problema de rede": "Problema de Rede",
            "indisponibilidade": "Indisponibilidade de Serviço",
            "lentidao": "Lentidão de Sistema",
            "erro de usuario": "Erro de Usuário",
            "erro de usuário": "Erro de Usuário",
            "falha de hardware": "Falha de Hardware",
            "problema de seguranca": "Problema de Segurança",
            "problema de segurança": "Problema de Segurança",
        }

        normalized = type_mappings.get(incident_type)
        if normalized:
            return normalized

        # If not in mappings, capitalize properly
        return incident_type.title()

    def _normalize_impact_description(self, impact: str | None) -> str | None:
        """Apply business rules to normalize impact description."""
        if not impact or not impact.strip():
            return None

        impact = impact.strip()

        # Business rule: limit impact description length
        if len(impact) > 500:
            impact = impact[:497] + "..."

        return impact
