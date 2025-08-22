"""Location value object for incident locations."""

from __future__ import annotations

import re
from dataclasses import dataclass

import structlog
from slugify import slugify

from ...core.exceptions import InvalidLocationError

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class Location:
    """Value object for incident locations with validation and normalization.

    Handles Brazilian location formats and common variations.
    Normalizes state abbreviations, city names, and location descriptions.
    """

    value: str
    normalized: str = ""
    city: str | None = None
    state: str | None = None

    def __post_init__(self):
        """Validate and normalize the location value."""
        if not self.value or not self.value.strip():
            raise InvalidLocationError("Location value cannot be empty")

        # Business rule: location cannot be too long
        if len(self.value) > 500:
            raise InvalidLocationError("Location value cannot be longer than 500 characters")

        # Normalize the location
        normalized = self._normalize_location(self.value)
        object.__setattr__(self, "normalized", normalized)

        # Extract city and state if possible
        city, state = self._extract_location_parts(normalized)
        object.__setattr__(self, "city", city)
        object.__setattr__(self, "state", state)

    def __str__(self) -> str:
        """Return the normalized location string."""
        return self.normalized

    def to_slug(self) -> str:
        """Convert location to URL-safe slug."""
        return slugify(self.normalized)

    @classmethod
    def from_string(cls, location_str: str) -> Location | None:
        """Create Location from string with error handling.

        Args:
            location_str: The location string to create the Location object from.

        Returns:
            Location instance or None if invalid
        """
        if not location_str or not location_str.strip():
            return None

        try:
            return cls(value=location_str.strip())
        except InvalidLocationError as e:
            logger.warning("Invalid location", location=location_str, error=str(e))
            return None

    def _normalize_location(self, location: str) -> str:
        """Normalize location string.

        Args:
            location: Raw location string

        Returns:
            Normalized location string
        """
        # Remove extra whitespace
        normalized = " ".join(location.split())

        # Capitalize first letter of each word for better readability
        normalized = normalized.title()

        # Handle common Brazilian state abbreviations
        state_abbreviations = {
            "Sp": "SP",
            "São Paulo": "SP",
            "Sao Paulo": "SP",
            "Rj": "RJ",
            "Rio De Janeiro": "RJ",
            "Rio de Janeiro": "RJ",
            "Mg": "MG",
            "Minas Gerais": "MG",
            "Rs": "RS",
            "Rio Grande Do Sul": "RS",
            "Rio Grande do Sul": "RS",
            "Pr": "PR",
            "Paraná": "PR",
            "Parana": "PR",
            "Sc": "SC",
            "Santa Catarina": "SC",
            "Ba": "BA",
            "Bahia": "BA",
            "Go": "GO",
            "Goiás": "GO",
            "Goias": "GO",
            "Mt": "MT",
            "Mato Grosso": "MT",
            "Ms": "MS",
            "Mato Grosso Do Sul": "MS",
            "Mato Grosso do Sul": "MS",
            "Es": "ES",
            "Espírito Santo": "ES",
            "Espirito Santo": "ES",
            "Ce": "CE",
            "Ceará": "CE",
            "Ceara": "CE",
            "Pe": "PE",
            "Pernambuco": "PE",
            "Pb": "PB",
            "Paraíba": "PB",
            "Paraiba": "PB",
            "Rn": "RN",
            "Rio Grande Do Norte": "RN",
            "Rio Grande do Norte": "RN",
            "Al": "AL",
            "Alagoas": "AL",
            "Se": "SE",
            "Sergipe": "SE",
            "Ma": "MA",
            "Maranhão": "MA",
            "Maranhao": "MA",
            "Pi": "PI",
            "Piauí": "PI",
            "Piaui": "PI",
            "To": "TO",
            "Tocantins": "TO",
            "Ro": "RO",
            "Rondônia": "RO",
            "Rondonia": "RO",
            "Ac": "AC",
            "Acre": "AC",
            "Am": "AM",
            "Amazonas": "AM",
            "Rr": "RR",
            "Roraima": "RR",
            "Pa": "PA",
            "Pará": "PA",
            "Para": "PA",
            "Ap": "AP",
            "Amapá": "AP",
            "Amapa": "AP",
            "Df": "DF",
            "Distrito Federal": "DF",
            "Brasília": "DF",
            "Brasilia": "DF",
        }

        # Apply state normalization
        for variation, correct in state_abbreviations.items():
            # Match whole words and common patterns
            patterns = [
                rf"\b{re.escape(variation)}\b",
                rf", {re.escape(variation)}$",
                rf" - {re.escape(variation)}$",
                rf" / {re.escape(variation)}$",
            ]
            for pattern in patterns:
                normalized = re.sub(pattern, f" {correct}", normalized, flags=re.IGNORECASE)

        # Normalize common location terms
        location_terms = {
            "Escritorio": "Escritório",
            "Predio": "Prédio",
            "Sala": "Sala",
            "Andar": "Andar",
            "Departamento": "Departamento",
            "Setor": "Setor",
            "Filial": "Filial",
            "Unidade": "Unidade",
            "Centro": "Centro",
            "Campus": "Campus",
            "Matriz": "Matriz",
        }

        for term, correct in location_terms.items():
            normalized = re.sub(rf"\b{term}\b", correct, normalized, flags=re.IGNORECASE)

        # Clean up extra spaces and punctuation
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = re.sub(r"\s*,\s*", ", ", normalized)
        normalized = re.sub(r"\s*-\s*", " - ", normalized)

        return normalized.strip()

    def _extract_location_parts(self, location: str) -> tuple[str | None, str | None]:
        """Extract city and state from normalized location."""
        # Brazilian state codes
        states = [
            "AC",
            "AL",
            "AP",
            "AM",
            "BA",
            "CE",
            "DF",
            "ES",
            "GO",
            "MA",
            "MT",
            "MS",
            "MG",
            "PA",
            "PB",
            "PR",
            "PE",
            "PI",
            "RJ",
            "RN",
            "RS",
            "RO",
            "RR",
            "SC",
            "SP",
            "SE",
            "TO",
        ]

        # Look for state pattern at the end
        state_pattern = r"\b(" + "|".join(states) + r")\b\s*$"
        state_match = re.search(state_pattern, location, re.IGNORECASE)

        state = state_match.group(1).upper() if state_match else None

        # Extract city - everything before state or comma
        city = None
        if state:
            # Remove state from end
            location_without_state = re.sub(state_pattern, "", location, flags=re.IGNORECASE).strip()
            # Get the last significant part as city
            parts = [p.strip() for p in location_without_state.split(",") if p.strip()]
            if parts:
                city = parts[-1].strip(" -/")
        else:
            # Try to get city from comma-separated parts
            parts = [p.strip() for p in location.split(",") if p.strip()]
            if len(parts) >= 2:
                # Assume last part might be state, second-to-last might be city
                city = parts[-2] if len(parts) > 1 else parts[0]
            elif parts:
                city = parts[0]

        # Clean city name
        if city:
            # Remove common prefixes/suffixes that aren't part of city name
            city = re.sub(r"^(Escritório|Prédio|Sala|Filial|Unidade)\s+", "", city, flags=re.IGNORECASE)
            city = city.strip(" -/")

        return city, state

    @property
    def is_specific(self) -> bool:
        """Check if location is specific (contains city, building, etc)."""
        # Specific if it has detailed location info
        specific_terms = [
            "escritório",
            "prédio",
            "sala",
            "andar",
            "departamento",
            "setor",
            "filial",
            "unidade",
            "centro",
            "campus",
            "matriz",
            "rua",
            "avenida",
            "av",
            "alameda",
            "praça",
            "largo",
        ]

        location_lower = self.normalized.lower()
        return (
            len(self.normalized.split()) >= 3  # Multiple words
            or any(term in location_lower for term in specific_terms)
            or bool(self.city and self.state)  # Has city and state
        )

    @property
    def is_brazilian(self) -> bool:
        """Check if location appears to be Brazilian."""
        brazilian_indicators = [
            # State codes
            "AC",
            "AL",
            "AP",
            "AM",
            "BA",
            "CE",
            "DF",
            "ES",
            "GO",
            "MA",
            "MT",
            "MS",
            "MG",
            "PA",
            "PB",
            "PR",
            "PE",
            "PI",
            "RJ",
            "RN",
            "RS",
            "RO",
            "RR",
            "SC",
            "SP",
            "SE",
            "TO",
            # Common city names
            "São Paulo",
            "Rio de Janeiro",
            "Brasília",
            "Belo Horizonte",
            "Salvador",
            "Fortaleza",
            "Recife",
            "Porto Alegre",
            "Curitiba",
            # Common terms
            "escritório",
            "prédio",
            "centro",
            "filial",
        ]

        location_text = self.normalized
        return any(indicator in location_text for indicator in brazilian_indicators)

    def to_display_format(self) -> str:
        """Format location for user display."""
        if self.city and self.state:
            base = f"{self.city}, {self.state}"
            # Add additional details if available
            remaining = self.normalized
            if self.city in remaining:
                remaining = remaining.replace(self.city, "").strip(", -")
            if self.state in remaining:
                remaining = remaining.replace(self.state, "").strip(", -")

            if remaining:
                return f"{remaining}, {base}"
            return base

        return self.normalized

    def to_dict(self) -> dict[str, str | None]:
        """Convert location to dictionary representation for serialization."""
        return {
            "raw": self.raw,
            "normalized": self.normalized,
            "city": self.city,
            "state": self.state,
            "url_slug": self.url_slug,
            "display_format": self.to_display_format(),
        }
