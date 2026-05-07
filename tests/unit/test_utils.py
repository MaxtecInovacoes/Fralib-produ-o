"""
test_utils.py - Testes unitários para utilitários diversos

Testa funções dos módulos em backend/utils/.
"""
import pytest
import sys
import os

# Adicionar backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from utils.validation_layer import validar_prd, CORES_PROIBIDAS


# ===== TESTES DE VALIDAÇÃO DE PRD =====

@pytest.mark.unit
def test_validar_prd_completo_valido():
    """Testa PRD completo e válido."""
    prd = {
        "cores": {
            "primaria": "#FF5733",
            "secundaria": "#33FF57"
        },
        "dark_mode": True,
        "headline": "Agência de Marketing Digital em São Paulo - Resultados Garantidos",
        "cidade": "São Paulo"
    }

    valido, erros = validar_prd(prd)

    assert valido is True
    assert len(erros) == 0


@pytest.mark.unit
def test_validar_prd_sem_cores():
    """Testa PRD sem cores definidas."""
    prd = {
        "dark_mode": True,
        "headline": "Agência de Marketing Digital em São Paulo",
        "cidade": "São Paulo"
    }

    valido, erros = validar_prd(prd)

    assert valido is False
    assert "PRD sem cores definidas" in erros


@pytest.mark.unit
def test_validar_prd_cor_proibida():
    """Testa PRD com cor genérica proibida."""
    prd = {
        "cores": {
            "primaria": "#3b82f6"  # Azul genérico proibido
        },
        "dark_mode": True,
        "headline": "Agência de Marketing Digital em São Paulo",
        "cidade": "São Paulo"
    }

    valido, erros = validar_prd(prd)

    assert valido is False
    assert any("Cor generica detectada" in erro for erro in erros)
    assert any("#3b82f6" in erro for erro in erros)


@pytest.mark.unit
def test_validar_prd_sem_dark_mode():
    """Testa PRD sem dark mode."""
    prd = {
        "cores": {
            "primaria": "#FF5733"
        },
        "headline": "Agência de Marketing Digital em São Paulo",
        "cidade": "São Paulo"
    }

    valido, erros = validar_prd(prd)

    assert valido is False
    assert any("Dark mode" in erro for erro in erros)


@pytest.mark.unit
def test_validar_prd_headline_vazia():
    """Testa PRD com headline vazia."""
    prd = {
        "cores": {
            "primaria": "#FF5733"
        },
        "dark_mode": True,
        "headline": "",
        "cidade": "São Paulo"
    }

    valido, erros = validar_prd(prd)

    assert valido is False
    assert "Headline vazia" in erros


@pytest.mark.unit
def test_validar_prd_headline_curta():
    """Testa PRD com headline muito curta."""
    prd = {
        "cores": {
            "primaria": "#FF5733"
        },
        "dark_mode": True,
        "headline": "Agência Digital",  # Menos de 30 caracteres
        "cidade": "São Paulo"
    }

    valido, erros = validar_prd(prd)

    assert valido is False
    assert any("Headline muito curta" in erro for erro in erros)


@pytest.mark.unit
def test_validar_prd_headline_sem_cidade():
    """Testa PRD com headline sem mencionar a cidade."""
    prd = {
        "cores": {
            "primaria": "#FF5733"
        },
        "dark_mode": True,
        "headline": "Agência de Marketing Digital - Resultados Garantidos",
        "cidade": "São Paulo"
    }

    valido, erros = validar_prd(prd)

    assert valido is False
    assert any("Headline sem cidade" in erro for erro in erros)


@pytest.mark.unit
def test_validar_prd_multiplos_erros():
    """Testa PRD com múltiplos erros."""
    prd = {
        "cores": {
            "primaria": "#3b82f6"  # Cor proibida
        },
        "dark_mode": False,  # Sem dark mode
        "headline": "Curto",  # Headline curta
        "cidade": "São Paulo"
    }

    valido, erros = validar_prd(prd)

    assert valido is False
    assert len(erros) >= 3
    assert any("Cor generica" in erro for erro in erros)
    assert any("Dark mode" in erro for erro in erros)
    assert any("Headline muito curta" in erro for erro in erros)


@pytest.mark.unit
def test_validar_prd_cores_case_insensitive():
    """Testa que validação de cores é case-insensitive."""
    prd = {
        "cores": {
            "primaria": "#3B82F6"  # Maiúscula, mas ainda proibida
        },
        "dark_mode": True,
        "headline": "Agência de Marketing Digital em São Paulo",
        "cidade": "São Paulo"
    }

    valido, erros = validar_prd(prd)

    assert valido is False
    assert any("Cor generica detectada" in erro for erro in erros)


@pytest.mark.unit
def test_validar_prd_cidade_case_insensitive():
    """Testa que validação de cidade na headline é case-insensitive."""
    prd = {
        "cores": {
            "primaria": "#FF5733"
        },
        "dark_mode": True,
        "headline": "Agência de Marketing Digital em são paulo - Resultados",
        "cidade": "São Paulo"
    }

    valido, erros = validar_prd(prd)

    assert valido is True
    assert len(erros) == 0


@pytest.mark.unit
def test_cores_proibidas_lista():
    """Testa que a lista de cores proibidas está definida."""
    assert CORES_PROIBIDAS is not None
    assert len(CORES_PROIBIDAS) > 0
    assert isinstance(CORES_PROIBIDAS, list)
    assert all(isinstance(cor, str) for cor in CORES_PROIBIDAS)
    assert all(cor.startswith('#') for cor in CORES_PROIBIDAS)


@pytest.mark.unit
def test_validar_prd_sem_cidade():
    """Testa PRD sem cidade definida."""
    prd = {
        "cores": {
            "primaria": "#FF5733"
        },
        "dark_mode": True,
        "headline": "Agência de Marketing Digital - Resultados Garantidos"
    }

    valido, erros = validar_prd(prd)

    # Sem cidade, não deve validar se está na headline
    assert valido is True
    assert len(erros) == 0


@pytest.mark.unit
def test_validar_prd_vazio():
    """Testa PRD vazio."""
    prd = {}

    valido, erros = validar_prd(prd)

    assert valido is False
    assert len(erros) >= 3  # Sem cores, sem dark mode, headline vazia
