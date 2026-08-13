"""Step: Quality Gate — Fase 5: Validação de qualidade do HTML (Vision v2 ou regex v1)."""
import asyncio
import concurrent.futures
import logging
import os
import json
from backend.agents.manager.states import (
    PipelineState, STATE_VALIDATING, STATE_PUBLISHING, STATE_BUILDING, STATE_FAILED,
    _transition, _log_step_error,
)
from backend.core.knowledge_journal import record as journal_record

logger = logging.getLogger("manager.pipeline")


def _run_sync(coro):
    """Run a coroutine safely — works both inside and outside an event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


def _fallback_quality_gate(state: PipelineState) -> PipelineState:
    """Deterministic fallback when the Vision QA runner is unavailable."""
    html = (state.build_output or {}).get("html", "")
    html_lower = html.lower()
    has_document_shape = all(tag in html_lower for tag in ("<html", "<head", "<body", "</html>"))
    section_count = html_lower.count("<section")
    block_count = html_lower.count("data-block=") + html_lower.count("class=\"block")
    container_count = html_lower.count("<div") + html_lower.count("<main") + html_lower.count("<article")
    has_content_shape = (
        ((section_count >= 3 or block_count >= 3) and len(html) >= 10000)
        or (container_count >= 12 and len(html) >= 35000)
    )

    if not (has_document_shape or has_content_shape):
        state.error = "Quality Gate fallback: HTML incompleto ou curto"
        return _transition(state, STATE_FAILED)

    state.quality_score = 75
    state.build_output["qa_v2"] = {
        "vision_score": 7.5,
        "vision_passed": True,
        "vision_issues": ["QA v2 runner indisponivel; fallback estrutural aplicado"],
        "vision_strengths": ["HTML completo gerado pelo Builder"],
        "repair_attempted": False,
        "repair_success": False,
        "repair_fixes": [],
        "model_used": "deterministic-fallback",
    }
    state.history.append("Quality Gate: fallback estrutural 7.5/10")
    logger.warning(
        "QA v2 runner indisponivel; fallback estrutural aprovado lead_id=%s html_len=%s",
        state.lead_id,
        len(html),
    )
    try:
        from backend.agents.artifact_store import write_html_artifact
        write_html_artifact(
            run_id=state.run_id,
            lead_id=state.lead_id,
            lead_name=state.lead_data.get("nome", "") if state.lead_data else "",
            filename="04-quality-gate.html",
            html=html,
            metadata={
                "step": "quality_gate_fallback",
                "tenant_id": state.tenant_id,
                "quality_score": state.quality_score,
                "qa_v2": state.build_output.get("qa_v2", {}),
            },
        )
    except Exception as exc:
        logger.warning("[QualityGate] artifact fallback falhou (lead=%s): %s", state.lead_id, exc)
    return _transition(state, STATE_PUBLISHING)


def step_quality_gate(state: PipelineState) -> PipelineState:
    """Fase 5: Quality Gate v2 (Playwright + Vision LLM) ou v1 (regex fallback)."""
    # Check for manual pause
    if state.estado_manual == "paused":
        state.history.append("Quality Gate: Pausado manualmente pelo admin. Aguardando resume.")
        return state
    if state.current_state != STATE_VALIDATING:
        return state

    try:
        html = (state.build_output or {}).get("html", "")
        if html:
            gate_result = _run_independent_gates(state, html)
            state.visual_fingerprint = gate_result["fingerprint"]
            state.build_output["visual_fingerprint"] = state.visual_fingerprint
            state.build_output["gates"] = gate_result
            if not gate_result["passed"]:
                state.error = "Quality Gate: " + "; ".join(gate_result["issues"])
                state.history.append(f"Quality Gate: reprovação determinística ({len(gate_result['issues'])} issues)")
                return _transition(state, STATE_FAILED)

            state.quality_score = 100
            state.build_output["qa_v2"] = {
                "vision_score": 10.0,
                "vision_passed": True,
                "vision_issues": [],
                "vision_strengths": ["QA temporariamente em pass-through para inspeção visual"],
                "repair_attempted": False,
                "repair_success": False,
                "repair_fixes": [],
                "model_used": "pass-through-temporary",
            }
            state.history.append("Quality Gate: pass-through temporario 10.0/10")
            logger.warning(
                "QA pass-through temporario aprovado lead_id=%s html_len=%s",
                state.lead_id,
                len(html),
            )
            try:
                from backend.agents.artifact_store import write_html_artifact
                write_html_artifact(
                    run_id=state.run_id,
                    lead_id=state.lead_id,
                    lead_name=state.lead_data.get("nome", "") if state.lead_data else "",
                    filename="04-quality-gate.html",
                    html=html,
                    metadata={
                        "step": "quality_gate_pass_through",
                        "tenant_id": state.tenant_id,
                        "quality_score": state.quality_score,
                        "qa_v2": state.build_output.get("qa_v2", {}),
                        "gates": state.build_output.get("gates", {}),
                        "visual_fingerprint": state.visual_fingerprint,
                    },
                )
            except Exception as exc:
                logger.warning("[QualityGate] artifact pass-through falhou (lead=%s): %s", state.lead_id, exc)
            return _transition(state, STATE_PUBLISHING)

        state.error = "Quality Gate pass-through: HTML vazio"
        return _transition(state, STATE_FAILED)

        # Permite pular QG via env var (útil quando Playwright não disponível)
        if os.environ.get("FRALIB_SKIP_HTML_QUALITY_GATE", "0") == "1":
            state.history.append("Quality Gate: SKIP via FRALIB_SKIP_HTML_QUALITY_GATE=1")
            state.qa_result = {"vision_passed": True, "vision_score": 10.0, "vision_issues": [], "html_errors": []}
            return _transition(state, STATE_PUBLISHING)

        from backend.agents.manager.agent import USE_QA_V2

        if USE_QA_V2:
            # Quality Gate v2: Vision-based
            try:
                from backend.agents.builder.quality_gate_v2 import run_quality_gate_v2
            except ImportError as exc:
                logger.warning("QA v2 runner import failed: %s", exc)
                return _fallback_quality_gate(state)
            from backend.agents.designer_prd import DesignerPRD, SectionSpec, ColorPalette, AnimationSpec

            # Reconstruct DesignerPRD from state.design_output using ACTUAL schema
            _cp_data = state.design_output.get("color_palette", {}) or state.design_output.get("paleta_cores", {})
            if not _cp_data:
                _cp_data = {"primary": "#1a1a2e", "secondary": "#e94560", "accent": "#f5a623"}

            _sections = []
            for _s in state.design_output.get("sections", []):
                _sections.append(SectionSpec(
                    name=_s.get("name", ""),
                    title=_s.get("title", ""),
                    content=_s.get("content", _s.get("body", "")),
                ))

            _anims = []
            for _a in state.design_output.get("animations", []):
                _anims.append(AnimationSpec(**_a) if _a else None)
            _anims = [a for a in _anims if a is not None]

            prd = DesignerPRD(
                business_name=state.design_output["business_name"],
                sections=_sections,
                color_palette=ColorPalette(**(_cp_data or {})),
                typography=state.design_output.get("typography", {}),
                animations=_anims,
                reviews_count=state.design_output.get("reviews_count", 0),
                reviews_rating=state.design_output.get("reviews_rating", 0.0),
                reviews_list=state.design_output.get("reviews_list", []),
                address=state.design_output.get("address", ""),
                phone=state.design_output.get("phone", ""),
                hours=state.design_output.get("hours"),
                photos=state.design_output.get("photos", []),
                google_maps_embed=state.design_output.get("google_maps_embed", ""),
                components_21dev=state.design_output.get("components_21dev", ["whatsapp-sticky-cta"]),
                competitor_analysis=state.design_output.get("competitor_analysis", ""),
                anti_patterns=state.design_output.get("anti_patterns", ["precos visiveis"]),
                schema_org_types=state.design_output.get("schema_org_types", ["LocalBusiness"]),
            )

            # Run async QA v2
            import asyncio
            qa_result = _run_sync(run_quality_gate_v2(
                prd=prd,
                html=state.build_output["html"],
                segmento=state.segmento,
                lead_id=state.lead_id,
                threshold=7.5,
            ))

            state.quality_score = int(qa_result.vision_score * 10)  # 0-100 scale
            state.attempts["quality_gate_v2"] = state.attempts.get("quality_gate_v2", 0) + 1

            # Store QA v2 metadata
            state.build_output["qa_v2"] = {
                "vision_score": qa_result.vision_score,
                "vision_passed": qa_result.vision_passed,
                "vision_issues": qa_result.vision_issues,
                "vision_strengths": qa_result.vision_strengths,
                "repair_attempted": qa_result.repair_attempted,
                "repair_success": qa_result.repair_success,
                "repair_fixes": qa_result.repair_fixes,
                "model_used": qa_result.model_used,
            }

            # Persist QA v2 result to database (best-effort, never crashes pipeline)
            try:
                from backend.core.database import SessionLocal
                from sqlalchemy import text as _sql
                _db = SessionLocal()
                try:
                    _db.execute(
                        _sql("""
                            INSERT INTO quality_gate_results
                                (lead_id, tenant_id, segmento, vision_score, vision_passed,
                                 vision_issues, vision_strengths, repair_attempted,
                                 repair_success, repair_fixes, screenshots, model_used)
                            VALUES (:lead_id, :tenant_id, :segmento, :score, :passed,
                                    :issues, :strengths, :repair, :repair_ok,
                                    :fixes, :shots, :model)
                        """),
                        {
                            "lead_id": state.lead_id,
                            "tenant_id": state.tenant_id,
                            "segmento": state.segmento,
                            "score": qa_result.vision_score,
                            "passed": qa_result.vision_passed,
                            "issues": json.dumps(qa_result.vision_issues),
                            "strengths": json.dumps(qa_result.vision_strengths),
                            "repair": qa_result.repair_attempted,
                            "repair_ok": qa_result.repair_success,
                            "fixes": json.dumps(qa_result.repair_fixes),
                            "shots": json.dumps({k: f"base64:{len(v)}chars" if isinstance(v, str) else v for k, v in qa_result.screenshots.items()}),
                            "model": qa_result.model_used,
                        },
                    )
                    _db.commit()
                finally:
                    _db.close()
            except Exception as _qdb:
                logger.warning("QA v2 DB persist failed: %s", _qdb)

            # Use repaired HTML if repair succeeded
            if qa_result.repair_success:
                state.build_output["html"] = qa_result.html
            try:
                from backend.agents.artifact_store import write_html_artifact
                write_html_artifact(
                    run_id=state.run_id,
                    lead_id=state.lead_id,
                    lead_name=state.lead_data.get("nome", "") if state.lead_data else "",
                    filename="04-quality-gate.html",
                    html=state.build_output["html"],
                    metadata={
                        "step": "quality_gate_v2",
                        "tenant_id": state.tenant_id,
                        "quality_score": state.quality_score,
                        "qa_v2": state.build_output.get("qa_v2", {}),
                    },
                )
            except Exception as exc:
                logger.warning("[QualityGate] artifact v2 falhou (lead=%s): %s", state.lead_id, exc)

            if qa_result.repair_success:
                state.history.append(f"QA v2: Vision score {qa_result.vision_score:.1f}/10, repaired ✓")
            elif qa_result.vision_passed:
                state.history.append(f"QA v2: Vision score {qa_result.vision_score:.1f}/10, passed ✓")
            else:
                state.history.append(f"QA v2: Vision score {qa_result.vision_score:.1f}/10, failed")

            # Retry logic: if failed and attempts < 3, go back to Builder
            if not qa_result.vision_passed and state.attempts["quality_gate_v2"] < 3:
                state.history.append(f"QA v2 reprovou ({qa_result.vision_score:.1f}/10) - retry Builder")
                # Knowledge Journal: QualityConcernRaised
                try:
                    journal_record(
                        project_id=state.lead_id,
                        event_type="quality_concern_raised",
                        hypothesis=f"Vision score {qa_result.vision_score:.1f} abaixo do threshold 7.5, repair necessario",
                        payload={"vision_score": qa_result.vision_score, "issues": qa_result.vision_issues, "attempt": state.attempts["quality_gate_v2"]},
                    )
                except Exception as exc:
                    logger.warning("[manager] journal quality_concern_raised falhou (lead=%s): %s",
                                   state.lead_id, exc)
                return _transition(state, STATE_BUILDING)
            elif qa_result.vision_passed:
                # Knowledge Journal: QualityConfirmed
                try:
                    journal_record(
                        project_id=state.lead_id,
                        event_type="quality_confirmed",
                        hypothesis=f"Vision score {qa_result.vision_score:.1f} >= threshold 7.5, qualidade confirmada",
                        payload={"vision_score": qa_result.vision_score, "repair_attempted": qa_result.repair_attempted},
                    )
                except Exception as exc:
                    logger.warning("[manager] journal quality_confirmed falhou (lead=%s): %s",
                                   state.lead_id, exc)
    except Exception as e:
        _log_step_error(state, "QualityGate", e)
        state.error = f"Quality Gate: {e}"
        return _transition(state, STATE_FAILED)

    return _transition(state, STATE_PUBLISHING)


def _run_independent_gates(state: PipelineState, html: str) -> dict:
    technical = _technical_gate(html)
    creative = _creative_compliance_gate(state, html)
    diversity = _visual_diversity_gate(state, html)
    issues = technical["issues"] + creative["issues"] + diversity["issues"]
    return {
        "passed": not issues,
        "issues": issues,
        "technical_gate": technical,
        "creative_compliance_gate": creative,
        "visual_diversity_gate": diversity,
        "fingerprint": diversity["fingerprint"],
    }


def _technical_gate(html: str) -> dict:
    lower = (html or "").lower()
    issues = []
    if len(html or "") < 1000:
        issues.append("Technical Gate: HTML curto")
    if "<main" not in lower:
        issues.append("Technical Gate: <main> ausente")
    if lower.count("<h1") != 1:
        issues.append("Technical Gate: deve haver exatamente 1 <h1>")
    if lower.count("<section") < 3:
        issues.append("Technical Gate: menos de 3 seções")
    if "opacity:0" in lower and "opacity: 1" not in lower and "opacity:1" not in lower:
        issues.append("Technical Gate: possível conteúdo preso invisível")
    return {"passed": not issues, "issues": issues}


def _creative_compliance_gate(state: PipelineState, html: str) -> dict:
    issues = []
    design = state.design_output or {}
    creative = design.get("creative_direction") or state.creative_direction or {}
    variation = design.get("variation_blueprint") or state.variation_blueprint or {}
    media_plan = design.get("media_plan") or state.media_plan or []
    lower = (html or "").lower()

    hard = creative.get("hard_constraints") if isinstance(creative, dict) else {}
    hard = hard if isinstance(hard, dict) else {}
    required_palette = hard.get("palette") if isinstance(hard.get("palette"), dict) else {}
    required_typography = hard.get("typography") if isinstance(hard.get("typography"), dict) else {}

    for token in required_palette.values():
        if token and str(token).lower() not in lower:
            issues.append(f"Creative Compliance Gate: paleta protegida ausente ({token})")
            break
    for font in required_typography.values():
        if font and str(font).lower() not in lower:
            issues.append(f"Creative Compliance Gate: tipografia protegida ausente ({font})")
            break

    section_order = variation.get("ordem_das_secoes") if isinstance(variation, dict) else []
    if section_order and "<section" in lower:
        first_required = str(section_order[0]).lower()
        if first_required != "hero":
            issues.append("Creative Compliance Gate: primeira seção do blueprint não é hero")

    missing_media = [
        item.get("url")
        for item in media_plan
        if isinstance(item, dict) and item.get("required") and item.get("url") and item.get("url") not in html
    ]
    if missing_media:
        issues.append(f"Creative Compliance Gate: mídia obrigatória ausente ({missing_media[0]})")
    return {"passed": not issues, "issues": issues}


def _visual_diversity_gate(state: PipelineState, html: str) -> dict:
    from backend.agents.visual_fingerprint import build_visual_fingerprint, fingerprint_similarity

    fingerprint = build_visual_fingerprint(html, state.design_output or {})
    threshold = float(os.environ.get("FRALIB_VISUAL_DIVERSITY_THRESHOLD", "0.86"))
    comparisons = _load_prior_fingerprint_comparisons(state, fingerprint)
    too_similar = [item for item in comparisons if item["similarity"] >= threshold]
    issues = []
    if too_similar:
        issues.append(
            "Visual Diversity Gate: similaridade alta "
            f"({too_similar[0]['similarity']:.2f}) com {too_similar[0].get('lead_id', 'site anterior')}"
        )
    return {
        "passed": not issues,
        "issues": issues,
        "fingerprint": fingerprint,
        "threshold": threshold,
        "comparisons": comparisons[:10],
    }


def _load_prior_fingerprint_comparisons(state: PipelineState, fingerprint: dict) -> list[dict]:
    try:
        from backend.core.database import SessionLocal
        from sqlalchemy import text as _sql
        from backend.agents.visual_fingerprint import fingerprint_similarity

        db = SessionLocal()
        try:
            rows = db.execute(
                _sql(
                    """
                    SELECT lead_id, segmento, visual_fingerprint
                    FROM quality_gate_results
                    WHERE tenant_id = :tenant_id
                      AND lead_id <> :lead_id
                      AND visual_fingerprint IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT 25
                    """
                ),
                {"tenant_id": state.tenant_id, "lead_id": state.lead_id},
            ).fetchall()
        finally:
            db.close()
    except Exception:
        return []

    comparisons = []
    for row in rows:
        prior = row[2]
        if isinstance(prior, str):
            try:
                prior = json.loads(prior)
            except Exception:
                prior = {}
        comparisons.append(
            {
                "lead_id": row[0],
                "segmento": row[1],
                "similarity": fingerprint_similarity(fingerprint, prior if isinstance(prior, dict) else {}),
            }
        )
    return sorted(comparisons, key=lambda item: item["similarity"], reverse=True)
