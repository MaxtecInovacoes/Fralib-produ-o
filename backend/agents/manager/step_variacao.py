"""Step: Variação — define blueprint estrutural autoritativo."""
import logging

from backend.agents.manager.states import (
    PipelineState,
    STATE_VARIATING,
    STATE_DESIGNING,
    STATE_FAILED,
    _transition,
    _log_step_error,
    _record_visual_custody,
)

logger = logging.getLogger("manager.pipeline")


def step_variacao(state: PipelineState) -> PipelineState:
    if state.current_state != STATE_VARIATING:
        return state

    try:
        from backend.agents.agente_variacao import gerar_variacao
        from backend.agents.handoff_types import NichoBriefing

        briefing = NichoBriefing(**(state.niche_brief or {}))
        variation = gerar_variacao(
            nicho_briefing=briefing,
            concorrentes_raw=(state.lead_data or {}).get("jina_insights", ""),
            task_id=state.run_id,
        )
        blueprint = variation.model_dump() if hasattr(variation, "model_dump") else variation.dict()
        blueprint = _normalize_blueprint(blueprint, state)
        state.variation_blueprint = blueprint
        state.history.append(
            "Variação: blueprint OK "
            f"({blueprint.get('template_hero', '')}/{len(blueprint.get('ordem_das_secoes', []))} seções)"
        )
        _record_visual_custody(
            state,
            "variation_blueprint",
            received_decisions={
                "creative_direction": bool(state.creative_direction),
                "hero_strategy": (state.creative_direction or {}).get("hero_strategy", ""),
                "anti_patterns": (state.creative_direction or {}).get("anti_patterns", []),
            },
            preserved_decisions={
                "hero_type": blueprint.get("template_hero", ""),
                "section_order": blueprint.get("ordem_das_secoes", []),
                "layout_variants": blueprint.get("layout_variants", {}),
                "avoid": blueprint.get("avoid", []),
            },
        )
        _write_artifact(state, "04-variation-blueprint.json", state.variation_blueprint, "variation_blueprint")
    except Exception as exc:
        _log_step_error(state, "Variacao", exc)
        state.error = f"Variação: {exc}"
        return _transition(state, STATE_FAILED)

    return _transition(state, STATE_DESIGNING)


def _normalize_blueprint(blueprint: dict, state: PipelineState) -> dict:
    order = blueprint.get("ordem_das_secoes") or []
    if not isinstance(order, list):
        order = []
    order = [_normalize_section_name(item) for item in order if str(item).strip()]
    if "hero" not in order:
        order.insert(0, "hero")
    if "footer" not in order:
        order.append("footer")
    if not any(item in order for item in ("contato", "contact", "location_contact", "localizacao")):
        order.insert(max(len(order) - 1, 1), "contato")
    blueprint["ordem_das_secoes"] = list(dict.fromkeys(order))
    blueprint.setdefault("layout_variants", {})
    blueprint.setdefault("rhythm", blueprint.get("template_estrutura", ""))
    blueprint.setdefault("signature_composition", blueprint.get("angulo_de_comunicacao", ""))
    avoid = blueprint.get("avoid") or []
    if isinstance(avoid, str):
        avoid = [avoid]
    if blueprint.get("regra_antirrepeticao"):
        avoid.append(blueprint["regra_antirrepeticao"])
    avoid.extend((state.creative_direction or {}).get("anti_patterns", []))
    blueprint["avoid"] = list(dict.fromkeys(str(item) for item in avoid if str(item).strip()))
    return blueprint


def _normalize_section_name(value: str) -> str:
    text = str(value or "").strip().lower().replace("_", "-")
    aliases = {
        "proof": "depoimentos",
        "social-proof": "depoimentos",
        "social_proof": "depoimentos",
        "location": "localizacao",
        "contact": "contato",
        "cta": "contato",
        "cta-final": "contato",
        "method": "sobre",
        "services": "servicos",
    }
    return aliases.get(text, text)


def _write_artifact(state: PipelineState, filename: str, payload: dict, step: str) -> None:
    try:
        from backend.agents.artifact_store import write_json_artifact

        write_json_artifact(
            run_id=state.run_id,
            lead_id=state.lead_id,
            lead_name=(state.lead_data or {}).get("nome", ""),
            filename=filename,
            payload=payload,
            metadata={"step": step, "tenant_id": state.tenant_id},
        )
    except Exception as exc:
        logger.warning("[%s] artifact falhou (lead=%s): %s", step, state.lead_id, exc)
