"""Content validations for generated HTML (text, emojis, emails, fake data)."""


import html as _html
import re
import unicodedata
from typing import Any


_EMOJI_RE = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "⬀-⯿"
    "☀-➿"
    "]+"
)


def contains_emoji(text: str) -> bool:
    """Check if text contains visible emoji characters."""
    if _EMOJI_RE.search(text or ""):
        return True
    return any(_is_emoji_symbol(ch) for ch in (text or ""))


def strip_emoji_symbols(text: str) -> str:
    """Remove all emoji symbols from text."""
    cleaned = _EMOJI_RE.sub("", text or "")
    return "".join(ch for ch in cleaned if not _is_emoji_symbol(ch))


def contains_internal_instruction(text: str) -> bool:
    """Check if text contains leaked internal instructions."""
    normalized = _normalize(text)
    internal_markers = (
        "dados capturados",
        "sem inventar",
        "apresente somente",
        "render one",
        "allowed facts",
        "site build contract",
    )
    return any(marker in normalized for marker in internal_markers)


def extract_emails(value) -> list[str]:
    """Extract email addresses from text."""
    if isinstance(value, (list, tuple, set)):
        value = " ".join(str(v) for v in value)
    return re.findall(r"[\w.\-+]+@[\w.\-]+\.[a-zA-Z]{2,}", str(value or ""))


def validate_emails(public_text: str, allowed_emails: set, found_emails: set) -> list[str]:
    """Check for unconfirmed emails in HTML."""
    unknown_emails = sorted(e for e in found_emails if e not in allowed_emails)
    if unknown_emails:
        return ["HTML contem email nao confirmado: " + ", ".join(unknown_emails)]
    return []


def detect_fake_data(normalized_text: str, address: str) -> list[str]:
    """Detect invented/template data in HTML."""
    problems: list[str] = []
    for fake in ("rua augusta", "vila madalena", "lorem ipsum"):
        if fake in normalized_text and fake not in _normalize(address):
            problems.append(f"HTML contem dado/template inventado: {fake}")
    return problems


def unsupported_metrics(text: str, prd) -> list[str]:
    """Check for unconfirmed metrics (reviews count, prices, percentages)."""
    issues: list[str] = []
    reviews_count = str(_get_field(prd, "reviews_count", "total_reviews", default="") or "")
    price_range = str(_get_field(prd, "faixa_preco", "price_range", default="") or "")
    tokens = re.findall(r"\b\d{2,4}\+|\b\d{2,3}\s*%|R\$\s*\d+(?:[,.]\d+)?", text)
    for token in tokens:
        compact = token.replace(" ", "")
        number = re.sub(r"\D", "", compact)
        if compact.endswith("+"):
            if not reviews_count or number != re.sub(r"\D", "", reviews_count):
                issues.append(f"metrica com plus nao confirmada: {token}")
        elif "%" in compact:
            issues.append(f"percentual nao confirmado: {token}")
        elif compact.startswith("R$"):
            if not price_range or compact not in price_range.replace(" ", ""):
                issues.append(f"preco nao confirmado: {token}")
    return issues


def unsupported_public_claims(text: str, prd) -> list[str]:
    """Check for unsupported superlative claims."""
    normalized = _normalize(text)
    allowed_blob = _normalize(
        " ".join(
            str(_get_field(prd, key, default="") or "")
            for key in (
                "business_name",
                "nome_negocio",
                "segmento",
                "description",
                "descricao",
            )
        )
    )
    forbidden = {
        "melhor": "melhor",
        "mais premi": "mais premia",
        "numero 1": "numero 1",
        "premium": "premium",
        "exclusiva": "exclusiva",
        "referencia": "referencia",
        "lider": "lider",
        "moderna": "moderna",
        "top": "top",
        "elite": "elite",
        "vip": "VIP",
    }
    found = []
    padded = f" {normalized} "
    allowed_padded = f" {allowed_blob} "
    for key, label in forbidden.items():
        if f" {key} " in padded and f" {key} " not in allowed_padded:
            found.append(label)
    if found:
        return [
            "HTML contem claim publica sem prova nos fatos permitidos: "
            + ", ".join(found)
        ]
    return []


def unsupported_hours(text: str, prd) -> list[str]:
    """Check for invented business hours."""
    hours = _get_field(prd, "hours", "horarios", default={}) or {}
    if not isinstance(hours, dict):
        return []
    issues: list[str] = []
    sunday_closed = any(
        "domingo" in _normalize(key) and "fechado" in _normalize(key)
        for key in hours.keys()
    )
    if sunday_closed and re.search(r"domingo[^.\n|;]{0,80}\d{1,2}\s*h", text or "", re.I):
        issues.append("HTML inventou horario de domingo apesar do lead marcar fechado")
    return issues


def unsupported_institutional_copy(text: str, prd) -> list[str]:
    """Check for unconfirmed institutional copy."""
    normalized = _normalize(text)
    risky_patterns = {
        "fundada": "historia/fundacao nao confirmada",
        "com o proposito": "proposito institucional nao confirmado",
        "professores dedicados": "equipe/professores nao confirmados",
        "professores que se preocupam": "equipe/professores nao confirmados",
        "instrutores dedicados": "equipe/instrutores nao confirmados",
        "instrutores qualificados": "equipe/instrutores nao confirmados",
        "profissionais dedicados": "equipe/profissionais nao confirmados",
        "equipe especializada": "equipe nao confirmada",
        "equipe qualificada": "equipe nao confirmada",
        "equipe dedicada": "equipe nao confirmada",
        "correcao tecnica": "metodologia tecnica nao confirmada",
        "equipamentos funcionais": "equipamentos nao confirmados",
        "ambiente de treino eficaz": "ambiente/resultado nao confirmado",
        "experiencia fitness personalizada": "experiencia personalizada nao confirmada",
        "treinamentos personalizados": "treinamentos personalizados nao confirmados",
        "ambiente moderno": "ambiente moderno nao confirmado",
        "suporte especializado": "suporte especializado nao confirmado",
        "tecnologia de ponta": "tecnologia/equipamento nao confirmado",
        "infraestrutura tecnica de ponta": "infraestrutura/equipamento nao confirmado",
        "infraestrutura de ponta": "infraestrutura/equipamento nao confirmado",
        "alto desempenho": "promessa de desempenho nao confirmada",
        "melhor desempenho": "promessa de desempenho nao confirmada",
        "transformacao fisica": "promessa de transformacao nao confirmada",
        "transformacao fisica e mental": "promessa de transformacao nao confirmada",
        "epicentro": "claim institucional exagerada",
        "resultados reais": "resultado nao confirmado",
        "estrutura completa": "estrutura completa nao confirmada",
        "ambiente completo": "ambiente completo nao confirmado",
        "treine onde estiver": "beneficio de aula online nao confirmado",
        "sua jornada fitness comeca aqui": "slogan nao confirmado",
        "multiplas opcoes": "opcoes de pagamento/servico nao confirmadas",
    }
    found = [label for key, label in risky_patterns.items() if key in normalized]
    if found:
        return ["HTML contem copy institucional inventada: " + ", ".join(found)]
    return []


def service_attribute_misuse(html: str, prd) -> list[str]:
    """Check for operational attributes exposed as services."""
    services = _get_field(prd, "servicos", "services", default=[]) or []
    if services:
        return []
    service_scope = _normalize(_service_scope_text(html))
    headings = _heading_text(html)
    forbidden_headings = {
        "aulas online": "Aulas online",
        "aulas on line": "Aulas online",
        "banheiro": "Banheiro",
        "cartao de credito": "Cartao de credito",
        "cartoes de credito": "Cartoes de credito",
        "cartao de debito": "Cartao de debito",
        "cartoes de debito": "Cartoes de debito",
        "pagamentos": "Pagamentos",
        "pagamentos por nfc": "Pagamentos por NFC",
        "servicos locais": "Servicos locais",
        "servicos no local": "Servicos no local",
    }
    found = [label for key, label in forbidden_headings.items() if key in headings]
    if found:
        return [
            "HTML transformou atributos operacionais em servicos: " + ", ".join(found)
        ]
    invented_services = {
        "muay thai": "Muay Thai",
        "danca": "Danca",
        "dancas": "Dancas",
        "musculacao": "Musculacao",
    }
    invented = [
        label
        for key, label in invented_services.items()
        if key in service_scope or key in headings
    ]
    if invented:
        return [
            "HTML criou/expôs servicos nao confirmados: " + ", ".join(invented)
        ]
    return []


def missing_required_copy(text: str, prd) -> list[str]:
    """Check that planned headings appear in generated HTML."""
    planned = _planned_headings(prd)
    if len(planned) < 3:
        return []
    normalized = _normalize(text)
    matched = sum(1 for heading in planned if _normalize(heading) in normalized)
    required = min(2, len(planned))
    if _archetype_id(prd) == "BOLD_ENERGY" or _is_fitness_segment(prd):
        required = min(2, len(planned))
    if _get_field(prd, "renderer_owns_headings", default=False):
        required = 1
    configured_required = _get_field(prd, "heading_preservation_min", default=None)
    if configured_required is not None:
        try:
            required = int(configured_required)
        except (TypeError, ValueError):
            pass
    required = max(0, min(required, len(planned)))
    if required == 0:
        return []
    if matched < required:
        return [
            f"HTML preservou apenas {matched}/{len(planned)} headings aprovados do PRD; minimo={required}"
        ]
    return []


def _service_scope_text(html: str) -> str:
    """Extract service scope text from HTML sections."""
    chunks = re.findall(
        r"(?is)<!--\s*SECTION:servicos\s*-->(.*?)<!--\s*/SECTION:servicos\s*-->",
        html or "",
    )
    if not chunks:
        chunks = re.findall(
            r"(?is)<section\b[^>]*(?:id|data-section)=['\"]?servicos['\"]?[^>]*>(.*?)</section>",
            html or "",
        )
    return " ".join(_visible_text(chunk) for chunk in chunks)


def _heading_text(html: str) -> str:
    """Extract heading text from HTML."""
    headings = re.findall(r"(?is)<h[1-4]\b[^>]*>(.*?)</h[1-4]>", html or "")
    clean = " ".join(_visible_text(h) for h in headings)
    return _normalize(clean)


def _planned_headings(prd) -> list[str]:
    """Extract planned headings from PRD sections."""
    headings: list[str] = []
    for section in _sections(prd):
        copy = _section_copy(section)
        for key in ("h1", "h2", "headline", "title", "titulo"):
            value = section.get(key) or copy.get(key)
            if isinstance(value, str) and value.strip():
                headings.append(value.strip())
    return headings


def _sections(prd) -> list[dict]:
    """Extract sections from PRD."""
    raw = _get_field(prd, "sections", "secoes", default=[]) or []
    if not isinstance(raw, list):
        return []
    sections = []
    for item in raw:
        if isinstance(item, dict):
            sections.append(item)
        elif hasattr(item, "model_dump"):
            sections.append(item.model_dump(by_alias=True))
        elif hasattr(item, "dict"):
            sections.append(item.dict())
        elif hasattr(item, "__dict__"):
            sections.append(vars(item))
    return sections


def _section_copy(section: dict) -> dict:
    """Extract copy from section."""
    copy = section.get("copy")
    return copy if isinstance(copy, dict) else {}


def _archetype_id(prd) -> str:
    """Get visual archetype ID from PRD."""
    visual_dna = _get_field(prd, "visual_dna", default={}) or {}
    if hasattr(visual_dna, "model_dump"):
        visual_dna = visual_dna.model_dump()
    if not isinstance(visual_dna, dict):
        return ""
    archetype = visual_dna.get("archetype")
    if isinstance(archetype, dict):
        return str(archetype.get("archetype") or archetype.get("id") or "").upper()
    return str(archetype or visual_dna.get("id") or "").upper()


def _is_fitness_segment(prd) -> bool:
    """Check if PRD is for fitness segment."""
    segment = _normalize(
        _get_field(prd, "segmento", "segment", "nicho", default="")
    )
    return any(token in segment for token in ("academia", "fitness", "cross", "treino"))


def _visible_text(html: str) -> str:
    """Extract visible text from HTML (strips tags, scripts, styles)."""
    clean = re.sub(r"(?is)<script\b.*?</script>", " ", html or "")
    clean = re.sub(r"(?is)<style\b.*?</style>", " ", clean)
    clean = re.sub(r"(?is)<!--.*?-->", " ", clean)
    clean = re.sub(r"(?is)<[^>]+>", " ", clean)
    return _html.unescape(re.sub(r"\s+", " ", clean)).strip()


def _normalize(value: str) -> str:
    """Normalize text for comparison (ASCII, lowercase, spaces)."""
    text = str(value or "")
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).lower()
    return re.sub(r"\s+", " ", text).strip()


def _get_field(obj: Any, *names: str, default=None) -> Any:
    """Get value from dict or object attribute, trying multiple field names."""
    if isinstance(obj, dict):
        for name in names:
            value = obj.get(name)
            if value not in (None, "", [], {}):
                return value
        return default
    for name in names:
        value = getattr(obj, name, None)
        if value not in (None, "", [], {}):
            return value
    return default


def _is_emoji_symbol(ch: str) -> bool:
    """Check if character is an emoji symbol/combining mark."""
    if ch in ("️", "‍"):
        return True
    code = ord(ch)
    if code in (0x00A9, 0x00AE, 0x2122, 0x2139):
        return True
    category = unicodedata.category(ch)
    return category.startswith("S") and code >= 0x2190
