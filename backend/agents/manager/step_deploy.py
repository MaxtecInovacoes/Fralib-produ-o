"""Step: Deploy — Fase 6: Publica site em sites/<tenant>/<lead_id>/index.html."""
import logging
import os
import json
import re
import html as html_lib
from pathlib import Path
from datetime import datetime
from backend.agents.manager.states import (
    PipelineState, STATE_PUBLISHING, STATE_OUTREACH, STATE_FAILED,
    _transition, _log_step_error,
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


def _demote_secondary_tag(html: str, original_tag: str, replacement_tag: str) -> str:
    tag_re = re.compile(rf"<(/?){original_tag}\b([^>]*)>", re.IGNORECASE)
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


def _normalize_single_main_and_h1(html: str) -> str:
    html = _demote_secondary_tag(html, "main", "section")
    html = _demote_secondary_tag(html, "h1", "h2")
    return html


def _sanitize_deploy_html(html: str) -> str:
    html = _sanitize_html_document_structure(html)
    html = _sanitize_corrupted_svg_paths(html)
    html = _normalize_single_main_and_h1(html)
    html = _guard_decorative_absolute_blocks(html)
    html = _inject_head_guard_css(html)
    return html


def _ensure_final_document_contract(html: str, state: PipelineState, canonical_url: str) -> str:
    """Última garantia documental, aplicada após todos os pós-processadores."""
    cleaned = html or ""
    name = html_lib.escape(str((state.lead_data or {}).get("nome") or "Negócio local"), quote=True)
    city = html_lib.escape(str(state.cidade or ""), quote=True)
    address = html_lib.escape(str((state.lead_data or {}).get("endereco") or ""), quote=True)
    phone = html_lib.escape(str((state.lead_data or {}).get("telefone") or ""), quote=True)
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
        # Slug a partir do nome do lead
        slug = state.lead_data.get("nome", "site").lower()
        slug = "".join(c if c.isalnum() else "-" for c in slug).strip("-")[:50]
        if not slug:
            slug = "site"

        # Diretorio: sites/<tenant_id>/<slug>-<lead_id>/
        sites_root = Path(os.getenv("FRALIB_SITES_ROOT", "sites"))
        site_dir = sites_root / str(state.tenant_id) / f"{slug}-{state.lead_id[:8]}"
        site_dir.mkdir(parents=True, exist_ok=True)

        # Escreve index.html
        index_path = site_dir / "index.html"
        html = state.build_output.get("html", "")

        # Pos-processamento tecnico seguro: nao altera decisões visuais do PRD/OpenUI.
        try:
            from backend.agents.cinematic_post_processor import process as cinematic_process
            design_tokens = {}
            if state.design_output:
                design_tokens = state.design_output.get("tokens_oklch", {}) or {}
            html = cinematic_process(
                html,
                design_tokens=design_tokens,
                segmento=state.segmento or "",
                nome=state.lead_data.get("nome", "") if state.lead_data else "",
                safe_only=True,
            )
        except Exception as e:
            print(f"[Deploy] Aviso: pos-processamento tecnico falhou: {e}")

        html = _sanitize_deploy_html(html)
        final_url = f"https://app.seunegociofralib.site/sites/{state.tenant_id}/{slug}-{state.lead_id[:8]}/"
        html = _ensure_final_document_contract(html, state, final_url)
        index_path.write_text(html, encoding="utf-8")

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
            from backend.core.database import SessionLocal
            from sqlalchemy import text as _sql
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
        _log_step_error(state, "Deploy", e)
        state.error = f"Deploy falhou: {e}"
        state.history.append(f"Deploy ERRO: {e}")
        return _transition(state, STATE_FAILED)

    return _transition(state, STATE_OUTREACH)
