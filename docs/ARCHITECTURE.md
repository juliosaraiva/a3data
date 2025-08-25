# Incident Extractor API - Architecture Documentation

## 📋 Overview

The Incident Extractor API is an intelligent system designed to extract structured information from IT incident reports written in Brazilian Portuguese. Using a multi-agent approach powered by Large Language Models (LLMs) and orchestrated through LangGraph, the system transforms unstructured incident descriptions into structured data.

### Key Capabilities

- **Multi-Agent Processing**: Coordinated workflow with specialized agents
- **LLM Provider Flexibility**: Support for Ollama, OpenAI, and Mock providers
- **Brazilian Localization**: Native support for Portuguese language and Brazilian date/time formats
- **Resilient Processing**: Automatic retry logic and error recovery
- **Real-time Monitoring**: Health checks, metrics, and structured logging

### Architecture at a Glance

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   LangGraph      │    │   LLM Service   │
│   Presentation  │───▶│   Workflow       │───▶│   Abstraction   │
│   Layer         │    │   Orchestration  │    │   Layer         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Configuration │    │   Agent System   │    │   External LLMs │
│   & Settings    │    │   (3 Agents)     │    │   (Ollama/OpenAI)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🏗️ Architecture Principles

### Clean Architecture
- **Separation of Concerns**: Clear boundaries between layers
- **Dependency Inversion**: Abstractions don't depend on details
- **Single Responsibility**: Each component has one reason to change
- **Interface Segregation**: Clients depend only on interfaces they use

### Multi-Agent Design
- **Specialized Agents**: Each agent handles a specific aspect of processing
- **Coordinated Workflow**: LangGraph orchestrates agent interactions
- **State Management**: Shared state tracks progress across agents
- **Fault Tolerance**: Error recovery and retry mechanisms

### Configuration-Driven
- **Environment-based**: All configuration through environment variables
- **Type-Safe**: Pydantic models ensure configuration validation
- **Flexible Deployment**: Easy adaptation across environments

## 🎯 System Architecture

### High-Level Architecture

```
                    ┌─────────────────────────────────────────────────┐
                    │                FastAPI Application              │
                    │  ┌─────────────┐ ┌──────────────┐ ┌──────────┐ │
                    │  │  /extract   │ │   /health    │ │ /metrics │ │
                    │  │  endpoint   │ │   endpoint   │ │ endpoint │ │
                    │  └─────────────┘ └──────────────┘ └──────────┘ │
                    └─────────────────┬───────────────────────────────┘
                                      │
                    ┌─────────────────▼───────────────────────────────┐
                    │             LangGraph Workflow                  │
                    │                                                 │
                    │  START ──► Supervisor ──► Preprocessor         │
                    │               │               │                 │
                    │               ▼               ▼                 │
                    │           Extractor ◄──── Supervisor           │
                    │               │               │                 │
                    │               ▼               ▼                 │
                    │         Error Handler ──► Finalizer ──► END    │
                    └─────────────────┬───────────────────────────────┘
                                      │
                    ┌─────────────────▼───────────────────────────────┐
                    │              Agent System                       │
                    │                                                 │
                    │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
                    │  │ Supervisor  │ │Preprocessor │ │ Extractor   ││
                    │  │   Agent     │ │   Agent     │ │   Agent     ││
                    │  │             │ │             │ │             ││
                    │  │ • Routing   │ │ • Text      │ │ • Info      ││
                    │  │ • Control   │ │   Cleanup   │ │   Extract   ││
                    │  │ • Recovery  │ │ • Context   │ │ • Validate  ││
                    │  └─────────────┘ └─────────────┘ └─────────────┘│
                    └─────────────────┬───────────────────────────────┘
                                      │
                    ┌─────────────────▼───────────────────────────────┐
                    │             LLM Service Layer                   │
                    │                                                 │
                    │         ┌─────────────────────────────────┐     │
                    │         │    LLM Service Manager          │     │
                    │         │  • Provider Selection           │     │
                    │         │  • Fallback Handling            │     │
                    │         │  • Connection Management        │     │
                    │         └─────────────────────────────────┘     │
                    │                                                 │
                    │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
                    │  │   Ollama    │ │   OpenAI    │ │    Mock     ││
                    │  │  Service    │ │  Service    │ │  Service    ││
                    │  └─────────────┘ └─────────────┘ └─────────────┘│
                    └─────────────────────────────────────────────────┘
```

### Folder Structure

```
src/incident_extractor/
├── agents/              # Multi-agent system implementation
│   ├── __init__.py
│   ├── supervisor.py    # Workflow orchestration agent
│   ├── preprocessor.py  # Text cleaning and normalization agent
│   └── extractor.py     # Information extraction agent
├── config/              # Configuration and settings
│   ├── __init__.py
│   ├── config.py        # Application settings
│   ├── llm.py          # LLM-specific configuration
│   └── logging.py      # Logging configuration
├── graph/               # LangGraph workflow definition
│   ├── __init__.py
│   └── workflow.py     # Workflow orchestration logic
├── models/              # Data models and schemas
│   ├── __init__.py
│   ├── schemas.py      # Pydantic models for API and internal use
│   └── graph_models.py # LangGraph state models
├── services/            # Service layer abstractions
│   ├── __init__.py
│   └── llm_service.py  # LLM service implementations
└── main.py             # FastAPI application entry point
```

## 🔧 Core Components

### 1. Multi-Agent System (`src/incident_extractor/agents/`)

#### Supervisor Agent (`supervisor.py`)
- **Purpose**: Orchestrates the entire workflow and makes routing decisions
- **Responsibilities**:
  - Analyze workflow state and determine next actions
  - Route between preprocessing and extraction agents
  - Handle error recovery and retry logic
  - Monitor overall workflow progress
- **Key Methods**:
  - `execute()`: Main workflow coordination logic
  - `_determine_next_action()`: Decision-making logic
  - `handle_error_recovery()`: Error recovery strategies

#### Preprocessor Agent (`preprocessor.py`)
- **Purpose**: Cleans and normalizes input text for better extraction
- **Responsibilities**:
  - Remove noise and irrelevant content
  - Standardize format and structure
  - Add contextual information when needed
  - Prepare text for LLM consumption
- **Key Features**:
  - Portuguese text normalization
  - Context enhancement for dates and locations
  - Text length optimization

#### Extractor Agent (`extractor.py`)
- **Purpose**: Extracts structured information from incident text
- **Responsibilities**:
  - Generate structured prompts for LLMs
  - Parse LLM responses into structured data
  - Validate and enhance extracted information
  - Handle multiple extraction strategies
- **Output Format**:
  ```json
  {
    "data_ocorrencia": "YYYY-MM-DD HH:MM",
    "local": "string",
    "tipo_incidente": "string", 
    "impacto": "string"
  }
  ```

### 2. LangGraph Workflow (`src/incident_extractor/graph/workflow.py`)

#### Workflow States
```
START → Supervisor → [Preprocessor|Extractor] → Supervisor → [Retry|Finish] → END
                  ↓                                       ↑
              Error Handler → [Retry|Finish] → Finalizer
```

#### State Management
- **AgentState**: Central state object tracking workflow progress
- **State Transitions**: Controlled transitions between workflow stages
- **Error Handling**: Automatic error detection and recovery

#### Key Features
- **Conditional Routing**: Dynamic decision-making based on state
- **Retry Logic**: Automatic retry with exponential backoff
- **Timeout Protection**: Configurable timeouts to prevent hanging
- **State Persistence**: Complete audit trail of processing steps

### 3. LLM Service Layer (`src/incident_extractor/services/llm_service.py`)

#### Service Abstraction
- **BaseLLMService**: Abstract interface for all LLM providers
- **Provider Implementations**: Concrete implementations for each LLM provider
- **Fallback Mechanism**: Automatic provider switching on failures

#### Supported Providers

| Provider | Primary Use | Configuration |
|----------|-------------|---------------|
| **Ollama** | Local development, privacy-focused | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` |
| **OpenAI** | Production, high accuracy | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| **Mock** | Testing, development | No external dependencies |

#### Service Manager
- **Provider Selection**: Automatic provider selection based on configuration
- **Connection Pooling**: Efficient connection management
- **Error Handling**: Retry logic and fallback strategies
- **Performance Monitoring**: Request timing and success rates

### 4. Configuration System (`src/incident_extractor/config/`)

#### Application Settings (`config.py`)
```python
# Environment-driven configuration
class Settings(BaseSettings):
    # Application
    app_name: str = "Incident Extractor API"
    app_version: str = "0.1.0" 
    debug: bool = False
    
    # LLM Providers
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    openai_api_key: Optional[str] = None
    
    # Performance
    max_concurrent_requests: int = 10
    request_timeout: int = 120
```

#### LLM Configuration (`llm.py`)
- **Agent-Specific Settings**: Different LLM configs for each agent
- **Model Parameters**: Temperature, top_k, top_p, max_tokens
- **Prompt Templates**: Specialized prompts for Brazilian Portuguese

### 5. Data Models (`src/incident_extractor/models/schemas.py`)

#### Core Models

```python
# Request/Response Models
class ExtractionRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000)
    options: Dict[str, Any] = Field(default_factory=dict)

class IncidentData(BaseModel):
    data_ocorrencia: Optional[str] = None
    local: Optional[str] = None
    tipo_incidente: Optional[str] = None
    impacto: Optional[str] = None

# State Management
class AgentState(BaseModel):
    raw_text: str
    status: ProcessingStatus
    current_status: str
    extracted_data: Optional[IncidentData] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
```

## 🔄 Data Flow

### End-to-End Processing Flow

```
1. Request Reception
   └─ FastAPI receives POST /extract request
   └─ Validates input format and length
   └─ Creates initial AgentState

2. Workflow Initialization  
   └─ LangGraph workflow starts
   └─ Supervisor agent analyzes input
   └─ Routes to appropriate next step

3. Text Preprocessing (Optional)
   └─ Preprocessor agent cleans text
   └─ Normalizes Portuguese content
   └─ Adds contextual information

4. Information Extraction
   └─ Extractor agent creates prompt
   └─ LLM Service generates response  
   └─ Parses structured data
   └─ Validates output format

5. Quality Control
   └─ Supervisor evaluates results
   └─ Decides on retry/completion
   └─ Handles error scenarios

6. Response Formation
   └─ Finalizer prepares response
   └─ Updates metrics and logs
   └─ Returns structured result
```

### Error Handling Flow

```
Error Detected
     │
     ▼
Is Recoverable?
     ├─ Yes ──► Increment Retry Count ──► Max Retries?
     │                                      ├─ No ──► Retry Processing
     │                                      └─ Yes ──► Return Partial/Error
     │
     └─ No ──► Log Error ──► Return Error Response
```

### State Transitions

```python
PENDING → PROCESSING → [SUCCESS | PARTIAL_SUCCESS | ERROR]
    │                              │
    └─ Can retry? ─► Yes ───────────┘
    └─ Can't retry ─► ERROR
```

## 🛠️ Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Runtime** | Python | 3.13+ | Primary language |
| **Web Framework** | FastAPI | 0.116.1+ | REST API implementation |
| **Agent Orchestration** | LangGraph | 0.6.6+ | Multi-agent workflow |
| **LLM Integration** | LangChain | 0.3.27+ | LLM provider abstraction |
| **Data Validation** | Pydantic | 2.11.7+ | Type-safe data models |
| **Configuration** | Pydantic Settings | 2.10.1+ | Environment-driven config |
| **HTTP Client** | HTTPX | 0.28.0+ | Async HTTP requests |
| **Logging** | Structlog | 24.4.0+ | Structured logging |

### Development & Testing

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Testing** | Pytest | 8.4.1+ | Unit and integration testing |
| **Async Testing** | Pytest-Asyncio | 1.1.0+ | Async test support |
| **Code Quality** | Ruff | 0.12.9+ | Linting and formatting |
| **Type Checking** | Pyright | 1.1.390+ | Static type analysis |
| **Coverage** | Pytest-Cov | 6.0.0+ | Code coverage reporting |

### LLM Providers

| Provider | Use Case | Requirements |
|----------|----------|-------------|
| **Ollama** | Local development, privacy | Local Ollama installation |
| **OpenAI** | Production, high accuracy | OpenAI API key |
| **Mock** | Testing, development | No external dependencies |

## ⚙️ Configuration & Deployment

### Environment Configuration

#### Required Environment Variables
```bash
# Application Settings
APP_NAME="Incident Extractor API"
APP_VERSION="0.1.0"
DEBUG=false
ENVIRONMENT=production

# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OPENAI_API_KEY=sk-...  # Optional

# Performance Settings  
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=120
MAX_PREPROCESSING_LENGTH=5000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

#### Configuration Validation
```python
# All settings are validated at startup
@lru_cache()
def get_settings() -> Settings:
    return Settings()  # Automatic .env loading and validation
```

### Deployment Options

#### Development
```bash
# Quick setup
make quick-start

# Manual setup
uv sync --dev
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Production  
```bash
# Docker deployment
docker-compose up -d

# Direct deployment
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

#### Health Checks
- **Endpoint**: `GET /health`
- **Components Checked**: LLM services, workflow validation, system metrics
- **Response**: Structured health status with component details

## 📊 Monitoring & Observability

### Structured Logging

#### Log Levels
- **INFO**: Workflow progress, successful operations
- **WARNING**: Retry attempts, partial failures
- **ERROR**: System errors, failed operations
- **DEBUG**: Detailed execution traces (development only)

#### Log Structure
```json
{
  "timestamp": "2025-01-20T10:30:45.123Z",
  "level": "info",
  "logger": "agent.extractor",
  "event": "extraction_completed", 
  "agent": "extractor",
  "attempt": 1,
  "confidence": 0.92,
  "fields_extracted": 4,
  "processing_time": 1.23
}
```

### Metrics & Monitoring

#### Key Metrics (`GET /metrics`)
```python
class ProcessingMetrics(BaseModel):
    total_requests: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    average_processing_time: float = 0.0
    total_processing_time: float = 0.0
    agent_execution_times: Dict[str, float] = Field(default_factory=dict)
    llm_provider_usage: Dict[str, int] = Field(default_factory=dict)
```

#### Health Check Components
- **LLM Service Availability**: Tests connection to configured providers
- **Workflow Validation**: Ensures workflow graph is properly compiled
- **System Resources**: Memory usage, request queue status
- **Configuration Status**: Validates all required settings

### Error Tracking

#### Error Categories
- **Configuration Errors**: Missing settings, invalid values
- **LLM Connection Errors**: Provider unavailable, timeout
- **Processing Errors**: Text too long/short, validation failures
- **Workflow Errors**: State corruption, agent failures

#### Error Recovery
- **Automatic Retry**: Configurable retry attempts with exponential backoff
- **Provider Fallback**: Switch to alternative LLM providers
- **Graceful Degradation**: Return partial results when possible
- **Circuit Breaker**: Prevent cascading failures

## 🚀 Development Guidelines

### Adding New Agents

1. **Create Agent Class**:
   ```python
   class NewAgent:
       async def execute(self, state: AgentState) -> AgentState:
           # Agent implementation
           return state
   ```

2. **Register in Workflow**:
   ```python
   # In workflow.py
   workflow.add_node("new_agent", self._new_agent_node)
   ```

3. **Update Routing Logic**:
   ```python
   # Add routing conditions
   workflow.add_conditional_edges("supervisor", routing_func, {
       "new_agent": "new_agent",
       # ... other routes
   })
   ```

### Adding New LLM Providers

1. **Implement BaseLLMService**:
   ```python
   class NewProviderService(BaseLLMService):
       async def generate(self, prompt: str, system_prompt: str = None) -> str:
           # Provider implementation
           pass
           
       async def is_available(self) -> bool:
           # Health check implementation
           pass
   ```

2. **Register in Service Manager**:
   ```python
   # In llm_service.py  
   _service_registry["new_provider"] = NewProviderService
   ```

3. **Add Configuration**:
   ```python
   # In config.py
   new_provider_api_key: Optional[str] = None
   new_provider_base_url: str = "https://api.newprovider.com"
   ```

### Testing Guidelines

#### Unit Testing
```python
@pytest.mark.asyncio
async def test_extractor_agent():
    agent = ExtractorAgent()
    state = AgentState(raw_text="Test incident")
    result = await agent.execute(state)
    assert result.extracted_data is not None
```

#### Integration Testing  
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_integration():
    workflow = await get_workflow()
    result = await workflow.run("Incident test text")
    assert result.status == ProcessingStatus.SUCCESS
```

#### Mock LLM Testing
```python
# Use MockLLMService for predictable testing
@pytest.fixture
def mock_llm_service():
    return MockLLMService(config=mock_config)
```

### Code Quality Standards

#### Type Safety
- **Strict Type Checking**: Pyright configured in strict mode
- **Type Hints Required**: All functions must have type hints
- **Pydantic Models**: Use for all data validation
- **Optional Types**: Explicit handling of nullable values

#### Code Formatting
```bash
# Auto-formatting with ruff
uv run ruff format .

# Linting checks  
uv run ruff check . --fix

# Type checking
uv run pyright .
```

#### Documentation
- **Docstrings**: Required for all public functions and classes
- **Type Documentation**: Document complex types and data structures
- **API Documentation**: Automatic OpenAPI generation via FastAPI
- **Architecture Documentation**: Keep this document updated

### Performance Considerations

#### Async Operations
- **LLM Calls**: Always use async/await for LLM interactions
- **HTTP Requests**: Use HTTPX for async HTTP operations
- **Database Operations**: Future database integrations should be async

#### Resource Management
- **Connection Pooling**: Managed automatically by service layer
- **Request Limits**: Configurable concurrent request limits
- **Timeout Handling**: Configurable timeouts prevent resource exhaustion
- **Memory Management**: Efficient state management in workflows

#### Monitoring Performance
- **Request Timing**: Track processing time for each component
- **LLM Provider Performance**: Monitor response times per provider
- **Error Rates**: Track success/failure rates by component
- **Resource Usage**: Monitor memory and CPU utilization

---

## 📚 References

- **FastAPI Documentation**: [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)
- **LangGraph Documentation**: [https://langchain-ai.github.io/langgraph/](https://langchain-ai.github.io/langgraph/)
- **Pydantic Documentation**: [https://docs.pydantic.dev/](https://docs.pydantic.dev/)
- **Ollama Documentation**: [https://ollama.ai/docs](https://ollama.ai/docs)

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-20  
**Architecture Version**: Based on implementation as of commit HEAD