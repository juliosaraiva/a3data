"""Helper services for the ExtractorAgent to reduce complexity."""

import json
import re
from datetime import datetime
from typing import Any

from incident_extractor.config.logging import get_logger


class DateTimeHandler:
    """Simple date/time operations for post-processing."""

    def __init__(self):
        self.logger = get_logger("service.datetime")
        self.today = datetime.now()

    def validate_datetime_format(self, date_str: str | None) -> str | None:
        """Validate and ensure datetime is in YYYY-MM-DD HH:MM format."""
        if not date_str:
            return None

        # Already in correct format
        if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$", date_str):
            return date_str

        # Try to parse and reformat if needed
        try:
            # Handle various input formats
            formats = [
                "%Y-%m-%d %H:%M:%S",  # With seconds
                "%Y-%m-%d %H:%M",  # Target format
                "%d/%m/%Y %H:%M",  # Brazilian format
                "%Y-%m-%d",  # Date only
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    continue

            self.logger.warning(f"Could not parse date format: {date_str}")
            return date_str  # Return as-is if unparseable

        except Exception as e:
            self.logger.error(f"Date validation failed: {e}")
            return None


class ResponseParser:
    """Clean JSON response parsing."""

    def __init__(self):
        self.logger = get_logger("service.parser")

    def extract_json(self, response: str) -> dict[str, Any] | None:
        """Extract and parse JSON from LLM response."""
        try:
            # Try direct parsing first
            if response.strip().startswith("{"):
                return json.loads(response.strip())

            # Look for JSON in code blocks or between markers
            json_patterns = [
                r"```json\s*(.*?)\s*```",  # JSON code block
                r"```\s*(.*?)\s*```",  # Generic code block
                r"\{[^}]*\}",  # Simple JSON object
            ]

            for pattern in json_patterns:
                matches = re.findall(pattern, response, re.DOTALL)
                for match in matches:
                    cleaned = match.strip()
                    if cleaned.startswith("{") and cleaned.endswith("}"):
                        try:
                            return json.loads(cleaned)
                        except json.JSONDecodeError:
                            continue

            self.logger.warning("No valid JSON found in response")
            return None

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Response parsing failed: {e}")
            return None


class FieldValidator:
    """Simple field validation and cleaning."""

    def __init__(self):
        self.logger = get_logger("service.validator")

    def clean_text_field(self, text: str | None, max_length: int) -> str | None:
        """Clean and validate text field."""
        if not text:
            return None

        # Remove extra whitespace
        cleaned = re.sub(r"\s+", " ", text.strip())

        # Remove surrounding quotes
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
            cleaned = cleaned[1:-1]

        # Truncate if too long
        if len(cleaned) > max_length:
            cleaned = cleaned[: max_length - 3] + "..."

        # Return None for empty or meaningless values
        if not cleaned or cleaned.lower() in ["null", "none", "n/a", "-"]:
            return None

        return cleaned

    def validate_extracted_data(self, data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        """Validate and clean extracted data fields."""
        validation_log: list[str] = []

        # Clean text fields
        if "local" in data:
            original = data["local"]
            data["local"] = self.clean_text_field(original, 200)
            if original != data["local"]:
                validation_log.append("local_cleaned")

        if "tipo_incidente" in data:
            original = data["tipo_incidente"]
            data["tipo_incidente"] = self.clean_text_field(original, 150)
            if original != data["tipo_incidente"]:
                validation_log.append("tipo_incidente_cleaned")

        if "impacto" in data:
            original = data["impacto"]
            data["impacto"] = self.clean_text_field(original, 500)
            if original != data["impacto"]:
                validation_log.append("impacto_cleaned")

        return data, validation_log

    def calculate_simple_confidence(self, data: dict[str, Any]) -> float:
        """Calculate simple confidence based on field completeness."""
        if not data:
            return 0.0

        # Check how many required fields are present
        required_fields = ["data_ocorrencia", "local", "tipo_incidente", "impacto"]
        present_fields = sum(1 for field in required_fields if data.get(field))

        # Consider LLM-provided confidence if available
        llm_confidence = data.get("confidence", "medium")
        confidence_multiplier = {"high": 1.0, "medium": 0.8, "low": 0.6}.get(llm_confidence, 0.8)

        base_score = present_fields / len(required_fields)
        return base_score * confidence_multiplier
