"""Supervisor agent for orchestrating the incident extraction workflow."""

from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from incident_extractor.config.llm import get_llm_config
from incident_extractor.config.logging import get_logger, log_agent_activity
from incident_extractor.models.schemas import AgentState, ProcessingStatus
from incident_extractor.services.llm_service import get_llm_service_manager


# Configuration constants loaded from YAML
class SupervisorConfig:
    """Configuration constants and prompts for the supervisor agent."""

    def __init__(self, config_path: str | None = None):
        """Initialize configuration from YAML file."""
        if config_path is None:
            self._config_path = Path(__file__).parent.parent / "prompts" / "supervisor.yaml"
        else:
            self._config_path = Path(config_path)

        self._config = self._load_config()

        # Extract thresholds
        thresholds = self._config["supervisor_config"]["thresholds"]
        self.MAX_ERRORS_THRESHOLD = thresholds["max_errors"]
        self.MAX_MISSING_FIELDS_THRESHOLD = thresholds["max_missing_fields"]
        self.MAX_CRITICAL_ERRORS_THRESHOLD = thresholds["max_critical_errors"]
        self.MAX_RECENT_ERRORS_TO_SHOW = thresholds["max_recent_errors_to_show"]

        # Extract error classification keywords
        error_config = self._config["supervisor_config"]["error_classification"]
        self.RECOVERABLE_KEYWORDS = error_config["recoverable_keywords"]
        self.CRITICAL_KEYWORDS = error_config["critical_keywords"]

        # Extract required fields
        self.REQUIRED_FIELDS = self._config["supervisor_config"]["required_fields"]

        # Extract visual indicators
        indicators = self._config["supervisor_config"]["indicators"]
        self.PRESENT_INDICATOR = indicators["present"]
        self.ABSENT_INDICATOR = indicators["absent"]
        self.FIELD_SEPARATOR = indicators["separator"]
        self.NO_ERRORS_MESSAGE = indicators["none_found"]
        self.NO_EXTRACTION_MESSAGE = indicators["none_extracted"]

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self._config_path, encoding="utf-8") as file:
                return yaml.safe_load(file)
        except Exception:
            # Fallback to default config if file loading fails
            return self._get_default_config()

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration as fallback."""
        return {
            "supervisor_config": {
                "thresholds": {
                    "max_errors": 3,
                    "max_missing_fields": 2,
                    "max_critical_errors": 2,
                    "max_recent_errors_to_show": 3,
                },
                "error_classification": {
                    "recoverable_keywords": ["timeout", "connection", "temporary", "retry"],
                    "critical_keywords": ["validation", "format", "parsing", "schema"],
                },
                "required_fields": ["data_ocorrencia", "local", "tipo_incidente", "impacto"],
                "indicators": {
                    "present": "✓",
                    "absent": "✗",
                    "separator": " | ",
                    "none_found": "Nenhum erro encontrado",
                    "none_extracted": "Nenhum campo extraído ainda",
                },
            }
        }

    def get_system_prompt(self) -> str:
        """Get system prompt with dynamic values."""
        template = self._config["supervisor_config"]["system_prompt"]
        return template.format(
            max_missing_fields=self.MAX_MISSING_FIELDS_THRESHOLD,
            max_errors=self.MAX_ERRORS_THRESHOLD,
            max_critical_errors=self.MAX_CRITICAL_ERRORS_THRESHOLD,
        )

    def get_decision_prompt_template(self) -> str:
        """Get decision prompt template."""
        return self._config["supervisor_config"]["decision_prompt_template"]

    def get_action_reasoning(self, action: str) -> str:
        """Get reasoning template for action."""
        reasoning = self._config["supervisor_config"]["action_reasoning"]
        return reasoning.get(action, f"Ação desconhecida: {action}")

    def get_status_message(self, status: str) -> str:
        """Get status message for final processing."""
        messages = self._config["supervisor_config"]["status_messages"]
        return messages.get(status, messages["unknown"])

    def get_recovery_message(self, message_type: str, **kwargs) -> str:
        """Get recovery message with formatting."""
        messages = self._config["supervisor_config"]["recovery_messages"]
        template = messages.get(message_type, messages["no_recovery"])
        return template.format(**kwargs)


class WorkflowAction(Enum):
    """Available workflow actions."""

    PREPROCESS = "preprocess"
    EXTRACT = "extract"
    RETRY = "retry"
    FINISH = "finish"
    ERROR = "error"


class ErrorType(Enum):
    """Error classification types."""

    RECOVERABLE = "recoverable"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class SupervisorAgent:
    """
    Supervisor agent that orchestrates the multi-agent workflow.

    Responsibilities:
    - Coordinate the overall extraction process
    - Route between preprocessing and extraction agents
    - Handle error recovery and retry logic
    - Monitor workflow progress
    """

    def __init__(self, config_path: str | None = None):
        self.logger = get_logger("agent.supervisor")
        self.llm_config = get_llm_config().supervisor
        self.config = SupervisorConfig(config_path)

        # Cache frequently used values
        self._system_prompt = self.config.get_system_prompt()
        self._decision_template = self.config.get_decision_prompt_template()

    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute the supervisor logic for workflow orchestration.

        Args:
            state: Current workflow state

        Returns:
            Updated state with supervisor decisions
        """
        log_agent_activity("supervisor", "Starting supervision", step=state.current_status, attempts=state.extraction_attempts)

        try:
            # Initialize supervision state
            state = self._initialize_supervision_state(state)

            # Make workflow decision using LLM with fallback
            next_action = await self._make_workflow_decision(state)

            # Update state with decision results
            state = self._update_state_with_decision(state, next_action)

            log_agent_activity(
                "supervisor",
                "Supervision completed",
                next_action=next_action,
                reasoning=state.supervisor_output.get("reasoning") if state.supervisor_output else None,
            )

            return state

        except Exception as e:
            return self._handle_execution_error(state, e)

    def _initialize_supervision_state(self, state: AgentState) -> AgentState:
        """
        Initialize the state for supervision processing.

        Args:
            state: Current workflow state

        Returns:
            State with supervision status set
        """
        state.current_status = "supervisao"
        state.status = ProcessingStatus.PROCESSING
        return state

    async def _make_workflow_decision(self, state: AgentState) -> str:
        """
        Make the primary workflow decision using LLM with deterministic fallback.

        Args:
            state: Current workflow state

        Returns:
            Next action to take
        """
        try:
            # Try LLM-based decision first
            return await self._use_llm_for_decision(state)
        except Exception as e:
            self.logger.warning(f"LLM decision failed, using fallback logic: {e}")
            # Fall back to deterministic logic
            return self._determine_next_action_deterministic(state)

    def _update_state_with_decision(self, state: AgentState, next_action: str) -> AgentState:
        """
        Update the state with the workflow decision and reasoning.

        Args:
            state: Current workflow state
            next_action: Determined next action

        Returns:
            Updated state with decision results
        """
        state.supervisor_output = {
            "next_action": next_action,
            "reasoning": self._get_reasoning(state, next_action),
            "timestamp": state.timestamp_inicio.isoformat(),
        }
        return state

    def _handle_execution_error(self, state: AgentState, error: Exception) -> AgentState:
        """
        Handle execution errors during supervision.

        Args:
            state: Current workflow state
            error: Exception that occurred

        Returns:
            State with error information
        """
        error_msg = f"Supervisor agent failed: {str(error)}"
        self.logger.error(error_msg, exc_info=True)
        state.add_error(error_msg)
        state.status = ProcessingStatus.ERROR
        return state

    async def _determine_next_action(self, state: AgentState) -> str:
        """
        Determine the next action based on current state (deterministic fallback).
        This method serves as a fallback when LLM decision-making fails.

        Args:
            state: Current workflow state

        Returns:
            Next action to take ('preprocess', 'extract', 'retry', 'finish', 'error')
        """
        return self._determine_next_action_deterministic(state)

    def _determine_next_action_deterministic(self, state: AgentState) -> str:
        """
        Deterministic logic for next action determination.

        Args:
            state: Current workflow state

        Returns:
            Next action to take
        """
        # If we have errors and haven't exceeded retry limits, suggest retry
        if state.errors and state.should_retry_extraction():
            return WorkflowAction.RETRY.value

        # If we have too many errors, finish with error
        if len(state.errors) > self.config.MAX_ERRORS_THRESHOLD:
            return WorkflowAction.ERROR.value

        # If text is not preprocessed yet, preprocess
        if not state.preprocessed_text:
            return WorkflowAction.PREPROCESS.value

        # If we don't have extracted data yet, extract
        if not state.extracted_data:
            return WorkflowAction.EXTRACT.value

        # If we have partial data and can retry, try again
        if state.extracted_data and self._is_extraction_incomplete(state) and state.should_retry_extraction():
            return WorkflowAction.RETRY.value

        # Otherwise, we're done
        return WorkflowAction.FINISH.value

    def _is_extraction_incomplete(self, state: AgentState) -> bool:
        """
        Check if the extraction is incomplete or needs improvement.

        Args:
            state: Current workflow state

        Returns:
            True if extraction should be retried
        """
        if not state.extracted_data:
            return True

        # Check if all key fields are missing
        data = state.extracted_data
        missing_fields = 0

        if not data.data_ocorrencia:
            missing_fields += 1
        if not data.local:
            missing_fields += 1
        if not data.tipo_incidente:
            missing_fields += 1
        if not data.impacto:
            missing_fields += 1

        # If more than threshold fields are missing, consider it incomplete
        return missing_fields > self.config.MAX_MISSING_FIELDS_THRESHOLD

    def _get_reasoning(self, state: AgentState, next_action: str) -> str:
        """Get human-readable reasoning using YAML configuration."""
        # Get base reason from config
        base_reason = self.config.get_action_reasoning(next_action)

        # Format retry message with attempt numbers
        if next_action == WorkflowAction.RETRY.value:
            base_reason = base_reason.format(attempt_number=state.extraction_attempts + 1, max_attempts=state.max_attempts)

        # Add context only when relevant
        context_info = self._build_context_info(state, next_action)

        return f"{base_reason}{context_info}" if context_info else base_reason

    def _build_context_info(self, state: AgentState, next_action: str) -> str:
        """
        Build context information for reasoning.

        Args:
            state: Current workflow state
            next_action: Determined next action

        Returns:
            Context information string or empty if not needed
        """
        context_parts = []

        # Only add context for actions that benefit from it
        if next_action in [WorkflowAction.RETRY.value, WorkflowAction.ERROR.value]:
            if state.errors:
                context_parts.append(f"{len(state.errors)} erro(s)")
            if state.warnings:
                context_parts.append(f"{len(state.warnings)} aviso(s)")

        if next_action == WorkflowAction.RETRY.value and state.extracted_data:
            if self._is_extraction_incomplete(state):
                context_parts.append("dados incompletos")

        return f" - {', '.join(context_parts)}" if context_parts else ""

    async def _use_llm_for_decision(self, state: AgentState) -> str:
        """
        Use LLM to make intelligent workflow decisions.

        Args:
            state: Current workflow state

        Returns:
            LLM-suggested next action
        """
        # Create enhanced prompt with context
        prompt = self._create_enhanced_decision_prompt(state)

        # Get LLM service manager
        service_manager = await get_llm_service_manager()

        # Enhanced system prompt for better decision making
        system_prompt = self._system_prompt

        # Generate decision using fallback services
        response = await service_manager.generate_with_fallback(["ollama", "openai"], prompt, system_prompt)

        # Parse and validate LLM response
        return self._parse_and_validate_llm_decision(response)

    def _create_enhanced_decision_prompt(self, state: AgentState) -> str:
        """Create enhanced prompt using YAML template with context analysis."""
        # Analyze error types for better context
        error_analysis = self._analyze_error_types(state.errors)

        # Calculate completion metrics
        completion_metrics = self._calculate_completion_metrics(state)

        # Format the template with actual values
        return self._decision_template.format(
            has_raw_text=self.config.PRESENT_INDICATOR if state.raw_text else self.config.ABSENT_INDICATOR,
            has_preprocessed_text=self.config.PRESENT_INDICATOR if state.preprocessed_text else self.config.ABSENT_INDICATOR,
            has_extracted_data=self.config.PRESENT_INDICATOR if state.extracted_data else self.config.ABSENT_INDICATOR,
            current_attempts=state.extraction_attempts,
            max_attempts=state.max_attempts,
            total_errors=len(state.errors),
            total_warnings=len(state.warnings),
            completion_rate=f"{completion_metrics['completion_rate']:.1%}",
            recoverable_errors=error_analysis["recoverable"],
            critical_errors=error_analysis["critical"],
            unknown_errors=error_analysis["unknown"],
            recent_errors=self._format_recent_errors(state.errors),
            extracted_fields_status=self._format_extracted_fields(state),
        )

    def _analyze_error_types(self, errors: list[str]) -> dict[str, int]:
        """
        Analyze error types for better decision making.

        Args:
            errors: List of error messages

        Returns:
            Dictionary with error type counts
        """
        analysis = {"recoverable": 0, "critical": 0, "unknown": 0}

        for error in errors:
            error_lower = error.lower()
            if any(keyword in error_lower for keyword in self.config.CRITICAL_KEYWORDS):
                analysis["critical"] += 1
            elif any(keyword in error_lower for keyword in self.config.RECOVERABLE_KEYWORDS):
                analysis["recoverable"] += 1
            else:
                analysis["unknown"] += 1

        return analysis

    def _calculate_completion_metrics(self, state: AgentState) -> dict[str, float]:
        """
        Calculate completion metrics for better analysis.

        Args:
            state: Current workflow state

        Returns:
            Dictionary with completion metrics
        """
        if not state.extracted_data:
            return {"completion_rate": 0.0}

        data = state.extracted_data
        total_fields = len(self.config.REQUIRED_FIELDS)
        completed_fields = 0

        for field in self.config.REQUIRED_FIELDS:
            if hasattr(data, field) and getattr(data, field):
                completed_fields += 1

        return {"completion_rate": completed_fields / total_fields}

    def _format_recent_errors(self, errors: list[str]) -> str:
        """Format recent errors for better readability."""
        if not errors:
            return self.config.NO_ERRORS_MESSAGE

        recent_errors = errors[-self.config.MAX_RECENT_ERRORS_TO_SHOW :]
        return "\n".join(f"- {error}" for error in recent_errors)

    def _format_extracted_fields(self, state: AgentState) -> str:
        """Format extracted fields status for analysis."""
        if not state.extracted_data:
            return self.config.NO_EXTRACTION_MESSAGE

        data = state.extracted_data
        fields_status = []

        for field in self.config.REQUIRED_FIELDS:
            field_name = field.replace("_", " ").title()
            has_value = hasattr(data, field) and getattr(data, field)
            indicator = self.config.PRESENT_INDICATOR if has_value else self.config.ABSENT_INDICATOR
            fields_status.append(f"{field_name}: {indicator}")

        return self.config.FIELD_SEPARATOR.join(fields_status)

    def _parse_and_validate_llm_decision(self, response: str) -> str:
        """
        Parse and validate LLM response with better error handling.

        Args:
            response: LLM response text

        Returns:
            Validated action string
        """
        response = response.strip().lower()

        # Map valid actions
        valid_actions = {action.value for action in WorkflowAction}

        # Find action in response
        for action in valid_actions:
            if action in response:
                return action

        # Enhanced fallback logic based on response content
        if any(word in response for word in ["erro", "error", "falha", "fail"]):
            return WorkflowAction.ERROR.value
        elif any(word in response for word in ["concluir", "finish", "done", "completo"]):
            return WorkflowAction.FINISH.value
        elif any(word in response for word in ["tentar", "retry", "repetir"]):
            return WorkflowAction.RETRY.value

        # Default fallback
        self.logger.warning(f"Could not parse LLM decision: '{response}', using extract as default")
        return WorkflowAction.EXTRACT.value

    async def handle_error_recovery(self, state: AgentState) -> AgentState:
        """
        Handle error recovery with improved analysis and decision making.

        Args:
            state: Current workflow state with errors

        Returns:
            Updated state with recovery decisions
        """
        log_agent_activity(
            "supervisor", "Handling error recovery", total_errors=len(state.errors), can_retry=state.should_retry_extraction()
        )

        # Enhanced error analysis
        error_analysis = self._analyze_error_types(state.errors)
        recovery_decision = self._make_recovery_decision(error_analysis, state)

        # Apply recovery decision
        state = self._apply_recovery_decision(state, recovery_decision, error_analysis)

        return state

    def _make_recovery_decision(self, error_analysis: dict[str, int], state: AgentState) -> str:
        """
        Make recovery decision based on error analysis.

        Args:
            error_analysis: Error type analysis
            state: Current state

        Returns:
            Recovery decision ('retry', 'terminate')
        """
        critical_errors = error_analysis["critical"]
        total_errors = len(state.errors)

        # Terminate if too many critical errors
        if critical_errors > self.config.MAX_CRITICAL_ERRORS_THRESHOLD:
            return "terminate"

        # Terminate if too many total errors
        if total_errors > self.config.MAX_ERRORS_THRESHOLD:
            return "terminate"

        # Terminate if can't retry anymore
        if not state.should_retry_extraction():
            return "terminate"

        # Otherwise, retry if we have recoverable errors
        return "retry" if error_analysis["recoverable"] > 0 else "terminate"

    def _apply_recovery_decision(self, state: AgentState, decision: str, error_analysis: dict[str, int]) -> AgentState:
        """
        Apply the recovery decision to the state.

        Args:
            state: Current state
            decision: Recovery decision
            error_analysis: Error analysis results

        Returns:
            Updated state
        """
        if decision == "terminate":
            state.add_error("Error recovery not possible - terminating processing")
            state.status = ProcessingStatus.ERROR
        else:  # retry
            recoverable_count = error_analysis["recoverable"]
            state.add_warning(f"Attempting recovery - {recoverable_count} recoverable errors found")
            state.status = ProcessingStatus.PROCESSING

        # Update supervisor output with recovery analysis
        self._update_recovery_analysis(state, decision, error_analysis)

        return state

    def _update_recovery_analysis(self, state: AgentState, decision: str, error_analysis: dict[str, int]) -> None:
        """
        Update supervisor output with recovery analysis.

        Args:
            state: Current state
            decision: Recovery decision
            error_analysis: Error analysis results
        """
        if state.supervisor_output is None:
            state.supervisor_output = {}

        recovery_strategy = "retry_with_modified_approach" if decision == "retry" else "terminate"

        state.supervisor_output.update(
            {
                "recovery_analysis": {
                    "recoverable_errors": error_analysis["recoverable"],
                    "critical_errors": error_analysis["critical"],
                    "unknown_errors": error_analysis["unknown"],
                    "recovery_possible": decision == "retry",
                    "recovery_strategy": recovery_strategy,
                    "decision_reason": self._get_recovery_reason(decision, error_analysis),
                }
            }
        )

    def _get_recovery_reason(self, decision: str, error_analysis: dict[str, int]) -> str:
        """
        Get human-readable reason for recovery decision.

        Args:
            decision: Recovery decision
            error_analysis: Error analysis results

        Returns:
            Recovery reason string
        """
        if decision == "retry":
            return f"Retry possible with {error_analysis['recoverable']} recoverable errors"
        else:
            reasons = []
            if error_analysis["critical"] > self.config.MAX_CRITICAL_ERRORS_THRESHOLD:
                reasons.append(f"{error_analysis['critical']} critical errors exceed threshold")
            if len(error_analysis) > self.config.MAX_ERRORS_THRESHOLD:
                reasons.append("total errors exceed threshold")
            return "Terminating: " + ", ".join(reasons) if reasons else "No recovery possible"

    async def finalize_processing(self, state: AgentState) -> AgentState:
        """
        Finalize the processing with improved status determination and metrics.

        Args:
            state: Current workflow state

        Returns:
            State with final status and comprehensive summary
        """
        log_agent_activity("supervisor", "Finalizing processing")

        # Determine final status based on extraction results
        state = self._determine_final_status(state)

        # Add comprehensive processing summary
        self._add_processing_summary(state)

        log_agent_activity("supervisor", "Processing finalized", final_status=state.status, processing_time=state.processing_time)

        return state

    def _determine_final_status(self, state: AgentState) -> AgentState:
        """
        Determine the final processing status.

        Args:
            state: Current workflow state

        Returns:
            State with updated final status
        """
        has_extracted_data = bool(state.extracted_data)
        is_complete = has_extracted_data and not self._is_extraction_incomplete(state)

        if is_complete:
            state.status = ProcessingStatus.SUCCESS
            state.current_status = "concluido"
        elif has_extracted_data:
            state.status = ProcessingStatus.PARTIAL_SUCCESS
            state.current_status = "concluido_parcial"
            state.add_warning("Extração parcialmente bem-sucedida")
        else:
            state.status = ProcessingStatus.ERROR
            state.current_status = "erro"
            state.add_error("Não foi possível extrair informações do incidente")

        return state

    def _add_processing_summary(self, state: AgentState) -> None:
        """
        Add comprehensive processing summary to supervisor output.

        Args:
            state: Current workflow state
        """
        if state.supervisor_output is None:
            state.supervisor_output = {}

        # Calculate success rate based on final status
        success_rates = {ProcessingStatus.SUCCESS: 1.0, ProcessingStatus.PARTIAL_SUCCESS: 0.5, ProcessingStatus.ERROR: 0.0}

        success_rate = success_rates.get(state.status, 0.0)

        # Get completion metrics
        completion_metrics = self._calculate_completion_metrics(state)

        state.supervisor_output.update(
            {
                "final_status": state.status,
                "processing_summary": {
                    "total_errors": len(state.errors),
                    "total_warnings": len(state.warnings),
                    "extraction_attempts": state.extraction_attempts,
                    "processing_time": state.processing_time,
                    "success_rate": success_rate,
                    "completion_rate": completion_metrics.get("completion_rate", 0.0),
                    "final_message": self._get_final_message(state),
                },
            }
        )

    def _get_final_message(self, state: AgentState) -> str:
        """
        Get final processing message based on status.

        Args:
            state: Current workflow state

        Returns:
            Final message string
        """
        messages = {
            ProcessingStatus.SUCCESS: "Processamento concluído com sucesso",
            ProcessingStatus.PARTIAL_SUCCESS: "Processamento parcialmente concluído",
            ProcessingStatus.ERROR: "Processamento finalizado com erro",
        }

        base_message = messages.get(state.status, "Status desconhecido")

        # Add context for partial success
        if state.status == ProcessingStatus.PARTIAL_SUCCESS and state.extracted_data:
            completion_metrics = self._calculate_completion_metrics(state)
            completion_pct = completion_metrics.get("completion_rate", 0.0) * 100
            base_message += f" ({completion_pct:.0f}% dos campos extraídos)"

        return base_message
