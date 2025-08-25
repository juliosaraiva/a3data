"""Preprocessor agent for text normalization and cleaning."""

import re

from incident_extractor.config import Settings, get_settings
from incident_extractor.config.llm import get_llm_config
from incident_extractor.config.logging import get_logger, log_agent_activity
from incident_extractor.models.schemas import AgentState
from incident_extractor.services.llm_service import get_llm_service_manager


class PreprocessorAgent:
    """
    Preprocessor agent that cleans and normalizes incident text.

    Responsibilities:
    - Clean and normalize Portuguese text
    - Standardize date/time references
    - Fix common typos and formatting issues
    - Expand abbreviations
    - Prepare text for information extraction
    """

    def __init__(self):
        self.logger = get_logger("agent.preprocessor")
        self.config = get_llm_config().preprocessor
        self.settings: Settings = get_settings()

        # Preprocessing patterns for Portuguese text
        self._initialize_patterns()

    def _initialize_patterns(self) -> None:
        """Initialize regex patterns for text preprocessing."""

        # Date/time patterns
        self.date_patterns = [
            (r"\bontem\b", "ontem"),
            (r"\bhoje\b", "hoje"),
            (r"\bamanhã\b", "amanhã"),
            (r"\bseg\b", "segunda-feira"),
            (r"\bter\b", "terça-feira"),
            (r"\bqua\b", "quarta-feira"),
            (r"\bqui\b", "quinta-feira"),
            (r"\bsex\b", "sexta-feira"),
            (r"\bsab\b", "sábado"),
            (r"\bdom\b", "domingo"),
        ]

        # Location standardization
        self.location_patterns = [
            (r"\bsp\b", "São Paulo"),
            (r"\brj\b", "Rio de Janeiro"),
            (r"\bbh\b", "Belo Horizonte"),
            (r"\bbsb\b", "Brasília"),
            (r"\bdatacenter\b", "data center"),
            (r"\bdc\b", "data center"),
        ]

        # Technical term standardization
        self.technical_patterns = [
            (r"\bserver\b", "servidor"),
            (r"\bfirewall\b", "firewall"),
            (r"\bdatabase\b", "banco de dados"),
            (r"\bdb\b", "banco de dados"),
            (r"\bapi\b", "API"),
            (r"\burl\b", "URL"),
            (r"\bip\b", "IP"),
            (r"\bvpn\b", "VPN"),
        ]

        # Common typos in Portuguese
        self.typo_patterns = [
            (r"\bfalaha\b", "falha"),
            (r"\bsistema\b", "sistema"),
            (r"\bproblema\b", "problema"),
            (r"\bservico\b", "serviço"),
            (r"\bindicponivel\b", "indisponível"),
            (r"\bfuncinando\b", "funcionando"),
        ]

    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute the preprocessing logic.

        Args:
            state: Current workflow state

        Returns:
            Updated state with preprocessed text
        """
        log_agent_activity("preprocessor", "Starting text preprocessing", text_length=len(state.raw_text))

        try:
            state.current_status = "preprocessamento"

            # Check text length limits
            if len(state.raw_text) > self.settings.max_preprocessing_length:
                state.add_warning(
                    f"Text length ({len(state.raw_text)}) exceeds maximum ({self.settings.max_preprocessing_length}), truncating"
                )
                text_to_process = state.raw_text[: self.settings.max_preprocessing_length]
            else:
                text_to_process = state.raw_text

            # Apply deterministic preprocessing
            preprocessed_text = await self._apply_deterministic_preprocessing(text_to_process)

            # Apply LLM-based preprocessing if needed
            if self._needs_llm_preprocessing(preprocessed_text):
                preprocessed_text = await self._apply_llm_preprocessing(preprocessed_text)

            # Final validation and cleanup
            preprocessed_text = self._final_cleanup(preprocessed_text)

            # Update state
            state.preprocessed_text = preprocessed_text
            state.preprocessor_output = {
                "original_length": len(state.raw_text),
                "processed_length": len(preprocessed_text),
                "preprocessing_applied": self._get_applied_preprocessing_summary(state.raw_text, preprocessed_text),
                "needs_llm": self._needs_llm_preprocessing(state.raw_text),
                "timestamp": state.timestamp_inicio.isoformat(),
            }

            log_agent_activity(
                "preprocessor",
                "Preprocessing completed",
                original_length=len(state.raw_text),
                processed_length=len(preprocessed_text),
                changes_made=len(state.preprocessor_output["preprocessing_applied"]),
            )

            return state

        except Exception as e:
            error_msg = f"Preprocessor agent failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            state.add_error(error_msg)
            # Use original text as fallback
            state.preprocessed_text = state.raw_text
            return state

    async def _apply_deterministic_preprocessing(self, text: str) -> str:
        """
        Apply rule-based preprocessing transformations.

        Args:
            text: Input text to preprocess

        Returns:
            Preprocessed text
        """
        processed_text = text

        # Basic cleaning
        processed_text = re.sub(r"\s+", " ", processed_text)  # Multiple spaces to single
        processed_text = processed_text.strip()

        # Fix common punctuation issues
        processed_text = re.sub(r"\.{2,}", ".", processed_text)  # Multiple dots
        processed_text = re.sub(r",{2,}", ",", processed_text)  # Multiple commas
        processed_text = re.sub(r"\s+([,.!?;:])", r"\1", processed_text)  # Space before punctuation

        # Apply pattern replacements
        for pattern, replacement in self.date_patterns:
            processed_text = re.sub(pattern, replacement, processed_text, flags=re.IGNORECASE)

        for pattern, replacement in self.location_patterns:
            processed_text = re.sub(pattern, replacement, processed_text, flags=re.IGNORECASE)

        for pattern, replacement in self.technical_patterns:
            processed_text = re.sub(pattern, replacement, processed_text, flags=re.IGNORECASE)

        for pattern, replacement in self.typo_patterns:
            processed_text = re.sub(pattern, replacement, processed_text, flags=re.IGNORECASE)

        # Normalize time references
        processed_text = self._normalize_time_references(processed_text)

        return processed_text

    def _normalize_time_references(self, text: str) -> str:
        """
        Normalize time references to standard format.

        Args:
            text: Input text

        Returns:
            Text with normalized time references
        """
        # Convert "às 14h" to "às 14:00"
        text = re.sub(r"\bàs\s+(\d{1,2})h\b", r"às \1:00", text)
        text = re.sub(r"\b(\d{1,2})h(\d{2})\b", r"\1:\2", text)
        text = re.sub(r"\b(\d{1,2})h\b", r"\1:00", text)

        # Normalize "hoje", "ontem", "amanhã" with context
        import datetime

        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        tomorrow = today + datetime.timedelta(days=1)

        text = text.replace("hoje", f"hoje ({today.strftime('%Y-%m-%d')})")
        text = text.replace("ontem", f"ontem ({yesterday.strftime('%Y-%m-%d')})")
        text = text.replace("amanhã", f"amanhã ({tomorrow.strftime('%Y-%m-%d')})")

        return text

    def _needs_llm_preprocessing(self, text: str) -> bool:
        """
        Determine if text needs LLM-based preprocessing.

        Args:
            text: Text to analyze

        Returns:
            True if LLM preprocessing is needed
        """
        # Check for complex patterns that might need LLM processing
        complexity_indicators = [
            len(re.findall(r"[,.;!?]", text)) > 10,  # Many punctuation marks
            len(text.split()) > 50,  # Long text
            bool(re.search(r"[^\w\s\-.,;!?():áàâãéèêíìîóòôõúùûç]", text)),  # Special characters
            "erro" in text.lower() and "sistema" in text.lower(),  # Error descriptions
            any(word in text.lower() for word in ["falha", "indisponível", "problema", "incidente"]),
        ]

        return sum(complexity_indicators) >= 2

    async def _apply_llm_preprocessing(self, text: str) -> str:
        """
        Apply LLM-based preprocessing for complex text.

        Args:
            text: Text to preprocess

        Returns:
            LLM-preprocessed text
        """
        try:
            prompt = self._create_preprocessing_prompt(text)

            # Get LLM service manager
            service_manager = await get_llm_service_manager()

            # Generate preprocessed text using fallback services
            response = await service_manager.generate_with_fallback(
                ["ollama", "openai", "mock"], prompt, self.config.system_prompt
            )

            # Extract the preprocessed text from response
            preprocessed = self._extract_preprocessed_text(response)

            # Validate the result
            if self._validate_preprocessed_text(text, preprocessed):
                return preprocessed
            else:
                self.logger.warning("LLM preprocessing validation failed, using deterministic result")
                return text

        except Exception as e:
            self.logger.warning(f"LLM preprocessing failed: {e}")
            return text

    def _create_preprocessing_prompt(self, text: str) -> str:
        """Create prompt for LLM-based preprocessing."""
        return f"""
Normalize e limpe o seguinte texto sobre um incidente de TI, mantendo todas as informações importantes:

Texto original:
{text}

Tarefas de normalização:
1. Corrija erros de ortografia e gramática óbvios
2. Padronize referências de data e hora (use formato claro)
3. Expanda abreviações técnicas quando necessário
4. Normalize nomes de locais
5. Mantenha todos os detalhes factuais intactos
6. Use português brasileiro padrão

Texto normalizado:"""

    def _extract_preprocessed_text(self, response: str) -> str:
        """Extract preprocessed text from LLM response."""
        # Remove common LLM response prefixes
        lines = response.strip().split("\n")

        # Find the actual content (skip explanatory text)
        content_start = 0
        for i, line in enumerate(lines):
            if any(keyword in line.lower() for keyword in ["texto", "normalizado", ":"]):
                content_start = i + 1
                break

        # Join the remaining lines
        if content_start < len(lines):
            preprocessed = "\n".join(lines[content_start:]).strip()
        else:
            preprocessed = response.strip()

        # Clean up any remaining formatting
        preprocessed = re.sub(r"^[:\-\s]+", "", preprocessed)
        preprocessed = re.sub(r"\s+", " ", preprocessed)

        return preprocessed.strip()

    def _validate_preprocessed_text(self, original: str, preprocessed: str) -> bool:
        """
        Validate that preprocessing didn't lose important information.

        Args:
            original: Original text
            preprocessed: Preprocessed text

        Returns:
            True if preprocessing is valid
        """
        # Check length ratio
        length_ratio = len(preprocessed) / len(original)
        if length_ratio < 0.5 or length_ratio > 2.0:
            return False

        # Check that key terms are preserved
        key_terms = ["incidente", "falha", "sistema", "servidor", "erro", "problema"]
        original_lower = original.lower()
        preprocessed_lower = preprocessed.lower()

        for term in key_terms:
            if term in original_lower and term not in preprocessed_lower:
                # Important term was removed
                return False

        # Check for completely empty result
        if not preprocessed.strip():
            return False

        return True

    def _final_cleanup(self, text: str) -> str:
        """
        Apply final cleanup operations.

        Args:
            text: Text to clean up

        Returns:
            Final cleaned text
        """
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        # Ensure proper sentence endings
        if text and not text.endswith((".", "!", "?")):
            text += "."

        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]

        return text

    def _get_applied_preprocessing_summary(self, original: str, processed: str) -> list[str]:
        """
        Get summary of preprocessing operations applied.

        Args:
            original: Original text
            processed: Processed text

        Returns:
            List of applied operations
        """
        operations: list[str] = []

        if len(processed) != len(original):
            operations.append(f"length_changed: {len(original)} -> {len(processed)}")

        if re.search(r"\s{2,}", original) and not re.search(r"\s{2,}", processed):
            operations.append("normalized_whitespace")

        if "ontem" in original and "ontem (" in processed:
            operations.append("expanded_time_references")

        # Check for pattern applications
        for pattern, replacement in self.technical_patterns:
            if re.search(pattern, original, re.IGNORECASE) and replacement in processed:
                operations.append(f"technical_term: {pattern} -> {replacement}")

        if not operations:
            operations.append("minimal_changes")

        return operations
