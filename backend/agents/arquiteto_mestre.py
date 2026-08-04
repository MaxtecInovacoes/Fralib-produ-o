"""
Arquiteto Mestre — Funde Theo + Designer em um unico agente.
Recebe dados brutos (Hunter, Alex, Jina, Caio) e retorna DesignerPRD
com reviews reais, paleta harmonizada e copy completa por secao.
Modelo: Claude Opus — structured output JSON.
"""
import sys
import json
import re
import urllib.request
import urllib.parse
sys.path.insert(0, "/root/fralib/backend/agents")

from llm_direct import call_claude
from designer_prd import DesignerPRD, ColorPalette, AnimationSpec, SectionSpec
from design_context import get_design_context, get_design_context_prompt, get_hero_style
from craft_rules import get_craft_rules, get_autocritica
from seo_context import get_seo_context
from open_design_selector import get_open_design_prompt, select_design_system


def selecionar_top_reviews(reviews: list, max_site: int = 3) -> dict:
    """
    Separa reviews em:
    - top_3: os melhores pro site (nota alta + texto longo)
    - insights: inteligência extraída de TODOS pra alimentar copy
    """
    if not reviews:
        return {"top_3": [], "insights": {"total_reviews": 0, "nota_media": 0, "elogios_resumo": [], "reclamacoes_resumo": [], "palavras_frequentes": [], "diferencial_detectado": ""}}

    scored = []
    for r in reviews:
        texto = r.get("texto", r.get("text", ""))
        nota = float(r.get("nota", r.get("rating", r.get("stars", 5))))
        score = nota * 10 + min(len(texto), 200)
        scored.append({"review": r, "score": score, "texto": texto, "nota": nota})

    scored.sort(key=lambda x: x["score"], reverse=True)

    top_3 = [s["review"] for s in scored[:max_site]]

    elogios = [s["texto"][:150] for s in scored if s["nota"] >= 4][:5]
    reclamacoes = [s["texto"][:150] for s in scored if s["nota"] <= 2][:3]

    palavras = {}
    _stop = {"para", "como", "mais", "muito", "esse", "essa", "este", "esta", "aqui", "onde", "quando", "lugar", "super", "legal"}
    for s in scored:
        for p in s["texto"].lower().split():
            if len(p) > 4 and p not in _stop:
                palavras[p] = palavras.get(p, 0) + 1
    top_palavras = sorted(palavras.items(), key=lambda x: x[1], reverse=True)[:10]

    insights = {
        "total_reviews": len(reviews),
        "nota_media": round(sum(s["nota"] for s in scored) / len(scored), 1),
        "elogios_resumo": elogios,
        "reclamacoes_resumo": reclamacoes,
        "palavras_frequentes": [p[0] for p in top_palavras],
        "diferencial_detectado": elogios[0][:100] if elogios else ""
    }

    return {"top_3": top_3, "insights": insights}
from markdown_prd_parser import parse_bloco1_with_fallback, parse_bloco2_with_fallback



def _montar_brief_estruturado(dados_hunter: dict, cidade: str, segmento: str, caio_tier: str, caio_score: int) -> str:
    """Monta brief automatico a partir dos dados existentes — equivalente ao Turn 1 do Open Design."""
    nome = dados_hunter.get("nome", "")
    rating = dados_hunter.get("rating", 0)
    total_av = dados_hunter.get("total_avaliacoes", 0)
    telefone = dados_hunter.get("telefone", "")
    endereco = dados_hunter.get("endereco", "")
    fotos = dados_hunter.get("fotos") or []
    reviews = dados_hunter.get("reviews") or []
    horarios = dados_hunter.get("horarios") or {}
    servicos = dados_hunter.get("servicos") or []
    atributos = dados_hunter.get("atributos") or []

    return f"""
=== BRIEF ESTRUTURADO DO NEGOCIO ===
SURFACE: website local (mobile-first, 1 pagina, carregamento rapido)
AUDIENCE: clientes de {cidade} buscando {segmento} — intenção transacional
TONE: definido pelo Design System do nicho abaixo
BRAND CONTEXT:
  Nome: {nome}
  Segmento: {segmento}
  Cidade: {cidade}
  Rating: {rating}/5 ({total_av} avaliacoes)
  Telefone: {telefone}
  Endereco: {endereco}
  Fotos disponiveis: {len(fotos)}
  Reviews disponiveis: {len(reviews)}
  Horarios: {horarios if horarios else "nao informado"}
  Servicos listados: {", ".join(servicos[:8]) if servicos else "nao informado"}
  Atributos: {", ".join(atributos[:6]) if atributos else "nao informado"}
SCALE: single-page, 6-8 secoes
TIER: {caio_tier} (score={caio_score})
CONSTRAINTS:
  - Sem precos visiveis (exceto se tier BASIC)
  - LGPD obrigatorio
  - WhatsApp CTA obrigatorio em todas as secoes
  - Dados reais apenas — nunca inventar metricas
=== FIM BRIEF ===
"""

def _extrair_dados_jina(jina_insights: str) -> dict:
    """Extrai FAQ, keywords e value_props do bloco estruturado da Jina."""
    import json as _j, re as _r
    result = {'faq_questions': [], 'seo_keywords': [], 'value_props': []}
    if '=== DADOS ESTRUTURADOS PARA SEO ===' not in jina_insights:
        return result
    try:
        bloco = jina_insights.split('=== DADOS ESTRUTURADOS PARA SEO ===')[1]
        for key in ('faq_questions', 'seo_keywords', 'value_props'):
            m = _r.search(key.upper() + r': (\[.*?\])', bloco, _r.DOTALL)
            if m:
                result[key] = _j.loads(m.group(1))
    except Exception as e:
        print('[ArquitetoMestre] Aviso: extracao Jina falhou:', e)
    return result


def clean_json(text: str) -> str:
    """Extrai o maior JSON valido do texto."""
    text = text.replace("```json", "").replace("```", "").strip()
    # Substituir Unicode Line/Paragraph Separator (\u2028, \u2029) que quebram json.loads
    text = text.replace("\u2028", " ").replace("\u2029", " ")
    # Sanitizar caracteres de controle ASCII
    import re as _re_u
    text = _re_u.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', text)
    candidates = []
    i = 0
    while i < len(text):
        if text[i] != "{":
            i += 1
            continue
        depth = 0
        in_str = False
        esc = False
        j = i
        while j < len(text):
            ch = text[j]
            if esc:
                esc = False
                j += 1
                continue
            if ch == "\\" and in_str:
                esc = True
                j += 1
                continue
            if ch == '"':
                in_str = not in_str
                j += 1
                continue
            if in_str:
                j += 1
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[i:j + 1])
                    break
            j += 1
        i += 1
    if not candidates:
        return text
    return max(candidates, key=len)


def _validar_prd_minimo(prd: DesignerPRD) -> None:
    """Falha cedo se o PRD vier sem contrato minimo para o Liam."""
    if not prd.business_name:
        raise ValueError("PRD invalido: business_name vazio")
    if not prd.sections or len(prd.sections) < 4:
        raise ValueError("PRD invalido: sections insuficientes")
    nomes = {str(s.name).lower() for s in prd.sections}
    obrigatorias = {"hero", "sobre", "servicos", "contato"}
    faltando = sorted(obrigatorias - nomes)
    if faltando:
        raise ValueError("PRD invalido: secoes obrigatorias ausentes: " + ", ".join(faltando))
    if not prd.typography:
        raise ValueError("PRD invalido: typography vazio")
    if not prd.color_palette:
        raise ValueError("PRD invalido: color_palette vazio")
    for campo in ("primary", "background", "text", "accent"):
        if not getattr(prd.color_palette, campo, None):
            raise ValueError(f"PRD invalido: color_palette.{campo} vazio")



def _buscar_google_suggest(segmento: str, cidade: str) -> list:
    """Busca termos reais do Google Suggest para o nicho/cidade."""
    try:
        query = urllib.parse.quote(f"{segmento} {cidade}")
        url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={query}&hl=pt-BR"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            suggestions = data[1] if len(data) > 1 else []
            return [s for s in suggestions if isinstance(s, str)][:10]
    except Exception as e:
        print("[ArquitetoMestre] Google Suggest falhou (nao critico):", e)
        return []

SYSTEM_ARQUITETO = """Voce e o Arquiteto Mestre e Diretor de Arte da FraLib. Sua unica funcao e receber dados brutos de um negocio local e retornar um JSON estruturado e completo que sera usado para gerar o site.

REGRAS ABSOLUTAS:
1. Retorne APENAS JSON valido. Nenhum texto fora do JSON.
2. Use APENAS dados reais fornecidos. NUNCA invente nomes, enderecos, telefones ou depoimentos.
3. Se reviews estiver vazio, o campo reviews_list deve ser uma lista vazia [].
4. Copy de cada secao deve ser especifica para o negocio — sem frases genericas intercambiaveis.
5. NUNCA mencione precos, valores ou mensalidades.
6. CORES E BACKGROUND: O campo "MODO VISUAL OBRIGATORIO" no user prompt tem prioridade absoluta. Se for DARK MODE, background DEVE ser escuro (#0a0a0f ou similar). Se for LIGHT MODE, background DEVE ser claro (#ffffff ou similar). NUNCA inverta o modo visual. Adicione glow (sombras coloridas) nos botoes CTA.
7. DIRECAO DE ARTE DO NICHO: Leia os INSIGHTS DE MERCADO (Jina AI) fornecidos no prompt. Extraia a VIBE VISUAL dominante do segmento (cores que convertem, estilo tipografico, tom emocional). Voce DEVE escolher animation_theme e color_palette baseados nessa vibe — garantindo que cada site seja unico para o segmento.
8. INSTRUCAO CRIATIVA: Com base nos insights da Jina, no briefing do Theo e nos dados do cliente, escreva instrucao unica para o Liam: vibe do site, como aplicar cores (gradientes, glassmorphism, glow), espacamento e personalidade visual. Cada instrucao deve ser radicalmente diferente entre nichos distintos. OBRIGATORIO: termine a instrucao_criativa_para_dev com a linha exata "CSS VARS CONFIRMADAS: --color-primary:X --color-background:Y --color-accent:Z --color-text:W" usando os valores reais da color_palette que voce gerou. Isso garante que o Liam use exatamente as cores certas sem ambiguidade.

DIRETRIZES VISUAIS CINEMATOGRÁFICAS (OBRIGATORIAS):
- Hero: headline MINIMO 8 palavras, tipografia bold extrema (font-size 3.5-5rem em desktop), imagem full-bleed com overlay gradiente
- Ritmo visual: secao clara → secao com cor de accent sutil → secao escura (invertida) → secao clara. NUNCA 3 secoes seguidas com mesmo fundo.
- Cards: hover translateY(-6px) + shadow-xl, border-radius generoso (rounded-2xl), border sutil
- CTAs: botoes grandes (py-4 px-8), rounded-full, bg-accent com text-white, pulse animation
- Espacamento: secoes generosas (py-20 md:py-32), cards com p-8, gap entre elementos 24px+
- Tipografia: H1 3.5-5rem, H2 max 2.5rem, subtitulo text-lg md:text-xl, contraste forte entre titulos e corpo
- Animacao: energetic para fitness/barbearia, elegant para saude/luxo, vibrante para comida
- Anti-patterns: NUNCA gerar sites "template" (hero→features→pricing→faq→cta). Varie estruturas drasticamente por nicho.
- Dados reais sempre: reviews reais, fotos reais, endereco real, telefone real. NUNCA inventar.

FATOR DE VARIANCIA DINAMICA — OBRIGATORIO:
Voce e um Diretor de Arte. Para nao gerar sites repetitivos, voce DEVE escolher uma estrutura visual especifica para cada secao usando o campo "layout_type". NUNCA use a mesma combinacao de estruturas duas vezes para clientes diferentes.

MENU DE LAYOUTS DISPONIVEIS:
- hero: "hero-split" (texto esquerda 60%, imagem direita 40%) | "hero-center" (texto centralizado, bg escuro com overlay) | "hero-fullscreen" (imagem full-screen com texto centralizado e overlay gradiente) | "hero-diagonal" (divisao diagonal entre texto e imagem)
- sobre: "sobre-timeline" (historia em linha do tempo vertical) | "sobre-grid" (texto esquerda + mosaico de fotos direita) | "sobre-cards" (3 cards com icones representando valores/diferenciais)
- servicos: "services-cards" (grid 3 colunas com cards elevados) | "services-accordion" (lista retratil com icones) | "services-grid-icons" (grid 2x3 com icone grande + titulo + descricao curta) | "services-list" (lista vertical com numero sequencial e linha separadora)
- depoimentos: "reviews-masonry" (cards em masonry 3 colunas) | "reviews-carousel" (carrossel horizontal) | "reviews-grid" (grid 2 colunas com cards grandes)
- localizacao: "location-split" (mapa esquerda, info direita) | "location-full" (mapa full-width, info abaixo) | "location-card" (card centralizado com endereco + botao Google Maps)
- contato: "contact-minimal" (formulario simples centralizado) | "contact-split" (info esquerda, cta direita) | "contact-card" (card unico centralizado com todos os dados de contato)

Use o hash do nome do negocio como seed mental para escolher combinacoes unicas. Negocios com nomes que comecam com A-H usam layouts mais assimetricos. I-P usam layouts com mais cards. Q-Z usam layouts mais minimalistas.

TEMA DE ANIMACAO GSAP — escolha UM para o site inteiro:
- "energetico": elementos entram rapido (0.3-0.5s), scale-in, bounce leve — academias, barbearias, crossfit
- "elegante": fade-up lento (0.8-1.2s), blur-in, sem bounce — doceria, clinica, atelier, advocacia
- "vibrante": slide lateral (0.5-0.7s), stagger agressivo, cores saturadas — restaurante, lanchonete, pizzaria

Escolha o tema baseado no segmento: academias/barbearias/crossfit = energetico. Doceria/clinica/atelier/advocacia = elegante. Restaurante/lanchonete/pizzaria = vibrante.

ESTRUTURA DO JSON DE SAIDA:
{
  "business_name": "nome exato do negocio",
  "address": "endereco completo ou vazio se nao disponivel",
  "phone": "telefone formatado",
  "reviews_rating": 0.0,
  "reviews_count": 0,
  "reviews_list": [],
  "color_palette": {
    "primary": "#hex",
    "secondary": "#hex",
    "accent": "#hex",
    "background": "#0a0a0f (DARK MODE) ou #ffffff (LIGHT MODE) — conforme MODO VISUAL OBRIGATORIO",
    "text": "#f0f0f5 (DARK MODE) ou #1f2937 (LIGHT MODE) — conforme MODO VISUAL OBRIGATORIO",
    "reasoning": "justificativa"
  },
  "typography": {"heading": "Plus Jakarta Sans", "body": "Inter"},
  "animation_theme": "elegante",
  "instrucao_criativa_para_dev": "Instrucao detalhada do Diretor de Arte para o desenvolvedor: vibe, cores, espacamento e personalidade visual unica para este cliente.",
  "sections": [
    {
      "name": "hero",
      "layout_type": "hero-split",
      "required": true,
      "components": ["h1 com nome e cidade", "subtitulo especifico", "cta whatsapp"],
      "data_source": "Hunter V2",
      "copy": {
        "h1": "texto exato do h1",
        "subtitulo": "texto do subtitulo",
        "cta": "texto do botao"
      }
    }
  ],
  "animations": [
    {"name": "hero-entrance", "type": "fade-up", "target": "#hero h1", "trigger": "load", "duration": "0.8s", "easing": "ease-out"},
    {"name": "cards-stagger", "type": "stagger-fade", "target": ".card", "trigger": "scroll", "duration": "0.6s", "easing": "ease-out"},
    {"name": "cta-pulse", "type": "pulse", "target": ".btn-primary", "trigger": "scroll", "duration": "2s", "easing": "ease-in-out"},
    {"name": "counter", "type": "counter", "target": ".stat-number", "trigger": "scroll", "duration": "1.5s", "easing": "ease-out"},
    {"name": "reveal-sections", "type": "reveal", "target": "section", "trigger": "scroll", "duration": "0.7s", "easing": "ease-out"}
  ],
  "google_maps_embed": "URL do maps ou vazio",
  "hours": {},
  "photos": [],
  "logo_url": null,
  "components_21dev": ["whatsapp-sticky-cta", "floating-rating-badge"],
  "jina_insights": "",
  "competitor_analysis": "",
  "anti_patterns": ["precos visiveis", "depoimentos fabricados", "lorem ipsum"],
  "schema_org_types": ["LocalBusiness"]
}

Para cada secao (hero, sobre, servicos, depoimentos, localizacao, contato, footer), inclua os campos "layout_type" e "copy" com os textos reais especificos para o negocio.
Se reviews_list estiver vazio, a secao depoimentos deve ter "omitir": true no objeto da secao.

RESTRICAO TECNICA ABSOLUTA: O destino final e HTML/Tailwind ESTATICO puro. E ESTRITAMENTE PROIBIDO solicitar React, Vue, JSX, componentes funcionais, hooks, useState, npm install ou qualquer biblioteca JS complexa. O Liam gera apenas HTML + Tailwind CDN + Vanilla JS."""

SYSTEM_COPY_MARKDOWN = """Voce e o Copywriter Senior da FraLib. Sua unica funcao e escrever copy especifica para secoes de sites locais.

REGRAS ABSOLUTAS:
1. Retorne APENAS Markdown estruturado no formato pedido. Nenhum JSON.
2. Nao use code blocks.
3. Use APENAS dados reais fornecidos. NUNCA invente nomes, enderecos, telefones ou depoimentos.
4. Copy de cada secao deve ser especifica para o negocio, sem frases genericas intercambiaveis.
5. NUNCA mencione precos, valores ou mensalidades.
6. O destino final e HTML/Tailwind ESTATICO puro. Nao solicite React, Vue, JSX, hooks, npm install ou biblioteca JS complexa."""


import hashlib as _hashlib_am

_LAYOUT_OPTIONS_AM = {
    'hero':        ['hero-split', 'hero-center', 'hero-fullscreen', 'hero-diagonal'],
    'sobre':       ['sobre-timeline', 'sobre-grid', 'sobre-cards'],
    'servicos':    ['services-cards', 'services-accordion', 'services-grid-icons', 'services-list'],
    'depoimentos': ['reviews-masonry', 'reviews-carousel', 'reviews-grid'],
    'localizacao': ['location-split', 'location-full', 'location-card'],
    'contato':     ['contact-minimal', 'contact-split', 'contact-card'],
}

def _garantir_layout_type(sections: list, nome_negocio: str) -> list:
    """Garante layout_type valido em cada secao usando seed do nome."""
    seed = int(_hashlib_am.md5(nome_negocio.encode()).hexdigest()[:8], 16)
    result = []
    for i, s in enumerate(sections):
        s = dict(s) if not isinstance(s, dict) else s
        nome_s = s.get('name', '').lower()
        layout_atual = s.get('layout_type', '')
        opcoes = _LAYOUT_OPTIONS_AM.get(nome_s, [])
        if opcoes and (not layout_atual or layout_atual == 'padrao' or layout_atual not in opcoes):
            idx = (seed + i * 7) % len(opcoes)
            s['layout_type'] = opcoes[idx]
        result.append(s)
    return result


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
) -> DesignerPRD:
    """
    Gera PRD completo fundindo estrategia + design em um unico passe.

    Args:
        dados_hunter: dict com nome, telefone, endereco, rating, reviews, fotos, logo_url
        cidade: cidade do negocio
        segmento: segmento do negocio
        jina_insights: insights de mercado do Jina AI
        caio_tier: PREMIUM / STANDARD / BASIC
        caio_score: score do Caio (0-100)
        caio_motivo: justificativa do Caio

    Returns:
        DesignerPRD validado com dados reais
    """
    # PRD #8: Semantic Cache — reutilizar PRD se nicho+tier+direction já existe
    try:
        from prd_cache import buscar_prd_cache, adaptar_prd_template
        from design_context import get_design_context
        _dc = get_design_context(segmento, dados_hunter.get("nome", ""))
        _direction = _dc.get("direction", "default") if _dc else "default"
        _cache_entry = buscar_prd_cache(segmento, caio_tier, _direction)
        if _cache_entry:
            _prd_adaptado = adaptar_prd_template(_cache_entry, dados_hunter, briefing_theo)
            if _prd_adaptado and isinstance(_prd_adaptado, dict):
                _prd_adaptado["_cache_hit"] = True
                _prd_adaptado["_cache_key"] = _cache_entry.get("key")
                return DesignerPRD(**_prd_adaptado) if not isinstance(_prd_adaptado, DesignerPRD) else _prd_adaptado
    except Exception as _cache_err:
        print(f"[CACHE] Erro no lookup (gerando normal): {_cache_err}")

    # Google Suggest: termos reais do nicho para enriquecer copy e SEO
    google_suggest_terms = _buscar_google_suggest(segmento, cidade)
    suggest_fmt = ", ".join(google_suggest_terms) if google_suggest_terms else "nao disponivel"
    print("[ArquitetoMestre] Google Suggest:", suggest_fmt[:80])

    # Extrair dados estruturados da Jina (FAQ, keywords, value_props)
    _jina_dados = _extrair_dados_jina(jina_insights or "")
    _jina_keywords = _jina_dados.get('seo_keywords', [])
    _jina_faq = _jina_dados.get('faq_questions', [])
    _jina_value_props = _jina_dados.get('value_props', [])
    if _jina_keywords:
        print("[ArquitetoMestre] Jina keywords extraidas:", len(_jina_keywords))
    if _jina_faq:
        print("[ArquitetoMestre] Jina FAQ extraido:", len(_jina_faq), "perguntas")

    # Design context primeiro — define tokens OKLch e tipografia
    # Selecionar slug do Open Design ANTES pra unificar cores + referência criativa
    _od_result = select_design_system(segmento, dados_hunter.get("nome", ""), caio_tier)
    _od_slug = _od_result.get("slug", "")
    _design_dict = get_design_context(segmento, dados_hunter.get("nome", ""), caio_tier, dark_mode, od_slug=_od_slug)

    # Sub-nicho: detectar a partir dos dados do Google
    from design_context import detectar_sub_nicho
    _sub_nicho = detectar_sub_nicho(segmento, dados_hunter)
    if _sub_nicho.get("sub_nicho"):
        print(f"[ArquitetoMestre] Sub-nicho detectado: {segmento}/{_sub_nicho['sub_nicho']} (tom: {_sub_nicho['tom'][:40]})")

    # Cores vem exclusivamente do design_context (tokens OKLch)

    # Formatar reviews reais
    # Separar reviews: top 3 pro site + insights pra inteligência
    reviews_reais = dados_hunter.get("reviews") or []
    _reviews_separados = selecionar_top_reviews(reviews_reais)
    _top_3 = _reviews_separados["top_3"]
    _reviews_insights_arq = _reviews_separados["insights"]

    reviews_fmt = ""
    if _top_3:
        reviews_fmt = "\n".join([
            f'- "{r.get("texto", r.get("text", ""))}" — {r.get("autor", r.get("author", "Cliente"))}'
            for r in _top_3
        ])
    else:
        reviews_fmt = "NENHUM REVIEW DISPONIVEL — campo reviews_list deve ser []"

    # Contexto de inteligência dos reviews (pra melhorar copy de TODAS as seções)
    _reviews_intel_ctx = ""
    if _reviews_insights_arq["total_reviews"] > 0:
        _reviews_intel_ctx = (
            f"\n=== INTELIGÊNCIA DOS REVIEWS ({_reviews_insights_arq['total_reviews']} avaliações, nota {_reviews_insights_arq['nota_media']}/5) ===\n"
            f"O que clientes ELOGIAM: {', '.join(_reviews_insights_arq['elogios_resumo'][:3])}\n"
            f"O que clientes RECLAMAM: {', '.join(_reviews_insights_arq['reclamacoes_resumo'][:2]) if _reviews_insights_arq['reclamacoes_resumo'] else 'nada relevante'}\n"
            f"Palavras mais citadas: {', '.join(_reviews_insights_arq['palavras_frequentes'][:8])}\n"
            f"Diferencial detectado: {_reviews_insights_arq['diferencial_detectado']}\n"
            f"REGRA: Use esses insights pra enriquecer copy do hero, sobre e serviços. Mencione elogios reais. Evite mencionar reclamações.\n"
            f"=== FIM INTELIGÊNCIA REVIEWS ===\n"
        )

    # Fotos disponiveis
    fotos = dados_hunter.get("fotos") or []
    fotos_fmt = "\n".join(fotos[:6]) if fotos else "Nenhuma foto disponivel"

    # Montar contextos Open Design
    _brief_estruturado = _montar_brief_estruturado(dados_hunter, cidade, segmento, caio_tier, caio_score)
    _design_ctx = get_design_context_prompt(segmento, dados_hunter.get("nome", ""), caio_tier, dark_mode, od_slug=_od_slug)  # string para prompt
    _craft_ctx = get_craft_rules()
    _autocritica_ctx = get_autocritica()
    _seo_ctx = get_seo_context(segmento, cidade, dados_hunter.get("nome", ""))

    # Sub-nicho: injetar no prompt pra direcionar tom e copy
    _sub_nicho_ctx = ""
    if _sub_nicho.get("sub_nicho"):
        _sub_nicho_ctx = (
            f"\n=== SUB-NICHO DETECTADO (OBRIGATORIO seguir) ===\n"
            f"Segmento: {segmento} | Sub-nicho: {_sub_nicho['sub_nicho']}\n"
            f"Tom de comunicação: {_sub_nicho['tom']}\n"
            f"Público-alvo: {_sub_nicho['publico']}\n"
            f"CTA principal sugerido: {_sub_nicho['cta']}\n"
            f"REGRA: Todo copy, H1, subtítulo e CTA DEVEM se comunicar com este público específico.\n"
            f"NÃO use tom genérico. Fale diretamente com {_sub_nicho['publico']}.\n"
            f"=== FIM SUB-NICHO ===\n"
        )

    # Open Design: referência criativa de design system real por segmento
    _open_design_ref = get_open_design_prompt(segmento, dados_hunter.get("nome", ""), caio_tier)
    if _open_design_ref:
        print(f"[ArquitetoMestre] Open Design ref carregada para {segmento}")

    # Keyword research (cache 30 dias) — intenção transacional real
    keyword_research_fmt = ""
    if keyword_research:
        keyword_research_fmt = keyword_research + "\n"

    # FAQ obrigatório para SEO de IA (Google SGE, ChatGPT, Perplexity)
    # Combina: FAQ do seo_context (nicho) + FAQ extraído da Jina + perguntas do lead real
    from seo_context import SEO_NICHOS, ALIASES
    _seg_alias = ALIASES.get(segmento.lower().replace(" ","_").replace("-","_"), segmento.lower().replace(" ","_"))
    _seo_nicho = SEO_NICHOS.get(_seg_alias, {})
    _faq_nicho = _seo_nicho.get("faq", ["Como entrar em contato?", "Qual o horario?", "Onde fica?"])
    _faq_jina = _jina_faq[:3] if _jina_faq else []
    _faq_combinado = list(dict.fromkeys(_faq_nicho + _faq_jina))[:8]
    faq_seo_fmt = "FAQ OBRIGATORIO PARA SEO DE IA (Google SGE, ChatGPT, Perplexity — inclua secao FAQ no site):\n"
    faq_seo_fmt += "\n".join(f"  Q: {q}" for q in _faq_combinado)
    faq_seo_fmt += "\nREGRA: A secao FAQ deve usar markup schema.org FAQPage (JSON-LD) para aparecer nos resultados de IA."


    # ================================================================
    # BLOCO 1 — Design + Estrutura (sem copy) — ~2000 tokens output
    # ================================================================
    _nome = dados_hunter.get("nome", "")
    _tel = dados_hunter.get("telefone", "")
    _end = dados_hunter.get("endereco", "")
    _rating = dados_hunter.get("rating", 0)
    _total_av = dados_hunter.get("total_avaliacoes", 0)

    # Injetar inteligência de mercado no prompt (se disponível)
    _intel_ctx = ""
    if inteligencia:
        _conc = inteligencia.get("concorrencia", {})
        _rev_ins = inteligencia.get("reviews_insights", {})
        _seo = inteligencia.get("seo", {})
        _servicos_r = inteligencia.get("servicos_reais", [])

        if _conc.get("padroes_mercado"):
            _pm = _conc["padroes_mercado"]
            _intel_ctx += f"\n=== INTELIGENCIA DE MERCADO ===\n"
            _intel_ctx += f"Tema dominante concorrentes: {_pm.get('tema_dominante', 'N/A')}\n"
            _intel_ctx += f"Fonte H1 dominante: {_pm.get('fonte_h1_dominante', 'N/A')}\n"
            _intel_ctx += f"CTAs encontrados: {', '.join(_pm.get('ctas_encontrados', [])[:3])}\n"
            # Headlines dos concorrentes
            _h1s = [c.get("h1_text", "") for c in _conc.get("concorrentes", []) if c.get("h1_text")]
            if _h1s:
                _intel_ctx += f"Headlines concorrentes: {' | '.join(_h1s[:3])}\n"

        if _rev_ins.get("palavras_frequentes"):
            _intel_ctx += f"Palavras mais citadas em reviews: {', '.join(_rev_ins['palavras_frequentes'][:8])}\n"
        if _rev_ins.get("diferencial_detectado"):
            _intel_ctx += f"Diferencial detectado nos reviews: {_rev_ins['diferencial_detectado']}\n"
        if _rev_ins.get("elogios"):
            _intel_ctx += f"Elogios reais: {_rev_ins['elogios'][0][:100]}\n"

        if _servicos_r:
            _intel_ctx += f"Servicos CONFIRMADOS no Maps: {', '.join(s['titulo'] for s in _servicos_r[:6])}\n"
            _intel_ctx += "REGRA: Use APENAS estes servicos. NAO invente servicos que nao estao listados.\n"

        if _seo.get("h1_sugerido"):
            _intel_ctx += f"H1 sugerido (SEO): {_seo['h1_sugerido']}\n"
        if _seo.get("people_also_ask"):
            _intel_ctx += f"People Also Ask (usar no FAQ): {' | '.join(_seo['people_also_ask'][:4])}\n"

        _intel_ctx += "=== FIM INTELIGENCIA ===\n"

    prompt_bloco1 = f"""Voce e o Diretor de Arte. Defina a estrutura e direcao criativa do site.

NEGOCIO: {_nome}
CIDADE: {cidade}
SEGMENTO: {segmento}
TIER: {caio_tier} (score={caio_score})
RATING: {_rating}/5 ({_total_av} avaliacoes)
{_intel_ctx}
{_sub_nicho_ctx}
{_design_ctx}

{_craft_ctx}

{_open_design_ref}

TOKENS CSS OBRIGATORIOS:
  --bg: {_design_dict["tokens"]["--bg"]}
  --surface: {_design_dict["tokens"]["--surface"]}
  --fg: {_design_dict["tokens"]["--fg"]}
  --muted: {_design_dict["tokens"]["--muted"]}
  --border: {_design_dict["tokens"]["--border"]}
  --accent: {_design_dict["tokens"]["--accent"]}
TIPOGRAFIA: heading={_design_dict["font_heading"]} body={_design_dict["font_body"]}
ANIMACAO: {_design_dict["animation"]}

Retorne em MARKDOWN ESTRUTURADO (nao JSON). Use EXATAMENTE este formato:

business_name: {_nome}
layout_type: (um de: brutalist/editorial/organic/corporate/minimal)

## INSTRUCAO CRIATIVA
(escreva aqui 2-3 paragrafos com a direcao visual detalhada para o desenvolvedor: vibe, cores, espacamento, personalidade visual unica. Termine com a linha: CSS VARS CONFIRMADAS: --color-primary:X --color-background:Y --color-accent:Z --color-text:W)

## SECOES
- hero | (hero-split ou hero-center ou hero-fullscreen ou hero-diagonal)
- sobre | (sobre-timeline ou sobre-grid ou sobre-cards)
- servicos | (services-cards ou services-accordion ou services-grid-icons ou services-list)
- depoimentos | (reviews-masonry ou reviews-carousel ou reviews-grid)
- faq | services-accordion
- localizacao | (location-split ou location-full ou location-card)
- contato | (contact-minimal ou contact-split ou contact-card)
- footer | (footer-3col ou footer-2col ou footer-centered ou footer-darkbar)

REGRAS DE VARIACAO POR NICHO:
- Restaurante/Bar: hero-fullscreen + foto comida, depoimentos ANTES de servicos se rating > 4.5
- Profissional saude: hero-split + foto profissional, sobre LOGO apos hero
- Academia/Fitness: hero-fullscreen dark + tipografia bold gigante
- Salao/Estetica: hero-diagonal editorial + galeria antes/depois
- Servico urgente (encanador, eletricista): contato ANTES de servicos

MARKDOWN APENAS. Sem JSON. Sem code blocks."""

    print(f"[ArquitetoMestre] Bloco 1: estrutura para {_nome}...")
    import re as _re_ctrl
    _resp1 = call_claude(system=SYSTEM_ARQUITETO, user=prompt_bloco1, model="sonnet", max_tokens=3000, temperature=0.3, agent_name="arquiteto_mestre")
    _resp1 = _re_ctrl.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', _resp1)
    _dados1 = parse_bloco1_with_fallback(_resp1)
    if _dados1 and _dados1.get("sections"):
        _sections_estrutura = _dados1.get("sections", [])
        _layout_type = _dados1.get("layout_type", "corporate")
        _instrucao = _dados1.get("instrucao_criativa_para_dev", "")
        print(f"[ArquitetoMestre] Bloco 1 OK: {len(_sections_estrutura)} secoes, layout={_layout_type}")
    else:
        print(f"[ArquitetoMestre] Bloco 1: parse falhou — usando estrutura padrao")
        _sections_estrutura = [
            {"name": "hero", "layout_type": "hero-split", "required": True},
            {"name": "sobre", "layout_type": "padrao", "required": True},
            {"name": "servicos", "layout_type": "padrao", "required": True},
            {"name": "depoimentos", "layout_type": "padrao", "required": True},
            {"name": "faq", "layout_type": "services-accordion", "required": True},
            {"name": "localizacao", "layout_type": "padrao", "required": True},
            {"name": "contato", "layout_type": "padrao", "required": True},
        ]
        _layout_type = "corporate"
        _instrucao = f"Site premium para {_nome} em {cidade}."

    # ================================================================
    # BLOCO 2 — Copy de cada secao — ~5000 tokens output
    # ================================================================
    _secoes_nomes = [s.get("name", "") for s in _sections_estrutura if s.get("name")]
    _reviews_has = bool(reviews_reais)

    prompt_bloco2 = f"""Voce e o Copywriter Senior. Escreva o copy de cada secao do site.

NEGOCIO: {_nome}
CIDADE: {cidade}
SEGMENTO: {segmento}
TELEFONE: {_tel}
ENDERECO: {_end}
RATING: {_rating}/5 ({_total_av} avaliacoes)
TIER: {caio_tier}
MODO VISUAL: {"DARK" if dark_mode else "LIGHT"}

DIRECAO CRIATIVA: {_instrucao[:500]}
{_intel_ctx}
{_reviews_intel_ctx}
REGRAS DE COPY:
- NUNCA usar: "atendimento personalizado", "qualidade e compromisso", "resultados reais", "pronto para comecar", "os melhores profissionais"
- CTAs: variar entre secoes (NUNCA repetir mesmo texto 2x). Hero=urgencia, Servicos=curiosidade, Depoimentos=desejo, Contato=escassez
- Copy geo-especifica: mencionar bairro/rua/pontos de referencia (minimo 3 mencoes geograficas)
- Secao SOBRE: usar elogios reais dos reviews + diferencial detectado. Contar historia REAL.
- Secao SERVICOS: usar APENAS servicos confirmados no Maps (listados acima). NAO inventar.
- Secao FAQ: usar People Also Ask como perguntas (se disponivel). Respostas com nome do negocio + localidade.

REVIEWS REAIS:
{reviews_fmt}

{_seo_ctx}
{faq_seo_fmt}
{keyword_research_fmt}

SECOES A GERAR: {", ".join(_secoes_nomes)}
{"IMPORTANTE: secao depoimentos tem reviews reais — use-os." if _reviews_has else "IMPORTANTE: secao depoimentos — adicione omitir:true pois nao ha reviews."}

Retorne MARKDOWN ESTRUTURADO com EXATAMENTE este formato:

## hero
h1: titulo principal com cidade
subtitulo: subtitulo persuasivo
cta: texto do botao CTA
eyebrow: tag acima do h1

## sobre
h2: titulo da secao
body: texto curto e especifico
cta: texto do botao CTA

## servicos
h2: titulo da secao
body: texto curto e especifico
items: lista curta dos servicos reais, separados por ponto e virgula
cta: texto do botao CTA

## depoimentos
omitir: {"false" if _reviews_has else "true"}
h2: titulo da secao
body: texto curto, usando apenas reviews reais quando existirem

## faq
h2: titulo da secao
body: perguntas e respostas curtas baseadas no contexto real

## localizacao
h2: titulo da secao
body: texto com endereco real quando disponivel
cta: texto do botao CTA

## contato
h2: titulo da secao
body: texto com telefone real quando disponivel
cta: texto do botao CTA
REGRAS CRAFT (obrigatorias):
{_craft_ctx}

{_autocritica_ctx}

REGRAS:
- H1 OBRIGATORIO: deve ter 8+ palavras com beneficio + cidade. Exemplo: "Nutricao personalizada para sua saude em {cidade}". NUNCA apenas o nome do negocio.
- Telefone real: {_tel}
- Copy especifico para {_nome}, nunca generico
- No campo omitir, use exatamente true ou false.
- MARKDOWN APENAS. Sem JSON. Sem code blocks."""

    print(f"[ArquitetoMestre] Bloco 2: copy para {len(_secoes_nomes)} secoes...")
    _resp2 = call_claude(system=SYSTEM_COPY_MARKDOWN, user=prompt_bloco2, model="sonnet", max_tokens=6000, temperature=0.4, agent_name="arquiteto_mestre")
    _resp2 = _re_ctrl.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', _resp2)
    _dados2 = parse_bloco2_with_fallback(_resp2)
    if _dados2 and _dados2.get("sections"):
        _sections_copy = _dados2.get("sections", [])
        print(f"[ArquitetoMestre] Bloco 2 OK: {len(_sections_copy)} secoes com copy")
    else:
        print(f"[ArquitetoMestre] Bloco 2: parse falhou — usando copy minimo")
        _sections_copy = []

    # ================================================================
    # MERGE: combinar estrutura (bloco1) + copy (bloco2)
    # ================================================================
    _copy_map = {s.get("name", ""): s.get("copy", {}) for s in _sections_copy}
    _omitir_map = {s.get("name", ""): s.get("omitir", False) for s in _sections_copy}
    sections_final = []
    for s in _sections_estrutura:
        nome_s = s.get("name", "")
        sec = dict(s)
        sec["copy"] = _copy_map.get(nome_s, {"h2": nome_s.capitalize(), "cta": "Fale Conosco"})
        sec["omitir"] = _omitir_map.get(nome_s, False)
        sections_final.append(sec)

    dados = {
        "business_name": _nome,
        "layout_type": _layout_type,
        "instrucao_criativa_para_dev": _instrucao,
        "sections": _garantir_layout_type(sections_final, _nome),
    }

    # Garantir reviews reais no objeto final
    if not dados.get("reviews_list"):
        dados["reviews_list"] = reviews_reais

    # Paleta: tokens OKLch do design_context têm prioridade absoluta.
    _tokens = _design_dict["tokens"]
    _tokens["_craft"] = _design_dict.get("craft", {})  # Craft profile (spacing/typography/rhythm)
    _tokens["_animation_profile"] = _design_dict.get("animation_profile", {})
    dados["color_palette"] = {
        "primary":   _tokens["--fg"],
        "secondary": _tokens["--surface"],
        "accent":    _tokens["--accent"],
        "background":_tokens["--bg"],
        "text":      _tokens["--fg"],
        "surface":   _tokens["--surface"],
        "muted":     _tokens["--muted"],
        "border":    _tokens["--border"],
        "tokens_oklch": _tokens,  # 6 tokens + craft + animation para o Liam
        "hero_style": _design_dict.get("hero_style") or get_hero_style(_design_dict["dir_key"]),  # hero variado por lead
        "reasoning": f"OKLch determinístico. Direção={_design_dict['dir_nome']} Nicho={segmento} Tier={caio_tier}.",
    }

    # Garantir campos obrigatorios
    dados.setdefault("business_name", dados_hunter.get("nome", ""))
    dados["segmento"] = segmento or dados.get("segmento") or ""
    dados["cidade"] = cidade or dados.get("cidade") or ""
    dados["sub_nicho"] = _sub_nicho  # Sub-nicho detectado (tom, publico, cta)
    dados.setdefault("address", dados_hunter.get("endereco", ""))
    dados.setdefault("phone", dados_hunter.get("telefone", ""))
    dados.setdefault("rating", float(dados_hunter.get("rating", 0)))
    dados.setdefault("reviews_rating", float(dados_hunter.get("rating", 0)))
    dados.setdefault("reviews_count", int(dados_hunter.get("total_avaliacoes", 0)))
    # SEO keywords: Jina keywords (priority) + base + Google Suggest
    _kw_base = [segmento, f"{segmento} {cidade}", f"melhor {segmento} {cidade}"]
    _kw_suggest = google_suggest_terms[:5] if google_suggest_terms else []
    dados["seo_keywords"] = list(dict.fromkeys(_jina_keywords + _kw_base + _kw_suggest))
    # FAQ combinado: nicho (seo_context) + Jina — garante FAQ mesmo sem Jina
    dados["faq_questions"] = _faq_combinado
    dados["value_props"] = _jina_value_props
    # Geo coordinates from Hunter data
    _lat = dados_hunter.get("lat") or dados_hunter.get("latitude")
    _lng = dados_hunter.get("lng") or dados_hunter.get("longitude") or dados_hunter.get("lon")
    if _lat is not None and _lng is not None:
        try:
            dados["geo"] = {"lat": float(_lat), "lng": float(_lng)}
        except (TypeError, ValueError):
            pass
    # Place ID do Google Maps (pra embed e link correto)
    _place_id = dados_hunter.get("place_id") or ""
    if _place_id:
        dados["place_id"] = _place_id
    # Tipografia do design_context — nunca fallback genérico
    dados["typography"] = {"heading": _design_dict["font_heading"], "body": _design_dict["font_body"]}
    dados.setdefault("animations", [])
    dados.setdefault("google_maps_embed", "")
    # Dados reais do Hunter — passados intactos pro Liam
    _horarios_raw = dados_hunter.get("horarios") or {}
    if isinstance(_horarios_raw, list):
        _horarios_dict = {}
        for h in _horarios_raw:
            if isinstance(h, str) and h.strip():
                parts = h.split("\t") if "\t" in h else h.split("  ")
                if len(parts) >= 2:
                    _horarios_dict[parts[0].strip()] = parts[1].strip()
                else:
                    _horarios_dict[h.strip()] = ""
        _horarios_raw = _horarios_dict
    dados["hours"] = _horarios_raw
    dados["servicos"] = dados_hunter.get("servicos") or []
    dados["atributos"] = dados_hunter.get("atributos") or []
    dados["faixa_preco"] = dados_hunter.get("faixa_preco") or ""
    dados.setdefault("photos", fotos)
    # Garantir reviews reais no PRD (fallback para o Liam)
    dados["_raw_reviews"] = reviews_reais
    _logo_hunter = dados_hunter.get("logo_url") or ""
    if _logo_hunter:
        dados["logo_url"] = _logo_hunter
    elif not dados.get("logo_url"):
        dados["logo_url"] = None
    dados.setdefault("components_21dev", ["whatsapp-sticky-cta"])
    dados.setdefault("jina_insights", jina_insights[:500] if jina_insights else "")
    dados.setdefault("competitor_analysis", "")
    dados.setdefault("anti_patterns", ["precos visiveis"])
    dados.setdefault("instrucao_criativa_para_dev", "Siga o padrao corporativo moderno e clean.")
    dados.setdefault("schema_org_types", ["LocalBusiness"])
    dados["dark_mode"] = dark_mode

    # ═══ DESIGN TOKENS — Single Source of Truth para o Builder (Step 2) ═══
    # Resolve archetype from dir_key using DIRECAO_TO_ARCHETYPE mapping
    _dir_key = _design_dict.get("dir_key", "")
    _archetype_map = {
        "industrial": "industrial-bold", "bold": "industrial-bold", "neobold": "industrial-bold",
        "neon-industrial": "industrial-bold", "tech-bold": "industrial-bold", "construct": "industrial-bold",
        "editorial": "editorial-asymmetric", "minimal": "apple-minimalist", "minimal-clean": "apple-minimalist",
        "apple": "apple-minimalist", "futurist": "dark-futurist", "dark-futurist": "dark-futurist",
        "cyber": "dark-futurist", "organic": "organic-warm", "warm": "organic-warm", "earth": "organic-warm",
        "corporate": "corporate-trust", "trust": "corporate-trust", "luxury": "corporate-trust",
        "brutal": "brutal-bold", "brutalism": "brutal-bold", "raw": "brutal-bold",
        "elegant": "luxury-sophisticated", "haute": "luxury-sophisticated",
        "friendly": "friendly-playful", "playful": "friendly-playful", "fun": "friendly-playful",
        "energetic": "energetic-vibrant", "vibrant": "energetic-vibrant", "pop": "energetic-vibrant",
        "neomorphic": "neomorphic-soft", "soft": "neomorphic-soft", "clay": "neomorphic-soft",
        "glass": "glassmorphism", "glassmorphism": "glassmorphism", "frosted": "glassmorphism",
        "clean": "apple-minimalist", "tech": "dark-futurist", "modern": "corporate-trust",
    }
    _archetype = _archetype_map.get(_dir_key, "editorial-asymmetric")
    dados["design_tokens"] = {
        "dir_key": _dir_key,
        "archetype": _archetype,
        "tokens": _tokens,
        "hero_style": dados["color_palette"].get("hero_style"),
    }

    # Se dados nao tem sections, fazer segunda chamada focada em Markdown estruturado
    if not dados.get('sections') or not isinstance(dados.get('sections'), list) or len(dados.get('sections', [])) == 0:
        print(f"[ArquitetoMestre] Markdown sem sections — segunda chamada focada")
        _prompt_retry = (
            f"Gere APENAS MARKDOWN ESTRUTURADO para o site de: {dados_hunter.get('nome', '')} em {cidade} ({segmento}).\n"
            f"Telefone: {dados_hunter.get('telefone', '')} | Rating: {dados_hunter.get('rating', 0)}/5 | Tier: {caio_tier}\n"
            f"Retorne as secoes em markdown no formato:\n"
            f"## hero\nh1: ...\nsubtitulo: ...\ncta: ...\neyebrow: ...\n\n"
            f"## sobre\nh2: ...\nbody: ...\ncta: ...\n\n"
            f"## servicos\nh2: ...\nbody: ...\nitems: ...\ncta: ...\n\n"
            f"## depoimentos\nomitir: true|false\nh2: ...\nbody: ...\n\n"
            f"## faq\nh2: ...\nbody: ...\n\n"
            f"## localizacao\nh2: ...\nbody: ...\ncta: ...\n\n"
            f"## contato\nh2: ...\nbody: ...\ncta: ...\n"
            f"MARKDOWN APENAS, sem JSON, sem explicacao."
        )
        _resp2 = call_claude(
            system=SYSTEM_COPY_MARKDOWN,
            user=_prompt_retry,
            model="sonnet",
            max_tokens=16000,
            temperature=0.2,
        )
        import re as _re2
        _resp2 = _re2.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", _resp2)
        _dados_retry = parse_bloco2_with_fallback(_resp2)
        try:
            if _dados_retry and _dados_retry.get("sections"):
                _copy_map2 = {s.get("name", ""): s.get("copy", {}) for s in _dados_retry.get("sections", [])}
                _omitir_map2 = {s.get("name", ""): s.get("omitir", False) for s in _dados_retry.get("sections", [])}
                _sections_retry = []
                for s in _sections_estrutura:
                    nome_s = s.get("name", "")
                    sec = dict(s)
                    sec["copy"] = _copy_map2.get(nome_s, sec.get("copy", {"h2": nome_s.capitalize(), "cta": "Fale Conosco"}))
                    sec["omitir"] = _omitir_map2.get(nome_s, sec.get("omitir", False))
                    _sections_retry.append(sec)
                dados["sections"] = _garantir_layout_type(_sections_retry, dados.get("business_name", dados_hunter.get("nome", "")))
                print(f"[ArquitetoMestre] Segunda chamada: {len(dados.get('sections', []))} secoes")
            else:
                print("[ArquitetoMestre] Segunda chamada falhou: markdown sem sections")
        except Exception as _e2:
            print(f"[ArquitetoMestre] Segunda chamada falhou: {_e2}")

    print(f"[ArquitetoMestre] PRD gerado: {len(dados.get('sections', []))} secoes, {len(dados.get('reviews_list', []))} reviews reais")

    prd = DesignerPRD(**dados)
    _validar_prd_minimo(prd)
    return prd
