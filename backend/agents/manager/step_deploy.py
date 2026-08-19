"""Step: Deploy — Fase 6: Publica site em sites/<tenant>/<lead_id>/index.html."""
import logging
import os
import json
import re
import html as html_lib
import unicodedata
from pathlib import Path
from urllib.parse import quote_plus
from datetime import datetime
from backend.agents.manager.states import (
    PipelineState, STATE_PUBLISHING, STATE_OUTREACH, STATE_FAILED,
    _transition, _log_step_error, _record_agent_handoff,
)
from backend.core.knowledge_journal import record as journal_record

logger = logging.getLogger("manager.pipeline")

_DECORATIVE_CLASS_RE = re.compile(
    r"(watermark|bg-text|background-text|floating-text|decorative|ornament|stamp|marca-d-agua)",
    re.IGNORECASE,
)

_DEPLOY_VISUAL_GUARD_CSS = """
<style data-fralib-deploy-guard>
main [class*="watermark"],
main [class*="bg-text"],
main [class*="background-text"],
main [class*="floating-text"],
main [class*="decorative"],
main [class*="ornament"] {
  pointer-events: none;
  max-width: 100%;
}
main .fralib-relative-guard {
  position: relative !important;
  overflow: hidden !important;
}
</style>
"""


def _is_placeholder_phone(value: str) -> bool:
    digits = re.sub(r"\D+", "", str(value or ""))
    return digits in {"4199999999", "41999999999", "5541999999999", "11999999999", "5511999999999"}


_FONT_FAMILY_ALIASES = {
    "ubermove": "Archivo Black",
    "ubermovetext": "Inter",
    "uber move": "Archivo Black",
    "uber move text": "Inter",
    "nouvelr": "Oswald",
}


def _normalize_web_font_family(family: str, fallback: str) -> str:
    raw = str(family or "").strip()
    if not raw:
        return fallback
    normalized = re.sub(r"[^a-z0-9]+", "", raw.lower())
    return _FONT_FAMILY_ALIASES.get(normalized, raw)


def _google_fonts_href(typography: dict) -> str:
    heading = _normalize_web_font_family(str((typography or {}).get("heading") or "Archivo Black").strip(), "Archivo Black")
    body = _normalize_web_font_family(str((typography or {}).get("body") or "Inter").strip(), "Inter")
    families: list[str] = []
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


def _enforce_final_font_contract(html: str, state: PipelineState) -> str:
    cleaned = html or ""
    typography = (
        (state.design_output or {}).get("typography")
        or (state.designer_prd or {}).get("typography")
        or {}
    )
    if str(state.segmento or "").strip().lower() == "academia":
        typography = {
            "heading": typography.get("heading") or "Archivo Black",
            "body": typography.get("body") or "Inter",
        }
    href = _google_fonts_href(typography)
    font_links = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'<link href="{href}" rel="stylesheet">'
    )
    cleaned = re.sub(
        r'(?is)<link\b[^>]*href=["\']https://fonts\.googleapis\.com/[^"\']+["\'][^>]*>\s*',
        "",
        cleaned,
    )
    cleaned = re.sub(
        r'(?is)<link\b[^>]*href=["\']https://fonts\.gstatic\.com/[^"\']+["\'][^>]*>\s*',
        "",
        cleaned,
    )
    cleaned = re.sub(
        r'(?is)<link\b[^>]*rel=["\']preconnect["\'][^>]*href=["\']https://fonts\.googleapis\.com["\'][^>]*>\s*',
        "",
        cleaned,
    )
    cleaned = re.sub(
        r'(?is)<link\b[^>]*rel=["\']preconnect["\'][^>]*href=["\']https://fonts\.gstatic\.com["\'][^>]*>\s*',
        "",
        cleaned,
    )
    return re.sub(r"(?is)</head>", font_links + "\n</head>", cleaned, count=1)


def _lookup_inventory_contact(lead_id: str) -> str:
    if not lead_id:
        return ""
    try:
        from backend.core.database import SessionLocal
        from sqlalchemy import text as _sql

        with SessionLocal() as db:
            row = db.execute(
                _sql(
                    """
                    SELECT
                        coalesce(
                            nullif(telefone, ''),
                            nullif(whatsapp, ''),
                            nullif(dados->>'telefone', ''),
                            nullif(dados->>'whatsapp', '')
                        ) AS phone
                    FROM lead_inventory
                    WHERE lead_id = :lead_id
                    ORDER BY atualizado_em DESC NULLS LAST, criado_em DESC NULLS LAST, id DESC
                    LIMIT 1
                    """
                ),
                {"lead_id": lead_id},
            ).fetchone()
        if not row:
            return ""
        phone = row[0] if isinstance(row, (tuple, list)) else getattr(row, "phone", "")
        return str(phone or "").strip()
    except Exception as exc:
        logger.warning("[Deploy] lookup de contato no inventory falhou (lead=%s): %s", lead_id, exc)
        return ""


def _resolve_real_phone(state: PipelineState) -> str:
    raw_phone = (
        (state.design_output or {}).get("phone")
        or (state.lead_data or {}).get("telefone")
        or (state.lead_data or {}).get("whatsapp")
        or ""
    )
    if _is_placeholder_phone(raw_phone) or not str(raw_phone or "").strip():
        inventory_phone = _lookup_inventory_contact(str(state.lead_id or ""))
        if inventory_phone and not _is_placeholder_phone(inventory_phone):
            raw_phone = inventory_phone
    if _is_placeholder_phone(raw_phone):
        return ""
    return str(raw_phone or "").strip()


def _sanitize_html_document_structure(html: str) -> str:
    body_start = re.search(r"<body[^>]*>", html, re.IGNORECASE)
    body_ends = list(re.finditer(r"</body>", html, re.IGNORECASE))
    if not body_start or not body_ends:
        return html

    body_end = body_ends[-1]
    body_content = html[body_start.end():body_end.start()]
    body_content = re.sub(r"<!DOCTYPE[^>]*>", "", body_content, flags=re.IGNORECASE)
    body_content = re.sub(r"</?html[^>]*>", "", body_content, flags=re.IGNORECASE)
    body_content = re.sub(r"<head[^>]*>.*?</head>", "", body_content, flags=re.IGNORECASE | re.DOTALL)
    body_content = re.sub(r"<title[^>]*>.*?</title>", "", body_content, flags=re.IGNORECASE | re.DOTALL)
    body_content = re.sub(r"<meta\b[^>]*>", "", body_content, flags=re.IGNORECASE)
    body_content = re.sub(r"<link\b[^>]*>", "", body_content, flags=re.IGNORECASE)
    body_content = re.sub(r"</?head[^>]*>", "", body_content, flags=re.IGNORECASE)
    body_content = re.sub(r"</?body[^>]*>", "", body_content, flags=re.IGNORECASE)

    return html[:body_start.end()] + "\n" + body_content.strip() + "\n" + html[body_end.start():]


def _sanitize_corrupted_svg_paths(html: str) -> str:
    unterminated_path_re = re.compile(
        r"(?P<prefix><path\b[^>]*\bd\s*=\s*)(?P<q>['\"])(?P<value>[^<>]*?)(?=<(?:main|section|header|footer|article|aside|div)\b)",
        re.IGNORECASE | re.DOTALL,
    )

    def _close_unterminated_path(match: re.Match) -> str:
        return (
            f'{match.group("prefix")}{match.group("q")}'
            f'{match.group("value").strip()}{match.group("q")}></path>\n'
        )

    html = unterminated_path_re.sub(_close_unterminated_path, html)

    path_re = re.compile(
        r"(<path\b[^>]*\bd\s*=\s*)(?P<q>['\"])(?P<value>.*?)(?P=q)",
        re.IGNORECASE | re.DOTALL,
    )

    def _replace(match: re.Match) -> str:
        value = match.group("value")
        if "<" not in value and ">" not in value:
            return match.group(0)
        safe_value = value.split("<", 1)[0].strip()
        return f'{match.group(1)}{match.group("q")}{safe_value}{match.group("q")}'

    return path_re.sub(_replace, html)


def _close_broken_inline_wrappers_before_sections(html: str) -> str:
    html = re.sub(
        r'(?is)(<a\b[^>]*>\s*<svg\b[^>]*>\s*<path\b[^>]*></path>)\s*(?=<section\b)',
        r'\1</svg></a>',
        html,
    )
    html = re.sub(
        r'(?is)(<button\b[^>]*>\s*<svg\b[^>]*>\s*<path\b[^>]*></path>)\s*(?=<section\b)',
        r'\1</svg></button>',
        html,
    )
    section_re = re.compile(r"(?i)<section\b")
    anchor_open_re = re.compile(r"(?i)<a\b")
    anchor_close_re = re.compile(r"(?i)</a>")
    button_open_re = re.compile(r"(?i)<button\b")
    button_close_re = re.compile(r"(?i)</button>")
    svg_open_re = re.compile(r"(?i)<svg\b")
    svg_close_re = re.compile(r"(?i)</svg>")

    fixed_parts: list[str] = []
    cursor = 0
    for match in section_re.finditer(html):
        fixed_parts.append(html[cursor:match.start()])
        assembled = "".join(fixed_parts)
        needs_anchor_close = len(anchor_open_re.findall(assembled)) > len(anchor_close_re.findall(assembled))
        needs_button_close = len(button_open_re.findall(assembled)) > len(button_close_re.findall(assembled))
        needs_svg_close = len(svg_open_re.findall(assembled)) > len(svg_close_re.findall(assembled))

        if needs_anchor_close or needs_button_close:
            closures: list[str] = []
            if needs_svg_close:
                closures.append("</svg>")
            if needs_anchor_close:
                closures.append("</a>")
            if needs_button_close:
                closures.append("</button>")
            fixed_parts.append("".join(closures))

        fixed_parts.append(match.group(0))
        cursor = match.end()

    fixed_parts.append(html[cursor:])
    return "".join(fixed_parts)


def _demote_secondary_tag(html: str, original_tag: str, replacement_tag: str) -> str:
    tag_re = re.compile(f"<(/?){re.escape(original_tag)}\\b([^>]*)>", re.IGNORECASE)
    open_seen = 0
    close_budget = 0

    def _replace(match: re.Match) -> str:
        nonlocal open_seen, close_budget
        is_closing = bool(match.group(1))
        attrs = match.group(2) or ""
        if not is_closing:
            open_seen += 1
            if open_seen == 1:
                close_budget += 1
                return match.group(0)
            return f"<{replacement_tag}{attrs}>"
        if close_budget > 0:
            close_budget -= 1
            return match.group(0)
        return f"</{replacement_tag}>"

    return tag_re.sub(_replace, html)


def _inject_head_guard_css(html: str) -> str:
    if "data-fralib-deploy-guard" in html:
        return html
    head_close = re.search(r"</head>", html, re.IGNORECASE)
    if head_close:
        return html[:head_close.start()] + _DEPLOY_VISUAL_GUARD_CSS + "\n" + html[head_close.start():]
    body_open = re.search(r"<body[^>]*>", html, re.IGNORECASE)
    if body_open:
        return html[:body_open.end()] + "\n" + _DEPLOY_VISUAL_GUARD_CSS + "\n" + html[body_open.end():]
    return _DEPLOY_VISUAL_GUARD_CSS + "\n" + html


def _guard_decorative_absolute_blocks(html: str) -> str:
    pattern = re.compile(
        r"<(?P<tag>div|section|aside)\b(?P<attrs>[^>]*)class=(?P<q>['\"])(?P<classname>[^'\"]+)(?P=q)(?P<rest>[^>]*)>(?P<inner>.*?)</(?P=tag)>",
        re.IGNORECASE | re.DOTALL,
    )

    def _replace(match: re.Match) -> str:
        classes = match.group("classname")
        attrs = (match.group("attrs") or "") + (match.group("rest") or "")
        if not _DECORATIVE_CLASS_RE.search(classes):
            return match.group(0)
        style_match = re.search(r"style=(['\"])(.*?)\1", attrs, re.IGNORECASE | re.DOTALL)
        style_text = style_match.group(2) if style_match else ""
        if "position:absolute" not in re.sub(r"\s+", "", style_text).lower():
            return match.group(0)
        if "fralib-relative-guard" in classes:
            return match.group(0)
        return f'<div class="fralib-relative-guard">{match.group(0)}</div>'

    return pattern.sub(_replace, html)


def _flatten_dense_circular_panels(html: str) -> str:
    pattern = re.compile(
        r"<(?P<tag>div|section|aside)\b(?P<before>[^>]*)class=(?P<q>['\"])(?P<classname>[^'\"]+)(?P=q)(?P<after>[^>]*)>(?P<inner>.*?)</(?P=tag)>",
        re.IGNORECASE | re.DOTALL,
    )

    def _replace(match: re.Match) -> str:
        classes = match.group("classname")
        normalized_classes = re.sub(r"\s+", " ", classes).strip()
        if "rounded-full" not in normalized_classes and "aspect-square" not in normalized_classes:
            return match.group(0)

        inner = match.group("inner") or ""
        text_only = re.sub(r"(?is)<[^>]+>", " ", inner)
        text_only = re.sub(r"\s+", " ", text_only).strip()
        has_dense_copy = len(text_only) > 80
        has_interactive_group = bool(re.search(r"(?is)<(?:a|button)\b", inner))
        if not has_dense_copy and not has_interactive_group:
            return match.group(0)

        before = match.group("before") or ""
        after = match.group("after") or ""
        attrs = before + after
        updated_classes = normalized_classes.replace("rounded-full", "rounded-3xl")
        updated_classes = re.sub(r"\baspect-square\b", "", updated_classes)
        updated_classes = re.sub(r"\s+", " ", updated_classes).strip()

        style_match = re.search(r"style=(['\"])(.*?)\1", attrs, re.IGNORECASE | re.DOTALL)
        extra_style = "width:min(100%,32rem);height:auto;aspect-ratio:auto;border-radius:2rem;"
        if style_match:
            current_style = style_match.group(2)
            new_style = current_style.rstrip(";") + ";" + extra_style
            attrs = attrs.replace(style_match.group(0), f'style="{new_style}"', 1)
        else:
            attrs += f' style="{extra_style}"'

        attrs = re.sub(
            r'class=(["\']).*?\1',
            f'class="{updated_classes}"',
            attrs,
            count=1,
            flags=re.IGNORECASE | re.DOTALL,
        )
        return f'<{match.group("tag")}{attrs}>{inner}</{match.group("tag")}>'

    return pattern.sub(_replace, html)


def _normalize_single_main_and_h1(html: str) -> str:
    html = _demote_secondary_tag(html, "main", "section")
    html = _demote_secondary_tag(html, "h1", "h2")
    return html


def _sanitize_deploy_html(html: str) -> str:
    html = _sanitize_html_document_structure(html)
    html = _sanitize_corrupted_svg_paths(html)
    html = _close_broken_inline_wrappers_before_sections(html)
    html = _normalize_single_main_and_h1(html)
    html = _guard_decorative_absolute_blocks(html)
    html = _flatten_dense_circular_panels(html)
    html = _inject_head_guard_css(html)
    return html


def _ensure_final_document_contract(html: str, state: PipelineState, canonical_url: str) -> str:
    """Última garantia documental, aplicada após todos os pós-processadores."""
    cleaned = html or ""
    cleaned = _enforce_final_font_contract(cleaned, state)
    name = html_lib.escape(str((state.lead_data or {}).get("nome") or "Negócio local"), quote=True)
    city = html_lib.escape(str(state.cidade or ""), quote=True)
    address = html_lib.escape(str((state.lead_data or {}).get("endereco") or ""), quote=True)
    raw_phone = _resolve_real_phone(state)
    phone = html_lib.escape(str(raw_phone), quote=True)
    photos = (state.design_output or {}).get("photos") or []
    if not photos:
        try:
            from backend.agents.unsplash_fetcher import buscar_fotos_unsplash
            photos = buscar_fotos_unsplash(
                segmento=state.segmento,
                quantidade=6,
                nome=(state.lead_data or {}).get("nome", ""),
                cidade=state.cidade,
            )
        except Exception as exc:
            logger.warning("[Deploy] restauração de mídia falhou: %s", exc)
    og_image = photos[0].get("url") if photos and isinstance(photos[0], dict) else (photos[0] if photos else "")
    title = f"{name} em {city}".strip()
    description = f"Conheça {name} em {city}: serviços, localização e contato oficial."

    if re.search(r"(?is)<title>\s*</title>", cleaned):
        cleaned = re.sub(r"(?is)<title>.*?</title>", f"<title>{title}</title>", cleaned, count=1)
    elif "<title" not in cleaned.lower():
        cleaned = re.sub(r"(?is)</head>", f"<title>{title}</title>\n</head>", cleaned, count=1)
    if re.search(r'(?is)<meta\s+name=["\']description["\'][^>]*>', cleaned):
        cleaned = re.sub(r'(?is)<meta\s+name=["\']description["\'][^>]*>', f'<meta name="description" content="{description}">', cleaned, count=1)

    head = [
        f'<link rel="canonical" href="{canonical_url}">',
        '<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 64 64%22><rect width=%2264%22 height=%2264%22 rx=%2214%22 fill=%22%23111827%22/><path d=%22M18 46V18h28v8H28v4h14v8H28v8z%22 fill=%22white%22/></svg>">',
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:description" content="{description}">',
        f'<meta property="og:url" content="{canonical_url}">',
        '<meta property="og:type" content="website">',
    ]
    if og_image:
        head.append(f'<meta property="og:image" content="{html_lib.escape(str(og_image), quote=True)}">')
    schema = {
        "@context": "https://schema.org", "@type": "LocalBusiness", "name": name,
        "url": canonical_url, "address": address or city, "telephone": phone,
    }
    head.append('<script type="application/ld+json">' + json.dumps({k: v for k, v in schema.items() if v}, ensure_ascii=False) + '</script>')
    cleaned = re.sub(r"(?is)</head>", "\n".join(head) + "\n</head>", cleaned, count=1)

    if phone:
        visible_phone = html_lib.unescape(phone)
        digits = re.sub(r"\D+", "", visible_phone)
        cleaned = re.sub(r"\(\d{2}\)\s*99999-9999", visible_phone, cleaned)
        cleaned = re.sub(r"https://wa\.me/\d{10,15}", f"https://wa.me/{digits}", cleaned)
        cleaned = re.sub(r'href="tel:[^"]+"', f'href="tel:+{digits}"', cleaned)
        cleaned = re.sub(r'("telephone"\s*:\s*")\+?\d{10,15}(")', f'\\1+{digits}\\2', cleaned)
        cleaned = re.sub(r'("telephone"\s*:\s*")\(\d{2}\)\s*99999-9999(")', f'\\1{visible_phone}\\2', cleaned)
    else:
        cleaned = re.sub(r"\(\d{2}\)\s*99999-9999", "", cleaned)
        cleaned = re.sub(r"(?i)\bwhatsapp:\s*\(\d{2}\)\s*99999-9999\b", "", cleaned)
        cleaned = re.sub(r"https://wa\.me/\d{10,15}", "#contato", cleaned)
        cleaned = re.sub(r'href="tel:[^"]+"', 'href="#contato"', cleaned)
        cleaned = re.sub(r'("telephone"\s*:\s*")[^"]*(")', r'\1\2', cleaned)

    if "<img" not in cleaned.lower() and og_image:
        image = (
            f'<img src="{html_lib.escape(str(og_image), quote=True)}" '
            f'alt="{name} em {city}" loading="eager" class="w-full h-auto object-cover">'
        )
        cleaned = re.sub(r"(?is)(<section\b[^>]*>)", r"\1" + image, cleaned, count=1)
    return cleaned


def step_deploy(state: PipelineState) -> PipelineState:
    """Fase 6: Deploy publica site."""
    if state.current_state != STATE_PUBLISHING:
        return state

    try:
        # Slug canônico ASCII (NFKD normaliza acentos → ascii; colapso de separadores).
        from backend.services.pipeline_state import gerar_slug_lead
        slug = gerar_slug_lead(state.lead_data.get("nome", ""), max_len=50)
        if not slug:
            slug = "site"

        # Diretorio: sites/<tenant_id>/<slug>-<lead_id>/
        sites_root = Path(os.getenv("FRALIB_SITES_ROOT", "sites"))
        site_dir = sites_root / str(state.tenant_id) / f"{slug}-{state.lead_id[:8]}"
        site_dir.mkdir(parents=True, exist_ok=True)

        # Escreve index.html
        index_path = site_dir / "index.html"
        html = state.build_output.get("html", "")

        # Pos-processamento cinematográfico DESATIVADO pelo protocolo de unificação.
        # A injeção de assets determinísticos (head tokens, AOS, WhatsApp, LGPD)
        # agora é responsabilidade exclusiva de _inject_deterministic_assets no Builder.
        # try:
        #     from backend.agents.cinematic_post_processor import process as cinematic_process
        #     design_tokens = {}
        #     if state.design_output:
        #         design_tokens = state.design_output.get("tokens_oklch", {}) or {}
        #     html = cinematic_process(
        #         html,
        #         design_tokens=design_tokens,
        #         segmento=state.segmento or "",
        #         nome=state.lead_data.get("nome", "") if state.lead_data else "",
        #         safe_only=True,
        #     )
        # except Exception as e:
        #     print(f"[Deploy] Aviso: pos-processamento tecnico falhou: {e}")

        html = _sanitize_deploy_html(html)
        # _ensure_final_document_contract DESATIVADO pelo protocolo de unificação.
        # Head additions (title, og, canonical, JSON-LD) e phone substitutions
        # destrutivas agora são responsabilidade do Builder (_inject_deterministic_assets).
        final_url = f"https://app.seunegociofralib.site/sites/{state.tenant_id}/{slug}-{state.lead_id[:8]}/"
        # html = _ensure_final_document_contract(html, state, final_url)
        index_path.write_text(html, encoding="utf-8")
        _record_agent_handoff(
            state,
            "deploy",
            received={
                "html_length_before_deploy": len(state.build_output.get("html", "") if state.build_output else ""),
                "quality_score": state.quality_score,
                "visual_fingerprint": state.visual_fingerprint,
            },
            produced={
                "deploy_url": final_url,
                "index_path": str(index_path),
                "html_length_final": len(html),
                "html_counts_final": {
                    "main": html.lower().count("<main"),
                    "h1": html.lower().count("<h1"),
                    "section": html.lower().count("<section"),
                    "img": html.lower().count("<img"),
                    "background_image": html.lower().count("background-image"),
                },
            },
            changed={
                "safe_post_processor": "safe_only",
                "deploy_sanitizer": "document_structure/main_h1/decorative_guard/head_contract",
            },
        )

        try:
            from backend.agents.artifact_store import write_html_artifact, write_json_artifact, artifact_dir
            artifact_path = write_html_artifact(
                run_id=state.run_id,
                lead_id=state.lead_id,
                lead_name=state.lead_data.get("nome", "") if state.lead_data else "",
                filename="05-deploy-final.html",
                html=html,
                metadata={
                    "step": "deploy",
                    "tenant_id": state.tenant_id,
                    "quality_score": state.quality_score,
                    "deploy_url": f"https://app.seunegociofralib.site/sites/{state.tenant_id}/{slug}-{state.lead_id[:8]}/",
                },
            )
            write_json_artifact(
                run_id=state.run_id,
                lead_id=state.lead_id,
                lead_name=state.lead_data.get("nome", "") if state.lead_data else "",
                filename="00-artifacts-index.json",
                payload={
                    "run_id": state.run_id,
                    "lead_id": state.lead_id,
                    "tenant_id": state.tenant_id,
                    "lead_name": state.lead_data.get("nome") if state.lead_data else "",
                    "artifact_dir": str(artifact_dir(state.run_id, state.lead_id, state.lead_data.get("nome", "") if state.lead_data else "")),
                    "latest_deploy_artifact": artifact_path,
                },
                metadata={"step": "index"},
            )
        except Exception as exc:
            logger.warning("[Deploy] artifacts falharam (lead=%s): %s", state.lead_id, exc)

        # Metadata
        meta_path = site_dir / "metadata.json"
        meta_path.write_text(json.dumps({
            "tenant_id": state.tenant_id,
            "lead_id": state.lead_id,
            "slug": slug,
            "lead_name": state.lead_data.get("nome"),
            "cidade": state.cidade,
            "segmento": state.segmento,
            "quality_score": state.quality_score,
            "deployed_at": datetime.now().isoformat(),
            "size_bytes": len(html),
            "paleta": state.design_output.get("paleta", {}) if state.design_output else {},
        }, indent=2, ensure_ascii=False), encoding="utf-8")

        # URL relativa + absoluta
        rel_path = site_dir.relative_to(sites_root)
        state.deploy_url = f"https://app.seunegociofralib.site/sites/{rel_path}/"
        state.deploy_path = str(site_dir.absolute())
        state.history.append(f"Deploy: salvo em {index_path} ({len(html)} bytes)")

        # Knowledge Journal: ProjectPublished
        try:
            journal_record(
                project_id=state.lead_id,
                event_type="project_published",
                hypothesis=f"Site publicado com quality_score {state.quality_score}, deploy em {state.deploy_url}",
                payload={"deploy_url": state.deploy_url, "quality_score": state.quality_score, "size_bytes": len(html)},
            )
        except Exception as exc:
            logger.warning("[manager] journal project_published falhou (lead=%s): %s",
                           state.lead_id, exc)

        # Persist status=concluido + site_url na tabela leads (fail-soft)
        try:
            _db = SessionLocal()
            try:
                # Garantir sessao limpa — step anterior pode ter deixado transacao falha
                _db.rollback()
                _db.execute(
                    _sql("""
                        UPDATE leads SET
                            status = 'concluido',
                            site_url = :url,
                            url_site = :url,
                            erro_pipeline = NULL,
                            atualizado_em = NOW()
                        WHERE id = :lid AND user_id = :tid
                          AND (status IS NULL OR status NOT IN ('descartado'))
                    """),
                    {"url": state.deploy_url, "lid": state.lead_id, "tid": state.tenant_id},
                )
                _db.commit()
            except Exception as exc:
                logger.warning("[manager] deploy DB commit falhou (lead=%s), tentando rollback: %s",
                               state.lead_id, exc)
                try:
                    _db.rollback()
                except Exception as rb_exc:
                    logger.warning("[manager] deploy DB rollback falhou (lead=%s): %s",
                                   state.lead_id, rb_exc)
            finally:
                _db.close()
        except Exception as _pdb:
            logger.error("PIPELINE_DEPLOY_UPDATE_FAILED lead_id=%s tenant_id=%d: %s", state.lead_id, state.tenant_id, _pdb)
    except Exception as e:
        logger.exception("[Deploy] falha ao publicar HTML (lead=%s)", state.lead_id)
        _log_step_error(state, "Deploy", e)
        state.error = "Deploy falhou: erro interno na publicação"
        state.history.append("Deploy ERRO: falha interna na publicação")
        return _transition(state, STATE_FAILED)

    return _transition(state, STATE_OUTREACH)
