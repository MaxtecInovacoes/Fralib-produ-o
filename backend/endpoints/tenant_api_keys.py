"""
Tenant API Keys - Permite que tenants acessem a API via API key.

Útil para integrações e automações de terceiros.
"""
import secrets
import hashlib
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from backend.core.database import get_db
from backend.core.auth import get_current_user


router = APIRouter(prefix="/api/tenant/api-keys", tags=["tenant-api-keys"])


class CreateAPIKeyRequest(BaseModel):
    name: str = "Primary"
    scopes: list[str] = ["leads:read", "pipeline:read"]


class APIKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str  # Primeiros 8 chars para identificação
    scopes: list[str]
    created_at: datetime
    last_used_at: datetime | None
    is_active: bool


def _hash_key(api_key: str) -> str:
    """Hash da API key usando SHA-256 (nunca armazena a key em plaintext)."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def _generate_key() -> str:
    """Gera uma API key segura."""
    return f"fralib_{secrets.token_urlsafe(32)}"


@router.post("")
def create_api_key(
    request: CreateAPIKeyRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Cria uma nova API key para o tenant.

    A key completa é retornada APENAS uma vez - depois só mostra o prefixo.
    """
    tenant_id = user.get("tenant_id", user["id"])
    api_key = _generate_key()
    key_hash = _hash_key(api_key)
    key_prefix = api_key[:12]

    db.execute(
        text("""
            INSERT INTO tenant_api_keys (user_id, key_hash, name, scopes, created_at, is_active)
            VALUES (:user_id, :key_hash, :name, :scopes, NOW(), true)
        """),
        {
            "user_id": tenant_id,
            "key_hash": key_hash,
            "name": request.name,
            "scopes": ",".join(request.scopes),
        }
    )
    db.commit()

    return {
        "id": f"key_{key_prefix}",
        "name": request.name,
        "key": api_key,  # MOSTRADO APENAS UMA VEZ
        "key_prefix": key_prefix,
        "scopes": request.scopes,
        "created_at": datetime.now().isoformat(),
        "warning": "Guarde esta key com segurança - não será mostrada novamente!",
    }


@router.get("")
def list_api_keys(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Lista todas as API keys do tenant (sem mostrar as keys completas)."""
    tenant_id = user.get("tenant_id", user["id"])
    rows = db.execute(
        text("""
            SELECT id, name, scopes, created_at, last_used_at, is_active
            FROM tenant_api_keys
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """),
        {"user_id": tenant_id},
    ).fetchall()

    return [
        {
            "id": str(row.id),
            "name": row.name,
            "scopes": row.scopes.split(",") if row.scopes else [],
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
            "is_active": row.is_active,
        }
        for row in rows
    ]


@router.delete("/{key_id}")
def delete_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Deleta uma API key do tenant."""
    tenant_id = user.get("tenant_id", user["id"])
    result = db.execute(
        text("""
            DELETE FROM tenant_api_keys
            WHERE id = :key_id AND user_id = :user_id
        """),
        {"key_id": key_id, "user_id": tenant_id},
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(404, "API key não encontrada")

    return {"message": "API key deletada"}


@router.post("/{key_id}/deactivate")
def deactivate_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Desativa uma API key (pode reativar depois)."""
    tenant_id = user.get("tenant_id", user["id"])
    result = db.execute(
        text("""
            UPDATE tenant_api_keys
            SET is_active = false
            WHERE id = :key_id AND user_id = :user_id
        """),
        {"key_id": key_id, "user_id": tenant_id},
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(404, "API key não encontrada")

    return {"message": "API key desativada"}


@router.post("/{key_id}/activate")
def activate_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Reativa uma API key."""
    tenant_id = user.get("tenant_id", user["id"])
    result = db.execute(
        text("""
            UPDATE tenant_api_keys
            SET is_active = true
            WHERE id = :key_id AND user_id = :user_id
        """),
        {"key_id": key_id, "user_id": tenant_id},
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(404, "API key não encontrada")

    return {"message": "API key reativada"}


# ============================================================
# Middleware para validar API key em requests
# ============================================================

def validate_api_key(db: Session, api_key: str) -> dict | None:
    """
    Valida uma API key e retorna o tenant se válida.

    Returns None se inválida ou inativa.
    Atualiza last_used_at em caso de sucesso.
    """
    if not api_key or not api_key.startswith("fralib_"):
        return None

    key_hash = _hash_key(api_key)
    row = db.execute(
        text("""
            SELECT tak.user_id, tak.scopes, u.status, u.plano
            FROM tenant_api_keys tak
            JOIN users u ON u.id = tak.user_id
            WHERE tak.key_hash = :key_hash AND tak.is_active = true
        """),
        {"key_hash": key_hash},
    ).fetchone()

    if not row:
        return None

    # Atualiza last_used_at
    db.execute(
        text("UPDATE tenant_api_keys SET last_used_at = NOW() WHERE key_hash = :key_hash"),
        {"key_hash": key_hash},
    )
    db.commit()

    return {
        "tenant_id": row.user_id,
        "scopes": row.scopes.split(",") if row.scopes else [],
        "status": row.status,
        "plano": row.plano,
    }
