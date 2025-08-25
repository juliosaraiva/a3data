"""Pydantic models for request/response schemas."""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProcessingStatus(str, Enum):
    """Processing status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL_SUCCESS = "partial_success"


class IncidentData(BaseModel):
    """Core incident data model matching the required output format."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, use_enum_values=True)

    data_ocorrencia: str | None = Field(
        None,
        description="Data e hora do incidente no formato YYYY-MM-DD HH:MM",
        examples=["2025-08-23 14:00", "2025-12-25 09:30"],
    )

    local: str | None = Field(
        None,
        description="Local onde ocorreu o incidente",
        min_length=1,
        max_length=200,
        examples=["São Paulo", "Escritório de Brasília", "Data Center RJ"],
    )

    tipo_incidente: str | None = Field(
        None,
        description="Tipo ou categoria do incidente",
        min_length=1,
        max_length=150,
        examples=["Falha no servidor", "Problema de rede", "Erro no sistema"],
    )

    impacto: str | None = Field(
        None,
        description="Descrição do impacto causado pelo incidente",
        min_length=1,
        max_length=500,
        examples=["Sistema de faturamento indisponível por 2 horas"],
    )

    @field_validator("data_ocorrencia")
    @classmethod
    def validate_data_ocorrencia(cls, v: str | None) -> str | None:
        """Validate date format."""
        if v is None:
            return v

        # Check format YYYY-MM-DD HH:MM
        pattern = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$"
        if not re.match(pattern, v):
            raise ValueError("Data deve estar no formato YYYY-MM-DD HH:MM")

        # Try to parse to validate it's a real date
        try:
            datetime.strptime(v, "%Y-%m-%d %H:%M")
        except ValueError:
            raise ValueError("Data inválida")

        return v

    @field_validator("local", "tipo_incidente", "impacto")
    @classmethod
    def validate_not_empty(cls, v: str | None) -> str | None:
        """Ensure non-empty strings."""
        if v is not None and len(v.strip()) == 0:
            return None
        return v


class ExtractionRequest(BaseModel):
    """Request model for incident extraction."""

    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(
        ...,
        description="Texto descritivo do incidente de TI em português",
        min_length=10,
        max_length=5000,
        examples=[
            (
                "Ontem às 14h, no escritório de São Paulo, "
                "houve uma falha no servidor principal que afetou o sistema de faturamento por 2 horas."
            )
        ],
    )

    options: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Opções adicionais para processamento",
        examples=[{"usar_contexto_ampliado": True, "nivel_detalhe": "alto"}],
    )


class ExtractionResponse(BaseModel):
    """Response model for incident extraction."""

    model_config = ConfigDict(use_enum_values=True)

    status: ProcessingStatus = Field(..., description="Status do processamento")
    data: IncidentData | None = Field(None, description="Dados extraídos do incidente")
    message: str | None = Field(
        None,
        description="Mensagem informativa sobre o processamento",
        examples=["Extração realizada com sucesso", "Erro no processamento do texto"],
    )
    processing_time: float | None = Field(None, description="Tempo de processamento em segundos", ge=0.0)
    processing_details: dict[str, Any] | None = Field(default_factory=dict, description="Detalhes adicionais do processamento")
    errors: list[str] = Field(default_factory=list, description="Lista de erros encontrados durante o processamento")


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Status da aplicação")
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = Field(..., description="Versão da aplicação")

    components: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Status dos componentes")


class AgentState(BaseModel):
    """State model for LangGraph workflow."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Input data
    raw_text: str = Field(..., description="Texto original do incidente")
    options: Dict[str, Any] = Field(default_factory=dict, description="Opções de processamento")

    # Processing state
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    current_status: str = Field(default="inicio", description="Etapa atual do processamento")

    # Processed data
    preprocessed_text: str | None = Field(default=None, description="Texto após pré-processamento")
    extracted_data: IncidentData | None = Field(default=None, description="Dados extraídos")

    # Workflow control
    extraction_attempts: int = Field(default=0, description="Número de tentativas de extração")
    max_attempts: int = Field(default=3, description="Máximo de tentativas")

    # Error tracking
    errors: list[str] = Field(default_factory=list, description="Lista de erros")
    warnings: list[str] = Field(default_factory=list, description="Lista de avisos")

    # Metadata
    timestamp_inicio: datetime = Field(default_factory=datetime.now)
    processing_time: float | None = Field(default=None)

    # Agent-specific data
    supervisor_output: dict[str, Any] | None = Field(default_factory=dict)
    preprocessor_output: dict[str, Any] | None = Field(default_factory=dict)
    extractor_output: dict[str, Any] | None = Field(default_factory=dict)

    def add_error(self, erro: str) -> None:
        """Add an error to the state."""
        self.errors.append(erro)

    def add_warning(self, warning: str) -> None:
        """Add a warning to the state."""
        self.warnings.append(warning)

    def should_retry_extraction(self) -> bool:
        """Check if extraction should be retried."""
        return self.extraction_attempts < self.max_attempts

    def increment_extraction_attempts(self) -> None:
        """Increment extraction attempts counter."""
        self.extraction_attempts += 1


class ValidationError(BaseModel):
    """Validation error details."""

    field: str = Field(..., description="Campo com erro")
    message: str = Field(..., description="Mensagem de erro")
    value: Any | None = Field(None, description="Valor que causou o erro")


class ProcessingMetrics(BaseModel):
    """Processing metrics for monitoring."""

    total_requests: int = Field(default=0, description="Total de requisições processadas")
    successful_extractions: int = Field(default=0, description="Extrações bem-sucedidas")
    failed_extractions: int = Field(default=0, description="Extrações falhadas")
    average_processing_time: float = Field(default=0.0, description="Tempo médio de processamento")

    # Agent-specific metrics
    supervisor_calls: int = Field(default=0, description="Chamadas do agente supervisor")
    preprocessor_calls: int = Field(default=0, description="Chamadas do agente preprocessor")
    extractor_calls: int = Field(default=0, description="Chamadas do agente extractor")

    # Error metrics
    validation_errors: int = Field(default=0, description="Erros de validação")
    llm_errors: int = Field(default=0, description="Erros de LLM")
    timeout_errors: int = Field(default=0, description="Erros de timeout")

    last_updated: datetime = Field(default_factory=datetime.now)
