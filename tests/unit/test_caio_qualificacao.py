"""
test_caio_qualificacao.py - Testes da lógica de qualificação do Caio

Lógica puramente determinística (zero LLM). Pode rodar sem banco.
"""

import pytest
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))


@pytest.mark.unit
def test_caio_imports():
    from agents.caio import (
        verificar_se_e_rede,
        validar_site,
        _calcular_score,
        qualificar_lead,
        LeadInput,
    )

    assert callable(verificar_se_e_rede)
    assert callable(validar_site)
    assert callable(_calcular_score)
    assert callable(qualificar_lead)
    assert LeadInput.__name__ == "LeadInput"


@pytest.mark.unit
def test_verificar_rede_conhecida():
    from agents.caio import verificar_se_e_rede

    assert verificar_se_e_rede("Smart Fit Academia") is True
    assert verificar_se_e_rede("McDonald's") is True
    assert verificar_se_e_rede("Academia Corpo em Forma") is False


@pytest.mark.unit
def test_calcular_score_maximo():
    from agents.caio import _calcular_score

    lead = {
        "rating": 5.0,
        "reviews": 500,
        "possui_site": False,
        "fotos": 20,
    }
    score, motivos = _calcular_score(lead)
    assert score >= 90
    assert score <= 100
    assert motivos


@pytest.mark.unit
def test_calcular_score_minimo():
    from agents.caio import _calcular_score

    lead = {
        "rating": 0,
        "reviews": 0,
        "possui_site": False,
        "fotos": 0,
    }
    with patch("agents.caio.validar_site", return_value=(True, "Site valido")):
        lead["possui_site"] = True
        score, _ = _calcular_score(lead)
    assert score == 0


@pytest.mark.unit
def test_calcular_score_sem_site_bonus():
    from agents.caio import _calcular_score

    lead_sem_site = {"rating": 4.0, "reviews": 50, "possui_site": False, "fotos": 5}
    lead_com_site = {"rating": 4.0, "reviews": 50, "possui_site": True, "fotos": 5}
    with patch("agents.caio.validar_site", return_value=(True, "Site valido")):
        score_sem, _ = _calcular_score(lead_sem_site)
        score_com, _ = _calcular_score(lead_com_site)
    assert score_sem > score_com


@pytest.mark.unit
def test_agent_imports_smoke():
    """Todos os agentes do pipeline devem importar sem erro"""
    import agents.caio
    import agents.sdr_langgraph
    import agents.design_context
    import agents.designer_prd
    import agents.craft_rules
    import agents.unsplash_fetcher
    import agents.pexels_video
    import agents.section_editor
    import agents.memory
    import agents.pipeline_checkpoint
    import agents.token_tracker

    assert True


@pytest.mark.unit
def test_design_context_tiers():
    """design_context.py tem 3 variantes por nicho"""
    from agents.design_context import get_design_context

    direcao = get_design_context("academia", tier="PREMIUM")
    assert direcao is not None
    assert "tokens" in direcao
    assert "font_heading" in direcao
    assert "font_body" in direcao


@pytest.mark.unit
def test_pipeline_lock_unique():
    """Apenas pipeline_state deve controlar lock (PipelineQueueManager removido)"""
    import os.path as osp
    import sys

    # PipelineQueueManager foi deletado
    queue_path = osp.join(sys.path[0], "pipeline_queue_manager.py")
    assert not osp.exists(queue_path), "PipelineQueueManager ainda existe!"
