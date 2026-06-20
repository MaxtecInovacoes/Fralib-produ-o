"""Helpers for pipeline lead capture and qualification flow."""

from __future__ import annotations

import json
import re
import unicodedata
import uuid
from datetime import datetime

from sqlalchemy import text
from backend.utils.agente1_hunter_v2 import LeadQualificado


def _slugify_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")[:50]


def build_lead_raw_data(lead, *, default_segmento: str = "", include_maps_embed: bool = True) -> dict:
    data = {
        "nome": lead.nome,
        "cidade": lead.cidade,
        "segmento": lead.segmento or default_segmento,
        "telefone": lead.telefone or "",
        "whatsapp": lead.whatsapp or "",
        "rating": lead.rating or 0.0,
        "reviews": list(lead.reviews or []),
        "total_avaliacoes": lead.total_avaliacoes or len(lead.reviews or []),
        "fotos": list(lead.fotos or []),
        "website": lead.website or "",
        "logo_url": getattr(lead, "logo_url", None) or "",
        "endereco": getattr(lead, "endereco", "") or getattr(lead, "address", "") or "",
        "lat": getattr(lead, "latitude", None),
        "lng": getattr(lead, "longitude", None),
        "horarios": getattr(lead, "horarios", None),
        "atributos": getattr(lead, "atributos", None),
        "servicos": getattr(lead, "servicos", None),
        "faixa_preco": getattr(lead, "faixa_preco", None),
        "place_id": getattr(lead, "place_id", "") or "",
    }
    if include_maps_embed:
        data["google_maps_embed"] = getattr(lead, "google_maps_embed", "") or ""
    return data


def persist_captured_lead(
    conn,
    *,
    lead_id: str,
    lead_nome: str,
    lead_city: str,
    lead_segmento: str,
    lead_phone: str,
    lead_whatsapp: str,
    lead_rating: float,
    lead_score: int,
    lead_tier: str,
    tenant_id: int,
    dados_completos: dict,
    status: str = "capturado",
) -> None:
    now = datetime.now().isoformat()
    conn.execute(
        text(
            """
            INSERT INTO leads (id,nome,cidade,segmento,telefone,whatsapp,rating,score,tier,status,user_id,criado_em,atualizado_em,processado,tentativas,dados_completos)
            VALUES (:id,:nome,:cidade,:segmento,:telefone,:whatsapp,:rating,:score,:tier,:status,:user_id,:criado_em,:atualizado_em,:processado,:tentativas,:dados_completos)
            ON CONFLICT DO NOTHING
            """
        ),
        {
            "id": lead_id,
            "nome": lead_nome,
            "cidade": lead_city,
            "segmento": lead_segmento,
            "telefone": lead_phone,
            "whatsapp": lead_whatsapp,
            "rating": lead_rating,
            "score": lead_score,
            "tier": lead_tier,
            "status": status,
            "user_id": tenant_id,
            "criado_em": now,
            "atualizado_em": now,
            "processado": False,
            "tentativas": 0,
            "dados_completos": json.dumps(dados_completos),
        },
    )


def choose_next_non_duplicate_lead(conn, leads, *, start_index: int, tenant_id: int):
    for lead_obj in leads[start_index + 1 :]:
        dup = conn.execute(
            text(
                """
                SELECT id FROM leads
                WHERE lower(trim(nome)) = lower(trim(:nome))
                  AND lower(cidade) = lower(trim(:cidade))
                  AND user_id = :user_id
                  AND status IN ('concluido', 'processando')
                LIMIT 1
                """
            ),
            {"nome": lead_obj.lead.nome, "cidade": lead_obj.lead.cidade, "user_id": tenant_id},
        ).fetchone()
        if not dup:
            return lead_obj
    return None


def build_or_reuse_lead_record(
    *,
    conn,
    state,
    lead_obj,
    tenant_id: int,
    lead_id: str | None = None,
):
    state.lead_obj = lead_obj
    state.lead_nome = lead_obj.lead.nome
    state.lead_slug = _slugify_name(state.lead_nome)
    state.lead_id = lead_id or str(uuid.uuid4())
    state.lead_raw_data = build_lead_raw_data(lead_obj.lead, default_segmento=state.segmento)
    existing = conn.execute(
        text(
            """
            SELECT id FROM leads
            WHERE lower(trim(nome)) = lower(trim(:nome))
              AND lower(cidade) = lower(trim(:cidade))
              AND user_id = :user_id
            LIMIT 1
            """
        ),
        {"nome": state.lead_nome, "cidade": lead_obj.lead.cidade, "user_id": tenant_id},
    ).fetchone()
    if existing:
        state.lead_id = str(existing[0])
    else:
        persist_captured_lead(
            conn,
            lead_id=state.lead_id,
            lead_nome=state.lead_nome,
            lead_city=lead_obj.lead.cidade,
            lead_segmento=state.segmento,
            lead_phone=lead_obj.lead.telefone or "",
            lead_whatsapp=lead_obj.lead.whatsapp or "",
            lead_rating=lead_obj.lead.rating or 0.0,
            lead_score=lead_obj.score,
            lead_tier=lead_obj.tier,
            tenant_id=tenant_id,
            dados_completos=state.lead_raw_data,
        )
        conn.commit()
    return state


async def prepare_lead_intelligence_assets(
    *,
    state,
    config,
    logger,
    _visual_archetype_id,
    buscar_fotos_unsplash,
    buscar_videos_pexels,
    get_design_context=None,
):
    """Normalize intelligence, curated media and map embed for the main pipeline."""
    from utils.espionar_concorrencia import (
        espionar_concorrencia,
        extrair_insights_reviews,
        mapear_atributos_para_servicos,
        gerar_seo_context,
    )

    async def _run_inteligencia():
        concorrencia = await espionar_concorrencia(
            state.segmento, state.cidade, max_concorrentes=3
        )
        reviews_insights = extrair_insights_reviews(state.lead_raw_data.get("reviews", []))
        atributos = state.lead_raw_data.get("atributos") or []
        servicos_reais = mapear_atributos_para_servicos(atributos, state.segmento)
        paa = concorrencia.get("people_also_ask", []) if isinstance(concorrencia, dict) else []
        seo = gerar_seo_context(
            state.segmento,
            state.cidade,
            state.lead_nome,
            paa=paa,
            rating=state.lead_raw_data.get("rating", 0),
            total_reviews=state.lead_raw_data.get("total_avaliacoes", 0),
            keyword_research=getattr(state, "keyword_research", "") or "",
            jina_insights=getattr(state, "jina_insights", "") or "",
        )
        state.inteligencia = {
            "concorrencia": concorrencia if isinstance(concorrencia, dict) else {},
            "reviews_insights": reviews_insights,
            "servicos_reais": servicos_reais,
            "seo": seo,
        }
        if state.inteligencia.get("concorrencia", {}).get("concorrentes"):
            conc_data = state.inteligencia["concorrencia"]
            enrich = "\n\n=== CONCORRENTES REAIS (via Playwright) ===\n"
            for c in conc_data.get("concorrentes", [])[:3]:
                enrich += f"- {c.get('nome', '?')}: tema={c.get('tema', '?')}, CTA='{c.get('cta_principal', '')}', H1='{c.get('h1_text', '')[:60]}'\n"
            pm = conc_data.get("padroes_mercado", {})
            if pm:
                enrich += f"Padrão: {pm.get('tema_dominante', '?')}, fonte={pm.get('fonte_h1_dominante', '?')}\n"
            paa_list = state.inteligencia.get("concorrencia", {}).get("people_also_ask", [])
            if paa_list:
                enrich += f"People Also Ask: {' | '.join(paa_list[:4])}\n"
            state.jina_insights = (state.jina_insights or "") + enrich

    import urllib.parse as _urlparse
    await _run_inteligencia()
    state.briefing_theo = f"Site premium para {state.lead_nome} ({state.segmento}) em {state.cidade}. Rating: {state.lead_obj.lead.rating or 0}/5."
    _nome_negocio = state.lead_raw_data.get("nome", "") or ""
    _cidade_negocio = getattr(state, "cidade", "") or state.lead_raw_data.get("cidade", "") or ""
    try:
        _fotos_unsplash = buscar_fotos_unsplash(
            state.segmento,
            quantidade=8,
            nome=_nome_negocio,
            cidade=_cidade_negocio,
            archetype=_visual_archetype_id(state.segmento, _nome_negocio, state.lead_raw_data),
        )
        state.lead_raw_data["fotos"] = _fotos_unsplash
        state.lead_raw_data["logo_url"] = None
    except Exception as e:
        logger.warning(f"[Pipeline] Unsplash erro: {e}")
        state.lead_raw_data["fotos"] = []
    try:
        _videos_pexels = buscar_videos_pexels(
            state.segmento,
            quantidade=2,
            nome=_nome_negocio,
            cidade=_cidade_negocio,
        )
        state.lead_raw_data["videos"] = _videos_pexels
    except Exception as e:
        logger.warning(f"[Pipeline] Pexels video erro: {e}")
        state.lead_raw_data["videos"] = []

    reviews_raw = state.lead_raw_data.get("reviews", [])
    if reviews_raw:
        def _get_rating(r):
            return float(r.get("rating") or r.get("nota") or r.get("stars") or r.get("estrelas") or 0)

        positivos = [r for r in reviews_raw if _get_rating(r) >= 4]
        if len(positivos) < 2:
            positivos = [r for r in reviews_raw if _get_rating(r) >= 3]
        if not positivos:
            melhores = sorted(reviews_raw, key=lambda r: _get_rating(r), reverse=True)[:3]
            positivos = [r for r in melhores if _get_rating(r) >= 2]
            state.lead_raw_data["reviews"] = positivos if positivos else []
        else:
            positivos_sorted = sorted(
                positivos,
                key=lambda r: len(str(r.get("texto", r.get("text", "")))),
                reverse=True,
            )
            state.lead_raw_data["reviews"] = positivos_sorted[:5]
    if len(state.jina_insights) > 5000:
        state.jina_insights = state.jina_insights[:5000]
    embed_hunter = state.lead_raw_data.get("google_maps_embed", "") or ""
    if not embed_hunter or len(embed_hunter) < 50:
        maps_query = _urlparse.quote(
            " ".join(
                str(v)
                for v in (
                    state.lead_nome,
                    getattr(state.lead_obj.lead, "endereco", "") or getattr(state.lead_obj.lead, "address", ""),
                    state.lead_obj.lead.cidade,
                )
                if v
            )
        )
        embed_hunter = (
            '<iframe width="100%" height="450" style="border:0;" loading="lazy" allowfullscreen="" '
            'referrerpolicy="no-referrer-when-downgrade" '
            'src="https://maps.google.com/maps?q=' + maps_query + '&output=embed&z=18"></iframe>'
        )
    state.lead_raw_data["google_maps_embed"] = embed_hunter


def build_reprocess_seed_state(state, lead_dict, dados, lead_raw, segmento, cidade, nome):
    """Recreate the normalized state used by reprocess and keep the orchestrator thin."""
    state.lead_obj = LeadQualificado(
        lead=lead_raw,
        score=int(lead_dict.get("score") or 50),
        tier=lead_dict.get("tier") or "STANDARD",
        razoes=[],
        sinais=[],
        presenca_digital="SITE" if lead_raw.website else "ZERO_PRESENCA",
        dados_suficientes=True,
    )
    state.lead_nome = nome
    state.lead_slug = _slugify_name(nome)
    state.lead_id = lead_dict.get("id") or lead_dict.get("lead_id") or ""
    state.lead_raw_data = build_lead_raw_data(lead_raw, default_segmento=segmento)
    state.lead_raw_data["reviews"] = list(lead_raw.reviews or [])
    state.lead_raw_data["logo_url"] = lead_dict.get("logo_url") or dados.get("logo_url") or ""
    return state
