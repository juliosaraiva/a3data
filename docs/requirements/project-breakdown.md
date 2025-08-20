# Incident Extractor API - Task Breakdown

## Overview
Build an LLM-agnostic FastAPI application that extracts structured information from incident descriptions using Ollama/Gemma 3, with clean architecture and modern Python tooling.

## 📋 Task Breakdown

### Phase 1: Project Foundation
#### Task 1.1: Initialize Project Structure
- [ ] Create project directory: `incident-extractor`
- [ ] Initialize with `uv`: `uv init incident-extractor`
- [ ] Set up Git repository
- [ ] Create basic folder structure:
```
incident-extractor/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_client.py
│   │   └── extractor.py
│   └── utils/
│       ├── __init__.py
│       └── preprocessing.py
├── tests/
│   ├── __init__.py
│   └── test_api.py
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

#### Task 1.2: Configure Development Tools
- [ ] Add dependencies with `uv`:
  ```bash
  uv add fastapi uvicorn python-dotenv httpx pydantic-settings
  ```
- [ ] Add dev dependencies:
  ```bash
  uv add --dev ruff pytest httpx pytest-asyncio
  ```
- [ ] Configure `ruff` in `pyproject.toml`:
  ```toml
  [tool.ruff]
  target-version = "py311"
  line-length = 88
  
  [tool.ruff.lint]
  select = ["E", "F", "I", "N", "W", "UP"]
  ignore = []
  
  [tool.ruff.format]
  quote-style = "double"
  indent-style = "space"
  ```

#### Task 1.3: Environment Configuration
- [ ] Create `.env.example` with all required variables:
  ```env
  # LLM Configuration
  LLM_PROVIDER=ollama
  OLLAMA_URL=http://localhost:11434
  MODEL_NAME=gemma:7b
  
  # API Configuration
  HOST=0.0.0.0
  PORT=8000
  DEBUG=true
  
  # Preprocessing
  MAX_INPUT_LENGTH=2000
  ```
- [ ] Create `app/config.py` using `pydantic-settings`
- [ ] Add `.env` to `.gitignore`

### Phase 2: Core Models and Schemas
#### Task 2.1: Define Pydantic Models
- [ ] Create `app/models/schemas.py`:
  - `IncidentRequest` model with validation
  - `IncidentResponse` model with optional fields
  - `ErrorResponse` model for API errors
- [ ] Add input validation (max length, required fields)
- [ ] Add response examples for API documentation

#### Task 2.2: Configuration Management
- [ ] Implement `app/config.py`:
  - Load environment variables
  - Validate configuration on startup
  - Provide defaults for optional settings
  - Support multiple LLM providers

### Phase 3: LLM Abstraction Layer
#### Task 3.1: Create LLM Client Interface
- [ ] Define abstract `LLMClient` class in `app/services/llm_client.py`:
  - `generate(prompt: str) -> str` method
  - `is_available() -> bool` method
  - Error handling interface
- [ ] Create `OllamaClient` implementation:
  - HTTP client for Ollama API
  - Request/response handling
  - Connection error handling
  - Timeout configuration

#### Task 3.2: LLM Client Factory
- [ ] Implement client factory pattern:
  - Support multiple providers (Ollama, OpenAI, Mock)
  - Configuration-based client selection
  - Graceful fallbacks

### Phase 4: Text Preprocessing Pipeline
#### Task 4.1: Implement Preprocessing Utils
- [ ] Create `app/utils/preprocessing.py`:
  - Text normalization (whitespace, encoding)
  - Date/time format standardization
  - Input length validation
  - Special character handling
- [ ] Add preprocessing configuration options
- [ ] Include logging for preprocessing steps

### Phase 5: Extraction Service
#### Task 5.1: Implement Extraction Logic
- [ ] Create `app/services/extractor.py`:
  - Build structured prompts for LLM
  - Handle LLM responses
  - JSON parsing and validation
  - Retry logic for malformed responses
- [ ] Design prompt template:
  - Clear instructions for JSON output
  - Field definitions and examples
  - Error handling instructions

#### Task 5.2: Response Processing
- [ ] Implement response validation:
  - JSON structure validation
  - Field type checking
  - Fallback value assignment
  - Error response generation

### Phase 6: FastAPI Application
#### Task 6.1: Create API Endpoints
- [ ] Implement `app/main.py`:
  - Health check endpoint (`GET /health`)
  - Extract endpoint (`POST /extract`)
  - Error handling middleware
  - CORS configuration
- [ ] Add proper HTTP status codes
- [ ] Include comprehensive API documentation

#### Task 6.2: Request/Response Handling
- [ ] Implement request validation
- [ ] Add response serialization
- [ ] Include request logging
- [ ] Add performance metrics

### Phase 7: Testing Suite
#### Task 7.1: Unit Tests
- [ ] Test preprocessing functions
- [ ] Test LLM client (with mocks)
- [ ] Test extraction service logic
- [ ] Test configuration loading

#### Task 7.2: Integration Tests
- [ ] Test API endpoints with `TestClient`
- [ ] Test end-to-end flow
- [ ] Test error scenarios
- [ ] Test with different input formats

#### Task 7.3: Mock LLM for Testing
- [ ] Create mock LLM client for tests
- [ ] Implement predictable test responses
- [ ] Test error conditions

### Phase 8: Documentation and Deployment
#### Task 8.1: Create Comprehensive README
- [ ] Installation instructions with `uv`
- [ ] Environment setup guide
- [ ] API usage examples
- [ ] Development workflow
- [ ] Troubleshooting section

#### Task 8.2: Code Quality and CI
- [ ] Add `ruff` formatting checks
- [ ] Add `ruff` linting rules
- [ ] Create pre-commit hooks (optional)
- [ ] Add type hints throughout codebase

### Phase 9: Advanced Features (Optional)
#### Task 9.1: Enhanced Error Handling
- [ ] Detailed error responses
- [ ] Logging configuration
- [ ] Request tracing
- [ ] Performance monitoring

#### Task 9.2: Production Readiness
- [ ] Docker containerization
- [ ] Health check improvements
- [ ] Configuration validation
- [ ] Security considerations

## 🚀 Development Workflow

### Daily Development Cycle
1. **Start**: `uv run uvicorn app.main:app --reload`
2. **Format**: `uv run ruff format .`
3. **Lint**: `uv run ruff check .`
4. **Test**: `uv run pytest`
5. **Commit**: Follow conventional commits

### Key Commands
```bash
# Setup
uv sync
uv run uvicorn app.main:app --reload --port 8000

# Development
uv run ruff check .
uv run ruff format .
uv run pytest -v
uv run pytest --cov=app

# Testing API
curl -X POST "http://localhost:8000/extract" \
  -H "Content-Type: application/json" \
  -d '{"description": "Ontem às 14h, no escritório de São Paulo, houve uma falha no servidor principal que afetou o sistema de faturamento por 2 horas."}'
```

## 📋 Success Criteria
- [ ] Clean, readable, well-documented code
- [ ] LLM-agnostic architecture
- [ ] Comprehensive error handling
- [ ] Complete test coverage
- [ ] Easy local reproduction
- [ ] Clear setup instructions
- [ ] Proper environment variable usage
- [ ] Modern Python tooling integration

## 🎯 Next Steps
1. Start with Phase 1 (Project Foundation)
2. Set up the development environment
3. Implement one phase at a time
4. Test each component before moving forward
5. Keep the README updated as you progress

This breakdown ensures a systematic approach to building a production-ready API that meets all the technical requirements while maintaining clean architecture and best practices.