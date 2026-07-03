"""Testes Sprint 1.7 — SDR sem fallback templates.

Garante:
- fallback_templates.py foi DELETADO
- _llm_with_retries_and_breaker faz 3 retries com backoff
- Circuit breaker abre apos 3 falhas e bloqueia a 4a chamada
- Quando tudo falha, caller marca needs_human_followup (NAO envia template)
- Nenhum texto hardcoded generico no agent.py
- SDR nodes usam _llm_with_retries_and_breaker (NAO chamam call_claude direto)
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))

from agents.sdr_langgraph.circuit_breaker import (  # noqa: E402
    StageCircuitBreaker,
    CircuitOpenError,
    get_breaker,
    reset_for_test,
)
from agents.sdr_langgraph.agent import (  # noqa: E402
    _llm_with_retries_and_breaker,
    SDRFallbackError,
)


# ── Templates hardcoded: deletados ────────────────────────────────────────


@pytest.mark.unit
class TestFallbackTemplatesDeleted:
    def test_fallback_templates_module_does_not_exist(self):
        """Sprint 1.7: fallback_templates.py FOI REMOVIDO. A 'tentacao' nao existe mais."""
        path = _ROOT / "backend" / "agents" / "sdr_langgraph" / "fallback_templates.py"
        assert not path.exists(), f"{path} should be deleted but exists"

    def test_agent_does_not_import_fallback_templates(self):
        """Nenhum import de fallback_templates deve existir em SDR."""
        agent_path = _ROOT / "backend" / "agents" / "sdr_langgraph" / "agent.py"
        src = agent_path.read_text(encoding="utf-8")
        assert "fallback_templates" not in src, "agent.py ainda importa fallback_templates"
        assert "FALLBACK_TEMPLATES" not in src, "FALLBACK_TEMPLATES ainda em uso"
        assert "get_fallback" not in src, "get_fallback ainda usado"


# ── Retry agressivo: 3 tentativas com backoff ─────────────────────────────


@pytest.mark.unit
class TestRetryAggressive:
    def setup_method(self):
        reset_for_test()

    def test_three_retries_with_backoff(self, monkeypatch):
        """Mock fn que falha 2x e sucede na 3a. Sistema deve chamar 3x e retornar."""
        calls = []

        def fake_sleep(d):
            calls.append(("sleep", d))

        monkeypatch.setattr("time.sleep", fake_sleep)
        # Patch dentro do retry_helper (ele usa time.sleep direto)
        from services import retry_helper
        monkeypatch.setattr(retry_helper.time, "sleep", fake_sleep)

        attempts = []

        def fake_fn():
            attempts.append(1)
            if len(attempts) < 3:
                raise Exception(f"fail {len(attempts)}")
            return "ok"

        reply = _llm_with_retries_and_breaker("retry_test", fake_fn)
        assert reply == "ok"
        assert len(attempts) == 3, f"deveria ter chamado 3x, chamou {len(attempts)}"
        # 2 sleeps entre as 3 tentativas
        sleeps = [d for kind, d in calls]
        assert len(sleeps) == 2, f"esperava 2 sleeps, teve {len(sleeps)}"
        # Backoff exponencial: primeiro ~5s ± jitter (entre 2.5 e 7.5)
        assert 2.0 <= sleeps[0] <= 7.5, f"primeiro sleep {sleeps[0]} fora da faixa"
        # Segundo ~10s ± jitter (entre 5 e 15)
        assert 5.0 <= sleeps[1] <= 15.0, f"segundo sleep {sleeps[1]} fora da faixa"

    def test_raises_sdr_fallback_after_exhaustion(self, monkeypatch):
        """3 falhas -> SDRFallbackError apos a 3a tentativa."""
        monkeypatch.setattr("time.sleep", lambda d: None)

        def fake_fn():
            raise Exception("always fails")

        with pytest.raises(SDRFallbackError) as exc_info:
            _llm_with_retries_and_breaker("exhaust_test", fake_fn)
        assert "failed after retries" in str(exc_info.value)

    def test_empty_reply_raises_sdr_fallback(self, monkeypatch):
        """fn retorna string vazia -> SDRFallbackError immediate (sem retry)."""
        monkeypatch.setattr("time.sleep", lambda d: None)

        def fake_fn():
            return ""

        with pytest.raises(SDRFallbackError) as exc_info:
            _llm_with_retries_and_breaker("empty_test", fake_fn)
        assert "returned empty reply" in str(exc_info.value)


# ── Circuit breaker: abre apos 3 falhas ───────────────────────────────────


@pytest.mark.unit
class TestCircuitBreaker:
    def setup_method(self):
        reset_for_test()

    def test_opens_after_three_failures(self, monkeypatch):
        """Apos 3 retry attempts do MESMO stage -> circuito abre."""
        monkeypatch.setattr("time.sleep", lambda d: None)

        def fake_fn():
            raise Exception("fail")

        breaker = get_breaker()
        assert not breaker.is_open("cb_stage")

        # 1 chamada externa dispara 3 retries internos, cada um registra 1 falha.
        with pytest.raises(SDRFallbackError):
            _llm_with_retries_and_breaker("cb_stage", fake_fn)

        assert breaker.is_open("cb_stage"), "deveria estar aberto apos 3 retries internos"

    def test_blocks_call_when_open(self, monkeypatch):
        """2a chamada externa com circuito aberto NAO tenta LLM."""
        monkeypatch.setattr("time.sleep", lambda d: None)
        calls = []

        def fake_fn():
            calls.append(1)
            raise Exception("fail")

        # 1a chamada: 3 retries internos, todos falham, circuit abre
        with pytest.raises(SDRFallbackError):
            _llm_with_retries_and_breaker("block_stage", fake_fn)
        assert len(calls) == 3

        # 2a chamada deve ser bloqueada sem tentar LLM
        with pytest.raises(CircuitOpenError):
            _llm_with_retries_and_breaker("block_stage", fake_fn)
        assert len(calls) == 3, f"nao deveria ter chamado LLM, mas chamou {len(calls)}x"

    def test_success_resets_circuit(self, monkeypatch):
        """Sucesso reseta contadores."""
        monkeypatch.setattr("time.sleep", lambda d: None)
        breaker = get_breaker()

        # Abrir
        try:
            _llm_with_retries_and_breaker("reset_stage", lambda: (_ for _ in ()).throw(Exception("x")))
        except SDRFallbackError:
            pass
        assert breaker.is_open("reset_stage")

        # Resetar com sucesso
        breaker.record_success("reset_stage")
        assert not breaker.is_open("reset_stage")

    def test_independent_stages(self, monkeypatch):
        """Falhas em stage A nao afetam stage B."""
        monkeypatch.setattr("time.sleep", lambda d: None)

        def fake_fn():
            raise Exception("fail")

        # Falha tudo no stage_a - circuit abre
        with pytest.raises(SDRFallbackError):
            _llm_with_retries_and_breaker("stage_a", fake_fn)

        breaker = get_breaker()
        assert breaker.is_open("stage_a")
        assert not breaker.is_open("stage_b"), "stage_b nao deveria estar aberto"


# ── Sem texto generico hardcoded ──────────────────────────────────────────


@pytest.mark.unit
class TestNoHardcodedGenericText:
    """Garante que nenhum template generico esta escondido no agent.py."""

    def test_no_hardcoded_greeting_text(self):
        """Texto tipo 'Combinado. Te chamo' ou 'Oi! Tudo bem?' deve ter saido."""
        agent_path = _ROOT / "backend" / "agents" / "sdr_langgraph" / "agent.py"
        src = agent_path.read_text(encoding="utf-8")
        forbidden = [
            "Combinado. Te chamo",
            "Oi! Tudo bem?",
            "como posso te ajudar hoje?",
            "Quer que eu te ajude",
            "Se fizer sentido, é só me avisar",
        ]
        for bad in forbidden:
            assert bad not in src, f"agent.py ainda contem texto generico: {bad!r}"

    def test_no_academia_specific_template(self):
        """'voce e o responsavel pela academia' era um if hardcoded — saiu."""
        agent_path = _ROOT / "backend" / "agents" / "sdr_langgraph" / "agent.py"
        src = agent_path.read_text(encoding="utf-8")
        assert "responsável pela academia" not in src
        assert "responsavel pela academia" not in src


# ── Nodes usam _llm_with_retries_and_breaker (NAO call_claude direto) ────


@pytest.mark.unit
class TestNodesUseHelper:
    """Garante que nenhum node chama call_claude fora do helper."""

    def test_call_claude_wrapped_in_nodes(self):
        """As 4 chamadas call_claude em agent.py devem estar dentro de lambdas
        passadas pra _llm_with_retries_and_breaker."""
        agent_path = _ROOT / "backend" / "agents" / "sdr_langgraph" / "agent.py"
        src = agent_path.read_text(encoding="utf-8")
        # Conta chamadas
        direct_calls = re.findall(r"=\s*call_claude\(", src)
        helper_calls = re.findall(r"_llm_with_retries_and_breaker\(", src)
        assert len(helper_calls) >= 4, (
            f"esperava >=4 chamadas do helper (greeting/hook/stage/is_decisor/schedule), "
            f"achei {len(helper_calls)}"
        )
        assert len(direct_calls) == 0, (
            f"NAO pode haver call_claude direto (sem retry): {direct_calls}"
        )


# ── Memory: needs_human_followup e NAO envia ──────────────────────────────


@pytest.mark.unit
class TestNeedsHumanFollowup:
    """Quando tudo falha, memory deve ser marcada, NAO deve enviar mensagem."""

    def test_node_marks_needs_human_and_returns_should_send_false(self, monkeypatch):
        """Mock do node_is_decisor: forçar _llm_with_retries_and_breaker a falhar.
        Verifica que o state retornado tem should_send=False e needs_human_followup=True.
        """
        monkeypatch.setattr("time.sleep", lambda d: None)
        reset_for_test()

        # Substituir helper pra sempre falhar COM SDRFallbackError
        import agents.sdr_langgraph.agent as _agent_mod

        def _always_fail(_stage, _fn):
            raise SDRFallbackError("mocked permanent failure")

        monkeypatch.setattr(_agent_mod, "_llm_with_retries_and_breaker", _always_fail)

        # Estado minimo pra node_is_decisor
        from types import SimpleNamespace

        memory = SimpleNamespace(
            nome="Loja do Zé",
            segmento="varejo",
            is_decisor=True,
            gatekeeper_level=0,
            last_message_received="sim, eu decido",
            lead_id="lead-xyz",
            stage="decisor",
        )
        state = {
            "memory": memory,
            "incoming_message": "sim, eu decido",
            "selected_agent": "qualificacao",
        }
        result = _agent_mod.node_is_decisor(state)
        assert result["should_send"] is False, "NAO deve enviar mensagem"
        assert result["needs_human_followup"] is True, "deve marcar needs_human_followup"
        assert result["outgoing_message"] == "", "mensagem vazia"
        assert memory.needs_human_followup is True
        assert memory.last_failure_stage == "is_decisor"
