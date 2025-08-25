.PHONY: help setup dev install run run-prod test format lint lint-fix type-check quality clean reset health check-deps check-env check-llm ollama-install ollama-start ollama-pull ollama-setup switch-to-openai switch-to-ollama logs
.DEFAULT_GOAL := help

PROJECT_NAME := incident-extractor
PORT ?= 8000
HOST ?= 0.0.0.0
PYTHON ?= python3
OLLAMA_DEFAULT_MODEL := gemma3:4b

# Internal helpers
ENV_FILE := .env

help: ## 📖 Show available commands (this help)
	@echo ""
	@echo "✨ $(PROJECT_NAME) - Make Commands"
	@echo "--------------------------------"
	@grep -E '^[a-zA-Z0-9_.-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Shortcuts: \033[33ms\033[0m=setup \033[33mf\033[0m=format \033[33ml\033[0m=lint-fix \033[33mq\033[0m=quality \033[33mt\033[0m=test \033[33mh\033[0m=health"

setup: ## 🚀 One-command project setup (env + deps + ollama + health)
	@[ -f $(ENV_FILE) ] || cp .env.example $(ENV_FILE)
	@echo "[1/4] Syncing development dependencies"; uv sync --dev >/dev/null
	@echo "[2/4] Ensuring LLM provider readiness"; $(MAKE) ollama-setup >/dev/null || true
	@echo "[3/4] Running health checks"; $(MAKE) health
	@echo "[4/4] Done. Run 'make run' to start the server."

install: ## 📦 Install production dependencies only
	uv sync --no-dev

dev: ## 🛠️ Install / update development dependencies
	uv sync --dev

run: ## 🏃 Start FastAPI dev server (reload)
	PYTHONPATH=src uv run uvicorn main:app --reload --host $(HOST) --port $(PORT)

run-prod: ## 🏭 Start FastAPI production server
	PYTHONPATH=src uv run uvicorn main:app --host $(HOST) --port $(PORT)

test: ## 🧪 Run tests
	uv run pytest

format: ## 🎨 Format code
	uv run ruff format .

lint: ## 🔍 Lint (no fix)
	uv run ruff check .

lint-fix: ## 🧹 Lint and auto-fix
	uv run ruff check . --fix

type-check: ## 🔬 Run pyright type checker
	uv run pyright .

quality: ## ✅ Format + lint-fix + type-check + tests
	$(MAKE) format
	$(MAKE) lint-fix
	$(MAKE) type-check
	$(MAKE) test

clean: ## 🗑️ Remove caches and build artifacts
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .pyright_cache .ruff_cache htmlcov .coverage coverage.xml

reset: ## ♻️ Clean and reinstall dev environment
	$(MAKE) clean
	rm -rf .venv
	$(MAKE) dev

health: ## ❤️ Run dependency, env, and LLM checks
	$(MAKE) check-deps
	$(MAKE) check-env
	$(MAKE) check-llm

check-deps: ## 🔧 Verify core tooling availability
	@echo "Tooling:"; \
	command -v uv >/dev/null && echo "  uv: OK" || echo "  uv: MISSING"; \
	command -v ollama >/dev/null && echo "  ollama: present" || echo "  ollama: not installed (optional)"; \
	[ -d .venv ] && echo "  venv: OK" || echo "  venv: missing (run make dev)"; \
	$(PYTHON) --version 2>&1 | sed 's/^/  python: /'

check-env: ## 📄 Validate .env presence and basic vars
	@if [ ! -f $(ENV_FILE) ]; then echo "  .env missing (cp .env.example .env)"; exit 1; fi; \
	echo "Environment:"; \
	grep -E '^LLM_PROVIDER=' $(ENV_FILE) | sed 's/^/  /' || true; \
	grep -E '^LLM_MODEL_NAME=' $(ENV_FILE) | sed 's/^/  /' || true

check-llm: ## 🤖 Quick LLM provider health check
	@if [ ! -f $(ENV_FILE) ]; then echo "Skip LLM check (no .env)"; exit 0; fi; \
	PROV=$$(grep LLM_PROVIDER $(ENV_FILE) | cut -d'=' -f2 | tr -d '"'); \
	if [ "$$PROV" = "ollama" ]; then \
		command -v ollama >/dev/null || { echo "  Ollama not installed"; exit 1; }; \
		ollama list >/dev/null 2>&1 && echo "  Ollama reachable" || echo "  Ollama not responding"; \
	else \
		echo "  Provider $$PROV configured (no local check)"; \
	fi

# ------------------------- Ollama Management -------------------------
ollama-install: ## 📥 Install Ollama locally (macOS/Linux)
	@if command -v ollama >/dev/null; then echo "Ollama already installed"; exit 0; fi; \
	UNAME=$$(uname -s); \
	if [ "$$UNAME" = "Darwin" ]; then \
		command -v brew >/dev/null && brew install ollama || { echo "Homebrew required"; exit 1; }; \
	else \
		curl -fsSL https://ollama.com/install.sh | sh; \
	fi

ollama-start: ## ▶️ Start Ollama daemon if not running
	@pgrep -f "ollama serve" >/dev/null || (nohup ollama serve >/dev/null 2>&1 & sleep 2)
	@echo "Ollama running"

ollama-pull: ## ⬇️ Pull configured or default model
	@MODEL=$$(grep -E '^LLM_MODEL_NAME=' $(ENV_FILE) | cut -d'=' -f2 | tr -d '"'); \
	[ -n "$$MODEL" ] || MODEL=$(OLLAMA_DEFAULT_MODEL); \
	echo "Pulling $$MODEL"; \
	ollama pull "$$MODEL" || true

ollama-setup: ## 🤖 Ensure Ollama installed, started & model pulled (if provider=ollama)
	@if [ -f $(ENV_FILE) ] && grep -q 'LLM_PROVIDER="ollama"' $(ENV_FILE); then \
		$(MAKE) ollama-install; \
		$(MAKE) ollama-start; \
		$(MAKE) ollama-pull; \
	else \
		echo "Provider not ollama; skipping local setup"; \
	fi

switch-to-openai: ## 🔐 Switch .env to OpenAI (prompts for key)
	@if [ ! -f $(ENV_FILE) ]; then echo ".env missing"; exit 1; fi; \
	read -p "OpenAI API Key: " KEY; \
	sed -i.bak 's/LLM_PROVIDER=".*"/LLM_PROVIDER="openai"/' $(ENV_FILE); \
	sed -i.bak 's/LLM_MODEL_NAME=".*"/LLM_MODEL_NAME="gpt-4o-mini"/' $(ENV_FILE); \
	grep -q 'LLM_API_KEY=' $(ENV_FILE) && sed -i.bak "s/LLM_API_KEY=".*"/LLM_API_KEY="$$KEY"/" $(ENV_FILE) || echo "LLM_API_KEY=\"$$KEY\"" >> $(ENV_FILE); \
	echo "Switched to OpenAI"

switch-to-ollama: ## 🔁 Switch .env to Ollama default model
	@if [ ! -f $(ENV_FILE) ]; then echo ".env missing"; exit 1; fi; \
	sed -i.bak 's/LLM_PROVIDER=".*"/LLM_PROVIDER="ollama"/' $(ENV_FILE); \
	sed -i.bak 's/LLM_MODEL_NAME=".*"/LLM_MODEL_NAME="$(OLLAMA_DEFAULT_MODEL)"/' $(ENV_FILE); \
	sed -i.bak 's/LLM_API_KEY=".*"/LLM_API_KEY=""/' $(ENV_FILE); \
	echo "Switched to Ollama"

logs: ## 📜 Tail application log (if exists)
	@if [ -f logs/app.log ]; then tail -50 logs/app.log; else echo "No log file yet"; fi

# Aliases
s: setup ## ⚡ Alias for setup
f: format ## ⚡ Alias for format
l: lint-fix ## ⚡ Alias for lint-fix
q: quality ## ⚡ Alias for quality
t: test ## ⚡ Alias for test
h: health ## ⚡ Alias for health
