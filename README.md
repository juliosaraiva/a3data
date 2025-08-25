# Incident Extractor API

FastAPI service that extracts structured incident data (datetime, location, type, impact) from natural language text in Brazilian Portuguese using interchangeable LLM providers (local Ollama by default, OpenAI and others optionally).

## 🚀 One‑Command Setup

```bash
git clone https://github.com/your-org/incident-extractor.git
cd incident-extractor
make setup     # creates .env (if missing), installs deps, prepares Ollama (if provider=ollama), runs health checks
make run       # start server (http://localhost:8000)
```

## ✨ Key Features

- Clean, layered domain-centric design
- Multiple LLM providers (Ollama local, OpenAI, mock for tests)
- Health & diagnostics (deps, env, LLM reachability)
- Strict typing (Pyright) & fast lint/format (Ruff)
- Unified quality pipeline (`make quality`)

## 🧪 Common Make Commands

```bash
make setup        # One-time project bootstrap
make run          # Dev server (reload)
make test         # Run tests
make quality      # Format + lint-fix + type-check + tests
make health       # Dependency, env, and LLM checks
make switch-to-openai  # Change provider (asks API key)
make switch-to-ollama  # Revert to local model
```

Short aliases: `make s f l q t h`

## ⚙️ Configuration (.env)

Create from example automatically on first `make setup`.
Important variables:

```env
LLM_PROVIDER="ollama"          # ollama | openai | mock
LLM_MODEL_NAME="gemma3:4b"     # overridden per provider
LLM_BASE_URL="http://localhost:11434"  # Ollama daemon
LOG_LEVEL="INFO"
```

For OpenAI set `LLM_PROVIDER="openai"` and run `make switch-to-openai`.

## 🤖 Provider Management

```bash
make switch-to-ollama   # Sets provider + default model
make switch-to-openai   # Prompts for API key
make ollama-setup       # Install + start + pull model (if provider=ollama)
```

## 🔍 Health & Diagnostics

```bash
make health      # Aggregated checks
make check-deps  # Toolchain (uv, ollama, python, venv)
make check-env   # .env presence + key vars
make check-llm   # Basic provider reachability
```

## 🧬 Development Workflow

```bash
make f           # Format only
make l           # Lint & fix
make type-check  # Pyright
make test        # Pytest
make quality     # All of the above + tests
```

Helper scripts:

```bash
./scripts/dev.sh test|format|fix|serve|health
./scripts/config.sh show|validate|ollama|openai|mock
./scripts/setup.sh   # Interactive wrapper for make setup
```

## 🏗️ Minimal Architecture Overview

```
src/
  incident_extractor/
    domain/       # Entities, value objects, repositories, services, specs
    services/     # LLM service manager & orchestration
    graph/        # Workflow / graph execution
    models/       # Schemas & Pydantic models
    config/       # Settings, logging, llm configuration
```

## 🧪 API Example

```bash
curl -X POST http://localhost:8000/extract \
  -H 'Content-Type: application/json' \
  -d '{"text":"Ontem às 14h, no escritório de São Paulo, houve uma falha no servidor principal que afetou o sistema de faturamento por 2 horas."}'
```

## 🛠️ Troubleshooting (Top 3)

| Issue            | Fix                                                    |
| ---------------- | ------------------------------------------------------ |
| Ollama not found | `make ollama-install` or `make ollama-setup`           |
| Model missing    | `make ollama-pull` (or rerun `make ollama-setup`)      |
| Import errors    | Ensure you run from project root and used `make setup` |

## 💡 Productivity Suggestions

- Add pre-commit hook referencing `make quality`
- Add test categories (unit vs integration directories)
- Optional: integrate continuous benchmarking script

## 📄 License

## MIT

## 🔄 Current API Endpoints

| Method | Path                   | Description                                         | Response Model      |
| ------ | ---------------------- | --------------------------------------------------- | ------------------- |
| GET    | `/`                    | Basic service info                                  | JSON dict           |
| GET    | `/health`              | Component health (LLMs, workflow, metrics)          | `HealthStatus`      |
| POST   | `/extract`             | Extract incident info from Portuguese text          | `IncidentData`      |
| GET    | `/metrics`             | Aggregated processing metrics                       | `ProcessingMetrics` |
| POST   | `/debug/workflow-info` | Workflow + LLM service state (only if `DEBUG=true`) | JSON                |

### IncidentData (POST /extract)

```json
{
  "data_ocorrencia": "2025-08-24 14:30",
  "local": "São Paulo",
  "tipo_incidente": "Falha no servidor",
  "impacto": "Sistema de faturamento indisponível por 2 horas"
}
```

### Processing Metrics (GET /metrics)

Core fields tracked internally (excerpt):

- `total_requests`, `successful_extractions`, `failed_extractions`
- `average_processing_time` (seconds)
- `supervisor_calls`, `preprocessor_calls`, `extractor_calls`
- `validation_errors`, `timeout_errors`, `llm_errors`

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
