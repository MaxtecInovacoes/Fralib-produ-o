"""pipeline_fsm.py — FSM pura do pipeline (E4 plano 2026-07-02)."""

PHASES = (
    "hunter",
    "caio",
    "jina",
    "design_director",
    "inteligencia",
    "nicho",
    "variacao",
    "arquiteto",
    "builder_renderer",
    "quality_gate",
    "validador",
    "deploy",
    "franz_sdr",
)


def is_valid_transition(from_phase: str, to_phase: str) -> bool:
    """Decide se uma transicao entre fases eh valida.

    FSM sequencial com pulos conhecidos (ex: caio→nicho pula jina
    em fast-path; builder→deploy pula quality_gate/validador em
    fail-fast).
    """
    if from_phase not in PHASES:
        return False
    if to_phase not in PHASES:
        return False
    return PHASES.index(to_phase) > PHASES.index(from_phase)


def next_phase(current: str) -> str | None:
    """Retorna proxima fase ou None se ja eh a ultima."""
    if current not in PHASES:
        return None
    i = PHASES.index(current)
    if i + 1 < len(PHASES):
        return PHASES[i + 1]
    return None