"""Arquiteto Mestre — Orquestrador enxuto.
Recebe NichoBriefing + VariacaoEstrutural + dados do lead e retorna DesignerPRD.
Delega blocos LLM para bloco_estrutura.py e bloco_copy.py.
"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_CORE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "core"))
if _CORE_DIR not in sys.path:
    sys.path.insert(0, _CORE_DIR)

from designer_prd import DesignerPRD
from design_context import (
    get_design_context,
    get_design_context_prompt,
    get_hero_style,
    detectar_sub_nicho,
)
from craft_rules import get_craft_rules, get_autocritica
from seo_context import get_seo_context, SEO_NICHOS, ALIASES
from design_system_selector import select_design_system
from handoff_types import NichoBriefing, VariacaoEstrutural
try:
    from core.design_reference_packs import format_design_reference_pack_prompt
    from core.design_system_router import build_design_dna, choose_section_variant
except Exception:  # pragma: no cover - local import variant
    from design_reference_packs import format_design_reference_pack_prompt
    from design_system_router import build_design_dna, choose_section_variant

# Sprint 5 (v1.8) - tracing opt-in (zero overhead se FRALIB_TRACING=0)
try:
    from backend.services.tracing import trace_run
    _HAS_TRACING = True
except ImportError:
    _HAS_TRACING = False
    from contextlib import contextmanager
    @contextmanager
    def trace_run(*args, **kwargs):
        yield None

from prompts_arquiteto import (
    _extrair_dados_jina,
    _montar_brief_estruturado,
    _garantir_layout_type,
    _validar_prd_minimo,
    _buscar_google_suggest,
    selecionar_top_reviews,
    _garantir_secoes_obrigatorias,
)


def gerar_arquiteto_mestre_prd(
    dados_hunter: dict,
    cidade: str,
    segmento: str,
    jina_insights: str,
    caio_tier: str,
    caio_score: int = 0,
    caio_motivo: str = "",
    briefing_theo: str = "",
    dark_mode: bool = False,
    keyword_research: str = "",
    inteligencia: dict = None,
    nicho_briefing: NichoBriefing = None,
    variacao: VariacaoEstrutural = None,
) -> DesignerPRD:
    with trace_run("arquiteto", "gerar_prd", inputs={
        "segmento": segmento, "cidade": cidade, "caio_tier": caio_tier,
    }, metadata={"dark_mode": dark_mode}):
        return _gerar_arquiteto_mestre_prd_impl(
            dados_hunter, cidade, segmento, jina_insights,
            caio_tier, caio_score, caio_motivo, briefing_theo,
            dark_mode, keyword_research, inteligencia,
            nicho_briefing, variacao,
        )


def _gerar_arquiteto_mestre_prd_impl(
    dados_hunter: dict,
    cidade: str,
    segmento: str,
    jina_insights: str,
    caio_tier: str,
    caio_score: int = 0,
    caio_motivo: str = "",
    briefing_theo: str = "",
    dark_mode: bool = False,
    keyword_research: str = "",
    inteligencia: dict = None,
    nicho_briefing: NichoBriefing = None,
    variacao: VariacaoEstrutural = None,
) -> DesignerPRD:
    inteligencia = inteligencia or {}

    # ── 1. Sub-nicho ──
    _sub_nicho = detectar_sub_nicho(segmento, dados_hunter) or {}
    _sub_nicho_nome = _sub_nicho.get("sub_nicho", "")
    if _sub_nicho_nome:
        print(
            f"[ArquitetoMestre] Sub-nicho: {segmento}/{_sub_nicho_nome} (tom: {_sub_nicho.get('tom', '')[:40]})"
        )

    # ── 2. Design system slug ──
    _design_system_result = select_design_system(segmento, dados_hunter.get("nome", ""), caio_tier)
    _design_system_slug = _design_system_result.get("slug", "")

    # ── 3. Design context ──
    _design_dict = (
        get_design_context(
            segmento,
            dados_hunter.get("nome", ""),
            caio_tier,
            dark_mode,
            od_slug=_design_system_slug,
            dados_lead=dados_hunter,
        )
        or {}
    )
    _direction = _design_dict.get("direction", "default")
    _lead_id = (
        dados_hunter.get("id")
        or dados_hunter.get("place_id")
        or dados_hunter.get("nome")
        or ""
    )
    _design_dna = build_design_dna(
        segmento=segmento,
        business_name=dados_hunter.get("nome", ""),
        lead_id=str(_lead_id),
        tier=caio_tier,
        base_design=_design_dict,
        dados_lead=dados_hunter,
    )
    _design_pack_ctx = format_design_reference_pack_prompt(
        _design_dna.get("design_reference_pack") or {}
    )

    # ── 4. PRD Cache ──
    _disable_cache = os.environ.get("DISABLE_PRD_CACHE", "False").lower() in (
        "true",
        "1",
        "yes",
    )
    if not _disable_cache:
        try:
            from prd_cache import buscar_prd_cache, adaptar_prd_template

            _cache_entry = buscar_prd_cache(
                segmento, caio_tier, _direction, _sub_nicho_nome
            )
            if _cache_entry:
                _prd_adaptado = adaptar_prd_template(
                    _cache_entry, dados_hunter, briefing_theo
                )
                if _prd_adaptado and isinstance(_prd_adaptado, dict):
                    _prd_adaptado["_cache_hit"] = True
                    _prd_adaptado["_cache_key"] = _cache_entry.get("key")
                    return (
                        DesignerPRD(**_prd_adaptado)
                        if not isinstance(_prd_adaptado, DesignerPRD)
                        else _prd_adaptado
                    )
        except Exception as e:
            print(f"[CACHE] Erro: {e}")

    # ── 5. Google Suggest + Jina extractions ──
    google_suggest_terms = _buscar_google_suggest(segmento, cidade)
    _jina_dados = _extrair_dados_jina(jina_insights or "")
    _jina_keywords = _jina_dados.get("seo_keywords", [])
    _jina_faq = _jina_dados.get("faq_questions", [])
    _jina_value_props = _jina_dados.get("value_props", [])

    # ── 6. Reviews ──
    reviews_reais = dados_hunter.get("reviews") or []
    _reviews_sep = selecionar_top_reviews(reviews_reais)

    # ── 7. FAQ combinado ──
    _seg_alias = ALIASES.get(
        segmento.lower().replace(" ", "_").replace("-", "_"),
        segmento.lower().replace(" ", "_"),
    )
    _seo_nicho = SEO_NICHOS.get(_seg_alias, {})
    _faq_nicho = _seo_nicho.get(
        "faq", ["Como entrar em contato?", "Qual o horario?", "Onde fica?"]
    )
    _faq_combinado = list(dict.fromkeys(_faq_nicho + _jina_faq[:3]))[:8]

    # ── 8. Build context strings ──
    _brief_estruturado = _montar_brief_estruturado(
        dados_hunter, cidade, segmento, caio_tier, caio_score
    )
    _design_ctx = get_design_context_prompt(
        segmento, dados_hunter.get("nome", ""), caio_tier, dark_mode, od_slug=_design_system_slug
    )
    if _design_pack_ctx:
        _design_ctx = f"{_design_ctx}\n\n{_design_pack_ctx}"
    _craft_ctx = get_craft_rules()
    _autocritica_ctx = get_autocritica()
    _seo_ctx = get_seo_context(segmento, cidade, dados_hunter.get("nome", ""))

    _sub_nicho_ctx = ""
    if _sub_nicho.get("sub_nicho"):
        _sub_nicho_ctx = (
            f"\n=== SUB-NICHO ===\nSegmento: {segmento} | Sub-nicho: {_sub_nicho['sub_nicho']}\n"
            f"Tom: {_sub_nicho['tom']}\nPublico: {_sub_nicho['publico']}\n"
            f"CTA: {_sub_nicho['cta']}\nREGRA: Copy direcionado a {_sub_nicho['publico']}. Nao generico.\n=== FIM ===\n"
        )

    _nicho_ref = ""
    if nicho_briefing:
        _nicho_ref = (
            f"\n=== BRIEFING NICHO ===\nNicho: {nicho_briefing.nicho}\n"
            f"Subnichos: {', '.join(nicho_briefing.subnichos) if nicho_briefing.subnichos else 'N/A'}\n"
            f"Publico: {', '.join(nicho_briefing.publico_alvo) if nicho_briefing.publico_alvo else 'N/A'}\n"
            f"USP: {', '.join(nicho_briefing.usp) if nicho_briefing.usp else 'N/A'}\n"
            f"Tom: {nicho_briefing.tom_de_voz}\nConfianca: {nicho_briefing.confianca}\n=== FIM ===\n"
        )
    _variacao_ref = ""
    if variacao:
        _variacao_ref = (
            f"\n=== VARIACAO ===\nEstrutura: {variacao.template_estrutura}\n"
            f"Hero: {variacao.template_hero}\nCTA: {variacao.template_cta}\n"
            f"Ordem: {', '.join(variacao.ordem_das_secoes) if variacao.ordem_das_secoes else 'N/A'}\n"
            f"Angulo: {variacao.angulo_de_comunicacao}\n=== FIM ===\n"
        )

    # ── 9. Bloco 1: Estrutura ──
    from bloco_estrutura import executar_bloco_estrutura

    _nome = dados_hunter.get("nome", "")
    _rating = dados_hunter.get("rating", 0)
    _total_av = dados_hunter.get("total_avaliacoes", 0)
    _bloco1 = executar_bloco_estrutura(
        nome=_nome,
        cidade=cidade,
        segmento=segmento,
        caio_tier=caio_tier,
        caio_score=caio_score,
        rating=_rating,
        total_av=_total_av,
        inteligencia=inteligencia,
        sub_nicho_ctx=_sub_nicho_ctx,
        design_ctx=_design_ctx,
        craft_ctx=_craft_ctx,
        design_dict=_design_dict,
        nicho_ref=_nicho_ref,
        variacao_ref=_variacao_ref,
    )

    # ── 10. Bloco 2: Copy ──
    from bloco_copy import executar_bloco_copy

    _secoes_nomes = [
        s.get("name", "") for s in _bloco1.get("sections", []) if s.get("name")
    ]
    _tel = dados_hunter.get("telefone", "")
    _end = dados_hunter.get("endereco", "")
    _faq_seo = "FAQ para AI Search:\n" + "\n".join(f"  Q: {q}" for q in _faq_combinado)
    _faq_seo += "\nREGRA: Usar schema.org FAQPage (JSON-LD)."

    _intel_ctx = ""
    if inteligencia:
        parts = []
        conc = inteligencia.get("concorrencia", {})
        rev_ins = inteligencia.get("reviews_insights", {})
        servicos_r = inteligencia.get("servicos_reais", [])
        if conc.get("padroes_mercado"):
            pm = conc["padroes_mercado"]
            parts.append(f"Tema dominante: {pm.get('tema_dominante', 'N/A')}")
            parts.append(f"CTAs: {', '.join(pm.get('ctas_encontrados', [])[:3])}")
        if rev_ins.get("palavras_frequentes"):
            parts.append(
                f"Palavras frequentes: {', '.join(rev_ins['palavras_frequentes'][:8])}"
            )
        if rev_ins.get("diferencial_detectado"):
            parts.append(f"Diferencial: {rev_ins['diferencial_detectado']}")
        if servicos_r:
            parts.append(
                f"Servicos confirmados: {', '.join(s['titulo'] for s in servicos_r[:6])}"
            )
            parts.append("REGRA: Use APENAS estes servicos.")
        if inteligencia.get("seo", {}).get("h1_sugerido"):
            parts.append(f"H1 sugerido: {inteligencia['seo']['h1_sugerido']}")
        if inteligencia.get("seo", {}).get("people_also_ask"):
            parts.append(
                f"PAA: {' | '.join(inteligencia['seo']['people_also_ask'][:4])}"
            )
        _intel_ctx = "\n".join(parts)

    _bloco2 = executar_bloco_copy(
        nome=_nome,
        cidade=cidade,
        segmento=segmento,
        telefone=_tel,
        endereco=_end,
        rating=_rating,
        total_av=_total_av,
        caio_tier=caio_tier,
        dark_mode=dark_mode,
        jina_insights=jina_insights,
        instrucao_criativa=_bloco1.get("instrucao_criativa_para_dev", ""),
        reviews_raw=reviews_reais,
        seo_ctx=_seo_ctx,
        faq_seo_fmt=_faq_seo,
        keyword_research=keyword_research or "",
        secoes_nomes=_secoes_nomes,
        intel_ctx=_intel_ctx,
        craft_ctx=_craft_ctx,
        autocritica_ctx=_autocritica_ctx,
    )

    # ── 11. Merge: estrutura + copy ──
    _copy_map = {
        s.get("name", ""): s.get("copy", {}) for s in _bloco2.get("sections", [])
    }
    _omitir_map = {
        s.get("name", ""): s.get("omitir", False) for s in _bloco2.get("sections", [])
    }
    sections_final = []
    for s in _garantir_secoes_obrigatorias(_bloco1.get("sections", [])):
        nome_s = s.get("name", "")
        sec = dict(s)
        sec["copy"] = _copy_map.get(
            nome_s, {"h2": nome_s.capitalize(), "cta": "Fale Conosco"}
        )
        sec["omitir"] = _omitir_map.get(nome_s, False)
        sections_final.append(sec)

    _layout_type = _bloco1.get("layout_type", "corporate")
    _instrucao = _bloco1.get(
        "instrucao_criativa_para_dev", f"Site premium para {_nome} em {cidade}."
    )
    if _design_dna.get("style_mix_instruction") and "DESIGN PACK CURADO" not in _instrucao:
        _instrucao = (
            _instrucao.rstrip()
            + "\nDESIGN PACK CURADO: "
            + _design_dna["style_mix_instruction"]
        )

    # ── 12. Build data dict ──
    dados = {
        "business_name": _nome,
        "layout_type": _layout_type,
        "instrucao_criativa_para_dev": _instrucao,
        "sections": _garantir_layout_type(sections_final, _nome),
        "reviews_list": reviews_reais,
    }

    _tokens = _design_dna.get("tokens") or _design_dict.get("tokens", {})
    _tokens["_craft"] = _design_dict.get("craft", {})
    _tokens["_animation_profile"] = _design_dict.get("animation_profile", {})
    dados["color_palette"] = {
        "primary": _tokens.get("--fg", ""),
        "secondary": _tokens.get("--surface", ""),
        "accent": _tokens.get("--accent", ""),
        "background": _tokens.get("--bg", ""),
        "text": _tokens.get("--fg", ""),
        "surface": _tokens.get("--surface", ""),
        "muted": _tokens.get("--muted", ""),
        "border": _tokens.get("--border", ""),
        "tokens_oklch": _tokens,
        "hero_style": _design_dict.get("hero_style")
        or get_hero_style(_design_dict.get("dir_key", "")),
        "reasoning": f"OKLch deterministico. Direcao={_design_dict.get('dir_nome', '')} Nicho={segmento} Tier={caio_tier}.",
    }
    _archetype = _design_dna["archetype"]
    _visual_seed = _design_dna["visual_seed"]
    dados["visual_direction"] = {
        "design_system": _design_system_slug or _design_dict.get("direction") or "local-editorial",
        "direction": _design_dict.get("direction") or "",
        "vibe": _design_dict.get("vibe") or "",
        "tokens": _tokens,
        "font_heading": _design_dna.get("font_heading") or _design_dict.get("font_heading"),
        "font_body": _design_dna.get("font_body") or _design_dict.get("font_body"),
        "archetype": _archetype["archetype"],
        "visual_seed": _visual_seed,
        "dna_combo": _design_dna["dna_combo"],
        "design_reference_pack_id": (_design_dna.get("design_reference_pack") or {}).get("id"),
        "footer_policy": "Footer deve continuar a paleta do site; usar fechamento escuro somente se os tokens forem dark.",
        "media_policy": "Fotos fornecidas sao mídia editorial/stock aprovada para narrativa visual; nao chamar de foto real do espaco.",
    }
    dados["visual_dna"] = {
        "archetype": _archetype["archetype"],
        "visual_voice": _archetype["visual_voice"],
        "color_theory": _archetype["color_theory"],
        "visual_seed": _visual_seed,
        "dna_combo": _design_dna["dna_combo"],
        "style_mix_instruction": _design_dna["style_mix_instruction"],
        "reference_vibes": _design_dna["reference_vibes"],
        "design_reference_pack": _design_dna.get("design_reference_pack") or {},
        "variation": _design_dna["variation"],
        "tokens": _tokens,
        "palette_id": _design_dna.get("palette_id"),
        "color_strategy": _design_dna.get("color_strategy"),
        "palette_contrast": _design_dna.get("palette_contrast") or {},
        "typography": {
            "heading": _design_dna.get("font_heading") or _design_dict.get("font_heading", "Inter"),
            "body": _design_dna.get("font_body") or _design_dict.get("font_body", "Inter"),
            **_archetype.get("typography", {}),
        },
        "composition_laws": _archetype["composition_laws"],
        "creative_director_protocol": {
            "impact_hierarchy": "Headlines display 72px+ desktop quando combinar com o arquetipo.",
            "depth": "Usar z-index, sobreposicoes, negative margins e camadas visuais.",
            "background": "Nao depender de fundo branco plano; usar textura, mesh, imagem ou bloco disruptivo.",
            "rhythm": "Alternar full-bleed, leitura estreita e grid assimetrico.",
            "cta": _archetype["cta_policy"],
        },
    }
    dados["layout_blueprint"] = [
        {
            "section": sec.get("name"),
            "variant": sec.get("layout_type")
            or choose_section_variant(sec.get("name", ""), _visual_seed, _archetype["archetype"]),
            "reason": f"visual_seed={_visual_seed}; reference_pack={dados['visual_dna']['design_reference_pack'].get('id', '')}",
        }
        for sec in dados["sections"]
        if isinstance(sec, dict)
    ]
    dados["dna_combo"] = _design_dna["dna_combo"]
    dados["visual_seed"] = _visual_seed
    dados["design_reference_pack"] = _design_dna.get("design_reference_pack") or {}

    dados["segmento"] = segmento
    dados["cidade"] = cidade
    dados["sub_nicho"] = _sub_nicho
    dados["address"] = dados_hunter.get("endereco", "")
    dados["phone"] = dados_hunter.get("telefone", "")
    dados["rating"] = float(dados_hunter.get("rating", 0))
    dados["reviews_rating"] = float(dados_hunter.get("rating", 0))
    dados["reviews_count"] = int(dados_hunter.get("total_avaliacoes", 0))

    _kw_base = [segmento, f"{segmento} {cidade}", f"melhor {segmento} {cidade}"]
    _kw_suggest = google_suggest_terms[:5] if google_suggest_terms else []
    dados["seo_keywords"] = list(dict.fromkeys(_jina_keywords + _kw_base + _kw_suggest))
    dados["faq_questions"] = _faq_combinado
    dados["value_props"] = _jina_value_props

    _lat = dados_hunter.get("lat") or dados_hunter.get("latitude")
    _lng = (
        dados_hunter.get("lng")
        or dados_hunter.get("longitude")
        or dados_hunter.get("lon")
    )
    if _lat is not None and _lng is not None:
        try:
            dados["geo"] = {"lat": float(_lat), "lng": float(_lng)}
        except (TypeError, ValueError):
            pass

    _place_id = dados_hunter.get("place_id") or ""
    if _place_id:
        dados["place_id"] = _place_id

    dados["typography"] = {
        "heading": _design_dna.get("font_heading") or _design_dict.get("font_heading", "Inter"),
        "body": _design_dna.get("font_body") or _design_dict.get("font_body", "Inter"),
    }
    _anim_profile = _design_dict.get("animation_profile", {}) or {}
    dados["animations"] = [
        {
            "name": "mask-reveal",
            "type": "clip-y",
            "target": "hero headings",
            "trigger": "load",
            "duration": "0.95s",
            "easing": _anim_profile.get("easing_std", "power3.out"),
        },
        {
            "name": "stagger-reveal",
            "type": "translate-y-fade",
            "target": "content blocks",
            "trigger": "scroll",
            "duration": "0.75s",
            "easing": _anim_profile.get("easing_std", "power3.out"),
        },
        {
            "name": "parallax-image",
            "type": "parallax-y",
            "target": "dominant images",
            "trigger": "scroll",
            "duration": "scrub",
            "easing": "none",
        },
        {
            "name": "scroll-progress",
            "type": "scale-x",
            "target": "page progress",
            "trigger": "scroll",
            "duration": "continuous",
            "easing": "linear",
        },
    ]
    dados["google_maps_embed"] = ""
    _horarios_raw = dados_hunter.get("horarios") or {}
    if isinstance(_horarios_raw, list):
        _h = {}
        for item in _horarios_raw:
            if isinstance(item, str) and item.strip():
                parts = item.split("\t") if "\t" in item else item.split("  ")
                _h[parts[0].strip()] = parts[1].strip() if len(parts) >= 2 else ""
        _horarios_raw = _h
    dados["hours"] = _horarios_raw
    dados["servicos"] = dados_hunter.get("servicos") or []
    dados["atributos"] = dados_hunter.get("atributos") or []
    dados["faixa_preco"] = dados_hunter.get("faixa_preco") or ""
    dados["_raw_reviews"] = reviews_reais
    _logo = dados_hunter.get("logo_url") or ""
    dados["logo_url"] = _logo if _logo else None
    dados["components_21dev"] = ["whatsapp-sticky-cta"]
    dados["jina_insights"] = (jina_insights or "")[:3500]
    dados["competitor_analysis"] = ""
    dados["anti_patterns"] = [
        "precos visiveis",
        "emoji em textos ou cards",
        "grid perfeito de cards iguais como UI kit",
        "hero centralizado generico",
        "footer minimo ou solto",
        "servicos, equipe, equipamentos ou metricas sem prova",
    ]
    dados["schema_org_types"] = ["LocalBusiness"]
    dados["dark_mode"] = dark_mode
    dados["design_system_slug"] = _design_system_slug
    try:
        from requirements_contract import build_requirements_contract
        from visual_contract import build_visual_contract
        from site_build_plan import build_site_build_plan
    except Exception:
        from agents.requirements_contract import build_requirements_contract
        from agents.visual_contract import build_visual_contract
        from agents.site_build_plan import build_site_build_plan

    dados["requirements_contract"] = build_requirements_contract(dados)
    dados["visual_contract"] = build_visual_contract(dados)
    dados["site_build_plan"] = build_site_build_plan(dados)

    print(
        f"[ArquitetoMestre] PRD: {len(dados.get('sections', []))} secoes, {len(dados.get('reviews_list', []))} reviews"
    )
    prd = DesignerPRD(**dados)
    _validar_prd_minimo(prd)
    return prd
