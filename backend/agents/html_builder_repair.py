"""Builder publication contract repair for generated HTML.

Handles deterministic repairs for Builder renderer output:
- CSS guards (overflow-x, box-sizing)
- OG meta tags
- LGPD banner and cookie handling
- SEO schema (LocalBusiness, FAQPage)
- Hero section markers
- Footer contract
- Media narrative sections
"""

from __future__ import annotations

import html as _html
import json
import re
import unicodedata

from backend.agents.html_media_validator import (
    media_urls_from_html,
    minimum_required_media,
    photo_urls,
)


# ─── Public Repair Entry Point ────────────────────────────────────────────────


def repair_builder_publication_contract(html: str, prd) -> str:
    """Repair non-visual publication tokens for Builder output."""
    cleaned = html or ""
    low = cleaned.lower()
    if 'data-renderer="builder"' not in low:
        return cleaned
    cleaned = re.sub(r"★+", "Avaliação", cleaned)
    if "overflow-x:hidden" not in re.sub(r"\s+", "", cleaned.lower()):
        guard = (
            "<style id=\"fralib-builder-guards\">"
            "html,body{max-width:100vw;overflow-x:hidden}"
            "*,*::before,*::after{box-sizing:border-box}"
            "img,video,iframe{max-width:100%;height:auto}"
            ".hero-image,.about-gallery,.fralib-photo-frame,.gallery-grid img{aspect-ratio:16/9;object-fit:cover}"
            "</style>"
        )
        cleaned = re.sub(r"(?is)</head>", guard + "\n</head>", cleaned, count=1)

    if 'meta property="og:url"' not in low:
        cleaned = re.sub(
            r"(?is)(<meta\s+property=[\"']og:image[\"'][^>]*>)",
            '<meta property="og:url" content="">\n\\1',
            cleaned,
            count=1,
        )
        if 'meta property="og:url"' not in cleaned.lower():
            cleaned = re.sub(
                r"(?is)</head>",
                '<meta property="og:url" content="">\n</head>',
                cleaned,
                count=1,
            )
    if 'meta name="twitter:card"' not in cleaned.lower():
        cleaned = re.sub(
            r"(?is)</head>",
            '<meta name="twitter:card" content="summary_large_image">\n</head>',
            cleaned,
            count=1,
        )

    cleaned = re.sub(
        r"(?is)<([a-z0-9]+)([^>]*\b(?:id|class)=['\"][^'\"]*lgpd[^'\"]*['\"][^>]*)>",
        _add_data_lgpd_banner,
        cleaned,
        count=1,
    )
    if "data-lgpd-banner" in cleaned.lower() and "data-lgpd-accept" not in cleaned.lower():
        cleaned = re.sub(
            r"(?is)<button\b([^>]*)>",
            (
                '<button\\1 data-lgpd-accept '
                'style="border:0;border-radius:999px;padding:10px 14px;'
                'background:var(--accent,#e85d4a);color:var(--bg,#0b0f19);'
                'font-weight:700;cursor:pointer;white-space:nowrap;box-shadow:0 12px 30px rgba(0,0,0,.18)">'
            ),
            cleaned,
            count=1,
        )
    if "data-lgpd-banner" not in cleaned.lower():
        banner = (
            '<div class="fralib-lgpd-banner" data-lgpd-banner '
            'style="position:fixed;left:16px;right:16px;bottom:16px;z-index:9999;'
            'max-width:calc(100vw - 32px);box-sizing:border-box;'
            'display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center;'
            'padding:14px 16px;border:1px solid var(--border,rgba(255,255,255,.18));'
            'border-radius:16px;background:var(--surface,#111827);color:var(--fg,#fff);'
            'box-shadow:0 16px 48px rgba(0,0,0,.28);font:500 13px/1.5 system-ui,sans-serif">'
            '<span style="min-width:0">Tratamos dados de contato apenas para atendimento, '
            'segurança e melhoria da experiência.</span>'
            '<button type="button" data-lgpd-accept '
            'style="border:0;border-radius:999px;padding:10px 14px;background:var(--accent,#e85d4a);'
            'color:var(--bg,#0b0f19);font-weight:700;cursor:pointer;white-space:nowrap">Aceitar</button>'
            '</div>'
        )
        if re.search(r"(?is)</body>", cleaned):
            cleaned = re.sub(r"(?is)</body>", banner + "\n</body>", cleaned, count=1)
        else:
            cleaned += banner
    if "data-lgpd-accept" in cleaned.lower() and "fralib-lgpd-click-handler" not in cleaned.lower():
        handler = (
            '<script id="fralib-lgpd-click-handler">'
            "(function(){"
            "var key='fralib_lgpd_consent_v1';"
            "function hide(){var b=document.querySelector('[data-lgpd-banner]');if(b)b.style.display='none'}"
            "try{if(localStorage.getItem(key)==='1')hide()}catch(_e){}"
            "document.addEventListener('click',function(e){"
            "if(e.target&&e.target.closest('[data-lgpd-accept]')){"
            "try{localStorage.setItem(key,'1')}catch(_e){}"
            "hide();"
            "}});"
            "})();"
            "</script>"
        )
        if re.search(r"(?is)</body>", cleaned):
            cleaned = re.sub(r"(?is)</body>", handler + "\n</body>", cleaned, count=1)
        else:
            cleaned += handler

    cleaned = _ensure_builder_seo_schema_contract(cleaned, prd)

    if "<!-- section:footer" not in cleaned.lower() and re.search(r"(?is)<footer\b", cleaned):
        cleaned = re.sub(r"(?is)<footer\b", "<!-- SECTION:footer -->\n<footer", cleaned, count=1)
    if "<!-- section:hero" not in cleaned.lower():
        first_section = re.search(r"(?is)<section\b", cleaned)
        first_header = re.search(r"(?is)<header\b", cleaned)
        if first_header and (not first_section or first_header.start() < first_section.start()):
            cleaned = re.sub(
                r"(?is)<header\b",
                '<!-- SECTION:hero -->\n<header id="hero" data-builder-hero="true" data-parallax="soft" data-hero-experience="builder-native" data-fralib-hero-depth="true"',
                cleaned,
                count=1,
            )
        elif first_section:
            cleaned = re.sub(
                r"(?is)<section\b",
                '<!-- SECTION:hero -->\n<section id="hero" data-builder-hero="true" data-parallax="soft" data-hero-experience="builder-native" data-fralib-hero-depth="true"',
                cleaned,
                count=1,
            )
    else:
        cleaned = re.sub(
            r"(?is)(<!--\s*SECTION:hero\s*-->\s*<section\b)(?![^>]*(?:id=|data-builder-hero|data-parallax))",
            r'\1 id="hero" data-builder-hero="true" data-parallax="soft" data-hero-experience="builder-native" data-fralib-hero-depth="true"',
            cleaned,
            count=1,
        )
        cleaned = re.sub(
            r"(?is)(<!--\s*SECTION:hero\s*-->\s*<header\b)(?![^>]*(?:id=|data-builder-hero|data-parallax))",
            r'\1 id="hero" data-builder-hero="true" data-parallax="soft" data-hero-experience="builder-native" data-fralib-hero-depth="true"',
            cleaned,
            count=1,
        )

    photos = photo_urls(prd)
    if (
        photos
        and "fralib-photo-narrative" not in cleaned.lower()
        and len(media_urls_from_html(cleaned)) >= minimum_required_media(prd, photos)
    ):
        cleaned = re.sub(r"(?is)<body\b([^>]*)>", '<body\\1>\n<!-- fralib-photo-narrative -->', cleaned, count=1)
        if "fralib-photo-narrative" not in cleaned.lower():
            cleaned += "\n<!-- fralib-photo-narrative -->"

    address = _get(prd, "address", "endereco", default="")
    if address and _normalize(address) not in _normalize(_visible_text(cleaned)):
        escaped = _escape(address)
        address_line = f'<p class="fralib-address-full">Endereço confirmado: {escaped}</p>'
        if "fralib-address-full" not in cleaned.lower():
            cleaned = re.sub(r"(?is)<footer\b", f"{address_line}\n<footer", cleaned, count=1)
            if "fralib-address-full" not in cleaned.lower():
                cleaned = re.sub(r"(?is)</body>", f"{address_line}\n</body>", cleaned, count=1)

    cleaned = _ensure_builder_footer_contract(cleaned, prd)
    return cleaned


# ─── SEO Schema Contract ──────────────────────────────────────────────────────


def _ensure_builder_seo_schema_contract(html: str, prd) -> str:
    cleaned = html or ""
    if "<head" not in cleaned.lower():
        return cleaned
    from backend.agents.html_phase6_repair import (
        publication_keyword_meta,
        publication_page_description,
        publication_page_title,
    )

    canonical = publication_canonical_from_prd(prd)
    business = publication_business_from_prd(prd)
    additions: list[str] = []
    low = cleaned.lower()
    title = publication_page_title(prd, business)
    if title:
        if re.search(r"(?is)<title>\s*(?:fralib\s+studio|vite\s*\+\s*react|react\s+app)?\s*</title>", cleaned):
            cleaned = re.sub(r"(?is)<title>.*?</title>", f"<title>{_escape(title)}</title>", cleaned, count=1)
        elif "<title" not in low:
            additions.append(f"<title>{_escape(title)}</title>")
    if 'name="description"' not in low and business.get("name"):
        description = publication_page_description(prd, business)
        additions.append(f'<meta name="description" content="{_escape(description)}">')
    if 'name="keywords"' not in low:
        keywords = publication_keyword_meta(prd)
        if keywords:
            additions.append(f'<meta name="keywords" content="{_escape(keywords)}">')
    if canonical:
        if 'rel="canonical"' not in low and "rel='canonical'" not in low:
            additions.append(f'<link rel="canonical" href="{_escape(canonical)}">')
        if 'property="og:url"' in low:
            cleaned = re.sub(
                r"""(?is)(<meta\s+property=["']og:url["']\s+content=["'])([^"']*)(["'][^>]*>)""",
                lambda m: m.group(1) + _escape(canonical) + m.group(3),
                cleaned,
                count=1,
            )
        else:
            additions.append(f'<meta property="og:url" content="{_escape(canonical)}">')
    if "localbusiness" not in cleaned.lower() and business.get("name"):
        schema = {
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "name": business["name"],
            "url": canonical or business.get("site_url") or "",
            "address": business.get("address") or business.get("city") or "",
            "telephone": business.get("phone") or "",
        }
        additions.append(
            '<script type="application/ld+json">'
            + json.dumps({k: v for k, v in schema.items() if v}, ensure_ascii=False)
            + "</script>"
        )
    if "faqpage" not in cleaned.lower():
        faq = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": f"Como falar com {business.get('name') or 'este negocio'}?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": "Use o WhatsApp ou os contatos confirmados nesta pagina.",
                    },
                }
            ],
        }
        additions.append('<script type="application/ld+json">' + json.dumps(faq, ensure_ascii=False) + "</script>")
    if additions:
        cleaned = re.sub(r"(?is)</head\s*>", "\n".join(additions) + "\n</head>", cleaned, count=1)
    return cleaned


def publication_page_title(prd, business: dict[str, str]) -> str:
    """Re-export from html_phase6_repair for backward compatibility."""
    from backend.agents.html_phase6_repair import publication_page_title as _func
    return _func(prd, business)


def publication_page_description(prd, business: dict[str, str]) -> str:
    """Re-export from html_phase6_repair for backward compatibility."""
    from backend.agents.html_phase6_repair import publication_page_description as _func
    return _func(prd, business)


def publication_canonical_from_prd(prd) -> str:
    """Re-export from html_phase6_repair for backward compatibility."""
    from backend.agents.html_phase6_repair import publication_canonical_from_prd as _func
    return _func(prd)


def publication_business_from_prd(prd) -> dict[str, str]:
    """Re-export from html_phase6_repair for backward compatibility."""
    from backend.agents.html_phase6_repair import publication_business_from_prd as _func
    return _func(prd)


def publication_keyword_meta(prd) -> str:
    """Re-export from phase6_repair for convenience."""
    from backend.agents.html_phase6_repair import _publication_keyword_meta
    return _publication_keyword_meta(prd)


# ─── Footer Contract ─────────────────────────────────────────────────────────


def _ensure_builder_footer_contract(html: str, prd) -> str:
    footer_match = re.search(r"(?is)<footer\b.*?</footer>", html or "")
    if not footer_match:
        return html
    footer = footer_match.group(0)
    additions: list[str] = []
    if len(re.findall(r"(?is)<a\b", footer)) < 2:
        phone = re.sub(r"\D+", "", str(_get(prd, "phone", "telefone", default="")))
        whatsapp = f"https://wa.me/55{phone}" if phone else "#contato"
        additions.append(
            '<nav class="fralib-footer-nav" aria-label="Navegação do site">'
            '<a href="#hero">Inicio</a>'
            '<a href="#localizacao">Localizacao</a>'
            f'<a href="{_escape(whatsapp)}">WhatsApp</a>'
            "</nav>"
        )
    footer_text = _normalize(_visible_text(footer))
    if not any(token in footer_text for token in ("confianca", "privacidade", "lgpd", "cookies", "seguranca")):
        additions.append(
            '<p class="fralib-footer-trust">Privacidade, LGPD e contato oficial preservados para atendimento seguro.</p>'
        )
    if "abrir mapa" not in footer_text and "abrir rota" not in footer_text:
        maps_url = str(_get(prd, "maps_url", "map_url", default="") or "").strip()
        if maps_url:
            additions.append(
                '<a class="fralib-footer-map" '
                f'href="{_escape(maps_url)}" target="_blank" rel="noopener noreferrer">Abrir mapa</a>'
            )
    if not additions:
        return html
    updated_footer = re.sub(
        r"(?is)</footer>",
        "\n" + "\n".join(additions) + "\n</footer>",
        footer,
        count=1,
    )
    return (html or "")[: footer_match.start()] + updated_footer + (html or "")[footer_match.end() :]


# ─── Helper Functions ────────────────────────────────────────────────────────


def _add_data_lgpd_banner(match: re.Match) -> str:
    tag = match.group(0)
    attrs = ""
    if "data-lgpd-banner" not in tag.lower():
        attrs += " data-lgpd-banner"
    if "style=" not in tag.lower():
        attrs += (
            ' style="position:fixed;left:16px;right:16px;bottom:16px;z-index:9999;'
            'max-width:calc(100vw - 32px);box-sizing:border-box;'
            'display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center;'
            'padding:14px 16px;border-radius:16px;border:1px solid var(--border,rgba(255,255,255,.18));'
            'background:var(--surface,#111827);color:var(--fg,#fff)"'
        )
    if not attrs:
        return tag
    return tag[:-1] + attrs + ">"


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
