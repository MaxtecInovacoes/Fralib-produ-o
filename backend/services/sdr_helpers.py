"""
Helpers compartilhados para o fluxo SDR (worker + cron endpoints).

Centraliza checagens usadas em mais de um caminho de execucao para evitar
duplicacao e manter consistencia (ex: bloqueio por incidente de qualidade).
"""
from __future__ import annotations

from typing import Optional


def _sdr_quality_hold_reason(db, lead_id: Optional[str], tenant_id: Optional[int]) -> Optional[str]:
    """Return a reason when a lead was quarantined after a publication incident.

    Returns a human-readable string when the lead (or its inventory snapshot)
    carries a quality-block marker (``blocked_quality*``, ``quality_hold``, or
    one of the textual alerts ``quality incident`` / ``wrong-niche`` /
    ``generic``). Returns ``None`` when the lead is safe to engage or when
    the lookup cannot be performed.
    """

    if not lead_id or not tenant_id:
        return None
    try:
        from sqlalchemy import text as _txt

        row = db.execute(
            _txt(
                """
                SELECT
                    COALESCE(to_jsonb(l)->>'sdr_stage', '') AS lead_stage,
                    COALESCE(to_jsonb(l)->>'status', '') AS lead_status,
                    COALESCE(to_jsonb(l)->>'erro_pipeline', '') AS erro_pipeline,
                    COALESCE(to_jsonb(l)->>'pipeline_alerta', '') AS pipeline_alerta,
                    COALESCE(li.status, '') AS inventory_status,
                    COALESCE(li.erro, '') AS inventory_error
                FROM leads l
                LEFT JOIN lead_inventory li
                  ON li.lead_id = l.id
                 AND li.tenant_id = l.user_id
                WHERE l.id = :lead_id
                  AND l.user_id = :tenant_id
                LIMIT 1
                """
            ),
            {"lead_id": lead_id, "tenant_id": tenant_id},
        ).fetchone()
    except Exception:
        return None
    if not row:
        return None

    values = [str(value or "").lower() for value in row]
    if any(value.startswith("blocked_quality") for value in values):
        return "lead bloqueado por incidente de qualidade"
    if any(value == "quality_hold" for value in values):
        return "lead/inventario em quality_hold"
    joined = " ".join(values)
    if "quality incident" in joined or "wrong-niche" in joined or "generic" in joined:
        return "alerta de qualidade bloqueia SDR"
    return None