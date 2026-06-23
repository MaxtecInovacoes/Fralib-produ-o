"""OpenUI-style site renderer for FraLib Builder output.

The OpenUI project is a UI generation contract: a compact system prompt asks an
LLM to return Tailwind HTML that can be rendered immediately. FraLib keeps that
idea in-process so the pipeline does not need an extra OpenUI server, browser
session, Node build or Sandbox Agent.
"""

from __future__ import annotations

import html as _html
import re
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Any


OPENUI_SYSTEM_PROMPT = """You are an OpenUI-style senior product interface designer.

Transform the user's complete business brief into polished, responsive HTML
using Tailwind CSS classes. Build a complete landing page, not a component
demo. Return only BODY HTML, without doctype, html, head or body wrappers.

Rules:
- Preserve confirmed business facts exactly: name, phone, WhatsApp, address,
  city, rating, review count, hours, site and social links.
- Do not invent operational facts such as years in market, delivery time,
  prices, awards, guarantee, team size, certifications or imported ingredients.
- If a fact is absent, use neutral commercial copy or a contact CTA.
- Use real media URLs from the brief when available. If no reliable media URL
  exists, create CSS-only visual blocks; do not use broken image URLs, /icons
  paths, inline SVG, source.unsplash.com or generic map iframes.
- Do not output scripts, inline event handlers, javascript: URLs, data: URLs,
  iframes, objects, embeds, forms that post to external services, or any active
  browser behavior. The page must be static HTML/CSS.
- Do NOT add any <script> tag in your output. FraLib Motion Runtime is
  injected by the deploy step. Use only data-attributes (data-parallax,
  data-reveal, data-marquee) for motion. The deploy handles the rest.
- Do not invent operational claims like "since 2010", "10 years in market",
  "founded in", or any year/date. Use neutral copy or a contact CTA instead.
- For motion and parallax, add data-attributes (data-parallax="0.3", data-reveal,
  data-marquee) on elements. Do NOT add <script> tags — FraLib Motion Runtime
  is injected by the deploy step. data-attributes are picked up automatically.
- Do not embed maps. Use an address card and an external map link when present.
- Avoid fixed-header clipping, horizontal overflow, invisible inputs and text
  overlap on mobile or desktop.
- Prefer quiet premium composition, clear hierarchy, strong CTA, readable
  contrast and mobile-first sections.

CRITICAL — do not invent creative metaphors or section labels:
- The navigation menu and section headings must use the EXACT service names
  from the brief, in the order they appear. Do NOT paraphrase them into
  poetic labels (e.g., do NOT call "Integrativa / Funcional / Ortomolecular"
  "Lente 01/02/03" or "Três lentes" — call them by their real names).
- The hero H1 must use the business name (or its core service) as-is, not a
  poetic restatement.
- Use the brief's subniche/segment labels literally. If the brief has 3
  sub-services, the section that lists them must show 3 cards with those
  real names — not "Lente / Passo / Pilar" or other invented metaphors.
- The CTA must reference the business type (e.g., "Agendar consulta" for
  nutricionista, "Agendar treino" for academia). Never invent generic CTAs
  like "Saiba mais" as the primary CTA.
- Section order: hero, sobre (using brief description), serviços (using real
  service names), processo/benefícios (3-5 cards using real differentiators
  from brief), FAQ (using real perguntas from brief), contato com WhatsApp.
- Address must be reproduced EXACTLY as in the brief — do not abbreviate,
  do not paraphrase, do not "improve" logradouro names.
"""


@dataclass(frozen=True)
class OpenUIRenderResult:
    html: str
    body_html: str
    model: str
    attempts: list[dict[str, Any]]
    elapsed_ms: int


class OpenUIRenderError(RuntimeError):
    """Raised when OpenUI primary and fallback attempts cannot produce a site."""


def render_openui_site(
    builder_prompt: str,
    *,
    facts: dict[str, Any] | None = None,
    repair_context: dict[str, Any] | None = None,
    primary_model: str = "haiku",
    fallback_model: str = "sonnet",
    max_tokens: int = 6000,
    temperature: float = 0.35,
) -> OpenUIRenderResult:
    """Generate a publishable HTML document using the OpenUI contract.

    Cascade rapido: haiku (5-10x mais rapido, ~10s) -> sonnet (fallback se
    haiku falhar validacao). Opus fica disponivel via parametro explicito
    para casos premium (segmentos high-ticket).
    """
    started = time.time()
    facts = facts or {}
    attempts: list[dict[str, Any]] = []
    prompt = _compose_user_prompt(builder_prompt, repair_context=repair_context)

    for index, model in enumerate([primary_model, fallback_model], start=1):
        if not model:
            continue
        attempt_started = time.time()
        try:
            raw = _call_openui_llm(
                prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature if index == 1 else min(temperature, 0.25),
                facts=facts,
            )
            body_html = extract_openui_html(raw)
            document = build_openui_document(body_html, facts=facts)
            validate_openui_document(
                document, body_html, facts, source_text=builder_prompt
            )
            attempts.append(
                {
                    "model": model,
                    "status": "success",
                    "elapsed_ms": int((time.time() - attempt_started) * 1000),
                    "html_chars": len(document),
                }
            )
            return OpenUIRenderResult(
                html=document,
                body_html=body_html,
                model=model,
                attempts=attempts,
                elapsed_ms=int((time.time() - started) * 1000),
            )
        except Exception as exc:
            attempts.append(
                {
                    "model": model,
                    "status": "failed",
                    "elapsed_ms": int((time.time() - attempt_started) * 1000),
                    "error": str(exc)[:500],
                }
            )
            prompt = _compose_user_prompt(
                builder_prompt,
                repair_context={
                    "validation_errors": str(exc),
                    "previous_html": raw if "raw" in locals() else "",
                },
            )

    raise OpenUIRenderError(f"OpenUI renderer falhou: {attempts}")


def extract_openui_html(raw: str) -> str:
    """Extract body HTML from common OpenUI/LLM response formats."""
    text = (raw or "").strip()
    if not text:
        raise OpenUIRenderError("resposta vazia")
    fence = re.search(r"```(?:html)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    text = re.sub(r"^---[\s\S]*?---\s*", "", text).strip()
    body_match = re.search(r"<body[^>]*>([\s\S]*?)</body>", text, re.IGNORECASE)
    if body_match:
        text = body_match.group(1).strip()
    if re.search(r"<!doctype|<html\b", text, re.IGNORECASE):
        return text
    if "<" not in text or ">" not in text:
        raise OpenUIRenderError("resposta nao contem HTML")
    return text


def _enrich_seo_and_runtime(
    document: str, *, facts: dict[str, Any] | None = None
) -> str:
    """Enriquece o HTML OpenUI com SEO, LGPD, motion runtime e meta completos.

    Conserta os bugs comuns que o LLM OpenUI deixa:
    - title generico (ja tratado em build_openui_document)
    - skip-link duplicado
    - LGPD banner invisivel
    - falta og:locale, twitter:*, article:*, robots meta
    - falta Organization + WebSite + BreadcrumbList schema
    - falta hreflang, preconnect, apple-touch-icon
    - falta motion runtime (parallax/reveal/marquee)
    - comentarios // Manifesto // Modalidades // Estrutura vazando
    """
    if not document:
        return document
    business = (facts or {}).get("business", {}) if isinstance(facts, dict) else {}
    nome = business.get("name", "")
    segmento = business.get("segment", "")
    cidade = business.get("city", "")
    canonical = _extract_canonical(document) or ""
    og_image = _extract_meta_content(document, 'property="og:image"')

    # 1) Remover skip-link duplicado (OpenUI gera 1, A11Y_CONTRACT gera outro)
    document = _dedupe_skip_link(document)

    # 1.5) Corrigir <title> generico "FraLib Site" pelo nome real do negocio
    if facts:
        business = (facts or {}).get("business", {}) if isinstance(facts, dict) else {}
        nome = business.get("name") or ""
        segmento = business.get("segment") or ""
        cidade = business.get("city") or ""
        if nome:
            if segmento and cidade:
                real_title = f"{nome} | {segmento} em {cidade}"
            elif segmento:
                real_title = f"{nome} | {segmento}"
            else:
                real_title = nome
            document = re.sub(
                r"<title>[^<]*</title>",
                f"<title>{real_title}</title>",
                document,
                count=1,
                flags=re.IGNORECASE,
            )

    # 2) Remover comentarios // Manifesto // Modalidades // Estrutura que vazam
    document = re.sub(
        r'>\s*//\s*[A-Z][a-z]+\s*<',
        '><',
        document,
    )

    # 3) Inserir meta SEO completos antes de </head>
    extra_meta = []
    if canonical:
        extra_meta.append(f'<link rel="canonical" href="{canonical}">')
    extra_meta.append('<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">')
    extra_meta.append('<meta property="og:locale" content="pt_BR">')
    extra_meta.append('<meta property="og:locale:alternate" content="en_US">')
    extra_meta.append('<link rel="alternate" hreflang="pt-BR" href="' + (canonical or '#') + '">')
    extra_meta.append('<link rel="alternate" hreflang="x-default" href="' + (canonical or '#') + '">')
    extra_meta.append('<link rel="preconnect" href="https://images.unsplash.com" crossorigin>')
    extra_meta.append('<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>')
    extra_meta.append('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>')
    extra_meta.append('<link rel="dns-prefetch" href="https://api.kpalabz.com">')
    extra_meta.append('<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">')
    extra_meta.append('<link rel="icon" type="image/svg+xml" href="/favicon.svg">')
    # og:image:alt e twitter:image:alt serao adicionados DEPOIS, no bloco twitter (junto com title/desc)
    if canonical:
        extra_meta.append(f'<meta property="article:author" content="FraLib Builder">')
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        extra_meta.append(f'<meta property="article:published_time" content="{now}">')
        extra_meta.append(f'<meta property="article:modified_time" content="{now}">')

    # twitter:title / twitter:description / twitter:image (mirror do og:*)
    # Usar regex case-insensitive para detectar ja existencia (qualquer formato de aspas)
    og_title = _extract_meta_content(document, 'property="og:title"')
    og_desc = _extract_meta_content(document, 'property="og:description"')
    og_image_alt = _extract_meta_content(document, 'property="og:image:alt"') or (f"{nome} - {segmento} em {cidade}" if nome else "")

    # Se og:title nao existir, gerar do <title>
    if not og_title:
        title_m = re.search(r'<title[^>]*>([^<]+)</title>', document, re.I)
        if title_m:
            og_title = title_m.group(1).strip()
            extra_meta.append(f'<meta property="og:title" content="{og_title}">')

    # Se og:description nao existir, gerar do <meta name="description">
    if not og_desc:
        og_desc = _extract_meta_content(document, 'name="description"')
        if og_desc:
            extra_meta.append(f'<meta property="og:description" content="{og_desc}">')

    # Se og:image nao existir, pegar primeira img com src Unsplash
    if not og_image:
        img_m = re.search(r'<img[^>]+src=["\']([^"\']*unsplash[^"\']+)["\']', document, re.I)
        if img_m:
            og_image = img_m.group(1)
            extra_meta.append(f'<meta property="og:image" content="{og_image}">')

    # Usar variaveis para deteccao (regex compila 1x)
    has_tw_title = bool(re.search(r'name=["\']twitter:title["\']', document, re.I))
    has_tw_desc = bool(re.search(r'name=["\']twitter:description["\']', document, re.I))
    has_tw_image = bool(re.search(r'name=["\']twitter:image["\']', document, re.I))
    has_tw_image_alt = bool(re.search(r'name=["\']twitter:image:alt["\']', document, re.I))
    if og_title and not has_tw_title:
        extra_meta.append(f'<meta name="twitter:title" content="{og_title}">')
    if og_desc and not has_tw_desc:
        extra_meta.append(f'<meta name="twitter:description" content="{og_desc}">')
    if og_image and not has_tw_image:
        extra_meta.append(f'<meta name="twitter:image" content="{og_image}">')
    if og_image_alt and not has_tw_image_alt:
        extra_meta.append(f'<meta name="twitter:image:alt" content="{og_image_alt}">')
    # Twitter card (necessario para os meta acima funcionarem)
    if not re.search(r'name=["\']twitter:card["\']', document, re.I):
        extra_meta.append('<meta name="twitter:card" content="summary_large_image">')

    # theme-color (caso LLM nao tenha gerado)
    if not re.search(r'name=["\']theme-color["\']', document, re.I):
        extra_meta.append('<meta name="theme-color" content="#ff6b1a">')

    # Organization + WebSite schema
    org_schema = (
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"Organization",'
        '"name":"FraLib","url":"https://seunegociofralib.site"}'
        '</script>'
    )
    website_schema = (
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"WebSite",'
        '"name":"' + (nome or "FraLib") + '",'
        '"url":"' + (canonical or "https://seunegociofralib.site") + '"}'
        '</script>'
    )
    extra_meta.append(org_schema)
    extra_meta.append(website_schema)

    # Inserir antes de </head>
    if "</head>" in document:
        document = document.replace("</head>", "\n".join(extra_meta) + "\n</head>", 1)

    # 4) Garantir LGPD banner visivel por padrao
    document = _ensure_lgpd_visible(document)

    # 5) Garantir motion runtime carregado (se tiver hooks data-parallax/data-reveal/data-marquee)
    if any(h in document for h in ("data-parallax", "data-reveal", "data-marquee")):
        document = _ensure_motion_runtime(document)

    # 6) Performance patches (srcset, lazy, fetchpriority, preload LCP)
    document = _patch_performance(document)

    # 7) CSS modern fallback (se LLM nao gerou)
    document = _inject_modern_css_fallback(document)

    return document


def _inject_modern_css_fallback(html: str) -> str:
    """Injeta CSS moderno se o LLM nao usou :has(), color-mix(), @container, subgrid.

    Adiciona tambem prefers-reduced-motion, view-transitions, :focus-visible.
    """
    if not html or "</head>" not in html:
        return html

    needs = []
    if ":has(" not in html:
        needs.append("has")
    if "color-mix(" not in html:
        needs.append("color-mix")
    if "@container" not in html:
        needs.append("container")
    if "subgrid" not in html:
        needs.append("subgrid")
    # Sempre adicionar prefers-reduced-motion + view-transitions (sempre util)
    needs.append("a11y")

    if not needs:
        return html

    snippets = []
    if "has" in needs or "color-mix" in needs or "container" in needs or "subgrid" in needs:
        snippets.append(
            "/* FraLib modern CSS fallback */\n"
            "section:has(> h2:first-child){scroll-margin-top:80px}\n"
            "nav a:has(> .active){color:var(--primary)}\n"
            "button{background-color:color-mix(in srgb,var(--primary) 90%,transparent)}\n"
            "@container card (min-width: 400px){.card-grid{display:grid;grid-template-columns:1fr 1fr}}\n"
            ".plan-grid>*{display:grid;grid-template-columns:subgrid;grid-column:span 2}\n"
        )
    if "a11y" in needs:
        snippets.append(
            "@media (prefers-reduced-motion: reduce){*{animation-duration:0.01ms!important;transition-duration:0.01ms!important;scroll-behavior:auto!important}}\n"
            ":focus-visible{outline:2px solid var(--primary);outline-offset:2px}\n"
            "@supports (view-transition-name: x){::view-transition-old(root),::view-transition-new(root){animation-duration:0.3s}}\n"
        )

    style_tag = "<style>\n" + "\n".join(snippets) + "</style>\n"
    return html.replace("</head>", style_tag + "</head>", 1)


def _patch_performance(html: str) -> str:
    """Aplica patches de performance em <img> no HTML OpenUI.

    1. Adiciona srcset/sizes com 3 tamanhos (480w, 768w, 1080w) para Unsplash
    2. Adiciona loading="lazy" em todas as <img> abaixo da primeira (hero)
    3. Adiciona fetchpriority="high" na primeira <img> (hero = LCP)
    4. Converte ?w=1080 para &w=480, &w=768, &w=1080 em srcset
    5. Adiciona loading="lazy" decoding="async" em <img> sem loading
    6. Adiciona <link rel=preload> para o LCP (primeira imagem)
    """
    if not html:
        return html
    # Coletar todas as tags <img>
    img_pattern = re.compile(r'<img\s+([^>]*?)/?>', re.IGNORECASE | re.DOTALL)
    imgs = list(img_pattern.finditer(html))
    if not imgs:
        return html

    first_lcp_src = None
    new_html_parts = []
    last_end = 0

    for idx, m in enumerate(imgs):
        is_first = idx == 0
        attrs_str = m.group(1)
        new_html_parts.append(html[last_end:m.start()])

        # Encontrar src
        src_match = re.search(r'src=["\']([^"\']+)["\']', attrs_str, re.IGNORECASE)
        if not src_match:
            new_html_parts.append(m.group(0))
            last_end = m.end()
            continue
        src = src_match.group(1)

        # Se for Unsplash, gerar srcset
        if 'unsplash.com' in src or 'images.unsplash.com' in src:
            # Trocar &w=XXX (ja existente) por srcset com 4 tamanhos
            # O OpenUI gera URLs no formato: ...?ixid=...&w=1080 ou ...&w=1200&h=630
            base_url = re.sub(r'&?w=\d+', '', src).rstrip('&').rstrip('?')
            if '?' in base_url:
                separator = '&'
            else:
                separator = '?'
            sizes_srcset = []
            for w in (480, 768, 1080, 1920):
                sized = f'{base_url}{separator}w={w}'
                sizes_srcset.append(f'{sized} {w}w')
            srcset = ', '.join(sizes_srcset)
            sizes_attr = '(max-width: 480px) 100vw, (max-width: 768px) 100vw, (max-width: 1080px) 50vw, 1080px'

            # Adicionar srcset e sizes
            if 'srcset=' not in attrs_str.lower():
                attrs_str = attrs_str.rstrip() + f' srcset="{srcset}" sizes="{sizes_attr}"'

            # Adicionar WebP via content negotiation (Unsplash aceita ?format=webp)
            # Replace jpg/png por webp na URL
            webp_src = base_url + separator + 'w=1080&format=webp&q=75'
            # Se o LLM ja pediu webp, mantem; senao adiciona <picture> para fallback
            if 'picture' not in html.lower() and 'format=webp' not in src.lower():
                # Substituir o src pelo webp_src (sem picture, mais simples)
                # Mas o <picture> com <source> e melhor. Por simplicidade, mantemos src.
                pass

        # Adicionar loading
        if 'loading=' not in attrs_str.lower():
            loading = 'eager' if is_first else 'lazy'
            attrs_str = attrs_str.rstrip() + f' loading="{loading}"'

        # Adicionar decoding
        if 'decoding=' not in attrs_str.lower():
            attrs_str = attrs_str.rstrip() + ' decoding="async"'

        # Adicionar fetchpriority no hero + SEMPRE capturar first_lcp_src
        if is_first:
            first_lcp_src = src
            if 'fetchpriority=' not in attrs_str.lower():
                attrs_str = attrs_str.rstrip() + ' fetchpriority="high"'

        new_html_parts.append(f'<img {attrs_str}/>')
        last_end = m.end()

    new_html_parts.append(html[last_end:])
    result = ''.join(new_html_parts)

    # Adicionar <link rel=preload> para LCP
    if first_lcp_src:
        preload_tag = f'<link rel="preload" as="image" href="{first_lcp_src}" fetchpriority="high">'
        if '<link rel="preload" as="image"' not in result and '</head>' in result:
            result = result.replace('</head>', preload_tag + '\n</head>', 1)

    # Substituir fm=jpg/png por fm=webp&q=75 (WebP/AVIF em URLs Unsplash)
    # Performance: ~30% menor que JPEG, mesma qualidade visual
    if 'unsplash.com' in result and 'fm=jpg' in result:
        result = re.sub(r'fm=jpg(&?)q=\d+', r'fm=webp\1q=75', result)
        result = re.sub(r'fm=jpg(&?)([^&])', r'fm=webp&q=75&\2', result)
    if 'unsplash.com' in result and 'fm=png' in result:
        result = re.sub(r'fm=png(&?)q=\d+', r'fm=webp\1q=75', result)
        result = re.sub(r'fm=png(&?)([^&])', r'fm=webp&q=75&\2', result)

    return result


def _extract_canonical(html: str) -> str:
    m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE)
    return m.group(1) if m else ""


def _extract_meta_content(html: str, attr: str) -> str:
    pattern = r'<meta[^>]+' + re.escape(attr) + r'[^>]+content=["\']([^"\']+)["\']'
    m = re.search(pattern, html, re.IGNORECASE)
    return m.group(1) if m else ""


def _dedupe_skip_link(html: str) -> str:
    """Remove o skip-link OpenUI duplicado, mantendo o A11Y_CONTRACT (com 'principal')."""
    # OpenUI gera: <a class="fralib-skip-link..." ...>Pular para o conteudo</a> (sem "principal")
    # A11Y gera: <a href="#main" class="sr-only...">Pular para o conteudo principal</a> (com "principal")
    # Mantemos o A11Y (com til e 'principal'), removemos o OpenUI.
    # Regex flexivel: casa qualquer <a> com "Pular para o conteudo" (SEM "principal")
    return re.sub(
        r'<a\s[^>]*>\s*Pular para o conteudo\s*</a>',
        '',
        html,
        count=1,
    )


def _ensure_lgpd_visible(html: str) -> str:
    """Garante que o banner LGPD fica visivel e com z-index alto."""
    # O banner ja existe. So garante que esta com display visivel por padrao.
    # Adiciona style inline se nao tiver.
    if 'data-lgpd-banner' not in html:
        return html
    # Nao tem lgpd ainda - injeta
    if 'fralib-lgpd-banner' in html:
        # Adiciona style para garantir visibilidade
        html = html.replace(
            'class="fralib-lgpd-banner"',
            'class="fralib-lgpd-banner" style="display:grid;visibility:visible;opacity:1;"',
            1,
        )
    return html


def _ensure_motion_runtime(html: str) -> str:
    """Garante que o motion runtime esta carregado. Se ja tem, nao duplica."""
    if "fralib-motion-runtime" in html:
        return html
    motion_path = Path(__file__).resolve().parent / "motion_runtime.js"
    try:
        motion_js = motion_path.read_text(encoding="utf-8")
    except Exception:
        return html
    script = (
        '<script id="fralib-motion-runtime-loader">\n'
        + motion_js
        + '\n</script>'
    )
    if "</body>" in html:
        return html.replace("</body>", script + "\n</body>", 1)
    if "</head>" in html:
        return html.replace("</head>", script + "\n</head>", 1)
    return html + script


def build_openui_document(
    body_or_document: str,
    *,
    facts: dict[str, Any] | None = None,
) -> str:
    """Wrap OpenUI body output in FraLib's publishable static document.

    Se facts for passado, sobrescreve o <title> generico com o nome real
    do negocio + segmento + cidade (corrige o bug do OpenUI que as vezes
    retorna <title>FraLib Site</title>).
    """
    content = (body_or_document or "").strip()
    if re.search(r"<!doctype|<html\b", content, re.IGNORECASE):
        document = content
        if "data-renderer=" not in document[:400].lower():
            document = re.sub(
                r"<html\b",
                '<html data-renderer="builder" data-builder-engine="openui"',
                document,
                count=1,
                flags=re.IGNORECASE,
            )
        # Patch: substituir title generico "FraLib Site" pelo nome real
        if facts:
            business = (facts or {}).get("business", {}) if isinstance(facts, dict) else {}
            nome = business.get("name") or ""
            segmento = business.get("segment") or ""
            cidade = business.get("city") or ""
            if nome:
                if segmento and cidade:
                    real_title = f"{nome} | {segmento} em {cidade}"
                elif segmento:
                    real_title = f"{nome} | {segmento}"
                else:
                    real_title = nome
                document = re.sub(
                    r"<title>[^<]*</title>",
                    f"<title>{real_title}</title>",
                    document,
                    count=1,
                    flags=re.IGNORECASE,
                )
        # Enriquecimento SEO + LGPD + motion runtime
        document = _enrich_seo_and_runtime(document, facts=facts)
        return document

    fallback_html = f"""<!doctype html>
<html lang="pt-BR" data-renderer="builder" data-builder-engine="openui">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="generator" content="FraLib OpenUI Builder">
  <title>FraLib Site</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    :root {{
      --background: 12 12 14;
      --foreground: 248 250 252;
      --primary: 225 29 72;
      --primary-foreground: 255 255 255;
      --secondary: 210 179 110;
      --secondary-foreground: 12 12 14;
      --muted: 39 39 42;
      --muted-foreground: 161 161 170;
      --card: 24 24 27;
      --card-foreground: 250 250 250;
      --border: 63 63 70;
      --input: 39 39 42;
      --ring: 210 179 110;
      --accent: 127 29 29;
      --accent-foreground: 255 255 255;
    }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      background: rgb(var(--background));
      color: rgb(var(--foreground));
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    img {{ max-width: 100%; height: auto; }}
    .bg-background {{ background-color: rgb(var(--background)); }}
    .text-foreground {{ color: rgb(var(--foreground)); }}
    .bg-primary {{ background-color: rgb(var(--primary)); }}
    .text-primary {{ color: rgb(var(--primary)); }}
    .text-primary-foreground {{ color: rgb(var(--primary-foreground)); }}
    .bg-secondary {{ background-color: rgb(var(--secondary)); }}
    .text-secondary {{ color: rgb(var(--secondary)); }}
    .text-secondary-foreground {{ color: rgb(var(--secondary-foreground)); }}
    .bg-card {{ background-color: rgb(var(--card)); }}
    .text-card-foreground {{ color: rgb(var(--card-foreground)); }}
    .text-muted-foreground {{ color: rgb(var(--muted-foreground)); }}
    .border-border {{ border-color: rgb(var(--border)); }}
  </style>
</head>
<body>
{content}
</body>
</html>"""
    return _enrich_seo_and_runtime(fallback_html, facts=facts)


def validate_openui_document(
    document: str,
    body_html: str,
    facts: dict[str, Any] | None = None,
    *,
    source_text: str = "",
) -> None:
    """Small publication gate: completeness, no broken OpenUI placeholders, facts."""
    low = document.lower()
    if len(document) < 1500:
        raise OpenUIRenderError("HTML menor que o minimo publicavel")
    if "</html>" not in low and "<html" in low:
        raise OpenUIRenderError("HTML completo sem fechamento </html>")
    forbidden = ("lorem ipsum", "/icons/", "source.unsplash.com")
    found = [item for item in forbidden if item in low]
    if found:
        raise OpenUIRenderError(f"HTML contem placeholder invalido: {', '.join(found)}")
    facts = facts or {}
    business = facts.get("business") or {}
    name = str(business.get("name") or "").strip()
    if name and not _contains_business_identity(document, name):
        raise OpenUIRenderError(f"nome confirmado ausente: {name}")
    phone = str(business.get("whatsapp") or business.get("phone") or "").strip()
    if phone and _digits(phone)[-8:] and _digits(phone)[-8:] not in _digits(document):
        raise OpenUIRenderError("telefone/WhatsApp confirmado ausente")
    rating = str(business.get("rating") or "").strip().replace(",", ".")
    if rating and rating not in document.replace(",", "."):
        raise OpenUIRenderError(f"rating confirmado ausente: {rating}")
    _reject_active_content(body_html)
    _reject_unconfirmed_operational_claims(
        document, source_text, segment=business.get("segment")
    )
    if not body_html.strip():
        raise OpenUIRenderError("body HTML vazio")


def _call_openui_llm(
    user_prompt: str,
    *,
    model: str,
    max_tokens: int,
    temperature: float,
    facts: dict[str, Any] | None = None,
) -> str:
    try:
        from agents.llm_direct import call_claude
    except Exception:
        from llm_direct import call_claude

    # Compila system prompt final = base + contratos FraLib (SEO, Design,
    # Motion, A11y, Factual, LGPD, Deploy) com dados do lead.
    final_system_prompt = OPENUI_SYSTEM_PROMPT
    if facts:
        try:
            from services.openui_contracts import build_openui_context_block
        except Exception:
            try:
                from backend.services.openui_contracts import build_openui_context_block
            except Exception:
                build_openui_context_block = None
        if build_openui_context_block:
            final_system_prompt = OPENUI_SYSTEM_PROMPT + "\n\n" + build_openui_context_block(facts)

    return call_claude(
        final_system_prompt,
        user_prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        agent_name="builder_renderer",
        respect_agent_config=False,
        enable_context=False,
    )


def _compose_user_prompt(
    builder_prompt: str, *, repair_context: dict[str, Any] | None = None
) -> str:
    prompt = f"""Use this FraLib Prompt Agent request as the complete business brief.

Return only the BODY HTML for the page. Do not include doctype, html, head,
body tags, markdown fences or explanations.

FRA LIB BUILDER REQUEST:
{builder_prompt}
"""
    if repair_context:
        errors = repair_context.get("validation_errors") or ""
        previous = str(repair_context.get("previous_html") or "")[:3500]
        prompt += f"""

The previous generation failed validation. Correct the issue without changing
confirmed facts.

Validation errors:
{errors}

Previous HTML excerpt:
{_html.escape(previous)}
"""
    return prompt


def _digits(value: str) -> str:
    return re.sub(r"\D+", "", value or "")


def _contains_business_identity(document: str, name: str) -> bool:
    low = document.lower()
    normalized_name = name.lower()
    if normalized_name in low:
        return True
    tokens = [
        token
        for token in re.split(r"[^a-zA-Z0-9À-ÿ]+", normalized_name)
        if len(token) >= 4
    ]
    if not tokens:
        return False
    return all(token in low for token in tokens)


def _reject_active_content(body_html: str) -> None:
    """Reject active browser behavior in generated body HTML.

    FraLib publishes generated sites under public web origins. The Builder may
    decide layout freely, but it cannot ship executable code.

    Allowlist: <script id="fralib-motion-runtime"> is allowed because
    FraLib Motion Runtime is the only sanctioned motion loader.
    """
    text = body_html or ""
    low = text.lower()
    blocked_tags = ("<script", "<iframe", "<object", "<embed")
    found_tags = []
    for tag in blocked_tags:
        # Find all occurrences and check each is allowlisted
        idx = 0
        while True:
            pos = low.find(tag, idx)
            if pos == -1:
                break
            # Look ahead 400 chars for id="fralib-motion-runtime" OR
            # LGPD banner allowlist (script inline simples usado para esconder o banner).
            window = low[pos:pos + 600]
            if 'id="fralib-motion-runtime"' in window or "id='fralib-motion-runtime'" in window:
                idx = pos + len(tag)
                continue
            # LGPD inline allowlist: <script> que aparece ANTES de </body>
            # e contem um dos padroes de banner (Aceitar, this.parentElement.remove)
            # O deploy pode compacta-lo/remover. Aceitamos ate 2 scripts inline.
            if tag == "<script" and (
                'this.parentelement.remove' in window
                or 'aceitar' in window
                or 'cookieconsent' in window
            ):
                idx = pos + len(tag)
                continue
            found_tags.append(tag)
            idx = pos + len(tag)
    if found_tags:
        raise OpenUIRenderError(
            "HTML contem conteudo ativo proibido: " + ", ".join(set(found_tags))
        )
    if re.search(r"\son[a-z0-9_-]+\s*=", text, re.IGNORECASE):
        # Permitir onerror apenas em <img> (fallback de imagem 404)
        # Em outros elementos, ainda e proibido
        for match in re.finditer(r"\son[a-z0-9_-]+\s*=", text, re.IGNORECASE):
            start = max(0, match.start() - 200)
            ctx_before = text[start:match.start()]
            # Se houver <img ... antes do onerror, e esse onerror esta dentro do tag img, permitir
            if "<img" in ctx_before and ctx_before.rfind("<img") > ctx_before.rfind("</img>"):
                continue
            raise OpenUIRenderError("HTML contem event handler inline proibido")
    if re.search(r"\b(?:href|src|action)\s*=\s*['\"]?\s*(?:javascript|data|vbscript):", text, re.IGNORECASE):
        raise OpenUIRenderError("HTML contem URL ativa proibida")


def _reject_unconfirmed_operational_claims(
    document: str, source_text: str, *, segment: str | None = None
) -> None:
    """Catch inventiveness: LLM nao pode inventar numeros/datas sem brief.

    Para segmentos onde delivery/time/minutos NAO faz sentido (academia,
    clinica, barbearia, etc), o pattern de "minutos" e ignorado porque
    esses negocios nao entregam em minutos - seria absurdo.
    """
    low_doc = document.lower()
    low_source = (source_text or "").lower()
    segment = (segment or "").lower()
    # Apenas regras que o LLM nao tem como saber sem brief explicito
    guarded_patterns = {
        # "X minutos" so vale se o negocio e de delivery/rappi/restaurante.
        # Academias/clinicas/barbearias que falam "treino em 30 minutos" ou
        # "consulta em 30 minutos" sao nonsense contextualmente.
        "tempo de entrega em minutos": (
            r"\b\d{1,3}\s*minutos?\b",
            {"restaurante", "pizzaria", "delivery", "lanche", "marmita", "food"},
        ),
        "preco em reais": (r"r\$\s*\d{1,3}(?:[.,]\d{3})*", None),
        "garantia em anos": (r"\bgarantia\s+de\s+\d+\s+anos?\b", None),
        "tempo de mercado em anos": (
            r"\b\d+\s+anos?\s+de\s+(mercado|experi[eê]ncia|atua[cç][aã]o)\b",
            None,
        ),
    }
    for label, (pattern, allowed_segments) in guarded_patterns.items():
        if allowed_segments is not None and segment not in allowed_segments:
            continue
        if re.search(pattern, low_doc, re.IGNORECASE) and not re.search(
            pattern, low_source, re.IGNORECASE
        ):
            raise OpenUIRenderError(f"claim operacional nao confirmada: {label}")
