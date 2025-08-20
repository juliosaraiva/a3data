"""Incident information extraction service."""

import json
import logging
from typing import Dict, Any, Optional

from app.services.llm_client import LLMClient, LLMResponse
from app.utils.preprocessing import TextPreprocessor
from app.models.schemas import IncidentResponse

logger = logging.getLogger(__name__)


class IncidentExtractor:
    """Service for extracting structured information from incident descriptions."""

    def __init__(self, llm_client: LLMClient, preprocessor: TextPreprocessor):
        """Initialize the extractor."""
        self.llm_client = llm_client
        self.preprocessor = preprocessor

    async def extract_incident_info(self, description: str) -> IncidentResponse:
        """Extract structured information from incident description."""
        logger.info("Starting incident information extraction")
        
        # Preprocess the input text
        processed_text = self.preprocessor.preprocess(description)
        logger.debug(f"Processed description: {processed_text}")
        
        # Build the prompt for the LLM
        prompt = self._build_extraction_prompt(processed_text)
        
        # Get response from LLM with retry logic
        llm_response = await self._generate_with_retry(prompt)
        
        if not llm_response.success:
            logger.error(f"LLM generation failed: {llm_response.error}")
            return self._create_fallback_response(processed_text)
        
        # Parse and validate the response
        return self._parse_llm_response(llm_response.text, processed_text)

    def _build_extraction_prompt(self, text: str) -> str:
        """Build the prompt for LLM to extract incident information."""
        
        # Extract hints from preprocessing
        date_hint = self.preprocessor.extract_date_hints(text)
        time_hint = self.preprocessor.extract_time_hints(text)
        
        context_info = ""
        if date_hint:
            context_info += f"\nData de contexto: {date_hint}"
        if time_hint:
            context_info += f"\nHorário de contexto: {time_hint}"
        
        prompt = f"""Você é um especialista em análise de incidentes. Analise o texto abaixo e extraia as informações estruturadas.

TEXTO DO INCIDENTE:
{text}

CONTEXTO ADICIONAL:{context_info}

INSTRUÇÕES:
1. Extraia APENAS as informações que estão claramente presentes no texto
2. Para campos não encontrados, use null
3. Para data_ocorrencia, use formato "AAAA-MM-DD HH:MM" se possível
4. Seja conciso e preciso nas descrições
5. RETORNE APENAS UM JSON VÁLIDO, sem explicações adicionais

FORMATO DE SAÍDA (JSON):
{{
    "data_ocorrencia": "AAAA-MM-DD HH:MM ou null",
    "local": "local do incidente ou null",
    "tipo_incidente": "tipo/categoria do incidente ou null",
    "impacto": "descrição do impacto ou null"
}}

JSON:"""
        
        return prompt

    async def _generate_with_retry(self, prompt: str, max_retries: int = 2) -> LLMResponse:
        """Generate LLM response with retry logic."""
        
        for attempt in range(max_retries + 1):
            logger.debug(f"LLM generation attempt {attempt + 1}")
            
            response = await self.llm_client.generate(prompt)
            
            if response.success:
                # Quick validation - check if response looks like JSON
                if self._is_valid_json_response(response.text):
                    return response
                else:
                    logger.warning(f"Attempt {attempt + 1}: Invalid JSON response")
                    if attempt < max_retries:
                        # Add instruction for retry
                        prompt += "\n\nATENÇÃO: Retorne APENAS JSON válido, sem texto adicional."
                        continue
            else:
                logger.error(f"Attempt {attempt + 1}: LLM error - {response.error}")
        
        return response

    def _is_valid_json_response(self, text: str) -> bool:
        """Quick check if response looks like valid JSON."""
        text = text.strip()
        return text.startswith('{') and text.endswith('}')

    def _parse_llm_response(self, response_text: str, original_text: str) -> IncidentResponse:
        """Parse and validate LLM response."""
        
        try:
            # Clean the response text
            cleaned_response = self._clean_json_response(response_text)
            
            # Parse JSON
            data = json.loads(cleaned_response)
            
            # Validate and clean the extracted data
            validated_data = self._validate_extracted_data(data, original_text)
            
            return IncidentResponse(**validated_data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response_text}")
            return self._create_fallback_response(original_text)
        
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return self._create_fallback_response(original_text)

    def _clean_json_response(self, text: str) -> str:
        """Clean the JSON response from LLM."""
        # Remove common prefixes/suffixes that LLMs might add
        text = text.strip()
        
        # Remove markdown code blocks
        if text.startswith('```json'):
            text = text[7:]
        if text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        
        # Find the JSON object
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start != -1 and end > start:
            text = text[start:end]
        
        return text.strip()

    def _validate_extracted_data(self, data: Dict[str, Any], original_text: str) -> Dict[str, Optional[str]]:
        """Validate and clean extracted data."""
        
        validated = {}
        
        # Validate each field
        for field in ["data_ocorrencia", "local", "tipo_incidente", "impacto"]:
            value = data.get(field)
            
            if value is None or value == "null" or str(value).strip() == "":
                validated[field] = None
            else:
                validated[field] = str(value).strip()
                
                # Additional validation for date
                if field == "data_ocorrencia" and validated[field]:
                    validated[field] = self._validate_date_format(validated[field])
        
        logger.debug(f"Validated data: {validated}")
        return validated

    def _validate_date_format(self, date_str: str) -> Optional[str]:
        """Validate and normalize date format."""
        if not date_str or date_str.lower() == "null":
            return None
        
        # Simple validation - keep as is if it looks reasonable
        # More sophisticated date parsing could be added here
        date_str = date_str.strip()
        
        # Check if it's a reasonable length and contains expected characters
        if len(date_str) >= 10 and ('-' in date_str or '/' in date_str):
            return date_str
        
        return None

    def _create_fallback_response(self, original_text: str) -> IncidentResponse:
        """Create a fallback response when LLM processing fails."""
        logger.info("Creating fallback response")
        
        # Try to extract basic information using regex patterns
        fallback_data = {
            "data_ocorrencia": self.preprocessor.extract_date_hints(original_text),
            "local": self._extract_location_fallback(original_text),
            "tipo_incidente": self._extract_incident_type_fallback(original_text),
            "impacto": self._extract_impact_fallback(original_text)
        }
        
        # Add time if available
        time_hint = self.preprocessor.extract_time_hints(original_text)
        if fallback_data["data_ocorrencia"] and time_hint:
            fallback_data["data_ocorrencia"] += f" {time_hint}"
        
        return IncidentResponse(**fallback_data)

    def _extract_location_fallback(self, text: str) -> Optional[str]:
        """Extract location using simple patterns."""
        # Look for common location patterns
        patterns = [
            r'(?:no|na|em)\s+([A-Z][a-zA-Z\s]+?)(?:\s|,|\.)',
            r'(?:escritório|servidor|sistema|local)(?:\s+de|\s+em|\s+na|\s+no)\s+([A-Z][a-zA-Z\s]+?)(?:\s|,|\.)',
        ]
        
        for pattern in patterns:
            import re
            match = re.search(pattern, text)
            if match:
                location = match.group(1).strip()
                if len(location) > 2:
                    return location
        
        return None

    def _extract_incident_type_fallback(self, text: str) -> Optional[str]:
        """Extract incident type using simple patterns."""
        # Look for common incident keywords
        keywords = [
            "falha", "erro", "problema", "incidente", "pane", "defeito",
            "interrupção", "indisponibilidade", "crash", "bug"
        ]
        
        for keyword in keywords:
            if keyword in text.lower():
                # Try to get context around the keyword
                import re
                pattern = rf'(\w+\s+)*{keyword}(\s+\w+)*'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group().strip()
        
        return None

    def _extract_impact_fallback(self, text: str) -> Optional[str]:
        """Extract impact using simple patterns."""
        # Look for duration and system affected
        duration_match = None
        system_match = None
        
        import re
        # Duration patterns
        duration_patterns = [
            r'por\s+(\d+\s+horas?)',
            r'durante\s+(\d+\s+horas?)',
            r'(\d+h\d*)',
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                duration_match = match.group(1)
                break
        
        # System patterns
        system_patterns = [
            r'sistema\s+de\s+(\w+)',
            r'(?:afetou|impactou)\s+(?:o\s+)?(\w+)',
        ]
        
        for pattern in system_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                system_match = match.group(1)
                break
        
        # Combine information
        impact_parts = []
        if system_match:
            impact_parts.append(f"Sistema {system_match} afetado")
        if duration_match:
            impact_parts.append(f"por {duration_match}")
        
        return " ".join(impact_parts) if impact_parts else None