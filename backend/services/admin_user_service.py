from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session


def set_user_plan(db: Session, user_id: int, plano: str) -> tuple[str, bool]:
    row = db.execute(text("SELECT id FROM users WHERE id = :id"), {"id": user_id}).fetchone()
    if not row:
        raise LookupError("Usuario nao encontrado")
    plano_pago = plano in ("starter", "pro", "beta", "ilimitado")
    status_novo = "ativo" if plano_pago else plano
    db.execute(text(
        "UPDATE users SET plano = :plano, plano_pago = :pago, status = :status WHERE id = :id"
    ), {"plano": plano, "pago": plano_pago, "status": status_novo, "id": user_id})
    db.commit()
    return status_novo, plano_pago


def set_user_creditos(db: Session, user_id: int, creditos: int) -> None:
    row = db.execute(text("SELECT id FROM users WHERE id = :id"), {"id": user_id}).fetchone()
    if not row:
        raise LookupError("Usuario nao encontrado")
    db.execute(text(
        "UPDATE users SET creditos = :c, creditos_max = :c WHERE id = :id"
    ), {"c": creditos, "id": user_id})
    db.commit()


def archive_all_leads(db: Session, tenant_id: int) -> int:
    result = db.execute(text(
        "UPDATE leads SET status='arquivado', atualizado_em=:ts WHERE user_id=:uid AND status != 'arquivado'"
    ), {"uid": tenant_id, "ts": datetime.now().isoformat()})
    db.commit()
    return int(result.rowcount or 0)
