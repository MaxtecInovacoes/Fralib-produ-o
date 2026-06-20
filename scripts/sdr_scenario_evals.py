"""Deterministic SDR scenario evals.

These are not WhatsApp tests and do not call an LLM. They validate the safety
contract that every real SDR send path must obey before a message is sent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from services.sdr_gateway import SdrMessageContext, evaluate_sdr_output  # noqa: E402


@dataclass(frozen=True)
class Scenario:
    name: str
    context: SdrMessageContext
    allowed: bool
    code: str


def _ctx(**overrides) -> SdrMessageContext:
    data = {
        "tenant_id": 2,
        "lead_id": "scenario-lead",
        "lead_name": "Start Academia",
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


SCENARIOS = [
    Scenario("cliente_frio_intro_segura", _ctx(), True, "allowed"),
    Scenario(
        "cliente_frio_nao_recebe_link",
        _ctx(
            message=(
                "Oi! Franz aqui de novo. Tenho o projeto reservado: "
                "https://seunegociofralib.site/sites/2/start-academia/"
            )
        ),
        False,
        "repeat_claim_without_history",
    ),
    Scenario(
        "interessado_pode_receber_link_depois_do_historico",
        _ctx(
            stage="reveal",
            next_stage="feedback",
            direction="reply",
            prior_outbound=True,
            message="Perfeito. Segue o site: https://seunegociofralib.site/sites/2/start-academia/",
        ),
        True,
        "allowed",
    ),
    Scenario(
        "funcionario_pode_encaminhar_sem_link_preco",
        _ctx(
            stage="qualify",
            next_stage="pain",
            direction="reply",
            prior_outbound=True,
            message="Boa. Voce consegue mostrar isso para quem decide pelo marketing dai?",
        ),
        True,
        "allowed",
    ),
    Scenario(
        "mau_humor_opt_out_para_bot",
        _ctx(
            stage="qualify",
            direction="reply",
            prior_outbound=True,
            opt_out=True,
            message="Tudo bem, nao vou insistir.",
        ),
        False,
        "opt_out",
    ),
    Scenario(
        "followup_sem_historico_bloqueado",
        _ctx(
            stage="followup_24h",
            direction="followup",
            prior_outbound=False,
            message="Passando para saber se conseguiu ver o site.",
        ),
        False,
        "followup_without_history",
    ),
]


def run() -> tuple[int, int]:
    passed = 0
    failed = 0
    for scenario in SCENARIOS:
        decision = evaluate_sdr_output(scenario.context)
        ok = decision.allowed == scenario.allowed and decision.code == scenario.code
        status = "PASS" if ok else "FAIL"
        print(
            f"[{status}] {scenario.name}: allowed={decision.allowed} "
            f"code={decision.code} reason={decision.reason}"
        )
        if ok:
            passed += 1
        else:
            failed += 1
    print(f"sdr scenario evals: passed={passed} failed={failed}")
    return passed, failed


if __name__ == "__main__":
    _, failed_count = run()
    raise SystemExit(1 if failed_count else 0)
