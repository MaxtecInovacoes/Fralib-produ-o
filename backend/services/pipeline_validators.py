"""
Validadores de estado, entrada e sanidade do pipeline FraLib.
Inclui também funções puras de validação/sanitização extraídas de pipeline_prd_builder.
"""

import os
import re
from typing import Any, Optional, List, Tuple
from sqlalchemy import text


# ─── CONSTANTES COMPARTILHADAS ────────────────────────────────────────────────

LOCAL_STOPWORDS: set[str] = {
    "subtitulos",
    "subtítulos",
    "title",
    "hero",
    "section",
    "sections",
    "local",
    "business",
    "site",
    "homepage",
    "landing",
    "page",
    "studio",
    "premium",
    "cta",
}

SUBNICHE_RULES: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    "nutricionista": [
        ("nutrição esportiva", ("esport", "performance", "treino", "atleta", "atletas")),
        ("reeducação alimentar", ("reeduca", "hábitos", "habitos", "rotina alimentar")),
        ("emagrecimento saudável", ("emagrec", "composicao corporal", "composição corporal", "peso")),
        ("nutrição clínica", ("clinica", "clínica", "patologia", "saúde metabólica", "saude metabolica")),
    ],
    "academia": [
        ("musculação e performance", ("muscula", "performance", "hipertrof", "força", "forca")),
        ("treinamento funcional", ("funcional", "mobilidade", "condicionamento")),
    ],
    "clinica": [
        ("atendimento clínico local", ("consulta", "avaliação", "avaliacao", "atendimento")),
    ],
}


# ─── FUNÇÕES PURAS EXTRAÍDAS DE pipeline_prd_builder.py ─────────────────────

def normalize_segment(segmento: Any) -> str:
    """Normalize a segment string to lowercase ASCII without accents.

    Args:
        segmento: Any value to be converted to normalized segment string.

    Returns:
        Lowercase ASCII string with accented characters replaced.

    Example:
        >>> normalize_segment("Nutrição")
        'nutricao'
    """
    text = str(segmento or "").strip().lower()
    text = (
        text.replace("á", "a")
        .replace("à", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    return text


def ascii_text(value: Any) -> str:
    """Convert any value to ASCII-normalized lowercase string.

    Args:
        value: Any value to be converted.

    Returns:
        Normalized ASCII lowercase string.

    Note:
        This is an alias for normalize_segment for semantic clarity
        when used for general text normalization.
    """
    return normalize_segment(value)


def sanitize_keyword_term(value: Any, *, limit: int = 60) -> str:
    """Sanitize a keyword term by removing special characters and stopwords.

    Args:
        value: The keyword term to sanitize.
        limit: Maximum length of the sanitized term (default 60).

    Returns:
        Sanitized keyword term or empty string if invalid/stopword.

    Example:
        >>> sanitize_keyword_term("  nutrition, clinic  ")
        'nutrition clinic'
    """
    text = re.sub(r"\s+", " ", str(value or "")).strip(" ,.;:-")
    if not text:
        return ""
    if len(text) > limit:
        text = text[:limit].rstrip(" ,.;:-")
    low = ascii_text(text)
    if not low or low in {ascii_text(item) for item in LOCAL_STOPWORDS}:
        return ""
    return text


def extract_neighborhood(address: str) -> str:
    """Extract neighborhood name from a street address.

    Parses an address string to find the neighborhood component,
    excluding city tokens, street prefixes, and numeric components.

    Args:
        address: Full address string (e.g., "Rua X, 123, Centro, Curitiba, PR").

    Returns:
        The extracted neighborhood name or empty string if not found.

    Example:
        >>> extract_neighborhood("Rua das Flores, 100, Batel, Curitiba, PR")
        'Batel'
    """
    parts = [part.strip() for part in re.split(r"\s*[-,]\s*", str(address or "")) if part.strip()]
    city_tokens = {"pr", "parana", "paraná", "brasil"}
    street_prefixes = (
        "r ",
        "r. ",
        "rua ",
        "av ",
        "av. ",
        "avenida ",
        "rod ",
        "rod. ",
        "estr ",
        "estr. ",
        "estrada ",
        "travessa ",
        "tv ",
        "tv. ",
    )
    for part in parts:
        low = ascii_text(part)
        if not low or low in city_tokens:
            continue
        if re.search(r"\d", low):
            continue
        if low.startswith(street_prefixes):
            continue
        if len(low.split()) >= 1:
            return part
    return ""


def derive_subniche(
    segmento: Any,
    *,
    services: Any,
    reviews: Any,
    keywords: Any,
    business_name: Any,
) -> str:
    """Derive the business subniche from multiple data sources.

    Analyzes services, reviews, keywords, and business name to identify
    a specific subniche category based on predefined rules.

    Args:
        segmento: The business segment (e.g., "nutricionista").
        services: List of services or service data.
        reviews: List of customer reviews.
        keywords: Keyword research string or list.
        business_name: Name of the business.

    Returns:
        The identified subniche label or empty string.

    Example:
        >>> derive_subniche("nutricionista", services=[{"nome": "Nutricao esportiva"}],
        ...                 reviews=[], keywords="", business_name="")
        'nutrição esportiva'
    """
    segment_key = normalize_segment(segmento)
    candidates: list[str] = []
    for source in (services, reviews, keywords, business_name):
        if isinstance(source, list):
            for item in source:
                if isinstance(item, dict):
                    candidates.append(" ".join(str(v or "") for v in item.values()))
                else:
                    candidates.append(str(item or ""))
        else:
            candidates.append(str(source or ""))
    haystack = ascii_text(" ".join(candidates))
    for label, tokens in SUBNICHE_RULES.get(segment_key, []):
        if any(token in haystack for token in tokens):
            return label
    return ""


def build_local_keyword_terms(
    *,
    name: str,
    segment: str,
    city: str,
    neighborhood: str,
    subniche: str,
    services: Any,
    raw_keywords: Any,
) -> list[str]:
    """Build a list of localized keyword terms from business data.

    Combines business name, segment, subniche, city, neighborhood,
    services, and raw keywords into a deduplicated list of terms.

    Args:
        name: Business name.
        segment: Business segment.
        city: City name.
        neighborhood: Neighborhood name.
        subniche: Identified subniche.
        services: List of services.
        raw_keywords: Raw keyword string or list.

    Returns:
        Deduplicated list of keyword terms (max 10 items).

    Example:
        >>> terms = build_local_keyword_terms(
        ...     name="Nutri Clinic",
        ...     segment="nutricionista",
        ...     city="Curitiba",
        ...     neighborhood="Batel",
        ...     subniche="nutrição esportiva",
        ...     services=[{"nome": "Avaliacao"}],
        ...     raw_keywords="emagrecimento, dieta"
        ... )
    """
    terms: list[str] = []
    segment_label = str(segment or "").strip()
    city_label = str(city or "").strip()
    neighborhood_label = str(neighborhood or "").strip()
    subniche_label = str(subniche or "").strip()
    if name:
        terms.append(name)
    if segment_label:
        terms.append(segment_label)
    if subniche_label:
        terms.append(subniche_label)
    if city_label:
        terms.extend(
            [
                city_label,
                f"{segment_label} {city_label}".strip(),
                f"{subniche_label} {city_label}".strip() if subniche_label else "",
            ]
        )
    if neighborhood_label and city_label:
        terms.extend(
            [
                f"{segment_label} {neighborhood_label} {city_label}".strip(),
                f"{subniche_label} {neighborhood_label} {city_label}".strip() if subniche_label else "",
            ]
        )
    if isinstance(services, list):
        for item in services[:4]:
            if isinstance(item, dict):
                label = str(item.get("nome") or item.get("title") or item.get("label") or "").strip()
            else:
                label = str(item or "").strip()
            if not label:
                continue
            if city_label:
                terms.append(f"{label} {city_label}")
            terms.append(label)
    if isinstance(raw_keywords, str):
        terms.extend(re.split(r"[,;\n]", raw_keywords))
    elif isinstance(raw_keywords, list):
        terms.extend(str(item or "") for item in raw_keywords)
    cleaned: list[str] = []
    seen: set[str] = set()
    for term in terms:
        clean = sanitize_keyword_term(term)
        key = ascii_text(clean)
        if not clean or not key or key in seen:
            continue
        seen.add(key)
        cleaned.append(clean)
    return cleaned[:10]


def review_highlights_from_reviews(reviews: Any) -> list[dict[str, str]]:
    """Extract highlight themes from customer reviews.

    Analyzes review text to identify common positive themes
    like empathy, personalization, follow-up, and results.

    Args:
        reviews: List of review dictionaries with 'texto' or 'text' keys.

    Returns:
        List of highlight dictionaries with 'title' and 'source' keys (max 4).

    Example:
        >>> reviews = [{"text": "Atendimento muito atencioso e personalizado"}]
        >>> review_highlights_from_reviews(reviews)
        [{'title': 'Empatia no atendimento', 'source': 'depoimentos reais'}]
    """
    if not isinstance(reviews, list):
        return []
    text = " ".join(
        str((r or {}).get("texto") or (r or {}).get("text") or "")
        for r in reviews
        if isinstance(r, dict)
    ).lower()
    patterns = [
        ("Empatia no atendimento", ("empatia", "humano", "paciente", "atenciosa")),
        ("Plano ajustado à rotina", ("personalizado", "preferências", "rotina", "realidade")),
        ("Acompanhamento próximo", ("acompanhando", "dúvidas", "ajustes", "contato")),
        ("Resultados percebidos", ("resultados", "bem-estar", "saúde", "hábitos")),
    ]
    highlights = []
    for title, words in patterns:
        if any(word in text for word in words):
            highlights.append({"title": title, "source": "depoimentos reais"})
    return highlights[:4]


def object_to_dict(value: Any) -> dict[str, Any]:
    """Convert an object to a dictionary representation.

    Handles Pydantic models, objects with dict/model_dump methods,
    and plain objects with __dict__.

    Args:
        value: Any object to convert.

    Returns:
        Dictionary representation of the object.

    Example:
        >>> from types import SimpleNamespace
        >>> object_to_dict(SimpleNamespace(a=1, b=2))
        {'a': 1, 'b': 2}
    """
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return {}


# ─── VALIDAÇÃO DE ENTRADA ──────────────────────────────────────────────────

def validar_config_pipeline(config: dict) -> Tuple[bool, List[str]]:
    """Valida configuração do pipeline antes da execução."""
    erros = []

    # Validar campos obrigatórios
    if not config.get("segmento"):
        erros.append("segmento é obrigatório")
    if not config.get("cidade"):
        erros.append("cidade é obrigatória")

    # Validar quantidade
    quantidade = config.get("quantidade", 1)
    if not isinstance(quantidade, int) or quantidade < 1:
        erros.append("quantidade deve ser um inteiro >= 1")

    # Validar score_minimo
    score_minimo = config.get("score_minimo", 45)
    if score_minimo and (not isinstance(score_minimo, int) or score_minimo < 0 or score_minimo > 100):
        erros.append("score_minimo deve estar entre 0 e 100")

    return len(erros) == 0, erros


def validar_lead_data(lead_data: dict) -> Tuple[bool, List[str]]:
    """Valida dados do lead antes de processar."""
    erros = []

    if not lead_data.get("nome"):
        erros.append("nome do lead é obrigatório")

    if not lead_data.get("cidade"):
        erros.append("cidade do lead é obrigatória")

    # Rating deve ser numérico entre 0 e 5
    rating = lead_data.get("rating", 0)
    if rating and (not isinstance(rating, (int, float)) or rating < 0 or rating > 5):
        erros.append("rating deve estar entre 0 e 5")

    return len(erros) == 0, erros


def validar_segmento(segmento: str) -> bool:
    """Valida se segmento não está vazio ou apenas espaços."""
    if not segmento or not segmento.strip():
        return False
    return True


def validar_cidade(cidade: str) -> bool:
    """Valida se cidade não está vazia ou apenas espaços."""
    if not cidade or not cidade.strip():
        return False
    return True


# ─── VALIDAÇÃO DE ESTADO ────────────────────────────────────────────────────

def validar_state_obrigatorio(state, campos: List[str]) -> Tuple[bool, List[str]]:
    """Valida que campos obrigatórios existem no state."""
    erros = []
    for campo in campos:
        if not hasattr(state, campo):
            erros.append(f"state não tem campo: {campo}")
        elif getattr(state, campo, None) is None:
            erros.append(f"state.{campo} está vazio")
    return len(erros) == 0, erros


def validar_fase_permitida(fase: int, fase_minima: int = 1, fase_maxima: int = 11) -> bool:
    """Valida se fase está no range permitido."""
    return fase_minima <= fase <= fase_maxima


def validar_score_lead(score: Any, score_minimo: int = 45) -> bool:
    """Valida se score do lead atende ao mínimo."""
    try:
        score_int = int(score) if score else 0
        return score_int >= score_minimo
    except (ValueError, TypeError):
        return False


def validar_tier_qualificado(tier: str) -> bool:
    """Verifica se tier representa lead qualificado."""
    if not tier:
        return False
    tier_upper = tier.upper()
    # Tiers rejeitados
    if tier_upper in ("REJEITADO", "BAIXO", "FRIO"):
        return False
    # Tiers válidos para continuar
    return tier_upper in ("STANDARD", "QUENTE", "ALTO", "PREMIUM", "HOT")


def validar_html_result(html: str, min_chars: int = 500) -> Tuple[bool, str]:
    """Valida HTML gerado pelo builder/renderer."""
    if not html:
        return False, "HTML vazio"

    if len(html) < min_chars:
        return False, f"HTML muito curto ({len(html)} chars)"

    # Verificar tags essenciais
    if "</html>" not in html.lower():
        return False, "HTML sem tag de fechamento </html>"

    if "<body" not in html.lower():
        return False, "HTML sem tag <body>"

    return True, "OK"


def validar_prd_arquiteto(prd) -> Tuple[bool, str]:
    """Valida PRD do Arquiteto Mestre."""
    if not prd:
        return False, "PRD vazio"

    # Verificar se tem sections
    if not hasattr(prd, "sections"):
        return False, "PRD sem sections"

    if not prd.sections or len(prd.sections) == 0:
        return False, "PRD com sections vazio"

    # Verificar builder_prompt ou sections
    if hasattr(prd, "builder_prompt"):
        if not prd.builder_prompt or len(prd.builder_prompt) < 100:
            return False, "builder_prompt muito curto"

    return True, "OK"


# ─── CHECKS DE SANIDADE ────────────────────────────────────────────────────

def sanity_check_lead_existente(
    engine,
    nome: str,
    cidade: str,
    tenant_id: int,
    status_permitidos: List[str] = None
) -> Optional[str]:
    """
    Verifica se lead já existe no banco com status que impede reprocessamento.
    Retorna o ID do lead se existir, None caso contrário.
    """
    if status_permitidos is None:
        status_permitidos = ["pendente", "capturado", "processando"]

    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT id, status FROM leads
                    WHERE lower(trim(nome)) = lower(trim(:nome))
                      AND lower(cidade) = lower(:cidade)
                      AND user_id = :user_id
                    LIMIT 1
                """),
                {"nome": nome, "cidade": cidade, "user_id": tenant_id}
            ).fetchone()

            if result:
                lead_id, status = result
                if status in status_permitidos:
                    return None  # Pode processar
                return str(lead_id)  # Já existe com status que impede
    except Exception as e:
        print(f"[Sanity] Erro ao verificar lead existente: {e}")

    return None


def sanity_check_lead_ja_contatado(
    engine,
    nome: str,
    tenant_id: int
) -> bool:
    """Verifica se lead já foi contatado anteriormente."""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT id FROM leads
                    WHERE lower(trim(nome)) = lower(trim(:nome))
                      AND user_id = :uid
                      AND status IN ('contatado', 'concluido')
                """),
                {"nome": nome, "uid": tenant_id}
            ).fetchone()
            return result is not None
    except Exception:
        return False


def sanity_check_checkpoint_lead_match(
    pipeline_id: str,
    lead_nome: str,
    get_dados_agente
) -> bool:
    """
    Verifica se checkpoint é do mesmo lead (evita contaminação).
    Retorna True se checkpoint é válido para este lead.
    """
    try:
        _ckpt = get_dados_agente(pipeline_id, "arquiteto_mestre")
        if _ckpt and _ckpt.get("prd_json"):
            _ckpt_bname = _ckpt["prd_json"].get("business_name", "")
            if _ckpt_bname and _ckpt_bname.lower().strip() != lead_nome.lower().strip():
                return False
    except Exception:
        pass
    return True


def sanity_check_leads_duplicados(
    engine,
    cidade: str,
    tenant_id: int
) -> set:
    """Retorna conjunto de nomes de leads já existentes na cidade."""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT lower(trim(nome)) FROM leads
                    WHERE lower(cidade) = lower(:cidade)
                      AND user_id = :user_id
                      AND COALESCE(status, '') IN ('processando','concluido','contatado','deployed','erro')
                """),
                {"cidade": cidade, "user_id": tenant_id}
            )
            return {row[0] for row in result.fetchall()}
    except Exception:
        return set()


# ─── VALIDAÇÃO DE CACHE ─────────────────────────────────────────────────────

def pode_usar_cache(config: dict, cold_run: bool = False) -> bool:
    """Determina se pode usar dados em cache."""
    if cold_run:
        return False
    if config.get("_forcar_renovacao"):
        return False
    if config.get("_cold_run"):
        return False
    return True


# ─── VALIDAÇÃO DE CREDENCIAIS/PERMISSÕES ────────────────────────────────────

def validar_permissao_executar(
    db_session,
    tenant_id: int,
    validar_permissao_pipeline
) -> Tuple[bool, str]:
    """Valida se tenant pode executar o pipeline."""
    try:
        _perm = validar_permissao_pipeline(db_session, tenant_id)
        if not _perm.get("allowed"):
            return False, _perm.get("message") or "Bloqueado"
        return True, "OK"
    except Exception as e:
        return False, str(e)


def validar_plano_sdr(db_session, tenant_id: int, tenant_sdr_allowed) -> bool:
    """Verifica se plano do tenant permite SDR/WhatsApp."""
    try:
        return tenant_sdr_allowed(db_session, tenant_id)
    except Exception:
        return False
