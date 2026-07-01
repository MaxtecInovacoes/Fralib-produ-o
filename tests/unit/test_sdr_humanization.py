"""Testes do módulo de humanização do SDR."""
import pytest

from backend.agents.sdr_langgraph.humanization import (
    ABERTURAS,
    CLOSINGS_NATURAIS,
    calc_humanize_delay,
    detect_msg_duplicate,
    is_robot_like,
    msg_hash,
)


class TestABERTURAS:
    def test_lead_novo_tem_minimo_3_variacoes(self):
        assert len(ABERTURAS["lead_novo"]) >= 3

    def test_lead_retorno_tem_minimo_3_variacoes(self):
        assert len(ABERTURAS["lead_retorno"]) >= 3


class TestClosings:
    def test_tem_closings_naturais(self):
        assert len(CLOSINGS_NATURAIS) >= 5


class TestCalcHumanizeDelay:
    def test_primeira_msg_cold_tem_delay_2_4s(self):
        d = calc_humanize_delay(
            last_response_time_min=None,
            is_objetou=False,
            is_first_msg=True,
            is_quente=False,
        )
        assert 2.0 <= d.seconds <= 4.0

    def test_pos_objecao_tem_delay_3_5s(self):
        d = calc_humanize_delay(
            last_response_time_min=None,
            is_objetou=True,
            is_first_msg=False,
            is_quente=False,
        )
        assert 3.0 <= d.seconds <= 5.0

    def test_lead_quente_tem_delay_curto(self):
        d = calc_humanize_delay(
            last_response_time_min=1,
            is_objetou=False,
            is_first_msg=False,
            is_quente=True,
        )
        assert 1.0 <= d.seconds <= 2.0

    def test_lead_frio_tem_delay_longo(self):
        d = calc_humanize_delay(
            last_response_time_min=120,
            is_objetou=False,
            is_first_msg=False,
            is_quente=False,
        )
        assert 60.0 <= d.seconds <= 180.0


class TestMsgDuplicate:
    def test_sem_historico_nao_detecta(self):
        assert detect_msg_duplicate("oi tudo bem", []) is False

    def test_msg_identica_detectada(self):
        prev = ["oi tudo bem? como posso ajudar?"]
        assert detect_msg_duplicate("Oi tudo bem? Como posso ajudar?", prev) is True

    def test_msg_muito_diferente_nao_detectada(self):
        prev = ["Oi tudo bem? Como posso ajudar?"]
        assert detect_msg_duplicate("Vi que vocês são referência em crossfit na região.", prev) is False

    def test_msg_quase_igual_detectada(self):
        prev = ["Oi! Tudo bem com você? Como posso te ajudar?"]
        new = "Oi tudo bem, como posso te ajudar"
        assert detect_msg_duplicate(new, prev) is True


class TestMsgHash:
    def test_mesma_msg_mesmo_hash(self):
        assert msg_hash("Oi tudo bem") == msg_hash("oi tudo bem")

    def test_msgs_diferentes_hash_diferente(self):
        assert msg_hash("Oi tudo bem") != msg_hash("Tudo ótimo")

    def test_hash_tem_16_chars(self):
        assert len(msg_hash("teste")) == 16


class TestIsRobotLike:
    @pytest.mark.parametrize("msg", [
        "Excelente pergunta! Temos a solução ideal.",
        "Poderia me informar seu telefone?",
        "Agradeço o contato!",
        "Fico à disposição!",
        "Vamos lá!!! 💪🔥🚀",
    ])
    def test_detecta_sinais_de_robo(self, msg):
        assert is_robot_like(msg) is True

    @pytest.mark.parametrize("msg", [
        "Vi que vocês são referência em CrossFit na região.",
        "Faz sentido o que você falou.",
        "Massa, me conta mais sobre o movimento.",
        "Oi, tudo certo?",
    ])
    def test_msg_naturais_passam(self, msg):
        assert is_robot_like(msg) is False
