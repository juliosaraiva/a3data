"""Text preprocessing utilities for incident descriptions."""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class TextPreprocessor:
    """Text preprocessing pipeline for incident descriptions."""

    def __init__(self, max_length: int = 2000, normalize_text: bool = True):
        """Initialize the preprocessor."""
        self.max_length = max_length
        self.normalize_text = normalize_text

    def preprocess(self, text: str) -> str:
        """Apply full preprocessing pipeline to text."""
        if not text or not text.strip():
            return ""

        processed_text = text.strip()

        if self.normalize_text:
            processed_text = self._normalize_whitespace(processed_text)
            processed_text = self._normalize_dates(processed_text)
            processed_text = self._normalize_times(processed_text)
            processed_text = self._clean_special_characters(processed_text)

        processed_text = self._truncate_text(processed_text)
        
        logger.debug(f"Preprocessed text: {len(processed_text)} chars")
        return processed_text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace characters."""
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        return text.strip()

    def _normalize_dates(self, text: str) -> str:
        """Normalize date references in text."""
        today = datetime.now()
        
        # Replace relative date references
        replacements = {
            r'\bhoje\b': today.strftime("%d/%m/%Y"),
            r'\bontem\b': (today - timedelta(days=1)).strftime("%d/%m/%Y"),
            r'\banteontem\b': (today - timedelta(days=2)).strftime("%d/%m/%Y"),
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text

    def _normalize_times(self, text: str) -> str:
        """Normalize time references in text."""
        # Normalize time formats (e.g., "14h" -> "14:00")
        text = re.sub(r'\b(\d{1,2})h\b', r'\1:00', text)
        text = re.sub(r'\b(\d{1,2})h(\d{2})\b', r'\1:\2', text)
        
        return text

    def _clean_special_characters(self, text: str) -> str:
        """Clean problematic special characters."""
        # Remove or replace problematic characters that might interfere with LLM processing
        # Keep Portuguese characters and common punctuation
        text = re.sub(r'[^\w\s\-.,;:!?()áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ]', ' ', text)
        
        # Normalize multiple punctuation
        text = re.sub(r'[.]{2,}', '.', text)
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        return text

    def _truncate_text(self, text: str) -> str:
        """Truncate text to maximum length."""
        if len(text) <= self.max_length:
            return text
        
        # Try to truncate at sentence boundary
        truncated = text[:self.max_length]
        last_sentence_end = max(
            truncated.rfind('.'),
            truncated.rfind('!'),
            truncated.rfind('?')
        )
        
        if last_sentence_end > self.max_length * 0.8:  # If we can keep 80% of content
            truncated = truncated[:last_sentence_end + 1]
        
        logger.warning(f"Text truncated from {len(text)} to {len(truncated)} characters")
        return truncated

    def extract_date_hints(self, text: str) -> Optional[str]:
        """Extract potential date information for context."""
        today = datetime.now()
        
        # Look for explicit dates
        date_patterns = [
            (r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', r'\3-\2-\1'),  # DD/MM/YYYY -> YYYY-MM-DD
            (r'\b(\d{1,2})/(\d{1,2})/(\d{2})\b', f'20\\3-\\2-\\1'),  # DD/MM/YY -> 20YY-MM-DD
        ]
        
        for pattern, replacement in date_patterns:
            match = re.search(pattern, text)
            if match:
                return re.sub(pattern, replacement, match.group())
        
        # Look for relative dates
        if re.search(r'\bhoje\b', text, re.IGNORECASE):
            return today.strftime("%Y-%m-%d")
        elif re.search(r'\bontem\b', text, re.IGNORECASE):
            return (today - timedelta(days=1)).strftime("%Y-%m-%d")
        elif re.search(r'\banteontem\b', text, re.IGNORECASE):
            return (today - timedelta(days=2)).strftime("%Y-%m-%d")
        
        return None

    def extract_time_hints(self, text: str) -> Optional[str]:
        """Extract potential time information for context."""
        # Look for time patterns
        time_patterns = [
            r'\b(\d{1,2}):(\d{2})\b',  # HH:MM
            r'\b(\d{1,2})h(\d{2})\b',  # HHhMM
            r'\b(\d{1,2})h\b',         # HHh
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 2:
                    hour, minute = match.groups()
                    return f"{hour.zfill(2)}:{minute}"
                else:  # Single group (hour only)
                    hour = match.group(1)
                    return f"{hour.zfill(2)}:00"
        
        return None