from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from services.sdr_gateway import SdrMessageContext, evaluate_sdr_output


def _ctx(**overrides):
    data = {
        "tenant_id": 2,
        "lead_id": "lead-1",
        "lead_name": "Academia Start",
        "lead_segment": "academia",
        "stage": "pendente_wpp",
        "next_stage": "hook",
        "message": "Oi, sou Franz da FraLib. Posso falar com o responsavel?",
        "site_url": "https://seunegociofralib.site/sites/2/start-academia/",
        "prior_outbound": False,
        "direction": "outbound",
        "plan_allows_sdr": True,
        "whatsapp_connected": True,
        "within_schedule": True,
        "site_ready": True,
        "human_assumed": False,
        "opt_out": False,
    }
    data.update(overrides)
    return SdrMessageContext(**data)


def test_cold_intro_without_link_is_allowed():
    decision = evaluate_sdr_output(_ctx())

    assert decision.allowed
    assert decision.action == "send"


def test_cold_intro_cannot_reveal_site_link():
    decision = evaluate_sdr_output(
        _ctx(
            message=(
                "Oi! Franz aqui de novo. Fiz o projeto da Start Academia: "
                "https://seunegociofralib.site/sites/2/start-academia/"
            )
        )
    )

    assert not decision.allowed
    assert decision.code == "repeat_claim_without_history"


def test_cold_intro_cannot_send_project_even_without_url():
    decision = evaluate_sdr_output(
        _ctx(message="Tenho o projeto da Start Academia reservado aqui. O que achou?")
    )

    assert not decision.allowed
    assert decision.code == "site_reveal_too_early"


def test_followup_requires_prior_outbound_history():
    decision = evaluate_sdr_output(
        _ctx(
            direction="followup",
            stage="followup_24h",
            message="Passando aqui para ver se conseguiu olhar.",
            prior_outbound=False,
        )
    )

    assert not decision.allowed
    assert decision.code == "followup_without_history"


def test_reveal_stage_with_history_can_send_site_link():
    decision = evaluate_sdr_output(
        _ctx(
            direction="reply",
            stage="reveal",
            next_stage="feedback",
            message="Perfeito, segue o site: https://seunegociofralib.site/sites/2/start-academia/",
            prior_outbound=True,
        )
    )

    assert decision.allowed


def test_human_assumed_and_opt_out_stop_sdr():
    human = evaluate_sdr_output(_ctx(stage="handoff", prior_outbound=True))
    opt_out = evaluate_sdr_output(_ctx(opt_out=True, prior_outbound=True))

    assert not human.allowed
    assert human.action == "handoff"
    assert not opt_out.allowed
    assert opt_out.code == "opt_out"


def test_quality_block_stage_stops_sdr():
    decision = evaluate_sdr_output(
        _ctx(stage="blocked_quality_incident", prior_outbound=True)
    )

    assert not decision.allowed
    assert decision.code == "lead_blocked"


def test_academia_message_cannot_use_delivery_context():
    decision = evaluate_sdr_output(
        _ctx(
            message="Vocês fazem delivery ou só pedido pelo cardápio online?",
            prior_outbound=True,
            direction="reply",
        )
    )

    assert not decision.allowed
    assert decision.code == "segment_contamination"
