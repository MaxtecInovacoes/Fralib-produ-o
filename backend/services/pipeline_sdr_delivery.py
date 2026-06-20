"""Regras de entrega SDR acionadas pela pipeline."""

from sqlalchemy import text

from backend.services.credits_manager import plano_tem_sdr


def tenant_sdr_allowed(db, tenant_id: int) -> bool:
    """Retorna se o tenant pode receber envio SDR no plano/status atual."""
    row = db.execute(
        text("SELECT plano, status, trial_expires_at FROM users WHERE id=:id"),
        {"id": tenant_id},
    ).fetchone()
    if not row:
        return False
    plano = ((row[0] if row else "") or "").lower()
    status = ((row[1] if row else "") or "").lower()
    trial_expires_at = row[2] if row else None
    return plano_tem_sdr(plano, status, trial_expires_at)
