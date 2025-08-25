"""LLM configuration and settings for the incident extractor application."""

from enum import Enum
from typing import Any

from pydantic import BaseModel
from pydantic_settings import BaseSettings

from .config import get_settings


class LLMProvider(str, Enum):
    """Available LLM providers."""

    OLLAMA = "ollama"
    OPENAI = "openai"
    MOCK = "mock"  # For testing


class LLMConfig(BaseSettings):
    """LLM configuration model."""

    provider: LLMProvider
    model: str
    base_url: str | None = None
    api_key: str | None = None
    timeout: int = 60
    max_retries: int = 3
    temperature: float = 0.1  # Low temperature for consistent extraction
    max_tokens: int | None = None

    # Ollama-specific settings
    num_predict: int | None = None
    top_k: int | None = None
    top_p: float | None = None

    # Model-specific prompts and settings
    system_prompt: str | None = None
    extraction_prompt_template: str | None = None


class AgentLLMSettings(BaseModel):
    """LLM settings for different agents."""

    supervisor: LLMConfig
    preprocessor: LLMConfig
    extractor: LLMConfig


def get_llm_config() -> AgentLLMSettings:
    """Get LLM configuration for all agents."""
    settings = get_settings()

    # Supervisor agent configuration
    supervisor_config = LLMConfig(
        provider=LLMProvider.OLLAMA,
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        temperature=0.1,
        top_k=40,
        top_p=0.9,
        max_retries=settings.ollama_max_retries,
        system_prompt=(
            "Você é um agente supervisor que coordena a extração de informações de incidentes de TI. "
            "Sua função é orquestrar o fluxo de trabalho e garantir que o texto seja processado corretamente "
            "pelos agentes especializados. Responda sempre em português brasileiro."
        ),
        max_tokens=500,
    )

    # Preprocessor agent configuration
    preprocessor_config = LLMConfig(
        provider=LLMProvider.OLLAMA,
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        temperature=0.1,
        top_k=40,
        top_p=0.9,
        system_prompt=(
            "Você é um agente de pré-processamento de texto especializado em normalizar e limpar "
            "descrições de incidentes de TI em português. Sua função é padronizar o texto, corrigir "
            "erros óbvios e prepará-lo para extração de informações. Mantenha o contexto original "
            "e responda sempre em português brasileiro."
        ),
        max_tokens=2000,
    )

    # Extractor agent configuration
    extractor_config = LLMConfig(
        provider=LLMProvider.OLLAMA,
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        temperature=0.1,
        top_k=40,
        top_p=0.9,
        system_prompt=(
            "Você é um especialista em extração de informações de incidentes de TI. "
            "Sua função é extrair com precisão: data/hora de ocorrência, local do incidente, "
            "tipo de incidente e impacto. Sempre responda em formato JSON estruturado e "
            "em português brasileiro. Seja preciso e consistente."
        ),
        extraction_prompt_template=(
            "Extraia as seguintes informações do texto do incidente de TI:\n\n"
            "Texto: {text}\n\n"
            "Forneça a resposta APENAS em formato JSON com as seguintes chaves:\n"
            "- data_ocorrencia: data e hora no formato YYYY-MM-DD HH:MM\n"
            "- local: localização do incidente\n"
            "- tipo_incidente: categoria/tipo do incidente\n"
            "- impacto: descrição do impacto causado\n\n"
            "Se alguma informação não estiver disponível, use null.\n\n"
            "JSON:"
        ),
        max_tokens=1000,
    )

    return AgentLLMSettings(
        supervisor=supervisor_config,
        preprocessor=preprocessor_config,
        extractor=extractor_config,
    )


def get_fallback_llm_config() -> LLMConfig:
    """Get fallback LLM configuration (OpenAI)."""
    settings = get_settings()

    if not settings.openai_api_key:
        # Return mock LLM for testing
        return LLMConfig(
            provider=LLMProvider.MOCK,
            model="mock-model",
            temperature=0.1,
            max_tokens=1000,
            system_prompt="Mock LLM for testing purposes.",
        )

    return LLMConfig(
        provider=LLMProvider.OPENAI,
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        timeout=60,
        max_retries=3,
        temperature=0.1,
        max_tokens=1000,
        system_prompt=(
            "Você é um especialista em extração de informações de incidentes de TI. "
            "Extraia informações precisas e responda em português brasileiro."
        ),
    )


def get_model_parameters(config: LLMConfig) -> dict[str, Any]:
    """Get model parameters for LLM initialization."""
    params: dict[str, Any] = {
        "temperature": config.temperature,
        "timeout": config.timeout,
    }

    if config.max_tokens:
        params["max_tokens"] = config.max_tokens

    if config.provider == LLMProvider.OLLAMA:
        if config.base_url:
            params["base_url"] = config.base_url
        if config.num_predict:
            params["num_predict"] = config.num_predict
        if config.top_k:
            params["top_k"] = config.top_k
        if config.top_p:
            params["top_p"] = config.top_p

    elif config.provider == LLMProvider.OPENAI:
        if config.api_key:
            params["api_key"] = config.api_key

    return params


# Prompt templates for different extraction scenarios
EXTRACTION_PROMPTS = {
    "standard": (
        "Analise o seguinte texto sobre um incidente de TI e extraia as informações solicitadas:\n\n"
        "Texto: {text}\n\n"
        "Extraia as seguintes informações em formato JSON:\n"
        "- data_ocorrencia: Data e hora no formato YYYY-MM-DD HH:MM\n"
        "- local: Local onde ocorreu o incidente\n"
        "- tipo_incidente: Tipo/categoria do incidente\n"
        "- impacto: Descrição do impacto causado\n\n"
        "Resposta JSON:"
    ),
    "contextual": (
        "Você é um especialista em análise de incidentes de TI. Analise cuidadosamente "
        "o seguinte relato e extraia as informações estruturadas.\n\n"
        "Contexto: Este é um relato de incidente de TI que precisa ser processado para "
        "documentação e análise.\n\n"
        "Texto do incidente: {text}\n\n"
        "Instruções de extração:\n"
        "1. Identifique quando o incidente ocorreu (data_ocorrencia no formato YYYY-MM-DD HH:MM)\n"
        "2. Determine onde aconteceu (local)\n"
        "3. Classifique o tipo de incidente (tipo_incidente)\n"
        "4. Descreva o impacto causado (impacto)\n\n"
        "Forneça APENAS a resposta em JSON válido:\n"
    ),
    "retry": (
        "IMPORTANTE: A extração anterior falhou. Por favor, seja mais cuidadoso.\n\n"
        "Texto do incidente: {text}\n\n"
        "Extraia OBRIGATORIAMENTE as seguintes informações e retorne APENAS JSON válido:\n"
        "{{\n"
        '  "data_ocorrencia": "YYYY-MM-DD HH:MM ou null",\n'
        '  "local": "string ou null",\n'
        '  "tipo_incidente": "string ou null",\n'
        '  "impacto": "string ou null"\n'
        "}}\n\n"
        "JSON:"
    ),
}
