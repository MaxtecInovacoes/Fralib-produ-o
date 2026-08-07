"""open_design_selector.py — Seleciona design system do open-design por segmento.
Usa os 149 DESIGN.md de /root/open-design/design-systems/ como referência criativa
para o ArquitetoMestre gerar sites únicos por nicho.
"""
import os
import re
import hashlib
import json
from typing import Optional

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DS_DIR = os.environ.get("OPEN_DESIGN_DS_DIR", os.path.join(_SCRIPT_DIR, "..", "open-design", "design-systems"))
INDEX_PATH = os.path.join(os.path.dirname(__file__), "open_design_index.json")

# ─── MAPEAMENTO SEGMENTO → SLUGS RELEVANTES ─────────────────────────────────
# Cada segmento tem 4-6 design systems ranqueados por relevância visual.
# O ArquitetoMestre usa o primeiro como referência principal e os demais como
# inspiração secundária para garantir variedade entre sites do mesmo nicho.

SEGMENT_DESIGN_MAP = {
    # Masculino, edgy, confiante
    "barbearia": ["brutalism", "bold", "neobrutalism", "editorial", "warp", "mono"],
    # Acolhedor, apetitoso, local
    "restaurante": ["cafe", "warm-editorial", "airbnb", "friendly", "storytelling"],
    "churrascaria": ["bold", "brutalism", "cafe", "warm-editorial"],
    "pizzaria": ["cafe", "colorful", "friendly", "warm-editorial", "vibrant"],
    "lanchonete": ["colorful", "friendly", "cafe", "duolingo", "vibrant", "bold"],
    "padaria": ["cafe", "warm-editorial", "friendly", "vintage", "paper"],
    # Clínico, confiável, moderno
    "clinica": ["clean", "minimal", "modern", "professional", "stripe", "linear-app"],
    "odontologia": ["clean", "modern", "minimal", "professional", "sleek", "refined"],
    "nutricionista": ["clean", "friendly", "modern", "minimal", "elegant", "warm-editorial"],
    "psicologia": ["warm-editorial", "elegant", "friendly", "clean", "editorial", "refined"],
    # Energético, poderoso, motivador
    "academia": ["energetic", "nike", "bold", "brutalism", "neobrutalism", "spacex"],
    "crossfit": ["brutalism", "bold", "energetic", "nike", "neobrutalism", "dramatic"],
    # Carinhoso, confiável, lúdico
    "pet_shop": ["friendly", "colorful", "duolingo", "warm-editorial", "cafe", "doodle"],
    # Sério, premium, competente
    "advocacia": ["elegant", "editorial", "luxury", "stripe", "premium", "professional"],
    # Sofisticado, pessoal, elegante
    "estetica": ["elegant", "luxury", "premium", "editorial", "refined", "airbnb"],
    "salao_beleza": ["elegant", "editorial", "luxury", "premium", "refined", "artistic"],
    # Funcional, técnico, confiável
    "farmacia": ["clean", "professional", "modern", "stripe", "enterprise", "material"],
    "auto_pecas": ["bold", "modern", "professional", "enterprise", "corporate", "dashboard"],
    # Profissional, local, moderno
    "imobiliaria": ["modern", "stripe", "professional", "airbnb", "sleek", "premium"],
    "contabilidade": ["professional", "stripe", "modern", "enterprise", "corporate", "clean"],
    # Acolhedor, inspirador, confiável
    "escola": ["friendly", "colorful", "duolingo", "warm-editorial", "cafe", "creative"],
}

# Categorias do open-design → segmentos FraLib (fallback para segmentos desconhecidos)
CATEGORY_AFFINITY = {
    "Professional & Corporate": ["clinica", "advocacia", "contabilidade", "imobiliaria", "farmacia"],
    "Bold & Expressive": ["barbearia", "academia", "crossfit"],
    "Creative & Artistic": ["estetica", "salao_beleza", "pet_shop"],
    "Modern & Minimal": ["clinica", "odontologia", "farmacia", "imobiliaria"],
    "E-Commerce & Retail": ["restaurante", "pizzaria"],
    "Fintech & Crypto": ["contabilidade", "imobiliaria"],
    "Morphism & Effects": ["estetica", "salao_beleza"],
    "Retro & Nostalgic": ["barbearia", "padaria"],
}


def _load_index() -> list:
    """Carrega o índice compacto dos design systems."""
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "r") as f:
            return json.load(f)
    return []


def _read_design_md_sections(slug: str, max_sections: int = 3) -> str:
    """Lê as primeiras N seções do DESIGN.md (atmosphere, colors, typography)."""
    path = os.path.join(DS_DIR, slug, "DESIGN.md")
    if not os.path.isfile(path):
        return ""
    
    with open(path, "r") as f:
        content = f.read()
    
    # Encontrar onde começa a seção max_sections+1 e cortar ali
    # Seções são ## 1., ## 2., ## 3., etc.
    cut_pattern = re.compile(r"\n## " + str(max_sections + 1) + r"\.")
    cut_match = cut_pattern.search(content)
    if cut_match:
        result = content[:cut_match.start()]
    else:
        result = content
    
    # Limitar a 2500 chars para não estourar o prompt
    return result[:2500]


def select_design_system(segmento: str, nome_negocio: str = "", tier: str = "STANDARD") -> dict:
    """Seleciona o design system mais adequado para o segmento.
    
    Retorna dict com:
        - slug: nome do design system selecionado
        - content: texto das seções 1-3 do DESIGN.md
        - alternatives: lista de slugs alternativos
        - category: categoria do design system
    """
    from design_context import ALIASES
    
    seg = segmento.lower().replace(" ", "_").replace("-", "_")
    seg = ALIASES.get(seg, seg)
    
    # Buscar slugs mapeados para o segmento
    slugs = SEGMENT_DESIGN_MAP.get(seg, [])
    
    if not slugs:
        # Fallback: usar índice para encontrar design systems por categoria
        slugs = _fallback_slugs_for_segment(seg)
    
    if not slugs:
        slugs = ["modern", "clean", "professional", "elegant"]
    
    # Usar hash do nome do negócio para variar a escolha entre sites do mesmo nicho
    seed = int(hashlib.md5((nome_negocio or segmento).encode()).hexdigest()[:8], 16)
    
    # Tier influencia: PREMIUM pega os mais sofisticados (primeiros), BASIC os mais simples
    tier_offset = {"PREMIUM": 0, "STANDARD": 1, "BASIC": 2}.get(tier.upper(), 1)
    
    # Combinar seed + tier para escolher
    idx = (seed + tier_offset) % len(slugs)
    chosen_slug = slugs[idx]
    
    # Verificar se o slug existe
    if not os.path.isfile(os.path.join(DS_DIR, chosen_slug, "DESIGN.md")):
        # Tentar o próximo
        for s in slugs:
            if os.path.isfile(os.path.join(DS_DIR, s, "DESIGN.md")):
                chosen_slug = s
                break
    
    # Ler conteúdo
    content = _read_design_md_sections(chosen_slug)
    
    # Buscar categoria do índice
    index = _load_index()
    category = ""
    for entry in index:
        if entry["slug"] == chosen_slug:
            category = entry.get("category", "")
            break
    
    # Alternativas (excluindo o escolhido)
    alternatives = [s for s in slugs if s != chosen_slug][:3]
    
    return {
        "slug": chosen_slug,
        "content": content,
        "alternatives": alternatives,
        "category": category,
    }


def _fallback_slugs_for_segment(seg: str) -> list:
    """Para segmentos não mapeados, infere slugs por afinidade de categoria."""
    # Tentar encontrar o segmento em alguma categoria
    index = _load_index()
    
    # Heurísticas por palavras-chave no nome do segmento
    keywords_map = {
        "bold": ["academia", "crossfit", "barbearia", "esporte", "fight", "mma", "box"],
        "elegant": ["luxo", "joalheria", "relojoaria", "moda", "boutique", "atelier"],
        "warm": ["cafe", "restaurante", "padaria", "doceria", "confeitaria", "sorveteria"],
        "clean": ["clinica", "medic", "saude", "hospital", "laboratorio", "fisio"],
        "professional": ["escritorio", "consultoria", "empresa", "servico"],
        "friendly": ["infantil", "brinquedo", "pet", "creche", "escola"],
        "energetic": ["academia", "esporte", "fitness", "personal", "funcional"],
    }
    
    # Mapear keyword → design slugs
    keyword_to_slugs = {
        "bold": ["bold", "brutalism", "energetic", "neobrutalism"],
        "elegant": ["elegant", "luxury", "premium", "editorial"],
        "warm": ["cafe", "warm-editorial", "friendly", "starbucks"],
        "clean": ["clean", "minimal", "modern", "professional"],
        "professional": ["professional", "stripe", "enterprise", "corporate"],
        "friendly": ["friendly", "colorful", "duolingo", "creative"],
        "energetic": ["energetic", "nike", "bold", "brutalism"],
    }
    
    for style, keywords in keywords_map.items():
        for kw in keywords:
            if kw in seg:
                return keyword_to_slugs.get(style, ["modern", "clean"])
    
    # Default genérico
    return ["modern", "clean", "professional", "elegant"]


def get_open_design_prompt(segmento: str, nome_negocio: str = "", tier: str = "STANDARD") -> str:
    """Retorna bloco formatado para injetar no prompt do ArquitetoMestre."""
    result = select_design_system(segmento, nome_negocio, tier)
    
    if not result["content"]:
        return ""
    
    alternatives_fmt = ", ".join(result["alternatives"]) if result["alternatives"] else "nenhuma"
    
    return f"""
=== REFERENCIA CRIATIVA — DESIGN SYSTEM: {result['slug'].upper()} ===
Categoria: {result['category']}
Alternativas consideradas: {alternatives_fmt}

USE COMO INSPIRACAO (adapte para o negocio local, nao copie literalmente):
{result['content']}
=== FIM REFERENCIA CRIATIVA ===
"""


def _read_design_md_range(slug: str, start_section: int, end_section: int, max_chars: int = 3000) -> str:
    """Le secoes especificas do DESIGN.md (ex: 4 a 7)."""
    path = os.path.join(DS_DIR, slug, "DESIGN.md")
    if not os.path.isfile(path):
        return ""
    with open(path, "r") as f:
        content = f.read()
    # Encontrar inicio da secao start
    start_pattern = re.compile(r"\n## " + str(start_section) + r"\.")
    start_match = start_pattern.search(content)
    if not start_match:
        return ""
    # Encontrar fim (secao end+1)
    end_pattern = re.compile(r"\n## " + str(end_section + 1) + r"\.")
    end_match = end_pattern.search(content)
    if end_match:
        result = content[start_match.start():end_match.start()]
    else:
        result = content[start_match.start():]
    return result[:max_chars].strip()


def get_open_design_for_liam(segmento: str, nome_negocio: str = "", tier: str = "STANDARD") -> str:
    """Retorna instrucoes de componentes e layout do Open Design para o Liam.
    Inclui secoes 4 (Component Stylings), 5 (Layout Principles) e 7 (Do/Dont).
    """
    result = select_design_system(segmento, nome_negocio, tier)
    if not result["slug"]:
        return ""

    # Secoes 4-5: Component Stylings + Layout Principles
    components_layout = _read_design_md_range(result["slug"], 4, 5, 2500)

    # Secao 7: Do's and Don'ts
    do_dont = _read_design_md_range(result["slug"], 7, 7, 800)

    # Secao 9: Agent Prompt Guide (se existir)
    agent_guide = _read_design_md_range(result["slug"], 9, 9, 1000)

    parts = []
    if components_layout:
        parts.append(components_layout)
    if do_dont:
        parts.append(do_dont)
    if agent_guide:
        parts.append(agent_guide)

    if not parts:
        return ""

    return f"""
=== DESIGN SYSTEM: {result['slug'].upper()} — REGRAS DE COMPONENTES ===
{chr(10).join(parts)}
=== FIM DESIGN SYSTEM ===
"""
