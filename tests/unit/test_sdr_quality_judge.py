"""Testes para quality_judge.py.

Testa:
- evaluate_reply() com enable_llm=False (heuristico)
- _heuristic_evaluate()
- Score 1-5 e should_send
- Edge cases
"""
import pytest
from unittest.mock import patch


class TestHeuristicEvaluate:
    """Testa avaliacao heuristica (sem LLM)."""

    def test_resposta_vazia_score_zero(self):
        from backend.agents.sdr_langgraph.quality_judge import _heuristic_evaluate

        result = _heuristic_evaluate("", "", min_score=3)
        assert result.score == 0
        assert result.should_send is False

    def test_multiplas_perguntas_reduz_score(self):
        from backend.agents.sdr_langgraph.quality_judge import _heuristic_evaluate

        reply = "Qual seu nome? Quando nasceu? Onde mora?"
        result = _heuristic_evaluate("msg", reply, min_score=3)
        assert "multiplas_perguntas" in result.issues

    def test_muitos_emojis_reduz_score(self):
        from backend.agents.sdr_langgraph.quality_judge import _heuristic_evaluate

        reply = "Oi! Tudo bem? emoji emoji emoji"
        # Simular multiplos emojis
        reply_with_emojis = reply + " " + "".join([chr(0x2700 + i) for i in range(5)])
        result = _heuristic_evaluate("msg", reply_with_emojis, min_score=3)
        assert "muitos_emojis" in result.issues

    def test_mensagem_longa_reduz_score(self):
        from backend.agents.sdr_langgraph.quality_judge import _heuristic_evaluate

        reply = "Linha 1\nLinha 2\nLinha 3\nLinha 4\nLinha 5"
        result = _heuristic_evaluate("msg", reply, min_score=3)
        assert "muito_longa" in result.issues

    def test_markdown_json_reduz_score(self):
        from backend.agents.sdr_langgraph.quality_judge import _heuristic_evaluate

        result1 = _heuristic_evaluate("", "{json: 'value'}", min_score=3)
        assert "markdown_json_cru" in result1.issues

        result2 = _heuristic_evaluate("", "Texto com **negrito**", min_score=3)
        assert "markdown_json_cru" in result2.issues

        result3 = _heuristic_evaluate("", "```json\n{}\n```", min_score=3)
        assert "markdown_json_cru" in result3.issues

    def test_mensagem_longa_chars_reduz_score(self):
        from backend.agents.sdr_langgraph.quality_judge import _heuristic_evaluate

        reply = "x" * 400
        result = _heuristic_evaluate("msg", reply, min_score=3)
        assert "muito_longa_chars" in result.issues

    def test_score_minimo_e_1(self):
        """Score nunca pode ser menor que 1."""
        from backend.agents.sdr_langgraph.quality_judge import _heuristic_evaluate

        reply = "{json}\n" + "x" * 500 + "\n" + "?" * 10 + "".join([chr(0x2700 + i) for i in range(10)])
        result = _heuristic_evaluate("", reply, min_score=3)
        assert result.score >= 1


class TestEvaluateReply:
    """Testa evaluate_reply()."""

    def test_resposta_vazia_nao_envia(self):
        from backend.agents.sdr_langgraph.quality_judge import evaluate_reply

        result = evaluate_reply("msg", "", enable_llm=False)
        assert result.score == 0
        assert result.should_send is False

    def test_enable_llm_false_usa_heuristica(self):
        from backend.agents.sdr_langgraph.quality_judge import evaluate_reply

        reply = "Oi, tudo bem?"
        result = evaluate_reply("msg", reply, enable_llm=False)
        assert result.score >= 1
        assert result.should_send is True  # Score 5, min 3

    def test_min_score_4_bloqueia_mensagens_ruins(self):
        from backend.agents.sdr_langgraph.quality_judge import evaluate_reply

        reply = "Ok"
        result = evaluate_reply("msg", reply, enable_llm=False, min_score_to_send=4)
        assert result.should_send is False

    def test_min_score_3_permite_mensagens_boas(self):
        from backend.agents.sdr_langgraph.quality_judge import evaluate_reply

        reply = "Oi, tudo bem?"
        result = evaluate_reply("msg", reply, enable_llm=False, min_score_to_send=3)
        assert result.should_send is True

    def test_with_incoming_message(self):
        from backend.agents.sdr_langgraph.quality_judge import evaluate_reply

        result = evaluate_reply(
            incoming="Quanto custa?",
            reply="R$ 1499",
            stage="close",
            enable_llm=False
        )
        assert isinstance(result.score, int)
        assert isinstance(result.should_send, bool)

    def test_llm_fallback_para_heuristica(self):
        from backend.agents.sdr_langgraph.quality_judge import evaluate_reply

        # Habilita LLM mas força falha
        with patch("backend.agents.sdr_langgraph.quality_judge.call_claude", side_effect=Exception("LLM fail")):
            result = evaluate_reply("msg", "Oi tudo bem?", enable_llm=True)
            # Deve voltar para heuristica
            assert isinstance(result.score, int)
            assert 1 <= result.score <= 5


class TestQualityScoreFields:
    """Verifica estrutura de QualityScore."""

    def test_score_tem_issues(self):
        from backend.agents.sdr_langgraph.quality_judge import evaluate_reply

        result = evaluate_reply("", "{json}", enable_llm=False)
        assert hasattr(result, 'issues')
        assert isinstance(result.issues, list)

    def test_score_tem_should_send(self):
        from backend.agents.sdr_langgraph.quality_judge import evaluate_reply

        result = evaluate_reply("", "Oi", enable_llm=False)
        assert hasattr(result, 'should_send')
        assert isinstance(result.should_send, bool)

    def test_score_tem_rationale(self):
        from backend.agents.sdr_langgraph.quality_judge import evaluate_reply

        result = evaluate_reply("", "Oi", enable_llm=False)
        assert hasattr(result, 'rationale')
        assert isinstance(result.rationale, str)


class TestEdgeCases:
    """Edge cases."""

    def test_stage_default(self):
        from backend.agents.sdr_langgraph.quality_judge import evaluate_reply

        result = evaluate_reply("msg", "Oi", enable_llm=False)
        assert isinstance(result.score, int)

    def test_segmento_vazio(self):
        from backend.agents.sdr_langgraph.quality_judge import evaluate_reply

        result = evaluate_reply("msg", "Oi", segmento="", enable_llm=False)
        assert isinstance(result.score, int)

    def test_resposta_muito_curta(self):
        from backend.agents.sdr_langgraph.quality_judge import evaluate_reply

        result = evaluate_reply("msg", "Ok", enable_llm=False)
        assert result.score >= 1

    def test_resposta_normal(self):
        from backend.agents.sdr_langgraph.quality_judge import evaluate_reply

        reply = "Oi! Tudo bem? Vi que voces tem experiencia com academias."
        result = evaluate_reply("msg", reply, enable_llm=False)
        assert result.score >= 3
        assert result.should_send is True
