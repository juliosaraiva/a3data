"""Text preprocessing service for incident extraction."""

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pytz
from pydantic import BaseModel, Field


@dataclass
class TextProcessorConfig:
    """Configuration for text preprocessing."""

    # Brazilian locale settings
    locale: str = "pt_BR"
    timezone: str = "America/Sao_Paulo"

    # Text normalization settings
    normalize_unicode: bool = True
    normalize_whitespace: bool = True
    normalize_quotes: bool = True
    normalize_currency: bool = True

    # Content filtering
    min_text_length: int = 10
    max_text_length: int = 10000
    remove_html: bool = True
    remove_urls: bool = False
    remove_emails: bool = False
    remove_phone_numbers: bool = False

    # Date/time extraction settings
    extract_dates: bool = True
    extract_times: bool = True
    date_formats: list[str] = None

    def __post_init__(self) -> None:
        """Initialize default date formats if not provided."""
        if self.date_formats is None:
            self.date_formats = [
                "%d/%m/%Y",  # 25/12/2023
                "%d-%m-%Y",  # 25-12-2023
                "%d.%m.%Y",  # 25.12.2023
                "%d de %B de %Y",  # 25 de dezembro de 2023
                "%d %B %Y",  # 25 dezembro 2023
                "%Y-%m-%d",  # 2023-12-25
                "%d/%m/%Y %H:%M",  # 25/12/2023 14:30
                "%d/%m/%Y %H:%M:%S",  # 25/12/2023 14:30:45
            ]


class TextExtractionResult(BaseModel):
    """Result of text extraction and preprocessing."""

    normalized_text: str = Field(..., description="Preprocessed and normalized text")
    original_text: str = Field(..., description="Original input text")
    extracted_dates: list[datetime] = Field(default_factory=list, description="Extracted dates")
    extracted_times: list[str] = Field(default_factory=list, description="Extracted time references")
    extracted_locations: list[str] = Field(default_factory=list, description="Extracted location references")
    extracted_numbers: list[float] = Field(default_factory=list, description="Extracted numeric values")
    word_count: int = Field(..., description="Word count of normalized text")
    character_count: int = Field(..., description="Character count of normalized text")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional extraction metadata")


class TextProcessor:
    """Advanced text preprocessing service for incident extraction.

    Provides Brazilian Portuguese-specific text normalization,
    date/time extraction, and content preprocessing.
    """

    def __init__(self, config: TextProcessorConfig | None = None) -> None:
        """Initialize text processor with configuration."""
        self.config = config or TextProcessorConfig()
        self.timezone = pytz.timezone(self.config.timezone)

        # Compile regex patterns for performance
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile frequently used regex patterns."""
        # Brazilian phone number patterns
        self.phone_pattern = re.compile(
            r"(?:\+55\s?)?(?:\(?(?:11|12|13|14|15|16|17|18|19|21|22|24|27|28|31|32|33|34|35|37|38|41|42|43|44|45|46|47|48|49|51|53|54|55|61|62|63|64|65|66|67|68|69|71|73|74|75|77|79|81|82|83|84|85|86|87|88|89|91|92|93|94|95|96|97|98|99)\)?\s?)?(?:9\s?)?[0-9]{4}[\-\s]?[0-9]{4}",
            re.IGNORECASE,
        )

        # Email pattern
        self.email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

        # URL pattern
        self.url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')

        # HTML tag pattern
        self.html_pattern = re.compile(r"<[^>]+>")

        # Whitespace normalization pattern
        self.whitespace_pattern = re.compile(r"\s+")

        # Brazilian currency pattern
        self.currency_pattern = re.compile(r"R\$\s*([0-9.,]+)")

        # Number extraction pattern
        self.number_pattern = re.compile(r"\b\d+(?:[.,]\d+)*\b")

        # Brazilian location indicators
        self.location_indicators = re.compile(
            r"\b(?:Rua|Av|Avenida|Travessa|Alameda|Praça|Largo|Rodovia|Estrada|Via|R\.|Av\.)[\s\.]\s*([^,\n]+)", re.IGNORECASE
        )

        # Time pattern (Brazilian format)
        self.time_pattern = re.compile(
            r"\b(?:(?:[01]?[0-9]|2[0-3]):?[0-5][0-9](?::[0-5][0-9])?(?:\s*(?:h|hrs?|horas?))?)|\b(?:(?:[01]?[0-9]|1[0-2])\s*(?:da\s+)?(?:manhã|tarde|madrugada|noite))\b",
            re.IGNORECASE,
        )

        # Brazilian date patterns
        self.date_patterns = [
            re.compile(r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b"),  # dd/mm/yyyy
            re.compile(r"\b(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\b", re.IGNORECASE),  # dd de mês de yyyy
        ]

    async def process_text(self, text: str, **kwargs: Any) -> TextExtractionResult:
        """Process and extract information from text.

        Args:
            text: Input text to process
            **kwargs: Additional processing options

        Returns:
            TextExtractionResult with processed text and extracted information

        Raises:
            ValueError: If text is empty or exceeds length limits
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        original_text = text

        # Validate text length
        if len(text) < self.config.min_text_length:
            raise ValueError(f"Text too short (minimum {self.config.min_text_length} characters)")

        if len(text) > self.config.max_text_length:
            raise ValueError(f"Text too long (maximum {self.config.max_text_length} characters)")

        # Extract information before normalization
        extracted_dates = self._extract_dates(text) if self.config.extract_dates else []
        extracted_times = self._extract_times(text) if self.config.extract_times else []
        extracted_locations = self._extract_locations(text)
        extracted_numbers = self._extract_numbers(text)

        # Normalize text
        normalized_text = await self._normalize_text(text)

        # Calculate metrics
        word_count = len(normalized_text.split())
        character_count = len(normalized_text)

        # Create metadata
        metadata = {
            "processing_timestamp": datetime.now(self.timezone).isoformat(),
            "config_used": {
                "locale": self.config.locale,
                "timezone": self.config.timezone,
            },
            "extraction_stats": {
                "dates_found": len(extracted_dates),
                "times_found": len(extracted_times),
                "locations_found": len(extracted_locations),
                "numbers_found": len(extracted_numbers),
            },
        }

        return TextExtractionResult(
            normalized_text=normalized_text,
            original_text=original_text,
            extracted_dates=extracted_dates,
            extracted_times=extracted_times,
            extracted_locations=extracted_locations,
            extracted_numbers=extracted_numbers,
            word_count=word_count,
            character_count=character_count,
            metadata=metadata,
        )

    async def _normalize_text(self, text: str) -> str:
        """Normalize text according to configuration."""
        result = text

        # Remove HTML tags
        if self.config.remove_html:
            result = self.html_pattern.sub("", result)

        # Remove URLs
        if self.config.remove_urls:
            result = self.url_pattern.sub(" ", result)

        # Remove emails
        if self.config.remove_emails:
            result = self.email_pattern.sub("", result)

        # Remove phone numbers
        if self.config.remove_phone_numbers:
            result = self.phone_pattern.sub("", result)

        # Unicode normalization
        if self.config.normalize_unicode:
            result = unicodedata.normalize("NFKC", result)

        # Normalize quotes
        if self.config.normalize_quotes:
            result = result.replace('"', '"').replace('"', '"')
            result = result.replace(""", "'").replace(""", "'")

        # Normalize currency
        if self.config.normalize_currency:
            result = self.currency_pattern.sub(r"R$ \1", result)

        # Normalize whitespace
        if self.config.normalize_whitespace:
            result = self.whitespace_pattern.sub(" ", result)
            result = result.strip()

        return result

    def _extract_dates(self, text: str) -> list[datetime]:
        """Extract dates from text using Brazilian formats."""
        dates = []

        for pattern in self.date_patterns:
            matches = pattern.findall(text)
            for match in matches:
                try:
                    if len(match) == 3:
                        if match[1].isdigit():  # dd/mm/yyyy format
                            day, month, year = int(match[0]), int(match[1]), int(match[2])
                            date = datetime(year, month, day, tzinfo=self.timezone)
                            dates.append(date)
                        else:  # dd de mês de yyyy format
                            day, month_name, year = match[0], match[1], match[2]
                            # Convert month name to number (Brazilian Portuguese)
                            month_map = {
                                "janeiro": 1,
                                "fevereiro": 2,
                                "março": 3,
                                "abril": 4,
                                "maio": 5,
                                "junho": 6,
                                "julho": 7,
                                "agosto": 8,
                                "setembro": 9,
                                "outubro": 10,
                                "novembro": 11,
                                "dezembro": 12,
                            }
                            month = month_map.get(month_name.lower())
                            if month:
                                date = datetime(int(year), month, int(day), tzinfo=self.timezone)
                                dates.append(date)
                except (ValueError, TypeError):
                    continue  # Skip invalid dates

        return dates

    def _extract_times(self, text: str) -> list[str]:
        """Extract time references from text."""
        times = []
        matches = self.time_pattern.findall(text)
        for match in matches:
            times.append(match.strip())
        return times

    def _extract_locations(self, text: str) -> list[str]:
        """Extract location references from text."""
        locations = []
        matches = self.location_indicators.findall(text)
        for match in matches:
            location = match.strip()
            if len(location) > 3:  # Avoid very short matches
                locations.append(location)
        return locations

    def _extract_numbers(self, text: str) -> list[float]:
        """Extract numeric values from text."""
        numbers = []
        matches = self.number_pattern.findall(text)
        for match in matches:
            try:
                # Handle Brazilian number format (comma as decimal separator)
                if "," in match and "." in match:
                    # Format like 1.234.567,89
                    normalized = match.replace(".", "").replace(",", ".")
                elif "," in match:
                    # Format like 123,45
                    normalized = match.replace(",", ".")
                else:
                    # Standard format
                    normalized = match

                number = float(normalized)
                numbers.append(number)
            except ValueError:
                continue  # Skip invalid numbers

        return numbers

    def get_processing_stats(self) -> dict[str, Any]:
        """Get processing statistics and configuration."""
        return {
            "config": {
                "locale": self.config.locale,
                "timezone": self.config.timezone,
                "normalize_unicode": self.config.normalize_unicode,
                "normalize_whitespace": self.config.normalize_whitespace,
                "remove_html": self.config.remove_html,
                "min_text_length": self.config.min_text_length,
                "max_text_length": self.config.max_text_length,
            },
            "patterns_compiled": {
                "phone_pattern": bool(self.phone_pattern),
                "email_pattern": bool(self.email_pattern),
                "url_pattern": bool(self.url_pattern),
                "html_pattern": bool(self.html_pattern),
                "currency_pattern": bool(self.currency_pattern),
            },
        }
