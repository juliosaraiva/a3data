"""LangGraph workflow definition for the incident extraction system."""

import asyncio
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from incident_extractor.agents import (
    ExtractorAgent,
    PreprocessorAgent,
    SupervisorAgent,
)
from incident_extractor.config.logging import get_logger, log_agent_activity
from incident_extractor.models.schemas import AgentState, ProcessingStatus


class IncidentExtractionWorkflow:
    """
    LangGraph workflow for incident information extraction.

    This workflow coordinates three agents:
    1. Supervisor: Orchestrates the process and makes routing decisions
    2. Preprocessor: Cleans and normalizes input text
    3. Extractor: Extracts structured incident information
    """

    def __init__(self):
        self.logger = get_logger("workflow.incident_extraction")

        # Initialize agents
        self.supervisor = SupervisorAgent()
        self.preprocessor = PreprocessorAgent()
        self.extractor = ExtractorAgent()

        # Build the workflow graph
        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledStateGraph[AgentState]:
        """
        Build the LangGraph state graph.

        Returns:
            Compiled state graph
        """
        self.logger.info("Building incident extraction workflow graph")

        # Create the state graph
        workflow: StateGraph[AgentState] = StateGraph(AgentState)

        # Add nodes for each agent
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("preprocessor", self._preprocessor_node)
        workflow.add_node("extractor", self._extractor_node)
        workflow.add_node("error_handler", self._error_handler_node)
        workflow.add_node("finalizer", self._finalizer_node)

        # Define the workflow edges
        workflow.add_edge(START, "supervisor")

        # Conditional routing from supervisor
        workflow.add_conditional_edges(
            "supervisor",
            self._route_from_supervisor,
            {
                "preprocess": "preprocessor",
                "extract": "extractor",
                "error": "error_handler",
                "retry": "extractor",
                "finish": "finalizer",
            },
        )

        # From preprocessor, always go back to supervisor
        workflow.add_edge("preprocessor", "supervisor")

        # From extractor, go back to supervisor for evaluation
        workflow.add_edge("extractor", "supervisor")

        # Finalizer always ends the workflow
        workflow.add_edge("finalizer", END)

        # Compile the graph
        compiled_graph: CompiledStateGraph[AgentState] = workflow.compile()

        self.logger.info("Incident extraction workflow graph compiled successfully")
        return compiled_graph

    async def _supervisor_node(self, state: AgentState) -> AgentState:
        """
        Execute the supervisor agent.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        log_agent_activity("workflow", "Executing supervisor node")
        return await self.supervisor.execute(state)

    async def _preprocessor_node(self, state: AgentState) -> AgentState:
        """
        Execute the preprocessor agent.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        log_agent_activity("workflow", "Executing preprocessor node")
        return await self.preprocessor.execute(state)

    async def _extractor_node(self, state: AgentState) -> AgentState:
        """
        Execute the extractor agent.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        log_agent_activity("workflow", "Executing extractor node")
        return await self.extractor.execute(state)

    async def _error_handler_node(self, state: AgentState) -> AgentState:
        """
        Handle errors and determine recovery strategy.

        Args:
            state: Current workflow state with errors

        Returns:
            Updated state with error handling decisions
        """
        log_agent_activity("workflow", "Executing error handler node", errors=len(state.errors))
        return await self.supervisor.handle_error_recovery(state)

    async def _finalizer_node(self, state: AgentState) -> AgentState:
        """
        Finalize the workflow processing.

        Args:
            state: Current workflow state

        Returns:
            Final state
        """
        log_agent_activity("workflow", "Executing finalizer node")
        return await self.supervisor.finalize_processing(state)

    def _route_from_supervisor(self, state: AgentState) -> Literal["preprocess", "extract", "retry", "finish", "error"]:
        """
        Route from supervisor based on state analysis.

        Args:
            state: Current workflow state

        Returns:
            Next node to execute
        """
        # Get supervisor decision from the state
        next_action: str | None = None
        if isinstance(state.supervisor_output, dict):
            next_action = state.supervisor_output.get("next_action", "error")

        log_agent_activity(
            "workflow",
            "Routing from supervisor",
            next_action=next_action if next_action else None,
            reasoning=state.supervisor_output.get("reasoning", "No reasoning provided")
            if isinstance(state.supervisor_output, dict)
            else None,
        )

        # Map supervisor decisions to valid routing options
        routing_map: dict[str, Literal["preprocess", "extract", "retry", "finish", "error"]] = {
            "preprocess": "preprocess",
            "extract": "extract",
            "retry": "retry",
            "finish": "finish",
            "error": "error",
        }

        return routing_map.get(next_action, "error") if next_action else "error"

    def _route_from_error_handler(self, state: AgentState) -> Literal["retry", "finish"]:
        """Route from error handler based on recovery analysis.

        Args:
            state: Current workflow state

        Returns:
            Next action (retry or finish)
        """
        # Check if recovery is possible
        recovery_info: dict[str, Any] = {}
        if isinstance(state.supervisor_output, dict):
            recovery_info = state.supervisor_output.get("recovery_analysis", {})
        can_recover = recovery_info.get("recovery_possible", False)

        if can_recover and state.should_retry_extraction():
            log_agent_activity("workflow", "Error recovery: retrying")
            return "retry"
        else:
            log_agent_activity("workflow", "Error recovery: finishing")
            return "finish"

    async def run(self, texto: str, options: dict[str, Any] | None = None) -> AgentState:
        """
        Run the complete incident extraction workflow.

        Args:
            texto: Input incident text in Portuguese
            options: Optional processing options

        Returns:
            Final workflow state with results
        """
        log_agent_activity("workflow", "Starting incident extraction workflow", text_length=len(texto), options=options or {})

        try:
            # Initialize workflow state
            initial_state = AgentState(
                raw_text=texto,
                options=options or {},
                status=ProcessingStatus.PENDING,
                current_status="inicio",
            )

            # Execute the workflow
            final_state_dict = await self.graph.ainvoke(initial_state)

            # Convert dict result back to AgentState
            final_state = AgentState(**final_state_dict)

            log_agent_activity(
                "workflow",
                "Incident extraction workflow completed",
                final_status=final_state.status,
                processing_time=final_state.processing_time,
                errors=final_state.errors,
                warnings=final_state.warnings,
            )

            return final_state

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}", exc_info=True)

            # Create error state
            error_state = AgentState(
                raw_text=texto, options=options or {}, status=ProcessingStatus.ERROR, current_status="erro_critico"
            )
            error_state.add_error(f"Workflow execution failed: {str(e)}")

            return error_state

    async def run_with_timeout(self, texto: str, options: dict[str, Any] | None = None, timeout: int = 120) -> AgentState:
        """
        Run workflow with timeout protection.

        Args:
            texto: Input incident text
            options: Processing options
            timeout: Timeout in seconds

        Returns:
            Final workflow state
        """
        try:
            return await asyncio.wait_for(self.run(texto, options), timeout=timeout)
        except TimeoutError:
            self.logger.error(f"Workflow timed out after {timeout} seconds")

            # Create timeout error state
            timeout_state = AgentState(
                raw_text=texto, options=options or {}, status=ProcessingStatus.ERROR, current_status="timeout"
            )
            timeout_state.add_error(f"Workflow timed out after {timeout} seconds")

            return timeout_state

    def get_workflow_info(self) -> dict[str, Any]:
        """
        Get information about the workflow structure.

        Returns:
            Workflow information
        """
        return {
            "workflow_type": "incident_extraction",
            "agents": ["supervisor", "preprocessor", "extractor"],
            "nodes": ["supervisor", "preprocessor", "extractor", "error_handler", "finalizer"],
            "features": ["multi_agent_coordination", "error_recovery", "retry_logic", "state_persistence", "conditional_routing"],
            "supported_languages": ["portuguese"],
            "output_format": {
                "data_ocorrencia": "YYYY-MM-DD HH:MM",
                "local": "string",
                "tipo_incidente": "string",
                "impacto": "string",
            },
        }

    async def validate_workflow(self) -> dict[str, bool]:
        """
        Validate that the workflow is properly configured.

        Returns:
            Validation results
        """
        validation_results: dict[str, bool] = {}

        try:
            # Test agents initialization
            validation_results["supervisor_initialized"] = True if self.supervisor else False
            validation_results["preprocessor_initialized"] = True if self.preprocessor else False
            validation_results["extractor_initialized"] = True if self.extractor else False

            # Test graph compilation
            validation_results["graph_compiled"] = True if self.graph else False

            # Test a dry run with minimal input
            test_state = AgentState(
                raw_text="Teste de incidente",
                options={},
                status=ProcessingStatus.PENDING,
                current_status="inicio",
            )

            # This should not actually run, just test state structure
            validation_results["state_structure_valid"] = True if test_state else False

            self.logger.info("Workflow validation completed", results=validation_results)

        except Exception as e:
            self.logger.error(f"Workflow validation failed: {e}")
            validation_results["validation_failed"] = True

        return validation_results


# Global workflow instance
_workflow_instance = None


async def get_workflow() -> IncidentExtractionWorkflow:
    """
    Get the global workflow instance.

    Returns:
        IncidentExtractionWorkflow instance
    """
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = IncidentExtractionWorkflow()

        # Validate the workflow
        validation_results = await _workflow_instance.validate_workflow()
        if "validation_failed" in validation_results:
            raise RuntimeError(f"Workflow validation failed: {validation_results['validation_failed']}")

    return _workflow_instance


async def extract_incident_info(text: str, options: dict[str, Any] | None = None) -> AgentState:
    """
    Convenience function to extract incident information.

    Args:
        text: Input incident text in Portuguese
        options: Optional processing options

    Returns:
        Final workflow state with extracted information
    """
    workflow = await get_workflow()
    return await workflow.run_with_timeout(text, options)
