"""
Módulo de detecção de sub-nichos para segmentação de leads.

Este módulo contém a lógica de detecção de sub-nichos baseada em palavras-chave
extraídas dos dados do Google (nome, serviços, atributos, reviews, categorias).

Usage:
    from backend.agents.sub_nicho import detectar_sub_nicho

    resultado = detectar_sub_nicho("nutricionista", dados_lead)
    # {
    #     "sub_nicho": "emagrecimento",
    #     "tom": "acolhedor, transformação pessoal, sem julgamento",
    #     "publico": "pessoas buscando perda de peso saudável",
    #     "cta": "Começar minha transformação",
    #     "vibe_override": None
    # }
"""

from typing import Any


# Dicionário hierárquico de sub-nichos por segmento
SUB_NICHOS: dict[str, dict[str, dict[str, Any]]] = {
    "nutricionista": {
        "esportivo": {
            "keywords": ["esportiv", "performance", "hipertrofia", "atleta", "suplementa", "treino", "muscula", "bodybuilding", "crossfit", "funcional"],
            "tom": "motivacional, direto, resultados mensuráveis",
            "publico": "atletas e praticantes de atividade física intensa",
            "cta": "Montar meu plano de performance",
            "vibe_override": "energetic",
        },
        "emagrecimento": {
            "keywords": ["emagrecimento", "emagrecer", "peso", "dieta", "detox", "metabol", "gordura", "slim", "fit"],
            "tom": "acolhedor, transformação pessoal, sem julgamento",
            "publico": "pessoas buscando perda de peso saudável",
            "cta": "Começar minha transformação",
            "vibe_override": None,
        },
        "clinico": {
            "keywords": ["clinic", "patolog", "diabetes", "hipertens", "renal", "oncolog", "hospital", "intolerancia", "alergia", "celiac"],
            "tom": "profissional, científico, confiável",
            "publico": "pacientes com condições de saúde específicas",
            "cta": "Agendar avaliação nutricional",
            "vibe_override": "minimal",
        },
        "materno": {
            "keywords": ["gestante", "matern", "gravid", "amament", "bebe", "infantil", "pediatr"],
            "tom": "carinhoso, seguro, cuidado",
            "publico": "gestantes e mães",
            "cta": "Cuidar da minha nutrição",
            "vibe_override": "friendly",
        },
    },
    "academia": {
        "musculacao": {
            "keywords": ["muscula", "bodybuilding", "hipertrofia", "peso", "halter", "anilha"],
            "tom": "intenso, disciplina, resultados",
            "publico": "praticantes de musculação focados em ganho de massa",
            "cta": "Começar meu treino",
            "vibe_override": "energetic",
        },
        "funcional": {
            "keywords": ["funcional", "crossfit", "hiit", "circuit", "bootcamp", "outdoor"],
            "tom": "comunidade, superação, energia",
            "publico": "pessoas que buscam condicionamento geral",
            "cta": "Agendar aula experimental",
            "vibe_override": "energetic",
        },
        "pilates_yoga": {
            "keywords": ["pilates", "yoga", "alongamento", "flexibilidade", "meditacao", "mindful", "bem-estar"],
            "tom": "calmo, equilíbrio, consciência corporal",
            "publico": "pessoas buscando bem-estar e flexibilidade",
            "cta": "Agendar minha primeira aula",
            "vibe_override": "warm",
        },
        "luta": {
            "keywords": ["luta", "boxe", "muay thai", "jiu", "mma", "karate", "judo", "taekwondo", "kickbox"],
            "tom": "guerreiro, disciplina, respeito",
            "publico": "praticantes de artes marciais",
            "cta": "Agendar aula experimental",
            "vibe_override": "brutalism",
        },
        "natacao": {
            "keywords": ["natacao", "natação", "piscina", "hidro", "aquatica", "aquática", "hidroginastica", "hidroginástica", "touca", "oculos", "óculos", "raia", "mergulh", "flex", "aqua", "swimming", "swim"],
            "tom": "aquatico, energetico, confiavel, focado em progresso na piscina",
            "publico": "crianças, adultos e idosos buscando saúde, lazer ou condicionamento na água",
            "cta": "Agendar aula experimental",
            "vibe_override": "energetic",
        },
    },
    "restaurante": {
        "fino": {
            "keywords": ["gourmet", "fine dining", "chef", "degusta", "harmoniza", "wine", "vinho", "premium", "autoral"],
            "tom": "sofisticado, experiência gastronômica, exclusivo",
            "publico": "público exigente que valoriza experiência",
            "cta": "Reservar mesa",
            "vibe_override": "luxury",
        },
        "casual": {
            "keywords": ["casual", "familia", "almoco", "prato feito", "buffet", "self-service", "kg", "executivo"],
            "tom": "acolhedor, familiar, bom custo-benefício",
            "publico": "famílias e trabalhadores da região",
            "cta": "Ver cardápio",
            "vibe_override": "warm",
        },
        "delivery": {
            "keywords": ["delivery", "entrega", "ifood", "rappi", "pedido", "online", "app"],
            "tom": "rápido, prático, conveniente",
            "publico": "pessoas que pedem comida em casa",
            "cta": "Pedir agora",
            "vibe_override": "energetic",
        },
    },
    "clinica": {
        "estetica": {
            "keywords": ["estetic", "botox", "preenchimento", "harmoniza", "facial", "laser", "peeling", "rejuvenesc"],
            "tom": "sofisticado, resultado natural, autoestima",
            "publico": "pessoas buscando procedimentos estéticos",
            "cta": "Agendar avaliação",
            "vibe_override": "luxury",
        },
        "odonto": {
            "keywords": ["dent", "odonto", "ortodont", "implante", "clareamento", "sorriso", "oral"],
            "tom": "confiável, tecnologia, sorriso",
            "publico": "pacientes odontológicos",
            "cta": "Agendar avaliação",
            "vibe_override": "minimal",
        },
        "medica": {
            "keywords": ["medic", "consult", "exame", "diagnos", "tratamento", "saude", "prevenc"],
            "tom": "profissional, cuidado, confiança",
            "publico": "pacientes buscando atendimento médico",
            "cta": "Agendar consulta",
            "vibe_override": "minimal",
        },
    },
    "advogado": {
        "trabalhista": {
            "keywords": ["trabalh", "CLT", "rescis", "demiss", "FGTS", "hora extra", "acidente trabalho"],
            "tom": "combativo, defesa dos direitos, justiça",
            "publico": "trabalhadores com direitos violados",
            "cta": "Consulta gratuita",
            "vibe_override": None,
        },
        "empresarial": {
            "keywords": ["empresar", "societar", "contrato", "compliance", "tributar", "fiscal", "holding"],
            "tom": "estratégico, parceiro de negócios, expertise",
            "publico": "empresários e gestores",
            "cta": "Agendar reunião",
            "vibe_override": "minimal",
        },
        "familia": {
            "keywords": ["famil", "divorc", "pensao", "guarda", "inventar", "heranca", "casamento"],
            "tom": "empático, discreto, acolhedor",
            "publico": "pessoas em situações familiares delicadas",
            "cta": "Conversar com advogado",
            "vibe_override": "warm",
        },
    },
    "barbearia": {
        "premium": {
            "keywords": ["premium", "vip", "lounge", "whisky", "cerveja", "experiencia", "exclusiv"],
            "tom": "masculino premium, experiência, clube",
            "publico": "homens que valorizam experiência premium",
            "cta": "Agendar horário",
            "vibe_override": "luxury",
        },
        "tradicional": {
            "keywords": ["tradicional", "classico", "navalha", "barba", "bigode", "vintage"],
            "tom": "tradição, ofício, autenticidade",
            "publico": "homens que valorizam o corte clássico",
            "cta": "Agendar corte",
            "vibe_override": None,
        },
    },
}


def detectar_sub_nicho(segmento: str, dados_lead: dict) -> dict[str, Any]:
    """
    Detecta sub-nicho a partir dos dados do Google (nome, serviços, atributos, reviews).

    Args:
        segmento: O segmento principal do lead (ex: "nutricionista", "academia").
        dados_lead: Dicionário com dados do lead contendo:
            - nome: Nome do estabelecimento
            - servicos: Lista de serviços oferecidos
            - atributos: Lista de atributos/características
            - reviews: Lista de reviews com campo "texto" ou "text"
            - categorias: Lista de categorias do Google

    Returns:
        Dict com:
            - sub_nicho: Nome do sub-nicho detectado (ou None se genérico)
            - tom: Tom de comunicação recomendado
            - publico: Descrição do público-alvo
            - cta: Call-to-action recomendado
            - vibe_override: Override de vibe (ou None)
    """
    sub_nichos = SUB_NICHOS.get(segmento, {})
    if not sub_nichos:
        return {"sub_nicho": None, "tom": "", "publico": "", "cta": "", "vibe_override": None}

    # Montar texto para buscar keywords
    nome = (dados_lead.get("nome", "") or "").lower()
    servicos = " ".join(dados_lead.get("servicos", []) or []).lower() if isinstance(dados_lead.get("servicos"), list) else str(dados_lead.get("servicos", "")).lower()
    atributos = " ".join(dados_lead.get("atributos", []) or []).lower() if isinstance(dados_lead.get("atributos"), list) else str(dados_lead.get("atributos", "")).lower()
    reviews_text = " ".join([
        str(r.get("texto", r.get("text", "")))
        for r in (dados_lead.get("reviews", []) or [])[:10]
    ]).lower()
    categorias = " ".join(dados_lead.get("categorias", []) or []).lower() if isinstance(dados_lead.get("categorias"), list) else str(dados_lead.get("categorias", "")).lower()

    corpus = f"{nome} {servicos} {atributos} {reviews_text} {categorias}"

    # Pontuar cada sub-nicho
    best_score = 0
    best_sub = None
    for sub_key, sub_data in sub_nichos.items():
        score = sum(1 for kw in sub_data["keywords"] if kw in corpus)
        if score > best_score:
            best_score = score
            best_sub = sub_key

    if best_sub and best_score >= 2:  # Mínimo 2 keywords para confirmar
        sub = sub_nichos[best_sub]
        return {
            "sub_nicho": best_sub,
            "tom": sub["tom"],
            "publico": sub["publico"],
            "cta": sub["cta"],
            "vibe_override": sub.get("vibe_override"),
        }

    return {"sub_nicho": None, "tom": "", "publico": "", "cta": "", "vibe_override": None}


# Lazy import para get_design_context (usado quando necessário)
def get_design_context() -> Any:
    """
    Retorna o contexto de design do módulo principal.
    Usado para integração retrocompatível com design_context.py.
    """
    # pylint: disable=import-outside-toplevel,reimported
    from backend.agents.design_context import get_design_context as _get_design_context  # type: ignore
    return _get_design_context()
