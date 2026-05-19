"""
Liz Rubricas — Dimensões, Perfis por Nicho, Thresholds
PRD #3: Agent-as-Judge com Rubrica Estruturada
"""

DIMENSOES = {
    "design_visual": {
        "desc": "Cores seguem tokens OKLch, tipografia correta, espaçamento, hierarquia visual",
        "peso_default": 1.5
    },
    "copy_qualidade": {
        "desc": "Texto persuasivo, sem frases genéricas, CTAs com verbo+benefício, sem narrativas fictícias",
        "peso_default": 1.5
    },
    "mobile_responsivo": {
        "desc": "Layout funciona em 375px, touch targets 44px+, sem overflow horizontal",
        "peso_default": 1.2
    },
    "performance": {
        "desc": "Imagens com lazy loading, CSS inline mínimo, sem JS bloqueante desnecessário",
        "peso_default": 1.0
    },
    "imagens": {
        "desc": "Foto real por seção obrigatória, relevante ao nicho, alta qualidade, não genérica",
        "peso_default": 1.0
    },
    "acessibilidade": {
        "desc": "Contraste WCAG AA, alt text, semântica HTML5, landmarks",
        "peso_default": 0.8
    },
    "seo_basico": {
        "desc": "Headings hierárquicos, meta description implícita, texto crawlável",
        "peso_default": 0.7
    },
    "coerencia_prd": {
        "desc": "HTML segue estrutura e conteúdo definidos no PRD do Arquiteto",
        "peso_default": 1.3
    }
}

PERFIS_NICHO = {
    "academia": {
        "design_visual": 2.0,
        "copy_qualidade": 1.2,
        "imagens": 1.8,
        "mobile_responsivo": 1.5,
    },
    "restaurante": {
        "imagens": 2.0,
        "design_visual": 1.5,
        "copy_qualidade": 1.3,
        "seo_basico": 1.2,
    },
    "pizzaria": {
        "imagens": 2.0,
        "design_visual": 1.5,
        "copy_qualidade": 1.3,
        "seo_basico": 1.2,
    },
    "clinica": {
        "copy_qualidade": 2.0,
        "acessibilidade": 1.5,
        "design_visual": 1.3,
        "coerencia_prd": 1.5,
    },
    "barbearia": {
        "design_visual": 2.0,
        "imagens": 1.5,
        "mobile_responsivo": 1.3,
        "copy_qualidade": 1.0,
    },
    "advocacia": {
        "copy_qualidade": 2.0,
        "coerencia_prd": 1.5,
        "acessibilidade": 1.2,
        "design_visual": 1.0,
    },
    "ecommerce": {
        "performance": 2.0,
        "mobile_responsivo": 1.8,
        "copy_qualidade": 1.5,
        "seo_basico": 1.5,
    },
    "dentista": {
        "copy_qualidade": 1.8,
        "acessibilidade": 1.3,
        "design_visual": 1.5,
        "imagens": 1.3,
    },
    "pet_shop": {
        "imagens": 1.8,
        "design_visual": 1.5,
        "copy_qualidade": 1.3,
        "mobile_responsivo": 1.3,
    },
    "salao_beleza": {
        "design_visual": 2.0,
        "imagens": 1.8,
        "mobile_responsivo": 1.3,
        "copy_qualidade": 1.0,
    },
    "default": {}
}

THRESHOLDS = {
    "aprovacao_minima": 7.0,
    "dimensao_critica_minima": 5.0,
    "aprovacao_premium": 8.5,
}


def calcular_score_ponderado(scores: dict, nicho: str) -> float:
    """
    Calcula score ponderado baseado no perfil do nicho.

    Args:
        scores: {"design_visual": 7, "copy_qualidade": 8, ...}
        nicho: "academia", "restaurante", etc.

    Returns: score ponderado (0-10)
    """
    # Normalizar nicho pra match
    nicho_lower = (nicho or "").lower().strip()
    perfil = None
    for key in PERFIS_NICHO:
        if key in nicho_lower or nicho_lower in key:
            perfil = PERFIS_NICHO[key]
            break
    if perfil is None:
        perfil = PERFIS_NICHO["default"]

    soma_ponderada = 0.0
    soma_pesos = 0.0

    for dim, config in DIMENSOES.items():
        peso = perfil.get(dim, config["peso_default"])
        score = scores.get(dim, 7)  # default 7 se não avaliado
        soma_ponderada += score * peso
        soma_pesos += peso

    return round(soma_ponderada / soma_pesos, 1) if soma_pesos > 0 else 7.0


def detectar_nicho(segmento: str) -> str:
    """Detecta o perfil de nicho a partir do segmento do lead."""
    seg = (segmento or "").lower()
    for key in PERFIS_NICHO:
        if key == "default":
            continue
        if key in seg or seg in key:
            return key
    # Mapeamentos extras
    _map = {
        "gym": "academia", "fitness": "academia", "crossfit": "academia",
        "burger": "restaurante", "lanchonete": "restaurante", "cafe": "restaurante",
        "barber": "barbearia",
        "advogad": "advocacia", "escritorio de advocacia": "advocacia",
        "odonto": "dentista", "ortodont": "dentista",
        "veterinar": "pet_shop",
        "estetica": "salao_beleza", "cabeleireir": "salao_beleza",
        "medic": "clinica", "fisioter": "clinica", "psicolog": "clinica",
    }
    for k, v in _map.items():
        if k in seg:
            return v
    return "default"
