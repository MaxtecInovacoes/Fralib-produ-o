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
    _record_agent_handoff,
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
        _record_agent_handoff(
            state,
            "variation_blueprint",
            received={
                "niche_brief": state.niche_brief or {},
                "creative_direction": state.creative_direction or {},
            },
            produced=state.variation_blueprint,
            preserved={
                "section_order": state.variation_blueprint.get("ordem_das_secoes", []),
                "hero_type": state.variation_blueprint.get("template_hero", ""),
                "avoid": state.variation_blueprint.get("avoid", []),
            },
        )
        _write_artifact(state, "04-variation-blueprint.json", state.variation_blueprint, "variation_blueprint")
    except Exception as exc:
        _log_step_error(state, "Variacao", exc)
        state.error = f"Variação: {exc}"
        return _transition(state, STATE_FAILED)

    return _transition(state, STATE_DESIGNING)


def _normalize_blueprint(blueprint: dict, state: PipelineState) -> dict:
    _enforce_dark_bold_variation(blueprint, state)
    order = blueprint.get("ordem_das_secoes") or []
    if not isinstance(order, list):
        order = []
    order = [_normalize_section_name(item) for item in order if str(item).strip()]
    order = _enforce_aida_order(order, state)
    blueprint["ordem_das_secoes"] = list(dict.fromkeys(order))
    blueprint["narrative_framework"] = "AIDA"
    blueprint["required_sections"] = ["hero", "interesse", "desejo", "acao", "faq", "lgpd", "footer"]
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


def _enforce_dark_bold_variation(blueprint: dict, state: PipelineState) -> None:
    segment = str(state.segmento or "").lower()
    creative = state.creative_direction or {}
    concept = str(creative.get("visual_concept", "") or "").lower()
    hard_concept = str((creative.get("hard_constraints") or {}).get("visual_concept", "") or "").lower()
    is_dark_niche = any(token in segment for token in ("academia", "fitness", "gym", "barbearia", "barber", "balada", "bar"))
    is_bold_direction = any(token in f"{concept} {hard_concept}" for token in ("bold", "dark", "industrial", "brutalist", "gymshark", "nike"))
    if not (is_dark_niche or is_bold_direction):
        return
    if str(blueprint.get("template_estrutura", "")).lower() in {"corporate", "minimal", ""}:
        blueprint["template_estrutura"] = "brutalist"
    if str(blueprint.get("template_hero", "")).lower() in {"hero-split", "hero-center", ""}:
        blueprint["template_hero"] = "hero-full-bleed"
    blueprint["dark_mode_required"] = True
    blueprint["surface_policy"] = "dark-only: all sections use var(--bg) or var(--surface) with var(--fg); never white backgrounds"


def _enforce_aida_order(order: list[str], state: PipelineState) -> list[str]:
    normalized = [_normalize_section_name(item) for item in order if str(item).strip()]
    if "hero" in normalized:
        normalized = ["hero"] + [item for item in normalized if item != "hero"]
    else:
        normalized.insert(0, "hero")

    required_middle = ["interesse", "desejo"]
    if (state.lead_data or {}).get("servicos") and "servicos" not in normalized:
        required_middle.insert(1, "servicos")
    if (state.lead_data or {}).get("reviews") and not any(item in normalized for item in ("depoimentos", "prova-social")):
        required_middle.append("depoimentos")
    if not any(item in normalized for item in ("seo-geo", "localizacao", "location_contact")):
        required_middle.append("seo-geo")

    tail = ["faq", "acao", "lgpd", "footer"]
    body = [item for item in normalized if item not in {"hero", *required_middle, *tail, "contato", "contact", "cta-final"}]
    result = ["hero"]
    for item in required_middle + body + tail:
        if item not in result:
            result.append(item)
    return result


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
        "contato": "acao",
        "contact": "acao",
        "location_contact": "acao",
        "atenção": "hero",
        "atencao": "hero",
        "attention": "hero",
        "interest": "interesse",
        "desejo": "desejo",
        "desire": "desejo",
        "ação": "acao",
        "acao": "acao",
        "action": "acao",
        "social-proof": "depoimentos",
        "prova_social": "depoimentos",
        "prova-social": "depoimentos",
        "geo": "seo-geo",
        "seo_geo": "seo-geo",
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
