"""Testes para intent_classifier.py.

Testa:
- Classificacao de intents via regex
- Confidence scores
- Signals (matches encontrados)
- Edge cases (texto vazio, muito longo)
- Prioridade entre intents empatadas
"""
import pytest

from backend.agents.sdr_langgraph.intent_classifier import (
    Intent,
    IntentResult,
    classify_intent,
)


class TestOptOutClassification:
    """Testa deteccao de OPT_OUT - deve ser preciso."""

    def test_parar_de_me_enviar(self):
        result = classify_intent("Para de me mandar mensagem")
        assert result.intent == Intent.OPT_OUT

    def test_nao_quero_mais(self):
        result = classify_intent("Nao quero mais")
        assert result.intent == Intent.OPT_OUT

    def test_tira_me_da_lista(self):
        result = classify_intent("Tira me da lista")
        assert result.intent == Intent.OPT_OUT

    def test_nao_atendo_nao_e_opt_out(self):
        """Bugfix: 'nao atendo atletas' NAO e opt-out - e qualificacao."""
        result = classify_intent("Nao atendo atletas")
        assert result.intent != Intent.OPT_OUT

    def test_tudo_bem_nao_e_opt_out(self):
        """'Tudo bem?' e greeting, nao opt-out."""
        result = classify_intent("Oi tudo bem?")
        assert result.intent != Intent.OPT_OUT

    def test_stop_isolado(self):
        result = classify_intent("stop")
        assert result.intent == Intent.OPT_OUT


class TestGatekeeperClassification:
    """Testa deteccao de GATEKEEPER."""

    def test_nao_sou_o_dono(self):
        result = classify_intent("Nao sou o dono da empresa")
        assert result.intent == Intent.GATEKEEPER

    def test_nao_esta_disponivel(self):
        result = classify_intent("Ele nao esta no momento")
        assert result.intent == Intent.GATEKEEPER

    def test_sou_recepcionista(self):
        result = classify_intent("Sou a recepcionista")
        assert result.intent == Intent.GATEKEEPER

    def test_encaminhe_pro_dono(self):
        result = classify_intent("Encaminha pra quem interessa")
        assert result.intent == Intent.GATEKEEPER


class TestBuyingIntentClassification:
    """Testa deteccao de BUYING_INTENT."""

    def test_quero_fechar(self):
        result = classify_intent("Quero fechar")
        assert result.intent == Intent.BUYING_INTENT

    def test_manda_o_link(self):
        result = classify_intent("Manda o link pra mim")
        assert result.intent == Intent.BUYING_INTENT

    def test_feedback_positivo_nao_e_buying(self):
        """Feedback como 'gostei' nao deve ser buying intent."""
        result = classify_intent("Gostei do site")
        assert result.intent != Intent.BUYING_INTENT


class TestScheduleClassification:
    """Testa deteccao de SCHEDULE."""

    def test_amanha(self):
        result = classify_intent("Amanha mesmo")
        assert result.intent == Intent.SCHEDULE

    def test_depois(self):
        result = classify_intent("Posso pensar depois?")
        assert result.intent == Intent.SCHEDULE

    def test_proxima_semana(self):
        result = classify_intent("Proxima semana we we conversa")
        assert result.intent == Intent.SCHEDULE

    def test_agendar(self):
        result = classify_intent("Podemos agendar?")
        assert result.intent == Intent.SCHEDULE


class TestObjectionClassification:
    """Testa deteccao de OBJECTION."""

    def test_muito_caro(self):
        result = classify_intent("Acho muito caro")
        assert result.intent == Intent.OBJECTION

    def test_quanto_custa(self):
        result = classify_intent("Quanto custa?")
        assert result.intent == Intent.OBJECTION

    def test_nao_tenho_dinheiro(self):
        result = classify_intent("Nao tenho dinheiro agora")
        assert result.intent == Intent.OBJECTION

    def test_nao_confio(self):
        result = classify_intent("Nao confio nesse tipo de servico")
        assert result.intent == Intent.OBJECTION

    def test_ja_tenho(self):
        result = classify_intent("Ja tenho um site")
        assert result.intent == Intent.OBJECTION

    def test_nao_tenho_tempo(self):
        result = classify_intent("Nao tenho tempo pra isso agora")
        assert result.intent == Intent.OBJECTION


class TestQuestionClassification:
    """Testa deteccao de QUESTION."""

    def test_como_funciona(self):
        result = classify_intent("Como funciona?")
        assert result.intent == Intent.QUESTION

    def test_interrogacao(self):
        result = classify_intent("Qual o prazo de entrega?")
        assert result.intent == Intent.QUESTION

    def test_me_explica(self):
        result = classify_intent("Me explica melhor")
        assert result.intent == Intent.QUESTION


class TestGreetingClassification:
    """Testa deteccao de GREETING."""

    def test_oi_simples(self):
        result = classify_intent("Oi")
        assert result.intent == Intent.GREETING

    def test_boa_noite(self):
        result = classify_intent("Boa noite")
        assert result.intent == Intent.GREETING

    def test_tudo_bem(self):
        result = classify_intent("Tudo bem?")
        assert result.intent == Intent.GREETING

    def test_eai(self):
        result = classify_intent("Eai")
        assert result.intent == Intent.GREETING


class TestAcknowledgmentClassification:
    """Testa deteccao de ACKNOWLEDGMENT."""

    def test_ok(self):
        result = classify_intent("Ok")
        assert result.intent == Intent.ACKNOWLEDGMENT

    def test_sim(self):
        result = classify_intent("sim")
        assert result.intent == Intent.ACKNOWLEDGMENT

    def test_hm(self):
        result = classify_intent("Hm")
        assert result.intent == Intent.ACKNOWLEDGMENT


class TestEngagementClassification:
    """Testa deteccao de ENGAGEMENT (resposta com conteudo)."""

    def test_porque_texto(self):
        result = classify_intent("Porque aqui na empresa...")
        assert result.intent == Intent.ENGAGEMENT

    def test_mensagem_longa(self):
        """Mensagens >= 8 palavras sao mais provaveis de ENGAGEMENT."""
        texto = "Temos uma equipe de 10 pessoas e precisamos de um site profissional para mostrar nossos servicos"
        result = classify_intent(texto)
        assert result.intent == Intent.ENGAGEMENT

    def test_sim_mas_resposta(self):
        """'Sim, mas...' indica engajamento com resistencia."""
        result = classify_intent("Sim, mas preciso primeiro ver o preco")
        assert result.intent == Intent.ENGAGEMENT


class TestConfidenceScores:
    """Verifica que confidence esta no range 0-1."""

    def test_confidence_sem_match(self):
        result = classify_intent("xyz123abc")
        assert result.intent == Intent.UNKNOWN
        assert 0 <= result.confidence <= 1

    def test_confidence_com_match(self):
        result = classify_intent("Quero fechar")
        assert result.confidence > 0

    def test_long_message_boosts_confidence(self):
        texto_longo = "Tenho uma academia ha 5 anos com 200 alunos e preciso de um site para mostrar meus servicos e captar novos clientes"
        result = classify_intent(texto_longo)
        # Mensagem longa com engagement deve ter confidence >= 0.3
        assert result.confidence >= 0.3


class TestEdgeCases:
    """Edge cases."""

    def test_texto_vazio(self):
        result = classify_intent("")
        assert result.intent == Intent.UNKNOWN
        assert result.confidence == 0.0

    def test_texto_none(self):
        result = classify_intent(None)
        assert result.intent == Intent.UNKNOWN
        assert result.confidence == 0.0

    def test_texto_muito_longo(self):
        """Texto > 2000 chars deve ser truncado."""
        texto_longo = "a" * 5000
        result = classify_intent(texto_longo)
        # Nao deve dar erro
        assert isinstance(result.intent, Intent)

    def test_signals_retornados(self):
        result = classify_intent("Quero fechar logo")
        assert isinstance(result.signals, list)

    def test_raw_text_preservado(self):
        texto = "Texto original"
        result = classify_intent(texto)
        assert result.raw_text == texto


class TestIntentResult:
    """Verifica estrutura de IntentResult."""

    def test_result_tem_intent(self):
        result = classify_intent("Oi")
        assert hasattr(result, 'intent')

    def test_result_tem_confidence(self):
        result = classify_intent("Oi")
        assert hasattr(result, 'confidence')

    def test_result_tem_signals(self):
        result = classify_intent("Oi")
        assert hasattr(result, 'signals')
        assert isinstance(result.signals, list)

    def test_result_tem_raw_text(self):
        result = classify_intent("Oi")
        assert hasattr(result, 'raw_text')
