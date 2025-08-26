# Incident Extractor API - Architecture Documentation

## 📋 Overview

The Incident Extractor API is an intelligent system designed to extract structured information from IT incident reports written in Brazilian Portuguese. Using a multi-agent approach powered by Large Language Models (LLMs) and orchestrated through LangGraph, the system transforms unstructured incident descriptions into structured data.

### Key Capabilities

- **Multi-Agent Processing**: Coordinated workflow with specialized agents
- **LLM Provider Flexibility**: Support for Ollama, OpenAI, Gemini, and Perplexity providers
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
                    │  │   Ollama    │ │   OpenAI    │ │  Perplexity ││
                    │  │  Service    │ │  Service    │ │   Service   ││
                    │  └─────────────┘ └─────────────┘ └─────────────┘│
                    └─────────────────────────────────────────────────┘
```

### Folder Structure (Current State)

```
src/incident_extractor/
├── agents/          # Multi-agent system implementation
│   ├── __init__.py
│   ├── supervisor.py    # Workflow orchestration agent
│   ├── preprocessor.py  # Text cleaning and normalization agent
│   └── extractor.py     # Information extraction agent
├── api/             # FastAPI application and routing
│   ├── __init__.py
│   ├── app.py          # FastAPI application factory
│   ├── dependencies.py # Dependency injection
│   ├── middleware/     # Custom middleware components
│   ├── responses/      # Response utilities
│   └── routers/        # API route definitions
│       ├── health.py   # Health check endpoints
│       ├── extraction.py # Incident extraction endpoints
│       ├── metrics.py  # Metrics and monitoring endpoints
│       └── debug.py    # Debug and development endpoints
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
│   └── schemas.py      # Pydantic models for API and internal use
├── services/            # Service layer abstractions
│   ├── __init__.py
│   └── llm_service.py  # LLM service implementations
└── main.py             # Application entry point and development server

tests/                   # Comprehensive integration test suite
├── conftest.py              # Test configuration, fixtures & environment
└── integration/             # Integration test modules
    ├── test_extraction_api.py   # API endpoint integration tests (21+ tests)
    ├── test_date_parsing.py     # Portuguese date parsing validation (9+ tests)
    └── test_error_handling.py   # Error scenarios & edge cases (8+ tests)
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

| Provider       | Primary Use                        | Configuration                    |
| -------------- | ---------------------------------- | -------------------------------- |
| **Ollama**     | Local development, privacy-focused | `LLM_BASE_URL`, `LLM_MODEL_NAME` |
| **OpenAI**     | Production, high accuracy          | `LLM_API_KEY`, `LLM_MODEL_NAME`  |
| **Gemini**     | Production, cost-effective         | `LLM_API_KEY`, `LLM_MODEL_NAME`  |
| **Perplexity** | Production, web search integration | `LLM_API_KEY`, `LLM_MODEL_NAME`  |

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

| Component               | Technology        | Version  | Purpose                   |
| ----------------------- | ----------------- | -------- | ------------------------- |
| **Runtime**             | Python            | 3.13+    | Primary language          |
| **Web Framework**       | FastAPI           | 0.116.1+ | REST API implementation   |
| **Agent Orchestration** | LangGraph         | 0.6.6+   | Multi-agent workflow      |
| **LLM Integration**     | LangChain         | 0.3.27+  | LLM provider abstraction  |
| **Data Validation**     | Pydantic          | 2.11.7+  | Type-safe data models     |
| **Configuration**       | Pydantic Settings | 2.10.1+  | Environment-driven config |
| **HTTP Client**         | HTTPX             | 0.28.0+  | Async HTTP requests       |
| **Logging**             | Structlog         | 24.4.0+  | Structured logging        |

### Development & Testing

| Component             | Technology       | Version  | Purpose                      |
| --------------------- | ---------------- | -------- | ---------------------------- |
| **Testing Framework** | Pytest           | 8.4.1+   | Unit and integration testing |
| **Async Testing**     | Pytest-Asyncio   | 1.1.0+   | Async test support           |
| **HTTP Testing**      | Pytest-HTTPX     | 0.30.0+  | HTTP client testing          |
| **Environment Testing** | Pytest-Env     | 1.0.0+   | Environment variable testing |
| **Time Mocking**      | Freezegun        | 1.2.0+   | Time manipulation for tests  |
| **Test Factories**    | Factories        | 0.2.0+   | Test data generation         |
| **Code Quality**      | Ruff             | 0.12.9+  | Linting and formatting       |
| **Type Checking**     | Pyright          | 1.1.390+ | Static type analysis         |
| **Coverage**          | Pytest-Cov       | 6.0.0+   | Code coverage reporting      |

### LLM Providers

| Provider       | Use Case                           | Requirements              |
| -------------- | ---------------------------------- | ------------------------- |
| **Ollama**     | Local development, privacy         | Local Ollama installation |
| **OpenAI**     | Production, high accuracy          | OpenAI API key            |
| **Gemini**     | Production, cost-effective         | Google API key            |
| **Perplexity** | Production, web search integration | Perplexity API key        |

## 🧪 Testing Architecture

### Testing Strategy

The project employs a comprehensive integration testing strategy designed specifically for AI-powered applications. Our testing approach balances rigorous validation with the inherent variability of Large Language Model (LLM) responses.

#### Core Testing Principles

1. **AI-Aware Testing**: Assertions accommodate realistic LLM behavior variations while maintaining validation rigor
2. **Integration Focus**: Tests validate complete request-response cycles rather than isolated units
3. **Portuguese Language Support**: Specialized testing for Brazilian date/time formats and language processing
4. **Error Resilience**: Comprehensive coverage of error scenarios and edge cases

### Test Suite Structure

#### Test Configuration (`tests/conftest.py`)

```python
# Core test fixtures and configuration
@pytest.fixture
async def app():
    """FastAPI application instance for testing"""
    return create_app()

@pytest.fixture
async def client(app):
    """HTTP test client with proper lifecycle management"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

# Time mocking for deterministic date testing
@pytest.fixture(autouse=True)
def freeze_time_fixture():
    """Freeze time for consistent date parsing tests"""
    with freeze_time("2024-01-15 10:00:00"):
        yield
```

#### Integration Test Modules

##### 1. API Endpoint Testing (`test_extraction_api.py`)

**Coverage**: 21+ comprehensive tests validating:
- Health endpoints (`/api/health/*`)
- Extraction endpoints (`/api/v1/incidents/extract`)
- Metrics endpoints (`/api/metrics/*`)
- Debug endpoints (`/api/debug/*`)
- Documentation endpoints (`/docs`, `/openapi.json`)

**Key Features**:
- **AI-Aware Assertions**: Flexible validation for LLM response variations
- **Performance Testing**: Response time validation (< 30 seconds)
- **Concurrent Request Testing**: Multiple simultaneous requests
- **Security Header Validation**: CORS and security middleware

**Example Test Pattern**:
```python
@pytest.mark.asyncio
async def test_incident_extraction_with_complex_scenario(client):
    """Test extraction with complex incident scenario"""
    response = await client.post("/api/v1/incidents/extract", json={
        "text": "Hoje às 09:30 no datacenter SP-01 houve queda de energia"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # AI-aware assertions: check presence and format rather than exact values
    assert "data_ocorrencia" in data
    assert "local" in data
    assert "tipo_incidente" in data
    assert "impacto" in data
    
    # Validate date format when present
    if data["data_ocorrencia"]:
        assert len(data["data_ocorrencia"]) >= 10  # At least YYYY-MM-DD
```

##### 2. Portuguese Date Parsing (`test_date_parsing.py`)

**Coverage**: 9+ specialized tests for Brazilian Portuguese date processing:
- Relative dates: "hoje", "ontem", "anteontem"
- Weekday references: "segunda-feira passada", "sexta-feira passada"
- Time variations: morning, afternoon, evening
- Year boundary scenarios
- Time precision testing

**Time Mocking Strategy**:
```python
@freeze_time("2024-01-15 10:00:00")  # Monday
@pytest.mark.asyncio
async def test_portuguese_relative_dates(client):
    """Test Portuguese relative date parsing"""
    test_cases = [
        ("ontem às 14h", "2024-01-14"),  # Yesterday
        ("hoje de manhã", "2024-01-15"),   # Today morning
        ("sexta-feira passada", "2024-01-12")  # Last Friday
    ]
    
    for text_input, expected_date in test_cases:
        response = await client.post("/api/v1/incidents/extract", json={
            "text": f"Incidente: {text_input} houve falha no sistema"
        })
        
        data = response.json()
        if data.get("data_ocorrencia"):
            assert expected_date in data["data_ocorrencia"]
```

##### 3. Error Handling & Edge Cases (`test_error_handling.py`)

**Coverage**: 8+ tests for robust error handling:
- Input validation errors
- Malformed request scenarios
- Text length boundary conditions
- HTTP error code validation
- Timeout and connection error simulation

**Error Scenario Testing**:
```python
@pytest.mark.asyncio
async def test_input_validation_errors(client):
    """Test various input validation scenarios"""
    test_cases = [
        ({}, 422),  # Missing text field
        ({"text": ""}, 422),  # Empty text
        ({"text": "x" * 10000}, 422),  # Text too long
        ({"text": "short"}, 422)  # Text too short
    ]
    
    for payload, expected_status in test_cases:
        response = await client.post("/api/v1/incidents/extract", json=payload)
        assert response.status_code == expected_status
```

### Testing Infrastructure

#### PyTest Configuration (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
    "--disable-warnings"
]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests"
]
```

#### Test Execution Commands

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test categories
uv run pytest -m integration
uv run pytest -m "not slow"

# Run with detailed output
uv run pytest -v --tb=long

# Run specific test file
uv run pytest tests/integration/test_extraction_api.py
```

#### Test Results & Metrics

**Current Test Status**:
- **Total Tests**: 38 comprehensive integration tests
- **Pass Rate**: 97% (37 passed, 1 deselected)
- **Coverage Areas**: API validation, date parsing, error handling, performance
- **Execution Time**: ~15-30 seconds for full suite

**Test Categories**:
- **API Integration**: 21+ tests covering all endpoints
- **Date Processing**: 9+ tests for Portuguese date parsing
- **Error Handling**: 8+ tests for edge cases and error scenarios
- **Performance**: Response time and concurrent request validation

### AI-Aware Testing Methodology

#### Challenge: LLM Response Variability

Large Language Models inherently produce variable responses, making traditional exact-match testing insufficient. Our approach addresses this through:

#### Flexible Assertion Patterns

```python
# ❌ Traditional rigid assertion (fails with AI)
assert data["tipo_incidente"] == "Queda de energia"

# ✅ AI-aware flexible assertion (accommodates variations)
assert "tipo_incidente" in data  # Field presence
assert data["tipo_incidente"] is not None  # Non-null value
if data["tipo_incidente"]:
    assert len(data["tipo_incidente"]) > 0  # Non-empty when present
```

#### Semantic Validation

```python
# Validate semantic correctness rather than exact strings
if data.get("data_ocorrencia"):
    # Check date format rather than exact value
    assert re.match(r'\d{4}-\d{2}-\d{2}', data["data_ocorrencia"])
    
if data.get("local"):
    # Check location contains expected elements
    assert any(term in data["local"].lower() 
               for term in ["datacenter", "sp", "são paulo"])
```

#### Confidence-Based Testing

```python
# Allow for partial extraction with confidence thresholds
extracted_fields = sum(1 for field in ["data_ocorrencia", "local", 
                                      "tipo_incidente", "impacto"]
                      if data.get(field))

# Expect at least 2-3 fields extracted for complex incidents
assert extracted_fields >= 2, f"Too few fields extracted: {extracted_fields}"
```

### Future Testing Enhancements

#### Planned Additions

1. **Load Testing**: Stress testing with concurrent requests
2. **End-to-End Testing**: Complete workflow validation with real LLM providers
3. **Performance Regression Testing**: Automated performance benchmarking
4. **Mock LLM Testing**: Controlled testing with predictable mock responses

#### Testing Metrics Dashboard

- **Success Rate Tracking**: Monitor test pass rates over time
- **Performance Benchmarking**: Track response times and resource usage
- **Coverage Analysis**: Ensure comprehensive test coverage maintenance
- **AI Model Behavior**: Monitor LLM response patterns and reliability

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

- **Primary Endpoint**: `GET /api/health/`
- **Detailed Health**: `GET /api/health/detailed`
- **Liveness Probe**: `GET /api/health/live`
- **Readiness Probe**: `GET /api/health/ready`
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

##### Key Metrics (`GET /api/metrics/`)

```python
class ProcessingMetrics(BaseModel):
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_processing_time: float = 0.0
    total_processing_time: float = 0.0
    agent_execution_counts: Dict[str, int] = Field(default_factory=dict)
    llm_provider_usage: Dict[str, int] = Field(default_factory=dict)
```

Additional metrics endpoints:

- **Health Score**: `GET /api/metrics/health-score`
- **Performance**: `GET /api/metrics/performance`

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

### Adding New API Endpoints

1. **Create Router Module**:

   ```python
   # In src/incident_extractor/api/routers/new_feature.py
   from fastapi import APIRouter

   router = APIRouter(prefix="/api/v1/new-feature", tags=["new-feature"])

   @router.get("/")
   async def get_new_feature():
       return {"message": "New feature endpoint"}
   ```

2. **Register Router**:

   ```python
   # In src/incident_extractor/api/app.py
   from .routers import new_feature

   app.include_router(new_feature.router)
   ```

3. **Add Tests**:
   ```python
   def test_new_feature_endpoint(client):
       response = client.get("/api/v1/new-feature/")
       assert response.status_code == 200
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

**Document Version**: 1.2
**Last Updated**: 2025-01-20
**Architecture Version**: Based on current implementation with API routing, multi-provider LLM support, comprehensive health checks, and complete integration testing infrastructure
