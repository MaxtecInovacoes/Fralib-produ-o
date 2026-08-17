"""
alerting.py — Sistema central de alertas de sistema (pipeline, QA, worker, deploy).

Uso:
    from backend.core.alerting import alert, get_unresolved, resolve

    # Disparar alerta (best-effort, nunca quebra o caller)
    alert(categoria="pipeline", severity="error",
          titulo="Pipeline travado",
          mensagem="pipeline_lead com heartbeat parado há 5min",
          tenant_id=42)

    # Listar alertas não resolvidos (admin panel)
    alerts = get_unresolved(severity="error", limit=50)

    # Marcar como resolvido
    resolve(alert_id=7)

Severity: info < warning < error < critical
Dedupe: mesmo (categoria, titulo) em 5min → 1 alerta apenas.
"""


import logging
from typing import Any

from backend.core.database import SessionLocal
from sqlalchemy import text

logger = logging.getLogger("fralib.alerting")

_SEVERITY_RANK = {"info": 0, "warning": 1, "error": 2, "critical": 3}
_DEDUPE_SECONDS = 300  # 5 minutos

# Categorias válidas do sistema FraLib
CATEGORIAS = (
    "pipeline", "qa", "deploy", "worker",
    "franz", "openui", "llm", "database", "infra",
)


def alert(
    categoria: str,
    titulo: str,
    mensagem: str,
    severity: str = "warning",
    contexto: dict | None = None,
    lead_id: str | None = None,
    tenant_id: int | None = None,
) -> int | None:
    """Cria alerta de sistema. Retorna ID ou None se dedupado/falhou."""
    if categoria not in CATEGORIAS:
        categoria = "infra"
    if severity not in _SEVERITY_RANK:
        severity = "warning"

    db = SessionLocal()
    alert_id = None
    try:
        # Dedupe: se existe alerta NÃO-resolvido igual nos últimos 5min, retorna ID dele.
        dup = db.execute(text("""
            SELECT id FROM system_alerts
            WHERE categoria = :cat
              AND titulo = :titulo
              AND COALESCE(tenant_id, -1) = COALESCE(:tid, -1)
              AND NOT resolved
              AND criado_em > NOW() - INTERVAL ':secs seconds'
            LIMIT 1
        """), {"cat": categoria, "titulo": titulo, "tid": tenant_id, "secs": _DEDUPE_SECONDS}).fetchone()
        if dup:
            return int(dup[0])

        alert_id = db.execute(text("""
            INSERT INTO system_alerts (categoria, severity, titulo, mensagem, contexto, lead_id, tenant_id)
            VALUES (:cat, :sev, :titulo, :msg, CAST(:ctx AS JSONB), :lead, :tid)
            RETURNING id
        """), {
            "cat": categoria,
            "sev": severity,
            "titulo": titulo[:200],
            "msg": mensagem[:5000],
            "ctx": _json_dump(contexto),
            "lead": lead_id,
            "tid": tenant_id,
        }).fetchone()
        db.commit()
        alert_id = int(alert_id[0]) if alert_id else None

        # Log estruturado para ELK/Datadog
        logger.warning("ALERT %s[%s] #%s: %s — %s", categoria, severity, alert_id, titulo, mensagem)

        # Critical → notificar imediatamente (log + opcional webhook futuro)
        if severity == "critical":
            logger.error("CRITICAL ALERT #%s: %s | %s", alert_id, titulo, mensagem)

    except Exception as exc:
        db.rollback()
        logger.error("alert() falhou: %s", exc)
    finally:
        db.close()
    return alert_id


def get_unresolved(
    categoria: str | None = None,
    severity: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Lista alertas não resolvidos. Filtra opcionalmente por categoria/severity."""
    where = ["NOT resolved"]
    params: dict[str, Any] = {"lim": max(1, min(int(limit), 500))}
    if categoria:
        where.append("categoria = :cat")
        params["cat"] = categoria
    if severity:
        where.append("severity = :sev")
        params["sev"] = severity

    db = SessionLocal()
    try:
        rows = db.execute(text(f"""
            SELECT id, categoria, severity, titulo, mensagem, contexto,
                   lead_id, tenant_id, criado_em
            FROM system_alerts
            WHERE {' AND '.join(where)}
            ORDER BY CASE severity
                WHEN 'critical' THEN 1
                WHEN 'error' THEN 2
                WHEN 'warning' THEN 3
                ELSE 4 END,
                criado_em DESC
            LIMIT :lim
        """), params).fetchall()
        return [
            {
                "id": r[0],
                "categoria": r[1],
                "severity": r[2],
                "titulo": r[3],
                "mensagem": r[4],
                "contexto": r[5] if isinstance(r[5], dict) else None,
                "lead_id": r[6],
                "tenant_id": r[7],
                "criado_em": r[8].isoformat() if r[8] else None,
            }
            for r in rows
        ]
    except Exception as exc:
        logger.error("get_unresolved() falhou: %s", exc)
        return []
    finally:
        db.close()


def resolve(alert_id: int) -> bool:
    """Marca alerta como resolvido. Retorna True se OK."""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            UPDATE system_alerts
            SET resolved = TRUE, resolved_at = NOW()
            WHERE id = :id AND NOT resolved
        """), {"id": alert_id})
        db.commit()
        return bool(result.rowcount)
    except Exception as exc:
        db.rollback()
        logger.error("resolve() falhou: %s", exc)
        return False
    finally:
        db.close()


def purge_resolved(older_than_days: int = 30) -> int:
    """Remove alertas resolvidos antigos. Retorna quantidade deletada."""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            DELETE FROM system_alerts
            WHERE resolved AND resolved_at < NOW() - INTERVAL ':d days'
        """), {"d": max(1, int(older_than_days))})
        db.commit()
        return result.rowcount
    except Exception as exc:
        db.rollback()
        logger.error("purge_resolved() falhou: %s", exc)
        return 0
    finally:
        db.close()


def _json_dump(obj: Any) -> str:
    if obj is None:
        return "{}"
    import json
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        return "{}"
