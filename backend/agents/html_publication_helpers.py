"""Publication helpers for HTML quality gate.

Provides utility functions for:
- Text rewriting (claims, service terms, placeholders)
- Media section management
- Location/map handling
- Sitemap/robots generation
- Business data extraction
"""

from __future__ import annotations

import datetime
import html as _html
import os
import re
import unicodedata
from urllib.parse import quote_plus

from backend.agents.html_media_validator import (
    image_fallback_for_segment,
    media_urls_from_html,
    minimum_required_media,
    photo_urls,
    safe_photo_url,
)


# ─── Text Rewrite Replacements ──────────────────────────────────────────────


_UNCONFIRMED_SERVICE_TERM_REPLACEMENTS = (
    (re.compile(r"\bmuay\s+thai\b", re.I), "atividade sob consulta"),
    (re.compile(r"\bmusculacao\b", re.I), "atividade sob consulta"),
    (re.compile(r"\bmusculação\b", re.I), "atividade sob consulta"),
    (re.compile(r"\bdancas?\b", re.I), "confirmação pelo contato"),
    (re.compile(r"\bdanças?\b", re.I), "confirmação pelo contato"),
    (re.compile(r"\binfraestrutura t[eé]cnica de ponta\b", re.I), "endereço e contato verificados"),
    (re.compile(r"\binfraestrutura de ponta\b", re.I), "endereço e contato verificados"),
    (re.compile(r"\balto desempenho\b", re.I), "atendimento local"),
    (re.compile(r"\btransforma[cç][aã]o f[ií]sica\b", re.I), "rotina de atividades"),
    (re.compile(r"\bambiente completo\b", re.I), "informações sob consulta"),
    (re.compile(r"\bestrutura completa\b", re.I), "endereço e contato verificados"),
    (re.compile(r"\bprofessores dedicados\b", re.I), "atendimento no local"),
    (re.compile(r"\bprofessores qualificados\b", re.I), "atendimento no local"),
    (re.compile(r"\binstrutores dedicados\b", re.I), "atendimento no local"),
    (re.compile(r"\binstrutores qualificados\b", re.I), "atendimento no local"),
    (re.compile(r"\bprofissionais dedicados\b", re.I), "atendimento no local"),
    (re.compile(r"\bequipe especializada\b", re.I), "contato oficial"),
    (re.compile(r"\bequipe qualificada\b", re.I), "contato oficial"),
    (re.compile(r"\bequipe dedicada\b", re.I), "contato oficial"),
)


_OPERATIONAL_ATTRIBUTE_REPLACEMENTS = (
    (re.compile(r"\baulas online\b", re.I), "confirmação pelo contato"),
    (re.compile(r"\bservi[cç]os no local\b", re.I), "atendimento no endereço informado"),
    (re.compile(r"\bbanheiro\b", re.I), "estrutura sob consulta"),
    (re.compile(r"\bpagamentos diversos\b", re.I), "formas de pagamento sob consulta"),
    (re.compile(r"\bpagamentos\b", re.I), "formas de pagamento sob consulta"),
)


_PUBLIC_CLAIM_REPLACEMENTS = (
    (re.compile(r"\bmelhor(?:ar|es)?\b", re.I), "local"),
    (re.compile(r"\bmais\s+premiada\b", re.I), "avaliada"),
    (re.compile(r"\bn[uú]mero\s+1\b", re.I), "opção local"),
    (re.compile(r"\bpremium\b", re.I), "cuidadosa"),
    (re.compile(r"\bexclusiv[ao]s?\b", re.I), "sob consulta"),
    (re.compile(r"\brefer[êe]ncias?\b", re.I), "presença local"),
    (re.compile(r"\bl[ií]der\b", re.I), "opção local"),
    (re.compile(r"\bmoderna\b", re.I), "atual"),
    (re.compile(r"\btop\b", re.I), "marcante"),
    (re.compile(r"\belite\b", re.I), "selecionada"),
    (re.compile(r"\bVIP\b", re.I), "prioritária"),
)


# Aliases without underscore for backward compatibility
UNCONFIRMED_SERVICE_TERM_REPLACEMENTS = _UNCONFIRMED_SERVICE_TERM_REPLACEMENTS
OPERATIONAL_ATTRIBUTE_REPLACEMENTS = _OPERATIONAL_ATTRIBUTE_REPLACEMENTS
PUBLIC_CLAIM_REPLACEMENTS = _PUBLIC_CLAIM_REPLACEMENTS


_TEXT_REWRITE_PROTECTED_RE = re.compile(
    r"(?is)(<style\b.*?</style>|<script\b.*?</script>|<[^>]+>)"
)


# ─── Text Rewrite Functions ──────────────────────────────────────────────────


def replace_visible_text_only(html: str, replacements) -> str:
    """Rewrite visitor-visible text without touching CSS, tags, attrs or URLs."""
    parts = _TEXT_REWRITE_PROTECTED_RE.split(html or "")
    rewritten: list[str] = []
    for part in parts:
        if not part:
            continue
        if part.startswith("<"):
            rewritten.append(part)
            continue
        text = part
        for pattern, replacement in replacements:
            text = pattern.sub(replacement, text)
        rewritten.append(text)
    return "".join(rewritten)


def replace_attribute_text(html: str, replacements) -> str:
    def repl(match):
        prefix, quote, value = match.group(1), match.group(2), match.group(3)
        updated = value
        for pattern, replacement in replacements:
            updated = pattern.sub(replacement, updated)
        return f"{prefix}{quote}{updated}{quote}"

    return re.sub(
        r"""(?is)(\b(?:content|alt|title|aria-label)\s*=\s*)(["'])(.*?)\2""",
        repl,
        html or "",
    )


def repair_legacy_css_rewrites(html: str) -> str:
    """Undo old whole-HTML rewrites that corrupted CSS property names."""
    return (
        (html or "")
        .replace("margin-direta", "margin-top")
        .replace("border-direta", "border-top")
    )


def remove_placeholder_markers(html: str) -> str:
    cleaned = re.sub(r"\bplaceholder\b", "editorial", html or "", flags=re.I)
    cleaned = re.sub(r"\bph-img\b", "media-frame", cleaned, flags=re.I)
    return cleaned


# ─── Email Handling ──────────────────────────────────────────────────────────


_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def extract_emails(text: str) -> list[str]:
    return _EMAIL_RE.findall(text or "")


def remove_unknown_emails(html: str, prd) -> str:
    allowed = set(extract_emails(_get(prd, "email", "emails", default="")))
    cleaned = html or ""
    for email in sorted(set(extract_emails(_visible_text(cleaned)) + extract_emails(cleaned))):
        if email in allowed:
            continue
        cleaned = re.sub(rf"mailto:{re.escape(email)}", "#contato", cleaned, flags=re.I)
        cleaned = re.sub(re.escape(email), "contato oficial", cleaned, flags=re.I)
    return cleaned


# ─── Image Handling ──────────────────────────────────────────────────────────


def add_image_error_fallbacks(html: str, prd) -> str:
    fallback = image_fallback_for_segment(prd)

    def repl(match: re.Match) -> str:
        tag = match.group(0)
        if " onerror=" in tag.lower():
            return tag
        return tag[:-1] + f' onerror="this.onerror=null;this.src=\'{fallback}\'">'

    return re.sub(r"(?is)<img\b[^>]*>", repl, html or "")


# ─── Media Section Management ───────────────────────────────────────────────


def ensure_required_media_section(html: str, prd) -> str:
    photos = [safe_photo_url(url, prd) for url in photo_urls(prd)]
    photos = [url for i, url in enumerate(photos) if url and url not in photos[:i]]
    required = minimum_required_media(prd, photos)
    if not photos:
        return html
    has_narrative = "fralib-photo-narrative" in (html or "").lower()
    if len(media_urls_from_html(html)) >= required and has_narrative:
        return html
    name = _get(prd, "business_name", "nome_negocio", default="Negocio local")
    segment = _get(prd, "segmento", "segment", "nicho", default="negocio local")
    city = _get(prd, "city", "cidade", default="")
    title = _media_title_for_segment(segment)
    body = _media_body_for_segment(segment, city)
    cards = []
    for idx, url in enumerate((photos + [image_fallback_for_segment(prd)] * required)[:required], 1):
        cards.append(
            '<figure class="fralib-photo-frame">'
            f'<img src="{escape(url)}" alt="{escape(name)}: imagem editorial {idx} relacionada a {escape(segment)}" '
            'loading="lazy" decoding="async">'
            '</figure>'
        )
    section = (
        '\n<!-- SECTION:media -->\n'
        '<section class="fralib-photo-narrative" data-reveal>'
        '<div class="fralib-photo-copy"><p class="eyebrow">Direção visual</p>'
        f'<h2>{escape(title)}</h2>'
        f'<p>{escape(body)}</p></div>'
        '<div class="fralib-photo-grid">'
        + "".join(cards)
        + '</div></section>\n'
        '<!-- /SECTION:media -->\n'
    )
    return _insert_before_footer(html, section)


def dedupe_media_narratives(html: str) -> str:
    """Keep one editorial media narrative; repeated galleries flatten the page."""
    pattern = re.compile(
        r"(?is)\n?\s*(?:<!--\s*SECTION:media\s*-->\s*)?"
        r"<section\b[^>]*\bfralib-photo-narrative\b[^>]*>.*?</section>\s*"
        r"(?:<!--\s*/SECTION:media\s*-->\s*)?"
    )
    matches = list(pattern.finditer(html or ""))
    if len(matches) <= 1:
        return html or ""
    keep_start = max(
        matches,
        key=lambda match: (len(media_urls_from_html(match.group(0))), len(match.group(0))),
    ).start()

    return pattern.sub(lambda match: match.group(0) if match.start() == keep_start else "", html or "")


def normalize_media_strip_order(html: str) -> str:
    """Remove or move the old minimum-media strip so images never appear after footer."""
    cleaned = html or ""
    strip_pattern = re.compile(
        r"(?is)\n?\s*(?:<!--\s*SECTION:galeria\s*-->\s*)?"
        r"<section\b[^>]*\bfralib-media-strip\b[^>]*>.*?</section>\s*"
        r"(?:<!--\s*/SECTION:galeria\s*-->\s*)?"
    )
    strips = list(strip_pattern.finditer(cleaned))
    if not strips:
        return cleaned
    if "fralib-photo-narrative" in cleaned.lower():
        return strip_pattern.sub("", cleaned)
    first_strip = strips[0].group(0)
    cleaned = strip_pattern.sub("", cleaned)
    return _insert_before_footer(cleaned, first_strip)


def _media_title_for_segment(segment: str) -> str:
    normalized = _normalize(segment)
    if any(token in normalized for token in ("otica", "optica", "oculos")):
        return "Detalhes que ajudam na escolha"
    if any(token in normalized for token in ("dentista", "odontologia")):
        return "Confiança começa no cuidado"
    if any(token in normalized for token in ("nutricionista", "nutricao")):
        return "Texturas calmas para decidir melhor"
    if any(token in normalized for token in ("academia", "fitness", "treino")):
        return "O ritmo visual acompanha o treino"
    if any(token in normalized for token in ("restaurante", "pizzaria", "cafe")):
        return "Presença de mesa e atmosfera"
    return f"Imagens conectadas a {segment or 'negócio local'}"


def _media_body_for_segment(segment: str, city: str) -> str:
    normalized = _normalize(segment)
    local = city or "sua região"
    if any(token in normalized for token in ("otica", "optica", "oculos")):
        return f"Produto, lente, armação e precisão visual organizam a percepção da ótica em {local}."
    if any(token in normalized for token in ("dentista", "odontologia")):
        return "Apoio visual focado em limpeza, acolhimento e confiança clínica, sem inventar procedimentos."
    if any(token in normalized for token in ("nutricionista", "nutricao")):
        return "Alimentos, rotina e leveza visual ajudam a explicar a decisão de cuidado."
    if any(token in normalized for token in ("academia", "fitness", "treino")):
        return "Intensidade, movimento e contraste sustentam uma leitura mais forte da oferta."
    if any(token in normalized for token in ("restaurante", "pizzaria", "cafe")):
        return "Textura, mesa e ambiente ajudam a construir apetite e intenção de visita."
    return "Imagens de apoio reforçam o contexto do negócio sem afirmar que são fotos reais do endereço."


# ─── Service Fallback Removal ────────────────────────────────────────────────


def remove_unrequested_service_fallbacks(html: str, prd) -> str:
    """Remove legacy visual fallback sections that flatten the page rhythm."""
    fallback_terms = (
        "atividades sob consulta",
        "informacoes de atendimento sob consulta",
        "modalidades devem ser confirmadas",
        "servicos modalidades e disponibilidade",
    )

    def is_fallback_block(block: str) -> bool:
        text = _normalize(_visible_text(block))
        return any(term in text for term in fallback_terms) or "fralib service fallback" in _normalize(block)

    cleaned = html or ""
    section_patterns = (
        r"(?is)\n?\s*<!--\s*SECTION:([a-z0-9_-]+)\s*-->.*?<!--\s*/SECTION:\1\s*-->\s*",
        r"(?is)\n?\s*<!--\s*SECTION:servicos\s*-->.*?<!--\s*/SECTION:servicos\s*-->\s*",
        r"(?is)\n?\s*<section\b[^>]*(?:fralib-service-fallback|id=['\"]?servicos['\"]?)[^>]*>.*?</section>\s*",
        r"(?is)\n?\s*<section\b[^>]*>.*?atividades\s+sob\s+consulta.*?</section>\s*",
    )
    for pattern in section_patterns:
        cleaned = re.sub(pattern, lambda m: "" if is_fallback_block(m.group(0)) else m.group(0), cleaned)
    cleaned = replace_visible_text_only(
        cleaned,
        (
            (
                re.compile(r"atividades\s+sob\s+consulta", re.I),
                "Confirme o atendimento pelo contato",
            ),
            (
                re.compile(r"informa[cç][oõ]es\s+de\s+atendimento\s+sob\s+consulta", re.I),
                "Confirme o atendimento pelo contato",
            ),
        ),
    )
    cleaned = cleaned.replace("fralib-service-fallback", "fralib-info-note")
    return cleaned


def remove_unsafe_review_sections(html: str, prd) -> str:
    """Drop reviews/testimonials that leak unconfirmed operations as public claims."""
    services = _get(prd, "servicos", "services", default=[]) or []
    if services:
        return html
    risky_terms = (
        "muay thai",
        "danca",
        "dancas",
        "danca",
        "musculacao",
        "professor",
        "professores",
        "instrutor",
        "instrutores",
        "equipamento",
        "equipamentos",
        "aparelho",
        "aparelhos",
    )

    def unsafe(block: str) -> bool:
        text = _normalize(_visible_text(block))
        return any(term in text for term in risky_terms)

    patterns = (
        r"(?is)\n?\s*<!--\s*SECTION:(?:depoimentos|reviews|prova_social|social_proof)\s*-->.*?<!--\s*/SECTION:(?:depoimentos|reviews|prova_social|social_proof)\s*-->\s*",
        r"(?is)\n?\s*<section\b[^>]*(?:depoimento|testimonial|review|social-proof|prova-social)[^>]*>.*?</section>\s*",
    )
    cleaned = html or ""
    for pattern in patterns:
        cleaned = re.sub(pattern, lambda m: "" if unsafe(m.group(0)) else m.group(0), cleaned)
    return cleaned


# ─── Location/Map Handling ───────────────────────────────────────────────────


def ensure_single_location_map(html: str, prd) -> str:
    address = str(_get(prd, "address", "endereco", default="") or "").strip()
    city = str(_get(prd, "city", "cidade", default="") or "").strip()
    if not address and not city:
        return html
    canonical = _canonical_location_map_section(prd)
    cleaned = html or ""
    cleaned = re.sub(
        r"(?is)\n?\s*<!--\s*SECTION:localizacao\s*-->.*?<!--\s*/SECTION:localizacao\s*-->\s*",
        "",
        cleaned,
    )
    cleaned = _remove_all_map_blocks(cleaned)
    cleaned = re.sub(
        r"(?is)<iframe\b[^>]+(?:maps\.google|google\.com/maps|openstreetmap)[^>]*>.*?</iframe>\s*",
        "",
        cleaned,
    )
    return _insert_before_footer(cleaned, canonical)


def _canonical_location_map_section(prd) -> str:
    name = _get(prd, "business_name", "nome_negocio", default="Negocio local")
    address = str(_get(prd, "address", "endereco", default="") or "").strip()
    city = str(_get(prd, "city", "cidade", default="") or "").strip()
    raw_query = _maps_query(prd, name, address, city)
    query = quote_plus(raw_query)
    maps_link = "https://www.google.com/maps/search/" + query
    embed = (
        '<iframe title="Mapa do endereço" width="100%" height="420" style="border:0;" '
        'loading="lazy" allowfullscreen referrerpolicy="no-referrer-when-downgrade" '
        f'src="https://maps.google.com/maps?q={query}&output=embed&z=18"></iframe>'
    )
    location = address or city
    return (
        '\n<!-- SECTION:localizacao -->\n'
        '<section id="localizacao" class="fralib-map-section" data-reveal>\n'
        '  <div class="fralib-map-copy">\n'
        '    <p>Endereço confirmado</p>\n'
        f'    <h2>Encontre {escape(name)}</h2>\n'
        f'    <address>{escape(location)}</address>\n'
        f'    <a href="{escape(maps_link)}" target="_blank" rel="noopener">Abrir no Google Maps</a>\n'
        '  </div>\n'
        '  <div class="fralib-map-frame" data-reveal>\n'
        f'    {embed}\n'
        '  </div>\n'
        '</section>\n'
        '<!-- /SECTION:localizacao -->\n'
    )


def _maps_query(prd, name: str, address: str, city: str) -> str:
    geo = _get(prd, "geo", default={}) or {}
    if isinstance(geo, dict):
        lat = geo.get("lat") or geo.get("latitude")
        lng = geo.get("lng") or geo.get("longitude") or geo.get("lon")
        if lat not in (None, "") and lng not in (None, ""):
            return f"{lat},{lng}"
    lat = _get(prd, "lat", "latitude", default=None)
    lng = _get(prd, "lng", "longitude", "lon", default=None)
    if lat not in (None, "") and lng not in (None, ""):
        return f"{lat},{lng}"
    return " ".join(str(v) for v in (name, address, city) if v)


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


def _remove_all_map_blocks(html: str) -> str:
    def repl(match: re.Match) -> str:
        block = match.group(0)
        if _map_embed_count(block) == 0:
            return block
        return ""

    return re.sub(r"(?is)<section\b[^>]*>.*?</section>", repl, html or "")


# ─── Footer Management ────────────────────────────────────────────────────────


def ensure_minimum_footer(html: str, prd) -> str:
    low = (html or "").lower()
    if "<footer" in low and "<!-- section:footer" in low:
        return html
    if "<footer" in low:
        return re.sub(
            r"(?is)(<footer\b.*?</footer>)",
            r"<!-- SECTION:footer -->\n\1\n<!-- /SECTION:footer -->",
            html or "",
            count=1,
        )
    name = _get(prd, "business_name", "nome_negocio", default="Negocio local")
    phone = _get(prd, "phone", "telefone", default="")
    city = _get(prd, "city", "cidade", default="")
    address = _get(prd, "address", "endereco", default="")
    whatsapp = _get(prd, "whatsapp", "telefone_whatsapp", default=phone)
    whatsapp_digits = re.sub(r"\D+", "", str(whatsapp or ""))
    whatsapp_href = f"https://wa.me/{whatsapp_digits}" if whatsapp_digits else "#contato"
    footer = (
        '\n<!-- SECTION:footer -->\n'
        '<footer class="fralib-footer" data-reveal '
        'style="padding:32px 20px;border-top:1px solid var(--border,rgba(255,255,255,.12));'
        'background:var(--bg,#0b0f19);color:var(--fg,#f3f4f6)">'
        '<div style="max-width:1200px;margin:0 auto;display:grid;gap:20px;'
        'grid-template-columns:repeat(auto-fit,minmax(220px,1fr));align-items:start">'
        '<div>'
        f'<strong style="display:block;font-size:1.1rem;margin-bottom:8px">{escape(name)}</strong>'
        f'<p style="opacity:.86;line-height:1.6">{escape(city)}</p>'
        f'<p style="opacity:.86;line-height:1.6">{escape(address)}</p>'
        '</div>'
        '<div>'
        '<strong style="display:block;margin-bottom:8px">Contato</strong>'
        f'<p style="opacity:.86;line-height:1.6">{escape(phone)}</p>'
        f'<a href="{whatsapp_href}" '
        'style="display:inline-flex;align-items:center;justify-content:center;margin-top:8px;'
        'padding:10px 14px;border-radius:999px;background:var(--accent,#e85d4a);'
        'color:var(--bg,#0b0f19);font-weight:700">Falar no WhatsApp</a>'
        '</div>'
        '<div>'
        '<strong style="display:block;margin-bottom:8px">Privacidade</strong>'
        '<p style="opacity:.86;line-height:1.6">Dados de contato usados apenas para atendimento, '
        'segurança e continuidade da experiência.</p>'
        '<a href="#footer-privacy-notice" style="display:inline-flex;align-items:center;justify-content:center;'
        'margin-top:8px;padding:10px 14px;border-radius:999px;border:1px solid var(--border,rgba(255,255,255,.14));'
        'color:var(--fg,#f3f4f6);font-weight:700">Ver política e consentimento</a>'
        '<p id="footer-privacy-notice" style="margin-top:10px;opacity:.78;line-height:1.6">'
        'Ao continuar, você consente com o uso dos seus dados apenas para atendimento e retorno comercial.'
        '</p>'
        '</div>'
        '</div>'
        '</footer>\n'
        '<!-- /SECTION:footer -->\n'
    )
    return _insert_before_body_end(html, footer)


def keep_client_navigation_in_page(html: str) -> str:
    """Client sites must never send logo/home clicks to the FraLib root."""
    cleaned = re.sub(
        r"""(?is)(<a\b[^>]*\bhref\s*=\s*)(["'])(?:/|/index\.html)\2""",
        r"\1\2#hero\2",
        html or "",
    )
    cleaned = re.sub(
        r"""(?is)(<a\b[^>]*\bhref\s*=\s*)(?:/|/index\.html)(?=[\s>])""",
        r"\1#hero",
        cleaned,
    )
    return cleaned


# ─── Sitemap/Robots Generation ──────────────────────────────────────────────


def gerar_sitemap_robots(html: str, prd, site_dir: str, deploy_url: str) -> str:
    """Gera e salva sitemap.xml e robots.txt no diretório do site."""
    from backend.agents.html_phase6_repair import publication_canonical_from_prd
    try:
        os.makedirs(site_dir, exist_ok=True)
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        canonical = publication_canonical_from_prd(prd) or deploy_url
        # sitemap.xml
        sitemap = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            '  <url>\n'
            f'    <loc>{canonical or deploy_url}</loc>\n'
            f'    <lastmod>{today}</lastmod>\n'
            '    <changefreq>weekly</changefreq>\n'
            '    <priority>1.0</priority>\n'
            '  </url>\n'
            '</urlset>'
        )
        with open(os.path.join(site_dir, "sitemap.xml"), "w", encoding="utf-8") as f:
            f.write(sitemap)
        # robots.txt
        sitemap_url = (canonical or deploy_url).rstrip('/') + '/sitemap.xml'
        robots = f"User-agent: *\nAllow: /\n\nSitemap: {sitemap_url}\n"
        with open(os.path.join(site_dir, "robots.txt"), "w", encoding="utf-8") as f:
            f.write(robots)
        print(f"[HQG] Sitemap + Robots salvos em {site_dir}")
    except Exception as e:
        print(f"[HQG] Erro ao gerar sitemap/robots: {e}")
    return html


# ─── Business Data Extraction ────────────────────────────────────────────────


def get_business_from_prd(prd) -> dict[str, str]:
    """Extrai dados do negocio do PRD (compativel com varios formatos)."""
    if isinstance(prd, dict):
        for key in ("business", "publication", "seo", "site"):
            val = prd.get(key)
            if isinstance(val, dict) and val.get("name"):
                return val
        if prd.get("name"):
            return prd
    # Suporte para Pydantic models e objetos com atributos
    if hasattr(prd, "model_dump"):
        prd_dict = prd.model_dump()
    elif hasattr(prd, "dict"):
        prd_dict = prd.dict()
    else:
        prd_dict = {}
    for key in ("business", "publication", "seo", "site"):
        val = prd_dict.get(key)
        if isinstance(val, dict) and val.get("name"):
            return val
    name = prd_dict.get("business_name") or prd_dict.get("name") or getattr(prd, "business_name", None) or getattr(prd, "name", None) or ""
    cidade = prd_dict.get("cidade") or prd_dict.get("city") or getattr(prd, "cidade", None) or getattr(prd, "city", None) or ""
    estado = prd_dict.get("estado") or getattr(prd, "estado", None) or ""
    segmento = prd_dict.get("segmento") or getattr(prd, "segmento", None) or ""
    if name:
        return {"name": name, "city": cidade, "state": estado, "segment": segmento}
    return {}


def get_og_image_from_prd(prd) -> str:
    """Tenta extrair URL da imagem OG do PRD."""
    # Vários lugares onde a imagem pode estar
    paths = [
        ("og_image",),
        ("business", "og_image"),
        ("publication", "og_image"),
        ("visual_contract", "og_image"),
        ("visual_direction", "og_image"),
        ("media", "hero", "url"),
        ("images", 0, "url"),
        ("assets", 0, "url"),
    ]
    val = None
    for path in paths:
        cur = prd
        found = True
        for key in path:
            if isinstance(cur, dict):
                cur = cur.get(key)
            elif isinstance(cur, list) and isinstance(key, int):
                if key < len(cur):
                    cur = cur[key]
                else:
                    found = False
                    break
            else:
                found = False
                break
        if found and cur and isinstance(cur, str) and cur.startswith("http"):
            val = cur
            break
    if val:
        return val

    for collection_name in ("media_plan", "photos", "images", "assets"):
        items = _get(prd, collection_name, default=[]) or []
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, str) and item.startswith("http"):
                return item
            if not isinstance(item, dict):
                continue
            url = item.get("url") or item.get("src")
            role = _normalize(item.get("role") or "")
            required = item.get("required")
            if isinstance(url, str) and url.startswith("http") and (required or role in {"hero", "og", "cover", "background"}):
                return url
        for item in items:
            if isinstance(item, dict):
                url = item.get("url") or item.get("src")
                if isinstance(url, str) and url.startswith("http"):
                    return url

    return image_fallback_for_segment(prd)


# ─── Utility Functions ──────────────────────────────────────────────────────


def escape(value) -> str:
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


def _insert_before_footer(html: str, snippet: str) -> str:
    match = re.search(r"(?is)<!--\s*SECTION:footer\s*-->|<footer\b", html or "")
    if match:
        return html[: match.start()] + snippet + html[match.start() :]
    return _insert_before_body_end(html, snippet)


def _insert_before_body_end(html: str, snippet: str) -> str:
    match = re.search(r"(?is)</body\s*>", html or "")
    if match:
        return html[: match.start()] + snippet + html[match.start() :]
    return (html or "") + snippet
