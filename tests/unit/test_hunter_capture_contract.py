import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from utils.agente1_hunter_v2 import (
    LeadQualificado,
    LeadRaw,
    _prioridade_captura,
    calcular_score,
)


def _lead(**overrides):
    dados = {
        "nome": "Barbearia Local",
        "cidade": "Curitiba",
        "segmento": "Barbearia",
        "telefone": "(41) 99999-9999",
        "rating": 4.9,
        "total_avaliacoes": 120,
        "endereco": "Rua Teste, 123 - Curitiba - PR",
    }
    dados.update(overrides)
    return LeadRaw(**dados)


def test_hunter_nao_qualifica_comercialmente():
    resultado = calcular_score(_lead(website="https://example.com"), "Curitiba")

    assert resultado["score"] == 0
    assert resultado["tier"] == "CAPTURADO"


def test_prioridade_hunter_usa_completude_sem_score_comercial():
    basico = LeadQualificado(
        lead=_lead(total_avaliacoes=5),
        score=0,
        tier="CAPTURADO",
        presenca_digital="ZERO_PRESENCA",
    )
    completo = LeadQualificado(
        lead=_lead(total_avaliacoes=120),
        score=0,
        tier="CAPTURADO",
        presenca_digital="ZERO_PRESENCA",
    )

    assert _prioridade_captura(completo) > _prioridade_captura(basico)
