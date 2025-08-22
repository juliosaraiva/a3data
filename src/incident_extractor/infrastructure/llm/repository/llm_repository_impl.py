"""LLM repository implementation."""

from __future__ import annotations

import logging
from typing import Any

from src.incident_extractor.domain.repositories.llm_repository import LLMRepository
from src.incident_extractor.domain.value_objects.incident import IncidentExtractionResult

from ..clients.base_client import BaseLLMClient, LLMRequest

logger = logging.getLogger(__name__)


class LLMRepositoryImpl(LLMRepository):
    """Implementation of LLM repository using configured LLM clients."""

    def __init__(self, primary_client: BaseLLMClient, fallback_clients: list[BaseLLMClient] | None = None):
        """Initialize LLM repository.

        Args:
            primary_client: Primary LLM client to use
            fallback_clients: Optional fallback clients if primary fails
        """
        self.primary_client = primary_client
        self.fallback_clients = fallback_clients or []
        self._all_clients = [primary_client] + self.fallback_clients

    async def extract_incident_data(
        self, text: str, extraction_type: str = "basic", context: dict[str, Any] | None = None
    ) -> IncidentExtractionResult:
        """Extract incident data from text using LLM.

        Args:
            text: Input text to extract from
            extraction_type: Type of extraction (basic, detailed, etc.)
            context: Additional context for extraction

        Returns:
            Extraction result with incident data

        Raises:
            Exception: If all LLM clients fail
        """
        # Build extraction prompt
        prompt = self._build_extraction_prompt(text, extraction_type)

        # Prepare LLM request
        llm_request = LLMRequest(
            prompt=prompt,
            temperature=0.3,  # Lower temperature for more consistent extraction
            max_tokens=2000,
            context=context,
        )

        # Try primary client first, then fallbacks
        last_error = None
        for i, client in enumerate(self._all_clients):
            try:
                logger.info(f"Attempting extraction with {client.name} (attempt {i + 1}/{len(self._all_clients)})")

                response = await client.generate_text(llm_request)

                # Parse and validate response
                result = self._parse_extraction_response(response.content, response)

                logger.info(f"Extraction successful with {client.name}")
                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Extraction failed with {client.name}: {e}")

                # If this was the last client, re-raise the error
                if i == len(self._all_clients) - 1:
                    break

        # All clients failed
        logger.error(f"All LLM clients failed. Last error: {last_error}")

        return IncidentExtractionResult(
            success=False,
            incident_data=None,
            confidence_score=0.0,
            extraction_time_ms=0,
            errors=[f"All LLM clients failed. Last error: {str(last_error)}"],
            provider_used=self.primary_client.name,
            raw_response=None,
        )

    def _build_extraction_prompt(self, text: str, extraction_type: str) -> str:
        """Build extraction prompt based on type and text.

        Args:
            text: Input text
            extraction_type: Type of extraction

        Returns:
            Formatted prompt
        """
        base_prompt = """
Você é um especialista em extração de informações sobre incidentes de segurança pública no Brasil.
Extraia as seguintes informações do texto fornecido e retorne em formato JSON válido:

CAMPOS OBRIGATÓRIOS:
- tipo_incidente: tipo do incidente (acidente_transito, incendio, crime, emergencia_medica, etc.)
- gravidade: nível de gravidade (baixa, moderada, alta, crítica)
- data_hora: data e hora do incidente (formato ISO 8601 com timezone de São Paulo)
- local: endereço completo ou descrição da localização
- descricao: descrição detalhada do incidente

CAMPOS OPCIONAIS (quando disponíveis):
- coordenadas: {latitude: number, longitude: number}
- feridos: número de feridos
- mortos: número de mortos
- envolvidos: lista de pessoas/veículos envolvidos
- orgaos_acionados: órgãos de emergência acionados (Bombeiros, SAMU, Polícia, etc.)
- status: status atual (em_andamento, resolvido, investigacao)

REGRAS:
1. Use APENAS informações explícitas no texto
2. Para data/hora, use o timezone de São Paulo (-03:00)
3. Se uma informação não estiver disponível, não inclua o campo
4. Retorne APENAS o JSON, sem explicações adicionais
5. Use termos em português brasileiro

TEXTO A ANALISAR:
"""

        if extraction_type == "detailed":
            base_prompt += """
ANÁLISE DETALHADA SOLICITADA:
- Inclua todos os campos opcionais possíveis
- Forneça coordenadas se mencionadas ou inferíveis
- Detalhe todos os envolvidos
- Liste todos os órgãos mencionados
"""

        return f"{base_prompt.strip()}\n\n{text}"

    def _parse_extraction_response(self, content: str, llm_response: Any) -> IncidentExtractionResult:
        """Parse LLM response into extraction result.

        Args:
            content: LLM response content
            llm_response: Full LLM response object

        Returns:
            Parsed extraction result
        """
        try:
            # Try to extract JSON from response
            import json
            import re

            # Find JSON in response (handle cases where LLM adds extra text)
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                incident_data = json.loads(json_str)
            else:
                # Fallback: try to parse entire content as JSON
                incident_data = json.loads(content)

            # Validate required fields
            required_fields = ["tipo_incidente", "gravidade", "descricao"]
            missing_fields = [field for field in required_fields if field not in incident_data]

            if missing_fields:
                return IncidentExtractionResult(
                    success=False,
                    incident_data=None,
                    confidence_score=0.2,
                    extraction_time_ms=getattr(llm_response, "processing_time_ms", 0),
                    errors=[f"Missing required fields: {missing_fields}"],
                    provider_used=getattr(llm_response, "provider", "unknown"),
                    raw_response=getattr(llm_response, "raw_response", {}),
                )

            # Calculate confidence score based on completeness
            confidence_score = self._calculate_confidence_score(incident_data)

            return IncidentExtractionResult(
                success=True,
                incident_data=incident_data,
                confidence_score=confidence_score,
                extraction_time_ms=getattr(llm_response, "processing_time_ms", 0),
                errors=[],
                provider_used=getattr(llm_response, "provider", "unknown"),
                raw_response=getattr(llm_response, "raw_response", {}),
            )

        except json.JSONDecodeError as e:
            return IncidentExtractionResult(
                success=False,
                incident_data=None,
                confidence_score=0.1,
                extraction_time_ms=getattr(llm_response, "processing_time_ms", 0),
                errors=[f"Invalid JSON response: {str(e)}"],
                provider_used=getattr(llm_response, "provider", "unknown"),
                raw_response={"raw_content": content},
            )

        except Exception as e:
            return IncidentExtractionResult(
                success=False,
                incident_data=None,
                confidence_score=0.0,
                extraction_time_ms=getattr(llm_response, "processing_time_ms", 0),
                errors=[f"Extraction parsing failed: {str(e)}"],
                provider_used=getattr(llm_response, "provider", "unknown"),
                raw_response={"raw_content": content},
            )

    def _calculate_confidence_score(self, incident_data: dict[str, Any]) -> float:
        """Calculate confidence score based on data completeness.

        Args:
            incident_data: Extracted incident data

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Define field weights
        field_weights = {
            # Required fields (high weight)
            "tipo_incidente": 0.2,
            "gravidade": 0.15,
            "descricao": 0.15,
            # Important optional fields
            "data_hora": 0.15,
            "local": 0.15,
            # Additional fields
            "coordenadas": 0.05,
            "feridos": 0.05,
            "envolvidos": 0.05,
            "orgaos_acionados": 0.05,
        }

        score = 0.0
        for field, weight in field_weights.items():
            if field in incident_data and incident_data[field]:
                score += weight

        # Bonus for data quality
        if "data_hora" in incident_data:
            try:
                from datetime import datetime

                datetime.fromisoformat(incident_data["data_hora"].replace("Z", "+00:00"))
                score += 0.05  # Valid datetime format bonus
            except Exception:
                pass

        if "coordenadas" in incident_data:
            coords = incident_data["coordenadas"]
            if isinstance(coords, dict) and "latitude" in coords and "longitude" in coords:
                score += 0.05  # Valid coordinates bonus

        return min(1.0, score)

    async def health_check(self) -> dict[str, bool]:
        """Check health of all LLM clients.

        Returns:
            Health status for each client
        """
        results = {}
        for client in self._all_clients:
            try:
                results[client.name] = await client.health_check()
            except Exception:
                results[client.name] = False

        return results

    def get_client_status(self) -> dict[str, Any]:
        """Get status information for all clients.

        Returns:
            Status information for each client
        """
        status = {
            "primary_client": self.primary_client.name,
            "fallback_clients": [client.name for client in self.fallback_clients],
            "clients": {},
        }

        for client in self._all_clients:
            client_status = {
                "name": client.name,
                "supported_models": client.get_supported_models(),
            }

            # Add circuit breaker status if available
            if hasattr(client, "get_circuit_breaker_status"):
                client_status["circuit_breaker"] = client.get_circuit_breaker_status()

            status["clients"][client.name] = client_status

        return status

    async def close(self) -> None:
        """Close all client connections."""
        for client in self._all_clients:
            if hasattr(client, "close"):
                try:
                    await client.close()
                except Exception as e:
                    logger.warning(f"Error closing client {client.name}: {e}")
