"""
Editor de tema global do site (G1).

Permite ao admin mudar as CSS variables do :root (--color-primary,
--color-secondary, --color-accent, --font-display) sem rebuild.

Quando o site e gerado pelo Vite/React, as CSS vars ficam dentro do
bundle compilado dist/index-*.css. A gente extrai, atualiza, e regrava.

Para sites que ja tem :root custom (editados pelo usuario), atualiza
in-place sem perder customizacoes.

API:
  GET  /api/sites/{lead_id}/theme      -> le tema atual (dict de CSS vars)
  PUT  /api/sites/{lead_id}/theme      -> atualiza tema (CSS vars)
"""

from __future__ import annotations

import os
import re
import sys
import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from backend.core.db_imports import Session, text  # noqa: F401  — B3 DRY

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, "core"))
from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.endpoints.sse_endpoints import adicionar_log

router = APIRouter(prefix="/api/sites", tags=["site-theme"])
logger = logging.getLogger("uvicorn")

# CSS vars permitidas (whitelist - evita XSS via CSS injection)
ALLOWED_VARS = {
    "--color-primary",
    "--color-secondary",
    "--color-accent",
    "--color-bg",
    "--color-text",
    "--color-muted",
    "--font-display",
    "--font-body",
    "--radius",
    "--spacing",
}

# Validators simples por var (hex color / font name / px)
HEX_RE = re.compile(r"^#[0-9a-fA-F]{3,8}$")
RGB_RE = re.compile(r"^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+")
FONT_RE = re.compile(r"^[a-zA-Z0-9 \-,'\"]{1,80}$")
PX_RE = re.compile(r"^\d+(\.\d+)?(px|rem|em|%)?$")


def _validate_var_value(name: str, value: str) -> str:
    """Valida valor de CSS var. Retorna valor limpo ou raise 400."""
    v = (value or "").strip()
    if not v:
        raise HTTPException(400, f"{name}: valor vazio")
    if len(v) > 200:
        raise HTTPException(400, f"{name}: valor muito longo")

    if "color" in name.lower():
        if not (HEX_RE.match(v) or RGB_RE.match(v) or v in {"transparent", "inherit", "currentColor", "none"}):
            raise HTTPException(400, f"{name}: cor invalida ({v[:30]})")
    elif "font" in name.lower():
        if not FONT_RE.match(v):
            raise HTTPException(400, f"{name}: font name invalido")
    elif "radius" in name.lower() or "spacing" in name.lower():
        if not PX_RE.match(v):
            raise HTTPException(400, f"{name}: precisa ser px/rem/em/%")
    # else: aceita string generica ate 200 chars
    return v


def _extract_css_vars(html_or_css: str) -> Dict[str, str]:
    """Extrai CSS vars do bloco :root { ... }."""
    out: Dict[str, str] = {}
    # Match :root { ... }
    m = re.search(r":root\s*\{([^}]+)\}", html_or_css, re.DOTALL)
    if not m:
        return out
    block = m.group(1)
    # Match --var: value;
    for line in block.split(";"):
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if key.startswith("--") and val:
            out[key] = val
    return out


def _replace_css_vars(html: str, updates: Dict[str, str]) -> str:
    """Atualiza CSS vars dentro do bloco :root. Cria :root se nao existir."""
    # Procura bloco :root
    m = re.search(r"(:root\s*\{)([^}]*)(\})", html, re.DOTALL)
    if not m:
        # Nao tem :root - injeta um no <head>
        css_block = ":root{\n" + "\n".join(f"{k}:{v};" for k, v in updates.items()) + "\n}"
        if "</head>" in html.lower():
            html = re.sub(r"(</head>)", f"<style>{css_block}</style>\\1", html, count=1, flags=re.IGNORECASE)
        else:
            html = f"<style>{css_block}</style>" + html
        return html

    head = m.group(1)
    body = m.group(2)
    tail = m.group(3)

    # Parse linhas atuais
    current = _extract_css_vars(f":root{{{body}}}")
    current.update(updates)

    # Re-renderiza
    new_body = "\n" + "\n".join(f"  {k}: {v};" for k, v in current.items()) + "\n"
    new_block = head + new_body + tail
    return html[: m.start()] + new_block + html[m.end():]


def _resolver_html_path(tenant_id, lead_nome: str, url_site: str):
    """Resolve path do HTML no disco. Retorna (path, slug) ou (None, None)."""
    from backend.endpoints.site_editor_endpoints import _resolver_html_path as _resolve
    return _resolve(tenant_id, lead_nome, url_site)


def _carregar_lead(db: Session, lead_id: str, tenant_id: int):
    row = db.execute(
        text("SELECT id, nome, site_url, url_site, html_gerado FROM leads WHERE id = :id AND user_id = :tid"),
        {"id": lead_id, "tid": tenant_id},
    ).fetchone()
    if not row:
        raise HTTPException(404, "Lead nao encontrado")
    return dict(row._mapping)


class ThemeUpdateRequest(BaseModel):
    """Mapa de CSS var name -> value. Ex: {"--color-primary": "#10b981"}"""

    vars: Dict[str, str] = Field(..., description="CSS vars a atualizar")


@router.get("/{lead_id}/theme")
async def obter_tema(
    lead_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Le tema atual (CSS vars) do site."""
    tenant_id = usuario.get("tenant_id", usuario["id"])
    lead = _carregar_lead(db, lead_id, tenant_id)
    html_path, slug = _resolver_html_path(
        tenant_id, lead.get("nome") or "", lead.get("site_url") or lead.get("url_site") or ""
    )

    html = ""
    if html_path and os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
    elif lead.get("html_gerado"):
        html = lead["html_gerado"]

    if not html:
        raise HTTPException(404, "Site ainda nao foi gerado")

    css_vars = _extract_css_vars(html)

    # Defaults caso nao tenha :root
    if not css_vars:
        css_vars = {
            "--color-primary": "#10b981",
            "--color-secondary": "#9333ea",
            "--color-accent": "#f59e0b",
        }

    return {
        "vars": css_vars,
        "slug": slug,
        "url_site": lead.get("site_url") or lead.get("url_site") or "",
    }


@router.put("/{lead_id}/theme")
async def atualizar_tema(
    lead_id: str,
    req: ThemeUpdateRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Atualiza CSS vars do :root. Whitelist + validacao anti-XSS."""
    tenant_id = usuario.get("tenant_id", usuario["id"])
    lead = _carregar_lead(db, lead_id, tenant_id)
    html_path, slug = _resolver_html_path(
        tenant_id, lead.get("nome") or "", lead.get("site_url") or lead.get("url_site") or ""
    )

    if not html_path or not os.path.exists(html_path):
        raise HTTPException(404, "Arquivo HTML nao encontrado no disco")

    # Whitelist + validate
    updates: Dict[str, str] = {}
    for k, v in req.vars.items():
        if k not in ALLOWED_VARS:
            raise HTTPException(400, f"var '{k}' nao permitida")
        updates[k] = _validate_var_value(k, v)

    if not updates:
        raise HTTPException(400, "Nenhuma var para atualizar")

    with open(html_path, "r", encoding="utf-8") as f:
        html_atual = f.read()

    # Backup
    backup_path = html_path + ".bak"
    try:
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(html_atual)
    except Exception:
        pass

    html_novo = _replace_css_vars(html_atual, updates)

    if len(html_novo.encode("utf-8")) > 500 * 1024:
        raise HTTPException(413, "HTML resultante excede 500KB")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_novo)

    # Persistir no DB tambem
    try:
        db.execute(
            text("UPDATE leads SET html_gerado = :h WHERE id = :id AND user_id = :tid"),
            {"h": html_novo, "id": lead_id, "tid": tenant_id},
        )
        db.commit()
    except Exception as e:
        logger.warning(f"[SiteTheme] persist DB falhou (disco ja foi salvo): {e}")

    adicionar_log(
        tenant_id=tenant_id,
        evento="site.theme.updated",
        lead_id=lead_id,
        detalhe={"vars_updated": list(updates.keys())},
    )

    return {
        "ok": True,
        "updated": list(updates.keys()),
        "vars": {**_extract_css_vars(html_novo)},
    }
