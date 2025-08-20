"""Tests for the Incident Extractor API."""

import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.services.llm_client import MockLLMClient
from app.models.schemas import IncidentResponse


# Test client
client = TestClient(app)


class TestAPI:
    """Test cases for the API endpoints."""

    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "llm_provider" in data
        assert "llm_available" in data

    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "endpoints" in data

    @patch('app.main.extractor')
    def test_extract_valid_request(self, mock_extractor):
        """Test extraction with valid request."""
        # Mock the extractor response
        mock_response = IncidentResponse(
            data_ocorrencia="2025-08-20 14:00",
            local="São Paulo",
            tipo_incidente="Falha no servidor",
            impacto="Sistema indisponível por 2 horas"
        )
        mock_extractor.extract_incident_info = AsyncMock(return_value=mock_response)
        
        request_data = {
            "description": "Ontem às 14h, no escritório de São Paulo, houve uma falha no servidor principal que afetou o sistema de faturamento por 2 horas."
        }
        
        response = client.post("/extract", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["data_ocorrencia"] == "2025-08-20 14:00"
        assert data["local"] == "São Paulo"
        assert data["tipo_incidente"] == "Falha no servidor"
        assert data["impacto"] == "Sistema indisponível por 2 horas"

    def test_extract_invalid_request_empty_description(self):
        """Test extraction with empty description."""
        request_data = {"description": ""}
        
        response = client.post("/extract", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_extract_invalid_request_short_description(self):
        """Test extraction with too short description."""
        request_data = {"description": "Erro"}
        
        response = client.post("/extract", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_extract_invalid_request_long_description(self):
        """Test extraction with too long description."""
        request_data = {"description": "A" * 3000}  # Exceeds max length
        
        response = client.post("/extract", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_extract_missing_description(self):
        """Test extraction with missing description field."""
        request_data = {}
        
        response = client.post("/extract", json=request_data)
        assert response.status_code == 422  # Validation error


class TestLLMClient:
    """Test cases for LLM client implementations."""

    def test_mock_llm_client(self):
        """Test mock LLM client."""
        client = MockLLMClient()
        
        # Test availability
        assert client.is_available() is True
        
        # Test response generation
        response = client.generate("Test prompt")
        assert response.success is True
        assert response.text is not None
        assert response.error is None

    def test_mock_llm_client_unavailable(self):
        """Test mock LLM client when unavailable."""
        client = MockLLMClient()
        client.set_availability(False)
        
        # Test availability
        assert client.is_available() is False
        
        # Test response generation when unavailable
        response = client.generate("Test prompt")
        assert response.success is False
        assert response.error is not None

    def test_mock_llm_client_custom_response(self):
        """Test mock LLM client with custom response."""
        custom_response = json.dumps({
            "data_ocorrencia": "2025-08-21 10:00",
            "local": "Rio de Janeiro",
            "tipo_incidente": "Falha de rede",
            "impacto": "Conectividade perdida por 1 hora"
        })
        
        client = MockLLMClient(custom_response)
        response = client.generate("Test prompt")
        
        assert response.success is True
        assert response.text == custom_response


class TestTextPreprocessor:
    """Test cases for text preprocessing."""

    def test_basic_preprocessing(self):
        """Test basic text preprocessing."""
        from app.utils.preprocessing import TextPreprocessor
        
        preprocessor = TextPreprocessor()
        
        # Test basic cleaning
        text = "  Ontem  às  14h  no  escritório  "
        processed = preprocessor.preprocess(text)
        
        assert processed == "20/08/2025 às 14:00 no escritório"

    def test_date_normalization(self):
        """Test date normalization."""
        from app.utils.preprocessing import TextPreprocessor
        
        preprocessor = TextPreprocessor()
        
        # Test relative dates
        text = "Hoje às 15h houve um problema"
        processed = preprocessor.preprocess(text)
        
        # Should contain today's date
        from datetime import datetime
        today = datetime.now().strftime("%d/%m/%Y")
        assert today in processed

    def test_time_normalization(self):
        """Test time normalization."""
        from app.utils.preprocessing import TextPreprocessor
        
        preprocessor = TextPreprocessor()
        
        text = "Às 14h30 e também às 9h"
        processed = preprocessor.preprocess(text)
        
        assert "14:30" in processed
        assert "9:00" in processed

    def test_text_truncation(self):
        """Test text truncation."""
        from app.utils.preprocessing import TextPreprocessor
        
        preprocessor = TextPreprocessor(max_length=50)
        
        long_text = "Este é um texto muito longo " * 10
        processed = preprocessor.preprocess(long_text)
        
        assert len(processed) <= 50

    def test_extract_date_hints(self):
        """Test date hint extraction."""
        from app.utils.preprocessing import TextPreprocessor
        
        preprocessor = TextPreprocessor()
        
        # Test explicit date
        text = "Em 15/08/2025 houve um problema"
        hint = preprocessor.extract_date_hints(text)
        assert hint == "2025-08-15"
        
        # Test relative date
        text = "Ontem houve um problema"
        hint = preprocessor.extract_date_hints(text)
        assert hint is not None

    def test_extract_time_hints(self):
        """Test time hint extraction."""
        from app.utils.preprocessing import TextPreprocessor
        
        preprocessor = TextPreprocessor()
        
        # Test time formats
        text = "Às 14:30 houve um problema"
        hint = preprocessor.extract_time_hints(text)
        assert hint == "14:30"
        
        text = "Às 9h houve um problema"
        hint = preprocessor.extract_time_hints(text)
        assert hint == "09:00"


class TestIncidentExtractor:
    """Test cases for incident extraction logic."""

    @pytest.mark.asyncio
    async def test_extract_with_mock_llm(self):
        """Test extraction with mock LLM."""
        from app.services.extractor import IncidentExtractor
        from app.utils.preprocessing import TextPreprocessor
        
        # Create mock response
        mock_response = json.dumps({
            "data_ocorrencia": "2025-08-20 14:00",
            "local": "São Paulo",
            "tipo_incidente": "Falha no servidor",
            "impacto": "Sistema faturamento indisponível"
        })
        
        llm_client = MockLLMClient(mock_response)
        preprocessor = TextPreprocessor()
        extractor = IncidentExtractor(llm_client, preprocessor)
        
        description = "Ontem às 14h, no escritório de São Paulo, houve uma falha no servidor principal que afetou o sistema de faturamento por 2 horas."
        
        result = await extractor.extract_incident_info(description)
        
        assert result.data_ocorrencia == "2025-08-20 14:00"
        assert result.local == "São Paulo"
        assert result.tipo_incidente == "Falha no servidor"
        assert result.impacto == "Sistema faturamento indisponível"

    @pytest.mark.asyncio
    async def test_extract_with_llm_failure(self):
        """Test extraction when LLM fails."""
        from app.services.extractor import IncidentExtractor
        from app.utils.preprocessing import TextPreprocessor
        
        llm_client = MockLLMClient()
        llm_client.set_availability(False)
        
        preprocessor = TextPreprocessor()
        extractor = IncidentExtractor(llm_client, preprocessor)
        
        description = "Ontem às 14h, no escritório de São Paulo, houve uma falha no servidor principal."
        
        result = await extractor.extract_incident_info(description)
        
        # Should still return a response (fallback)
        assert isinstance(result, IncidentResponse)

    @pytest.mark.asyncio
    async def test_extract_with_invalid_json(self):
        """Test extraction when LLM returns invalid JSON."""
        from app.services.extractor import IncidentExtractor
        from app.utils.preprocessing import TextPreprocessor
        
        llm_client = MockLLMClient("Invalid JSON response")
        preprocessor = TextPreprocessor()
        extractor = IncidentExtractor(llm_client, preprocessor)
        
        description = "Teste de incidente"
        
        result = await extractor.extract_incident_info(description)
        
        # Should handle gracefully and return fallback
        assert isinstance(result, IncidentResponse)


class TestConfiguration:
    """Test cases for configuration management."""

    def test_settings_loading(self):
        """Test settings loading."""
        from app.config import settings
        
        assert hasattr(settings, 'llm_provider')
        assert hasattr(settings, 'ollama_url')
        assert hasattr(settings, 'model_name')
        assert hasattr(settings, 'api_title')
        assert hasattr(settings, 'api_version')

    def test_settings_validation(self):
        """Test settings validation."""
        from app.config import Settings
        
        # Test valid settings
        valid_settings = Settings(
            llm_provider="ollama",
            port=8000,
            request_timeout=30
        )
        
        assert valid_settings.llm_provider == "ollama"
        assert valid_settings.port == 8000
        assert valid_settings.request_timeout == 30

    def test_development_mode_detection(self):
        """Test development mode detection."""
        from app.config import settings
        
        # Should be able to detect development mode
        is_dev = settings.is_development
        assert isinstance(is_dev, bool)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])