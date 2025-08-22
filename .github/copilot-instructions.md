# GitHub Copilot Instructions

## 🏗️ Project Architecture: Clean Architecture + DDD

This is an **LLM-powered incident extraction API** transitioning to Clean Architecture. Understanding the layered structure is crucial for proper implementation.

### **Folder Structure (Target State)**
```
src/incident_extractor/
├── domain/          # Business entities, value objects, repository interfaces
├── application/     # Use cases, DTOs, application services
├── infrastructure/  # LLM clients, external adapters, concrete implementations
├── presentation/    # FastAPI endpoints, middleware, Pydantic schemas
├── core/           # Cross-cutting: config, exceptions, DI container
└── shared/         # Common utilities and constants
```

### **Key Architectural Patterns**
- **Repository Pattern**: Abstract `LLMRepository` interface with concrete implementations (Ollama, OpenAI, Mock)
- **Factory Pattern**: `LLMClientFactory` switches providers via `LLM_PROVIDER` env var
- **Value Objects**: Immutable `IncidentDateTime` and `Location` with Brazilian format support
- **Domain Entities**: `Incident` entity with business rules and validation

## 🔧 Development Workflow

### **Essential Commands (Use VS Code Tasks)**
```bash
# Setup (Task: "Setup Development Environment")
uv sync --dev

# Code Quality Pipeline (Task: "Pre-commit Check")
uv run ruff format . && uv run ruff check . --fix && uv run mypy . && uv run pytest

# Server (Task: "Start FastAPI Server")
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### **Testing Strategy**
- Unit tests in `tests/unit/` following `test_*.py` pattern
- Integration tests for LLM clients with mocking
- Use `pytest-asyncio` for async test functions
- Mock LLM responses using the `MockClient` implementation

## 🛠️ Project-Specific Conventions

### **Configuration Management**
- **Environment-driven**: All config via `.env` files using Pydantic Settings
- **Nested config**: Use `env_nested_delimiter="__"` for complex settings (e.g., `LLM__PROVIDER=ollama`)
- **Computed fields**: Use `@computed_field` to build complex objects from env vars
```python
@computed_field
@property
def llm_config(self) -> LLMSettings:
    return LLMSettings(provider=self.LLM_PROVIDER, api_key=self.LLM_API_KEY, ...)
```

### **Error Handling Patterns**
- **Domain exceptions**: Inherit from `DomainError` with structured details
- **LLM errors**: Use specific exceptions (`LLMTimeoutError`, `LLMConnectionError`)
- **Validation**: Pydantic models with custom validators, not manual checks

### **Brazilian Localization**
- **Date formats**: Support `DD/MM/YYYY HH:MM` and relative dates ("ontem", "hoje")
- **Location normalization**: Handle Brazilian state abbreviations (SP, RJ, etc.)
- **Text processing**: Consider Portuguese-specific preprocessing in `TextPreprocessor`

## 🔌 Integration Points

### **LLM Client Pattern**
All LLM implementations follow this contract:
```python
async def generate(self, prompt: str, **kwargs: Any) -> str:
    # Provider-specific implementation

async def is_available(self) -> bool:
    # Health check implementation
```

### **Extraction Pipeline**
1. `TextPreprocessor` → clean/normalize input
2. `ExtractionService` → build structured prompts
3. `LLMRepository` → get LLM response
4. `Incident` entity → parse and validate output

### **FastAPI Patterns**
- **Dependency injection**: Use `Depends()` for services and config
- **Middleware order**: Logging → CORS → Error handling → Custom middleware
- **Response models**: Always use Pydantic response models with examples

## 📝 Code Generation Guidelines

### **When creating new components:**
- Follow vertical slicing feature: domain → application → infrastructure → presentation
- Use async/await for I/O operations (LLM calls, file operations)
- Include comprehensive docstrings with Args/Returns/Raises
- Add structured logging with correlation IDs for debugging

### **Domain modeling:**
- Make entities immutable with `@dataclass(frozen=True)`
- Validate business rules in `__post_init__` methods
- Use value objects for complex data types (dates, locations, etc.)
- Keep repository interfaces in domain, implementations in infrastructure

## 🚨 Critical Implementation Notes

- **Configuration**: Always use the enhanced Settings class, never direct env access
- **Logging**: Use `structlog.get_logger(__name__)` for structured logging
- **Type hints**: Required for all function parameters and return values (mypy strict mode)
- **Testing**: Mock LLM clients using the provided `MockClient` for predictable tests

## 🛠️ Use Tools available
- DO NOT hesitate to use available tools and libraries to simplify your implementation.
- ALWAYS use Sequential Thinking, Context7, Memory, Web Search, Microsoft-docs, or any Tool available to design, engineer, and troubleshooting .
