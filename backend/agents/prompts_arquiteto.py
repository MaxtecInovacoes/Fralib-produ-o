"""System prompts, helpers e constantes para o Arquiteto Mestre.
Extraído do arquiteto_mestre.py original para modularização.
"""

import re
import json
import urllib.request
import urllib.parse

from backend.agents._text_utils import strip_control_chars  # noqa: E402,F401  — B2 DRY

SYSTEM_DESIGN_DIRECTOR = """You are the Creative PRD Director at FraLib.

YOUR ROLE: Define content architecture, conversion intent, factual priority,
and compact creative direction for the Builder.

INPUT: Business briefing + SEO + real proof + craft rules + POLO block.
OUTPUT: Structured Markdown with per-section objective, copy intent,
required sections list, and editorial visual brief.

RULES:
- Use the niche briefing as the primary source
- Never invent numbers, testimonials, or results
- Prioritize truth, commercial clarity, local SEO, and contact-driven conversion
- May guide vibe, rhythm, hierarchy, motion, spacing, contrast, and anti-patterns
- Never invent services, team, equipment, prices, or metrics
- If services are not confirmed, do not force a services section; use contato/sobre
  for a brief confirmation note instead
- Layout_type and visual direction are strong briefs for the Builder, not public data
- Include performance observation when applicable
- If a POLO block is present, follow its tokens (radius, font, motion, spacing)
  even when other guidance contradicts them

All user-facing copy MUST be in Brazilian Portuguese (pt-BR)."""

SYSTEM_COPY_SENIOR = """You are the Senior Copywriter at FraLib.

YOUR ONLY ROLE: Write specific copy for local business website sections.

ABSOLUTE RULES:
1. Return ONLY structured Markdown. No JSON.
2. Do not use code blocks.
3. Use ONLY provided real data. NEVER invent.
4. Copy specific to the business - no generic phrases.
5. NEVER mention prices, amounts, or monthly fees.
6. Static HTML/Tailwind only - no React, Vue, JSX.
7. If a POLO block is present, follow the tone/voice/cta_primary it specifies
   over any other style guidance.

All user-facing copy MUST be in Brazilian Portuguese (pt-BR)."""

LAYOUT_OPTIONS = {
    "hero": [
        "hero-split",
        "hero-center",
        "hero-fullscreen",
        "hero-diagonal",
        "hero-video",
    ],
    "sobre": ["sobre-timeline", "sobre-grid", "sobre-cards", "sobre-story"],
    "servicos": [
        "services-cards",
        "services-accordion",
        "services-grid-icons",
        "services-list",
        "services-bento",
    ],
    "depoimentos": [
        "reviews-masonry",
        "reviews-carousel",
        "reviews-grid",
        "reviews-spotlight",
    ],
    "faq": ["faq-accordion", "faq-two-col", "faq-minimal"],
    "localizacao": ["location-split", "location-full", "location-card"],
    "contato": ["contact-minimal", "contact-split", "contact-card"],
    "numeros": ["stats-horizontal", "stats-cards", "stats-big"],
    "galeria": ["gallery-masonry", "gallery-grid", "gallery-carousel"],
    "footer": ["footer-3col", "footer-2col", "footer-centered", "footer-darkbar"],
}

VALID_SECTIONS = (
    "hero",
    "sobre",
    "servicos",
    "depoimentos",
    "faq",
    "localizacao",
    "contato",
    "footer",
)

REQUIRED_SECTIONS = ("hero", "sobre", "contato")


def limpar_texto_review(texto: str) -> str:
    if not texto:
        return ""
    texto = re.sub(
        r"\.\.\.\s*(?:[Mm]ais|[Ll]er\s+[Mm]ais|[Vv]er\s+[Mm]ais|[Vv]er\s+[Tt]udo)\b",
        "",
        texto,
    )
    return texto.strip()


def selecionar_top_reviews(reviews: list, max_site: int = 3) -> dict:
    if not reviews:
        return {
            "top_3": [],
            "insights": {
                "total_reviews": 0,
                "nota_media": 0,
                "elogios_resumo": [],
                "reclamacoes_resumo": [],
                "palavras_frequentes": [],
                "diferencial_detectado": "",
            },
        }
    scored = []
    for r in reviews:
        texto = limpar_texto_review(r.get("texto", r.get("text", "")))
        nota = float(r.get("nota", r.get("rating", r.get("stars", 5))))
        score = nota * 10 + min(len(texto), 200)
        scored.append({"review": r, "score": score, "texto": texto, "nota": nota})
    scored.sort(key=lambda x: x["score"], reverse=True)
    top_3 = [s["review"] for s in scored[:max_site]]
    elogios = [s["texto"][:150] for s in scored if s["nota"] >= 4][:5]
    reclamacoes = [s["texto"][:150] for s in scored if s["nota"] <= 2][:3]
    _stop = {
        "para",
        "como",
        "mais",
        "muito",
        "esse",
        "essa",
        "aqui",
        "lugar",
        "super",
        "legal",
    }
    palavras = {}
    for s in scored:
        for p in s["texto"].lower().split():
            if len(p) > 4 and p not in _stop:
                palavras[p] = palavras.get(p, 0) + 1
    top_palavras = sorted(palavras.items(), key=lambda x: x[1], reverse=True)[:10]
    return {
        "top_3": top_3,
        "insights": {
            "total_reviews": len(reviews),
            "nota_media": round(sum(s["nota"] for s in scored) / len(scored), 1),
            "elogios_resumo": elogios,
            "reclamacoes_resumo": reclamacoes,
            "palavras_frequentes": [p[0] for p in top_palavras],
            "diferencial_detectado": elogios[0][:100] if elogios else "",
        },
    }


def _montar_brief_estruturado(
    dados_hunter: dict, cidade: str, segmento: str, caio_tier: str, caio_score: int
) -> str:
    return f"""
=== BRIEF ESTRUTURADO ===
Nome: {dados_hunter.get("nome", "")} | Segmento: {segmento}
Cidade: {cidade} | Rating: {dados_hunter.get("rating", 0)}/5 ({dados_hunter.get("total_avaliacoes", 0)} avaliacoes)
Telefone: {dados_hunter.get("telefone", "")} | Endereco: {dados_hunter.get("endereco", "")}
Fotos: {len(dados_hunter.get("fotos") or [])} | Reviews: {len(dados_hunter.get("reviews") or [])}
Servicos: {", ".join((dados_hunter.get("servicos") or [])[:8]) or "N/A"}
Atributos: {", ".join((dados_hunter.get("atributos") or [])[:6]) or "N/A"}
Horarios: {dados_hunter.get("horarios") or "N/A"}
TIER: {caio_tier} (score={caio_score})
TIPO: single-page, mobile-first, 6-8 secoes
=== FIM BRIEF ==="""


def clean_json(text: str) -> str:
    text = text.replace("```json", "").replace("```", "").strip()
    text = text.replace("\u2028", " ").replace("\u2029", " ")
    text = strip_control_chars(text)
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
                    candidates.append(text[i : j + 1])
                    break
            j += 1
        i += 1
    return max(candidates, key=len) if candidates else text


def _validar_prd_minimo(prd) -> None:
    if not prd.business_name:
        raise ValueError("PRD invalido: business_name vazio")
    if not prd.sections or len(prd.sections) < 4:
        raise ValueError("PRD invalido: sections insuficientes")
    nomes = {str(s.name).lower() for s in prd.sections}
    obrigatorias = set(REQUIRED_SECTIONS)
    faltando = sorted(obrigatorias - nomes)
    if faltando:
        raise ValueError(
            "PRD invalido: secoes obrigatorias ausentes: " + ", ".join(faltando)
        )
    if not prd.typography:
        raise ValueError("PRD invalido: typography vazio")
    if not prd.color_palette:
        raise ValueError("PRD invalido: color_palette vazio")
    for campo in ("primary", "background", "text", "accent"):
        if not getattr(prd.color_palette, campo, None):
            raise ValueError(f"PRD invalido: color_palette.{campo} vazio")


def _garantir_secoes_obrigatorias(sections: list) -> list:
    """Injeta secoes contratuais se o LLM omitir alguma."""
    sections = [dict(s) for s in (sections or []) if isinstance(s, dict)]
    por_nome = {str(s.get("name", "")).lower(): s for s in sections}
    defaults = {
        "hero": {"name": "hero", "layout_type": "hero-split", "required": True},
        "sobre": {"name": "sobre", "layout_type": "sobre-grid", "required": True},
        "servicos": {
            "name": "servicos",
            "layout_type": "services-cards",
            "required": True,
        },
        "contato": {"name": "contato", "layout_type": "contact-split", "required": True},
    }
    ordered = []
    for name in REQUIRED_SECTIONS:
        ordered.append(por_nome.get(name) or defaults[name])
    for section in sections:
        name = str(section.get("name", "")).lower()
        if name and name not in REQUIRED_SECTIONS:
            ordered.append(section)
    return ordered


def _extrair_dados_jina(jina_insights: str) -> dict:
    """Extrai FAQ, keywords e value_props do bloco estruturado da Jina."""
    result = {"faq_questions": [], "seo_keywords": [], "value_props": []}
    if "=== DADOS ESTRUTURADOS PARA SEO ===" not in jina_insights:
        return result
    try:
        bloco = jina_insights.split("=== DADOS ESTRUTURADOS PARA SEO ===")[1]
        for key in ("faq_questions", "seo_keywords", "value_props"):
            m = re.search(key.upper() + r": (\[.*?\])", bloco, re.DOTALL)
            if m:
                result[key] = json.loads(m.group(1))
    except Exception as e:
        print("[ArquitetoMestre] Aviso: extracao Jina falhou:", e)
    return result


def _buscar_google_suggest(segmento: str, cidade: str) -> list:
    try:
        query = urllib.parse.quote(f"{segmento} {cidade}")
        url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={query}&hl=pt-BR"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [
                s for s in (data[1] if len(data) > 1 else []) if isinstance(s, str)
            ][:10]
    except Exception as e:
        print("[ArquitetoMestre] Google Suggest falhou (nao critico):", e)
        return []


def _garantir_layout_type(sections: list, nome_negocio: str) -> list:
    import hashlib as _h

    seed = int(_h.md5(nome_negocio.encode()).hexdigest()[:8], 16)
    result = []
    for i, s in enumerate(sections):
        s = dict(s) if not isinstance(s, dict) else s
        nome_s = s.get("name", "").lower()
        layout_atual = s.get("layout_type", "")
        opcoes = LAYOUT_OPTIONS.get(nome_s, [])
        if opcoes and (
            not layout_atual or layout_atual == "padrao" or layout_atual not in opcoes
        ):
            s["layout_type"] = opcoes[(seed + i * 7) % len(opcoes)]
        result.append(s)
    return result
