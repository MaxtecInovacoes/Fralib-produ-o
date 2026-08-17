"""Phase 6 publication contract repair for generated HTML.

Handles deterministic repairs to ensure Phase 6 contract compliance:
- Head elements (fonts, schema, og tags)
- Body elements (hero, skip link, progress bar)
- CSS contract and animation foundations
"""


import html as _html
import re

from backend.domain.phase6_contract import (
    phase6_business_segment as _shared_phase6_business_segment,
    phase6_business_subniche as _shared_phase6_business_subniche,
    phase6_design_archetype as _shared_phase6_design_archetype,
    phase6_image_asset as _shared_phase6_image_asset,
    phase6_should_use_video_hero as _shared_phase6_should_use_video_hero,
    phase6_slug_token as _shared_phase6_slug_token,
    phase6_video_asset as _shared_phase6_video_asset,
    sanitize_keyword_term as _shared_sanitize_keyword_term,
)
from backend.utils.schema_builder import gerar_faq_schema as _gerar_faq_schema


# ─── Phase 6 Wrappers ────────────────────────────────────────────────────────


def phase6_should_use_video_hero(prd) -> bool:
    return _shared_phase6_should_use_video_hero(prd, require_video_asset=True)


def phase6_video_asset(prd) -> dict[str, str]:
    return _shared_phase6_video_asset(prd)


def phase6_image_asset(prd) -> str:
    return _shared_phase6_image_asset(prd)


def phase6_business_segment(prd) -> str:
    return _shared_phase6_business_segment(prd)


def phase6_business_subniche(prd) -> str:
    return _shared_phase6_business_subniche(prd)


def phase6_design_archetype(prd) -> str:
    return _shared_phase6_design_archetype(prd)


def phase6_slug_token(value) -> str:
    return _shared_phase6_slug_token(value)


def sanitize_keyword_term(value, *, limit: int = 60) -> str:
    return _shared_sanitize_keyword_term(value, limit=limit)


# ─── Public Repair Entry Points ──────────────────────────────────────────────


def repair_phase6_publication_contract(html: str, prd=None) -> str:
    """Repair Phase 6 publication contract in HTML head."""
    cleaned = html or ""
    low = cleaned.lower()
    if 'data-renderer="builder"' not in low:
        return cleaned
    html_tag = re.search(r"(?is)<html\b[^>]*>", cleaned)
    if html_tag and "data-theme=" not in html_tag.group(0).lower():
        cleaned = re.sub(r"(?is)<html\b([^>]*)>", r'<html\1 data-theme="light">', cleaned, count=1)
    if "<head" in cleaned.lower():
        head_additions = []
        if "fonts.gstatic.com" not in cleaned.lower():
            head_additions.append('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>')
        if "display=swap" not in cleaned.lower():
            head_additions.append('<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">')
        if 'name="keywords"' not in cleaned.lower():
            keywords = _publication_keyword_meta(prd)
            if keywords:
                head_additions.append(f'<meta name="keywords" content="{_escape(keywords)}">')
        if 'property="og:image:width"' not in cleaned.lower():
            head_additions.append('<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">')
        if "breadcrumblist" not in cleaned.lower():
            head_additions.append('<script type="application/ld+json">{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Inicio","item":"#"}]}</script>')
        if "faqpage" not in cleaned.lower():
            faq_tag = _gerar_faq_schema_from_prd(prd)
            if faq_tag:
                head_additions.append(faq_tag)
        if phase6_should_use_video_hero(prd) and "https://videos.pexels.com" not in cleaned.lower():
            head_additions.append('<link rel="preconnect" href="https://videos.pexels.com">')
        if "cdn.jsdelivr.net/npm/gsap" not in cleaned.lower():
            head_additions.append('<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script><script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js"></script>')
        if "cdn.jsdelivr.net/npm/lenis" not in cleaned.lower():
            head_additions.append('<script src="https://cdn.jsdelivr.net/npm/lenis@1.1.20/dist/lenis.min.js"></script>')
        if "fralib-phase6-contract" not in cleaned.lower():
            head_additions.append(
                '<style id="fralib-phase6-contract">:root{--fralib-scroll:0;--fralib-scroll-velocity:0}'
                '[data-theme="dark"]{--background:8 8 7;--foreground:255 247 237}'
                '*:focus-visible{outline:3px solid currentColor;outline-offset:4px}'
                'header,nav{backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px)}'
                '::-webkit-scrollbar{width:12px}html{scrollbar-color:currentColor transparent}'
                '.fralib-reading-progress{position:fixed;top:0;left:0;height:4px;width:calc(var(--fralib-scroll)*100%)}'
                '.fralib-cursor,.fralib-cursor-follower{position:fixed;pointer-events:none;border-radius:999px}'
                '.fralib-grain{position:fixed;inset:0;pointer-events:none}.fralib-card-interactive{transition:transform .28s ease}'
                '.fralib-letter-reveal{animation:fralib-letter-reveal .9s both}.magnetic-cta,[data-magnetic]{will-change:transform}'
                '@keyframes fralib-letter-reveal{from{opacity:.01;transform:translateY(.28em)}to{opacity:1;transform:translateY(0)}}'
                '</style>'
            )
        # FIX: prefers-reduced-motion verificado ANTES de iniciar GSAP
        if "fralibsmoothscroll" not in cleaned.lower() or "gsap.registerplugin" not in cleaned.lower():
            head_additions.append('<script id="fralib-phase6-runtime">window.fralibSmoothScroll=window.fralibSmoothScroll||{};(function(){const r=window.matchMedia&&window.matchMedia("(prefers-reduced-motion:reduce)").matches;if(r){document.documentElement.style.setProperty("--fralib-reduced-motion","1");}else if(window.gsap&&window.ScrollTrigger){gsap.registerPlugin(ScrollTrigger);}})();</script>')
        if head_additions:
            cleaned = re.sub(r"(?is)</head\s*>", "\n".join(head_additions) + "\n</head>", cleaned, count=1)
    return repair_phase6_body_contract(cleaned, prd)


def repair_phase6_body_contract(html: str, prd=None) -> str:
    """Repair Phase 6 publication contract in HTML body."""
    cleaned = html or ""
    video_asset = phase6_video_asset(prd) if phase6_should_use_video_hero(prd) else {}
    hero_type = "video" if video_asset else "image"
    if "data-hero-type=" not in cleaned.lower():
        if re.search(r"(?is)<header\b", cleaned):
            cleaned = re.sub(
                r"(?is)<header\b([^>]*)>",
                lambda m: _add_phase6_hero_attrs(m.group(0), hero_type),
                cleaned,
                count=1,
            )
        else:
            contract_header = _phase6_contract_header(prd, hero_type, video_asset)
            cleaned = re.sub(r"(?is)<body\b([^>]*)>", r"<body\1>" + contract_header, cleaned, count=1)
    if hero_type == "video" and "<video" not in cleaned.lower():
        cleaned = _inject_phase6_video_into_header(cleaned, video_asset)
    if "fralib-skip-link" not in cleaned.lower():
        cleaned = re.sub(r"(?is)<body\b([^>]*)>", r'<body\1><a class="fralib-skip-link" href="#main">Pular para o conteudo</a>', cleaned, count=1)
    if '<main id="main"' not in cleaned.lower():
        body_match = re.search(r"(?is)(<body\b[^>]*>)([\s\S]*?)(</body\s*>)", cleaned)
        if body_match:
            cleaned = cleaned[: body_match.start(2)] + '<main id="main">' + body_match.group(2) + '</main>' + cleaned[body_match.end(2) :]
    cleaned = re.sub(r"(?is)<h1\b[^>]*>", lambda m: _add_class_to_tag(_add_class_to_tag(m.group(0), "fralib-letter-reveal"), "font-black uppercase"), cleaned, count=1)
    cleaned = re.sub(r"(?is)<h2\b[^>]*>", lambda m: _add_class_to_tag(m.group(0), "fralib-text-scramble"), cleaned, count=1)
    if "fralib-text-scramble" not in cleaned.lower() and re.search(r"(?is)<h1\b", cleaned):
        cleaned = re.sub(r"(?is)<h1\b[^>]*>", lambda m: _add_class_to_tag(m.group(0), "fralib-text-scramble"), cleaned, count=1)
    if "fralib-text-scramble" not in cleaned.lower():
        marker = '<span class="fralib-text-scramble" data-text-scramble aria-hidden="true"></span>'
        cleaned = re.sub(r"(?is)</header\s*>", marker + "</header>", cleaned, count=1)
    cleaned = re.sub(r"(?is)<a\b[^>]*href=[^>]*>", lambda m: _add_class_to_tag(m.group(0), "magnetic-cta data-magnetic"), cleaned, count=1)
    cleaned = re.sub(r"(?is)<(?:article|div)\b[^>]*>", lambda m: _add_class_to_tag(m.group(0), "fralib-card-interactive"), cleaned, count=1)
    additions = []
    if "fralib-reading-progress" not in cleaned.lower() or 'role="progressbar"' not in cleaned.lower():
        additions.append('<div class="fralib-reading-progress" role="progressbar" aria-label="Progresso de leitura"></div>')
    if not re.search(r"""(?is)<div\b[^>]*class=(["'])[^"']*fralib-cursor-follower""", cleaned):
        additions.append('<div class="fralib-cursor"></div><div class="fralib-cursor-follower"></div>')
    if "fralib-theme-toggle" not in cleaned.lower():
        additions.append('<button class="fralib-theme-toggle magnetic-cta" type="button" aria-label="Alternar tema" data-magnetic>Tema</button>')
    if not re.search(r"""(?is)<svg\b[^>]*class=(["'])[^"']*fralib-grain""", cleaned):
        additions.append('<svg class="fralib-grain" aria-hidden="true"></svg>')
    if additions:
        cleaned = re.sub(r"(?is)</body\s*>", "\n".join(additions) + "\n</body>", cleaned, count=1)
    return cleaned


# ─── Helper Functions ────────────────────────────────────────────────────────


def _add_phase6_hero_attrs(tag: str, hero_type: str) -> str:
    updated = tag
    if "data-hero-type=" not in updated.lower():
        updated = updated[:-1].rstrip() + f' data-hero-type="{hero_type}">'
    if "data-parallax" not in updated.lower():
        updated = updated[:-1].rstrip() + " data-parallax>"
    return updated


def _phase6_contract_header(prd, hero_type: str, video_asset: dict[str, str]) -> str:
    business = _publication_business_from_prd(prd)
    name = business.get("name") or "Negocio local"
    segment = phase6_business_segment(prd) or "negocio local"
    city = business.get("city") or ""
    title = name
    subtitle = " ".join(part for part in (segment, city) if part).strip()
    media = ""
    if hero_type == "video" and video_asset.get("url"):
        poster = f' poster="{_escape(video_asset.get("poster"))}"' if video_asset.get("poster") else ""
        media = (
            f'<video class="fralib-hero-video" src="{_escape(video_asset["url"])}"{poster} '
            'autoplay muted loop playsinline preload="metadata"></video>'
        )
    else:
        from backend.agents.html_media_validator import image_fallback_for_segment
        image = phase6_image_asset(prd) or image_fallback_for_segment(prd)
        media = f'<img class="fralib-hero-image" src="{_escape(image)}" alt="{_escape(title)}" loading="eager" decoding="async">'
    return (
        f'<header id="hero" class="fralib-contract-hero" data-hero-type="{hero_type}" data-parallax>'
        f'{media}<div class="fralib-contract-hero-copy">'
        f'<p>{_escape(subtitle)}</p><h1 class="fralib-letter-reveal fralib-text-scramble" data-text-scramble>{_escape(title)}</h1>'
        '</div></header>'
    )


def _inject_phase6_video_into_header(html: str, video_asset: dict[str, str]) -> str:
    if not video_asset.get("url"):
        return html
    poster = f' poster="{_escape(video_asset.get("poster"))}"' if video_asset.get("poster") else ""
    video = (
        f'<video class="fralib-hero-video" src="{_escape(video_asset["url"])}"{poster} '
        'autoplay muted loop playsinline preload="metadata"></video>'
    )
    return re.sub(r"(?is)(<header\b[^>]*>)", r"\1" + video, html or "", count=1)


def _add_class_to_tag(tag: str, class_name: str) -> str:
    if class_name in tag:
        return tag
    match = re.search(r"(?is)\bclass\s*=\s*([\"'])(.*?)\1", tag)
    if match:
        updated = f'class={match.group(1)}{match.group(2).strip()} {class_name}{match.group(1)}'
        return tag[: match.start()] + updated + tag[match.end() :]
    return tag[:-1].rstrip() + f' class="{class_name}">'


def _escape(value) -> str:
    return _html.escape(str(value or ""), quote=True)


def _publication_keyword_meta(prd) -> str:
    """Extract and clean publication keywords from PRD."""
    business = _publication_business_from_prd(prd)
    segment = phase6_business_segment(prd)
    city = business.get("city") or str(_get(prd, "cidade", "city", default="") or "")
    terms: list[object] = [business.get("name"), segment]
    if city:
        terms.extend([city, f"{segment} {city}".strip()])
    seo = _get(prd, "seo", default={})
    if isinstance(seo, dict):
        raw_terms = seo.get("primary_terms") if isinstance(seo.get("primary_terms"), list) else []
        terms.extend(raw_terms)
    for key in ("seo_keywords", "keywords"):
        raw = _get(prd, key, default=[])
        if isinstance(raw, list):
            terms.extend(raw)
        elif isinstance(raw, str):
            terms.extend(re.split(r"[,;\n]+", raw))
    research = _get(prd, "research", default={})
    if isinstance(research, dict):
        research_text = str(research.get("keyword_research") or "")
        terms.extend(re.split(r"[,;\n]+", research_text))
    else:
        terms.extend(re.split(r"[,;\n]+", str(_get(prd, "keyword_research", default="") or "")))
    cleaned: list[str] = []
    seen: set[str] = set()
    for term in terms:
        clean = sanitize_keyword_term(term)
        if _is_garbage_publication_keyword(clean):
            continue
        key = clean.lower()
        if clean and key not in seen:
            cleaned.append(clean)
            seen.add(key)
    return ", ".join(cleaned[:10])


def publication_keyword_meta(prd) -> str:
    """Public export of _publication_keyword_meta for external modules."""
    return _publication_keyword_meta(prd)


def publication_business_from_prd(prd) -> dict[str, str]:
    """Public export of _publication_business_from_prd for external modules."""
    return _publication_business_from_prd(prd)


def publication_canonical_from_prd(prd) -> str:
    """Extract canonical URL from PRD."""
    for container_name in ("publication", "seo", "business"):
        container = _get(prd, container_name, default={})
        if not isinstance(container, dict):
            continue
        for key in ("canonical_url", "canonical", "site_url", "url_site"):
            url = str(container.get(key) or "").strip()
            if url.startswith(("http://", "https://")):
                return url
    for key in ("canonical_url", "canonical", "site_url", "url_site"):
        url = str(_get(prd, key, default="") or "").strip()
        if url.startswith(("http://", "https://")):
            return url
    return ""


def publication_page_title(prd, business: dict[str, str]) -> str:
    """Build publication page title."""
    name = business.get("name") or ""
    if not name:
        return ""
    segment = phase6_business_segment(prd)
    city = business.get("city") or ""
    suffix = " em ".join(part for part in (segment, city) if part)
    return f"{name} | {suffix}" if suffix else name


def publication_page_description(prd, business: dict[str, str]) -> str:
    """Build publication page description."""
    name = business.get("name") or "Negocio local"
    segment = phase6_business_segment(prd) or "negocio local"
    city = business.get("city") or ""
    if city:
        return f"{name}: {segment} em {city}, com contato e informações confirmadas."
    return f"{name}: {segment} com contato e informações confirmadas."


def _is_garbage_publication_keyword(term: str) -> bool:
    low = _normalize(term)
    if not low:
        return True
    blocked_fragments = (
        "title:",
        "titulo:",
        "título:",
        "subtitulo",
        "subtítulo",
        "subtitulos",
        "subtítulos",
        "meta description",
        "cta",
        "h1",
        "h2",
        "headline",
        "copy",
        "seo:",
        "keyword:",
        "keywords:",
        "prompt",
        "instrucao",
        "instrução",
    )
    if any(fragment in low for fragment in blocked_fragments):
        return True
    if ":" in term and len(term.split(":", 1)[0].strip()) <= 20:
        return True
    return False


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
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).lower()
    return re.sub(r"\s+", " ", text).strip()


def _publication_business_from_prd(prd) -> dict[str, str]:
    business = _get(prd, "business", default={})
    if not isinstance(business, dict):
        business = {}
    return {
        "name": str(business.get("name") or business.get("business_name") or _get(prd, "nome", "name", default="")).strip(),
        "city": str(business.get("city") or business.get("cidade") or _get(prd, "cidade", "city", default="")).strip(),
        "address": str(business.get("address") or business.get("endereco") or _get(prd, "address", "endereco", default="")).strip(),
        "phone": str(business.get("phone") or business.get("telefone") or business.get("whatsapp") or _get(prd, "phone", "telefone", "whatsapp", default="")).strip(),
        "site_url": str(business.get("site_url") or business.get("url_site") or _get(prd, "site_url", "url_site", default="")).strip(),
    }


def _gerar_faq_schema_from_prd(prd) -> str:
    """Extrai FAQ do PRD e gera tag JSON-LD FAQPage."""
    if not prd:
        return ""

    perguntas_respostas = []

    # Extrair de faqs direto no PRD
    faqs = _get(prd, "faqs", "faq", "perguntas_respostas", default=[])
    if isinstance(faqs, list):
        perguntas_respostas.extend(faqs)

    # Extrair de sections que contem faqs
    sections = _get(prd, "sections", default=[])
    if isinstance(sections, list):
        for section in sections:
            if isinstance(section, dict):
                section_faqs = section.get("faqs") or section.get("faq") or []
                if isinstance(section_faqs, list):
                    perguntas_respostas.extend(section_faqs)
                section_qa = section.get("perguntas_respostas") or []
                if isinstance(section_qa, list):
                    perguntas_respostas.extend(section_qa)

    # Extrair de content
    content = _get(prd, "content", default={})
    if isinstance(content, dict):
        content_faqs = content.get("faqs") or content.get("faq") or []
        if isinstance(content_faqs, list):
            perguntas_respostas.extend(content_faqs)

    if not perguntas_respostas:
        return ""

    deploy_url = publication_canonical_from_prd(prd) or ""
    return _gerar_faq_schema(perguntas_respostas, deploy_url)


def gerar_faq_schema_from_prd(prd) -> str:
    """Public export of _gerar_faq_schema_from_prd for external modules."""
    return _gerar_faq_schema_from_prd(prd)
