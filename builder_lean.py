"""
Builder Agent — OpenUI Single-Shot Client (LEAN PIPELINE).

Uma ÚNICA chamada ao OpenUI gera o HTML completo de ponta a ponta.
Sem shell, sem fragmentos, sem costuras.
"""
import os
import re
import time
import requests
from urllib.parse import quote_plus
from loguru import logger as _builder_logger

from backend.agents.design_guidelines import TAILWIND_FIRST_RULES, ANIMATION_PRINCIPLES

try:
    from backend.agents.artifact_store import write_html_artifact, write_json_artifact
except Exception:
    write_html_artifact = None
    write_json_artifact = None

# ── OpenUI ──────────────────────────────────────────────────────────────
OPENUI_URL = os.environ.get("OPENUI_URL") or os.environ.get("OPENUI_SERVICE_URL", "http://localhost:7878")
GENERATE_ENDPOINT = f"{OPENUI_URL}/generate"


# ── Archetype design systems ────────────────────────────────────────────
ARCHETYPE_DESIGN_SYSTEMS = {
    "industrial-bold": {
        "heading_font": "Bebas Neue",
        "body_font": "Space Grotesk",
        "border_radius": "0px",
        "heading_align": "left",
        "card_style": "sharp-border",
        "spacing_tight": True,
        "palette_bias": {"bg": "#0a0a0a", "surface": "#1a1a1a", "accent": "#ff3b00"},
    },
    "editorial-asymmetric": {
        "heading_font": "Playfair Display",
        "body_font": "Inter",
        "border_radius": "8px",
        "heading_align": "left",
        "card_style": "shadow-elevated",
        "spacing_tight": False,
        "palette_bias": {"bg": "#fafafa", "surface": "#ffffff", "accent": "#1a1a1a"},
    },
    "apple-minimalist": {
        "heading_font": "SF Pro Display",
        "body_font": "SF Pro Text",
        "border_radius": "16px",
        "heading_align": "center",
        "card_style": "glass-subtle",
        "spacing_tight": False,
        "palette_bias": {"bg": "#fbfbfd", "surface": "#ffffff", "accent": "#0071e3"},
    },
    "dark-futurist": {
        "heading_font": "Orbitron",
        "body_font": "Exo 2",
        "border_radius": "12px",
        "heading_align": "center",
        "card_style": "glass-neon",
        "spacing_tight": True,
        "palette_bias": {"bg": "#0a0a14", "surface": "#12122a", "accent": "#00f0ff"},
    },
    "organic-warm": {
        "heading_font": "DM Serif Display",
        "body_font": "DM Sans",
        "border_radius": "24px",
        "heading_align": "left",
        "card_style": "soft-shadow",
        "spacing_tight": False,
        "palette_bias": {"bg": "#fdf8f3", "surface": "#fff9f0", "accent": "#8b5e3c"},
    },
    "corporate-trust": {
        "heading_font": "Source Serif 4",
        "body_font": "Source Sans 3",
        "border_radius": "4px",
        "heading_align": "left",
        "card_style": "bordered",
        "spacing_tight": True,
        "palette_bias": {"bg": "#ffffff", "surface": "#f5f7fa", "accent": "#1a56db"},
    },
}


def _get_archetype_design_system(archetype: str) -> dict:
    return ARCHETYPE_DESIGN_SYSTEMS.get(archetype, ARCHETYPE_DESIGN_SYSTEMS["editorial-asymmetric"])


# ── Resultado ──────────────────────────────────────────────────────────
class BuildResult:
    __slots__ = ("html", "model", "success", "error")
    def __init__(self, html="", model="", success=False, error=""):
        self.html = html
        self.model = model
        self.success = success
        self.error = error


# ── Helpers ─────────────────────────────────────────────────────────────
def _artifact_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-") or "section"


def _first_non_empty(*values):
    for v in values:
        s = str(v or "").strip()
        if s:
            return s
    return ""


def _looks_like_valid_body_fragment(html: str) -> tuple[bool, str]:
    if not html or len(html.strip()) < 200:
        return False, "html vazio ou muito pequeno"
    lower = html.lower()
    has_section = "<section" in lower
    has_content = "<h1" in lower or "<h2" in lower or "<p" in lower
    if not has_section or not has_content:
        return False, "sem section ou heading visível"
    return True, ""


def _extract_body_only(html: str) -> str:
    html = re.sub(r"(?is)<head\b[^>]*>.*?(?:</head\s*>|(?=<body\b))", "", html, flags=re.DOTALL)
    html = re.sub(r"(?is)</?body\b[^>]*>", "", html)
    return html.strip()


def _pin_footer_last(html: str) -> str:
    """Garante que <footer> ou <section id="footer"> seja a última seção visível antes de </body>.

    Se o LLM posicionar seções (contato, sobre, CTA) após o footer,
    esta função as move para ANTES do footer, mantendo a ordem original.
    """
    lower = html.lower()
    if "</body>" not in lower:
        return html

    # Match tanto <footer> quanto <section id="footer">
    footer_match = re.search(
        r"(?is)(?:<footer\b[^>]*>|<section\b[^>]*id=['\"]footer['\"][^>]*>)(.*?)(?:</footer>|</section>)",
        html,
    )
    if not footer_match:
        return html

    footer_block = html[footer_match.start():footer_match.end()]

    # Remove footer da posição original
    html_no_footer = html[:footer_match.start()] + html[footer_match.end():]

    # Remove qualquer <section> que "vazou" para depois do footer (não deveria existir)
    html_no_footer = re.sub(
        r"(?is)(<section\b[^>]*>.*?</section>)",
        "",
        html_no_footer,
    )

    # Injeta footer imediatamente antes de </body>
    html_pinned = re.sub(
        r"(?is)(</body>)",
        footer_block + "\n" + r"\1",
        html_no_footer,
        count=1,
    )

    return html_pinned


def _ensure_shell_fonts(html: str, spec: dict) -> str:
    typography = spec.get("typography", {}) or {}
    heading = str(typography.get("heading", "Inter")).strip()
    body = str(typography.get("body", "Inter")).strip()

    def _normalize(family, fallback):
        normalized = re.sub(r"[^a-z0-9]+", "", family.lower())
        return {"ubermove": "Archivo Black", "ubermovetext": "Inter", "uber move": "Archivo Black", "uber move text": "Inter",
                "nouvelr": "Oswald"}.get(normalized, family or fallback)

    heading = _normalize(heading, "Inter")
    body = _normalize(body, "Inter")

    families = []
    for family in (heading, body):
        if not family or family.lower() in {"system-ui", "sans-serif", "serif", "monospace"}:
            continue
        encoded = quote_plus(family)
        if encoded.lower() == "inter":
            encoded = "Inter:wght@400;500;600;700;800;900"
        families.append(f"family={encoded}")
    if not families:
        families.append("family=Inter:wght@400;500;600;700;800;900")
    href = "https://fonts.googleapis.com/css2?" + "&".join(dict.fromkeys(families)) + "&display=swap"
    links = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'<link href="{href}" rel="stylesheet">'
    )
    return re.sub(r"(?is)</head>", links + "\n</head>", html, count=1)


def _google_fonts_href(typography: dict) -> str:
    heading = _normalize_web_font_family(
        str((typography or {}).get("heading") or "Archivo Black").strip(), "Archivo Black"
    )
    body = _normalize_web_font_family(
        str((typography or {}).get("body") or "Inter").strip(), "Inter"
    )
    families = []
    for family in (heading, body):
        if not family or family.lower() in {"system-ui", "sans-serif", "serif", "monospace"}:
            continue
        encoded = quote_plus(family)
        if encoded.lower() == "inter":
            encoded = "Inter:wght@400;500;600;700;800;900"
        families.append(f"family={encoded}")
    if not families:
        families.append("family=Inter:wght@400;500;600;700;800;900")
    return "https://fonts.googleapis.com/css2?" + "&".join(dict.fromkeys(families)) + "&display=swap"


def _normalize_web_font_family(family: str, fallback: str) -> str:
    raw = str(family or "").strip()
    if not raw:
        return fallback
    normalized = re.sub(r"[^a-z0-9]+", "", raw.lower())
    return {"ubermove": "Archivo Black", "ubermovetext": "Inter",
            "uber move": "Archivo Black", "uber move text": "Inter",
            "nouvelr": "Oswald"}.get(normalized, raw)


# ── Deterministic asset injection (brand tokens + AOS + Google Fonts) ──
def _inject_deterministic_assets(html: str, design_tokens: dict) -> str:
    if not html or "<html" not in html.lower():
        return html

    flat = dict(design_tokens or {})
    for nested_key in ("palette", "color_palette"):
        nested = flat.get(nested_key)
        if isinstance(nested, dict):
            for k, v in nested.items():
                if k.startswith("--"):
                    flat.setdefault(k[2:], v)
                else:
                    flat.setdefault(k, v)

    def _first(*candidates):
        for c in candidates:
            v = flat.get(c)
            if v:
                return str(v)
        return ""

    primary   = _first("primary", "--primary", "accent", "--accent") or "#2563eb"
    secondary = _first("secondary", "--secondary") or "#4b5563"
    accent    = _first("accent", "--accent", "primary", "--primary") or primary
    bg        = _first("background", "bg") or "#ffffff"
    surface   = _first("surface", "--surface") or "#f9fafb"
    text      = _first("text", "fg", "--fg") or "#111827"
    border    = _first("border", "--border") or "#e5e7eb"
    muted     = _first("muted", "--muted") or "#6b7280"
    radius    = _first("radius", "--radius", "border_radius") or "8px"
    heading_font = _first("heading_font", "--font-heading") or "Inter"
    body_font    = _first("body_font", "--font-body") or "Inter"

    brand_style = (
        '<style id="design-tokens">'
        f":root{{--bg:{bg};--surface:{surface};--foreground:{text};"
        f"--muted:{muted};--primary:{primary};--primary-fg:{text};"
        f"--border:{border};--radius:{radius};"
        f"--font-heading:{heading_font};--font-body:{body_font};"
        f"--brand-primary:{primary};--brand-secondary:{secondary};"
        f"--brand-accent:{accent};--brand-bg:{bg};--brand-surface:{surface};"
        f"--brand-text:{text};--brand-border:{border};--brand-muted:{muted};}}"
        "</style>"
    )
    aos_head = '<link rel="stylesheet" href="https://unpkg.com/aos@next/dist/aos.css" />'
    aos_body = (
        '<script src="https://unpkg.com/aos@next/dist/aos.js"></script>'
        '<script>document.addEventListener("DOMContentLoaded",function(){'
        "if(window.AOS){AOS.init({duration:700,once:true,offset:40});}"
        "});</script>"
    )
    html = re.sub(r"(?is)(</head>)", f"{brand_style}\n{aos_head}\n\\1", html, count=1)
    html = re.sub(r"(?is)(</body>)", f"{aos_body}\n\\1", html, count=1)
    if "</head>" not in html.lower():
        html = f"{brand_style}\n{aos_head}\n{html}"
    if "</body>" not in html.lower():
        html = f"{html}\n{aos_body}"
    return html


# ── Single-shot OpenUI call ─────────────────────────────────────────────
def _render_full_document(spec: dict, design_tokens: dict) -> tuple[str, str]:
    """Single OpenUI call returning the complete HTML document."""
    max_retries = 3
    retry_delays = [5, 15, 45]

    # Build a unified directive that says: "generate the COMPLETE HTML file, doctype to </html>"
    archetype_slug = getattr(spec.get("_prd"), "design_system_slug", None) or "editorial-asymmetric"
    archetype = _get_archetype_design_system(archetype_slug)
    archetype_briefing = (
        f"Estilo visual: {archetype_slug}. "
        f"Heading={archetype['heading_font']}, body={archetype['body_font']}, "
        f"border-radius={archetype['border_radius']}, card={archetype['card_style']}."
    )

    # Build full-document directive
    review_section_hint = ""
    rl = spec.get("reviews_list") or []
    if rl:
        review_section_hint = (
            f"Inclua seção 'depoimentos' com os {min(len(rl), 3)} reviews reais abaixo "
            f"(autor/nota/texto). NÃO invente depoimentos.\n"
            + "\n".join(
                f"- {r.get('author','?')} ({r.get('rating',0)}/5): {r.get('text','')[:120]}"
                for r in sorted(rl, key=lambda x: x.get("rating", 0), reverse=True)[:3]
            )
        )
    else:
        review_section_hint = "NÃO inclua seção de depoimentos — não há reviews reais."

    builder_directive = f"""
Landing page completa para {spec.get('business_name','')} ({spec.get('segmento','')}) em {spec.get('cidade','')}.
{_first_non_empty(spec.get('instrucao_criativa_para_dev'), '')}

Gere o documento HTML COMPLETO, de <!DOCTYPE html> até </html>, em um único bloco.
NÃO retorne fragmento. O HTML deve ser executável por si só.

{archetype_briefing}

DIRETRIZES:
{TAILWIND_FIRST_RULES.strip()}
{ANIMATION_PRINCIPLES.strip()}

ESTRUTURA OBRIGATÓRIA:
- <!DOCTYPE html><html lang="pt-BR"><head>... Google Fonts ...</head><body>
- 1 <main> raiz. 1 <h1> no hero. Seções com <section> e <h2>/<h3>.
- Hero com background image do Unsplash (URLs que começam com https://images.unsplash.com).
- Seções: hero → diferenciais/compromissos (3 cards) → depoimentos/comprovantes → planos (3 preços)
  → FAQ (details/summary) → contato (telefone + WhatsApp + endereço).
- FOOTER É A ÚLTIMA SEÇÃO — coloque o <footer> imediatamente antes de </body>.
  NENHUMA seção (contato, localização, sobre, CTA, depoimentos) pode aparecer APÓS o <footer>.
  A ordem final é: [seções de conteúdo] → <footer> → </body>.
- Use as fotos do lead quando houver; senão use Unsplash.

{review_section_hint}

SEO: title com nome do negócio + cidade. meta description persuasiva (≤160 chars).
Schema.org: LocalBusiness com nome, endereço, telefone, cidade.

PROIBIDO:
- NUNCA posicione texto decorativo sobre CTA ou dados de contato.
- NUNCA use `min-w-[Npx]` em grids ou cards.
- NUNCA invente depoimentos.
- NUNCA use `color:var(--fg)` sobre fundo escurecido — use `text-white`.

TELEFONE: {spec.get('phone','')}
ENDEREÇO: {spec.get('address','')}
HORÁRIO: {spec.get('hours',{}) or {}}
""".strip()

    # Build lean spec payload — only fields the LLM needs
    lean_spec = {
        "_render_hint": "full_document",
        "business_name": spec.get("business_name"),
        "segmento": spec.get("segmento"),
        "cidade": spec.get("cidade"),
        "builder_directive": builder_directive,
        "design_tokens": design_tokens,
        "typography": spec.get("typography") or {},
        "color_palette": spec.get("color_palette") or {},
        "reviews_count": spec.get("reviews_count", 0),
        "reviews_rating": spec.get("reviews_rating", 0.0),
        "reviews_list": rl[:3],
        "address": spec.get("address", ""),
        "phone": spec.get("phone", ""),
        "hours": spec.get("hours") or {},
        "photos": (spec.get("photos") or [])[:6],
        "google_maps_embed": spec.get("google_maps_embed", ""),
        "faqs": spec.get("faqs") or [],
        "seo_keywords": spec.get("seo_keywords") or [],
        "ctas": spec.get("ctas") or [],
        "value_props": spec.get("value_props") or [],
        "dark_mode": spec.get("dark_mode", False),
        "schema_org_types": spec.get("schema_org_types") or ["LocalBusiness"],
        "anti_patterns": spec.get("anti_patterns") or [],
    }

    last_error = ""
    for attempt in range(max_retries):
        try:
            if last_error:
                lean_spec["_repair_feedback"] = (
                    f"Tentativa anterior inválida: {last_error}. "
                    "Gere o HTML completo, válido, de <!DOCTYPE até </html>."
                )
            payload = {"designerPRD": lean_spec}
            if _builder_logger:
                _builder_logger.info(
                    "[builder] full-document OpenUI call attempt={}/{} business={}",
                    attempt + 1, max_retries, spec.get("business_name"),
                )
            resp = requests.post(
                GENERATE_ENDPOINT,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120,
            )
            if resp.status_code == 200:
                data = resp.json()
                html = data.get("html", "")
                model = data.get("model", "")
                if _builder_logger:
                    _builder_logger.info(
                        "[builder] full-document OpenUI OK bytes={} model={}",
                        len(html), model,
                    )
                return html, model
            if resp.status_code in (529, 503) or (
                resp.status_code == 500
                and any(m in resp.text.lower() for m in ("529", "overloaded", "sobrecarregado", "503", "provider_error"))
            ):
                last_error = f"OpenUI overloaded: HTTP {resp.status_code}"
                if _builder_logger:
                    _builder_logger.warning("[builder] full-document overloaded attempt={}/{}", attempt + 1, max_retries)
                if attempt < max_retries - 1:
                    time.sleep(retry_delays[attempt])
                    continue
                return "", ""
            last_error = f"OpenUI HTTP {resp.status_code}: {resp.text[:200]}"
            if _builder_logger:
                _builder_logger.warning("[builder] full-document HTTP {}: {}", resp.status_code, resp.text[:200])
            return "", ""
        except requests.exceptions.Timeout:
            last_error = f"OpenUI timeout attempt {attempt + 1}"
            if _builder_logger:
                _builder_logger.warning("[builder] full-document timeout attempt={}/{}", attempt + 1, max_retries)
            if attempt < max_retries - 1:
                time.sleep(retry_delays[attempt])
                continue
            return "", ""
        except Exception as e:
            last_error = f"OpenUI error: {str(e)}"
            if _builder_logger:
                _builder_logger.error("[builder] full-document error: {}", e)
            return "", ""

    if _builder_logger:
        _builder_logger.error("[builder] full-document failed after {} retries causa={}", max_retries, last_error)
    return "", ""


# ── _prd_to_spec: converte DesignerPRD para dict enxuto ────────────────
def _prd_to_spec(prd) -> dict:
    """Converts DesignerPRD to a lean spec dict for single-shot generation."""
    design_tokens = {}
    design_system_slug = getattr(prd, "design_system_slug", None) or "editorial-asymmetric"
    archetype = _get_archetype_design_system(design_system_slug)

    # Flatten archetype tokens
    design_tokens.update(archetype.get("palette_bias", {}))

    # Merge color_palette (ColorPalette model)
    try:
        cp = prd.color_palette
        if hasattr(cp, "model_dump"):
            cp_dict = cp.model_dump()
        elif hasattr(cp, "dict"):
            cp_dict = cp.dict()
        else:
            cp_dict = {}
        # Skip reasoning-only entries
        for k, v in cp_dict.items():
            if k in {"reasoning", "harmony_score", "accessibility_rating"}:
                continue
            if isinstance(v, str) and v.startswith("#"):
                design_tokens[k] = v
    except Exception:
        pass

    # Flatten nested palette from visual_dna
    visual_dna = getattr(prd, "visual_dna", {}) or {}
    palette_src = visual_dna.get("palette") or visual_dna.get("color_palette") or {}
    if isinstance(palette_src, dict):
        for k, v in palette_src.items():
            if k.startswith("--"):
                design_tokens[k[2:]] = v
            else:
                design_tokens[k] = v

    # Typography
    typography = getattr(prd, "typography", None) or {}
    if isinstance(typography, str):
        try:
            import json
            typography = json.loads(typography)
        except Exception:
            typography = {}
    design_tokens["heading_font"] = typography.get("heading", archetype["heading_font"])
    design_tokens["body_font"] = typography.get("body", archetype["body_font"])
    design_tokens["radius"] = typography.get("border_radius", archetype["border_radius"])

    # ─── PALETTE ROTATION POR LEAD (FRA-LIB 2026-08-17) ────────────────────────
    # Sobrescreve tokens de cor com a paleta rotacionada do design_context.
    # Se get_design_context falhar, mantém os tokens do archetype (fallback seguro).
    _seg = getattr(prd, "segmento", "") or ""
    _nome = getattr(prd, "business_name", "") or ""
    try:
        from agents.design_context import get_design_context as _gdc
        _ctx = _gdc(_seg, _nome, getattr(prd, "tier", "STANDARD") or "STANDARD", False)
        _ctx_tokens = _ctx.get("tokens", {}) if isinstance(_ctx, dict) else {}
        for _tk, _tv in _ctx_tokens.items():
            if _tk.startswith("--"):
                _flat = _tk[2:]
            else:
                _flat = _tk
            design_tokens[_flat] = _tv
    except Exception:
        pass  # fallback: mantém tokens do archetype

    # Photos
    photos = getattr(prd, "photos", None) or []
    if isinstance(photos, str):
        try:
            import json
            photos = json.loads(photos)
        except Exception:
            photos = []

    # Media plan (for Unsplash fallback)
    media_plan = getattr(prd, "media_plan", None) or []
    if isinstance(media_plan, str):
        try:
            import json
            media_plan = json.loads(media_plan)
        except Exception:
            media_plan = []
    for item in media_plan:
        if isinstance(item, dict) and item.get("url"):
            url = item["url"]
            if url.startswith("https://images.unsplash.com") and url not in photos:
                photos.append(url)

    # Animations / motion directives
    animations = getattr(prd, "animations", None) or []
    if isinstance(animations, str):
        try:
            import json
            animations = json.loads(animations)
        except Exception:
            animations = []

    motion_directives = {
        "aos": True,
        "duration": "700ms",
        "once": True,
        "offset": 40,
        "animations": [
            {
                "name": getattr(a, "name", a.get("name", "fade-up")) if hasattr(a, "name") else a.get("name", "fade-up"),
                "type": getattr(a, "type", a.get("type", "fade-up")) if hasattr(a, "type") else a.get("type", "fade-up"),
                "duration": getattr(a, "duration", a.get("duration", "700ms")) if hasattr(a, "duration") else a.get("duration", "700ms"),
            }
            for a in animations[:5]
        ],
    }

    # Sections from PRD
    sections = getattr(prd, "sections", None) or []
    if isinstance(sections, str):
        try:
            import json
            sections = json.loads(sections)
        except Exception:
            sections = []

    # FAQ
    faqs = getattr(prd, "faq_questions", None) or []
    if isinstance(faqs, str):
        try:
            import json
            faqs = json.loads(faqs)
        except Exception:
            faqs = []

    # SEO keywords
    seo_keywords = getattr(prd, "seo_keywords", None) or []
    if isinstance(seo_keywords, str):
        try:
            import json
            seo_keywords = json.loads(seo_keywords)
        except Exception:
            seo_keywords = []

    # Reviews
    reviews_list = getattr(prd, "reviews_list", None) or []
    if isinstance(reviews_list, str):
        try:
            import json
            reviews_list = json.loads(reviews_list)
        except Exception:
            reviews_list = []

    # Value props
    value_props = getattr(prd, "value_props", None) or []
    if isinstance(value_props, str):
        try:
            import json
            value_props = json.loads(value_props)
        except Exception:
            value_props = []

    # CTAs
    ctas = getattr(prd, "ctas", None) or []
    if isinstance(ctas, str):
        try:
            import json
            ctas = json.loads(ctas)
        except Exception:
            ctas = []

    # Google Maps embed
    google_maps_embed = getattr(prd, "google_maps_embed", "") or ""

    # Hours
    hours = getattr(prd, "hours", None) or {}
    if isinstance(hours, str):
        try:
            import json
            hours = json.loads(hours)
        except Exception:
            hours = {}

    spec = {
        "_prd": prd,
        "business_name": getattr(prd, "business_name", None),
        "segmento": getattr(prd, "segmento", None),
        "cidade": getattr(prd, "cidade", None),
        "sections": sections,
        "design_tokens": design_tokens,
        "typography": typography,
        "color_palette": design_tokens.get("palette", {}),
        "design_system_slug": design_system_slug,
        "layout_dna": getattr(prd, "layout_dna", {}) or {},
        "design_system": archetype,
        "motion_directives": motion_directives,
        "animations": animations,
        "reviews_count": getattr(prd, "reviews_count", None) or len(reviews_list),
        "reviews_rating": getattr(prd, "reviews_rating", None) or 0.0,
        "reviews_list": reviews_list,
        "address": getattr(prd, "address", "") or "",
        "phone": getattr(prd, "phone", "") or "",
        "hours": hours,
        "photos": photos[:8],
        "videos": getattr(prd, "videos", None) or [],
        "logo_url": getattr(prd, "logo_url", None),
        "google_maps_embed": google_maps_embed,
        "components_21dev": getattr(prd, "components_21dev", None) or [],
        "seo_keywords": seo_keywords,
        "faqs": faqs,
        "ctas": ctas,
        "value_props": value_props,
        "geo": getattr(prd, "geo", None) or {},
        "dark_mode": getattr(prd, "dark_mode", None) or False,
        "instrucao_criativa_para_dev": getattr(prd, "instrucao_criativa_para_dev", None) or "",
        "anti_patterns": getattr(prd, "anti_patterns", None) or [],
        "schema_org_types": getattr(prd, "schema_org_types", None) or ["LocalBusiness"],
        "site_build_plan": getattr(prd, "site_build_plan", None) or {},
        "requirements_contract": getattr(prd, "requirements_contract", None) or {},
        "media_plan": media_plan,
        "competitor_analysis": getattr(prd, "competitor_analysis", None) or "",
        "visual_dna": visual_dna,
        "creative_direction": getattr(prd, "creative_direction", None) or {},
        "niche_brief": getattr(prd, "niche_brief", None) or {},
        "variation_blueprint": getattr(prd, "variation_blueprint", None) or {},
    }

    # Sanitize footer section (evita 'NÚ QUE...' do chunked merge)
    _f = next((s for s in sections if isinstance(s, dict) and str(s.get("name", "")).strip().lower() == "footer"), None)
    if _f and not (_f.get("copy") or _f.get("content") or _f.get("text")):
        _f["copy"] = spec.get("business_name", "") or ""
        _f["content"] = {"name": "footer", "business_name": spec.get("business_name", "")}

    return spec


# ── Public API: render_site ─────────────────────────────────────────────
def render_site(prd, usar_llm: bool = True) -> BuildResult:
    """Generate the COMPLETE HTML site via single OpenUI call (LEAN PIPELINE)."""
    if not usar_llm:
        return BuildResult(html="", model="", success=False, error="Template fallback not implemented (lean pipeline)")

    # Convert PRD to lean spec
    spec = _prd_to_spec(prd)
    spec["_run_id"] = getattr(prd, "_run_id", "") or ""
    spec["_lead_id"] = getattr(prd, "_lead_id", "") or ""
    _lead_data = getattr(prd, "_lead_data", None) or {}
    spec["_lead_name"] = _lead_data.get("nome", "") if isinstance(_lead_data, dict) else ""

    try:
        _write_builder_spec_artifacts(spec)
    except Exception as exc:
        if _builder_logger:
            _builder_logger.warning("[builder] artifact spec falhou err={}", exc)

    design_tokens = spec.get("design_tokens", {}) or {}
    t0 = time.time()
    html, model = _render_full_document(spec, design_tokens)
    elapsed = time.time() - t0

    if not html:
        return BuildResult(
            html="",
            model=model,
            success=False,
            error="Falha ao gerar HTML single-shot no OpenUI",
        )

    # Post-processing: Google Fonts + brand tokens + AOS + footer pin
    html = _ensure_shell_fonts(html, spec)
    html = _inject_deterministic_assets(html, design_tokens)
    html = _pin_footer_last(html)

    if _builder_logger:
        _builder_logger.info(
            "[builder] LEAN single-shot OK bytes={} model={} time={:.1f}s",
            len(html), model, elapsed,
        )

    try:
        if write_html_artifact:
            write_html_artifact(
                run_id=spec["_run_id"],
                lead_id=spec["_lead_id"],
                lead_name=spec["_lead_name"],
                filename="builder/final_html/99-final-document.html",
                html=html,
                metadata={
                    "step": "builder",
                    "artifact_type": "final_document",
                    "model": model,
                    "elapsed_seconds": round(elapsed, 2),
                    "pipeline": "lean_single_shot",
                },
            )
        from backend.agents.llm_direct import _registrar_uso_completo
        _registrar_uso_completo(
            model_id=model or "openui-unknown",
            input_tokens=0,
            output_tokens=len(html) // 4,
            agent_name="builder_openui_lean",
            provider="openui",
        )
    except Exception as e:
        if _builder_logger:
            _builder_logger.warning("[builder] tracking falhou lean err={}", e)

    return BuildResult(html=html, model=model, success=True)


# ── Artifact helper (reused from previous builder) ─────────────────────
def _write_builder_spec_artifacts(spec: dict) -> None:
    try:
        if write_json_artifact:
            payload = {k: v for k, v in spec.items() if k != "_prd"}
            write_json_artifact(
                run_id=str(spec.get("_run_id") or "no-run"),
                lead_id=str(spec.get("_lead_id") or "no-lead"),
                lead_name=str(spec.get("_lead_name") or ""),
                filename="builder/openui_payload/00-openui-payload.json",
                payload=payload,
                metadata={"step": "builder", "artifact_type": "openui_payload"},
            )
    except Exception as exc:
        if _builder_logger:
            _builder_logger.warning("[builder] artifact spec falhou err={}", exc)


def _wait_for_openui(max_wait: int = 30) -> bool:
    """Poll OpenUI /generate endpoint until ready or timeout."""
    import time as _t
    deadline = _t.time() + max_wait
    while _t.time() < deadline:
        try:
            r = requests.post(GENERATE_ENDPOINT, json={"test": "ping"}, timeout=5)
            if r.status_code in (200, 422):  # 422 = validation error, but endpoint is up
                return True
        except Exception:
            pass
        _t.sleep(2)
    return False
