"""Manager agent — orquestrador supervisor (FSM pura em Python).

Coordena a esteira canonica:
  Hunter → Caio → Arquiteto → Builder → Quality Gate v2 (Vision) → Deploy → Franz

Cada agente retorna output estruturado. O Manager valida, decide retry ou avança.
State central persiste entre transições (em memória por enquanto).
"""

from dataclasses import dataclass, field
from typing import Optional
import logging
import traceback
import sys
import os
import json
import time

from backend.core.knowledge_journal import record as journal_record


logger = logging.getLogger("manager.pipeline")

# Feature flag: usa Quality Gate v2 (Playwright + Vision) em vez do v1 (regex)
USE_QA_V2 = os.getenv("FRALIB_QA_V2", "true").lower() in ("1", "true", "yes")


# Estados da FSM
STATE_INIT = "init"
STATE_HUNTING = "hunting"
STATE_QUALIFYING = "qualifying"
STATE_DESIGNING = "designing"
STATE_BUILDING = "building"
STATE_VALIDATING = "validating"
STATE_PUBLISHING = "publishing"
STATE_OUTREACH = "outreach"
STATE_DONE = "done"
STATE_FAILED = "failed"


@dataclass
class PipelineState:
    """Estado central da run."""
    tenant_id: int = 0
    run_id: str = ""
    lead_id: str = ""
    job_id: int = 0  # job queue ID for cost tracking
    segmento: str = ""
    cidade: str = ""
    lead_data: dict = field(default_factory=dict)

    # Outputs dos agentes
    caio_output: Optional[dict] = None
    design_output: Optional[dict] = None
    build_output: Optional[dict] = None
    quality_score: int = 0
    deploy_url: str = ""
    deploy_path: str = ""

    # Controle
    current_state: str = STATE_INIT
    history: list[str] = field(default_factory=list)
    error: str = ""
    error_step: str = ""  # step name that set the error (for pipeline_error_log)
    attempts: dict = field(default_factory=dict)

    # Controle administrativo adicional
    estado_manual: str = ""  # "running" / "paused" / "idle"
    paused_by: Optional[str] = None


def _transition(state: PipelineState, new_state: str) -> PipelineState:
    """Move para novo estado e loga no histórico."""
    state.history.append(f"{state.current_state} → {new_state}")
    state.current_state = new_state
    return state


def _validate_required_fields(data: dict, required: list[str]) -> tuple[bool, str]:
    """Valida que campos obrigatórios estão presentes."""
    missing = [f for f in required if not data.get(f)]
    if missing:
        return False, f"campos faltando: {', '.join(missing)}"
    return True, ""


def step_hunter(state: PipelineState) -> PipelineState:
    """Fase 1: Hunter captura leads."""
    if state.current_state != STATE_INIT:
        return state
    state = _transition(state, STATE_HUNTING)

    # Em produção: chamar get_agent().search()
    # Aqui validamos o que já temos
    if not state.lead_data:
        state.error = "Hunter sem lead"
        return _transition(state, STATE_FAILED)

    ok, msg = _validate_required_fields(
        state.lead_data, ["nome", "cidade", "telefone"]
    )
    if not ok:
        state.error = f"Hunter: {msg}"
        return _transition(state, STATE_FAILED)

    # Knowledge Journal: MarketOpportunityDiscovered
    # Se o lead_data já tem market_intelligence (veio do Hunter real), registra
    if state.lead_data.get("market_intelligence"):
        try:
            mi = state.lead_data["market_intelligence"]
            insights = mi.get("strategic_insights", [])
            journal_record(
                project_id=state.lead_id,
                event_type="market_analyzed",
                hypothesis=f"Oportunidade de mercado identificada para {state.segmento} em {state.cidade}: {insights[0] if insights else 'segmento com baixa presença digital'}",
                payload={"segmento": state.segmento, "cidade": state.cidade, "insights_count": len(insights)},
            )
        except Exception:
            pass

    return _transition(state, STATE_QUALIFYING)


def step_caio(state: PipelineState) -> PipelineState:
    """Fase 2: Caio qualifica."""
    if state.current_state != STATE_QUALIFYING:
        return state

    try:
        from backend.agents.caio.agent import LeadInput, qualificar
        lead_data = state.lead_data
        lead = LeadInput(
            nome=lead_data.get("nome", ""),
            cidade=lead_data.get("cidade", ""),
            segmento=state.segmento or lead_data.get("segmento", ""),
            telefone=lead_data.get("telefone", "") or "",
            whatsapp=lead_data.get("whatsapp", "") or "",
            website=lead_data.get("website", "") or "",
            rating=float(lead_data.get("rating") or 0),
            reviews_count=int(lead_data.get("reviews_count") or lead_data.get("total_avaliacoes") or 0),
            fotos=lead_data.get("fotos") or [],
        )
        out = qualificar(lead)
        state.caio_output = {
            "tier": out.tier, "score": out.score,
            "motivo": out.motivo, "qualificado": out.qualificado,
            "paleta": out.paleta_cores,
        }
    except Exception as e:
        _log_step_error(state, "Caio", e)
        state.error = f"Caio: {e}"
        return _transition(state, STATE_FAILED)

    if not state.caio_output["qualificado"]:
        state.error = f"Lead não qualificado: {state.caio_output['tier']}"
        return _transition(state, STATE_FAILED)

    # Knowledge Journal: LeadQualified
    try:
        journal_record(
            project_id=state.lead_id,
            event_type="lead_qualified",
            hypothesis=f"Lead qualificado como {state.caio_output['tier']} (score {state.caio_output['score']})",
            payload={"tier": state.caio_output["tier"], "score": state.caio_output["score"]},
        )
    except Exception:
        pass

    # RAG: indexar lead após qualificação (best-effort)
    try:
        from backend.core.rag import index_lead
        lead_text = (
            f"{state.lead_data.get('nome', '')} — "
            f"{state.segmento or state.lead_data.get('segmento', '')} em "
            f"{state.cidade or state.lead_data.get('cidade', '')}. "
            f"Tier: {state.caio_output['tier']}, Score: {state.caio_output['score']}. "
            f"Motivo: {state.caio_output['motivo']}"
        )
        index_lead(
            lead_id=state.lead_id,
            tenant_id=state.tenant_id,
            text=lead_text,
            metadata={
                "tier": state.caio_output["tier"],
                "score": state.caio_output["score"],
                "segmento": state.segmento,
                "cidade": state.cidade,
            },
        )
    except Exception:
        pass

    return _transition(state, STATE_DESIGNING)


def _is_transient_llm_error(exc: BaseException) -> bool:
    """Detecta erros transientes do LLM provider que valem retry.

    Rate limit (429), timeout, e erros 5xx passam.
    JSON malformado, campos faltando, ValueError de validacao NAO passam.
    """
    msg = str(exc).lower()
    transient_markers = (
        "429", "rate limit", "ratelimit", "rate_limit",
        "529", "overloaded",
        "timeout", "timed out",
        "502", "503", "504",
        "service unavailable", "bad gateway", "gateway timeout",
        "connection reset", "connection aborted",
        "temporarily unavailable",
    )
    return any(marker in msg for marker in transient_markers)


def step_arquiteto(state: PipelineState) -> PipelineState:
    """Fase 3: Arquiteto gera DesignerPRD. Retry com backoff para erros transientes."""
    if state.current_state != STATE_DESIGNING:
        return state

    from backend.agents.arquiteto.agent import gerar_prd, DesignerPRD, DesignerSection

    # Extrai market_intelligence do lead_data se disponível (vem do Hunter)
    market_intelligence = state.lead_data.get("market_intelligence")

    max_attempts = 3
    backoff_seconds = [5, 15, 45]  # exponential-ish: 5s, 15s, 45s
    state.attempts["arquiteto"] = state.attempts.get("arquiteto", 0)

    last_exc: Exception | None = None
    prd = None

    for attempt in range(1, max_attempts + 1):
        try:
            prd = gerar_prd(state.lead_data, usar_llm=True,
                            market_intelligence=market_intelligence)
            state.attempts["arquiteto"] = attempt
            if attempt > 1:
                state.history.append(
                    f"Arquiteto: sucesso na tentativa {attempt}/{max_attempts} "
                    f"apos retry de erro transiente."
                )
            break
        except Exception as e:
            last_exc = e
            transient = _is_transient_llm_error(e)

            if not transient:
                # Erro estrutural (JSON invalido, campo faltando, etc) NAO vale retry.
                _log_step_error(state, "Arquiteto", e)
                state.error = f"Arquiteto: {e}"
                return _transition(state, STATE_FAILED)

            if attempt < max_attempts:
                wait = backoff_seconds[attempt - 1]
                state.attempts["arquiteto"] = attempt
                state.history.append(
                    f"Arquiteto: erro transiente na tentativa {attempt}/{max_attempts} "
                    f"({type(e).__name__}: {str(e)[:120]}). "
                    f"Aguardando {wait}s antes de retry."
                )
                logger.warning(
                    "Arquiteto transiente (tentativa %d/%d): %s. Retry em %ds.",
                    attempt, max_attempts, e, wait,
                )
                time.sleep(wait)
            else:
                state.attempts["arquiteto"] = attempt
                state.history.append(
                    f"Arquiteto: {max_attempts} tentativas esgotadas em erro transiente. "
                    f"Ultimo erro: {type(e).__name__}: {str(e)[:120]}"
                )

    if prd is None:
        _log_step_error(state, "Arquiteto", last_exc)
        state.error = f"Arquiteto: {last_exc}"
        return _transition(state, STATE_FAILED)

    state.design_output = {
        "business_name": prd.business_name,
        "hero": prd.hero,
        "sections": [{"name": s.name, "title": s.title,
                      "content": s.content} for s in prd.sections],
        "ctas": prd.ctas,
        "faqs": prd.faqs,
        "paleta": prd.paleta,
        # Fase 1: tokens autoritativos via theme_mapper.
        # Esses campos sao injetados no payload do Builder -> OpenUI service.
        "design_tokens": prd.design_tokens,
        "layout_dna": prd.layout_dna,
        # Fase 2: design_system auto-emitido (google_fonts, tailwind.config,
        # forbidden_radius/copy) para o Builder aplicar de forma autoritativa.
        "design_system": prd.design_system,
    }

    # Knowledge Journal: NarrativeLocked + IdentityApproved
    try:
        journal_record(
            project_id=state.lead_id,
            event_type="narrative_locked",
            hypothesis="PRD gerado com promessa, narrativa e estrutura definidas",
            payload={"business_name": prd.business_name, "sections_count": len(prd.sections)},
        )
        journal_record(
            project_id=state.lead_id,
            event_type="identity_approved",
            hypothesis=f"Arquétipo {prd.design_tokens.get('archetype')} com tokens autoritativos",
            payload={"archetype": prd.design_tokens.get("archetype"), "tokens": prd.design_tokens},
        )
    except Exception:
        pass

    return _transition(state, STATE_BUILDING)


def step_builder(state: PipelineState) -> PipelineState:
    """Fase 9: Builder gera HTML."""
    if state.current_state != STATE_BUILDING:
        return state

    try:
        from backend.agents.builder.agent import render_site
        from backend.agents.arquiteto.agent import DesignerPRD, DesignerSection

        prd = DesignerPRD(
            business_name=state.design_output["business_name"],
            cidade=state.cidade,
            segmento=state.segmento,
            hero=state.design_output["hero"],
            sections=[DesignerSection(**s) for s in state.design_output["sections"]],
            ctas=state.design_output["ctas"],
            faqs=state.design_output["faqs"],
            paleta=state.design_output["paleta"],
            # Fase 1/2: tokens autoritativos do Arquiteto. Sem repassar aqui,
            # o OpenUI cai nos defaults editorial-asymmetric + Inter (archetype
            # perdido). design_system carrega archetype/google_fonts_url/briefing.
            design_tokens=state.design_output.get("design_tokens", {}),
            layout_dna=state.design_output.get("layout_dna", {}),
            design_system=state.design_output.get("design_system", {}),
        )
        # Fase 3 SEO/GEO - AGENTE 19 TRUST SIGNALS: propagar rating do lead
        # para o JSON-LD LocalBusiness.aggregateRating do inject.py.
        lead_rating = state.lead_data.get("rating") if state.lead_data else None
        lead_reviews = (
            state.lead_data.get("reviews_count")
            or state.lead_data.get("total_avaliacoes")
        ) if state.lead_data else None
        lead_telefone = (
            state.lead_data.get("telefone")
        ) if state.lead_data else None
        if lead_rating:
            setattr(prd, "_lead_rating", float(lead_rating))
        if lead_reviews:
            setattr(prd, "_lead_reviews_count", int(lead_reviews))
        if lead_telefone:
            # Fase 4 — scrub de placeholder telefonico.
            setattr(prd, "_lead_telefone", str(lead_telefone))
        # Fase 5 — Entity-Placeholder resolution (inject.resolve_entity_tags
        # troca {{business_name}}/etc pelos valores reais, fora do LLM).
        if state.lead_data:
            setattr(prd, "_lead_data", dict(state.lead_data))
        result = render_site(prd, usar_llm=True)
        state.build_output = {"html": result.html, "model": result.model}
    except Exception as e:
        _log_step_error(state, "Builder", e)
        state.error = f"Builder: {e}"
        return _transition(state, STATE_FAILED)

    # Knowledge Journal: ArtifactGenerated
    try:
        journal_record(
            project_id=state.lead_id,
            event_type="artifact_generated",
            hypothesis="HTML gerado pelo Builder a partir do PRD completo",
            payload={"model": state.build_output.get("model", "unknown"), "html_length": len(state.build_output.get("html", ""))},
        )
    except Exception:
        pass

    return _transition(state, STATE_VALIDATING)


def step_quality_gate(state: PipelineState) -> PipelineState:
    """Fase 9b: Quality Gate v2 (Playwright + Vision LLM) ou v1 (regex fallback)."""
    # Check for manual pause - if paused by admin, skip processing
    if state.estado_manual == "paused":
        state.history.append(f"Quality Gate: Pausado manualmente pelo admin. Aguardando resume.")
        return state
    if state.current_state != STATE_VALIDATING:
        return state

    try:
        # Permite pular QG via env var (útil quando Playwright não disponível)
        if os.environ.get("FRALIB_SKIP_HTML_QUALITY_GATE", "0") == "1":
            state.history.append("Quality Gate: SKIP via FRALIB_SKIP_HTML_QUALITY_GATE=1")
            state.qa_result = {"vision_passed": True, "vision_score": 10.0, "vision_issues": [], "html_errors": []}
            return _transition(state, STATE_PUBLISHING)
        if USE_QA_V2:
            # Quality Gate v2: Vision-based
            from backend.agents.builder.quality_gate_v2 import run_quality_gate_v2
            from backend.agents.arquiteto.agent import DesignerPRD, DesignerSection

            # Reconstruct PRD from state.design_output
            prd = DesignerPRD(
                business_name=state.design_output["business_name"],
                cidade=state.cidade,
                segmento=state.segmento,
                hero=state.design_output["hero"],
                sections=[DesignerSection(**s) for s in state.design_output["sections"]],
                ctas=state.design_output["ctas"],
                faqs=state.design_output["faqs"],
                paleta=state.design_output["paleta"],
                design_tokens=state.design_output.get("design_tokens", {}),
                layout_dna=state.design_output.get("layout_dna", {}),
                design_system=state.design_output.get("design_system", {}),
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
                        hypothesis=f"Vision score {qa_result.vision_score:.1f} abaixo do threshold 7.5, repair necessário",
                        payload={"vision_score": qa_result.vision_score, "issues": qa_result.vision_issues, "attempt": state.attempts["quality_gate_v2"]},
                    )
                except Exception:
                    pass
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
                except Exception:
                    pass
    except Exception as e:
        _log_step_error(state, "QualityGate", e)
        state.error = f"Quality Gate: {e}"
        return _transition(state, STATE_FAILED)

    return _transition(state, STATE_PUBLISHING)


def step_deploy(state: PipelineState) -> PipelineState:
    """Fase 10: Deploy publica site em sites/<tenant>/<lead_id>/index.html."""
    if state.current_state != STATE_PUBLISHING:
        return state

    try:
        import os
        from pathlib import Path
        from datetime import datetime

        # Slug a partir do nome do lead
        slug = state.lead_data.get("nome", "site").lower()
        slug = "".join(c if c.isalnum() else "-" for c in slug).strip("-")[:50]
        if not slug:
            slug = "site"

        # Diretório: sites/<tenant_id>/<slug>-<lead_id>/
        sites_root = Path(os.getenv("FRALIB_SITES_ROOT", "sites"))
        site_dir = sites_root / str(state.tenant_id) / f"{slug}-{state.lead_id[:8]}"
        site_dir.mkdir(parents=True, exist_ok=True)

        # Escreve index.html
        index_path = site_dir / "index.html"
        html = state.build_output.get("html", "")

        # Pós-processamento cinematográfico
        try:
            from backend.agents.cinematic_post_processor import process as cinematic_process
            design_tokens = {}
            if state.design_output:
                design_tokens = state.design_output.get("tokens_oklch", {}) or {}
            html = cinematic_process(
                html,
                design_tokens=design_tokens,
                segmento=state.segmento or "",
                nome=state.lead_data.get("nome", "") if state.lead_data else "",
            )
        except Exception as e:
            print(f"[Deploy] Aviso: pos-processamento cinematico falhou: {e}")

        index_path.write_text(html, encoding="utf-8")

        # Metadata
        meta_path = site_dir / "metadata.json"
        import json
        meta_path.write_text(json.dumps({
            "tenant_id": state.tenant_id,
            "lead_id": state.lead_id,
            "slug": slug,
            "lead_name": state.lead_data.get("nome"),
            "cidade": state.cidade,
            "segmento": state.segmento,
            "quality_score": state.quality_score,
            "deployed_at": datetime.now().isoformat(),
            "size_bytes": len(html),
            "paleta": state.design_output.get("paleta", {}) if state.design_output else {},
        }, indent=2, ensure_ascii=False), encoding="utf-8")

        # URL relativa + absoluta
        rel_path = site_dir.relative_to(sites_root)
        state.deploy_url = f"https://seunegociofralib.site/sites/{rel_path}/"
        state.deploy_path = str(site_dir.absolute())
        state.history.append(f"Deploy: salvo em {index_path} ({len(html)} bytes)")

        # Knowledge Journal: ProjectPublished
        try:
            journal_record(
                project_id=state.lead_id,
                event_type="project_published",
                hypothesis=f"Site publicado com quality_score {state.quality_score}, deploy em {state.deploy_url}",
                payload={"deploy_url": state.deploy_url, "quality_score": state.quality_score, "size_bytes": len(html)},
            )
        except Exception:
            pass

        # Persist status=concluido + site_url na tabela leads (fail-soft)
        try:
            from backend.core.database import SessionLocal
            from sqlalchemy import text as _sql
            _db = SessionLocal()
            try:
                _db.execute(
                    _sql("""
                        UPDATE leads SET
                            status = 'concluido',
                            site_url = :url,
                            sdr_stage = 'pendente_wpp',
                            atualizado_em = NOW()
                        WHERE id = :lid AND user_id = :tid
                          AND (status IS NULL OR status NOT IN ('qualificado', 'convertido', 'descartado'))
                    """),
                    {"url": state.deploy_url, "lid": state.lead_id, "tid": state.tenant_id},
                )
                _db.commit()
            except Exception:
                try:
                    _db.rollback()
                except Exception:
                    pass
            finally:
                _db.close()
        except Exception as _pdb:
            logger.error("PIPELINE_DEPLOY_UPDATE_FAILED lead_id=%s tenant_id=%d: %s", state.lead_id, state.tenant_id, _pdb)
    except Exception as e:
        _log_step_error(state, "Deploy", e)
        state.error = f"Deploy falhou: {e}"
        state.history.append(f"Deploy ERRO: {e}")
        return _transition(state, STATE_FAILED)

    return _transition(state, STATE_OUTREACH)


def step_franz(state: PipelineState) -> PipelineState:
    """Fase 11: Franz outreach — delegado ao cron dispatcher (leads WHERE status='concluido' AND sdr_stage='pendente_wpp')."""
    if state.current_state != STATE_OUTREACH:
        return state

    state.history.append(f"Franz: lead marcado como concluido, site_url={state.deploy_url}")
    return _transition(state, STATE_DONE)


# Pipeline completa (lista de steps em ordem)
PIPELINE_STEPS = [
    step_hunter,
    step_caio,
    step_arquiteto,
    step_builder,
    step_quality_gate,
    step_deploy,
    step_franz,
]


def _log_step_error(state: PipelineState, step_name: str, exc: Exception) -> None:
    """Log estruturado de erro com step, exception type, traceback e lead_id.

    Persiste no DB (pipeline_error_log) + stdout.
    Falha de persistencia nunca quebra a pipeline.
    """
    state.error_step = step_name
    logger.error(
        "PIPELINE_ERROR step=%s lead_id=%s tenant_id=%s exception=%s msg=%s",
        step_name,
        state.lead_id,
        state.tenant_id,
        type(exc).__name__,
        str(exc),
    )
    logger.debug(
        "PIPELINE_TRACEBACK step=%s lead_id=%s\n%s",
        step_name,
        state.lead_id,
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    )
    # Persist to DB (best-effort)
    try:
        from backend.core.pipeline_error_log import log_step_error as _db_log

        _db_log(
            lead_id=state.lead_id,
            tenant_id=state.tenant_id,
            step_name=step_name,
            exc=exc,
        )
    except Exception as db_err:
        logger.warning("Pipeline error DB persist failed: %s", db_err)


def run_pipeline(state: PipelineState) -> PipelineState:
    """Executa toda a pipeline com suporte a retry.

    O loop externo (while) permite que o Quality Gate retorne ao Builder
    quando o score for insuficiente. O loop interno (for) percorre os steps
    em ordem. Quando o Quality Gate seta state=BUILDING, o loop externo
    reinicia para que step_builder seja re-executado.

    O Quality Gate tem contador de attempts interno (max 3), entao nao ha
    risco de loop infinito.

    Custo: define RunContext (run_id, job_id, tenant_id, lead_id) no início,
    faz aggregate_pipeline_usage(run_id) no fim (sucesso ou falha).
    """
    # 1. Set RunContext for cost tracking
    from backend.agents.llm.context import set_run_context, RunContext, clear_run_context, update_run_context

    ctx = RunContext(
        run_id=state.run_id,
        job_id=state.job_id if hasattr(state, 'job_id') and state.job_id else None,
        tenant_id=state.tenant_id,
        lead_id=state.lead_id,
        phase="initializing",
        agent="manager",
        metadata={
            "lead_nome": (state.lead_data or {}).get("nome", ""),
            "nicho": state.segmento or (state.lead_data or {}).get("segmento", ""),
        },
    )
    token = set_run_context(ctx)

    try:
        max_passes = 10  # safety contra loop inesperado
        passes = 0
        while state.current_state not in (STATE_DONE, STATE_FAILED) and passes < max_passes:
            passes += 1
            prev_state = state.current_state
            for step in PIPELINE_STEPS:
                state = step(state)
                # Atualiza phase/agent conforme transição do pipeline
                new_state = state.current_state
                if new_state != prev_state:
                    phase_map = {
                        STATE_HUNTING: "hunting",
                        STATE_QUALIFYING: "qualifying",
                        STATE_DESIGNING: "designing",
                        STATE_BUILDING: "building",
                        STATE_VALIDATING: "validating",
                        STATE_OUTREACH: "outreach",
                        STATE_DONE: "done",
                        STATE_FAILED: "failed",
                    }
                    agent_map = {
                        STATE_HUNTING: "hunter",
                        STATE_QUALIFYING: "caio",
                        STATE_DESIGNING: "arquiteto",
                        STATE_BUILDING: "builder",
                        STATE_VALIDATING: "qa_vision",
                        STATE_OUTREACH: "franz",
                        STATE_DONE: "manager",
                        STATE_FAILED: "manager",
                    }
                    _ = update_run_context(
                        phase=phase_map.get(new_state, new_state),
                        agent=agent_map.get(new_state, "manager"),
                    )
                    prev_state = new_state
                if state.current_state in (STATE_DONE, STATE_FAILED):
                    break
        if passes >= max_passes:
            logger.error("run_pipeline esgotou passes (%s) sem completar", max_passes)
            if not state.error:
                state.error = f"pipeline estagnou apos {max_passes} passes"
            state = _transition(state, STATE_FAILED)
        return state
    finally:
        # 2. Aggregate cost at end (sempre, mesmo se falhou)
        try:
            from backend.agents.cost_tracker import aggregate_pipeline_usage
            aggregate_pipeline_usage(state.run_id)
        except Exception as exc:
            logger.warning("[cost_tracker] aggregate no run_pipeline falhou: %s", exc)
        # 2.1 Deduzir créditos por custo real do pipeline (fail-safe)
        try:
            from backend.services.credits_manager import deduzir_creditos_por_pipeline
            from backend.agents.llm.context import current_tenant_id
            tid = current_tenant_id()
            if tid and state.run_id:
                result = deduzir_creditos_por_pipeline(
                    tenant_id=tid,
                    run_id=state.run_id,
                )
                logger.info(
                    "[credits_manager] pipeline run_id=%s tenant_id=%d deduzidos=%d custo_usd=%.4f ok=%s",
                    state.run_id, tid, result.get("deduzidos", 0), result.get("custo_usd", 0.0), result.get("ok"),
                )
        except Exception as exc:
            logger.warning("[credits_manager] deducao no run_pipeline falhou run_id=%s: %s", state.run_id, exc)
        # 2.2 RAG: indexar falha se pipeline falhou (best-effort)
        if state.current_state == STATE_FAILED and state.error:
            try:
                from backend.core.rag import index_failure
                error_step = state.error_step or "unknown"
                index_failure(
                    lead_id=state.lead_id,
                    tenant_id=state.tenant_id,
                    text=f"[{error_step}] {state.error}",
                    step_name=error_step,
                    metadata={
                        "step": error_step,
                        "estado_final": "failed",
                        "run_id": state.run_id,
                    },
                )
            except Exception:
                pass
        # 3. Clear context
        clear_run_context(token)
