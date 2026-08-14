"""Step: Design Director — cria contrato explícito de direção criativa."""
import logging

from backend.agents.manager.states import (
    PipelineState,
    STATE_DIRECTING,
    STATE_VARIATING,
    STATE_FAILED,
    _transition,
    _log_step_error,
    _record_visual_custody,
    _record_agent_handoff,
)

logger = logging.getLogger("manager.pipeline")


def step_design_director(state: PipelineState) -> PipelineState:
    if state.current_state != STATE_DIRECTING:
        return state

    try:
        from backend.agents.design_director import gerar_direcao_criativa
        from backend.agents.handoff_types import CreativeDirectionContract

        raw = gerar_direcao_criativa(
            nicho=state.segmento,
            cidade=state.cidade,
            nome_negocio=(state.lead_data or {}).get("nome", ""),
            briefing_nicho=state.niche_brief or {},
            rating=float((state.lead_data or {}).get("rating") or 0),
            segment=state.segmento,
            tier=getattr(state.caio_output, "tier", "STANDARD") if state.caio_output else "STANDARD",
            dados_lead=state.lead_data or {},
        )
        contract = _normalize_creative_direction(raw, state)
        state.creative_direction = contract.model_dump() if hasattr(contract, "model_dump") else contract.dict()
        state.history.append("Design Director: creative direction OK")
        _record_visual_custody(
            state,
            "creative_direction",
            received_decisions={
                "niche_brief": bool(state.niche_brief),
                "audience": (state.niche_brief or {}).get("publico_alvo", []),
                "positioning": (state.niche_brief or {}).get("usp", []),
            },
            preserved_decisions={
                "visual_concept": state.creative_direction.get("visual_concept", ""),
                "color_strategy": state.creative_direction.get("color_strategy", {}),
                "typography_strategy": state.creative_direction.get("typography_strategy", {}),
                "hero_strategy": state.creative_direction.get("hero_strategy", ""),
            },
        )
        _record_agent_handoff(
            state,
            "creative_direction",
            received={
                "niche_brief": state.niche_brief or {},
                "caio_tier": getattr(state.caio_output, "tier", None) if state.caio_output else None,
                "caio_score": getattr(state.caio_output, "score", None) if state.caio_output else None,
            },
            produced=state.creative_direction,
            preserved={
                "visual_concept": state.creative_direction.get("visual_concept", ""),
                "palette": state.creative_direction.get("hard_constraints", {}).get("palette", {}),
                "typography": state.creative_direction.get("hard_constraints", {}).get("typography", {}),
                "anti_patterns": state.creative_direction.get("anti_patterns", []),
            },
        )
        _write_artifact(state, "03-creative-direction.json", state.creative_direction, "creative_direction")
    except Exception as exc:
        _log_step_error(state, "DesignDirector", exc)
        state.error = f"Design Director: {exc}"
        return _transition(state, STATE_FAILED)

    return _transition(state, STATE_VARIATING)


def _normalize_creative_direction(raw: dict, state: PipelineState):
    from backend.agents.handoff_types import CreativeDirectionContract

    raw = raw if isinstance(raw, dict) else {}
    visual = raw.get("direcao_visual", {}) if isinstance(raw, dict) else {}
    motion = raw.get("motion_style", {}) if isinstance(raw, dict) else {}
    voice = raw.get("tom_de_voz", {}) if isinstance(raw, dict) else {}
    structure = raw.get("estrutura_unica", {}) if isinstance(raw, dict) else {}
    anti = raw.get("anti_repeticao", {}) if isinstance(raw, dict) else {}
    tokens = raw.get("design_tokens", {}) if isinstance(raw, dict) else {}
    token_data = (tokens or {}).get("tokens") if isinstance(tokens, dict) else {}
    font_heading = (tokens or {}).get("font_heading") if isinstance(tokens, dict) else ""
    font_body = (tokens or {}).get("font_body") if isinstance(tokens, dict) else ""
    business_name = (state.lead_data or {}).get("nome", "")
    audience = ", ".join((state.niche_brief or {}).get("publico_alvo", [])[:4])
    positioning = ", ".join((state.niche_brief or {}).get("usp", [])[:4])
    visual_concept = visual.get("estilo") or (tokens or {}).get("vibe") or state.segmento

    return CreativeDirectionContract(
        task_id=state.run_id,
        source_agent="design_director",
        target_agent="agente_variacao",
        task_summary=f"Direção criativa para {business_name}",
        brand_concept=business_name,
        audience=audience,
        positioning=positioning,
        commercial_thesis=structure.get("diferenciador_local", positioning),
        visual_concept=visual_concept,
        visual_keywords=[item for item in [visual.get("estilo"), (tokens or {}).get("vibe"), state.segmento] if item],
        physical_scene=_physical_scene(state, visual_concept),
        color_strategy={
            "primary": visual.get("paleta_primaria") or token_data.get("--fg", ""),
            "secondary": visual.get("paleta_secundaria") or token_data.get("--surface", ""),
            "accent": visual.get("paleta_acento") or token_data.get("--accent", ""),
            "tokens_oklch": token_data or {},
        },
        typography_strategy={
            "heading": visual.get("fonte_titulo") or font_heading,
            "body": visual.get("fonte_corpo") or font_body,
        },
        photography_strategy={
            "policy": "usar URLs reais do media_plan com papeis por seção",
            "hero": "imagem dominante coerente com a cena física",
        },
        composition_strategy=", ".join(structure.get("ordem_secoes", [])) if isinstance(structure.get("ordem_secoes"), list) else str(structure.get("ordem_secoes", "")),
        density_strategy=motion.get("intensidade", ""),
        rhythm_strategy=motion.get("efeito_principal", ""),
        hero_strategy=structure.get("template_hero", "") or (tokens or {}).get("hero_style", {}).get("layout", ""),
        cta_strategy=structure.get("cta_principal", ""),
        signature_section=structure.get("diferenciador_local", ""),
        anti_patterns=list(anti.get("evitar", [])) if isinstance(anti, dict) else [],
        required_visual_differences=list(anti.get("inspiracoes", [])) if isinstance(anti, dict) else [],
        hard_constraints={
            "visual_concept": visual_concept,
            "palette": token_data or visual,
            "typography": {"heading": visual.get("fonte_titulo") or font_heading, "body": visual.get("fonte_corpo") or font_body},
            "hero_strategy": structure.get("template_hero", ""),
            "anti_patterns": list(anti.get("evitar", [])) if isinstance(anti, dict) else [],
        },
        soft_constraints={
            "motion": motion,
            "voice": voice,
            "inspirations": list(anti.get("inspiracoes", [])) if isinstance(anti, dict) else [],
        },
    )


def _physical_scene(state: PipelineState, visual_concept: str) -> str:
    name = (state.lead_data or {}).get("nome", "negócio local")
    return f"{name} em {state.cidade}: {state.segmento} com atmosfera {visual_concept}."


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
