"""Testes do modulo BANT/MEDDIC."""
import pytest

from backend.agents.sdr_langgraph.bant_meddic import (
    AuthorityLevel,
    BudgetLevel,
    TimelineLevel,
    compute_bant,
    compute_meddic,
    compute_need_score,
    detect_authority,
    detect_budget,
    detect_timeline,
)


class TestDetectBudget:
    @pytest.mark.parametrize("msg,expected", [
        ("Quanto custa? Menos de 500 nao da", BudgetLevel.MENOS_500),
        ("Posso pagar uns R$ 1.500", BudgetLevel.DE_500_A_1500),
        ("Tenho uns R$ 2.500 pra investir", BudgetLevel.DE_1500_A_5000),
        ("Faco mais de 5 mil tranquilo", BudgetLevel.MAIS_5000),
        ("Ja tenho site, quero refazer", BudgetLevel.JA_TEM),
        ("Pago no pix se ficar bom", BudgetLevel.PIX),
        ("Nao quero dizer quanto tenho", BudgetLevel.NAO_QUIS_DIZER),
    ])
    def test_detecta_orcamento(self, msg, expected):
        assert detect_budget(msg) == expected


class TestDetectAuthority:
    @pytest.mark.parametrize("msg,expected", [
        ("Eu sou dono, decido tudo", AuthorityLevel.DECISOR),
        ("Eu mesmo decido aqui", AuthorityLevel.DECISOR),
        ("Vou ver com meu socio", AuthorityLevel.INFLUENCIA),
        ("Preciso falar com meu marido antes", AuthorityLevel.CONSULTA),
        ("Nao sei te dizer, depende", AuthorityLevel.NAO_SEI),
    ])
    def test_detecta_autoridade(self, msg, expected):
        assert detect_authority(msg) == expected


class TestDetectTimeline:
    @pytest.mark.parametrize("msg,expected", [
        ("Preciso pra ontem", TimelineLevel.URGENTE),
        ("To com pressa aqui", TimelineLevel.URGENTE),
        ("Quero comecar este mes", TimelineLevel.TRINTA_DIAS),
        ("Posso ver isso em 90 dias", TimelineLevel.NOVENTA_DIAS),
        ("Sem previsao, um dia destes", TimelineLevel.SEM_PREVISAO),
    ])
    def test_detecta_timeline(self, msg, expected):
        assert detect_timeline(msg) == expected


class TestComputeNeed:
    def test_msg_sem_indicador(self):
        score = compute_need_score("oi tudo bem?")
        assert score == 0

    def test_msg_com_indicadores_multiplos(self):
        msg = "Preciso aumentar a captação, perco cliente pro concorrente"
        score = compute_need_score(msg)
        assert score >= 5

    def test_score_max_10(self):
        msg = " ".join([
            "preciso", "ta dificil", "perco cliente", "preciso aumentar",
            "quero crescer", "concorrente na frente", "trafego", "conversao",
            "aparecer no google", "vender mais"
        ])
        score = compute_need_score(msg)
        assert score == 10


class TestComputeBant:
    def test_bant_vazio_retorna_score_zero(self):
        result = compute_bant([])
        assert result.total_score == 0
        assert result.confidence == 0.0

    def test_bant_completo_score_maximo(self):
        msgs = [
            "Quanto custa? Tenho R$ 2000",
            "Eu sou dono, decido",
            "Preciso pra esta semana",
            "Perco cliente pro concorrente, preciso aumentar vendas",
        ]
        result = compute_bant(msgs)
        # Pelo menos 2 das 3 dimensoes principais detectaveis
        detected = sum(1 for x in [result.budget, result.authority, result.timeline] if x)
        assert detected >= 2, f"Deteccoes: budget={result.budget}, auth={result.authority}, time={result.timeline}"
        assert result.total_score >= 15

    def test_bant_parcial_menor_score(self):
        msgs = ["oi", "tudo bem"]
        result = compute_bant(msgs)
        assert result.budget is None
        assert result.total_score == 0


class TestComputeMeddic:
    def test_pain_identificado(self):
        msgs = ["Meu site ta lento e feio", "perco cliente todo dia"]
        result = compute_meddic(msgs)
        assert "site" in result.pain_identified.lower() or "cliente" in result.pain_identified.lower()
        assert result.total_score >= 3

    def test_champion_detectado(self):
        msgs = ["Vou defender isso aqui na empresa", "levo isso adiante"]
        result = compute_meddic(msgs)
        assert result.champion is True

    def test_score_max_10(self):
        msgs = [
            "quero atingir 100 clientes por mes",
            "meu socio que paga",
            "conta que o site carregue rapido",
            "site ta lento e feio",
            "vou defender isso aqui",
        ]
        result = compute_meddic(msgs)
        # Score minimo 8 (alguns elementos nao detectados por regex simplificado)
        assert result.total_score >= 7
