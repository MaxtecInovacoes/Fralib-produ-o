"""Seleciona design system por segmento.

Usa os DESIGN.md de FRALIB_DS_DIR
como referência criativa para o ArquitetoMestre gerar sites por nicho.
"""

import os
import re
import hashlib
import json
from backend.config import DS_DIR as _CFG_DS_DIR

DS_DIR = _CFG_DS_DIR
DESIGN_DNA_CACHE_VERSION = "design-dna-v2"

INDEX_PATH = os.path.join(os.path.dirname(__file__), "design_system_index.json")

# ─── MAPEAMENTO SEGMENTO → SLUGS RELEVANTES ─────────────────────────────────
# Cada segmento tem 4-6 design systems ranqueados por relevância visual.
# O ArquitetoMestre usa o primeiro como referência principal e os demais como
# inspiração secundária para garantir variedade entre sites do mesmo nicho.

SEGMENT_DESIGN_MAP = {
    # Masculino, edgy, confiante
    "barbearia": ["brutalism", "bold", "neobrutalism", "editorial", "warp", "mono"],
    # Acolhedor, apetitoso, local
    "restaurante": ["bistro-cardapio", "cafe", "warm-editorial", "airbnb", "storytelling"],
    "churrascaria": ["bold", "brutalism", "cafe", "warm-editorial"],
    "pizzaria": ["bistro-cardapio", "cafe", "warm-editorial", "colorful", "vibrant"],
    "lanchonete": ["bistro-cardapio", "colorful", "cafe", "duolingo", "vibrant", "bold"],
    "padaria": ["bistro-cardapio", "cafe", "warm-editorial", "vintage", "paper"],
    # Clínico, confiável, moderno
    "clinica": ["claude", "linear", "clean", "professional", "minimal"],
    "odontologia": ["claude", "linear", "clean", "professional", "sleek", "refined"],
    "nutricionista": [
        "editorial-wellness",
        "warm-editorial",
        "claude",
        "linear",
        "clean",
        "friendly",
    ],
    "psicologia": [
        "warm-editorial",
        "elegant",
        "friendly",
        "clean",
        "editorial",
        "refined",
    ],
    # Energético, poderoso, motivador
    "academia": ["crossfit-box", "nike", "brutalism", "spacex", "bold", "energetic"],
    "crossfit": ["crossfit-box", "brutalism", "nike", "bold", "neobrutalism", "dramatic"],
    # Carinhoso, confiável, lúdico
    "pet_shop": [
        "pet-friendly",
        "colorful",
        "duolingo",
        "warm-editorial",
        "cafe",
        "doodle",
    ],
    # Sério, premium, competente
    "advocacia": [
        "legal-trust",
        "elegant",
        "editorial",
        "luxury",
        "premium",
        "professional",
    ],
    # Sofisticado, pessoal, elegante
    "estetica": ["beauty-editorial", "elegant", "luxury", "premium", "editorial", "refined"],
    "salao_beleza": [
        "beauty-editorial",
        "elegant",
        "editorial",
        "luxury",
        "premium",
        "refined",
        "artistic",
    ],
    # Funcional, técnico, confiável
    "farmacia": ["clean", "professional", "modern", "enterprise", "material"],
    "auto_pecas": [
        "bold",
        "modern",
        "professional",
        "enterprise",
        "corporate",
        "dashboard",
    ],
    # Profissional, local, moderno
    "imobiliaria": ["realty-grid", "professional", "airbnb", "sleek", "premium"],
    "contabilidade": [
        "professional",
        "modern",
        "enterprise",
        "corporate",
        "clean",
    ],
    # Acolhedor, inspirador, confiável
    "escola": [
        "edu-playful",
        "colorful",
        "duolingo",
        "warm-editorial",
        "cafe",
        "creative",
    ],
}

GENERIC_TEMPLATE_SLUGS = {"bold", "clean", "modern", "friendly", "minimal", "elegant"}

CURATED_DESIGN_SYSTEMS = {
    "editorial-wellness": {
        "category": "Health & Wellness",
        "font_primary": "Fraunces",
        "colors": {"primary": "#0F766E", "secondary": "#F9735B", "surface": "#F7FBF7", "text": "#12332E"},
        "content": """# Editorial Wellness
## 1. Atmosphere
Mineral teal, eucalyptus light and human coral. The page must feel like a calm editorial clinic, not a beige wellness template.
## 2. Color
Primary #0F766E, deep #073B3A, coral #F9735B, mist #F7FBF7, ink #12332E. Avoid Tailwind blue, cream-only pages and repeated white cards.
## 3. Typography
Use Fraunces or a refined serif for display, Manrope/Inter for body. Headlines are soft but specific: "Cuidado nutricional que respeita sua rotina".
## 4. Components
Asymmetric hero with human photo, proof chip near the fold, methodology strip, services as editorial rows, FAQ with neutral factual answers.
## 5. Layout
Alternate full-bleed mineral sections with narrow reading bands. Use one photo-led story section and one local trust section.
## 7. Do/Don't
Do: teal commitment, coral CTA, subniche copy. Don't: generic "saude e bem-estar", beige AI spa, hospital blue, invented outcomes.""",
    },
    "crossfit-box": {
        "category": "Bold & Expressive",
        "font_primary": "Oswald",
        "colors": {"primary": "#DC2626", "secondary": "#F59E0B", "surface": "#090807", "text": "#FFF7ED"},
        "content": """# Crossfit Box
## 1. Atmosphere
Dark full-bleed training campaign with red cuts, chalk texture, big schedule/proof numbers and aggressive crops.
## 2. Color
Black #090807, red #DC2626, amber #F59E0B, warm white #FFF7ED. Never corporate blue.
## 3. Typography
Oswald/condensed uppercase display, compact Inter body. H1 should look like a poster.
## 4. Components
Video or action hero, magnetic CTA, WOD-style proof block, plan cards with physical hover, manifesto band.
## 5. Layout
Asymmetric hero, diagonal overlaps, high contrast strips, stats above fold.
## 7. Do/Don't
Do: motion, sweat, red accent, local proof. Don't: centered SaaS hero, pastel fitness, soft cards.""",
    },
    "bistro-cardapio": {
        "category": "Food & Hospitality",
        "font_primary": "Cormorant Garamond",
        "colors": {"primary": "#B4532A", "secondary": "#D6A85C", "surface": "#15100C", "text": "#FFF7ED"},
        "content": """# Bistro Cardapio
## 1. Atmosphere
Editorial restaurant page: warm dark room, food in motion, menu rhythm and an "aberto/contato" conversion path.
## 2. Color
Terracotta #B4532A, gold #D6A85C, espresso #15100C, paper #FFF7ED.
## 3. Typography
High contrast serif display with readable sans body. Headlines feel like menu covers.
## 4. Components
Video hero when available, menu-preview rows, ambience gallery, reservation/WhatsApp CTA, local proof.
## 5. Layout
Full-bleed hero, alternating menu/editorial bands, large image crops.
## 7. Do/Don't
Do: appetite, ambience, craft. Don't invent dishes, prices or delivery time.""",
    },
    "beauty-editorial": {
        "category": "Beauty & Lifestyle",
        "font_primary": "Playfair Display",
        "colors": {"primary": "#9F5A6A", "secondary": "#C9A46B", "surface": "#171012", "text": "#FFF7F8"},
        "content": """# Beauty Editorial
## 1. Atmosphere
Beauty magazine, treatment detail, soft luxury and lifestyle transformation.
## 2. Color
Rose #9F5A6A, champagne #C9A46B, noir #171012, blush #FFF7F8.
## 3. Typography
Playfair-style display, Manrope body, compact service labels.
## 4. Components
Atmosphere video/photo hero, service editorial grid, before/after-safe copy, WhatsApp CTA.
## 5. Layout
Large crops, narrow copy, service cards with interactive lift.
## 7. Do/Don't
Do not promise results or certifications unless provided.""",
    },
    "realty-grid": {
        "category": "Real Estate",
        "font_primary": "Space Grotesk",
        "colors": {"primary": "#12324A", "secondary": "#C6A55B", "surface": "#F4F7F8", "text": "#10202A"},
        "content": """# Realty Grid
## 1. Atmosphere
Premium real estate grid: precise, calm, image-led and trust-heavy.
## 2. Color
Navy #12324A, gold #C6A55B, cloud #F4F7F8, ink #10202A.
## 3. Typography
Space Grotesk or elegant sans, restrained headings, tabular facts.
## 4. Components
Static photo hero, property-style cards, location proof, contact CTA.
## 5. Layout
Grid discipline with one strong hero image. Avoid video unless explicit.
## 7. Do/Don't
Do not invent listings, prices or areas.""",
    },
    "legal-trust": {
        "category": "Professional & Corporate",
        "font_primary": "Cormorant Garamond",
        "colors": {"primary": "#102A43", "secondary": "#B08D57", "surface": "#F8FAFC", "text": "#111827"},
        "content": """# Legal Trust
## 1. Atmosphere
Sober authority, editorial law office, gravitas and clarity.
## 2. Color
Deep navy #102A43, restrained gold #B08D57, off-white #F8FAFC.
## 3. Typography
Serif display with professional sans body.
## 4. Components
Static hero, areas of practice as trust rows, credentials only when confirmed, CTA for consultation.
## 5. Layout
Measured spacing, proof above fold, no playful decoration.
## 7. Do/Don't
Do not promise legal outcomes or cite awards without evidence.""",
    },
    "pet-friendly": {
        "category": "Family & Pets",
        "font_primary": "Nunito Sans",
        "colors": {"primary": "#F97316", "secondary": "#10B981", "surface": "#FFF7ED", "text": "#2B2118"},
        "content": """# Pet Friendly
## 1. Atmosphere
Warm, lively and trustworthy, with pets in action and owner reassurance.
## 2. Color
Orange #F97316, green #10B981, warm paper #FFF7ED.
## 3. Typography
Rounded sans with clear hierarchy.
## 4. Components
Video hero when available, service chips, care proof, contact CTA.
## 5. Layout
Friendly but not childish; strong photos and simple scanning.
## 7. Do/Don't
Do not invent veterinary licenses or emergency service.""",
    },
    "edu-playful": {
        "category": "Education",
        "font_primary": "Plus Jakarta Sans",
        "colors": {"primary": "#2563EB", "secondary": "#F59E0B", "surface": "#F8FAFC", "text": "#0F172A"},
        "content": """# Edu Playful
## 1. Atmosphere
Institutional trust with controlled playfulness, clear dates/contact and parent confidence.
## 2. Color
Blue #2563EB, amber #F59E0B, white #F8FAFC, slate #0F172A.
## 3. Typography
Friendly geometric sans, never childish.
## 4. Components
Static student/space hero, program rows, parent FAQ, contact CTA.
## 5. Layout
Readable sections, badges, gallery and proof.
## 7. Do/Don't
Do not invent MEC status, grades or enrollment dates.""",
    },
}

# Categorias de design system -> segmentos FraLib (fallback para segmentos desconhecidos)
CATEGORY_AFFINITY = {
    "Professional & Corporate": [
        "clinica",
        "advocacia",
        "contabilidade",
        "imobiliaria",
        "farmacia",
    ],
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
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _read_design_md_sections(slug: str, max_sections: int = 3) -> str:
    """Lê as primeiras N seções do DESIGN.md (atmosphere, colors, typography)."""
    if slug in CURATED_DESIGN_SYSTEMS:
        return CURATED_DESIGN_SYSTEMS[slug]["content"][:2500]
    path = os.path.join(DS_DIR, slug, "DESIGN.md")
    if not os.path.isfile(path):
        return ""

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Encontrar onde começa a seção max_sections+1 e cortar ali
    # Seções são ## 1., ## 2., ## 3., etc.
    cut_pattern = re.compile(r"\n## " + str(max_sections + 1) + r"\.")
    cut_match = cut_pattern.search(content)
    if cut_match:
        result = content[: cut_match.start()]
    else:
        result = content

    # Limitar a 2500 chars para não estourar o prompt
    return result[:2500]


def select_design_system(
    segmento: str, nome_negocio: str = "", tier: str = "STANDARD"
) -> dict:
    """Seleciona o design system mais adequado para o segmento.

    Retorna dict com:
        - slug: nome do design system selecionado
        - content: texto das seções 1-3 do DESIGN.md
        - alternatives: lista de slugs alternativos
        - category: categoria do design system
    """
    try:
        from design_context import ALIASES
    except Exception:
        from agents.design_context import ALIASES

    seg = segmento.lower().replace(" ", "_").replace("-", "_")
    seg = ALIASES.get(seg, seg)

    # Buscar slugs mapeados para o segmento
    slugs = SEGMENT_DESIGN_MAP.get(seg, [])

    if not slugs:
        # Fallback: usar índice para encontrar design systems por categoria
        slugs = _fallback_slugs_for_segment(seg)

    if not slugs:
        slugs = ["modern", "clean", "professional", "elegant"]

    slugs = _prioritize_curated_slugs(slugs)

    # Usar hash do nome do negócio para variar a escolha entre sites do mesmo nicho
    seed = int(hashlib.md5((nome_negocio or segmento).encode()).hexdigest()[:8], 16)

    # Tier influencia: PREMIUM pega os mais sofisticados (primeiros), BASIC os mais simples
    tier_offset = {"PREMIUM": 0, "STANDARD": 1, "BASIC": 2}.get(tier.upper(), 1)

    # Combinar seed + tier para escolher
    candidate_count = min(3, len(slugs))
    candidate_pool = slugs[:candidate_count] or slugs
    idx = (seed + tier_offset) % len(candidate_pool)
    chosen_slug = candidate_pool[idx]

    # Verificar se o slug existe
    if chosen_slug not in CURATED_DESIGN_SYSTEMS and not os.path.isfile(os.path.join(DS_DIR, chosen_slug, "DESIGN.md")):
        # Tentar o próximo
        for s in slugs:
            if s in CURATED_DESIGN_SYSTEMS or os.path.isfile(os.path.join(DS_DIR, s, "DESIGN.md")):
                chosen_slug = s
                break

    # Ler conteúdo
    content = _read_design_md_sections(chosen_slug)

    # Buscar categoria do índice
    index = _load_index()
    category = ""
    if chosen_slug in CURATED_DESIGN_SYSTEMS:
        category = CURATED_DESIGN_SYSTEMS[chosen_slug].get("category", "")
    else:
        for entry in index:
            if entry["slug"] == chosen_slug:
                category = entry.get("category", "")
                break

    # Alternativas (excluindo o escolhido)
    alternatives = [s for s in candidate_pool + slugs if s != chosen_slug]
    alternatives = list(dict.fromkeys(alternatives))[:3]

    return {
        "slug": chosen_slug,
        "content": content,
        "alternatives": alternatives,
        "category": category,
        "candidate_slugs": candidate_pool,
        "cache_version": DESIGN_DNA_CACHE_VERSION,
    }


def _prioritize_curated_slugs(slugs: list[str]) -> list[str]:
    strong = [slug for slug in slugs if slug in CURATED_DESIGN_SYSTEMS]
    real = [slug for slug in slugs if slug not in strong and slug not in GENERIC_TEMPLATE_SLUGS]
    generic = [slug for slug in slugs if slug in GENERIC_TEMPLATE_SLUGS]
    return list(dict.fromkeys(strong + real + generic))


def _fallback_slugs_for_segment(seg: str) -> list:
    """Para segmentos não mapeados, infere slugs por afinidade de categoria."""
    # Heurísticas por palavras-chave no nome do segmento
    keywords_map = {
        "bold": ["academia", "crossfit", "barbearia", "esporte", "fight", "mma", "box"],
        "elegant": ["luxo", "joalheria", "relojoaria", "moda", "boutique", "atelier"],
        "warm": [
            "cafe",
            "restaurante",
            "padaria",
            "doceria",
            "confeitaria",
            "sorveteria",
        ],
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
        "professional": ["professional", "enterprise", "corporate"],
        "friendly": ["friendly", "colorful", "duolingo", "creative"],
        "energetic": ["energetic", "nike", "bold", "brutalism"],
    }

    for style, keywords in keywords_map.items():
        for kw in keywords:
            if kw in seg:
                return keyword_to_slugs.get(style, ["modern", "clean"])

    # Default genérico
    return ["modern", "clean", "professional", "elegant"]


def get_design_system_prompt(
    segmento: str, nome_negocio: str = "", tier: str = "STANDARD"
) -> str:
    """Retorna bloco formatado para injetar no prompt do ArquitetoMestre."""
    result = select_design_system(segmento, nome_negocio, tier)

    if not result["content"]:
        return ""

    alternatives_fmt = (
        ", ".join(result["alternatives"]) if result["alternatives"] else "nenhuma"
    )

    return f"""
=== REFERENCIA CRIATIVA — DESIGN SYSTEM: {result["slug"].upper()} ===
Categoria: {result["category"]}
Alternativas consideradas: {alternatives_fmt}

USE COMO INSPIRACAO (adapte para o negocio local, nao copie literalmente):
{result["content"]}
=== FIM REFERENCIA CRIATIVA ===
"""


def _read_design_md_range(
    slug: str, start_section: int, end_section: int, max_chars: int = 3000
) -> str:
    """Le secoes especificas do DESIGN.md (ex: 4 a 7)."""
    path = os.path.join(DS_DIR, slug, "DESIGN.md")
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
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
        result = content[start_match.start() : end_match.start()]
    else:
        result = content[start_match.start() :]
    return result[:max_chars].strip()


def get_design_system_for_generator(
    segmento: str, nome_negocio: str = "", tier: str = "STANDARD"
) -> str:
    """Retorna instrucoes de componentes e layout para o renderer.
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
=== DESIGN SYSTEM: {result["slug"].upper()} — REGRAS DE COMPONENTES ===
{chr(10).join(parts)}
=== FIM DESIGN SYSTEM ===
"""
