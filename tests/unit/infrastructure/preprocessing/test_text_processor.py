"""Tests for text preprocessing functionality."""

import pytest

from src.incident_extractor.infrastructure.preprocessing import TextProcessor, TextProcessorConfig


class TestTextProcessorConfig:
    """Test TextProcessorConfig functionality."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = TextProcessorConfig()

        assert config.locale == "pt_BR"
        assert config.timezone == "America/Sao_Paulo"
        assert config.normalize_unicode is True
        assert config.normalize_whitespace is True
        assert config.min_text_length == 10
        assert config.max_text_length == 10000
        assert config.extract_dates is True
        assert config.extract_times is True

        # Check that default date formats are set
        assert config.date_formats is not None
        assert len(config.date_formats) > 0
        assert "%d/%m/%Y" in config.date_formats

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        custom_formats = ["%d/%m/%Y", "%Y-%m-%d"]
        config = TextProcessorConfig(
            locale="en_US", timezone="UTC", normalize_unicode=False, min_text_length=5, date_formats=custom_formats
        )

        assert config.locale == "en_US"
        assert config.timezone == "UTC"
        assert config.normalize_unicode is False
        assert config.min_text_length == 5
        assert config.date_formats == custom_formats


class TestTextProcessor:
    """Test TextProcessor functionality."""

    @pytest.fixture
    def processor(self) -> TextProcessor:
        """Create a text processor with default config."""
        return TextProcessor()

    @pytest.fixture
    def custom_processor(self) -> TextProcessor:
        """Create a text processor with custom config."""
        config = TextProcessorConfig(
            normalize_unicode=True,
            normalize_whitespace=True,
            remove_html=True,
            remove_urls=True,
            extract_dates=True,
            extract_times=True,
        )
        return TextProcessor(config)

    async def test_basic_text_processing(self, processor: TextProcessor) -> None:
        """Test basic text processing functionality."""
        text = "Este é um texto de teste com informações sobre um incidente."

        result = await processor.process_text(text)

        assert result.original_text == text
        assert result.normalized_text == text
        assert result.word_count > 0
        assert result.character_count == len(text)
        assert isinstance(result.extracted_dates, list)
        assert isinstance(result.extracted_times, list)
        assert isinstance(result.extracted_locations, list)
        assert isinstance(result.extracted_numbers, list)

    async def test_text_length_validation(self, processor: TextProcessor) -> None:
        """Test text length validation."""
        # Test empty text
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await processor.process_text("")

        with pytest.raises(ValueError, match="Text cannot be empty"):
            await processor.process_text("   ")

        # Test text too short
        with pytest.raises(ValueError, match="Text too short"):
            await processor.process_text("short")

        # Test text too long
        long_text = "a" * 10001
        with pytest.raises(ValueError, match="Text too long"):
            await processor.process_text(long_text)

    async def test_html_removal(self, custom_processor: TextProcessor) -> None:
        """Test HTML tag removal."""
        text = "<p>Este é um <strong>teste</strong> com <em>HTML</em>.</p>"

        result = await custom_processor.process_text(text)

        assert "<p>" not in result.normalized_text
        assert "<strong>" not in result.normalized_text
        assert "<em>" not in result.normalized_text
        assert "Este é um teste com HTML." == result.normalized_text

    async def test_url_removal(self, processor: TextProcessor) -> None:
        """Test URL removal."""
        config = TextProcessorConfig(remove_urls=True)
        processor = TextProcessor(config)

        text = "Visite https://example.com para mais informações sobre o incidente."

        result = await processor.process_text(text)

        assert "https://example.com" not in result.normalized_text
        assert "Visite para mais informações sobre o incidente." == result.normalized_text

    async def test_whitespace_normalization(self, processor: TextProcessor) -> None:
        """Test whitespace normalization."""
        text = "Este    é   um    texto    com    espaços     extras."

        result = await processor.process_text(text)

        assert "Este é um texto com espaços extras." == result.normalized_text

    async def test_brazilian_date_extraction(self, processor: TextProcessor) -> None:
        """Test Brazilian date format extraction."""
        text = "O incidente ocorreu em 25/12/2023 e foi relatado em 26 de dezembro de 2023."

        result = await processor.process_text(text)

        assert len(result.extracted_dates) >= 1
        # Check that at least one date was extracted correctly
        found_date = any(date.day == 25 and date.month == 12 and date.year == 2023 for date in result.extracted_dates)
        assert found_date

    async def test_brazilian_time_extraction(self, processor: TextProcessor) -> None:
        """Test Brazilian time format extraction."""
        text = "O incidente aconteceu às 14:30 da tarde e foi resolvido às 16h45."

        result = await processor.process_text(text)

        assert len(result.extracted_times) >= 1
        assert any("14:30" in time_ref or "16h45" in time_ref for time_ref in result.extracted_times)

    async def test_location_extraction(self, processor: TextProcessor) -> None:
        """Test location extraction from Brazilian addresses."""
        text = "O incidente ocorreu na Rua das Flores, 123 e na Avenida Paulista, 1000."

        result = await processor.process_text(text)

        assert len(result.extracted_locations) >= 1
        locations = " ".join(result.extracted_locations).lower()
        assert "das flores" in locations or "paulista" in locations

    async def test_number_extraction(self, processor: TextProcessor) -> None:
        """Test number extraction including Brazilian formats."""
        text = "O valor foi R$ 1.234,56 e a temperatura era 25,7 graus."

        result = await processor.process_text(text)

        assert len(result.extracted_numbers) >= 1
        # Should extract 1234.56 and 25.7
        numbers = set(result.extracted_numbers)
        assert 1234.56 in numbers or 25.7 in numbers

    async def test_currency_normalization(self, processor: TextProcessor) -> None:
        """Test Brazilian currency normalization."""
        text = "O custo foi R$1.234,56 para reparos."

        result = await processor.process_text(text)

        assert "R$ 1.234,56" in result.normalized_text

    async def test_metadata_generation(self, processor: TextProcessor) -> None:
        """Test metadata generation."""
        text = "Este é um texto de teste para validar metadados."

        result = await processor.process_text(text)

        assert "processing_timestamp" in result.metadata
        assert "config_used" in result.metadata
        assert "extraction_stats" in result.metadata

        config_info = result.metadata["config_used"]
        assert config_info["locale"] == "pt_BR"
        assert config_info["timezone"] == "America/Sao_Paulo"

        stats = result.metadata["extraction_stats"]
        assert "dates_found" in stats
        assert "times_found" in stats
        assert "locations_found" in stats
        assert "numbers_found" in stats

    def test_get_processing_stats(self, processor: TextProcessor) -> None:
        """Test processing statistics retrieval."""
        stats = processor.get_processing_stats()

        assert "config" in stats
        assert "patterns_compiled" in stats

        config_info = stats["config"]
        assert config_info["locale"] == "pt_BR"
        assert config_info["timezone"] == "America/Sao_Paulo"

        patterns = stats["patterns_compiled"]
        assert patterns["phone_pattern"] is True
        assert patterns["email_pattern"] is True
        assert patterns["currency_pattern"] is True

    async def test_phone_number_removal(self, processor: TextProcessor) -> None:
        """Test Brazilian phone number removal."""
        config = TextProcessorConfig(remove_phone_numbers=True)
        processor = TextProcessor(config)

        text = "Contato: (11) 99999-9999 ou +55 11 98888-8888"

        result = await processor.process_text(text)

        assert "(11) 99999-9999" not in result.normalized_text
        assert "+55 11 98888-8888" not in result.normalized_text

    async def test_email_removal(self, processor: TextProcessor) -> None:
        """Test email address removal."""
        config = TextProcessorConfig(remove_emails=True)
        processor = TextProcessor(config)

        text = "Entre em contato: usuario@example.com para mais informações."

        result = await processor.process_text(text)

        assert "usuario@example.com" not in result.normalized_text

    async def test_unicode_normalization(self, processor: TextProcessor) -> None:
        """Test Unicode normalization."""
        # Text with different unicode representations of the same characters
        text = "café naïve résumé"  # These might have different unicode representations

        result = await processor.process_text(text)

        # Should be normalized to consistent unicode form
        assert result.normalized_text is not None
        assert len(result.normalized_text) > 0

    async def test_quote_normalization(self, processor: TextProcessor) -> None:
        """Test quote character normalization."""
        text = "\"Este é um 'teste' com aspas diferentes.\""

        result = await processor.process_text(text)

        # Should normalize to standard quotes
        assert "\"Este é um 'teste' com aspas diferentes.\"" == result.normalized_text

    async def test_empty_extraction_results(self, processor: TextProcessor) -> None:
        """Test behavior when no extractable content is found."""
        text = "Este é apenas um texto simples sem datas ou números especiais."

        result = await processor.process_text(text)

        # Should still return valid result even if no special content found
        assert result.normalized_text == text
        assert result.word_count > 0
        assert isinstance(result.extracted_dates, list)  # May be empty
        assert isinstance(result.extracted_times, list)  # May be empty

    async def test_extraction_with_custom_config(self) -> None:
        """Test extraction with disabled features."""
        config = TextProcessorConfig(
            extract_dates=False, extract_times=False, normalize_unicode=False, normalize_whitespace=False
        )
        processor = TextProcessor(config)

        text = "Data: 25/12/2023 às 14:30, valor: R$ 100,00"

        result = await processor.process_text(text)

        # Should not extract dates/times when disabled
        assert len(result.extracted_dates) == 0
        assert len(result.extracted_times) == 0
        # Should not normalize when disabled
        assert result.normalized_text == text
