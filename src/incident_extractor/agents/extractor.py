"""Simplified ExtractorAgent with complexity moved to prompts and helper services."""

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from incident_extractor.agents.helpers import DateTimeHandler, FieldValidator, ResponseParser
from incident_extractor.config.logging import get_logger, log_agent_activity
from incident_extractor.models.schemas import AgentState, IncidentData, ProcessingStatus
from incident_extractor.services.llm_service import get_llm_service_manager


class ExtractorAgent:
    """
    Simplified ExtractorAgent that focuses on orchestration.

    Complex logic has been moved to:
    - LLM prompts (extractor.yaml) - business rules, date parsing, field validation
    - Helper services - simple technical operations

    Responsibilities:
    - Load and manage prompts
    - Orchestrate extraction workflow
    - Coordinate with LLM and helper services
    - Manage state transitions
    """

    def __init__(self):
        self.logger = get_logger("agent.extractor")

        # Initialize helper services
        self.date_handler = DateTimeHandler()
        self.response_parser = ResponseParser()
        self.field_validator = FieldValidator()

        # Load prompts
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> dict[str, Any]:
        """Load extraction prompts from YAML configuration."""
        try:
            prompts_file = Path(__file__).parent.parent / "prompts" / "extractor.yaml"
            with open(prompts_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load prompts: {e}")
            # Fallback to basic prompts
            return {
                "system_prompt": "Extract incident data and return as JSON.",
                "strategies": {"standard": {"user_prompt": "Extract incident information from: {text}"}},
            }

    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute simplified extraction workflow.

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

            # Get text to process (preprocessed if available, otherwise raw)
            text_to_extract = state.preprocessed_text or state.raw_text

            # Select extraction strategy
            strategy = self._select_strategy(state.extraction_attempts)

            # Perform extraction
            extracted_data = await self._perform_extraction(text_to_extract, strategy)

            # Process results
            if extracted_data:
                state.extracted_data = extracted_data
                state = self._update_extraction_output(state, strategy, extracted_data)
                state.status = ProcessingStatus.SUCCESS

                log_agent_activity(
                    "extractor",
                    "Extraction completed successfully",
                    fields_extracted=self._count_fields(extracted_data),
                )
            else:
                # Handle extraction failure
                if state.should_retry_extraction():
                    state.status = ProcessingStatus.PROCESSING
                    state.add_warning("Extraction failed, retrying")
                else:
                    state.status = ProcessingStatus.ERROR
                    state.add_error("Extraction failed after maximum attempts")

            return state

        except Exception as e:
            error_msg = f"Extractor agent failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            state.add_error(error_msg)
            state.status = ProcessingStatus.ERROR
            return state

    def _select_strategy(self, attempt_number: int) -> str:
        """Select extraction strategy based on attempt number."""
        strategy_map = {1: "standard", 2: "contextual", 3: "retry"}
        return strategy_map.get(attempt_number, "retry")

    async def _perform_extraction(self, text: str, strategy: str) -> IncidentData | None:
        """
        Perform the actual extraction using LLM and helper services.

        Args:
            text: Text to extract from
            strategy: Extraction strategy name

        Returns:
            Extracted incident data or None if failed
        """
        try:
            # Get prompts for strategy
            system_prompt_template = self.prompts.get("system_prompt", "")
            strategy_config = self.prompts.get("strategies", {}).get(strategy, {})
            user_prompt = strategy_config.get("user_prompt", "Extract incident information from: {text}")

            # Inject current date context into system prompt
            system_prompt = self._format_system_prompt_with_date_context(system_prompt_template)

            # Format prompt with text
            formatted_prompt = user_prompt.format(text=text)

            self.logger.info(f"Using extraction strategy: {strategy}")

            # Get LLM service and generate response
            service_manager = await get_llm_service_manager()
            response = await service_manager.generate_with_fallback(["ollama", "openai"], formatted_prompt, system_prompt)

            # Parse JSON response
            response_data = self.response_parser.extract_json(response)
            if not response_data:
                self.logger.warning("Failed to parse LLM response")
                return None

            # Clean and validate fields
            cleaned_data, validation_log = self.field_validator.validate_extracted_data(response_data)

            # Handle datetime field
            if cleaned_data.get("data_ocorrencia"):
                cleaned_data["data_ocorrencia"] = self.date_handler.validate_datetime_format(cleaned_data["data_ocorrencia"])

            # Create IncidentData object
            incident_data = IncidentData(
                data_ocorrencia=cleaned_data.get("data_ocorrencia"),
                local=cleaned_data.get("local"),
                tipo_incidente=cleaned_data.get("tipo_incidente"),
                impacto=cleaned_data.get("impacto"),
            )

            self.logger.info(
                "Extraction successful", validation_applied=validation_log, fields_extracted=self._count_fields(incident_data)
            )

            return incident_data

        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            return None

    def _update_extraction_output(self, state: AgentState, strategy: str, data: IncidentData) -> AgentState:
        """Update state with extraction output metadata."""
        confidence = self.field_validator.calculate_simple_confidence(
            {
                "data_ocorrencia": data.data_ocorrencia,
                "local": data.local,
                "tipo_incidente": data.tipo_incidente,
                "impacto": data.impacto,
            }
        )

        state.extractor_output = {
            "extraction_strategy": strategy,
            "extraction_confidence": confidence,
            "fields_extracted": self._count_fields(data),
            "attempt_number": state.extraction_attempts,
            "timestamp": datetime.now().isoformat(),
            "validation_status": "completed",
        }

        return state

    def _count_fields(self, data: IncidentData | None) -> int:
        """Count non-null fields in extracted data."""
        if not data:
            return 0
        fields = [data.data_ocorrencia, data.local, data.tipo_incidente, data.impacto]
        return sum(1 for field in fields if field is not None)

    def _format_system_prompt_with_date_context(self, system_prompt_template: str) -> str:
        """Format system prompt with current date context for accurate relative date parsing."""
        from datetime import datetime, timedelta

        now = datetime.now()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        # Calculate last Friday
        days_since_friday = (now.weekday() - 4) % 7  # Friday is weekday 4
        if days_since_friday == 0:  # Today is Friday
            last_friday = now - timedelta(days=7)  # Last Friday was 7 days ago
        else:
            last_friday = now - timedelta(days=days_since_friday)

        # Portuguese weekday names
        weekdays_pt = {
            0: "segunda-feira",
            1: "terça-feira",
            2: "quarta-feira",
            3: "quinta-feira",
            4: "sexta-feira",
            5: "sábado",
            6: "domingo",
        }

        return system_prompt_template.format(
            current_date=now.strftime("%Y-%m-%d"),
            current_weekday=now.strftime("%A"),
            current_weekday_pt=weekdays_pt[now.weekday()],
            yesterday=yesterday.strftime("%Y-%m-%d"),
            tomorrow=tomorrow.strftime("%Y-%m-%d"),
            last_friday=last_friday.strftime("%Y-%m-%d"),
        )
