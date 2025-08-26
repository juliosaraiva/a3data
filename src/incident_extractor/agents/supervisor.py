"""Supervisor agent for orchestrating the incident extraction workflow."""

from incident_extractor.config.llm import get_llm_config
from incident_extractor.config.logging import get_logger, log_agent_activity
from incident_extractor.models.schemas import AgentState, ProcessingStatus
from incident_extractor.services.llm_service import get_llm_service_manager


class SupervisorAgent:
    """
    Supervisor agent that orchestrates the multi-agent workflow.

    Responsibilities:
    - Coordinate the overall extraction process
    - Route between preprocessing and extraction agents
    - Handle error recovery and retry logic
    - Monitor workflow progress
    """

    def __init__(self):
        self.logger = get_logger("agent.supervisor")
        self.config = get_llm_config().supervisor

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
            # Update state
            state.current_status = "supervisao"
            state.status = ProcessingStatus.PROCESSING

            # Analyze the current state and determine next steps
            next_action = await self._determine_next_action(state)

            # Update supervisor output with decision
            state.supervisor_output = {
                "next_action": next_action,
                "reasoning": self._get_reasoning(state, next_action),
                "timestamp": state.timestamp_inicio.isoformat(),
            }

            log_agent_activity(
                "supervisor", "Supervision completed", next_action=next_action, reasoning=state.supervisor_output.get("reasoning")
            )

            return state

        except Exception as e:
            error_msg = f"Supervisor agent failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            state.add_error(error_msg)
            state.status = ProcessingStatus.ERROR
            return state

    async def _determine_next_action(self, state: AgentState) -> str:
        """
        Determine the next action based on current state.

        Args:
            state: Current workflow state

        Returns:
            Next action to take ('preprocess', 'extract', 'retry', 'finish', 'error')
        """
        # If we have errors and haven't exceeded retry limits, suggest retry
        if state.errors and state.should_retry_extraction():
            return "retry"

        # If we have too many errors, finish with error
        if len(state.errors) > 3:
            return "error"

        # If text is not preprocessed yet, preprocess
        if not state.preprocessed_text:
            return "preprocess"

        # If we don't have extracted data yet, extract
        if not state.extracted_data:
            return "extract"

        # If we have partial data and can retry, try again
        if state.extracted_data and self._is_extraction_incomplete(state) and state.should_retry_extraction():
            return "retry"

        # Otherwise, we're done
        return "finish"

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

        # If more than 2 fields are missing, consider it incomplete
        return missing_fields > 2

    def _get_reasoning(self, state: AgentState, next_action: str) -> str:
        """
        Get human-readable reasoning for the decision.

        Args:
            state: Current workflow state
            next_action: Determined next action

        Returns:
            Reasoning string
        """
        reasoning_map = {
            "preprocess": "Texto original precisa ser pré-processado para normalização",
            "extract": "Texto pré-processado está pronto para extração de informações",
            "retry": f"Extração anterior falhou ou incompleta, tentativa {state.extraction_attempts + 1} de {state.max_attempts}",
            "finish": "Extração concluída com sucesso",
            "error": "Muitos erros encontrados, finalizando com falha",
        }

        base_reason = reasoning_map.get(next_action, f"Ação não reconhecida: {next_action}")

        # Add context
        context_parts: list[str] = []
        if state.errors:
            context_parts.append(f"{len(state.errors)} erro(s) encontrado(s)")
        if state.warnings:
            context_parts.append(f"{len(state.warnings)} aviso(s)")
        if state.extracted_data and self._is_extraction_incomplete(state):
            context_parts.append("extração incompleta detectada")

        if context_parts:
            return f"{base_reason}. Contexto: {', '.join(context_parts)}"

        return base_reason

    async def _use_llm_for_decision(self, state: AgentState) -> str:
        """
        Use LLM to help make complex routing decisions.

        Args:
            state: Current workflow state

        Returns:
            LLM-suggested next action
        """
        try:
            # Create a prompt for the LLM to analyze the state
            prompt = self._create_decision_prompt(state)

            # Get LLM service manager
            service_manager = await get_llm_service_manager()

            # Generate decision using fallback services
            response = await service_manager.generate_with_fallback(["ollama", "openai"], prompt, self.config.system_prompt)

            # Parse LLM response to extract decision
            return self._parse_llm_decision(response)

        except Exception as e:
            self.logger.warning(f"LLM decision failed, using fallback logic: {e}")
            # Fall back to deterministic logic
            return await self._determine_next_action(state)

    def _create_decision_prompt(self, state: AgentState) -> str:
        """Create prompt for LLM-based decision making."""
        return f"""
Analise o estado atual do workflow de extração de incidentes e determine a próxima ação.

Estado atual:
- Etapa: {state.current_status}
- Status: {state.status}
- Texto original disponível: {"Sim" if state.raw_text else "Não"}
- Texto pré-processado: {"Sim" if state.preprocessed_text else "Não"}
- Dados extraídos: {"Sim" if state.extracted_data else "Não"}
- Tentativas de extração: {state.extraction_attempts}/{state.max_attempts}
- Erros: {len(state.errors)}
- Avisos: {len(state.warnings)}

Erros encontrados:
{chr(10).join(f"- {erro}" for erro in state.errors[-3:]) if state.errors else "Nenhum"}

Responda APENAS com uma das seguintes opções:
- preprocess: Se o texto precisa ser pré-processado
- extract: Se está pronto para extração
- retry: Se deve tentar extrair novamente
- finish: Se o processo está completo
- error: Se deve finalizar com erro

Resposta:"""

    def _parse_llm_decision(self, response: str) -> str:
        """Parse LLM response to extract decision."""
        response = response.strip().lower()

        valid_actions = ["preprocess", "extract", "retry", "finish", "error"]

        for action in valid_actions:
            if action in response:
                return action

        # Default fallback
        self.logger.warning(f"Could not parse LLM decision: {response}")
        return "extract"

    async def handle_error_recovery(self, state: AgentState) -> AgentState:
        """
        Handle error recovery and determine if processing should continue.

        Args:
            state: Current workflow state with errors

        Returns:
            Updated state with recovery decisions
        """
        log_agent_activity(
            "supervisor", "Handling error recovery", total_errors=len(state.errors), can_retry=state.should_retry_extraction()
        )

        # Analyze errors to determine if they're recoverable
        recoverable_errors = 0
        critical_errors = 0

        for error in state.errors:
            if any(keyword in error.lower() for keyword in ["timeout", "connection", "temporary"]):
                recoverable_errors += 1
            elif any(keyword in error.lower() for keyword in ["validation", "format", "parsing"]):
                critical_errors += 1
            else:
                recoverable_errors += 1

        # Decision logic for error recovery
        if critical_errors > 2:
            state.add_error("Too many critical errors, stopping processing")
            state.status = ProcessingStatus.ERROR
        elif recoverable_errors > 0 and state.should_retry_extraction():
            state.add_warning(f"Attempting recovery, {recoverable_errors} recoverable errors found")
            state.status = ProcessingStatus.PROCESSING
        else:
            state.add_error("Error recovery not possible or max retries exceeded")
            state.status = ProcessingStatus.ERROR

        # Update supervisor output with recovery analysis
        if state.supervisor_output is None:
            state.supervisor_output = {}
        state.supervisor_output.update(
            {
                "recovery_analysis": {
                    "recoverable_errors": recoverable_errors,
                    "critical_errors": critical_errors,
                    "recovery_possible": state.status == ProcessingStatus.PROCESSING,
                    "recovery_strategy": "retry_with_modified_approach"
                    if state.status == ProcessingStatus.PROCESSING
                    else "terminate",
                }
            }
        )

        return state

    async def finalize_processing(self, state: AgentState) -> AgentState:
        """
        Finalize the processing and set final status.

        Args:
            state: Current workflow state

        Returns:
            State with final status
        """
        log_agent_activity("supervisor", "Finalizing processing")

        # Determine final status
        if state.extracted_data and not self._is_extraction_incomplete(state):
            state.status = ProcessingStatus.SUCCESS
            state.current_status = "concluido"
        elif state.extracted_data:
            state.status = ProcessingStatus.PARTIAL_SUCCESS
            state.current_status = "concluido_parcial"
            state.add_warning("Extração parcialmente bem-sucedida")
        else:
            state.status = ProcessingStatus.ERROR
            state.current_status = "erro"
            state.add_error("Não foi possível extrair informações do incidente")

        # Calculate processing time
        if state.processing_time is None:
            pass

        # Add final summary to supervisor output
        if state.supervisor_output is None:
            state.supervisor_output = {}
        state.supervisor_output.update(
            {
                "final_status": state.status,
                "processing_summary": {
                    "total_errors": len(state.errors),
                    "total_warnings": len(state.warnings),
                    "extraction_attempts": state.extraction_attempts,
                    "processing_time": state.processing_time,
                    "success_rate": 1.0
                    if state.status == ProcessingStatus.SUCCESS
                    else 0.5
                    if state.status == ProcessingStatus.PARTIAL_SUCCESS
                    else 0.0,
                },
            }
        )

        log_agent_activity("supervisor", "Processing finalized", final_status=state.status, processing_time=state.processing_time)

        return state
