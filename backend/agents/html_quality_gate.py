"""Deterministic quality gate for generated landing HTML.

This module provides the main audit entry point. Specialized validations are
delegated to dedicated modules:
- html_phase6_repair: Phase 6/T publication contract repairs
- html_builder_repair: Builder renderer output repairs
- html_publication_helpers: Text rewriting, media, maps, sitemap
- html_contract_validator: SEO, LGPD, and Phase 6 contract checks
- html_media_validator: Images, videos, placeholders, URLs
- html_content_validator: Text content, emojis, emails, fake data
"""

from __future__ import annotations

import dataclasses
import datetime
import html as _html
import re
import unicodedata


# Import validators from dedicated modules
from backend.agents.html_contract_validator import (
    phase6_contract_problems as _phase6_contract_problems,
    publication_contract_problems as _publication_contract_problems,
    visual_contract_problems as _visual_contract_problems,
)
from backend.agents.html_content_validator import (
    contains_emoji as _contains_emoji,
    contains_internal_instruction as _contains_internal_instruction,
    detect_fake_data as _detect_fake_data,
    extract_emails as _extract_emails,
    missing_required_copy as _missing_required_copy,
    service_attribute_misuse as _service_attribute_misuse,
    strip_emoji_symbols as _strip_emoji_symbols,
    unsupported_hours as _unsupported_hours,
    unsupported_institutional_copy as _unsupported_institutional_copy,
    unsupported_metrics as _unsupported_metrics,
    unsupported_public_claims as _unsupported_public_claims,
)
from backend.agents.html_media_validator import (
    has_placeholder_media as _has_placeholder_media,
    media_urls_from_html as _media_urls_from_html,
    minimum_required_media as _minimum_required_media,
    photo_urls as _photo_urls,
)

# Import repair modules
from backend.agents.html_phase6_repair import (
    repair_phase6_publication_contract as _repair_phase6_publication_contract,
)
from backend.agents.html_builder_repair import (
    publication_page_title as _publication_page_title,
    publication_page_description as _publication_page_description,
    repair_builder_publication_contract as _repair_builder_publication_contract,
)
from backend.agents.html_publication_helpers import (
    ensure_minimum_footer as _ensure_minimum_footer,
    ensure_required_media_section as _ensure_required_media_section,
    ensure_single_location_map as _ensure_single_location_map,
    gerar_sitemap_robots as _gerar_sitemap_robots,
    get_business_from_prd as _get_business_from_prd,
    get_og_image_from_prd as _get_og_image_from_prd,
    keep_client_navigation_in_page as _keep_client_navigation_in_page,
    normalize_media_strip_order as _normalize_media_strip_order,
    dedupe_media_narratives as _dedupe_media_narratives,
    remove_placeholder_markers as _remove_placeholder_markers,
    remove_unknown_emails as _remove_unknown_emails,
    add_image_error_fallbacks as _add_image_error_fallbacks,
    remove_unrequested_service_fallbacks as _remove_unrequested_service_fallbacks,
    remove_unsafe_review_sections as _remove_unsafe_review_sections,
    replace_visible_text_only as _replace_visible_text_only,
    replace_attribute_text as _replace_attribute_text,
    repair_legacy_css_rewrites as _repair_legacy_css_rewrites,
    UNCONFIRMED_SERVICE_TERM_REPLACEMENTS,
    OPERATIONAL_ATTRIBUTE_REPLACEMENTS,
    PUBLIC_CLAIM_REPLACEMENTS,
)


# ─── Public Classes ──────────────────────────────────────────────────────────


class HtmlQualityGateError(ValueError):
    """Raised when generated HTML is not safe to publish."""


@dataclasses.dataclass
class HtmlQualityReport:
    aprovado: bool
    problemas: list[str]


# ─── Public Entry Points ─────────────────────────────────────────────────────


def audit_generated_html(html: str, prd) -> HtmlQualityReport:
    """Audit generated HTML for quality issues.

    Validations are delegated to specialized modules for:
    - Contract checks (SEO, LGPD, Phase 6)
    - Media validation (images, videos, placeholders)
    - Content validation (text, emojis, emails, fake data)
    """
    problems: list[str] = []
    text = _visible_text(html)
    public_text = f"{text} {_metadata_text(html)}"
    normalized_text = _normalize(public_text)
    photos = _photo_urls(prd)
    problems.extend(_contract_problems(prd))

    if _contains_emoji(public_text):
        problems.append("HTML contem emoji visivel; use SVG/HTML sem emoji")

    if _contains_internal_instruction(public_text):
        problems.append("HTML vazou instrucao interna/policy para o visitante")

    if _has_placeholder_media(html, text):
        problems.append("HTML contem placeholder visual em vez de midia final")

    media_refs = _media_urls_from_html(html)
    real_media_count = len(media_refs)
    min_required_media = _minimum_required_media(prd, photos)
    if real_media_count < min_required_media:
        problems.append(
            f"HTML usou {real_media_count} midias finais; "
            f"minimo exigido={min_required_media}"
        )

    address = _get(prd, "address", "endereco", default="")
    if address and _normalize(address) not in normalized_text:
        problems.append("Endereco real do lead nao aparece de forma visivel no HTML")

    allowed_emails = set(_extract_emails(_get(prd, "email", "emails", default="")))
    found_emails = set(_extract_emails(public_text))
    unknown_emails = sorted(e for e in found_emails if e not in allowed_emails)
    if unknown_emails:
        problems.append("HTML contem email nao confirmado: " + ", ".join(unknown_emails))

    problems.extend(_detect_fake_data(normalized_text, address))

    metric_issues = _unsupported_metrics(public_text, prd)
    problems.extend(metric_issues)

    problems.extend(_unsupported_public_claims(public_text, prd))
    problems.extend(_unsupported_hours(public_text, prd))
    problems.extend(_unsupported_institutional_copy(public_text, prd))
    problems.extend(_service_attribute_misuse(html, prd))
    problems.extend(_missing_required_copy(text, prd))
    problems.extend(_visual_experience_problems(html, prd))
    problems.extend(_visual_contract_problems(html, prd))
    problems.extend(_publication_contract_problems(html))
    problems.extend(_phase6_contract_problems(html))

    if _requires_motion(prd) and not _has_real_motion(html):
        problems.append("HTML nao contem animacao/motion real apesar do PRD exigir")

    return HtmlQualityReport(aprovado=not problems, problemas=problems)


# ─── Lazy Loading Helper (#9) ────────────────────────────────────────────────


_LAZY_LOAD_IMG_RE = re.compile(r"<img\b(?![^>]*\bloading=)([^>]*?)>", re.IGNORECASE)
_LAZY_LOAD_SKIP_HERO = re.compile(r"<img\b[^>]*\bdata-hero-image", re.IGNORECASE)


def apply_lazy_loading_to_images(html: str) -> str:
    """Adiciona loading=lazy e decoding=async em todas as <img> exceto a do hero.

    -25% LCP, -40% banda. Imagens below-the-fold carregam sob demanda.
    """
    if not html or "<img" not in html:
        return html

    def _add_lazy(match: re.Match) -> str:
        tag = match.group(0)
        # Nao modifica a imagem do hero (ja tem loading=eager)
        if 'data-hero-image' in tag or 'loading=' in tag:
            return tag
        # Adicionar loading=lazy + decoding=async antes do > de fechamento
        if tag.endswith("/>"):
            return tag[:-2] + ' loading="lazy" decoding="async" />'
        return tag[:-1] + ' loading="lazy" decoding="async">'

    return _LAZY_LOAD_IMG_RE.sub(_add_lazy, html)


def validate_generated_html(html: str, prd) -> None:
    """Validate generated HTML. Raises HtmlQualityGateError if issues found."""
    report = audit_generated_html(html, prd)
    if not report.aprovado:
        raise HtmlQualityGateError("; ".join(report.problemas))


def normalize_generated_html_for_publication(html: str, prd) -> str:
    """Remove deterministic public-copy violations before final validation."""
    cleaned = _strip_emoji_symbols(html or "")
    cleaned = _repair_legacy_css_rewrites(cleaned)
    cleaned = _keep_client_navigation_in_page(cleaned)
    cleaned = _replace_visible_text_only(cleaned, PUBLIC_CLAIM_REPLACEMENTS)
    cleaned = _replace_attribute_text(cleaned, PUBLIC_CLAIM_REPLACEMENTS)
    cleaned = _replace_visible_text_only(cleaned, UNCONFIRMED_SERVICE_TERM_REPLACEMENTS)
    cleaned = _replace_visible_text_only(cleaned, OPERATIONAL_ATTRIBUTE_REPLACEMENTS)
    cleaned = _remove_placeholder_markers(cleaned)
    cleaned = _remove_unknown_emails(cleaned, prd)
    cleaned = _add_image_error_fallbacks(cleaned, prd)
    cleaned = _remove_unrequested_service_fallbacks(cleaned, prd)
    cleaned = _remove_unsafe_review_sections(cleaned, prd)
    cleaned = _ensure_required_media_section(cleaned, prd)
    cleaned = _dedupe_media_narratives(cleaned)
    cleaned = _normalize_media_strip_order(cleaned)
    cleaned = _ensure_single_location_map(cleaned, prd)
    cleaned = _ensure_minimum_footer(cleaned, prd)
    # Lazy loading (#9)
    cleaned = apply_lazy_loading_to_images(cleaned)
    return cleaned


def sanitize_builder_html_for_publication(
    html: str, prd, *, include_phase6: bool = True,
    site_dir: str = "", deploy_url: str = "",
) -> str:
    """Apply only safe publication fixes without redesigning Builder output."""
    from backend.agents.html_phase6_repair import publication_keyword_meta as _publication_keyword_meta

    cleaned = _strip_emoji_symbols(html or "")
    cleaned = _repair_legacy_css_rewrites(cleaned)
    cleaned = _keep_client_navigation_in_page(cleaned)
    cleaned = _replace_visible_text_only(cleaned, PUBLIC_CLAIM_REPLACEMENTS)
    cleaned = _replace_attribute_text(cleaned, PUBLIC_CLAIM_REPLACEMENTS)
    cleaned = _remove_unknown_emails(cleaned, prd)
    cleaned = _add_image_error_fallbacks(cleaned, prd)
    cleaned = _ensure_required_media_section(cleaned, prd)
    cleaned = _repair_builder_publication_contract(cleaned, prd)
    if include_phase6:
        cleaned = _repair_phase6_publication_contract(cleaned, prd)
    cleaned = _replace_visible_text_only(cleaned, PUBLIC_CLAIM_REPLACEMENTS)
    cleaned = _replace_attribute_text(cleaned, PUBLIC_CLAIM_REPLACEMENTS)

    # Lazy loading em imagens (#9)
    cleaned = apply_lazy_loading_to_images(cleaned)

    # OG Tags completas
    business = _get_business_from_prd(prd)
    canonical = _publication_canonical_from_prd(prd) or deploy_url
    low = cleaned.lower()
    keywords = _publication_keyword_meta(prd)
    # og:title
    if 'property="og:title"' not in low:
        og_title = _publication_page_title(prd, business)
        if og_title:
            cleaned = re.sub(r"(?is)</head>", f'<meta property="og:title" content="{_escape(og_title)}">\n</head>', cleaned, count=1)
    # og:description
    if 'property="og:description"' not in low:
        og_desc = _publication_page_description(prd, business)
        if og_desc:
            cleaned = re.sub(r"(?is)</head>", f'<meta property="og:description" content="{_escape(og_desc)}">\n</head>', cleaned, count=1)
    # og:image
    if 'property="og:image"' not in low or 'content=""' in low:
        og_image = _get_og_image_from_prd(prd) or "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1200&h=630&fit=crop"
        cleaned = re.sub(
            r'(?is)(<meta\s+property=["\']og:image["\']\s+content=)""',
            f'\\1"{_escape(og_image)}"',
            cleaned, count=1,
        )
        if 'property="og:image"' not in cleaned.lower():
            cleaned = re.sub(r"(?is)</head>", f'<meta property="og:image" content="{_escape(og_image)}">\n</head>', cleaned, count=1)
    else:
        og_image = _get_og_image_from_prd(prd) or "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1200&h=630&fit=crop"
    if canonical:
        if re.search(r'(?is)<link\s+rel=["\']canonical["\']\s+href=["\'][^"\']*["\']', cleaned):
            cleaned = re.sub(
                r'(?is)(<link\s+rel=["\']canonical["\']\s+href=["\'])([^"\']*)(["\'][^>]*>)',
                lambda m: m.group(1) + _escape(canonical) + m.group(3),
                cleaned,
                count=1,
            )
        else:
            cleaned = re.sub(r"(?is)</head>", f'<link rel="canonical" href="{_escape(canonical)}">\n</head>', cleaned, count=1)
        if re.search(r'(?is)<meta\s+property=["\']og:url["\']\s+content=["\'][^"\']*["\']', cleaned):
            cleaned = re.sub(
                r'(?is)(<meta\s+property=["\']og:url["\']\s+content=["\'])([^"\']*)(["\'][^>]*>)',
                lambda m: m.group(1) + _escape(canonical) + m.group(3),
                cleaned,
                count=1,
            )
        else:
            cleaned = re.sub(r"(?is)</head>", f'<meta property="og:url" content="{_escape(canonical)}">\n</head>', cleaned, count=1)
    if og_image:
        if re.search(r'(?is)<meta\s+property=["\']og:image["\']\s+content=["\'][^"\']*["\']', cleaned):
            cleaned = re.sub(
                r'(?is)(<meta\s+property=["\']og:image["\']\s+content=["\'])([^"\']*)(["\'][^>]*>)',
                lambda m: m.group(1) + _escape(og_image) + m.group(3),
                cleaned,
                count=1,
            )
        if re.search(r'(?is)<meta\s+name=["\']twitter:image["\']\s+content=["\'][^"\']*["\']', cleaned):
            cleaned = re.sub(
                r'(?is)(<meta\s+name=["\']twitter:image["\']\s+content=["\'])([^"\']*)(["\'][^>]*>)',
                lambda m: m.group(1) + _escape(og_image) + m.group(3),
                cleaned,
                count=1,
            )
        else:
            cleaned = re.sub(r"(?is)</head>", f'<meta name="twitter:image" content="{_escape(og_image)}">\n</head>', cleaned, count=1)
    if keywords:
        if re.search(r'(?is)<meta\s+name=["\']keywords["\']\s+content=["\'][^"\']*["\']', cleaned):
            cleaned = re.sub(
                r'(?is)(<meta\s+name=["\']keywords["\']\s+content=["\'])([^"\']*)(["\'][^>]*>)',
                lambda m: m.group(1) + _escape(keywords) + m.group(3),
                cleaned,
                count=1,
            )
        else:
            cleaned = re.sub(r"(?is)</head>", f'<meta name="keywords" content="{_escape(keywords)}">\n</head>', cleaned, count=1)
    # og:type
    if 'property="og:type"' not in low:
        cleaned = re.sub(r"(?is)</head>", '<meta property="og:type" content="website">\n</head>', cleaned, count=1)

    # Footer: ano automático
    current_year = str(datetime.datetime.now().year)
    if re.search(r"202[0-9]", cleaned):
        def _replace_copyright_year(m):
            return '\xa9 ' + current_year
        cleaned = re.sub(r'(?:\xa9|\s)\s*(202[0-9])(?=\D)', _replace_copyright_year, cleaned)
        def _replace_standalone_year(m):
            return ' ' + current_year
        cleaned = re.sub(r'(?:>|\s)(202[0-9])(?=\s|<)', _replace_standalone_year, cleaned)

    # Sitemap XML + Robots.txt
    if site_dir and deploy_url:
        cleaned = _gerar_sitemap_robots(cleaned, prd, site_dir, deploy_url)

    return cleaned


# ─── Wrapper Functions for Backward Compatibility ───────────────────────────


def _publication_canonical_from_prd(prd) -> str:
    """Wrapper for backward compatibility - imports from html_builder_repair."""
    from backend.agents.html_builder_repair import publication_canonical_from_prd as _func
    return _func(prd)


# ─── Audit Helper Functions ──────────────────────────────────────────────────


def _contract_problems(prd) -> list[str]:
    """Validate PRD structure has required sections."""
    sections = _get_sections(prd)
    if not sections:
        return ["PRD sem secoes estruturadas para o Builder Renderer"]
    names = [_get_section_identity(section) for section in sections]
    contentful = [section for section in sections if _has_section_content(section)]
    hero = next(
        (
            section
            for section in sections
            if _get_section_identity(section) in {"hero", "inicio", "home"}
        ),
        None,
    )
    problems: list[str] = []
    if len(sections) < 4:
        problems.append("PRD tem menos de 4 secoes estruturadas")
    if any(not name for name in names):
        problems.append("PRD contem secao sem nome/id")
    if len(contentful) < 3:
        problems.append("PRD tem menos de 3 secoes com copy/conteudo")
    if not hero or not _has_section_content(hero):
        problems.append("PRD hero sem headline/copy")
    return problems


def _get_sections(prd) -> list[dict]:
    """Extract sections from PRD."""
    raw = _get(prd, "sections", "secoes", default=[]) or []
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


def _get_section_identity(section: dict) -> str:
    """Get identity (name/id) from section."""
    for key in ("name", "id", "type", "tipo", "titulo", "title"):
        value = section.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return ""


def _has_section_content(section: dict) -> bool:
    """Check if section has meaningful content."""
    copy = section.get("copy")
    copy = copy if isinstance(copy, dict) else {}
    for key in (
        "h1",
        "h2",
        "headline",
        "subheadline",
        "subtitulo",
        "body",
        "texto",
        "items",
        "cta",
    ):
        if section.get(key) not in (None, "", [], {}):
            return True
        if copy.get(key) not in (None, "", [], {}):
            return True
    return False


def _requires_motion(prd) -> bool:
    animations = _get(prd, "animations", default=[]) or []
    tier = str(_get(prd, "tier", "caio_tier", default="")).upper()
    return bool(animations) or tier == "PREMIUM" or _is_fitness_segment(prd)


def _has_real_motion(html: str) -> bool:
    low = (html or "").lower()
    engine = any(token in low for token in ("gsap.fromto", "intersectionobserver", "scrolltrigger"))
    reveal_points = low.count("data-reveal") >= 6
    scroll_effect = any(token in low for token in ("data-parallax", "parallax-img", "scroll-progress"))
    return engine and reveal_points and scroll_effect


def _visual_experience_problems(html: str, prd) -> list[str]:
    low = (html or "").lower()
    issues: list[str] = []
    if "<footer" not in low:
        issues.append("HTML sem footer final visivel")
    if "<!-- section:footer" not in low:
        issues.append("HTML sem marcador SECTION:footer")
    visible_norm = _normalize(_visible_text(html))
    if (
        "atividades sob consulta" in visible_norm
        or "informacoes de atendimento sob consulta" in visible_norm
        or "fralib service fallback" in _normalize(html)
    ):
        issues.append("HTML contem fallback visual legado de servicos sob consulta")
    photos = _photo_urls(prd)
    if photos and "fralib-photo-narrative" not in low:
        issues.append("HTML com fotos disponiveis sem narrativa visual editorial")
    address = _get(prd, "address", "endereco", default="")
    if address and "fralib-map-section" not in low and "maps.google" not in low and "openstreetmap" not in low:
        issues.append("HTML com endereco real sem secao de mapa/localizacao")
    if _map_embed_count(html) > 1:
        issues.append("HTML contem mapa/localizacao duplicado")
    issues.extend(_hero_experience_problems(html, prd))
    if not _requires_motion(prd):
        return issues
    if low.count("data-reveal") < 4:
        issues.append("HTML tem poucos pontos de reveal/motion para o nivel visual exigido")
    if low.count("gsap.registerplugin") > 1 or low.count("new lenis") > 1:
        issues.append("HTML contem scripts de motion duplicados; renderer deve controlar a animacao")
    if "gsap" not in low and "scrolltrigger" not in low and "intersectionobserver" not in low:
        issues.append("HTML sem engine de motion/reveal reconhecivel")
    if _is_fitness_segment(prd) and "data-parallax" not in low and "parallax-img" not in low:
        issues.append("HTML fitness sem camada visual parallax/imagem dominante")
    issues.extend(_bold_energy_hero_problems(html, prd))
    return issues


def _hero_experience_problems(html: str, prd) -> list[str]:
    """Generic hero guard: first viewport must not regress to a flat institutional block."""
    hero = _hero_html(html)
    low = hero.lower()
    if not hero:
        return ["HTML sem hero auditavel"]
    issues: list[str] = []
    has_media_or_depth = any(
        token in low
        for token in (
            "<img",
            "<video",
            "background-image",
            "linear-gradient",
            "radial-gradient",
            "fralib-hero-depth",
            "builder-experience-hero",
            "fralib-deterministic-hero",
            "fralib-hero-bg",
        )
    ) or ("hero-bg" in low and "background-image" in (html or "").lower())
    if not has_media_or_depth:
        issues.append("Hero sem midia/camada visual dominante")
    if not any(token in low for token in ("data-parallax", "kenburns", "ken-burns", "fralibkenburns")):
        issues.append("Hero sem parallax/Ken Burns auditavel")
    if not re.search(r"(?is)<a\b|<button\b", hero or ""):
        issues.append("Hero sem CTA clicavel")
    if not re.search(r"(?is)<h1\b[^>]*>.*?</h1>", hero or ""):
        issues.append("Hero sem H1 visivel")
    if _requires_motion(prd) and not any(
        token in low for token in ("magnetic-btn", "fralib-proof-chip", "shadow", "hover", "glow")
    ):
        issues.append("Hero sem microinteracao/prova visual")
    return issues


def _is_fitness_segment(prd) -> bool:
    segment = _normalize(_get(prd, "segmento", "segment", "nicho", default=""))
    return any(token in segment for token in ("academia", "fitness", "cross", "treino"))


def _archetype_id(prd) -> str:
    visual_dna = _get(prd, "visual_dna", default={}) or {}
    if hasattr(visual_dna, "model_dump"):
        visual_dna = visual_dna.model_dump()
    if not isinstance(visual_dna, dict):
        return ""
    archetype = visual_dna.get("archetype")
    if isinstance(archetype, dict):
        return str(archetype.get("archetype") or archetype.get("id") or "").upper()
    return str(archetype or visual_dna.get("id") or "").upper()


def _hero_html(html: str) -> str:
    match = re.search(
        r"(?is)<!--\s*SECTION:hero\s*-->(.*?)<!--\s*/SECTION:hero\s*-->",
        html or "",
    )
    if match:
        return match.group(1)
    match = re.search(r"(?is)<section\b[^>]*(?:id|data-section)=['\"]?hero['\"]?[^>]*>.*?</section>", html or "")
    if match:
        return match.group(0)
    match = re.search(r"(?is)<header\b[^>]*(?:id|data-section)=['\"]?hero['\"]?[^>]*>.*?</header>", html or "")
    if match:
        return match.group(0)
    first_section = re.search(r"(?is)<section\b.*?</section>", html or "")
    return first_section.group(0) if first_section else ""


def _bold_energy_hero_problems(html: str, prd) -> list[str]:
    """Keep academy pages from regressing to a generic institutional template."""
    if not (_is_fitness_segment(prd) or _archetype_id(prd) == "BOLD_ENERGY"):
        return []
    low = (html or "").lower()
    hero = _hero_html(html).lower()
    has_bold_polish = "data-bold-energy-polish" in low
    issues: list[str] = []
    if not hero:
        return ["HTML BOLD_ENERGY sem SECTION:hero auditavel"]
    if not any(token in low for token in ("anton", "bebas", "condensed", "display-font", "font-black")):
        issues.append("Hero BOLD_ENERGY sem tipografia display condensada/pesada")
    if not any(token in low for token in ("#ff1f1f", "#ff2a1f", "#f20", "red-", "vermelho", "--accent")):
        issues.append("Hero BOLD_ENERGY sem acento vermelho eletrico dominante")
    if not has_bold_polish and not any(token in hero for token in ("min-h-screen", "100vh", "100svh", "h-screen")):
        issues.append("Hero BOLD_ENERGY nao ocupa o primeiro viewport")
    if not has_bold_polish and not any(token in hero for token in ("#030303", "#050505", "#070707", "#080808", "#0a0a0a", "bg-black", "rgb(0", "rgba(0")):
        issues.append("Hero BOLD_ENERGY sem base preta cinematografica")
    if not any(token in low for token in ("-webkit-text-stroke", "text-stroke", "outline-text", "text-outline")):
        issues.append("Hero BOLD_ENERGY sem texto outline/eco tipografico")
    if not has_bold_polish and not any(token in hero for token in ("linear-gradient", "radial-gradient", "mix-blend", "overlay", "after:", "::after", "shadow-")):
        issues.append("Hero BOLD_ENERGY sem profundidade/overlay dramatico")
    if not any(token in hero for token in ("data-parallax", "parallax-img")):
        issues.append("Hero BOLD_ENERGY sem parallax/camada dominante")
    if not any(token in hero for token in ("4.6", "rating", "avali", "hor", "06h", "22h", "stat")):
        issues.append("Hero BOLD_ENERGY sem slabs de estatistica/prova no fold")
    if any(token in hero for token in ("bg-white", "background:#fff", "background: #fff", "pastel", "beige", "cream")):
        issues.append("Hero BOLD_ENERGY ainda tem vestigio de tema claro/pastel")
    return issues


def _map_embed_count(html: str) -> int:
    low = (html or "").lower()
    iframe_maps = len(
        re.findall(r"(?is)<iframe\b[^>]+(?:maps\.google|google\.com/maps|openstreetmap)[^>]*>", html or "")
    )
    section_maps = len(
        re.findall(r"(?is)<section\b[^>]*\bfralib-map-section\b[^>]*>", html or "")
    )
    bare_maps = 1 if iframe_maps == 0 and ("maps.google" in low or "openstreetmap" in low) else 0
    return max(iframe_maps, section_maps, bare_maps)


# ─── Utility Functions ───────────────────────────────────────────────────────


def _escape(value) -> str:
    return _html.escape(str(value or ""), quote=True)


def _get(obj, *names, default=None):
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


def _normalize(value) -> str:
    text = str(value or "")
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).lower()
    return re.sub(r"\s+", " ", text).strip()


def _visible_text(html: str) -> str:
    clean = re.sub(r"(?is)<script\b.*?</script>", " ", html or "")
    clean = re.sub(r"(?is)<style\b.*?</style>", " ", clean)
    clean = re.sub(r"(?is)<!--.*?-->", " ", clean)
    clean = re.sub(r"(?is)<[^>]+>", " ", clean)
    return _html.unescape(re.sub(r"\s+", " ", clean)).strip()


def _metadata_text(html: str) -> str:
    parts: list[str] = []
    for match in re.findall(r"(?is)<title\b[^>]*>(.*?)</title>", html or ""):
        parts.append(_visible_text(match))
    for match in re.findall(r"""(?is)<meta\b[^>]*\bcontent=(["'])(.*?)\1[^>]*>""", html or ""):
        parts.append(_html.unescape(match[1]))
    return " ".join(parts)
