from types import SimpleNamespace

from backend.endpoints.pipeline_phase_helpers import build_franz_outreach_payload


def test_build_franz_outreach_payload_includes_optional_test_number():
    state = SimpleNamespace(
        lead_nome="Lead X",
        lead_obj=SimpleNamespace(
            lead=SimpleNamespace(
                cidade="São Paulo",
                segmento="fitness",
                telefone="11999999999",
                whatsapp="11999999999",
                rating=4.9,
            )
        ),
        site_url="https://example.com",
        qualificacao_caio=SimpleNamespace(score=91, tier="HOT", motivo="ok"),
        lead_id=123,
        tenant_id=7,
        run_id="run123",
    )
    payload = build_franz_outreach_payload(state, {"_job_id": "job-1", "_bryan_test_number": 42})

    assert payload["_bryan_test_number"] == "42"
    assert payload["site_url"] == "https://example.com"
    assert payload["_parent_job_id"] == "job-1"
