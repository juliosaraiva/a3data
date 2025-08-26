"""
Test data fixtures for incident extractor testing.

This module contains comprehensive test data scenarios covering various
incident types, date formats, complexity levels, and edge cases.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import pytest


class TestDataProvider:
    """Centralized test data provider for incident extraction scenarios."""

    @staticmethod
    def get_base_date() -> datetime:
        """Get the base date for test scenarios (current test date)."""
        return datetime(2025, 8, 26, 10, 0, 0)  # Monday

    @classmethod
    def get_relative_dates(cls) -> Dict[str, str]:
        """Get relative date mappings for test scenarios."""
        base_date = cls.get_base_date()
        yesterday = base_date - timedelta(days=1)
        last_friday = base_date - timedelta(days=3)  # Friday before Monday

        return {
            "hoje": base_date.strftime("%Y-%m-%d"),
            "ontem": yesterday.strftime("%Y-%m-%d"),
            "na_sexta_feira_passada": last_friday.strftime("%Y-%m-%d"),
        }


@pytest.fixture
def comprehensive_test_scenarios() -> List[Tuple[str, Dict[str, str]]]:
    """
    Comprehensive test scenarios with input text and expected outputs.

    Returns:
        List of tuples: (input_text, expected_response)
    """
    dates = TestDataProvider.get_relative_dates()

    return [
        # Simple date scenarios
        (
            "Sistema caiu ontem",
            {"data_ocorrencia": f"{dates['ontem']} 12:00", "local": None, "tipo_incidente": "sistema caiu", "impacto": None},
        ),
        (
            "Email não funcionou hoje às 14:30",
            {"data_ocorrencia": f"{dates['hoje']} 14:30", "local": None, "tipo_incidente": "email", "impacto": None},
        ),
        # Complex scenario - the main test case from the original issue
        (
            "Na sexta-feira passada por volta das 16:45, o sistema de vendas ficou indisponível por aproximadamente 30 minutos. Vários clientes relataram não conseguir finalizar suas compras online. A equipe de TI identificou o problema como uma falha no servidor de banco de dados principal.",
            {
                "data_ocorrencia": f"{dates['na_sexta_feira_passada']} 16:45",
                "local": "sistema de vendas",
                "tipo_incidente": "falha no servidor de banco de dados",
                "impacto": "vários clientes não conseguir finalizar suas compras online",
            },
        ),
        # Oracle database scenario
        (
            "Na sexta-feira passada por volta das 16:45, o banco de dados Oracle da aplicação de RH apresentou lentidão extrema. Isso afetou mais de 200 usuários que não conseguiam fazer login no sistema, impactando o fechamento da folha de pagamento.",
            {
                "data_ocorrencia": f"{dates['na_sexta_feira_passada']} 16:45",
                "local": "banco de dados Oracle da aplicação de RH",
                "tipo_incidente": "lentidão",
                "impacto": "mais de 200 usuários que não conseguiam fazer login no sistema, impactando o fechamento da folha de pagamento",
            },
        ),
        # Email system scenario
        (
            "Ontem o email não funcionou das 09:00 às 12:00",
            {"data_ocorrencia": f"{dates['ontem']} 09:00", "local": None, "tipo_incidente": "email", "impacto": None},
        ),
        # Server failure scenario
        (
            "Hoje às 15:45 o servidor web principal parou de responder. Os usuários não conseguiram acessar o portal por 2 horas.",
            {
                "data_ocorrencia": f"{dates['hoje']} 15:45",
                "local": "servidor web principal",
                "tipo_incidente": "servidor parou de responder",
                "impacto": "usuários não conseguiram acessar o portal por 2 horas",
            },
        ),
        # Network issue
        (
            "Ontem pela manhã houve problemas de conectividade na rede do escritório de São Paulo, afetando todos os sistemas internos.",
            {
                "data_ocorrencia": f"{dates['ontem']} 09:00",
                "local": "escritório de São Paulo",
                "tipo_incidente": "problemas de conectividade na rede",
                "impacto": "afetando todos os sistemas internos",
            },
        ),
    ]


@pytest.fixture
def date_parsing_scenarios() -> List[Tuple[str, str]]:
    """
    Specific date parsing test scenarios.

    Returns:
        List of tuples: (input_text, expected_date)
    """
    dates = TestDataProvider.get_relative_dates()

    return [
        ("Sistema falhou hoje às 14:30", f"{dates['hoje']} 14:30"),
        ("Problema ontem às 16:45", f"{dates['ontem']} 16:45"),
        ("Na sexta-feira passada por volta das 16:45", f"{dates['na_sexta_feira_passada']} 16:45"),
        ("Hoje de manhã às 08:00", f"{dates['hoje']} 08:00"),
        ("Ontem à noite às 23:15", f"{dates['ontem']} 23:15"),
    ]


@pytest.fixture
def edge_case_scenarios() -> List[Tuple[str, Dict[str, str]]]:
    """
    Edge case scenarios for testing robustness.

    Returns:
        List of tuples: (input_text, expected_response)
    """
    return [
        # Minimal information
        (
            "Sistema com problema",
            {"data_ocorrencia": None, "local": None, "tipo_incidente": "sistema com problema", "impacto": None},
        ),
        # Very detailed scenario
        (
            "Na segunda-feira passada, dia 21 de agosto de 2025, às 14:30, o data center principal localizado em São Paulo apresentou uma falha crítica no sistema de refrigeração que causou o desligamento automático de 15 servidores físicos, resultando na indisponibilidade completa dos sistemas ERP, CRM e portal de clientes por aproximadamente 4 horas, afetando mais de 1000 usuários internos e externos.",
            {
                "data_ocorrencia": "2025-08-21 14:30",
                "local": "data center principal localizado em São Paulo",
                "tipo_incidente": "falha crítica no sistema de refrigeração",
                "impacto": "indisponibilidade completa dos sistemas ERP, CRM e portal de clientes por aproximadamente 4 horas, afetando mais de 1000 usuários internos e externos",
            },
        ),
        # Multiple systems mentioned
        (
            "Hoje às 10:00 tanto o sistema financeiro quanto o de RH apresentaram lentidão devido a problemas no banco de dados compartilhado.",
            {
                "data_ocorrencia": f"{TestDataProvider.get_relative_dates()['hoje']} 10:00",
                "local": "banco de dados compartilhado",
                "tipo_incidente": "lentidão",
                "impacto": "sistema financeiro e de RH apresentaram lentidão",
            },
        ),
    ]


@pytest.fixture
def error_scenarios() -> List[Tuple[str, int, str]]:
    """
    Error scenarios for testing error handling.

    Returns:
        List of tuples: (input_text, expected_status_code, expected_error_type)
    """
    return [
        # Text too short
        ("Sistema", 422, "validation_error"),
        # Empty text
        ("", 422, "validation_error"),
        # Text too long (over 5000 characters)
        ("X" * 5001, 422, "validation_error"),
        # Non-Portuguese text (should still process but might not extract well)
        ("System failed yesterday at 3 PM", 200, None),
        # Special characters and formatting
        ("Sistema falhou @#$%^&*() ontem", 200, None),
    ]


@pytest.fixture
def performance_scenarios() -> List[Tuple[str, float]]:
    """
    Performance test scenarios with maximum expected response times.

    Returns:
        List of tuples: (input_text, max_response_time_seconds)
    """
    return [
        # Simple scenario should be fast
        ("Sistema caiu ontem", 15.0),
        # Complex scenario should still be reasonable
        (
            "Na sexta-feira passada por volta das 16:45, o sistema de vendas ficou indisponível por aproximadamente 30 minutos. Vários clientes relataram não conseguir finalizar suas compras online. A equipe de TI identificou o problema como uma falha no servidor de banco de dados principal.",
            30.0,
        ),
        # Very long text should not timeout
        ("Esta é uma descrição muito longa de um incidente que aconteceu " * 50 + " ontem às 14:00 no servidor principal.", 45.0),
    ]
