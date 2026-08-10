"""Step: Quality Gate — Fase 5: Validação de qualidade do HTML (Vision v2 ou regex v1)."""
import logging
import os
import json
from backend.agents.manager.states import (
    PipelineState, STATE_VALIDATING, STATE_PUBLISHING, STATE_BUILDING, STATE_FAILED,
    _transition, _log_step_error,
)
from backend.core.knowledge_journal import record as journal_record

logger = logging.getLogger("manager.pipeline")


def step_quality_gate(state: PipelineState) -> PipelineState:
    """Fase 5: Quality Gate v2 (Playwright + Vision LLM) ou v1 (regex fallback)."""
    # Check for manual pause
    if state.estado_manual == "paused":
        state.history.append("Quality Gate: Pausado manualmente pelo admin. Aguardando resume.")
        return state
    if state.current_state != STATE_VALIDATING:
        return state

    try:
        # Permite pular QG via env var (útil quando Playwright não disponível)
        if os.environ.get("FRALIB_SKIP_HTML_QUALITY_GATE", "0") == "1":
            state.history.append("Quality Gate: SKIP via FRALIB_SKIP_HTML_QUALITY_GATE=1")
            state.qa_result = {"vision_passed": True, "vision_score": 10.0, "vision_issues": [], "html_errors": []}
            return _transition(state, STATE_PUBLISHING)

        from backend.agents.manager.agent import USE_QA_V2

        if USE_QA_V2:
            # Quality Gate v2: Vision-based
            from backend.agents.builder.quality_gate_v2 import run_quality_gate_v2
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
            qa_result = asyncio.run(run_quality_gate_v2(
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
