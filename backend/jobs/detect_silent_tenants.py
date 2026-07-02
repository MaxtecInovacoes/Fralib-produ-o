"""Sprint 3.3 — Detector de Tenants Silenciosos.

Varre ``users`` ativos e gera alertas ``tenant_alerts`` para 5 critérios:

1. ``admin_inactive_7d`` — ``ultimo_acesso`` nulo ou > 7d (severity: warning)
2. ``no_new_leads_15d`` — sem leads novos > 15d E tenant > 7d de existência (info)
3. ``no_cost_events_3d`` — tenant ativo sem cost_event > 3d (warning)
4. ``subscription_expiring_7d`` — plano vence em <= 7d (critical)
5. ``trial_active_no_use_14d`` — trial > 14d sem login (warning)

Função principal: ``detect_all(engine)`` — retorna lista de dicts
``{tenant_id, alert_type, severity, detail}``.

Dedupe: usa ``SELECT 1 FROM tenant_alerts WHERE status='open'`` antes de
inserir (ON CONFLICT DO NOTHING via partial unique index).

Notificações: ``send_email_notifications(alerts)`` — NO-OP se
``SILENT_TENANT_ALERT_EMAIL`` nao estiver setado; caso contrário, loga
com intenção de envio (delegado ao ``email_service`` se existir).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


# ── Dataclasses ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TenantAlert:
    """Representa um alerta detectado para um tenant."""

    tenant_id: int
    alert_type: str
    severity: str
    detail: dict[str, Any]


# Severities
_INFO = "info"
_WARNING = "warning"
_CRITICAL = "critical"


# ── SQL constants ────────────────────────────────────────────────────────

_SQL_ADMIN_INACTIVE_7D = """
    SELECT id, ultimo_acesso
    FROM users
    WHERE status = 'active'
      AND role != 'superadmin'
      AND (ultimo_acesso IS NULL
           OR ultimo_acesso < NOW() - INTERVAL '7 days')
"""

_SQL_NO_NEW_LEADS_15D = """
    SELECT u.id,
           (SELECT MAX(l.criado_em) FROM leads l WHERE l.user_id = u.id) AS last_lead_at
    FROM users u
    WHERE u.status = 'active'
      AND u.role != 'superadmin'
      AND u.criado_em < NOW() - INTERVAL '7 days'
      AND (
        (SELECT MAX(l.criado_em) FROM leads l WHERE l.user_id = u.id) IS NULL
        OR (SELECT MAX(l.criado_em) FROM leads l WHERE l.user_id = u.id)
             < NOW() - INTERVAL '15 days'
      )
"""

_SQL_NO_COST_EVENTS_3D = """
    SELECT u.id
    FROM users u
    WHERE u.status = 'active'
      AND u.role != 'superadmin'
      AND u.plan_expires_at > NOW()
      AND (SELECT COUNT(*) FROM cost_events ce
            WHERE ce.tenant_id = u.id
              AND ce.criado_em > NOW() - INTERVAL '3 days') = 0
"""

_SQL_SUBSCRIPTION_EXPIRING_7D = """
    SELECT id, plan_expires_at
    FROM users
    WHERE status = 'active'
      AND role != 'superadmin'
      AND plan_expires_at IS NOT NULL
      AND plan_expires_at BETWEEN NOW() AND NOW() + INTERVAL '7 days'
"""

_SQL_TRIAL_NO_USE_14D = """
    SELECT id, criado_em
    FROM users
    WHERE status = 'active'
      AND role != 'superadmin'
      AND status_plano = 'trial'
      AND ultimo_acesso IS NULL
      AND criado_em < NOW() - INTERVAL '14 days'
"""

_SQL_OPEN_ALERT_EXISTS = """
    SELECT 1
    FROM tenant_alerts
    WHERE tenant_id = :tenant_id
      AND alert_type = :alert_type
      AND status = 'open'
    LIMIT 1
"""

_SQL_INSERT_ALERT = """
    INSERT INTO tenant_alerts
        (tenant_id, alert_type, severity, detail, status, criado_em, atualizado_em)
    VALUES
        (:tenant_id, :alert_type, :severity, CAST(:detail AS jsonb),
         'open', NOW(), NOW())
    ON CONFLICT DO NOTHING
"""


# ── Helpers ──────────────────────────────────────────────────────────────

def _open_alert_exists(
    conn: Any, tenant_id: int, alert_type: str,
) -> bool:
    """Retorna True se já existe alerta OPEN para (tenant_id, alert_type)."""
    row = conn.execute(
        text(_SQL_OPEN_ALERT_EXISTS),
        {"tenant_id": tenant_id, "alert_type": alert_type},
    ).fetchone()
    return row is not None


def _insert_alert(conn: Any, alert: TenantAlert) -> bool:
    """Insere alerta, retorna True se inseriu (não duplicado)."""
    import json as _json

    result = conn.execute(
        text(_SQL_INSERT_ALERT),
        {
            "tenant_id": alert.tenant_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "detail": _json.dumps(alert.detail),
        },
    )
    return (result.rowcount or 0) > 0


# ── Detectores individuais ───────────────────────────────────────────────

def detect_admin_inactive_7d(engine: Engine) -> list[dict[str, Any]]:
    """Critério 1: admin nunca logou OU ultimo_acesso > 7 dias."""
    with engine.connect() as conn:
        rows = conn.execute(text(_SQL_ADMIN_INACTIVE_7D)).fetchall()
    return [
        {
            "tenant_id": r[0],
            "alert_type": "admin_inactive_7d",
            "severity": _WARNING,
            "detail": {
                "ultimo_acesso": str(r[1]) if r[1] else None,
            },
        }
        for r in rows
    ]


def detect_no_new_leads_15d(engine: Engine) -> list[dict[str, Any]]:
    """Critério 2: tenant > 7d de existência, sem leads > 15d."""
    with engine.connect() as conn:
        rows = conn.execute(text(_SQL_NO_NEW_LEADS_15D)).fetchall()
    return [
        {
            "tenant_id": r[0],
            "alert_type": "no_new_leads_15d",
            "severity": _INFO,
            "detail": {
                "last_lead_at": str(r[1]) if r[1] else None,
            },
        }
        for r in rows
    ]


def detect_no_cost_events_3d(engine: Engine) -> list[dict[str, Any]]:
    """Critério 3: tenant ativo sem evento de custo > 3d."""
    with engine.connect() as conn:
        rows = conn.execute(text(_SQL_NO_COST_EVENTS_3D)).fetchall()
    return [
        {
            "tenant_id": r[0],
            "alert_type": "no_cost_events_3d",
            "severity": _WARNING,
            "detail": {},
        }
        for r in rows
    ]


def detect_subscription_expiring_7d(engine: Engine) -> list[dict[str, Any]]:
    """Critério 4: plano vence em <= 7d."""
    with engine.connect() as conn:
        rows = conn.execute(text(_SQL_SUBSCRIPTION_EXPIRING_7D)).fetchall()
    return [
        {
            "tenant_id": r[0],
            "alert_type": "subscription_expiring_7d",
            "severity": _CRITICAL,
            "detail": {
                "plan_expires_at": str(r[1]) if r[1] else None,
            },
        }
        for r in rows
    ]


def detect_trial_active_no_use_14d(engine: Engine) -> list[dict[str, Any]]:
    """Critério 5: trial > 14d sem login."""
    with engine.connect() as conn:
        rows = conn.execute(text(_SQL_TRIAL_NO_USE_14D)).fetchall()
    return [
        {
            "tenant_id": r[0],
            "alert_type": "trial_active_no_use_14d",
            "severity": _WARNING,
            "detail": {
                "criado_em": str(r[1]) if r[1] else None,
            },
        }
        for r in rows
    ]


# ── Orquestrador ─────────────────────────────────────────────────────────

def detect_all(
    engine: Engine, *, now: Any = None, dry_run: bool = False,
) -> list[dict[str, Any]]:
    """Executa os 5 critérios, deduplica contra OPEN e persiste (a menos que dry_run).

    Retorna lista de dicts ``{tenant_id, alert_type, severity, detail}``.
    ``now`` é ignorado (mantido pra extensibilidade de testes).
    """
    detectors = (
        detect_admin_inactive_7d,
        detect_no_new_leads_15d,
        detect_no_cost_events_3d,
        detect_subscription_expiring_7d,
        detect_trial_active_no_use_14d,
    )
    raw: list[dict[str, Any]] = []
    for detector in detectors:
        try:
            raw.extend(detector(engine))
        except Exception as exc:
            logger.warning("detector %s falhou: %s", detector.__name__, exc)

    if dry_run:
        return raw

    persisted: list[dict[str, Any]] = []
    with engine.begin() as conn:
        for item in raw:
            try:
                if _open_alert_exists(conn, item["tenant_id"], item["alert_type"]):
                    continue
                alert = TenantAlert(
                    tenant_id=item["tenant_id"],
                    alert_type=item["alert_type"],
                    severity=item["severity"],
                    detail=item.get("detail", {}),
                )
                if _insert_alert(conn, alert):
                    persisted.append(item)
            except Exception as exc:
                logger.warning(
                    "falha ao inserir alerta tenant=%s type=%s: %s",
                    item.get("tenant_id"),
                    item.get("alert_type"),
                    exc,
                )
    return persisted


# ── Email (opcional) ─────────────────────────────────────────────────────

def send_email_notifications(alerts: list[dict[str, Any]]) -> int:
    """Envia notificações por email se env ``SILENT_TENANT_ALERT_EMAIL`` setado.

    NO-OP caso contrário (retorna 0). Retorna quantidade "intent" de envios.
    """
    target = os.getenv("SILENT_TENANT_ALERT_EMAIL", "").strip()
    if not target:
        logger.debug(
            "SILENT_TENANT_ALERT_EMAIL nao setado — no-op (%d alertas silenciados)",
            len(alerts),
        )
        return 0

    if not alerts:
        return 0

    try:
        from backend.services import email_service as _es  # type: ignore
        if hasattr(_es, "send_template"):
            for alert in alerts:
                try:
                    _es.send_template(  # type: ignore[attr-defined]
                        to=target,
                        template="silent_tenant_alert",
                        context=alert,
                    )
                except Exception as exc:
                    logger.warning(
                        "email_service.send_template falhou: %s", exc,
                    )
            logger.info(
                "silent-tenant: %d alertas enviados para %s",
                len(alerts), target,
            )
            return len(alerts)
    except ImportError:
        pass

    # Fallback: só loga
    logger.info(
        "[silent-tenant] target=%s count=%d sample=%s",
        target, len(alerts), alerts[0] if alerts else None,
    )
    return len(alerts)


# ── Entrypoint CLI ───────────────────────────────────────────────────────

def main() -> int:
    """Entry point para cron diario."""
    from backend.core.database import engine as _engine  # type: ignore

    logger.info("detect_silent_tenants: iniciando varredura")
    alerts = detect_all(_engine)
    logger.info("detect_silent_tenants: %d alertas persistidos", len(alerts))
    send_email_notifications(alerts)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
