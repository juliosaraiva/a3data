# Incident Extractor API

An intelligent FastAPI service that extracts structured incident information from Brazilian Portuguese incident reports using multi-agent LLM processing. Transforms unstructured text into standardized data for datetime, location, incident type, and impact assessment.

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone <repository-url>
cd incident-extractor
make setup     # One-command setup: dependencies + environment + LLM

# 2. Start the server
make run       # http://localhost:8000

# 3. Test the API
curl -X POST http://localhost:8000/api/v1/incidents/extract \
  -H 'Content-Type: application/json' \
  -d '{"text":"Ontem às 14h no escritório de São Paulo houve falha no servidor principal, impactando o sistema de faturamento por 2 horas."}'
```

## ✨ Key Features

- **Multi-Agent Processing**: LangGraph workflow with specialized agents (Supervisor, Preprocessor, Extractor)
- **Multiple LLM Providers**: Local Ollama, OpenAI, Gemini, Perplexity, or Mock for testing
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
LLM_PROVIDER="ollama"          # ollama | openai | gemini | perplexity | mock
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

| Method | Path                          | Description                  | Response            |
| ------ | ----------------------------- | ---------------------------- | ------------------- |
| GET    | `/api/health/`                | Basic health status          | `HealthStatus`      |
| GET    | `/api/health/detailed`        | Detailed component status    | `HealthStatus`      |
| GET    | `/api/health/live`            | Liveness probe               | JSON                |
| GET    | `/api/health/ready`           | Readiness probe              | JSON                |
| POST   | `/api/v1/incidents/extract`   | Extract incident information | `IncidentData`      |
| GET    | `/api/metrics/`               | Processing metrics           | `ProcessingMetrics` |
| GET    | `/api/metrics/health-score`   | Health score                 | JSON                |
| GET    | `/api/metrics/performance`    | Performance metrics          | JSON                |
| GET    | `/api/debug/system-info`      | System information           | JSON                |
| GET    | `/api/debug/components`       | Component status             | JSON                |
| GET    | `/api/debug/workflow-info`    | Workflow state (DEBUG only)  | JSON                |
| POST   | `/api/debug/test-extraction`  | Test extraction (DEBUG only) | `IncidentData`      |
| GET    | `/docs`                       | OpenAPI documentation        | HTML                |
| GET    | `/openapi.json`               | OpenAPI specification        | JSON                |

### Example Request/Response

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/incidents/extract \
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
make validate         # Quick API health check
make v                # Alias for validate
```

## 🔍 API Health Checks

The system includes comprehensive API validation:

```bash
make validate         # Run API health check (~15 seconds)
make api-check        # Alternative command
make v               # Quick alias (6 keystrokes)
```

This validates 14 endpoints across:
- **Health**: `/api/health/*` endpoints
- **Extraction**: `/api/v1/incidents/extract`
- **Metrics**: `/api/metrics/*` endpoints  
- **Debug**: `/api/debug/*` endpoints
- **Documentation**: `/docs`, `/openapi.json`

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
                    ┌─────────────────────────────────────────┐
                    │        LLM Services                     │
                    │   Ollama │ OpenAI │ Gemini │ Mock       │
                    └─────────────────────────────────────────┘
```

### Project Structure

```
src/incident_extractor/
├── agents/        # Multi-agent system (Supervisor, Preprocessor, Extractor)
├── api/           # FastAPI routers, middleware, and application setup
├── config/        # Settings, logging, LLM configuration
├── graph/         # LangGraph workflow orchestration
├── models/        # Pydantic models and schemas
└── services/      # LLM service abstractions and implementations
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
3. **API Endpoints**: Extend FastAPI routes in `src/incident_extractor/api/routers/`

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.

---

**Documentation**: For detailed architecture and implementation details, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

**Last Updated**: Based on implementation as of 2025-01-20
