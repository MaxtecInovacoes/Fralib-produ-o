"""Franz SDR agent — core logic and axis normalization.

Re-exports conversion_axes and provides normalize_axis for training rules.
"""

import unicodedata

from backend.agents.franz.conversion_axes import (
    _CONVERSION_AXES,
    _CONVERSION_AXIS_LABELS,
    _CONVERSION_AXIS_WEIGHTS,
    get_active_conversion_axes,
    get_conversion_axis_prompts,
    get_conversion_score_bonus,
    normalize_conversion_axis,
)

__all__ = [
    "normalize_axis",
    "normalize_conversion_axis",
    "_CONVERSION_AXES",
    "_CONVERSION_AXIS_LABELS",
    "_CONVERSION_AXIS_WEIGHTS",
    "get_active_conversion_axes",
    "get_conversion_axis_prompts",
    "get_conversion_score_bonus",
]


def normalize_axis(raw: str | None) -> str:
    """Normalize axis name for training rules storage.

    Strips accents, lowercases, falls back to 'lead_qualification_rigor' if unknown.
    """
    if not raw or not isinstance(raw, str):
        return "lead_qualification_rigor"
    slug = raw.strip().lower().replace(" ", "_").replace("-", "_")
    slug = "".join(
        c for c in unicodedata.normalize("NFD", slug)
        if unicodedata.category(c) != "Mn"
    )
    # Try conversion_axis first
    try:
        return normalize_conversion_axis(slug)
    except ValueError:
        pass
    # Fallback para eixos de governança antigos (12 eixos)
    governance_axes = {
        "anti_injection": "anti_injection",
        "lgpd": "lgpd",
        "handoff": "handoff",
        "kill_switch": "kill_switch",
        "privacy": "lgpd",
        "data_protection": "lgpd",
        "human_handoff": "handoff",
        "escalation": "handoff",
        "injection_prevention": "anti_injection",
        "prompt_injection": "anti_injection",
        "emergency_stop": "kill_switch",
        "emergency": "kill_switch",
        "qualification": "qualification",
        "qualificacao": "qualification",
        "closing": "closing",
        "fechamento": "closing",
        "objection": "objection_handling",
        "objecao": "objection_handling",
        "followup": "follow_up",
        "follow_up": "follow_up",
        "seguimento": "follow_up",
    }
    resolved = governance_axes.get(slug, slug)
    if resolved in _CONVERSION_AXES or resolved in governance_axes.values():
        return resolved
    return "lead_qualification_rigor"
