.PHONY: help install dev clean test lint format type-check security audit run docs docker-build docker-run
.DEFAULT_GOAL := help

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Project configuration
PROJECT_NAME := incident-extractor
PYTHON_VERSION := 3.13
PORT := 8000
HOST := 0.0.0.0

help: ## Show this help message
	@echo "$(BLUE)$(PROJECT_NAME) Development Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\\n", $$1, $$2}'

# =============================================================================
# INSTALLATION & SETUP
# =============================================================================

install: ## Install production dependencies
	@echo "$(YELLOW)Installing production dependencies...$(NC)"
	uv sync --no-dev
	@echo "$(GREEN)✓ Production dependencies installed$(NC)"

dev: ## Install development dependencies and setup pre-commit hooks
	@echo "$(YELLOW)Setting up development environment...$(NC)"
	uv sync --dev
	@echo "$(GREEN)✓ Development environment ready$(NC)"

clean: ## Clean up cache files and temporary directories
	@echo "$(YELLOW)Cleaning cache files...$(NC)"
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .pyright_cache .ruff_cache
	rm -rf htmlcov/ .coverage coverage.xml
	rm -rf build/ dist/ *.egg-info/
	@echo "$(GREEN)✓ Cache cleaned$(NC)"

# =============================================================================
# CODE QUALITY
# =============================================================================

format: ## Format code with ruff
	@echo "$(YELLOW)Formatting code...$(NC)"
	uv run ruff format .
	@echo "$(GREEN)✓ Code formatted$(NC)"

lint: ## Run linting with ruff
	@echo "$(YELLOW)Running linter...$(NC)"
	uv run ruff check .
	@echo "$(GREEN)✓ Linting complete$(NC)"

lint-fix: ## Run linting with auto-fix
	@echo "$(YELLOW)Running linter with auto-fix...$(NC)"
	uv run ruff check . --fix
	@echo "$(GREEN)✓ Linting complete with fixes applied$(NC)"

type-check: ## Run type checking with pyright
	@echo "$(YELLOW)Running type checker...$(NC)"
	uv run pyright .
	@echo "$(GREEN)✓ Type checking complete$(NC)"

security: ## Run security audit
	@echo "$(YELLOW)Running security audit...$(NC)"
	uv audit
	@echo "$(GREEN)✓ Security audit complete$(NC)"

audit: security ## Alias for security

quality: format lint-fix type-check ## Run all code quality checks
	@echo "$(GREEN)✓ All quality checks complete$(NC)"

pre-commit: quality test ## Run pre-commit checks (format, lint, type-check, test)
	@echo "$(GREEN)✓ Pre-commit checks complete - ready to commit!$(NC)"

# =============================================================================
# TESTING
# =============================================================================

test: ## Run tests with pytest
	@echo "$(YELLOW)Running tests...$(NC)"
	uv run pytest
	@echo "$(GREEN)✓ Tests complete$(NC)"

test-verbose: ## Run tests with verbose output
	@echo "$(YELLOW)Running tests (verbose)...$(NC)"
	uv run pytest -v

test-coverage: ## Run tests with coverage report
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	uv run pytest --cov=src --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Tests with coverage complete$(NC)"
	@echo "$(BLUE)Coverage report: htmlcov/index.html$(NC)"

test-watch: ## Run tests in watch mode
	@echo "$(YELLOW)Running tests in watch mode...$(NC)"
	uv run pytest --watch

# =============================================================================
# DEVELOPMENT SERVER
# =============================================================================

run: ## Start FastAPI development server
	@echo "$(YELLOW)Starting development server...$(NC)"
	@echo "$(BLUE)Server will be available at http://$(HOST):$(PORT)$(NC)"
	@echo "$(BLUE)API docs at http://$(HOST):$(PORT)/docs$(NC)"
	uv run uvicorn main:app --reload --host $(HOST) --port $(PORT)

run-prod: ## Start FastAPI production server
	@echo "$(YELLOW)Starting production server...$(NC)"
	uv run uvicorn main:app --host $(HOST) --port $(PORT)

run-debug: ## Start server with debug logging
	@echo "$(YELLOW)Starting server with debug logging...$(NC)"
	LOG_LEVEL=DEBUG uv run uvicorn main:app --reload --host $(HOST) --port $(PORT) --log-level debug

# =============================================================================
# DOCKER
# =============================================================================

docker-build: ## Build Docker image
	@echo "$(YELLOW)Building Docker image...$(NC)"
	docker build -t $(PROJECT_NAME):latest .
	@echo "$(GREEN)✓ Docker image built$(NC)"

docker-run: ## Run Docker container
	@echo "$(YELLOW)Running Docker container...$(NC)"
	docker run --rm -p $(PORT):$(PORT) --env-file .env $(PROJECT_NAME):latest

docker-shell: ## Open shell in Docker container
	@echo "$(YELLOW)Opening shell in Docker container...$(NC)"
	docker run --rm -it --env-file .env $(PROJECT_NAME):latest /bin/bash

# =============================================================================
# DOCUMENTATION
# =============================================================================

docs: ## Generate project documentation
	@echo "$(YELLOW)Generating documentation...$(NC)"
	@echo "$(BLUE)Architecture: ARCHITECTURE.md$(NC)"
	@echo "$(BLUE)README: README.md$(NC)"
	@echo "$(GREEN)✓ Documentation available$(NC)"

docs-serve: ## Serve documentation locally (if using MkDocs)
	@echo "$(YELLOW)Serving documentation...$(NC)"
	@echo "$(BLUE)Documentation will be available at http://localhost:8080$(NC)"
	# mkdocs serve --dev-addr localhost:8080

# =============================================================================
# UTILITIES
# =============================================================================

info: ## Show project information
	@echo "$(BLUE)Project Information$(NC)"
	@echo "Name: $(PROJECT_NAME)"
	@echo "Python Version: $(PYTHON_VERSION)"
	@echo "Port: $(PORT)"
	@echo "Host: $(HOST)"
	@echo ""
	@echo "$(BLUE)Dependencies$(NC)"
	uv tree

env: ## Show environment information
	@echo "$(BLUE)Environment Information$(NC)"
	uv python list
	@echo ""
	@echo "$(BLUE)UV Version$(NC)"
	uv version

outdated: ## Check for outdated dependencies
	@echo "$(YELLOW)Checking for outdated dependencies...$(NC)"
	uv tree --outdated

update: ## Update dependencies
	@echo "$(YELLOW)Updating dependencies...$(NC)"
	uv sync --upgrade
	@echo "$(GREEN)✓ Dependencies updated$(NC)"

# =============================================================================
# DEPLOYMENT
# =============================================================================

build: quality test ## Build for production (run quality checks and tests)
	@echo "$(GREEN)✓ Build complete - ready for deployment$(NC)"

deploy-check: build ## Check if ready for deployment
	@echo "$(YELLOW)Running deployment checks...$(NC)"
	@echo "$(GREEN)✓ Ready for deployment$(NC)"

# =============================================================================
# MAINTENANCE
# =============================================================================

reset: clean ## Reset development environment
	@echo "$(YELLOW)Resetting development environment...$(NC)"
	rm -rf .venv
	uv sync --dev
	@echo "$(GREEN)✓ Development environment reset$(NC)"

backup: ## Create backup of important files
	@echo "$(YELLOW)Creating backup...$(NC)"
	mkdir -p backups
	tar -czf backups/project-backup-$$(date +%Y%m%d-%H%M%S).tar.gz \
		--exclude='.venv' \
		--exclude='__pycache__' \
		--exclude='.git' \
		--exclude='backups' \
		.
	@echo "$(GREEN)✓ Backup created in backups/$(NC)"
