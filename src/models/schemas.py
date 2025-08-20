"""Pydantic models for request and response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class IncidentRequest(BaseModel):
    """Request model for incident extraction."""

    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Description of the incident to process",
        examples=[
            "Ontem às 14h, no escritório de São Paulo, houve uma falha no servidor principal que afetou o sistema de faturamento por 2 horas."
        ],
    )

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate and clean the description field."""
        if not v or not v.strip():
            raise ValueError("Description cannot be empty")
        return v.strip()


class IncidentResponse(BaseModel):
    """Response model for extracted incident information."""

    data_ocorrencia: Optional[str] = Field(
        None,
        description="Date and time of the incident (ISO format if available)",
        examples=["2025-08-12 14:00"],
    )
    local: Optional[str] = Field(
        None,
        description="Location where the incident occurred",
        examples=["São Paulo"],
    )
    tipo_incidente: Optional[str] = Field(
        None,
        description="Type or category of the incident",
        examples=["Falha no servidor"],
    )
    impacto: Optional[str] = Field(
        None,
        description="Brief description of the impact caused",
        examples=["Sistema de faturamento indisponível por 2 horas"],
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "data_ocorrencia": "2025-08-12 14:00",
                "local": "São Paulo",
                "tipo_incidente": "Falha no servidor",
                "impacto": "Sistema de faturamento indisponível por 2 horas",
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "error": "Processing failed",
                "detail": "Unable to connect to LLM service",
                "timestamp": "2025-08-20T19:00:00",
            }
        }


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Health check timestamp")
    version: str = Field(..., description="API version")
    llm_provider: str = Field(..., description="Configured LLM provider")
    llm_available: bool = Field(..., description="Whether LLM service is available")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-08-20T19:00:00",
                "version": "1.0.0",
                "llm_provider": "ollama",
                "llm_available": True,
            }
        }
