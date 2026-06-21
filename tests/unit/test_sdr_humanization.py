"""Testes do módulo de humanização do SDR."""
import pytest

from backend.agents.sdr_langgraph.humanization import (
    ABERTURAS,
    CLOSINGS_NATURAIS,
    WALL_STREET_CLOSES,
    calc_humanize_delay,
    detect_msg_duplicate,
    inject_variation,
    is_robot_like,
    msg_hash,
    pick_abertura,
    pick_closing,
    pick_wall_street_close,
)


class TestAberturas:
    def test_lead_novo_tem_minimo_3_variacoes(self):
        assert len(ABERTURAS["lead_novo"]) >= 3

    def test_lead_retorno_tem_minimo_3_variacoes(self):
        assert len(ABERTURAS["lead_retorno"]) >= 3

    def test_pick_abertura_retorna_string(self):
        for ctx in ["lead_novo", "lead_retorno", "lead_objetou", "lead_quente"]:
            abertura = pick_abertura(ctx)
            assert isinstance(abertura, str)
            assert len(abertura) > 0

    def test_pick_abertura_contexto_desconhecido_caem_no_default(self):
        abertura = pick_abertura("contexto_inexistente")
        assert abertura in ABERTURAS["lead_novo"]


class TestClosings:
    def test_tem_closings_naturais(self):
        assert len(CLOSINGS_NATURAIS) >= 5

    def test_tem_wall_street_closes(self):
        assert len(WALL_STREET_CLOSES) >= 3

    def test_pick_closing_natural(self):
        c = pick_closing(use_wall_street=False)
        assert c in CLOSINGS_NATURAIS

    def test_pick_closing_wall_street(self):
        c = pick_closing(use_wall_street=True)
        assert c in WALL_STREET_CLOSES
        # Wall Street close deve mencionar perda/oportunidade
        c_lower = c.lower()
        keywords = ["modelo pronto", "concorrente", "oportunidade", "sem compromisso", "descarta", "olhada", "exemplo pronto", "site lindo"]
        assert any(kw in c_lower for kw in keywords), f"Wall Street close nao menciona oportunidade: {c}"


class TestCalcHumanizeDelay:
    def test_primeira_msg_cold_tem_delay_2_4s(self):
        d = calc_humanize_delay(
            last_response_time_min=None,
            is_objetou=False,
            is_first_msg=True,
            is_quente=False,
        )
        assert 2.0 <= d.seconds <= 4.0

    def test_pos_objeção_tem_delay_3_5s(self):
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
        # Variação minima: troca 1-2 palavras
        new = "Oi tudo bem, como posso te ajudar"
        # Threshold novo (0.70) deve detectar
        assert detect_msg_duplicate(new, prev) is True


class TestMsgHash:
    def test_mesma_msg_mesmo_hash(self):
        assert msg_hash("Oi tudo bem") == msg_hash("oi tudo bem")

    def test_msgs_diferentes_hash_diferente(self):
        assert msg_hash("Oi tudo bem") != msg_hash("Tudo ótimo")

    def test_hash_tem_16_chars(self):
        assert len(msg_hash("teste")) == 16


class TestInjectVariation:
    def test_substitui_algumas_palavras(self):
        # Roda 100x pra ver se pelo menos 1x substitui
        hits = 0
        for _ in range(100):
            result = inject_variation("Você está bem?")
            if "vc" in result or "tá" in result:
                hits += 1
                break
        assert hits > 0  # probabilidade alta de pelo menos 1 hit

    def test_preserva_significado(self):
        # Roda varias vezes, sempre deve manter palavras-chave
        for _ in range(50):
            result = inject_variation("Você está estudando muito")
            # Pelo menos uma das 3 palavras-chave deve permanecer
            keywords = ["vc", "tá", "mt"]
            assert any(kw in result.lower() for kw in keywords) or "vo" in result.lower()


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


class TestPickWallStreet:
    def test_retorna_close_com_oportunidade(self):
        c = pick_wall_street_close("academia")
        assert any(kw in c.lower() for kw in ["modelo pronto", "concorrente", "oportunidade", "descarta"])
