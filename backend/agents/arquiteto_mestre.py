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
from color_enforcer import harmonizar_paleta
from designer_prd import DesignerPRD, ColorPalette, AnimationSpec, SectionSpec


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
6. CORES E BACKGROUND: O BRIEFING DO THEO tem prioridade absoluta para definir background e paleta. Leia o briefing estrategico fornecido e extraia a direcao visual indicada. Se o briefing nao especificar, use os INSIGHTS DE MERCADO (Jina AI) para decidir. Adicione glow (sombras coloridas) nos botoes CTA.
7. DIRECAO DE ARTE DO NICHO: Leia os INSIGHTS DE MERCADO (Jina AI) fornecidos no prompt. Extraia a VIBE VISUAL dominante do segmento (cores que convertem, estilo tipografico, tom emocional). Voce DEVE escolher animation_theme e color_palette baseados nessa vibe — garantindo que cada site seja unico para o segmento.
8. INSTRUCAO CRIATIVA: Com base nos insights da Jina, no briefing do Theo e nos dados do cliente, escreva instrucao unica para o Liam: vibe do site, como aplicar cores (gradientes, glassmorphism, glow), espacamento e personalidade visual. Cada instrucao deve ser radicalmente diferente entre nichos distintos.

FATOR DE VARIANCIA DINAMICA — OBRIGATORIO:
Voce e um Diretor de Arte. Para nao gerar sites repetitivos, voce DEVE escolher uma estrutura visual especifica para cada secao usando o campo "layout_type". NUNCA use a mesma combinacao de estruturas duas vezes para clientes diferentes.

MENU DE LAYOUTS DISPONIVEIS:
- hero: "hero-split" (texto esquerda 60%, imagem direita 40%) | "hero-center" (texto centralizado, bg escuro com overlay)
- sobre: "sobre-timeline" (historia em linha do tempo vertical) | "sobre-grid" (texto esquerda + mosaico de fotos direita)
- servicos: "services-cards" (grid 3 colunas com cards elevados) | "services-accordion" (lista retrátil com icones)
- depoimentos: "reviews-masonry" (cards em masonry 3 colunas) | "reviews-carousel" (carrossel horizontal)
- localizacao: "location-split" (mapa esquerda, info direita) | "location-full" (mapa full-width, info abaixo)
- contato: "contact-minimal" (formulario simples centralizado) | "contact-split" (info esquerda, cta direita)

TEMA DE ANIMACAO GSAP — escolha UM para o site inteiro:
- "energetico": elementos entram rapido (0.3-0.5s), scale-in, bounce leve
- "elegante": fade-up lento (0.8-1.2s), blur-in, sem bounce

Escolha o tema baseado no segmento: academias/barbearias = energetico. Doceria/clinica/atelier = elegante.

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
    "background": "#ffffff",
    "text": "#1f2937",
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


def gerar_arquiteto_mestre_prd(
    dados_hunter: dict,
    cidade: str,
    segmento: str,
    jina_insights: str,
    alex_colors: dict,
    caio_tier: str,
    caio_score: int = 0,
    caio_motivo: str = "",
    briefing_theo: str = "",
) -> DesignerPRD:
    """
    Gera PRD completo fundindo estrategia + design em um unico passe.

    Args:
        dados_hunter: dict com nome, telefone, endereco, rating, reviews, fotos, logo_url
        cidade: cidade do negocio
        segmento: segmento do negocio
        jina_insights: insights de mercado do Jina AI
        alex_colors: paleta extraida pelo Alex (chaves: primaria/acento ou primary/accent)
        caio_tier: PREMIUM / STANDARD / BASIC
        caio_score: score do Caio (0-100)
        caio_motivo: justificativa do Caio

    Returns:
        DesignerPRD validado com dados reais
    """
    # Google Suggest: termos reais do nicho para enriquecer copy e SEO
    google_suggest_terms = _buscar_google_suggest(segmento, cidade)
    suggest_fmt = ", ".join(google_suggest_terms) if google_suggest_terms else "nao disponivel"
    print("[ArquitetoMestre] Google Suggest:", suggest_fmt[:80])

    # Normalizar paleta do Alex (suporta chaves em portugues e ingles)
    _primary = (
        alex_colors.get("primary")
        or alex_colors.get("primaria")
        or "#374151"
    )
    _accent = (
        alex_colors.get("accent")
        or alex_colors.get("acento")
        or "#6366f1"
    )
    paleta_harmonizada = harmonizar_paleta({
        "primary": _primary,
        "secondary": "#f9fafb",
        "accent": _accent,
        "background": "#ffffff",
        "text": "#1f2937",
    })

    # Formatar reviews reais
    reviews_reais = dados_hunter.get("reviews") or []
    reviews_fmt = ""
    if reviews_reais:
        reviews_fmt = "\n".join([
            f'- "{r.get("texto", r.get("text", ""))}" — {r.get("autor", r.get("author", "Cliente"))}'
            for r in reviews_reais[:8]
        ])
    else:
        reviews_fmt = "NENHUM REVIEW DISPONIVEL — campo reviews_list deve ser []"

    # Fotos disponiveis
    fotos = dados_hunter.get("fotos") or []
    fotos_fmt = "\n".join(fotos[:6]) if fotos else "Nenhuma foto disponivel"

    prompt = f"""Gere o JSON completo para o site do seguinte negocio local:

NEGOCIO: {dados_hunter.get("nome", "")}
CIDADE: {cidade}
SEGMENTO: {segmento}
TELEFONE: {dados_hunter.get("telefone", "")}
ENDERECO: {dados_hunter.get("endereco", "")}
RATING: {dados_hunter.get("rating", 0)}/5 ({dados_hunter.get("total_avaliacoes", 0)} avaliacoes)
TIER (qualificacao): {caio_tier} (score={caio_score})
LOGO: {dados_hunter.get("logo_url") or "nao disponivel"}

PALETA DE CORES BASE DO CLIENTE (harmonize para Premium):
- primary: {paleta_harmonizada["primary"]}
- accent: {paleta_harmonizada["accent"]}
- text_on_primary: {paleta_harmonizada["text_on_primary"]}
- text_on_accent: {paleta_harmonizada["text_on_accent"]}
IMPORTANTE: As cores acima sao apenas uma base extraida de fotos. Voce DEVE obrigatoriamente harmoniza-las para uma estetica Premium, Moderna e Viva. NUNCA use cores opacas ou sujas (como marrom escuro chapado). Transforme cores opacas em gradientes modernos ou tons vibrantes. Instrua o Liam a usar gradientes, glassmorphism e sombras suaves.

REVIEWS REAIS:
{reviews_fmt}

FOTOS DISPONIVEIS:
{fotos_fmt}

INSIGHTS DE MERCADO (Jina AI):
{jina_insights[:3000] if jina_insights else "Nao disponivel"}

BRIEFING ESTRATEGICO DO THEO (use como base para copy e direcao criativa):
{briefing_theo[:2000] if briefing_theo else "Nao disponivel"}

TERMOS REAIS PESQUISADOS NO GOOGLE (use para H3, subtitulos e FAQ):
{suggest_fmt}

INSTRUCOES ESPECIAIS:
- Tier {caio_tier}: {"use copy premium, diferenciais exclusivos, linguagem sofisticada" if caio_tier == "PREMIUM" else "use copy direto, foco em resultado e custo-beneficio"}
- Para cada secao, escreva copy ESPECIFICA para {dados_hunter.get("nome", "")} em {cidade}
- Se reviews_list estiver vazio, adicione "omitir": true na secao depoimentos
- Retorne APENAS o JSON. Nenhum texto fora do JSON."""

    print(f"[ArquitetoMestre] Gerando PRD para {dados_hunter.get('nome', '')}...")
    resposta = call_claude(
        system=SYSTEM_ARQUITETO,
        user=prompt,
        model="sonnet",
        max_tokens=12000,
        temperature=0.3,
    )

    # Extrair e parsear JSON
    # Sanitizar caracteres de controle na resposta bruta ANTES do clean_json
    import re as _re_ctrl
    resposta = _re_ctrl.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', resposta)
    json_str = clean_json(resposta)
    # Sanitizar novamente apos clean_json (dupla protecao)
    json_str = _re_ctrl.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', json_str)
    try:
        dados = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"[ArquitetoMestre] Erro JSON parse: {e} — tentando recuperar com segunda chamada")
        # Segunda chamada: pedir JSON mais enxuto sem briefing longo
        prompt_retry = f"""Gere o JSON completo para o site do seguinte negocio local.
NEGOCIO: {dados_hunter.get("nome", "")}
CIDADE: {cidade}
SEGMENTO: {segmento}
TELEFONE: {dados_hunter.get("telefone", "")}
ENDERECO: {dados_hunter.get("endereco", "")}
RATING: {dados_hunter.get("rating", 0)}/5 ({dados_hunter.get("total_avaliacoes", 0)} avaliacoes)
TIER: {caio_tier}
LOGO: {dados_hunter.get("logo_url") or "nao disponivel"}
PALETA: primary={paleta_harmonizada["primary"]} accent={paleta_harmonizada["accent"]}
REVIEWS: {reviews_fmt[:500] if reviews_fmt else "Nenhum"}
INSTRUCAO: Retorne APENAS JSON valido. Inclua obrigatoriamente as sections: hero, sobre, servicos, depoimentos, localizacao, contato, footer. Cada section com name, layout_type e copy especifico para o negocio."""
        resposta2 = call_claude(
            system=SYSTEM_ARQUITETO,
            user=prompt_retry,
            model="sonnet",
            max_tokens=12000,
            temperature=0.2,
        )
        import re as _re_ctrl2
        resposta2 = _re_ctrl2.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', resposta2)
        json_str2 = clean_json(resposta2)
        json_str2 = _re_ctrl2.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', json_str2)
        try:
            dados = json.loads(json_str2)
            print(f"[ArquitetoMestre] Recuperado na segunda chamada: {len(dados.get('sections', []))} secoes")
        except json.JSONDecodeError as e2:
            print(f"[ArquitetoMestre] Segunda chamada tambem falhou: {e2} — abortando pipeline")
            raise RuntimeError(f"ArquitetoMestre nao conseguiu gerar JSON valido apos 2 tentativas: {e2}")

    # Garantir reviews reais no objeto final
    if not dados.get("reviews_list"):
        dados["reviews_list"] = reviews_reais

    # Paleta: Theo tem prioridade absoluta via LLM. Apenas harmonizar primary/accent do Alex.
    _bg_decidido = dados.get("color_palette", {}).get("background", "#ffffff")
    _text_decidido = dados.get("color_palette", {}).get("text", "#1f2937")
    dados["color_palette"] = {
        "primary": paleta_harmonizada["primary"],
        "secondary": dados.get("color_palette", {}).get("secondary", "#f9fafb"),
        "accent": paleta_harmonizada["accent"],
        "background": _bg_decidido,
        "text": _text_decidido,
        "reasoning": f"Paleta harmonizada. Primary={paleta_harmonizada['primary']} Accent={paleta_harmonizada['accent']}. Background={_bg_decidido} (definido pelo Arquiteto via briefing Theo).",
    }

    # Garantir campos obrigatorios
    dados.setdefault("business_name", dados_hunter.get("nome", ""))
    dados.setdefault("address", dados_hunter.get("endereco", ""))
    dados.setdefault("phone", dados_hunter.get("telefone", ""))
    dados.setdefault("reviews_rating", float(dados_hunter.get("rating", 0)))
    dados.setdefault("reviews_count", int(dados_hunter.get("total_avaliacoes", 0)))
    dados.setdefault("typography", {"heading": "Plus Jakarta Sans", "body": "Inter"})
    dados.setdefault("animations", [])
    dados.setdefault("google_maps_embed", "")
    dados.setdefault("hours", {})
    dados.setdefault("photos", fotos)
    dados.setdefault("logo_url", dados_hunter.get("logo_url"))
    dados.setdefault("components_21dev", ["whatsapp-sticky-cta"])
    dados.setdefault("jina_insights", jina_insights[:500] if jina_insights else "")
    dados.setdefault("competitor_analysis", "")
    dados.setdefault("anti_patterns", ["precos visiveis"])
    dados.setdefault("instrucao_criativa_para_dev", "Siga o padrao corporativo moderno e clean.")
    dados.setdefault("schema_org_types", ["LocalBusiness"])

    print(f"[ArquitetoMestre] PRD gerado: {len(dados.get('sections', []))} secoes, {len(dados.get('reviews_list', []))} reviews reais")

    return DesignerPRD(**dados)
