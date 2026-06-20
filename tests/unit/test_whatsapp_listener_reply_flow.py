from pathlib import Path
import os
import sys
import types


os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import whatsapp_listener as listener
from whatsapp import response_executor


class _FakeExecuteResult:
    def __init__(self, *, scalar_value=None, rows=None, one=None):
        self._scalar_value = scalar_value
        self._rows = rows or []
        self._one = one

    def scalar(self):
        return self._scalar_value

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._one


class _FakeConn:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.calls = []

    def execute(self, query, params=None):
        self.calls.append((str(query), params or {}))
        sql = str(query)
        if "SELECT mensagem, direcao" in sql:
            return _FakeExecuteResult(rows=self.rows)
        if "SELECT mensagem FROM interacoes" in sql:
            return _FakeExecuteResult(scalar_value="")
        return _FakeExecuteResult()

    def commit(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeEngine:
    def __init__(self, rows=None):
        self.rows = rows or []

    def connect(self):
        return _FakeConn(rows=self.rows)


def _msg(text):
    return {
        "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
        "pushName": "Lead",
        "message": {"conversation": text},
    }


def _lead(status="concluido", stage="intro"):
    return (
        "lead-1",
        "Lead Teste",
        "academia",
        "Curitiba",
        stage,
        status,
        "5511999999999",
    )


def _patch_common(monkeypatch, lead_row):
    saved = []
    stages = []
    cooldowns = []
    increments = []
    handoffs = []

    monkeypatch.setattr(listener, "engine", _FakeEngine())
    monkeypatch.setattr(listener, "_user_id_from_tenant", lambda tenant_id: 2)
    monkeypatch.setattr(listener, "_buscar_lead_por_tel", lambda telefone, user_id: lead_row)
    monkeypatch.setattr(listener, "_salvar_interacao", lambda lead_id, mensagem, direcao, user_id=None: saved.append((lead_id, mensagem, direcao, user_id)))
    monkeypatch.setattr(listener, "_atualizar_stage", lambda lead_id, stage, user_id: stages.append((lead_id, stage, user_id)))
    monkeypatch.setattr(listener, "_user_can_use_bot", lambda user_id: True)
    monkeypatch.setattr(listener, "_get_sdr_settings", lambda user_id: {})
    monkeypatch.setattr(listener, "_is_human_paused", lambda lead_key: False)
    monkeypatch.setattr(listener, "_check_cooldown", lambda lead_key: False)
    monkeypatch.setattr(listener, "_check_daily_limit", lambda lead_key: False)
    monkeypatch.setattr(listener, "is_tenant_connected", lambda tenant_id, fallback_http=True: True)
    monkeypatch.setattr(listener, "_get_tenant_status", lambda tenant_id: "connected")
    monkeypatch.setattr(response_executor, "has_prior_outbound", lambda conn, lead_id, user_id: False)
    monkeypatch.setattr(response_executor, "evaluate_sdr_output", lambda ctx: types.SimpleNamespace(allowed=True, code="", reason=""))
    monkeypatch.setattr(response_executor._time, "sleep", lambda secs: None)
    monkeypatch.setattr(listener, "_time", types.SimpleNamespace(sleep=lambda secs: None, time=lambda: 0.0))
    monkeypatch.setattr(listener, "_set_cooldown", lambda lead_key: cooldowns.append(lead_key))
    monkeypatch.setattr(listener, "_increment_daily", lambda lead_key: increments.append(lead_key))
    monkeypatch.setattr(listener, "_notificar_handoff_humano", lambda *args, **kwargs: handoffs.append((args, kwargs)))
    return saved, stages, cooldowns, increments, handoffs


def test_processar_mensagem_saves_inbound_and_stops_before_ia_when_site_not_ready(monkeypatch):
    saved, stages, _, _, _ = _patch_common(monkeypatch, _lead(status="processando", stage="intro"))

    fake_sdr_module = types.SimpleNamespace(
        responder_lead=lambda **kwargs: (_ for _ in ()).throw(AssertionError("IA nao deveria ser chamada"))
    )
    monkeypatch.setitem(sys.modules, "agents.sdr_langgraph", fake_sdr_module)

    listener._processar_mensagem("fralib_user_2", _msg("Oi"))

    assert saved == [("lead-1", "Oi", "entrada", 2)]
    assert stages == []


def test_processar_mensagem_opt_out_marks_lost_before_ia(monkeypatch):
    saved, stages, _, _, _ = _patch_common(monkeypatch, _lead(status="concluido", stage="intro"))

    fake_sdr_module = types.SimpleNamespace(
        responder_lead=lambda **kwargs: (_ for _ in ()).throw(AssertionError("IA nao deveria ser chamada"))
    )
    monkeypatch.setitem(sys.modules, "agents.sdr_langgraph", fake_sdr_module)

    listener._processar_mensagem("fralib_user_2", _msg("Nao quero continuar"))

    assert saved == [("lead-1", "Nao quero continuar", "entrada", 2)]
    assert stages == [("lead-1", "perdidos", 2)]


def test_processar_mensagem_empty_reply_with_lost_stage_marks_lost_without_sending(monkeypatch):
    saved, stages, _, _, _ = _patch_common(monkeypatch, _lead(status="concluido", stage="intro"))

    franz_output = types.SimpleNamespace(
        reply="   ",
        next_stage="lost",
        intent="skip",
        proximo_passo="",
        update_facts=None,
        should_handoff=False,
    )
    fake_sdr_module = types.SimpleNamespace(responder_lead=lambda **kwargs: franz_output)
    monkeypatch.setitem(sys.modules, "agents.sdr_langgraph", fake_sdr_module)

    listener._processar_mensagem("fralib_user_2", _msg("Tenho uma duvida"))

    assert saved == [("lead-1", "Tenho uma duvida", "entrada", 2)]
    assert stages == [("lead-1", "perdidos", 2)]


def test_processar_mensagem_guard_opt_out_blocks_send_and_marks_lost(monkeypatch):
    saved, stages, cooldowns, increments, handoffs = _patch_common(monkeypatch, _lead(status="concluido", stage="intro"))

    franz_output = types.SimpleNamespace(
        reply="Pode deixar",
        next_stage="followup1",
        intent="reply",
        proximo_passo="",
        update_facts=None,
        should_handoff=False,
    )
    fake_sdr_module = types.SimpleNamespace(
        responder_lead=lambda **kwargs: franz_output,
        learning=types.SimpleNamespace(format_outgoing_messages=lambda text: [text]),
    )
    monkeypatch.setitem(sys.modules, "agents.sdr_langgraph", fake_sdr_module)
    monkeypatch.setattr(response_executor, "evaluate_sdr_output", lambda ctx: types.SimpleNamespace(allowed=False, code="opt_out", reason="blocked"))
    monkeypatch.setattr(response_executor, "send_presence_composing", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("nao deveria enviar presence")))
    monkeypatch.setattr(response_executor, "send_text_parts", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("nao deveria enviar resposta")))

    class _FakeHttpxClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setitem(sys.modules, "httpx", types.SimpleNamespace(Client=_FakeHttpxClient))

    listener._processar_mensagem("fralib_user_2", _msg("Tenho uma duvida"))

    assert saved == [("lead-1", "Tenho uma duvida", "entrada", 2)]
    assert stages == [("lead-1", "perdidos", 2)]
    assert cooldowns == []
    assert increments == []
    assert handoffs == []


def test_processar_mensagem_successful_send_persists_output_and_advances_stage(monkeypatch):
    saved, stages, cooldowns, increments, handoffs = _patch_common(monkeypatch, _lead(status="concluido", stage="intro"))
    presence_calls = []
    send_calls = []

    franz_output = types.SimpleNamespace(
        reply="Pode sim, me diga seu objetivo.",
        next_stage="followup1",
        intent="reply",
        proximo_passo="",
        update_facts=None,
        should_handoff=False,
    )
    fake_sdr_module = types.SimpleNamespace(
        responder_lead=lambda **kwargs: franz_output,
        learning=types.SimpleNamespace(format_outgoing_messages=lambda text: [text]),
    )
    monkeypatch.setitem(sys.modules, "agents.sdr_langgraph", fake_sdr_module)
    monkeypatch.setattr(response_executor, "send_presence_composing", lambda *args, **kwargs: presence_calls.append((args, kwargs)))
    monkeypatch.setattr(response_executor, "send_text_parts", lambda *args, **kwargs: (send_calls.append((args, kwargs)) or (True, "")))

    class _FakeHttpxClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setitem(sys.modules, "httpx", types.SimpleNamespace(Client=_FakeHttpxClient))

    listener._processar_mensagem("fralib_user_2", _msg("Tenho uma duvida"))

    assert saved == [
        ("lead-1", "Tenho uma duvida", "entrada", 2),
        ("lead-1", "Pode sim, me diga seu objetivo.", "saida", 2),
    ]
    assert stages == [("lead-1", "followup1", 2)]
    assert cooldowns == ["2:5511999999999"]
    assert increments == ["2:5511999999999"]
    assert len(presence_calls) == 1
    assert len(send_calls) == 1
    assert handoffs == []
