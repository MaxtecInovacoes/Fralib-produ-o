"""
Mobile responsiveness audit (G5).

Depois do site ser gerado/publicado, abre o site final num viewport
mobile (375x812) via Playwright headless e mede horizontal overflow.
Se detectar overflow, marca o lead como 'mobile_audit_fail' para o
pipeline re-rodar a fase 9 com constraints mais agressivas.

FAIL-OPEN: se Playwright/DB falhar, não bloqueia o pipeline.
Apenas loga warning. (Mesma política que phone_health_service.)

Uso:
    from backend.services.mobile_audit_service import audit_site_mobile
    result = audit_site_mobile(site_url, lead_id, tenant_id)
    # result = {"ok": True/False, "overflow_px": int, "viewport": "375x812"}
"""

from __future__ import annotations

import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Viewports a testar (mobile portrait + tablet)
VIEWPORTS = [
    {"name": "mobile-375", "width": 375, "height": 812},   # iPhone X base
    {"name": "mobile-320", "width": 320, "height": 568},   # iPhone SE 1ª gen
    {"name": "tablet-768", "width": 768, "height": 1024},  # iPad portrait
]

# Tolerância: 4px de scroll horizontal é aceitável (subpixel rounding)
OVERFLOW_TOLERANCE_PX = 4

# Threshold para considerar "fail" - se TODOS os viewports mobile overflow > 8px
OVERFLOW_FAIL_THRESHOLD_PX = 8

# Toggle: desabilita audit mobile (em dev local sem Playwright)
ENABLED = os.getenv("MOBILE_AUDIT_ENABLED", "1").lower() in {"1", "true", "yes", "on"}

# Timeout total por viewport (segundos)
TIMEOUT_PER_VIEWPORT = int(os.getenv("MOBILE_AUDIT_TIMEOUT", "15"))


def _check_viewport(page, viewport: Dict) -> Dict:
    """Abre page no viewport, mede horizontal overflow, retorna dict."""
    try:
        page.set_viewport_size({"width": viewport["width"], "height": viewport["height"]})
        # Aguarda 800ms pra fonts/images carregarem
        page.wait_for_timeout(800)
        # Mede: documentElement.scrollWidth - clientWidth
        metrics = page.evaluate("""
            () => {
                const root = document.documentElement;
                return {
                    scrollWidth: root.scrollWidth,
                    clientWidth: root.clientWidth,
                    bodyScrollWidth: document.body ? document.body.scrollWidth : 0,
                    hasHorizontalScroll: root.scrollWidth > (root.clientWidth + 4)
                };
            }
        """)
        overflow_px = max(
            metrics.get("scrollWidth", 0) - metrics.get("clientWidth", 0),
            metrics.get("bodyScrollWidth", 0) - metrics.get("clientWidth", 0),
            0,
        )
        return {
            "name": viewport["name"],
            "width": viewport["width"],
            "height": viewport["height"],
            "overflow_px": int(overflow_px),
            "scroll_width": int(metrics.get("scrollWidth", 0)),
            "client_width": int(metrics.get("clientWidth", 0)),
            "has_overflow": overflow_px > OVERFLOW_TOLERANCE_PX,
        }
    except Exception as e:
        logger.warning(f"[MobileAudit] Erro medindo {viewport['name']}: {e}")
        return {
            "name": viewport["name"],
            "width": viewport["width"],
            "height": viewport["height"],
            "error": str(e)[:200],
        }


def audit_site_mobile(site_url: str, lead_id: int | str, tenant_id: int | str) -> Dict:
    """Roda audit mobile. Retorna dict com status e métricas por viewport.

    FAIL-OPEN: se Playwright/DB falhar, retorna {"ok": True, "skipped": reason}.
    """
    if not ENABLED:
        return {"ok": True, "skipped": "MOBILE_AUDIT_ENABLED=0"}

    if not site_url or not site_url.startswith("http"):
        return {"ok": True, "skipped": "site_url invalida"}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"ok": True, "skipped": "playwright nao instalado"}

    results = []
    overall_overflow = 0
    failed_viewports = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
            )
            page = context.new_page()
            try:
                page.goto(site_url, timeout=TIMEOUT_PER_VIEWPORT * 1000, wait_until="domcontentloaded")
            except Exception as nav_err:
                browser.close()
                return {
                    "ok": True,  # fail-open
                    "skipped": f"nav falhou: {str(nav_err)[:100]}",
                    "site_url": site_url,
                }

            for vp in VIEWPORTS:
                r = _check_viewport(page, vp)
                results.append(r)
                if r.get("has_overflow"):
                    overflow = r.get("overflow_px", 0)
                    overall_overflow = max(overall_overflow, overflow)
                    if overflow > OVERFLOW_FAIL_THRESHOLD_PX:
                        failed_viewports.append(vp["name"])

            browser.close()
    except Exception as e:
        logger.warning(f"[MobileAudit] Falha geral (fail-open): {e}")
        return {
            "ok": True,  # fail-open
            "skipped": f"playwright erro: {str(e)[:100]}",
            "site_url": site_url,
        }

    # Mobile portrait falha = site precisa re-rodar com constraints
    mobile_failed = [v for v in failed_viewports if v.startswith("mobile-")]
    needs_regen = len(mobile_failed) >= 1  # qualquer mobile que falhou

    audit_result = {
        "ok": not needs_regen,
        "needs_regen": needs_regen,
        "site_url": site_url,
        "lead_id": lead_id,
        "tenant_id": tenant_id,
        "max_overflow_px": overall_overflow,
        "failed_viewports": failed_viewports,
        "viewports": results,
    }

    if needs_regen:
        logger.warning(
            f"[MobileAudit] FAIL lead={lead_id}: overflow max={overall_overflow}px "
            f"em {failed_viewports} (tol={OVERFLOW_TOLERANCE_PX}px)"
        )
    else:
        logger.info(
            f"[MobileAudit] OK lead={lead_id}: max overflow={overall_overflow}px "
            f"em {len(results)} viewports"
        )

    return audit_result


def persist_audit_result(engine, audit_result: Dict) -> bool:
    """Salva resultado do audit em site_mobile_audit (best-effort)."""
    if not audit_result or not audit_result.get("lead_id"):
        return False
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            # Cria tabela se não existir (idempotente)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS site_mobile_audit (
                    id SERIAL PRIMARY KEY,
                    lead_id INTEGER NOT NULL,
                    tenant_id INTEGER,
                    site_url TEXT,
                    ok BOOLEAN NOT NULL DEFAULT TRUE,
                    needs_regen BOOLEAN NOT NULL DEFAULT FALSE,
                    max_overflow_px INTEGER DEFAULT 0,
                    failed_viewports JSONB DEFAULT '[]'::jsonb,
                    viewports JSONB DEFAULT '[]'::jsonb,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_site_mobile_audit_lead
                    ON site_mobile_audit(lead_id, created_at DESC);
            """))
            conn.execute(text("""
                INSERT INTO site_mobile_audit
                    (lead_id, tenant_id, site_url, ok, needs_regen, max_overflow_px, failed_viewports, viewports)
                VALUES (:lid, :tid, :url, :ok, :regen, :overflow, CAST(:failed AS jsonb), CAST(:viewports AS jsonb))
            """), {
                "lid": audit_result["lead_id"],
                "tid": audit_result.get("tenant_id"),
                "url": audit_result.get("site_url", ""),
                "ok": audit_result.get("ok", True),
                "regen": audit_result.get("needs_regen", False),
                "overflow": audit_result.get("max_overflow_px", 0),
                "failed": str(audit_result.get("failed_viewports", [])).replace("'", '"'),
                "viewports": str(audit_result.get("viewports", [])).replace("'", '"'),
            })
            conn.commit()
        return True
    except Exception as e:
        logger.warning(f"[MobileAudit] Falha ao persistir (best-effort): {e}")
        return False
