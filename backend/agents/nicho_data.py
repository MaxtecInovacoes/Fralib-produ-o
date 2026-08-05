"""nicho_data.py — Dados de nichos e contexto de design para agentes.

Este módulo contém:
- NICHOS: 17 segmentos de mercado com direção visual, componentes, tom e SEO
- ALIASES: mapeamento de variações de nomes para segmentos principais
- get_design_context(): função principal que retorna tokens, tipografia e perfil
  de animação para um nicho específico

Uso:
    from backend.agents.nicho_data import get_design_context

    ctx = get_design_context(
        segmento="restaurante",
        nome_negocio="Cantina da Vovó",
        tier="STANDARD",
        dark_mode=False
    )
"""

from typing import Any


# ─── NICHOS ────────────────────────────────────────────────────────────────────
# 17 segmentos de mercado com direção visual e diretrizes de conteúdo
NICHOS: dict[str, dict[str, Any]] = {
    "barbearia":    {"dir": "luxury", "dir_variantes": ["editorial", "brutalism", "cal"],      "components": "galeria de cortes, lista de serviços, CTA agendamento WhatsApp, badge avaliação Google, horários", "tom": "direto, masculino, confiante — sem adjetivos vagos", "seo": "H1 com cidade, schema BarberShop, FAQ sobre cortes e preços", "anti": "pastéis, fontes cursivas, fotos de stock, contadores inventados"},
    "restaurante":  {"dir": "cafe", "dir_variantes": ["cafe", "rustico", "warm_editorial"],      "components": "foto hero do prato principal, cardápio resumido, horários, localização embed, CTA reserva WhatsApp, avaliações reais", "tom": "apetitoso, acolhedor, local", "seo": "H1 com cidade e culinária, schema Restaurant + Menu, FAQ sobre reservas", "anti": "fotos de stock de comida, layout genérico de delivery"},
    "churrascaria": {"dir": "rustico", "dir_variantes": ["rustico", "cafe"],      "components": "foto hero de carne/brasa, cardápio resumido, horários, localização embed, CTA reserva WhatsApp, avaliações reais", "tom": "robusto, acolhedor, gaúcho, sabor de brasa", "seo": "H1 com cidade e tipo de carne, schema Restaurant, FAQ sobre rodízio e reservas", "anti": "fotos de comida gourmet/fine dining, paleta fria, layout minimalista"},
    "clinica":      {"dir": "clean", "dir_variantes": ["clean", "minimal", "friendly"], "components": "especialidades, equipe com CRM, CTA agendamento WhatsApp, convênios, localização", "tom": "profissional, empático, claro", "seo": "H1 com especialidade e cidade, schema MedicalBusiness, FAQ sobre consultas", "anti": "jargão médico, fotos de stock de médicos, promessas de cura"},
    "nutricionista": {"dir": "friendly", "dir_variantes": ["friendly", "warm_editorial", "clean"], "components": "especialidades, CTA agendamento WhatsApp, depoimentos, FAQ sobre consultas, localização", "tom": "acolhedor, empático, motivador — fala de saúde sem ser clínico", "seo": "H1 com especialidade e cidade, schema MedicalBusiness, FAQ sobre nutrição", "anti": "jargão médico, fotos de stock, promessas de emagrecimento rápido"},
    "academia":     {"dir": "bold", "dir_variantes": ["bold", "nike", "brutalism", "dramatic", "theverge"],      "components": "modalidades, planos e preços, CTA matrícula WhatsApp, fotos do espaço real, horários de aulas", "tom": "energético, motivador, direto", "seo": "H1 com modalidade e cidade, schema SportsActivityLocation, FAQ sobre planos", "anti": "atletas de stock, promessas em X dias, layout corporativo"},
    "pet_shop":     {"dir": "friendly", "dir_variantes": ["friendly", "duolingo", "lingo"],      "components": "serviços (banho, tosa, vet), galeria de pets, CTA WhatsApp, produtos, horários", "tom": "carinhoso, confiável — fala com o dono", "seo": "H1 com serviço e cidade, schema AnimalShelter, FAQ sobre serviços", "anti": "fotos de stock de animais, tom infantilizado"},
    "advocacia":    {"dir": "warm_editorial", "dir_variantes": ["warm_editorial", "editorial", "professional"],      "components": "áreas de atuação, perfil com OAB, CTA consulta WhatsApp, casos de sucesso, localização", "tom": "sério, competente, acessível — sem juridiquês", "seo": "H1 com área do direito e cidade, schema LegalService, FAQ sobre honorários", "anti": "promessas de ganhar causas, jargão no hero, stock de martelo"},
    "odontologia":  {"dir": "clean", "dir_variantes": ["clean", "minimal", "friendly"], "components": "tratamentos, antes/depois, CTA WhatsApp, convênios, equipe com CRO, localização", "tom": "profissional, acolhedor — reduz ansiedade", "seo": "H1 com tratamento e cidade, schema Dentist, FAQ sobre dor e procedimentos", "anti": "sorrisos perfeitos de stock, jargão técnico, promessas imediatas"},
    "estetica":     {"dir": "elegant", "dir_variantes": ["elegant", "refined", "warm_editorial"],      "components": "tratamentos, galeria de resultados reais, CTA WhatsApp, certificações, faixa de preço", "tom": "elegante, confiante — foco em autoestima", "seo": "H1 com tratamento e cidade, schema BeautySalon, FAQ sobre recuperação", "anti": "modelos perfeitas de stock, promessas milagrosas"},
    "pizzaria":     {"dir": "vibrant", "dir_variantes": ["vibrant", "cafe", "starbucks"],      "components": "cardápio com fotos reais, sabores em destaque, CTA pedido WhatsApp, horários, área de entrega", "tom": "apetitoso, descontraído, local", "seo": "H1 com cidade e tipo, schema FoodEstablishment, FAQ sobre entrega", "anti": "fotos de stock de pizza, layout de app de delivery"},
    "farmacia":     {"dir": "clean", "dir_variantes": ["clean", "minimal", "simple"],   "components": "serviços (manipulação, delivery, plantão), produtos em destaque, CTA WhatsApp, horários, localização", "tom": "confiável, claro — saúde sem alarmismo", "seo": "H1 com cidade e diferencial, schema Pharmacy, FAQ sobre manipulação", "anti": "jargão farmacêutico, e-commerce genérico"},
    "imobiliaria":  {"dir": "airbnb", "dir_variantes": ["airbnb", "minimal", "warm_editorial"], "components": "tipos de imóveis, lançamentos, CTA WhatsApp com corretor, avaliações, área de atuação", "tom": "profissional, local — conhece o bairro", "seo": "H1 com cidade e tipo, schema RealEstateAgent, FAQ sobre financiamento", "anti": "casas perfeitas de stock, promessas de valorização"},
    "contabilidade":{"dir": "professional", "dir_variantes": ["professional", "clean", "corporate"],   "components": "serviços (MEI, PJ, IR), diferenciais, CTA WhatsApp, equipe com CRC, cases", "tom": "técnico mas acessível, parceiro", "seo": "H1 com serviço e cidade, schema AccountingService, FAQ sobre abertura de empresa", "anti": "jargão contábil no hero, calculadora de stock"},
    "escola":       {"dir": "duolingo", "dir_variantes": ["duolingo", "friendly", "lingo"],      "components": "níveis de ensino, diferenciais, CTA matrícula WhatsApp, fotos reais, depoimentos de pais", "tom": "acolhedor, inspirador — fala com os pais", "seo": "H1 com nível e cidade, schema School, FAQ sobre matrícula", "anti": "crianças felizes de stock, jargão pedagógico"},
    "salao_beleza": {"dir": "elegant", "dir_variantes": ["elegant", "refined", "warm_editorial"],      "components": "serviços com galeria, equipe com especialidades, CTA WhatsApp, produtos usados, horários", "tom": "elegante, pessoal — o salão tem personalidade", "seo": "H1 com serviço e cidade, schema HairSalon, FAQ sobre coloração", "anti": "modelos de stock, tom neutro sem personalidade"},
    "auto_pecas":   {"dir": "bold", "dir_variantes": ["bold", "brutalism", "clean"],   "components": "marcas atendidas, serviços, CTA WhatsApp, localização com referência, horários", "tom": "direto, técnico, confiável", "seo": "H1 com serviço e cidade, schema AutoRepair, FAQ sobre garantia", "anti": "e-commerce genérico, carros de stock, tom corporativo"},
}

# ─── ALIASES — Variações de nomes mapeadas para segmentos principais ───────────
ALIASES: dict[str, str] = {
    "restaurantes": "restaurante", "barbearias": "barbearia",
    "clinicas": "clinica", "clinica_medica": "clinica",
    "pet": "pet_shop", "pets": "pet_shop",
    "advogado": "advocacia", "advogados": "advocacia",
    "dentista": "odontologia", "dentistas": "odontologia",
    "estetica_facial": "estetica", "estetica_corporal": "estetica",
    "pizzarias": "pizzaria", "farmacias": "farmacia",
    "imoveis": "imobiliaria", "contabil": "contabilidade",
    "escolas": "escola", "salao": "salao_beleza",
    "auto_peca": "auto_pecas", "mecanica": "auto_pecas",
    "crossfit": "academia", "personal": "academia", "personal_trainer": "academia",
    "musculacao": "academia", "funcional": "academia",
    "psicologia": "clinica", "lanchonete": "restaurante",
    "padaria": "restaurante",
    "churrascaria": "churrascaria", "churrascarias": "churrascaria",
    "steakhouse": "churrascaria",
}


# ─── Dark mode overlay ─────────────────────────────────────────────────────────
DARK_OVERLAY: dict[str, str] = {
    "--bg":      "oklch(12% 0.010 260)",
    "--surface": "oklch(17% 0.012 260)",
    "--fg":      "oklch(93% 0.005 0)",
    "--muted":   "oklch(65% 0.010 260)",
    "--border":  "oklch(28% 0.015 260)",
}


# ─── Mapeamento TIER → DIREÇÃO ─────────────────────────────────────────────────
TIER_DIRECAO: dict[str, list[str]] = {
    "PREMIUM":  ["warm_editorial", "minimal"],
    "STANDARD": ["cafe", "clean"],
    "BASIC":    ["clean"],
}


def get_design_context(
    segmento: str,
    nome_negocio: str = "",
    tier: str = "STANDARD",
    dark_mode: bool = False,
    od_slug: str = "",
    dados_lead: dict | None = None,
) -> dict[str, Any]:
    """Retorna dict com tokens, tipografia e perfil de animação para o nicho.

    Se od_slug fornecido, usa tokens pré-computados do DESIGN.md extraido.
    Fallback: DIRECOES_VISUAIS hardcoded.

    Args:
        segmento: Nome do segmento (ex: "restaurante", "barbearia")
        nome_negocio: Nome do negócio para variações determinísticas
        tier: Nível do pacote ("BASIC", "STANDARD", "PREMIUM")
        dark_mode: Se True, aplica overlay de dark mode
        od_slug: Slug do Open Design para tokens pré-computados
        dados_lead: Dados do lead para detecção de sub-nicho

    Returns:
        Dict com:
        - dir_key: chave da direção visual
        - dir_nome: nome da direção visual
        - tokens: 6 tokens universais em OKLch
        - font_heading: fonte para títulos
        - font_body: fonte para corpo
        - vibe: descrição da direção visual
        - animation: perfil de animação
        - animation_profile: dict com timings e easing
        - hero_style: estilo do hero section
        - components: lista de componentes recomendados
        - tom: tom de comunicação
        - seo: diretrizes SEO
        - anti: anti-patterns a evitar
        - segmento: segmento normalizado
        - tier: tier em uppercase
        - craft: perfil de craft (spacing, typography, rhythm)
    """
    # Lazy imports para evitar dependência circular
    import hashlib as _hlib
    import random as _rnd
    import re as _re

    from backend.agents.design_tokens import ANIMATION_PROFILES, CRAFT_PROFILES, DIRECOES_VISUAIS, get_craft_profile
    from backend.agents.hero_styles import get_hero_style
    from backend.agents.sub_nicho import detectar_sub_nicho

    seg = segmento.lower().replace(" ", "_").replace("-", "_")
    seg = ALIASES.get(seg, seg)
    nicho = NICHOS.get(seg, {
        "dir": "minimal",
        "components": "hero com proposta de valor, serviços, CTA WhatsApp, localização, avaliações",
        "tom": "profissional, claro, local",
        "seo": "H1 com serviço e cidade, schema LocalBusiness",
        "anti": "fotos de stock genéricas, contadores inventados",
    })
    tier_upper = tier.upper()

    _variantes = nicho.get("dir_variantes", [nicho["dir"]])
    if nome_negocio:
        _seed = int(_hlib.md5(nome_negocio.encode()).hexdigest(), 16)
        _rnd_local = _rnd.Random(_seed)
        dir_key = _rnd_local.choice(_variantes)
    else:
        dir_key = _rnd.choice(_variantes)
    if dir_key not in DIRECOES_VISUAIS:
        dir_key = nicho["dir"]

    _sub_nicho_data = None
    if dados_lead:
        _sub_nicho_data = detectar_sub_nicho(seg, dados_lead)
        if _sub_nicho_data and _sub_nicho_data.get("vibe_override"):
            dir_key = _sub_nicho_data["vibe_override"]

    if dir_key not in DIRECOES_VISUAIS:
        dir_key = nicho["dir"]
    d = DIRECOES_VISUAIS[dir_key]

    # Tokens: prioridade DESIGN.md real extraido > DIRECOES_VISUAIS hardcoded
    _od_effective_slug = od_slug or dir_key

    # Verificar se há tokens pré-computados (via design_tokens)
    tokens = dict(d["tokens"])

    if dark_mode:
        tokens.update(DARK_OVERLAY)
    anim = dict(ANIMATION_PROFILES[d["animation"]])  # copia pra não mutar original

    # Variação de animação por lead — mesmo perfil base, tipos diferentes
    _anim_hero_types = ["fade-up", "slide-up", "scale-in"]
    _anim_card_types = ["fade-up", "slide-left", "scale-in", "fade-up"]
    if nome_negocio:
        _anim_seed = int(_hlib.md5(("anim_" + nome_negocio).encode()).hexdigest(), 16)
        _anim_rng = _rnd.Random(_anim_seed)
        anim["hero_type"] = _anim_rng.choice(_anim_hero_types)
        anim["card_type"] = _anim_rng.choice(_anim_card_types)

    # Variação de hero layout por lead — mesmo nicho, hero diferente
    _hero_base = get_hero_style(dir_key)
    _hero_layouts_pool = ["hero-split", "hero-center", "hero-fullscreen", "hero-diagonal"]
    if nome_negocio:
        _hero_seed = int(_hlib.md5(("hero_" + nome_negocio).encode()).hexdigest(), 16)
        _hero_rng = _rnd.Random(_hero_seed)
        # Manter layout compatível com a direção (dark = fullscreen/center, light = split/center/diagonal)
        _bg_lightness = 100
        _m_lgt = _re.search(r"oklch\((\d+)%", tokens.get("--bg", "oklch(100% 0.0 0)"))
        if _m_lgt:
            _bg_lightness = int(_m_lgt.group(1))
        if _bg_lightness < 30:
            _hero_pool = ["hero-fullscreen", "hero-center", "hero-diagonal"]
        else:
            _hero_pool = ["hero-split", "hero-center", "hero-diagonal", "hero-fullscreen"]
        _hero_base["layout"] = _hero_rng.choice(_hero_pool)

    # ═══ VALIDAÇÃO DE SANIDADE DOS TOKENS ═══
    # Garantir que tokens OKLch fazem sentido visual
    def _get_lightness(val: str) -> float | None:
        m = _re.search(r"oklch\((\d+(?:\.\d+)?)%", val)
        return float(m.group(1)) if m else None

    def _get_chroma(val: str) -> float | None:
        m = _re.search(r"oklch\(\d+(?:\.\d+)?%\s+([\d.]+)", val)
        return float(m.group(1)) if m else None

    def _get_hue(val: str) -> float | None:
        m = _re.search(r"oklch\(\d+(?:\.\d+)?%\s+[\d.]+\s+([\d.]+)", val)
        return float(m.group(1)) if m else None

    # Hue contextual por segmento — fallback vibrante quando accent é fraco
    _SEGMENT_HUE: dict[str, int] = {
        # Comida/bebida → vermelho/laranja/amarelo quente
        "pizzaria": 25, "pizza": 25, "restaurante": 30, "hamburgueria": 25,
        "lanchonete": 35, "padaria": 50, "cafe": 55, "bar": 20,
        "churrascaria": 20, "sorveteria": 340, "doceria": 350, "confeitaria": 350,
        "acai": 320, "sushi": 15, "pastelaria": 40, "food_truck": 30,
        # Saúde → verde/azul
        "nutricionista": 270, "dentista": 210, "psicologo": 280, "psicologa": 280,
        "medico": 210, "medica": 210, "fisioterapeuta": 180, "veterinario": 150,
        "farmacia": 160, "clinica": 200, "hospital": 210, "esteticista": 330,
        # Fitness → laranja/vermelho energético
        "academia": 25, "personal": 20, "crossfit": 15, "pilates": 300,
        # Jurídico/financeiro → azul/dourado
        "advogado": 240, "advogada": 240, "contador": 230, "contadora": 230,
        "escritorio": 240, "consultoria": 250,
        # Tech/criativo → roxo/azul
        "agencia": 270, "marketing": 280, "design": 290, "fotografo": 300,
        "fotografa": 300, "arquiteto": 260, "arquiteta": 260,
        # Educação → azul/verde
        "escola": 220, "curso": 230, "professor": 220, "professora": 220,
        # Beleza → rosa/roxo
        "salao": 330, "barbearia": 30, "manicure": 340, "maquiadora": 350,
        # Automotivo → azul/cinza
        "mecanica": 220, "oficina": 220, "lava_jato": 210, "auto_eletrica": 230,
        # Imóveis → azul/verde
        "imobiliaria": 200, "corretor": 200, "corretora": 200,
        # Pet → verde/laranja
        "pet_shop": 150, "petshop": 150, "dog_walker": 140,
    }
    _fallback_hue = _SEGMENT_HUE.get(seg, 270)
    if _sub_nicho_data and _sub_nicho_data.get("sub_nicho") == "natacao":
        _fallback_hue = 200  # Tom de piscina refrescante (azul/ciano)

    _bg_l = _get_lightness(tokens.get("--bg", ""))
    _fg_l = _get_lightness(tokens.get("--fg", ""))
    _muted_l = _get_lightness(tokens.get("--muted", ""))
    _accent_l = _get_lightness(tokens.get("--accent", ""))
    _accent_c = _get_chroma(tokens.get("--accent", ""))

    if _bg_l is not None:
        is_light_theme = _bg_l > 60

        # Muted: deve ser intermediário (40-70% em tema claro, 50-80% em tema escuro)
        if _muted_l is not None:
            if is_light_theme and (_muted_l > 80 or _muted_l < 30):
                tokens["--muted"] = f"oklch(55% 0.015 {_fallback_hue})"
            elif not is_light_theme and (_muted_l < 40 or _muted_l > 90):
                tokens["--muted"] = f"oklch(65% 0.015 {_fallback_hue})"

        # Accent: deve ser vibrante (30-70% lightness E chroma >= 0.1)
        _accent_needs_fix = False
        if _accent_l is not None:
            if _accent_l > 85 or _accent_l < 20:
                _accent_needs_fix = True
            elif _accent_c is not None and _accent_c < 0.1:
                _accent_needs_fix = True  # Chroma muito baixo = sem cor visível

        if _accent_needs_fix:
            tokens["--accent"] = f"oklch(55% 0.2 {_fallback_hue})"

        # Hue override: se segmento tem preferência forte de cor e accent hue está longe
        # (ex: pizzaria deve ser vermelho/laranja, não roxo/azul)
        _SEGMENT_HUE_STRICT: set[str] = {
            "pizzaria", "pizza", "restaurante", "hamburgueria", "lanchonete",
            "churrascaria", "padaria", "sorveteria", "doceria", "confeitaria",
            "acai", "sushi", "pastelaria", "food_truck", "bar", "cafe",
            "academia", "personal", "crossfit",
        }
        if seg in _SEGMENT_HUE_STRICT and not _accent_needs_fix:
            _current_hue = _get_hue(tokens.get("--accent", ""))
            if _current_hue is not None:
                # Verificar se hue atual está longe do ideal (> 90° de diferença)
                _hue_diff = abs(_current_hue - _fallback_hue)
                if _hue_diff > 180:
                    _hue_diff = 360 - _hue_diff
                if _hue_diff > 90:
                    # Manter lightness e chroma, trocar hue
                    _keep_l = _accent_l if _accent_l else 55
                    _keep_c = _accent_c if _accent_c and _accent_c >= 0.1 else 0.18
                    tokens["--accent"] = f"oklch({_keep_l}% {_keep_c} {_fallback_hue})"

        # FG: deve contrastar com BG (diferença mínima 50%)
        if _fg_l is not None:
            if is_light_theme and _fg_l > 50:
                tokens["--fg"] = f"oklch(15% 0.02 {_fallback_hue})"
            elif not is_light_theme and _fg_l < 50:
                tokens["--fg"] = "oklch(92% 0.01 0)"

        # Border: não pode ser invisível
        _border_l = _get_lightness(tokens.get("--border", ""))
        if _border_l is not None:
            if is_light_theme and _border_l < 40:
                tokens["--border"] = "oklch(85% 0.005 0)"
            elif not is_light_theme and _border_l > 80:
                tokens["--border"] = "oklch(25% 0.005 0)"

    return {
        "dir_key":       dir_key,
        "dir_nome":      d["nome"],
        "tokens":        tokens,
        "font_heading":  d["font_heading"],
        "font_body":     d["font_body"],
        "vibe":          d["vibe"],
        "animation":     d["animation"],
        "animation_profile": anim,
        "hero_style":    _hero_base,
        "components":    nicho["components"],
        "tom":           nicho["tom"],
        "seo":           nicho["seo"],
        "anti":          nicho["anti"] + " | " + d.get("anti", ""),
        "segmento":      seg,
        "tier":          tier_upper,
        "craft":         get_craft_profile(dir_key),
    }
