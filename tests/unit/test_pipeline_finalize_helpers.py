from types import SimpleNamespace

from backend.endpoints.pipeline_phase_helpers import finalize_reprocess_state


def test_finalize_reprocess_state_resets_context_and_session():
    calls = []

    class FakeTracker:
        def __init__(self):
            self.lead_nome = ""

        def resumo(self):
            calls.append("resumo")
            return {"ok": True}

    class FakeSession:
        def close(self):
            calls.append("close")

    def _set_ctx(*args):
        calls.append(("ctx", args))

    def _update(db, tenant_id, pausado=False):
        calls.append(("update", tenant_id, pausado))

    state = SimpleNamespace(lead_nome="Lead")

    finalize_reprocess_state(
        state,
        tenant_id=99,
        token_tracker=FakeTracker(),
        set_llm_context=_set_ctx,
        update_pipeline_state=_update,
        session_factory=lambda: FakeSession(),
    )

    assert "resumo" in calls
    assert ("ctx", (None, None, None)) in calls
    assert ("update", 99, False) in calls
    assert "close" in calls
