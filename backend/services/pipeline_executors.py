"""
Executores de fase e lógica de retry do pipeline FraLib.
"""

import os
import asyncio
import hashlib
import logging
from typing import Any, Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

logger = logging.getLogger("uvicron")


# ─── RETRY HELPER ───────────────────────────────────────────────────────────

def tentar(
    fn: Callable,
    fase: str,
    max_attempts: int = 3,
    base_delay: float = 2.0,
    log_fn: Callable = None,
) -> Any:
    """
    Executa função com retry exponencial em caso de falha.
    """
    from retry_helper import tentar as _original
    return _original(fn, fase, max_attempts, base_delay, log_fn)


# ─── FASE 1: HUNTER + KEYWORD ───────────────────────────────────────────────

async def executar_fase1_hunter(
    state,
    config: dict,
    tenant_id: int,
    leads_existentes: set,
    buscar_leads_google_maps: Callable,
    pesquisar_keywords_nicho: Callable,
    score_minimo: int = 45,
    log_fn: Callable = None,
) -> list:
    """Executa Fase 1: Hunter + Keyword Research em paralelo."""

    # Keyword research em paralelo com o Hunter
    _kw_result = [None]

    def _run_kw():
        try:
            _kw_result[0] = pesquisar_keywords_nicho(state.segmento, state.cidade)
            if log_fn:
                log_fn("  Keywords: OK", "success")
        except Exception as _e:
            logger.warning(f"[Pipeline] Keyword research erro: {_e}")

    _kw_executor = ThreadPoolExecutor(max_workers=1)
    _kw_future = _kw_executor.submit(_run_kw)

    # Executar Hunter
    leads = await buscar_leads_google_maps(
        cidade=state.cidade,
        segmento=state.segmento,
        limite=config.get("_candidate_pool_limit", 10),
        leads_existentes=leads_existentes,
        force_fresh=config.get("force_fresh", False),
        user_id=tenant_id,
        score_minimo=score_minimo,
        aprovados_necessarios=1,
    )

    _kw_future.result(timeout=30)
    _kw_executor.shutdown(wait=False)

    state.keyword_research = _kw_result[0] or ""

    return leads


# ─── FASE 2: CAIO ───────────────────────────────────────────────────────────

async def executar_fase2_caio(
    state,
    caio_input_class,
    qualificar_lead_func: Callable,
    score_minimo: int = 45,
    log_fn: Callable = None,
) -> Any:
    """Executa Fase 2: Qualificação Caio."""

    caio_input = caio_input_class(
        nome=state.lead_nome,
        cidade=state.lead_obj.lead.cidade,
        segmento=state.segmento,
        telefone=state.lead_obj.lead.telefone or "",
        whatsapp=state.lead_obj.lead.whatsapp or "",
        rating=state.lead_obj.lead.rating or 0.0,
        reviews_count=state.lead_obj.lead.total_avaliacoes
        or len(state.lead_obj.lead.reviews or [])
        or 0,
        fotos=state.lead_obj.lead.fotos or [],
        website=state.lead_obj.lead.website,
        reprocessamento=True,
    )

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as ex:
        state.qualificacao_caio = await loop.run_in_executor(ex, qualificar_lead_func, caio_input)

    # Verificar score mínimo
    if (
        state.qualificacao_caio
        and state.qualificacao_caio.qualificado
        and int(getattr(state.qualificacao_caio, "score", 0) or 0) < score_minimo
    ):
        state.qualificacao_caio.qualificado = False
        state.qualificacao_caio.tier = "REJEITADO"
        state.qualificacao_caio.motivo = f"Score abaixo do mínimo ({score_minimo})"

    return state.qualificacao_caio


# ─── FASE 3: JINA ──────────────────────────────────────────────────────────

async def executar_fase3_jina(
    state,
    config: dict,
    buscar_inteligencia_jina: Callable = None,
    formatar_inteligencia: Callable = None,
    pesquisar_referencias_jina: Callable = None,
    pode_usar_cache: Callable = None,
    get_dados_agente: Callable = None,
    salvar_checkpoint: Callable = None,
    validar_output: Callable = None,
    log_fn: Callable = None,
) -> str:
    """Executa Fase 3: Jina AI Intelligence."""

    _use_cache = pode_usar_cache(config) if pode_usar_cache else True

    _jina_cached = None
    if _use_cache and get_dados_agente:
        try:
            _jina_cached = get_dados_agente(state.pipeline_id, "jina")
        except Exception:
            pass

    if _jina_cached and _jina_cached.get("insights"):
        state.jina_insights = _jina_cached["insights"]
        state.jina_intel_dict = _jina_cached.get("intel") or {}
        if log_fn:
            log_fn(f"  Jina: ♻️ retomado do checkpoint ({len(state.jina_insights)} chars)", "success")
    else:
        if buscar_inteligencia_jina:
            try:
                _jina_intel = buscar_inteligencia_jina(
                    nicho=state.segmento,
                    cidade=state.cidade,
                    nome_negocio=state.lead_nome or "",
                    concorrentes_urls=getattr(state, "_concorrentes_urls", None),
                )
                state.jina_intel_dict = _jina_intel
                if formatar_inteligencia:
                    state.jina_insights = formatar_inteligencia(_jina_intel)
                else:
                    state.jina_insights = str(_jina_intel)

                if log_fn:
                    log_fn(f"  Jina Intel: {len(state.jina_insights)} chars", "success")

                if salvar_checkpoint and validar_output:
                    if validar_output(state.jina_insights, min_chars=30):
                        salvar_checkpoint(
                            state.pipeline_id, "jina",
                            {"insights": state.jina_insights, "intel": _jina_intel}
                        )
            except Exception as e:
                logger.warning(f"[Pipeline] Jina Intel erro: {e}")
                # Fallback para Jina antigo
                if pesquisar_referencias_jina:
                    try:
                        state.jina_insights = pesquisar_referencias_jina(
                            state.segmento, cidade=state.cidade
                        )
                        if log_fn:
                            log_fn(f"  Jina (fallback v1): {len(state.jina_insights)} chars", "warning")
                    except Exception as e_jina_fallback:
                        # IMPORTANTE: Jina v1 fallback falhou silenciosamente
                        # SEO do site pode estar incompleto
                        logger.warning(f"[Pipeline] Jina fallback v1 falhou: {e_jina_fallback}")
                        state.jina_insights = ""
        else:
            state.jina_insights = ""

    return state.jina_insights


# ─── FASE 6: AGENTE DE NICHO ────────────────────────────────────────────────

def executar_fase6_nicho(
    state,
    config: dict,
    gerar_briefing_func: Callable,
    pode_usar_cache: Callable,
    get_dados_agente: Callable,
    salvar_checkpoint: Callable,
    _builder_fast_path: bool,
    _prompt_agent_flow: bool,
    log_fn: Callable = None,
):
    """Executa Fase 6: Agente de Nicho."""

    _nicho_cached = None
    if pode_usar_cache(config):
        try:
            _nicho_cached = get_dados_agente(state.pipeline_id, "agente_nicho")
        except Exception:
            pass

    if _builder_fast_path:
        from agents.handoff_types import NichoBriefing
        state.nicho_briefing = NichoBriefing(
            task_id=state.pipeline_id,
            source_agent="pipeline",
            target_agent="builder_renderer",
            nicho=state.segmento or state.lead_obj.lead.segmento or "negocio local",
            cidade=state.cidade or state.lead_obj.lead.cidade or "",
            confianca="media",
        )
        if log_fn:
            msg = "Nicho: pulado; dados seguem direto para o Agente de Prompt" if _prompt_agent_flow else "Nicho: fast-path deterministico"
            log_fn(f"  {msg}", "success")

    elif _nicho_cached and _nicho_cached.get("briefing_json"):
        try:
            from agents.handoff_types import NichoBriefing
            state.nicho_briefing = NichoBriefing(**_nicho_cached["briefing_json"])
            if log_fn:
                log_fn("  Nicho briefing: ♻️ retomado do checkpoint", "success")
        except Exception:
            _nicho_cached = None

    if not _builder_fast_path and (not _nicho_cached or not _nicho_cached.get("briefing_json")):
        _dados_hunter = state.lead_raw_data or {}
        state.nicho_briefing = gerar_briefing_func(
            dados_lead=_dados_hunter,
            segmento=state.segmento,
            cidade=state.cidade,
            jina_insights=state.jina_insights or "",
            task_id=state.pipeline_id,
        )
        if log_fn:
            log_fn(f"  Nicho: {state.nicho_briefing.nicho} | confianca={state.nicho_briefing.confianca}", "success")

        if salvar_checkpoint:
            try:
                salvar_checkpoint(
                    state.pipeline_id, "agente_nicho",
                    {"briefing_json": state.nicho_briefing.model_dump()}
                )
            except Exception:
                pass


# ─── FASE 7: VARIAÇÃO ESTRUTURAL ───────────────────────────────────────────

def executar_fase7_variacao(
    state,
    config: dict,
    gerar_variacao_func: Callable,
    pode_usar_cache: Callable,
    get_dados_agente: Callable,
    salvar_checkpoint: Callable,
    _builder_fast_path: bool,
    _prompt_agent_flow: bool,
    log_fn: Callable = None,
):
    """Executa Fase 7: Variação Estrutural."""

    _var_cached = None
    if pode_usar_cache(config):
        try:
            _var_cached = get_dados_agente(state.pipeline_id, "agente_variacao")
        except Exception:
            pass

    if _builder_fast_path:
        from agents.handoff_types import VariacaoEstrutural
        state.variacao_estrutural = VariacaoEstrutural(
            task_id=state.pipeline_id,
            source_agent="pipeline",
            target_agent="builder_renderer",
            template_estrutura="skill-fast",
            template_hero="renderer-decides",
            ordem_das_secoes=["hero", "sobre", "prova-social", "contato", "footer"],
        )
        if log_fn:
            msg = "Variação: pulada; estrutura sera pedida no prompt final" if _prompt_agent_flow else "Variação: fast-path deterministica"
            log_fn(f"  {msg}", "success")

    elif _var_cached and _var_cached.get("variacao_json"):
        try:
            from agents.handoff_types import VariacaoEstrutural
            state.variacao_estrutural = VariacaoEstrutural(**_var_cached["variacao_json"])
            if log_fn:
                log_fn("  Variação: ♻️ retomado do checkpoint", "success")
        except Exception:
            _var_cached = None

    if not _builder_fast_path and (not _var_cached or not _var_cached.get("variacao_json")):
        _conc_raw = state.jina_insights or ""
        state.variacao_estrutural = gerar_variacao_func(
            nicho_briefing=state.nicho_briefing,
            concorrentes_raw=_conc_raw[:3000],
            task_id=state.pipeline_id,
        )
        if log_fn:
            log_fn(f"  Variação: {state.variacao_estrutural.template_estrutura}/{state.variacao_estrutural.template_hero}", "success")

        if salvar_checkpoint:
            try:
                salvar_checkpoint(
                    state.pipeline_id, "agente_variacao",
                    {"variacao_json": state.variacao_estrutural.model_dump()}
                )
            except Exception:
                pass


# ─── FASE 9: BUILDER/RENDERER ──────────────────────────────────────────────

def gerar_html_renderer(
    state,
    config: dict,
    prd_arquiteto,
    tenant_id: int,
    render_site_with_builder: Callable,
    builder_job_id_for_state: Callable = None,
    validation_errors: str = "",
    previous_html: str = "",
    publication_url: str = "",
) -> str:
    """Executa Fase 9: Geração HTML via Builder/Renderer."""

    _repair_context = None
    _repair_hash = ""
    if validation_errors or previous_html:
        _repair_context = {
            "validation_errors": validation_errors,
            "previous_html": previous_html,
        }
        _repair_hash = hashlib.sha1(
            f"{validation_errors}\n{previous_html[:2000]}".encode("utf-8", errors="ignore")
        ).hexdigest()[:10]

    _job_id = builder_job_id_for_state(state, config, _repair_hash) if builder_job_id_for_state else None

    _result = render_site_with_builder(
        prd_arquiteto,
        tenant_id=tenant_id,
        job_id=_job_id,
        repair_context=_repair_context,
        publication_url=publication_url or f"https://seunegociofralib.site/sites/{tenant_id}/{state.lead_slug}/",
    )

    state.builder_output_dir = _result.get("output_dir", "")
    state.builder_manifest_path = _result.get("manifest_path", "")

    return _result["html"]


# ─── FASE 10: DEPLOY ─────────────────────────────────────────────────────────

def executar_fase10_deploy(
    state,
    tenant_id: int,
    copy_builder_dist: Callable,
    web_dir_base: str = "/var/www/fralib/sites",
    log_fn: Callable = None,
) -> str:
    """Executa Fase 10: Deploy do site."""

    web_dir = f"{web_dir_base}/{tenant_id}/{state.lead_slug}"
    os.makedirs(web_dir, exist_ok=True)

    # Copiar assets do builder se existir
    if state.builder_output_dir:
        copy_builder_dist(state.builder_output_dir, web_dir)

    # Salvar HTML
    with open(f"{web_dir}/index.html", "w", encoding="utf-8") as _f:
        _f.write(state.html_final)

    # Permissões
    import subprocess as _sp
    _sp.run(["chown", "-R", "www-data:www-data", web_dir], check=False)
    _sp.run(["chmod", "-R", "755", web_dir], check=False)

    state.site_url = f"https://seunegociofralib.site/sites/{tenant_id}/{state.lead_slug}/"

    if log_fn:
        log_fn(f"  Deploy: {state.site_url}", "success")

    return state.site_url


# ─── FASE 11: FRANZ/SDR ─────────────────────────────────────────────────────

def executar_fase11_franz(
    state,
    config: dict,
    tenant_id: int,
    tenant_sdr_allowed: Callable,
    db_session_factory,
    job_queue_module,
    log_fn: Callable = None,
) -> tuple:
    """
    Executa Fase 11: Franz/SDR Outreach.
    Retorna (sdr_stage_final, sdr_allowed).
    """

    _sdr_stage_final = "pending_sdr_send"
    _sdr_allowed = False
    _skip_franz = bool(config.get("_skip_franz_outreach"))

    if _skip_franz:
        _sdr_stage_final = "manual_test_no_wpp"
        if log_fn:
            log_fn("  Franz: pulado por teste controlado sem WhatsApp", "info")
        return _sdr_stage_final, _sdr_allowed

    # Verificar plano
    try:
        with db_session_factory() as _db_sdr:
            _sdr_allowed = tenant_sdr_allowed(_db_sdr, tenant_id)
    except Exception as _sdr_plan_err:
        logger.warning(f"[Pipeline] SDR plan gate falhou fechado: {_sdr_plan_err}")

    if not _sdr_allowed:
        _sdr_stage_final = "blocked_plan"
        if log_fn:
            log_fn("  Franz: bloqueado pelo plano atual", "info")
        return _sdr_stage_final, _sdr_allowed

    # Enfileirar job Franz
    try:
        _franz_payload = {
            "nome": state.lead_nome,
            "cidade": state.lead_obj.lead.cidade,
            "segmento": state.segmento,
            "telefone": state.lead_obj.lead.telefone or "",
            "whatsapp": state.lead_obj.lead.whatsapp or "",
            "rating": state.lead_obj.lead.rating or 0.0,
            "site_url": state.site_url,
            "score_caio": state.qualificacao_caio.score if state.qualificacao_caio else 0,
            "tier": state.qualificacao_caio.tier if state.qualificacao_caio else "STANDARD",
            "proof": getattr(state.qualificacao_caio, "motivo", None) if state.qualificacao_caio else None,
            "lead_id": state.lead_id,
            "tenant_id": tenant_id,
            "_run_id": state.run_id,
            "_parent_job_id": config.get("_job_id"),
        }
        if config.get("_bryan_test_number"):
            _franz_payload["_bryan_test_number"] = str(config.get("_bryan_test_number"))

        _db_franz = db_session_factory()
        try:
            job_queue_module.enqueue(
                _db_franz,
                tipo="franz_outreach",
                payload=_franz_payload,
                tenant_id=tenant_id,
                max_attempts=5,
                idempotency_key=f"franz-{state.lead_id}",
                run_id=state.run_id,
            )
            _db_franz.close()
            if log_fn:
                log_fn("  Franz: enfileirado como job separado", "info")
            _sdr_stage_final = "pending_sdr_send"
        except Exception:
            _db_franz.close()
            raise
    except Exception as e:
        logger.warning(f"[Pipeline] Franz enqueue erro (não bloqueia): {e}")
        if log_fn:
            log_fn(f"  Franz: falha ao enfileirar ({e}). Site gerado OK.", "warning")
        _sdr_stage_final = "s_enqueue_failed"

    return _sdr_stage_final, _sdr_allowed


# ─── HANDLERS DE SUCESSO/ERRO ────────────────────────────────────────────────

def on_fase_sucesso(
    fase: int,
    state,
    resultado: Any = None,
    log_fn: Callable = None,
) -> None:
    """Callback chamado quando uma fase completa com sucesso."""
    if log_fn:
        log_fn(f"  Fase {fase}: OK", "success")


def on_fase_erro(
    fase: int,
    erro: Exception,
    state,
    log_fn: Callable = None,
) -> str:
    """Callback chamado quando uma fase falha. Retorna tipo de erro."""
    err_str = str(erro).lower()

    if "rate" in err_str or "limit" in err_str:
        return "RATE_LIMIT"
    if any(x in err_str for x in ["nenhum lead", "no leads", "sem leads"]):
        return "NO_LEADS"
    if any(x in err_str for x in ["deploy", "nginx", "filesystem"]):
        return "DEPLOY_FAIL"
    if any(x in err_str for x in ["scraper", "playwright", "google maps"]):
        return "SCRAPER_FAIL"
    return "LLM_FAIL"


# ─── ATUALIZAR STATUS LEAD ─────────────────────────────────────────────────

def atualizar_status_lead(
    engine,
    lead_id: str,
    tenant_id: int,
    status: str,
    site_url: str = None,
    sdr_stage: str = None,
    erro: str = None,
) -> None:
    """Atualiza status do lead no banco de dados."""
    from sqlalchemy import text

    campos = ["status = :status", "atualizado_em = :ts"]
    valores = {"id": lead_id, "uid": tenant_id, "status": status, "ts": datetime.now().isoformat()}

    if site_url:
        campos.extend(["site_url = :url", "url_site = :url"])
        valores["url"] = site_url

    if sdr_stage:
        campos.append("sdr_stage = :stage")
        valores["stage"] = sdr_stage

    if erro:
        campos.append("erro_pipeline = :erro")
        valores["erro"] = erro

    if status == "concluido":
        campos.extend(["processado = true", "processado_em = :ts"])

    query = f"UPDATE leads SET {', '.join(campos)} WHERE id=:id AND user_id=:uid"

    try:
        with engine.connect() as conn:
            conn.execute(text(query), valores)
            conn.commit()
    except Exception as e:
        logger.warning(f"[Pipeline] Erro ao atualizar lead: {e}")
