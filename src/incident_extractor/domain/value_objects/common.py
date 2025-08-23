"""Additional value objects for incident processing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import Any

from incident_extractor.core.exceptions.domain import DomainError


class InvalidSeverityError(DomainError):
    """Exception raised when incident severity is invalid."""

    def __init__(self, message: str):
        super().__init__(message, "INVALID_SEVERITY")


class IncidentSeverity(Enum):
    """Enumeration of incident severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"

    @classmethod
    def from_string(cls, severity_str: str) -> IncidentSeverity:
        """Create severity from string with normalization.

        Args:
            severity_str: String representation of severity

        Returns:
            IncidentSeverity instance

        Raises:
            InvalidSeverityError: If severity is invalid
        """
        if not severity_str or not severity_str.strip():
            raise InvalidSeverityError("Severity cannot be empty")

        severity_str = severity_str.strip().lower()

        # Map common variations to standard values
        severity_mapping = {
            # Portuguese variations
            "crítico": cls.CRITICAL,
            "critico": cls.CRITICAL,
            "crítica": cls.CRITICAL,
            "critica": cls.CRITICAL,
            "alto": cls.HIGH,
            "alta": cls.HIGH,
            "grave": cls.HIGH,
            "médio": cls.MEDIUM,
            "medio": cls.MEDIUM,
            "média": cls.MEDIUM,
            "media": cls.MEDIUM,
            "moderado": cls.MEDIUM,
            "moderada": cls.MEDIUM,
            "baixo": cls.LOW,
            "baixa": cls.LOW,
            "menor": cls.LOW,
            "pequeno": cls.LOW,
            "pequena": cls.LOW,
            "informativo": cls.INFORMATIONAL,
            "informativa": cls.INFORMATIONAL,
            "informacao": cls.INFORMATIONAL,
            # English variations
            "critical": cls.CRITICAL,
            "crit": cls.CRITICAL,
            "urgent": cls.CRITICAL,
            "high": cls.HIGH,
            "major": cls.HIGH,
            "medium": cls.MEDIUM,
            "moderate": cls.MEDIUM,
            "med": cls.MEDIUM,
            "low": cls.LOW,
            "minor": cls.LOW,
            "informational": cls.INFORMATIONAL,
            # Numeric levels
            "1": cls.CRITICAL,
            "2": cls.HIGH,
            "3": cls.MEDIUM,
            "4": cls.LOW,
            "5": cls.INFORMATIONAL,
        }

        if severity_str in severity_mapping:
            return severity_mapping[severity_str]

        # Try exact match with enum values
        for severity in cls:
            if severity.value == severity_str:
                return severity

        raise InvalidSeverityError(f"Invalid severity: {severity_str}")

    def to_numeric(self) -> int:
        """Convert severity to numeric value (1=critical, 5=informational)."""
        mapping = {
            self.CRITICAL: 1,
            self.HIGH: 2,
            self.MEDIUM: 3,
            self.LOW: 4,
            self.INFORMATIONAL: 5,
        }
        return mapping[self]

    def to_brazilian_portuguese(self) -> str:
        """Convert to Brazilian Portuguese representation."""
        mapping = {
            self.CRITICAL: "Crítico",
            self.HIGH: "Alto",
            self.MEDIUM: "Médio",
            self.LOW: "Baixo",
            self.INFORMATIONAL: "Informativo",
        }
        return mapping[self]


@dataclass(frozen=True)
class IncidentType:
    """Value object for incident type/category."""

    value: str
    normalized: str = ""
    category: str | None = None
    subcategory: str | None = None

    def __post_init__(self):
        """Validate and normalize the incident type."""
        if not self.value or not self.value.strip():
            raise DomainError("Incident type cannot be empty", "EMPTY_INCIDENT_TYPE")

        if len(self.value) > 200:
            raise DomainError("Incident type cannot be longer than 200 characters", "INCIDENT_TYPE_TOO_LONG")

        # Normalize the type
        normalized = self._normalize_type(self.value)
        object.__setattr__(self, "normalized", normalized)

        # Extract category and subcategory if possible
        category, subcategory = self._extract_type_parts(normalized)
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "subcategory", subcategory)

    def _normalize_type(self, type_str: str) -> str:
        """Normalize incident type string."""
        normalized = type_str.strip()

        # Common incident type mappings (Portuguese -> normalized)
        type_mappings = {
            # Infrastructure
            "falha de servidor": "Falha de Servidor",
            "problema de rede": "Problema de Rede",
            "queda de sistema": "Queda de Sistema",
            "indisponibilidade": "Indisponibilidade",
            "lentidão": "Lentidão",
            "timeout": "Timeout",
            # Security
            "vazamento de dados": "Vazamento de Dados",
            "acesso não autorizado": "Acesso Não Autorizado",
            "tentativa de invasão": "Tentativa de Invasão",
            # Business
            "erro de processamento": "Erro de Processamento",
            "falha de integração": "Falha de Integração",
            "problema de sincronização": "Problema de Sincronização",
            # Human error
            "erro humano": "Erro Humano",
            "configuração incorreta": "Configuração Incorreta",
            "erro de operação": "Erro de Operação",
        }

        normalized_lower = normalized.lower()
        for original, replacement in type_mappings.items():
            if original in normalized_lower:
                normalized = normalized_lower.replace(original, replacement)
                break

        # Capitalize first letter of each word
        return normalized.title()

    def _extract_type_parts(self, type_str: str) -> tuple[str | None, str | None]:
        """Extract category and subcategory from type string."""
        # Define main categories
        categories = {
            "infraestrutura": ["servidor", "rede", "sistema", "hardware", "software"],
            "segurança": ["dados", "acesso", "invasão", "vulnerabilidade", "autenticação"],
            "negócio": ["processamento", "integração", "sincronização", "transação"],
            "operacional": ["configuração", "operação", "manutenção", "backup"],
        }

        type_lower = type_str.lower()

        for category, keywords in categories.items():
            if any(keyword in type_lower for keyword in keywords):
                # Use the original type as subcategory
                return category.title(), type_str

        # If no category found, use the type itself as category
        return type_str, None

    def to_dict(self) -> dict[str, str | None]:
        """Convert to dictionary representation."""
        return {
            "raw": self.value,
            "normalized": self.normalized,
            "category": self.category,
            "subcategory": self.subcategory,
        }


@dataclass(frozen=True)
class ImpactAssessment:
    """Value object for incident impact assessment."""

    description: str
    affected_users: int | None = None
    duration: timedelta | None = None
    business_impact: str | None = None
    financial_impact: float | None = None

    def __post_init__(self):
        """Validate impact assessment values."""
        if not self.description or not self.description.strip():
            raise DomainError("Impact description cannot be empty", "EMPTY_IMPACT_DESCRIPTION")

        if len(self.description) > 1000:
            raise DomainError("Impact description cannot be longer than 1000 characters", "IMPACT_DESCRIPTION_TOO_LONG")

        if self.affected_users is not None and self.affected_users < 0:
            raise DomainError("Affected users cannot be negative", "INVALID_AFFECTED_USERS")

        if self.financial_impact is not None and self.financial_impact < 0:
            raise DomainError("Financial impact cannot be negative", "INVALID_FINANCIAL_IMPACT")

    @classmethod
    def from_description(cls, description: str) -> ImpactAssessment:
        """Create impact assessment from description with extraction."""
        if not description or not description.strip():
            raise DomainError("Impact description cannot be empty", "EMPTY_IMPACT_DESCRIPTION")

        description = description.strip()

        # Try to extract duration from description
        duration = cls._extract_duration(description)

        # Try to extract affected users from description
        affected_users = cls._extract_affected_users(description)

        # Extract business impact keywords
        business_impact = cls._extract_business_impact(description)

        return cls(
            description=description,
            duration=duration,
            affected_users=affected_users,
            business_impact=business_impact,
        )

    @staticmethod
    def _extract_duration(description: str) -> timedelta | None:
        """Extract duration from impact description."""
        description_lower = description.lower()

        # Look for time patterns
        time_patterns = [
            (r"(\d+)\s*horas?", "hours"),
            (r"(\d+)\s*minutos?", "minutes"),
            (r"(\d+)\s*dias?", "days"),
            (r"(\d+)h", "hours"),
            (r"(\d+)min", "minutes"),
            (r"(\d+)d", "days"),
        ]

        for pattern, unit in time_patterns:
            match = re.search(pattern, description_lower)
            if match:
                value = int(match.group(1))
                if unit == "hours":
                    return timedelta(hours=value)
                elif unit == "minutes":
                    return timedelta(minutes=value)
                elif unit == "days":
                    return timedelta(days=value)

        return None

    @staticmethod
    def _extract_affected_users(description: str) -> int | None:
        """Extract affected users count from description."""
        description_lower = description.lower()

        # Look for user count patterns
        user_patterns = [
            r"(\d+)\s*usuários?",
            r"(\d+)\s*users?",
            r"(\d+)\s*pessoas?",
            r"(\d+)\s*clientes?",
        ]

        for pattern in user_patterns:
            match = re.search(pattern, description_lower)
            if match:
                return int(match.group(1))

        return None

    @staticmethod
    def _extract_business_impact(description: str) -> str | None:
        """Extract business impact classification from description."""
        description_lower = description.lower()

        # Business impact keywords
        impact_keywords = {
            "crítico": "critical",
            "grave": "severe",
            "significativo": "significant",
            "moderado": "moderate",
            "menor": "minor",
            "vendas": "sales_impact",
            "receita": "revenue_impact",
            "produção": "production_impact",
            "atendimento": "service_impact",
        }

        for keyword, impact_type in impact_keywords.items():
            if keyword in description_lower:
                return impact_type

        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "description": self.description,
            "affected_users": self.affected_users,
            "duration_minutes": self.duration.total_seconds() / 60 if self.duration else None,
            "business_impact": self.business_impact,
            "financial_impact": self.financial_impact,
        }

    @property
    def severity_indicator(self) -> str:
        """Get severity indicator based on impact metrics."""
        if self.affected_users and self.affected_users > 1000:
            return "high"
        elif self.duration and self.duration.total_seconds() > 3600:  # > 1 hour
            return "high"
        elif self.financial_impact and self.financial_impact > 10000:
            return "high"
        elif self.business_impact in ["critical", "severe"]:
            return "high"
        elif self.affected_users and self.affected_users > 100:
            return "medium"
        elif self.duration and self.duration.total_seconds() > 600:  # > 10 minutes
            return "medium"
        else:
            return "low"
