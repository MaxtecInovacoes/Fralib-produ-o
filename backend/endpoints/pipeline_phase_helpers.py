"""Helpers for pipeline phase execution."""

from __future__ import annotations

try:
    from agents.agente_nicho import gerar_briefing
except Exception:  # pragma: no cover - import fallback keeps tests patchable.
    gerar_briefing = None

try:
    from agents.agente_variacao import gerar_variacao
except Exception:  # pragma: no cover - import fallback keeps tests patchable.
    gerar_variacao = None

try:
    from agents.keyword_research import pesquisar_keywords_nicho
except Exception:  # pragma: no cover - import fallback keeps tests patchable.
    pesquisar_keywords_nicho = None

try:
    from utils.jina_intelligence import (
        buscar_inteligencia_jina,
        formatar_inteligencia_para_arquiteto,
    )
except Exception:  # pragma: no cover - import fallback keeps tests patchable.
    buscar_inteligencia_jina = None
    formatar_inteligencia_para_arquiteto = None


def init_phase_tracking(state, tenant_id, config, set_llm_context, tracker_cls, set_tracker):
    """Initialize LLM context and optional token tracking for a phase run."""
    set_llm_context(
        tenant_id=tenant_id,
        run_id=getattr(state, "run_id", None) or config.get("_run_id"),
        job_id=config.get("_job_id"),
    )
    token_tracker = None
    try:
        token_tracker = tracker_cls(
            run_id=getattr(state, "run_id", None) or config.get("_run_id"),
            lead_nome=getattr(state, "lead_nome", "") or "",
            nicho=getattr(state, "segmento", "") or config.get("segmento", ""),
            tenant_id=tenant_id,
            job_id=config.get("_job_id"),
        )
        set_tracker(token_tracker)
    except Exception:
        token_tracker = None
    return token_tracker


def ensure_keyword_research(state, logger, warning_fn=None) -> None:
    """Populate keyword research when missing."""
    if state.keyword_research:
        return
    try:
        if pesquisar_keywords_nicho is None:
            raise RuntimeError("pesquisar_keywords_nicho indisponivel")
        state.keyword_research = pesquisar_keywords_nicho(
            state.lead_obj.lead.segmento, state.lead_obj.lead.cidade
        )
        logger("  Keywords: OK (cache)", "success")
    except Exception as exc:
        message = f"[Pipeline] Keyword research erro: {exc}"
        if warning_fn:
            warning_fn(message)
        elif hasattr(logger, "warning"):
            logger.warning(message)
        else:
            logger(message, "warning")


def ensure_jina_insights(state, log_fn, fallback_researcher, warning_fn) -> None:
    """Populate Jina intelligence or fail closed."""
    try:
        if buscar_inteligencia_jina is None or formatar_inteligencia_para_arquiteto is None:
            raise RuntimeError("jina_intelligence indisponivel")
        jina_intel = buscar_inteligencia_jina(
            nicho=state.lead_obj.lead.segmento,
            cidade=state.lead_obj.lead.cidade,
            nome_negocio=state.lead_nome,
            concorrentes_urls=getattr(state, "_concorrentes_urls", None),
        )
        state.jina_intel_dict = jina_intel
        state.jina_insights = formatar_inteligencia_para_arquiteto(jina_intel)
        log_fn(
            f"  Jina Intel: {len(state.jina_insights)} chars, {len(jina_intel.get('palavras_poder', []))} sinais",
            "success",
        )
    except Exception as exc:
        state.jina_intel_dict = {}
        state.jina_insights = ""
        warning_fn(f"[Pipeline] Jina Intel erro: {exc}")
        raise


def curate_lead_assets(state, logger) -> None:
    """Normalize curated media and map data for downstream rendering."""
    reviews_raw = state.lead_raw_data.get("reviews", [])
    if len(reviews_raw) > 5:
        state.lead_raw_data["reviews"] = sorted(
            reviews_raw,
            key=lambda r: len(str(r.get("texto", r.get("text", "")))),
            reverse=True,
        )[:5]
    if len(state.jina_insights) > 5000:
        state.jina_insights = state.jina_insights[:5000]

    import urllib.parse as _urlparse

    embed_hunter = state.lead_raw_data.get("google_maps_embed", "") or ""
    if embed_hunter and len(embed_hunter) >= 50:
        state.lead_raw_data["google_maps_embed"] = embed_hunter
        logger("  Mapa: embed confiavel mantido", "info")
        return

    maps_query = _urlparse.quote_plus(
        " ".join(
            str(v)
            for v in (
                state.lead_nome,
                getattr(state.lead_obj.lead, "endereco", "")
                or getattr(state.lead_obj.lead, "address", ""),
                state.lead_obj.lead.cidade,
            )
            if v
        )
    )
    state.lead_raw_data["google_maps_embed"] = ""
    if maps_query:
        state.lead_raw_data["maps_url"] = (
            "https://www.google.com/maps/search/?api=1&query=" + maps_query
        )
    logger("  Mapa: sem embed confiavel; Builder recebera link/card", "info")


def build_prompt_phase_outputs(
    *,
    state,
    tenant_id,
    seg,
    cid,
    dark_mode,
    builder_fast_path,
    prompt_agent_flow,
    build_prompt_prd,
    build_skill_prd,
    build_master_prd,
    gerar_briefing,
    gerar_variacao,
    log_fn,
    warning_fn,
):
    """Build niche briefing, structural variation and PRD for phase 6."""
    try:
        from backend.agents.handoff_types import NichoBriefing, VariacaoEstrutural
    except ModuleNotFoundError:
        from agents.handoff_types import NichoBriefing, VariacaoEstrutural

    if builder_fast_path:
        state.nicho_briefing = NichoBriefing(
            task_id=state.pipeline_id,
            source_agent="pipeline",
            target_agent="builder_renderer",
            nicho=seg,
            cidade=cid,
            confianca="media",
        )
    elif not getattr(state, "nicho_briefing", None):
        try:
            state.nicho_briefing = gerar_briefing(
                dados_lead=state.lead_raw_data,
                segmento=seg,
                cidade=cid,
                jina_insights=state.jina_insights,
                task_id=state.pipeline_id,
            )
        except Exception as exc:
            warning_fn(f"[Pipeline] agente_nicho erro: {exc}")
            raise

    if builder_fast_path:
        state.variacao_estrutural = VariacaoEstrutural(
            task_id=state.pipeline_id,
            source_agent="pipeline",
            target_agent="builder_renderer",
            template_estrutura="skill-fast",
            template_hero="renderer-decides",
            ordem_das_secoes=["hero", "sobre", "prova-social", "contato", "footer"],
        )
    elif not getattr(state, "variacao_estrutural", None):
        try:
            state.variacao_estrutural = gerar_variacao(
                nicho_briefing=state.nicho_briefing,
                concorrentes_raw=state.jina_insights,
                task_id=state.pipeline_id,
            )
        except Exception as exc:
            warning_fn(f"[Pipeline] agente_variacao erro: {exc}")
            raise

    if prompt_agent_flow:
        state.prd_arquiteto = build_prompt_prd(state, tenant_id)
        log_fn(
            f"  Prompt: {len(state.prd_arquiteto.builder_prompt):,} chars para o Builder",
            "success",
        )
    elif builder_fast_path:
        if build_skill_prd is not None:
            state.prd_arquiteto = build_skill_prd(state)
    else:
        qualificacao_caio = getattr(state, "qualificacao_caio", None)
        state.prd_arquiteto = build_master_prd(
            dados_hunter=state.lead_raw_data,
            cidade=cid,
            segmento=seg,
            jina_insights=state.jina_insights,
            briefing_theo=getattr(state, "briefing_theo", ""),
            caio_tier=qualificacao_caio.tier if qualificacao_caio else "STANDARD",
            caio_score=qualificacao_caio.score if qualificacao_caio else 0,
            caio_motivo=qualificacao_caio.motivo if qualificacao_caio else "",
            dark_mode=dark_mode,
            keyword_research=getattr(state, "keyword_research", None),
            nicho_briefing=getattr(state, "nicho_briefing", None),
            variacao=getattr(state, "variacao_estrutural", None),
        )


def publish_rendered_site(
    *,
    state,
    tenant_id,
    web_dir,
    copy_builder_dist,
    gerar_sitemap_robots,
    logger_warning,
):
    """Publish the rendered site and normalize assets."""
    import os
    import shutil
    import subprocess as _sp

    try:
        from backend.services.builder_worker import assert_canonical_builder_publication_allowed
    except Exception:
        from services.builder_worker import assert_canonical_builder_publication_allowed  # type: ignore

    os.makedirs(web_dir, exist_ok=True)
    assert_canonical_builder_publication_allowed(
        state.builder_output_dir or web_dir,
        html=state.html_final,
    )
    if state.builder_output_dir:
        copy_builder_dist(state.builder_output_dir, web_dir)
    with open(f"{web_dir}/index.html", "w", encoding="utf-8") as _f:
        _f.write(state.html_final)
    try:
        gerar_sitemap_robots(
            state.html_final,
            state.prd_arquiteto,
            web_dir,
            f"https://seunegociofralib.site/sites/{tenant_id}/{state.lead_slug}/",
        )
    except Exception as exc:
        logger_warning(f"[Pipeline] Erro sitemap/robots (nao-fatal): {exc}")
    if state.alex_result and state.alex_result.assets_dir:
        assets_src = os.path.realpath(state.alex_result.assets_dir)
        assets_dst = os.path.realpath(f"{web_dir}/assets")
        if assets_src == assets_dst:
            print(f"[Pipeline] Assets já no lugar: {assets_dst}")
        elif os.path.exists(assets_src):
            if os.path.exists(assets_dst):
                shutil.rmtree(assets_dst)
            shutil.copytree(assets_src, assets_dst)
    _sp.run(["chown", "-R", "www-data:www-data", web_dir], check=False)
    _sp.run(["chmod", "-R", "755", web_dir], check=False)


def build_franz_outreach_payload(state, config) -> dict:
    """Build the canonical Franz outreach payload."""
    payload = {
        "nome": state.lead_nome,
        "cidade": state.lead_obj.lead.cidade,
        "segmento": state.lead_obj.lead.segmento,
        "telefone": state.lead_obj.lead.telefone or "",
        "whatsapp": state.lead_obj.lead.whatsapp or "",
        "rating": state.lead_obj.lead.rating or 0.0,
        "site_url": state.site_url,
        "score_caio": state.qualificacao_caio.score if state.qualificacao_caio else 0,
        "tier": state.qualificacao_caio.tier if state.qualificacao_caio else "STANDARD",
        "proof": getattr(state.qualificacao_caio, "motivo", None)
        if state.qualificacao_caio
        else None,
        "lead_id": state.lead_id,
        "tenant_id": state.tenant_id,
        "_run_id": state.run_id,
        "_parent_job_id": config.get("_job_id"),
    }
    if config.get("_bryan_test_number"):
        payload["_bryan_test_number"] = str(config.get("_bryan_test_number"))
    return payload


def finalize_reprocess_state(
    state,
    tenant_id,
    token_tracker,
    set_llm_context,
    update_pipeline_state,
    session_factory,
):
    """Persist trace/token state after the reprocess flow ends."""
    try:
        if token_tracker:
            token_tracker.lead_nome = getattr(state, "lead_nome", "") or ""
            from agents.token_tracker import log_tracking, salvar_tracking

            resumo = token_tracker.resumo()
            log_tracking(resumo)
            salvar_tracking(resumo)
    except Exception as exc:
        print(f"[TRACKING] Erro no lead existente: {exc}")
    try:
        from agents.token_tracker import set_tracker

        set_tracker(None)
    except Exception:
        pass
    set_llm_context(None, None, None)
    db_final = None
    try:
        db_final = session_factory()
        update_pipeline_state(db_final, tenant_id, pausado=False)
    finally:
        if db_final:
            db_final.close()
