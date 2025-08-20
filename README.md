# Incident Extractor API

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-ready FastAPI application that extracts structured information from incident descriptions using Large Language Models (LLMs). The application is designed to be LLM-agnostic, supporting multiple providers including Ollama, OpenAI, and mock clients for testing.

## Features

- 🤖 **LLM-Agnostic Architecture**: Supports multiple LLM providers (Ollama, OpenAI, Mock)
- 🔧 **Modern Python Tooling**: Uses `uv` for dependency management and `ruff` for linting/formatting
- 📊 **Structured Extraction**: Extracts date, location, incident type, and impact from text
- 🛡️ **Robust Error Handling**: Comprehensive error handling with fallback mechanisms
- ⚡ **High Performance**: Async/await pattern for optimal performance
- 📝 **Comprehensive Testing**: Full test suite with mocking capabilities
- 🔍 **Text Preprocessing**: Advanced text normalization and cleaning pipeline
- 📚 **API Documentation**: Auto-generated OpenAPI documentation
- 🎯 **Production Ready**: Health checks, logging, monitoring, and configuration management

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- [Ollama](https://ollama.com/) (optional, for local LLM)

### Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd incident-extractor
```

2. **Install dependencies**:
```bash
uv sync
```

3. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Install and configure Ollama** (optional):
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve &

# Pull a model (e.g., Gemma 7B)
ollama pull gemma:7b
```

### Running the Application

1. **Start the API server**:
```bash
uv run uvicorn app.main:app --reload --port 8000
```

2. **Access the API**:
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## Usage

### API Endpoints

#### Extract Incident Information
```bash
POST /extract
```

**Request Body**:
```json
{
    "description": "Ontem às 14h, no escritório de São Paulo, houve uma falha no servidor principal que afetou o sistema de faturamento por 2 horas."
}
```

**Response**:
```json
{
    "data_ocorrencia": "2025-08-19 14:00",
    "local": "São Paulo",
    "tipo_incidente": "Falha no servidor",
    "impacto": "Sistema de faturamento indisponível por 2 horas"
}
```

#### Health Check
```bash
GET /health
```

**Response**:
```json
{
    "status": "healthy",
    "timestamp": "2025-08-20T19:00:00",
    "version": "1.0.0",
    "llm_provider": "ollama",
    "llm_available": true
}
```

### Using cURL

```bash
# Extract incident information
curl -X POST "http://localhost:8000/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Hoje às 09h30, no data center principal, ocorreu uma pane elétrica que causou indisponibilidade dos serviços por 3 horas."
  }'

# Check health
curl "http://localhost:8000/health"
```

### Using Python

```python
import httpx

# Create client
client = httpx.Client(base_url="http://localhost:8000")

# Extract incident information
response = client.post("/extract", json={
    "description": "Ontem às 15h, houve um problema de conectividade na filial de Brasília que afetou 50 usuários por 1 hora."
})

print(response.json())
```

## Configuration

The application uses environment variables for configuration. Copy `.env.example` to `.env` and customize:

```env
# LLM Configuration
LLM_PROVIDER=ollama              # ollama, openai, mock
OLLAMA_URL=http://localhost:11434
MODEL_NAME=gemma:7b
REQUEST_TIMEOUT=30

# API Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true
API_TITLE=Incident Extractor API
API_VERSION=1.0.0

# Preprocessing Configuration
MAX_INPUT_LENGTH=2000
ENABLE_TEXT_NORMALIZATION=true

# Logging Configuration
LOG_LEVEL=INFO
```

### LLM Provider Options

1. **Ollama** (Default):
   ```env
   LLM_PROVIDER=ollama
   OLLAMA_URL=http://localhost:11434
   MODEL_NAME=gemma:7b
   ```

2. **Mock** (For testing):
   ```env
   LLM_PROVIDER=mock
   ```

3. **OpenAI** (Future support):
   ```env
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your-api-key
   MODEL_NAME=gpt-3.5-turbo
   ```

## Development

### Code Quality

The project uses modern Python tooling for code quality:

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Fix linting issues automatically
uv run ruff check . --fix
```

### Testing

Run the comprehensive test suite:

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app

# Run specific test file
uv run pytest tests/test_api.py -v

# Run with coverage report
uv run pytest --cov=app --cov-report=html
```

### Project Structure

```
incident-extractor/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py              # Configuration management
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py         # Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_client.py      # LLM client abstraction
│   │   └── extractor.py       # Extraction logic
│   └── utils/
│       ├── __init__.py
│       └── preprocessing.py   # Text preprocessing
├── tests/
│   ├── __init__.py
│   └── test_api.py           # Test suite
├── .env.example              # Environment variables template
├── .gitignore               # Git ignore rules
├── pyproject.toml           # Project configuration
└── README.md               # This file
```

### Adding New LLM Providers

To add support for a new LLM provider:

1. **Create a new client class** in `app/services/llm_client.py`:
```python
class NewProviderClient(LLMClient):
    async def generate(self, prompt: str) -> LLMResponse:
        # Implementation here
        pass
    
    async def is_available(self) -> bool:
        # Implementation here
        pass
```

2. **Register in the factory** in `LLMClientFactory.create_client()`:
```python
elif provider.lower() == "newprovider":
    return NewProviderClient(...)
```

3. **Update configuration** in `app/config.py` to include new provider settings.

## Deployment

### Docker (Coming Soon)

```bash
# Build image
docker build -t incident-extractor .

# Run container
docker run -p 8000:8000 --env-file .env incident-extractor
```

### Production Considerations

1. **Environment Variables**: Use a secure method to manage environment variables
2. **Logging**: Configure appropriate log levels and destinations
3. **Monitoring**: Implement health checks and metrics collection
4. **Security**: Use HTTPS, implement rate limiting, and validate inputs
5. **Scaling**: Consider load balancing and horizontal scaling

## API Response Schema

The API extracts the following information from incident descriptions:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `data_ocorrencia` | string \| null | Date/time of incident | "2025-08-20 14:00" |
| `local` | string \| null | Location of incident | "São Paulo" |
| `tipo_incidente` | string \| null | Type/category of incident | "Falha no servidor" |
| `impacto` | string \| null | Impact description | "Sistema indisponível por 2 horas" |

## Error Handling

The API provides comprehensive error handling:

- **400 Bad Request**: Invalid input data
- **422 Unprocessable Entity**: Validation errors
- **500 Internal Server Error**: Server-side errors
- **503 Service Unavailable**: LLM service unavailable

Error responses follow this format:
```json
{
    "error": "Error message",
    "detail": "Detailed error information",
    "timestamp": "2025-08-20T19:00:00"
}
```

## Performance

The application is optimized for performance:

- **Async Processing**: Non-blocking I/O operations
- **Connection Pooling**: Efficient HTTP client management
- **Text Preprocessing**: Optimized text cleaning pipeline
- **Caching**: Response caching for repeated requests (configurable)
- **Timeouts**: Configurable request timeouts

## Monitoring and Observability

### Health Checks

The `/health` endpoint provides detailed service status:
- API health status
- LLM service availability
- Version information
- Timestamp

### Logging

Structured logging with configurable levels:
- Request/response logging
- Error tracking
- Performance metrics
- Debug information

### Metrics (Future)

Planned metrics collection:
- Request count and latency
- Error rates
- LLM response times
- System resource usage

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run quality checks: `uv run ruff check . && uv run pytest`
5. Commit your changes: `git commit -am 'Add feature'`
6. Push to the branch: `git push origin feature-name`
7. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions:
- Open an issue on GitHub
- Check the API documentation at `/docs`
- Review the test cases for usage examples

## Changelog

### v1.0.0
- Initial release
- LLM-agnostic architecture
- Ollama integration
- Comprehensive test suite
- Text preprocessing pipeline
- Production-ready configuration