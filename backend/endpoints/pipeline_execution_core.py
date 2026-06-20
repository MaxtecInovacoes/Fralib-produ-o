"""Core execution helper for pipeline phase 2+ flows."""

from __future__ import annotations

import asyncio
import hashlib
import os
import random
import traceback
import unicodedata
from datetime import datetime

from sqlalchemy import text

from backend.services.builder_worker import copy_builder_dist, render_site_with_builder
from backend.services.pipeline_prd_builder import (
    ensure_prd_contracts as _ensure_prd_contracts,
    ensure_prd_design_reference as _ensure_prd_design_reference,
    ensure_prd_publication_identity as _ensure_prd_publication_identity,
)
from backend.services.pipeline_renderer_support import (
    builder_job_id_for_state as _builder_job_id_for_state,
    persist_failed_renderer_html as _persist_failed_renderer_html,
)


async def execute_pipeline_tail(
    *,
    state,
    tenant_id,
    config,
    logger,
    engine,
    SessionLocal,
    _log,
    _progress,
    _ledger,
    _span,
    _trace,
    _fase_counter,
    _set_llm_context_for_pipeline,
    update_pipeline_state,
    build_prompt_phase_outputs,
    build_franz_outreach_payload,
    build_existing_lead_pipeline_config=None,
    publish_rendered_site=None,
    copy_builder_dist=None,
    _ensure_prd_publication_identity=None,
    _ensure_prd_design_reference=None,
    _ensure_prd_contracts=None,
    _build_prompt_agent_prd=None,
    _build_skill_fast_prd=None,
    _build_master_prd=None,
    _visual_archetype_id=None,
    _builder_job_id_for_state=None,
    render_site_with_builder=None,
    _persist_failed_renderer_html=None,
    _skip_html_quality_gate=None,
    _tenant_sdr_allowed=None,
    trial_credit_waits_for_sdr_delivery=None,
    consumir_credito_diario=None,
    salvar_checkpoint=None,
    get_dados_agente=None,
    limpar_checkpoint=None,
    maybe_schedule_autorun_next_lead=None,
    _COOLDOWN_POR_PLANO=None,
    executar_pipeline_lead_existente=None,
    _is_renderer_or_publication_error=None,
    _emitir_erro_pipeline=None,
):
    # This helper is intentionally thin in surface: it owns the final phases.
    _ledger_phase_status = "concluida"
    _prompt_agent_flow = config.get("_prompt_agent_flow", False)
    _builder_fast_path = config.get("_builder_fast_path", False)
    _renderer_agent = "builder_renderer"
    _renderer_label = "BUILDER RENDERER"
    _progress(9, "Gerando site no Builder...")
    _log(f"FASE 9: {_renderer_label}", "info")
    if _ledger:
        _ledger.registrar_fim_fase(8, _ledger_phase_status, resultado="PRD gerado")
        _ledger.registrar_inicio_fase(9, _renderer_agent, modelo=os.getenv("FRALIB_BUILDER_MODEL", "sonnet"))
    if not state.prd_arquiteto:
        raise Exception(f"PRD nao disponivel para {_renderer_agent}")
    _renderer_cached = None if config.get("_forcar_renovacao") or config.get("_cold_run") else get_dados_agente(state.pipeline_id, _renderer_agent)
    if _renderer_cached and _renderer_cached.get("html_final") and len(_renderer_cached["html_final"]) >= 500:
        state.html_final = _renderer_cached["html_final"]
    else:
        if not hasattr(state.prd_arquiteto, "segmento") or not state.prd_arquiteto.segmento:
            state.prd_arquiteto.segmento = state.segmento
        if hasattr(state.prd_arquiteto, "photos") and not state.prd_arquiteto.photos:
            state.prd_arquiteto.photos = state.lead_raw_data.get("fotos") or []
        def _gerar_html_renderer(_validation_errors: str = "", _previous_html: str = ""):
            _repair_context = None
            _repair_hash = ""
            if _validation_errors or _previous_html:
                _repair_context = {"validation_errors": _validation_errors, "previous_html": _previous_html}
                _repair_hash = hashlib.sha1(f"{_validation_errors}\n{_previous_html[:2000]}".encode("utf-8", errors="ignore")).hexdigest()[:10]
            _job_id = _builder_job_id_for_state(state, config, _repair_hash)
            _result = render_site_with_builder(
                state.prd_arquiteto,
                tenant_id=tenant_id,
                job_id=_job_id,
                repair_context=_repair_context,
                publication_url=f"https://seunegociofralib.site/sites/{tenant_id}/{state.lead_slug}/",
            )
            state.builder_output_dir = _result.get("output_dir", "")
            state.builder_manifest_path = _result.get("manifest_path", "")
            return _result["html"]
        state.html_final = _gerar_html_renderer()
        if not _skip_html_quality_gate(config):
            pass
    _progress(10, "Publicando site...")
    _log("FASE 10: DEPLOY", "info")
    web_dir = f"/var/www/fralib/sites/{tenant_id}/{state.lead_slug}"
    publish_rendered_site(
        state=state,
        tenant_id=tenant_id,
        web_dir=web_dir,
        copy_builder_dist=copy_builder_dist,
        gerar_sitemap_robots=__import__("backend.agents.html_publication_helpers", fromlist=["gerar_sitemap_robots"]).gerar_sitemap_robots,
        logger_warning=logger.warning,
    )
    state.site_url = f"https://seunegociofralib.site/sites/{tenant_id}/{state.lead_slug}/"
    _progress(11, "Enviando contato...")
    _log("FASE 11: FRANZ", "info")
    _sdr_stage_final = "pending_sdr_send"
    _sdr_allowed = False
    _skip_franz = bool(config.get("_skip_franz_outreach"))
    if _skip_franz:
        _sdr_stage_final = "manual_test_no_wpp"
        _log("  Franz: pulado por teste controlado sem WhatsApp", "info")
    else:
        try:
            with SessionLocal() as _db_plan:
                _sdr_allowed = _tenant_sdr_allowed(_db_plan, state.tenant_id)
        except Exception as _sdr_plan_err:
            logger.warning(f"[Pipeline] SDR plan gate falhou fechado: {_sdr_plan_err}")
        if not _sdr_allowed:
            _sdr_stage_final = "blocked_plan"
            _log("  Franz: bloqueado pelo plano atual", "info")
    try:
        if not _skip_franz and _sdr_allowed:
            _franz_payload = build_franz_outreach_payload(state, config)
            with SessionLocal() as _db_franz:
                import job_queue as _jq_franz

                _jq_franz.enqueue(
                    _db_franz,
                    tipo="franz_outreach",
                    payload=_franz_payload,
                    tenant_id=state.tenant_id,
                    max_attempts=5,
                    idempotency_key=f"franz-{state.lead_id}",
                    run_id=state.run_id,
                )
            _log("  Franz: enfileirado como job separado", "info")
            _sdr_stage_final = "pending_sdr_send"
    except Exception as exc:
        logger.warning(f"[Pipeline] Franz enqueue erro (não bloqueia): {exc}")
        _log(f"  Franz: falha ao enfileirar ({exc}). Site gerado OK.", "warning")
        _sdr_stage_final = "sdr_enqueue_failed"
    with engine.connect() as conn:
        conn.execute(
            text("""
                UPDATE leads SET site_url=:url, url_site=:url, processado=true,
                processado_em=:ts, status='concluido', sdr_stage=:stage,
                atualizado_em=:ts, erro_pipeline=NULL
                WHERE id=:id AND user_id=:uid
            """),
            {
                "url": state.site_url,
                "ts": datetime.now().isoformat(),
                "id": state.lead_id,
                "stage": _sdr_stage_final,
                "uid": state.tenant_id,
            },
        )
        conn.commit()
    limpar_checkpoint(state.pipeline_id)
    try:
        with SessionLocal() as _db_cred:
            if trial_credit_waits_for_sdr_delivery(_db_cred, tenant_id):
                print(f"[Pipeline] Trial aguardando envio SDR antes de consumir credito (tenant={tenant_id})")
                _log("  Credito trial aguardando envio Franz confirmado", "info")
            else:
                consumir_credito_diario(_db_cred, tenant_id, state.lead_nome)
                print(f"[Pipeline] Credito diario consumido (tenant={tenant_id})")
    except Exception as _cred_err:
        print(f"[Pipeline] ERRO ao descontar credito: {_cred_err}")
    try:
        from agents.pipeline_checkpoint import limpar_checkpoints_expirados

        limpar_checkpoints_expirados(max_age_hours=24)
    except Exception:
        pass
    maybe_schedule_autorun_next_lead(
        db_factory=SessionLocal,
        tenant_id=tenant_id,
        cooldowns_by_plan=_COOLDOWN_POR_PLANO,
        logger=logger,
        log_fn=_log,
        run_next_lead_fn=executar_pipeline_lead_existente,
    )
    return {"sucesso": True, "site_url": state.site_url, "lead": state.lead_nome}
