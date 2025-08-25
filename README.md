# Incident Extractor API

An intelligent FastAPI service that extracts structured incident information from Brazilian Portuguese incident reports using multi-agent LLM processing. Transforms unstructured text into standardized data for datetime, location, incident type, and impact assessment.

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/your-org/incident-extractor.git
cd incident-extractor
make setup     # One-command setup: dependencies + environment + LLM

# 2. Start the server
make run       # http://localhost:8000

# 3. Test the API
curl -X POST http://localhost:8000/extract \
  -H 'Content-Type: application/json' \
  -d '{"text":"Ontem às 14h no escritório de São Paulo houve falha no servidor principal, impactando o sistema de faturamento por 2 horas."}'
```

## ✨ Key Features

- **Multi-Agent Processing**: LangGraph workflow with specialized agents (Supervisor, Preprocessor, Extractor)
- **Multiple LLM Providers**: Local Ollama, OpenAI, or Mock for testing
- **Brazilian Portuguese**: Native support for PT-BR language and date formats
- **Type-Safe**: Strict typing with Pydantic and Pyright
- **Production Ready**: Health checks, metrics, structured logging
- **Developer Friendly**: Hot reload, comprehensive testing, code quality tools

## 📋 System Requirements

- **Python**: 3.13+
- **uv**: Fast Python package manager
- **Ollama**: For local LLM (optional, auto-installed with `make setup`)
- **macOS/Linux**: Primary supported platforms

## ⚙️ Essential Commands

| Command        | Purpose       | Description                                            |
| -------------- | ------------- | ------------------------------------------------------ |
| `make setup`   | Initial setup | Install dependencies, configure environment, setup LLM |
| `make run`     | Start server  | Development server with hot reload                     |
| `make test`    | Run tests     | Execute test suite                                     |
| `make quality` | Code quality  | Format, lint, type-check, and test                     |
| `make health`  | System check  | Verify dependencies, environment, and LLM connectivity |

**Quick aliases**: `s` (setup), `f` (format), `l` (lint-fix), `q` (quality), `t` (test), `h` (health)

## ⚙️ Configuration

Environment variables are configured automatically on first `make setup` from `.env.example`.

### Core Settings

```env
LLM_PROVIDER="ollama"          # ollama | openai | mock
LLM_MODEL_NAME="gemma3:4b"     # Model name (provider-specific)
LLM_BASE_URL="http://localhost:11434"  # Ollama daemon URL
LLM_TIMEOUT=30                 # Request timeout (seconds)
LOG_LEVEL="INFO"               # Logging level
DEBUG=false                    # Debug mode
```

### LLM Provider Setup

#### Ollama (Default - Local)

```bash
make setup              # Auto-installs and configures Ollama
# OR manually:
make ollama-setup       # Install + start + pull model
```

#### OpenAI (Cloud)

```bash
make switch-to-openai   # Prompts for API key and switches provider
# Manually set: LLM_PROVIDER="openai" and LLM_API_KEY="your-key"
```

#### Mock (Testing)

```bash
# Set in .env: LLM_PROVIDER="mock"
# No external dependencies required
```

## 💼 API Reference

### Endpoints

| Method | Path                   | Description                  | Response            |
| ------ | ---------------------- | ---------------------------- | ------------------- |
| GET    | `/`                    | Service information          | JSON                |
| GET    | `/health`              | Component health status      | `HealthStatus`      |
| POST   | `/extract`             | Extract incident information | `IncidentData`      |
| GET    | `/metrics`             | Processing metrics           | `ProcessingMetrics` |
| POST   | `/debug/workflow-info` | Workflow state (DEBUG only)  | JSON                |

### Example Request/Response

**Request:**

```bash
curl -X POST http://localhost:8000/extract \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "Hoje às 09:30 no datacenter SP-01 houve queda de energia que causou indisponibilidade dos serviços críticos por 45 minutos."
  }'
```

**Response:**

```json
{
  "data_ocorrencia": "2025-01-20 09:30",
  "local": "Datacenter SP-01",
  "tipo_incidente": "Queda de energia",
  "impacto": "Indisponibilidade dos serviços críticos por 45 minutos"
}
```

## 🚀 Development

### Development Workflow

```bash
# Setup development environment
make dev              # Install dev dependencies
make run              # Start dev server with reload

# Code quality checks
make format           # Format code with Ruff
make lint-fix         # Lint and auto-fix issues
make type-check       # Type checking with Pyright
make quality          # Run all quality checks + tests
```

### Testing

```bash
make test             # Run full test suite
uv run pytest tests/ # Direct pytest execution
uv run pytest -v     # Verbose output
```

### Additional Commands

```bash
make logs             # View application logs
make clean            # Remove cache files
make reset            # Clean + reinstall environment
```

## 🏗️ Architecture Overview

The system uses a **multi-agent approach** with LangGraph orchestration:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │───▶│   LangGraph      │───▶│   Multi-Agent   │
│   REST API      │    │   Workflow       │    │   Processing    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                    ┌───────────────────────────────────────┐
                    │         Agent System                  │
                    │  ┌──────────┐ ┌─────────┐ ┌────────┐  │
                    │  │Supervisor│ │Preproc. │ │Extract.│  │
                    │  │  Agent   │ │ Agent   │ │ Agent  │  │
                    │  └──────────┘ └─────────┘ └────────┘  │
                    └───────────────────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────────────┐
                    │        LLM Services             │
                    │   Ollama │ OpenAI │ Mock        │
                    └─────────────────────────────────┘
```

### Project Structure

```
src/incident_extractor/
├── agents/        # Multi-agent system (Supervisor, Preprocessor, Extractor)
├── config/        # Settings, logging, LLM configuration
├── graph/         # LangGraph workflow orchestration
├── models/        # Pydantic models and schemas
└── services/      # LLM service abstractions
```

### Processing Flow

1. **Supervisor Agent**: Analyzes input and orchestrates workflow
2. **Preprocessor Agent**: Cleans and normalizes Portuguese text
3. **Extractor Agent**: Extracts structured data via LLM
4. **Quality Control**: Validates results and handles retries

> 📖 **Detailed Architecture**: See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for comprehensive documentation.

## � Troubleshooting

### Common Issues

| Issue                    | Cause                      | Solution                                     |
| ------------------------ | -------------------------- | -------------------------------------------- |
| **Ollama not found**     | Ollama not installed       | `make ollama-setup` or `brew install ollama` |
| **Model missing**        | Default model not pulled   | `make ollama-pull`                           |
| **Import errors**        | Wrong working directory    | Run commands from project root               |
| **422 validation error** | Text too short (<10 chars) | Provide more descriptive incident text       |
| **408 timeout**          | LLM response too slow      | Increase `LLM_TIMEOUT` or reduce text length |
| **500 internal error**   | LLM provider failure       | Check `make health` and logs                 |

### Health Checks

```bash
make health       # Complete system health check
make check-deps   # Verify tooling (uv, python, ollama)
make check-env    # Validate .env configuration
make check-llm    # Test LLM provider connectivity
make logs         # View recent application logs
```

### Provider-Specific Issues

**Ollama:**

- Ensure Ollama daemon is running: `ollama serve`
- Check available models: `ollama list`
- Pull missing model: `ollama pull gemma3:4b`

**OpenAI:**

- Verify API key in `.env`: `LLM_API_KEY="sk-..."`
- Check quota and billing in OpenAI dashboard
- Test connectivity: `curl -H "Authorization: Bearer $LLM_API_KEY" https://api.openai.com/v1/models`

## 🤝 Contributing

### Development Setup

```bash
git clone <repository>
cd incident-extractor
make setup          # Full environment setup
make dev            # Install dev dependencies
```

### Code Quality Standards

- **Type Safety**: All functions must have type hints (Pyright strict mode)
- **Testing**: Write tests for new features and bug fixes
- **Documentation**: Update relevant documentation for changes
- **Code Style**: Use `make quality` before committing

### Commit Workflow

```bash
# Before committing
make quality        # Format, lint, type-check, test
git add .
git commit -m "feat: your change description"
```

### Adding New Features

1. **New Agents**: Extend the multi-agent system in `src/incident_extractor/agents/`
2. **LLM Providers**: Add support for new providers in `src/incident_extractor/services/`
3. **API Endpoints**: Extend FastAPI routes in `main.py`

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.

---

**Documentation**: For detailed architecture and implementation details, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

**Last Updated**: Based on implementation as of 2025-01-20

## 📂 Current Folder Structure

```
src/incident_extractor/
  agents/        # Preprocessor, extractor, supervisor agent logic
  config/        # Settings, logging, llm configuration and middleware
  graph/         # LangGraph workflow orchestration (workflow.py)
  models/        # Pydantic models: requests, responses, state, metrics
  services/      # LLM service manager & provider handling
```

## 🧠 Workflow Overview

The extraction pipeline uses a LangGraph workflow with three main agents:

1. Preprocessor agent: normalizes, cleans and contextualizes raw text
2. Extractor agent: interacts with the configured LLM provider
3. Supervisor agent: validates / reconciles outputs and finalizes state

State transitions are tracked; metrics accumulate processing statistics for observability.

## 🧾 Environment Keys (excerpt from `.env.example`)

```env
LLM_PROVIDER="ollama"        # ollama | openai | gemini | perplexity | mock
LLM_MODEL_NAME="gemma3:4b"
LLM_BASE_URL="http://localhost:11434"
LLM_TEMPERATURE=0.1
LLM_TIMEOUT=30
LOG_LEVEL="INFO"
LOG_FORMAT="json"
LOG_FILE_ENABLED="true"
LOG_FILE_PATH="logs/app.log"
DEBUG=false
```

Only cloud providers (openai, gemini, perplexity) require `LLM_API_KEY`.

## 🔁 Provider Switching

```bash
make switch-to-ollama      # Set provider + model locally
make switch-to-openai      # Prompt for API key & switch
./scripts/config.sh ollama # Alternative script interface
./scripts/config.sh openai
```

## 🔍 Health Internals

`/health` assembles:

- LLM service availability (`service_manager.health_check_all()`)
- Workflow validation (`workflow.validate_workflow()`)
- Current processing metrics snapshot
  Overall status = healthy if at least one LLM healthy AND workflow validations pass.

## 🧪 Testing & Quality (Targets Recap)

```bash
make test        # pytest
make format      # ruff format
make lint        # ruff check (no fix)
make lint-fix    # ruff check --fix
make type-check  # pyright
make quality     # all + tests
```

Helper scripts mirror these: `./scripts/dev.sh format|test|fix|serve|health`.

## �️ Troubleshooting Additions

| Symptom            | Cause                              | Action                                       |
| ------------------ | ---------------------------------- | -------------------------------------------- |
| 422 short text     | <10 chars                          | Provide more descriptive incident text       |
| 422 long text      | Exceeds `max_preprocessing_length` | Shorten input or raise limit in settings/env |
| 408 timeout        | LLM slow / large prompt            | Reduce text size or increase `LLM_TIMEOUT`   |
| 500 internal error | LLM/provider failure               | Check logs (`make logs`) & `/health`         |

## 🧩 Future Enhancements (Suggestions)

- Add persisted audit trail of extractions (DB or file-based)
- Implement circuit breaker around repeated LLM failures
- Expose Prometheus metrics adapter for `/metrics`
- Add streaming endpoint for progressive extraction feedback

## 📄 License

MIT (See LICENSE)

---

**Updated documentation reflects current simplified architecture (agents + graph + services) replacing earlier layered DDD scaffolding not present in code.**
