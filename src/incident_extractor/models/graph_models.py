"""Graph state models for LangGraph workflow."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    """Result from an individual agent."""

    agent_name: str
    success: bool = True
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    execution_time_ms: Optional[int] = None


class GraphState(BaseModel):
    """Shared state object for the LangGraph workflow."""

    # Input data
    original_text: str
    processed_text: Optional[str] = None

    # Agent results
    preprocessor_result: Optional[AgentResult] = None
    datetime_result: Optional[AgentResult] = None
    location_result: Optional[AgentResult] = None
    incident_type_result: Optional[AgentResult] = None
    impact_result: Optional[AgentResult] = None

    # Final extraction results
    extracted_data: Optional[Dict[str, Any]] = None

    # Metadata
    graph_execution_id: str
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_execution_time_ms: Optional[int] = None

    # Error handling
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    # Configuration
    use_fallback: bool = False
    retry_count: int = 0
    max_retries: int = 3

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True

    def add_agent_result(self, agent_name: str, result: AgentResult) -> None:
        """Add result from an agent."""
        setattr(self, f"{agent_name}_result", result)

        if not result.success and result.error:
            self.errors.append(f"{agent_name}: {result.error}")

    def get_agent_result(self, agent_name: str) -> Optional[AgentResult]:
        """Get result from a specific agent."""
        return getattr(self, f"{agent_name}_result", None)

    def is_extraction_complete(self) -> bool:
        """Check if all extraction agents have completed."""
        required_agents = ["datetime", "location", "incident_type", "impact"]
        return all(self.get_agent_result(agent) is not None for agent in required_agents)

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def should_retry(self) -> bool:
        """Check if the workflow should retry."""
        return self.retry_count < self.max_retries and self.has_errors()

    def increment_retry(self) -> None:
        """Increment retry counter."""
        self.retry_count += 1

    def finalize(self) -> None:
        """Finalize the state with timing information."""
        self.end_time = datetime.now()
        if self.start_time:
            delta = self.end_time - self.start_time
            self.total_execution_time_ms = int(delta.total_seconds() * 1000)


class GraphConfig(BaseModel):
    """Configuration for graph execution."""

    max_iterations: int = Field(default=10, ge=1, le=100)
    parallel_execution: bool = True
    enable_retries: bool = True
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout_seconds: int = Field(default=60, ge=1, le=300)

    # Agent-specific configuration
    agent_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    agent_timeout: int = Field(default=15, ge=1, le=60)

    # Fallback configuration
    enable_fallback: bool = True
    fallback_on_partial_failure: bool = True
