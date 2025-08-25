# Multi-stage Dockerfile for Incident Extractor API
# Stage 1: Build & dependency install
FROM python:3.13-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps (build essentials for any wheels that need compiling)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata first for better layer caching
COPY pyproject.toml ./
COPY uv.lock ./uv.lock
COPY README.md ./

# Copy source
COPY src ./src
COPY main.py ./

# Install production dependencies (build wheel & install)
RUN pip install --upgrade pip \
    && pip install .

# Stage 2: Runtime image (slim, non-root)
FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_HOME=/app \
    PORT=8000

WORKDIR ${APP_HOME}

# Runtime utilities (curl for healthcheck)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only installed site-packages & entry points from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source (kept separate to allow live rebuilds without reinstalling deps)
COPY --from=builder /app/src ./src
COPY --from=builder /app/main.py ./
COPY --from=builder /app/README.md ./
COPY .env.example ./.env.example

# Create non-root user
RUN useradd -u 1001 -m appuser \
    && chown -R appuser:appuser ${APP_HOME}
USER appuser

EXPOSE 8000

# Basic healthcheck (FastAPI /health)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -fsS http://localhost:${PORT}/health || exit 1

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
