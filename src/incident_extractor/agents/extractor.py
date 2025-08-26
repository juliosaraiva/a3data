"""Extractor agent for incident information extraction."""

import json
import re
from datetime import datetime, timedelta
from typing import Any

from incident_extractor.config.llm import EXTRACTION_PROMPTS, get_llm_config
from incident_extractor.config.logging import get_logger, log_agent_activity
from incident_extractor.models.schemas import AgentState, IncidentData, ProcessingStatus
from incident_extractor.services.llm_service import get_llm_service_manager


class ExtractorAgent:
    """
    Extractor agent that extracts structured incident information.

    Responsibilities:
    - Extract data_ocorrencia, local, tipo_incidente, impacto
    - Parse and validate LLM responses
    - Handle multiple extraction strategies
    - Ensure output format compliance
    """

    def __init__(self):
        self.logger = get_logger("agent.extractor")
        self.config = get_llm_config().extractor

        # Context for date interpretation
        self._initialize_date_context()

    def _initialize_date_context(self) -> None:
        """Initialize context for date interpretation."""
        self.today = datetime.now()
        self.yesterday = self.today - timedelta(days=1)
        self.tomorrow = self.today + timedelta(days=1)

        # Portuguese day names to numbers
        self.day_names = {
            "segunda-feira": 0,
            "segunda": 0,
            "terça-feira": 1,
            "terça": 1,
            "quarta-feira": 2,
            "quarta": 2,
            "quinta-feira": 3,
            "quinta": 3,
            "sexta-feira": 4,
            "sexta": 4,
            "sábado": 5,
            "domingo": 6,
        }

    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute the extraction logic.

        Args:
            state: Current workflow state

        Returns:
            Updated state with extracted incident data
        """
        log_agent_activity(
            "extractor",
            "Starting information extraction",
            attempt=state.extraction_attempts + 1,
            max_attempts=state.max_attempts,
        )

        try:
            state.current_status = "extracao"
            state.increment_extraction_attempts()

            # Choose text source (preprocessed if available, otherwise original)
            text_to_extract = state.preprocessed_text or state.raw_text

            # Choose extraction strategy based on attempt number
            strategy = self._choose_extraction_strategy(state.extraction_attempts)

            # Perform extraction
            extracted_data = await self._extract_incident_data(text_to_extract, strategy)

            # Post-process and validate extracted data
            validated_data = self._validate_and_enhance_data(extracted_data, text_to_extract)

            # Update state
            state.extracted_data = validated_data
            state.extractor_output = {
                "extraction_strategy": strategy,
                "raw_extraction": extracted_data.model_dump() if extracted_data else None,
                "validation_applied": self._get_validation_summary(extracted_data, validated_data),
                "extraction_confidence": self._calculate_confidence(validated_data),
                "attempt_number": state.extraction_attempts,
                "timestamp": datetime.now().isoformat(),
            }

            # Check if extraction is satisfactory
            if self._is_extraction_satisfactory(validated_data):
                log_agent_activity(
                    "extractor",
                    "Extraction completed successfully",
                    confidence=state.extractor_output["extraction_confidence"],
                    fields_extracted=self._count_extracted_fields(validated_data),
                )
                state.status = ProcessingStatus.SUCCESS
            else:
                log_agent_activity(
                    "extractor",
                    "Extraction incomplete, may need retry",
                    confidence=state.extractor_output["extraction_confidence"],
                    fields_extracted=self._count_extracted_fields(validated_data),
                )
                if state.should_retry_extraction():
                    state.status = ProcessingStatus.PROCESSING
                    state.add_warning("Extração incompleta, tentando novamente")
                else:
                    state.status = ProcessingStatus.PARTIAL_SUCCESS
                    state.add_warning("Extração incompleta, máximo de tentativas atingido")

            return state

        except Exception as e:
            error_msg = f"Extractor agent failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            state.add_error(error_msg)
            state.status = ProcessingStatus.ERROR
            return state

    def _choose_extraction_strategy(self, attempt_number: int) -> str:
        """
        Choose extraction strategy based on attempt number.

        Args:
            attempt_number: Current attempt number (1-based)

        Returns:
            Strategy name
        """
        strategies = {1: "standard", 2: "contextual", 3: "retry"}
        return strategies.get(attempt_number, "retry")

    async def _extract_incident_data(self, text: str, strategy: str) -> IncidentData | None:
        """
        Extract incident data using specified strategy.

        Args:
            text: Text to extract from
            strategy: Extraction strategy to use

        Returns:
            Extracted incident data or None if failed
        """
        try:
            # Create prompt based on strategy
            prompt = EXTRACTION_PROMPTS[strategy].format(text=text)

            self.logger.info(f"Using extraction strategy: {strategy}")

            # Get LLM service manager
            service_manager = await get_llm_service_manager()

            # Generate extraction using fallback services
            response = await service_manager.generate_with_fallback(["ollama", "openai"], prompt, self.config.system_prompt)

            # Parse JSON response
            extracted_data = self._parse_extraction_response(response)

            return extracted_data

        except Exception as e:
            self.logger.error(f"Extraction failed with strategy {strategy}: {e}")
            return None

    def _parse_extraction_response(self, response: str) -> IncidentData | None:
        """
        Parse LLM response to extract structured data.

        Args:
            response: Raw LLM response

        Returns:
            Parsed incident data or None if parsing failed
        """
        try:
            # Clean response to find JSON
            json_str = self._extract_json_from_response(response)

            if not json_str:
                self.logger.warning("No JSON found in LLM response")
                return None

            # Parse JSON
            data_dict = json.loads(json_str)

            # Create IncidentData object with validation
            incident_data = IncidentData(
                data_ocorrencia=data_dict.get("data_ocorrencia"),
                local=data_dict.get("local"),
                tipo_incidente=data_dict.get("tipo_incidente"),
                impacto=data_dict.get("impacto"),
            )

            self.logger.info("Successfully parsed extraction response")
            return incident_data

        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON parsing failed: {e}")
            # Try to extract individual fields using regex
            return self._fallback_field_extraction(response)
        except Exception as e:
            self.logger.error(f"Response parsing failed: {e}")
            return None

    def _extract_json_from_response(self, response: str) -> str | None:
        """
        Extract JSON string from LLM response.

        Args:
            response: Raw LLM response

        Returns:
            JSON string or None if not found
        """
        # Look for JSON block patterns
        json_patterns = [
            r"```json\s*(.*?)\s*```",  # Markdown code block
            r"```\s*(.*?)\s*```",  # Generic code block
            r"\{.*?\}",  # Curly braces content
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                # Clean the match
                cleaned = match.strip()
                if cleaned.startswith("{") and cleaned.endswith("}"):
                    return cleaned

        # Try to find JSON-like structure
        lines = response.split("\n")
        json_lines = []
        in_json = False

        for line in lines:
            line = line.strip()
            if line.startswith("{"):
                in_json = True
                json_lines = [line]
            elif in_json:
                json_lines.append(line)
                if line.endswith("}"):
                    break

        if json_lines:
            return "\n".join(json_lines)

        return None

    def _fallback_field_extraction(self, response: str) -> IncidentData | None:
        """
        Fallback extraction using regex patterns.

        Args:
            response: LLM response text

        Returns:
            Extracted incident data or None
        """
        try:
            self.logger.info("Attempting fallback field extraction")

            # Patterns for each field
            patterns = {
                "data_ocorrencia": [
                    r'"data_ocorrencia":\s*"([^"]+)"',
                    r"data[_\s]*ocorrência[:\s]*([^\n,]+)",
                    r"data[:\s]*([0-9]{4}-[0-9]{2}-[0-9]{2}\s+[0-9]{2}:[0-9]{2})",
                ],
                "local": [
                    r'"local":\s*"([^"]+)"',
                    r"local[:\s]*([^\n,]+)",
                ],
                "tipo_incidente": [
                    r'"tipo_incidente":\s*"([^"]+)"',
                    r"tipo[_\s]*incidente[:\s]*([^\n,]+)",
                ],
                "impacto": [
                    r'"impacto":\s*"([^"]+)"',
                    r"impacto[:\s]*([^\n,]+)",
                ],
            }

            extracted_fields: dict[str, Any] = {}

            for field, field_patterns in patterns.items():
                for pattern in field_patterns:
                    match = re.search(pattern, response, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip().strip("\"'")
                        if value.lower() not in ["null", "none", "n/a", ""]:
                            extracted_fields[field] = value
                        break

            if extracted_fields:
                self.logger.info(f"Fallback extraction found {len(extracted_fields)} fields")
                return IncidentData(**extracted_fields)
            else:
                self.logger.warning("Fallback extraction found no fields")
                return None

        except Exception as e:
            self.logger.error(f"Fallback extraction failed: {e}")
            return None

    def _validate_and_enhance_data(self, data: IncidentData | None, original_text: str) -> IncidentData | None:
        """
        Validate and enhance extracted data.

        Args:
            data: Extracted incident data
            original_text: Original text for context

        Returns:
            Enhanced incident data
        """
        if not data:
            return None

        enhanced_data = data.model_copy()

        # Enhance date/time information
        if enhanced_data.data_ocorrencia:
            enhanced_data.data_ocorrencia = self._enhance_date_time(enhanced_data.data_ocorrencia, original_text)

        # Clean and validate text fields
        if enhanced_data.local:
            enhanced_data.local = self._clean_text_field(enhanced_data.local, max_length=200)

        if enhanced_data.tipo_incidente:
            enhanced_data.tipo_incidente = self._clean_text_field(enhanced_data.tipo_incidente, max_length=150)

        if enhanced_data.impacto:
            enhanced_data.impacto = self._clean_text_field(enhanced_data.impacto, max_length=500)

        return enhanced_data

    def _enhance_date_time(self, date_str: str, context_text: str) -> str | None:
        """
        Enhance date/time information using context.

        Args:
            date_str: Extracted date string
            context_text: Original text for context

        Returns:
            Enhanced date string in YYYY-MM-DD HH:MM format
        """
        try:
            # If already in correct format, return as is
            if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$", date_str):
                return date_str

            # Handle relative dates
            if "ontem" in date_str:
                base_date = self.yesterday
            elif "hoje" in date_str:
                base_date = self.today
            elif "amanhã" in date_str:
                base_date = self.tomorrow
            else:
                # Try to parse as regular date
                return self._parse_date_string(date_str)

            # Extract time if present
            time_match = re.search(r"(\d{1,2}):?(\d{2})?", date_str)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
            else:
                # Look for time in context
                context_time = re.search(r"(\d{1,2}):?(\d{2})?[h]?", context_text)
                if context_time:
                    hour = int(context_time.group(1))
                    minute = int(context_time.group(2)) if context_time.group(2) else 0
                else:
                    hour, minute = 12, 0  # Default to noon

            # Construct final datetime
            result_date = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return result_date.strftime("%Y-%m-%d %H:%M")

        except Exception as e:
            self.logger.warning(f"Date enhancement failed for '{date_str}': {e}")
            return date_str  # Return original if enhancement fails

    def _parse_date_string(self, date_str: str) -> str | None:
        """Parse various date string formats."""
        # Common patterns
        patterns = [
            (r"(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2})", "%Y-%m-%d %H:%M"),
            (r"(\d{2})/(\d{2})/(\d{4})\s+(\d{1,2}):(\d{2})", "%d/%m/%Y %H:%M"),
            (r"(\d{1,2})/(\d{1,2})/(\d{4})", "%d/%m/%Y"),
            (r"(\d{4})-(\d{2})-(\d{2})", "%Y-%m-%d"),
        ]

        for pattern, format_str in patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    if "%H:%M" in format_str:
                        dt = datetime.strptime(match.group(0), format_str)
                        return dt.strftime("%Y-%m-%d %H:%M")
                    else:
                        dt = datetime.strptime(match.group(0), format_str)
                        return dt.strftime("%Y-%m-%d 12:00")  # Default to noon
                except ValueError:
                    continue

        return None

    def _clean_text_field(self, text: str, max_length: int) -> str:
        """
        Clean and validate text field.

        Args:
            text: Text to clean
            max_length: Maximum allowed length

        Returns:
            Cleaned text
        """
        # Remove extra whitespace
        cleaned = re.sub(r"\s+", " ", text.strip())

        # Remove quotes if they wrap the entire string
        if cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1]
        if cleaned.startswith("'") and cleaned.endswith("'"):
            cleaned = cleaned[1:-1]

        # Truncate if too long
        if len(cleaned) > max_length:
            cleaned = cleaned[: max_length - 3] + "..."

        return cleaned

    def _is_extraction_satisfactory(self, data: IncidentData | None) -> bool:
        """
        Check if extraction results are satisfactory.

        Args:
            data: Extracted incident data

        Returns:
            True if extraction is satisfactory
        """
        if not data:
            return False

        # Count non-null fields
        fields = [data.data_ocorrencia, data.local, data.tipo_incidente, data.impacto]
        non_null_fields = sum(1 for field in fields if field is not None)

        # At least 2 out of 4 fields should be extracted
        return non_null_fields >= 2

    def _count_extracted_fields(self, data: IncidentData | None) -> int:
        """Count number of successfully extracted fields."""
        if not data:
            return 0

        fields = [data.data_ocorrencia, data.local, data.tipo_incidente, data.impacto]
        return sum(1 for field in fields if field is not None)

    def _calculate_confidence(self, data: IncidentData | None) -> float:
        """
        Calculate confidence score for extracted data.

        Args:
            data: Extracted incident data

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not data:
            return 0.0

        scores: list[int | float] = []

        # Date field confidence
        if data.data_ocorrencia:
            if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$", data.data_ocorrencia):
                scores.append(1.0)
            else:
                scores.append(0.5)
        else:
            scores.append(0.0)

        # Location field confidence
        if data.local:
            if len(data.local) > 2 and not data.local.isdigit():
                scores.append(0.8)
            else:
                scores.append(0.3)
        else:
            scores.append(0.0)

        # Incident type confidence
        if data.tipo_incidente:
            tech_terms = ["servidor", "sistema", "rede", "falha", "erro", "problema"]
            if any(term in data.tipo_incidente.lower() for term in tech_terms):
                scores.append(0.9)
            else:
                scores.append(0.6)
        else:
            scores.append(0.0)

        # Impact confidence
        if data.impacto:
            if len(data.impacto) > 10:
                scores.append(0.8)
            else:
                scores.append(0.5)
        else:
            scores.append(0.0)

        return sum(scores) / len(scores)

    def _get_validation_summary(self, original: IncidentData | None, validated: IncidentData | None) -> list[str]:
        """
        Get summary of validation operations applied.

        Args:
            original: Original extracted data
            validated: Validated data

        Returns:
            List of validation operations
        """
        if not original or not validated:
            return ["validation_failed"]

        operations: list[str] = []

        if original.data_ocorrencia != validated.data_ocorrencia:
            operations.append("date_enhanced")

        for field in ["local", "tipo_incidente", "impacto"]:
            orig_val = getattr(original, field)
            valid_val = getattr(validated, field)
            if orig_val != valid_val:
                operations.append(f"{field}_cleaned")

        if not operations:
            operations.append("no_changes_needed")

        return operations
