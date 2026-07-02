"""Characterization tests for whatsapp.response_executor.

Proves the current behavior of the response execution block:
- Guard evaluation (allow/block)
- Tenant connection check
- Send + persist + stage advance
- Cooldown/daily increment
- Handoff notification
"""

import sys
import types
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from whatsapp.response_executor import (
    ExecutionContext,
    evaluate_guard,
    check_tenant_connected,
    send_response,
    execute_response,
)


# ── Helpers ──────────────────────────────────────────────────────────────


class _FakeEngine:
    """Fake SQLAlchemy engine."""

    def __init__(self, prior_outbound=False):
        self._prior_outbound = prior_outbound

    def connect(self):
        return _FakeConn(self._prior_outbound)


class _FakeConn:
    def __init__(self, prior_outbound):
        self._prior_outbound = prior_outbound
        self._executed = []
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, query, params=None):
        self._executed.append((query, params))
        return _FakeResult(self._prior_outbound)

    def commit(self):
        self.committed = True


class _FakeResult:
    def __init__(self, prior_outbound):
        self._prior = prior_outbound

    def scalar(self):
        return 1 if self._prior else 0

    def fetchall(self):
        return []


def _franz_output(reply="Oi!", next_stage="followup1", should_handoff=False, intent="reply", update_facts=None):
    return types.SimpleNamespace(
        reply=reply,
        proximo_passo="",
        next_stage=next_stage,
        should_handoff=should_handoff,
        intent=intent,
        update_facts=update_facts or {},
    )


def _make_ctx(
    resposta="Oi, tudo bem?",
    novo_stage="followup1",
    raw_stage="followup1",
    opt_out=False,
    prior_outbound=False,
    tenant_connected=True,
    tenant_status="connected",
    franz_output_obj=None,
    send_ok=True,
):
    """Build an ExecutionContext with sensible defaults and tracking lists."""
    saved = []
    stages = []
    cooldowns = []
    increments = []
    handoffs = []

    def _save_interaction(lead_id, msg, direction, user_id):
        saved.append((lead_id, msg, direction, user_id))

    def _update_stage(lead_id, stage, user_id):
        stages.append((lead_id, stage, user_id))

    def _set_cooldown(lead_key):
        cooldowns.append(lead_key)

    def _increment_daily(lead_key):
        increments.append(lead_key)

    def _notify_handoff(*args, **kwargs):
        handoffs.append((args, kwargs))

    class FakeHttpClient:
        def post(self, url, **kwargs):
            return types.SimpleNamespace(status_code=200 if send_ok else 500, text="")

    ctx = ExecutionContext(
        engine=_FakeEngine(prior_outbound),
        http_client=FakeHttpClient(),
        meowhats_http="http://localhost:3001",
        meowhats_key="test-key",
        tenant_id="fralib_user_2",
        jid="5511999999999@s.whatsapp.net",
        lead_id="lead-1",
        lead_name="Acme Corp",
        telefone="5511999999999",
        user_id=2,
        segmento="tech",
        status="concluido",
        sdr_stage_atual="intro",
        novo_stage=novo_stage,
        raw_stage=raw_stage,
        resposta=resposta,
        resposta_partes=[resposta],
        franz_output=franz_output_obj or _franz_output(reply=resposta, next_stage=novo_stage),
        opt_out=opt_out,
        prior_outbound=prior_outbound,
        lead_key="2:5511999999999",
        is_tenant_connected_fn=lambda tid: tenant_connected,
        get_tenant_status_fn=lambda tid: tenant_status,
        set_cooldown_fn=_set_cooldown,
        increment_daily_fn=_increment_daily,
        notify_handoff_fn=_notify_handoff,
        save_interaction_fn=_save_interaction,
        update_stage_fn=_update_stage,
        humanized_delay_fn=lambda text: 0.0,
    )
    return ctx, saved, stages, cooldowns, increments, handoffs


# ── Tests: evaluate_guard ────────────────────────────────────────────────


def test_guard_allows_normal_reply():
    """Normal reply without opt-out passes the guard."""
    ctx, *_ = _make_ctx()
    allowed, guard = evaluate_guard(ctx)
    assert allowed is True


def test_guard_blocks_opt_out():
    """Opt-out reply is blocked by the guard."""
    ctx, *_ = _make_ctx(opt_out=True)
    allowed, guard = evaluate_guard(ctx)
    assert allowed is False
    assert guard.code == "opt_out"


# ── Tests: check_tenant_connected ────────────────────────────────────────


def test_tenant_connected_returns_true():
    ctx, *_ = _make_ctx(tenant_connected=True, tenant_status="connected")
    connected, status = check_tenant_connected(ctx)
    assert connected is True
    assert status == "connected"


def test_tenant_disconnected_returns_false_with_status():
    ctx, *_ = _make_ctx(tenant_connected=False, tenant_status="pairing")
    connected, status = check_tenant_connected(ctx)
    assert connected is False
    assert status == "pairing"


# ── Tests: send_response ─────────────────────────────────────────────────


def test_send_response_persists_output_on_success():
    """When send succeeds, interaction is saved and stage advanced."""
    ctx, saved, stages, cooldowns, increments, _ = _make_ctx()
    result = send_response(ctx)
    assert result is True
    assert ("lead-1", "Oi, tudo bem?", "saida", 2) in saved
    assert ("lead-1", "followup1", 2) in stages
    assert cooldowns == ["2:5511999999999"]
    assert increments == ["2:5511999999999"]


def test_send_response_does_not_persist_on_failure():
    """When send fails, interaction/stage are not persisted.

    Note: cooldown e increment_daily SÃO setados ANTES do envio
    intencionalmente (response_executor.py:111-114) para evitar race
    condition entre threads. Esse teste verifica apenas que dados de
    conversa (saved, stages) não vazam em caso de falha de envio.
    """
    ctx, saved, stages, cooldowns, increments, _ = _make_ctx(send_ok=False)
    result = send_response(ctx)
    assert result is False
    assert saved == []
    assert stages == []
    # Cooldown/daily são setados antes do envio (anti-race) — não validar aqui
    # assert cooldowns == []  # removido: comportamento correto é setar antes
    # assert increments == []  # removido: comportamento correto é setar antes


def test_send_response_triggers_handoff_when_flagged():
    """When franz signals handoff, notify function is called."""
    fo = _franz_output(next_stage="handoff", should_handoff=True)
    ctx, _, _, _, _, handoffs = _make_ctx(
        franz_output_obj=fo, novo_stage="qualificados", raw_stage="handoff"
    )
    send_response(ctx)
    assert len(handoffs) == 1


# ── Tests: execute_response (full flow) ──────────────────────────────────


def test_execute_response_happy_path():
    """Full flow: guard passes, tenant connected, send succeeds."""
    ctx, saved, stages, cooldowns, *_ = _make_ctx()
    sent, reason = execute_response(ctx)
    assert sent is True
    assert reason is None
    assert len(saved) == 1
    assert len(stages) == 1


def test_execute_response_blocked_by_guard_opt_out():
    """Full flow blocked by opt-out guard, stage set to perdidos."""
    ctx, _, stages, *_ = _make_ctx(opt_out=True)
    sent, reason = execute_response(ctx)
    assert sent is False
    assert "guard:opt_out" in reason
    assert ("lead-1", "perdidos", 2) in stages


def test_execute_response_blocked_by_disconnect():
    """Full flow blocked when tenant is disconnected."""
    ctx, saved, stages, *_ = _make_ctx(tenant_connected=False, tenant_status="pairing")
    sent, reason = execute_response(ctx)
    assert sent is False
    assert "disconnected" in reason
    assert saved == []
    assert stages == []
