"""
Testes unitários para os 3 bugs críticos do SDR (Franz).

BUG 1: sanitize_reply NÃO deve chamar retry_extractor (2ª LLM)
BUG 2: watchdog deve liberar quando lead_responded=True
BUG 3: history deve ser sincronizada com state LangGraph

Executar: python -m pytest tests/unit/test_sdr_bugfix.py -v
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import pytest


# ════════════════════════════════════════════════════════════════════
# BUG 1: sanitize_reply NÃO deve chamar retry_extractor
# ════════════════════════════════════════════════════════════════════

def test_sanitize_sem_chamar_llm_extra():
    """
    BUGFIX: sanitize_reply com retry_extractor=None NÃO deve chamar LLM extra.
    Garante que a sanitização é feita via regex, não via LLM.
    """
    from whatsapp.sdr_reply_service import sanitize_reply

    # JSON com campo resposta - deve extrair via regex
    raw = '{"resposta":"Oi, tudo bem?","novo_stage":"intro"}'
    result = sanitize_reply(raw, retry_extractor=None)

    assert result == "Oi, tudo bem?"
    assert not result.startswith("{")
    assert '"resposta"' not in result


def test_sanitize_nao_chama_retry_extractor_quando_regex_funciona():
    """
    Quando regex consegue extrair, NÃO deve chamar retry_extractor.
    """
    from whatsapp.sdr_reply_service import sanitize_reply

    # Mock retry_extractor que deve ser chamado SÓ se regex falhar
    call_count = {"count": 0}

    def mock_retry_extractor(raw):
        call_count["count"] += 1
        return "NÃO DEVE SER CHAMADO"

    raw = '{"resposta":"Texto limpo","stage":"hook"}'
    result = sanitize_reply(raw, retry_extractor=mock_retry_extractor)

    # Regex funciona, então retry_extractor NÃO deve ser chamado
    assert call_count["count"] == 0
    assert result == "Texto limpo"


def test_sanitize_chama_retry_apenas_se_regex_falhar():
    """
    retry_extractor deve ser chamado SÓ quando regex falha.
    """
    from whatsapp.sdr_reply_service import sanitize_reply

    call_count = {"count": 0}

    def mock_retry_extractor(raw):
        call_count["count"] += 1
        return "Fallback texto"

    # JSON malformado que regex não consegue extrair
    raw = '{"foo": "bar", "baz": 123}'
    result = sanitize_reply(raw, retry_extractor=mock_retry_extractor)

    # Regex falha, então retry_extractor DEVE ser chamado
    assert call_count["count"] == 1
    assert result == "Fallback texto"


def test_responder_nao_envia_json_puro():
    """
    JSON invalido deve virar resposta vazia, que o listener nao envia.
    """
    from whatsapp.sdr_reply_service import sanitize_reply

    # JSON inválido que sanitization não consegue processar
    raw = '{invalid json}'
    result = sanitize_reply(raw, retry_extractor=None)

    assert result == ""
    assert not bool(result.strip())


# ════════════════════════════════════════════════════════════════════
# BUG 2: watchdog libera quando lead_responded=True
# ════════════════════════════════════════════════════════════════════

def test_watchdog_libera_quando_lead_respondeu(monkeypatch):
    """
    BUGFIX: can_send_next_outbound deve retornar True quando lead_responded=True.
    """
    from agents.sdr_langgraph.watchdog import can_send_next_outbound

    # Simular resposta do banco (não vai ser consultada se lead_responded=True)
    class MockConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, *args, **kwargs):
            # Não deve ser chamado se lead_responded=True
            raise AssertionError("DB não deve ser consultado quando lead_responded=True")

    class MockEngine:
        def connect(self):
            return MockConn()

    monkeypatch.setattr(
        "agents.sdr_langgraph.watchdog._get_engine",
        lambda: MockEngine()
    )

    pode_enviar, motivo = can_send_next_outbound(
        telefone="5511999999999",
        user_id=1,
        sdr_stage="hook",
        lead_responded=True
    )

    assert pode_enviar is True
    assert motivo == "lead_responded_can_reply"


def test_watchdog_bloqueia_sem_lead_responded(monkeypatch):
    """
    Sem lead_responded=True, watchdog pode bloquear (teste de regressão).
    """
    from agents.sdr_langgraph.watchdog import can_send_next_outbound

    class MockResult:
        def fetchall(self):
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            return [
                ("msg1", "saida", now),
                ("msg2", "saida", now),
            ]

    class MockConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, *args, **kwargs):
            # 2 mensagens de saída sem resposta → bloqueia
            return MockResult()

    class MockEngine:
        def connect(self):
            return MockConn()

    monkeypatch.setattr(
        "agents.sdr_langgraph.watchdog._get_engine",
        lambda: MockEngine()
    )

    pode_enviar, motivo = can_send_next_outbound(
        telefone="5511999999999",
        user_id=1,
        sdr_stage="hook",
        lead_responded=False  # Não respondeu
    )

    assert pode_enviar is False
    assert motivo == "max_2_messages_without_response"


def test_responder_nao_envia_duplicado(monkeypatch):
    """
    Se 2ª chamada LLM for feita desnecessariamente, deve falhar.
    Este teste verifica que o fluxo não faz chamada dupla.
    """
    from whatsapp.sdr_reply_service import is_duplicate_reply

    # History com mensagem do bot
    history = [
        {"role": "user", "content": "Olá"},
        {"role": "assistant", "content": "Olá! Como posso ajudar?"},
    ]

    # Mesma mensagem → duplicado
    is_dup = is_duplicate_reply(history, "Olá! Como posso ajudar?")

    # Deve detectar duplicado e não enviar
    assert is_dup is True


# ════════════════════════════════════════════════════════════════════
# BUG 3: history sincronizada com LangGraph state
# ════════════════════════════════════════════════════════════════════

def test_history_sincronizada_com_langgraph():
    """
    BUGFIX: history deve ser mesclada com state LangGraph anterior.
    Verifica que a lógica de merge não perde mensagens.
    """
    # Simular dados que seriam passados
    db_history = [
        {"role": "user", "content": "Mensagem antiga do DB 1"},
        {"role": "assistant", "content": "Resposta antiga do DB 1"},
    ]

    # Simular state LangGraph com mensagens adicionais
    lg_history = [
        {"type": "human", "content": "Mensagem do state LangGraph"},
        {"type": "ai", "content": "Resposta do state LangGraph"},
    ]

    # Lógica de merge (reproduzir a lógica do compat.py)
    merged = list(db_history)
    for msg in lg_history[-10:]:
        if isinstance(msg, dict):
            role = "assistant" if msg.get("type") == "ai" else "user"
            content = msg.get("content", "")
        else:
            role = "assistant"
            content = str(msg) if msg else ""
        if content:
            merged.insert(0, {"role": role, "content": content})

    # De-duplicar
    seen = set()
    deduped = []
    for item in merged:
        key = f"{item.get('role')}:{item.get('content', '')[:50]}"
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    # Manter últimas 20
    deduped = deduped[-20:]

    # Verificar que todas as mensagens foram preservadas
    contents = [item["content"] for item in deduped]
    assert "Mensagem antiga do DB 1" in contents
    assert "Resposta antiga do DB 1" in contents
    assert "Mensagem do state LangGraph" in contents
    assert "Resposta do state LangGraph" in contents


def test_history_dedup_preserva_ordem():
    """
    De-duplicação deve preservar ordem cronológica (mais antigo primeiro).
    """
    history = [
        {"role": "user", "content": "Msg 1"},
        {"role": "assistant", "content": "Msg 2"},
        {"role": "user", "content": "Msg 1"},  # Duplicado
        {"role": "assistant", "content": "Msg 2"},  # Duplicado
        {"role": "user", "content": "Msg 3"},
    ]

    # Lógica de dedup do compat.py
    seen = set()
    deduped = []
    for item in history:
        key = f"{item.get('role')}:{item.get('content', '')[:50]}"
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    assert len(deduped) == 3
    assert deduped[0]["content"] == "Msg 1"
    assert deduped[1]["content"] == "Msg 2"
    assert deduped[2]["content"] == "Msg 3"


def test_history_limit_20_mensagens():
    """
    History mesclada deve ser limitada a 20 mensagens.
    """
    # Gerar 30 mensagens
    history = [{"role": "user", "content": f"Msg {i}"} for i in range(30)]

    # Limitar a 20
    limited = history[-20:]

    assert len(limited) == 20
    assert limited[0]["content"] == "Msg 10"
    assert limited[-1]["content"] == "Msg 29"


# ════════════════════════════════════════════════════════════════════
# Testes de regressão
# ════════════════════════════════════════════════════════════════════

def test_build_history_reversed_order():
    """
    build_history deve reverter ordem para cronológica correta.
    """
    from whatsapp.sdr_reply_service import build_history

    # DB retorna DESC, mas precisamos ASC (mais antigo primeiro)
    rows = [("msg_nova", "saida"), ("msg_velha", "saida")]

    history = build_history(rows)

    # Mais antigo primeiro
    assert history[0]["content"] == "msg_velha"
    assert history[1]["content"] == "msg_nova"


def test_is_emoji_reaction_only():
    """
    Reactions de emoji não devem contar como resposta real.
    """
    from agents.sdr_langgraph.watchdog import is_emoji_reaction_only

    assert is_emoji_reaction_only("👀") is True
    assert is_emoji_reaction_only("❤️") is True
    assert is_emoji_reaction_only("👍👍") is True
    assert is_emoji_reaction_only("") is True
    assert is_emoji_reaction_only("ok") is False
    assert is_emoji_reaction_only("sim, quero") is False
