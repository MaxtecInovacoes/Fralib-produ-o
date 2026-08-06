"""
Endpoints de status do usuario — apenas GET /status e GET /check.

Rotas duplicadas (/sync-cakto, /pricing, /balance) foram consolidadas
em backend/endpoints/credits/checkout.py para evitar conflito de rota
no FastAPI (segundo registro silenciosamente vence).
"""
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from backend.core.auth import get_current_user
from backend.core.db_imports import Session
from backend.core.database import get_db

router = APIRouter(prefix="/api/credits", tags=["credits-status"])


@router.get("/status")
async def get_status(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Retorna status do plano e creditos do usuario."""
    row = db.execute(text(
        "SELECT plano, creditos, creditos_max, plano_pago, trial_expires_at FROM users WHERE id=:id"
    ), {"id": usuario["id"]}).fetchone()
    if not row:
        raise HTTPException(404, "Usuario nao encontrado")
    return {
        "plano": row[0],
        "creditos": row[1],
        "creditos_max": row[2],
        "plano_pago": row[3],
        "trial_expires_at": row[4],
    }


@router.get("/check")
async def credits_check(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Verifica se usuario pode iniciar pipeline."""
    row = db.execute(text(
        "SELECT creditos, creditos_max, plano FROM users WHERE id=:id"
    ), {"id": usuario["id"]}).fetchone()
    if not row:
        raise HTTPException(404, "Usuario nao encontrado")
    creditos = row[0] or 0
    plano = row[2] or "trial"
    is_unlimited = plano.lower() in ("ilimitado", "agency", "admin", "beta")
    role = (usuario.get("role") or "").lower()
    can_proceed = creditos > 0 or is_unlimited or role == "superadmin"
    alert = None
    if creditos == 1:
        payment_link = os.getenv("CAKTO_PAYMENT_LINK", "/planos")
        alert = {
            "message": "Ultimo ciclo disponivel. Considere fazer upgrade ou recarregar creditos.",
            "icon": "!",
            "color": "#f59e0b",
            "payment_link": payment_link,
        }
    return {
        "can_proceed": can_proceed,
        "creditos": creditos,
        "creditos_max": row[1] or 0,
        "plano": plano,
        "alert": alert,
        "is_unlimited": is_unlimited or role == "superadmin",
        "tokens_restantes": creditos,
        "reset_em": None if plano == "trial" else "proximo mes",
        "erro": None if is_unlimited or role == "superadmin" else (
            "Voce usou seu site gratuito. Assine um plano para continuar gerando sites."
            if (not can_proceed and plano == "trial")
            else ("Sem ciclos disponiveis. Faca upgrade ou recarregue creditos para continuar."
                  if not can_proceed else None)
        ),
    }
